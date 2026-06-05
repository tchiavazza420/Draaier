"""
tests/test_cron_tareas.py
-------------------------
Endpoint /tareas/correr: protegido por CRON_TOKEN, dispara recordatorios y
vencimiento de suscripciones (para cron externo en plan free).
"""

from datetime import datetime, timedelta

from app.extensions import db
from app.models.cliente import Cliente
from app.models.reserva import Reserva, EstadoReservaEnum
from app.models.negocio import EstadoSuscripcionEnum


def _reserva_para_manana(neg, recurso, servicio, con_email=True, con_tel=False):
    import uuid
    cli = Cliente(negocio_id=neg.id, nombre="Cli",
                  email="c@x.com" if con_email else None,
                  telefono="+5493510000000" if con_tel else None)
    db.session.add(cli); db.session.flush()
    ini = datetime.combine((datetime.now() + timedelta(days=1)).date(),
                           datetime.min.time().replace(hour=10))
    r = Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:10].upper(),
                cliente_id=cli.id, servicio_id=servicio.id, recurso_id=recurso.id,
                inicio=ini, fin=ini + timedelta(hours=1),
                estado=EstadoReservaEnum.CONFIRMADO)
    db.session.add(r); db.session.commit()
    return r


def test_sin_token_configurado_404(client, app):
    app.config["CRON_TOKEN"] = None
    r = client.post("/tareas/correr")
    assert r.status_code == 404


def test_token_incorrecto_403(client, app):
    app.config["CRON_TOKEN"] = "secreto"
    r = client.post("/tareas/correr", headers={"X-Cron-Token": "mal"})
    assert r.status_code == 403


def test_dispara_recordatorios_y_vencimientos(client, app, crear_negocio,
                                              crear_recurso, crear_servicio):
    app.config["CRON_TOKEN"] = "secreto"
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, [rec])
    _reserva_para_manana(neg, rec, serv, con_email=True)

    # Un negocio vencido (trial pasado) para ver el conteo de vencimientos.
    neg.estado_suscripcion = EstadoSuscripcionEnum.TRIAL
    neg.trial_fin = datetime.now() - timedelta(days=1)
    db.session.commit()

    r = client.post("/tareas/correr?dias=1", headers={"X-Cron-Token": "secreto"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["recordatorios_enviados"] >= 1
    assert data["suscripciones_vencidas"] >= 1


def test_cron_no_falla_si_una_tarea_revienta(client, app, monkeypatch):
    """Si una tarea lanza excepción, el endpoint igual responde 200 con el error
    (para que el cron de Render no se marque como fallido)."""
    app.config["CRON_TOKEN"] = "secreto"
    import app.notificaciones.service as svc

    def _boom(*a, **k):
        raise RuntimeError("explotó")

    monkeypatch.setattr(svc, "enviar_recordatorios", _boom)

    r = client.post("/tareas/correr", headers={"X-Cron-Token": "secreto"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["recordatorios_enviados"] is None
    assert any("recordatorios_enviados" in e for e in data["errores"])


def test_recordatorio_a_cliente_solo_whatsapp(client, app, crear_negocio,
                                              crear_recurso, crear_servicio):
    """Cliente sin email pero con teléfono igual recibe recordatorio."""
    app.config["CRON_TOKEN"] = "secreto"
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, [rec])
    _reserva_para_manana(neg, rec, serv, con_email=False, con_tel=True)

    r = client.post("/tareas/correr", headers={"Authorization": "Bearer secreto"})
    assert r.status_code == 200
    assert r.get_json()["recordatorios_enviados"] >= 1
