"""Tests de notificaciones (email + WhatsApp en bandeja dev)."""

from datetime import datetime, time

from app.extensions import db
from app.models.reserva import EstadoReservaEnum
from app.models.cliente import Cliente
from app.reservas.service import crear_reserva, obtener_o_crear_cliente
from app.notificaciones.email import BANDEJA_DEV
from app.notificaciones.whatsapp import BANDEJA_WA
from app.notificaciones.service import (
    notificar_reserva_confirmada, _enviar_recordatorio,
    _avisar_negocio_nueva,
)


def _reserva(neg, rec, serv, lunes, email="ana@test.com", telefono="+5491122334455"):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email=email, telefono=telefono)
    return crear_reserva(neg.id, serv, rec, cli, datetime.combine(lunes, time(9, 0)),
                         estado=EstadoReservaEnum.CONFIRMADO)


def test_confirmacion_email_y_whatsapp(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    BANDEJA_DEV.clear()
    BANDEJA_WA.clear()
    notificar_reserva_confirmada(r)   # eager -> sync

    assert len(BANDEJA_DEV) == 1                  # email
    assert len(BANDEJA_WA) == 1                   # whatsapp
    assert "confirmada" in BANDEJA_WA[-1]["body"].lower()
    assert BANDEJA_WA[-1]["to"] == "5491122334455"  # normalizado (sin +)


def test_toggles_apagan_envios(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """Si el negocio desactiva confirmación o un canal, no se envía por ahí."""
    neg, _ = crear_negocio()
    neg.notif_confirmacion = False          # confirmaciones apagadas
    db.session.commit()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    BANDEJA_DEV.clear(); BANDEJA_WA.clear()
    notificar_reserva_confirmada(r)
    assert len(BANDEJA_DEV) == 0 and len(BANDEJA_WA) == 0   # nada (confirmación off)

    # Reactivar confirmación pero solo canal email
    neg.notif_confirmacion = True
    neg.notif_canal_whatsapp = False
    db.session.commit()
    BANDEJA_DEV.clear(); BANDEJA_WA.clear()
    notificar_reserva_confirmada(r)
    assert len(BANDEJA_DEV) == 1 and len(BANDEJA_WA) == 0   # solo email


def test_aviso_al_negocio_por_turno_nuevo(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """Cuando entra un turno, el NEGOCIO recibe un email de aviso (a su email)."""
    neg, _ = crear_negocio(email="local@test.com")
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    BANDEJA_DEV.clear()
    _avisar_negocio_nueva(r)

    assert len(BANDEJA_DEV) == 1
    aviso = BANDEJA_DEV[-1]
    assert aviso["to"] == "local@test.com"
    assert "nuevo turno" in aviso["subject"].lower()


def test_push_suscribir_guarda_suscripcion(client, crear_negocio, login, monkeypatch):
    """El endpoint de suscripción push guarda la suscripción del navegador."""
    from app.notificaciones import push
    from app.models.push import PushSubscription
    neg, dueno = crear_negocio()
    login(dueno.email)
    monkeypatch.setattr(push, "esta_configurado", lambda: True)

    sub = {"endpoint": "https://push.example/abc",
           "keys": {"p256dh": "clave-p", "auth": "clave-a"}}
    r = client.post("/panel/push/suscribir", json=sub)
    assert r.status_code == 200 and r.get_json()["ok"] is True

    guardada = PushSubscription.query.filter_by(negocio_id=neg.id).first()
    assert guardada is not None
    assert guardada.endpoint == "https://push.example/abc"
    assert guardada.usuario_id == dueno.id


def test_confirmacion_usa_plantilla_wa_si_esta_configurada(
        app, crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """Con WHATSAPP_TEMPLATE_CONFIRMACION seteado, la confirmación sale como template."""
    from app.notificaciones.service import _enviar_confirmada
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    app.config["WHATSAPP_TEMPLATE_CONFIRMACION"] = "reserva_confirmada"
    try:
        BANDEJA_WA.clear()
        _enviar_confirmada(r)
    finally:
        app.config["WHATSAPP_TEMPLATE_CONFIRMACION"] = None

    assert len(BANDEJA_WA) == 1
    assert "template:reserva_confirmada" in BANDEJA_WA[-1]["body"]
    # La confirmación incluye el profesional (4ª variable).
    assert rec.nombre in BANDEJA_WA[-1]["body"]


def test_recordatorio_usa_plantilla_wa_si_esta_configurada(
        app, crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """Con WHATSAPP_TEMPLATE_RECORDATORIO seteado, el recordatorio sale como template."""
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    app.config["WHATSAPP_TEMPLATE_RECORDATORIO"] = "recordatorio_turno"
    try:
        BANDEJA_WA.clear()
        _enviar_recordatorio(r)
    finally:
        app.config["WHATSAPP_TEMPLATE_RECORDATORIO"] = None

    assert len(BANDEJA_WA) == 1
    assert "template:recordatorio_turno" in BANDEJA_WA[-1]["body"]
    # El recordatorio también incluye el profesional (4ª variable).
    assert rec.nombre in BANDEJA_WA[-1]["body"]


def test_recordatorio_2h_envia_solo_los_proximos(crear_negocio, crear_recurso, crear_servicio):
    """Recordatorio 'X horas antes': avisa a los que empiezan dentro de la ventana
    y los marca; no toca los que están más lejos."""
    from datetime import datetime, timedelta
    from app.models.reserva import Reserva, EstadoReservaEnum
    from app.notificaciones.service import enviar_recordatorios_proximas

    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")

    def _reserva(delta_horas, codigo):
        ini = datetime.now() + timedelta(hours=delta_horas)
        r = Reserva(negocio_id=neg.id, codigo=codigo, cliente_id=cli.id,
                    servicio_id=serv.id, recurso_id=rec.id, inicio=ini,
                    fin=ini + timedelta(minutes=60), estado=EstadoReservaEnum.CONFIRMADO)
        db.session.add(r); db.session.flush()
        return r

    cercana = _reserva(1, "PROX0001")      # dentro de 1 h -> entra
    lejana = _reserva(5, "LEJO0001")       # dentro de 5 h -> no entra
    db.session.commit()

    BANDEJA_DEV.clear()
    n = enviar_recordatorios_proximas(horas=2)
    assert n == 1
    db.session.refresh(cercana); db.session.refresh(lejana)
    assert cercana.recordatorio_2h_enviado is True
    assert lejana.recordatorio_2h_enviado is False

    # Segunda corrida: no reenvía la ya avisada.
    assert enviar_recordatorios_proximas(horas=2) == 0


def test_sin_telefono_no_manda_whatsapp(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    cli = Cliente(negocio_id=neg.id, nombre="SinTel", email="x@test.com", telefono=None)
    db.session.add(cli)
    db.session.flush()
    r = crear_reserva(neg.id, serv, rec, cli, datetime.combine(proximo_lunes, time(9, 0)),
                      estado=EstadoReservaEnum.CONFIRMADO)

    BANDEJA_WA.clear()
    _enviar_recordatorio(r)
    assert len(BANDEJA_WA) == 0   # sin teléfono, no se envía WA
