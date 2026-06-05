"""
tests/test_reserva_gestion.py
-----------------------------
Reprogramar / cancelar (con reembolso de seña según política) y confirmar
asistencia desde el recordatorio.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.reserva import EstadoReservaEnum
from app.models.pago import Pago, PagoEstadoEnum, ProveedorPagoEnum
from app.reservas.service import (
    crear_reserva, obtener_o_crear_cliente,
    reprogramar_reserva, cancelar_reserva, cliente_puede_gestionar,
)


def _reserva(neg, rec, serv, lunes, hora=9, estado=EstadoReservaEnum.CONFIRMADO):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com", telefono="+5491100000000")
    return crear_reserva(neg.id, serv, rec, cli,
                         datetime.combine(lunes, time(hora, 0)), estado=estado)


def test_reprogramar_mueve_el_turno(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, duracion=60)
    r = _reserva(neg, rec, serv, proximo_lunes, hora=9)

    nuevo = datetime.combine(proximo_lunes, time(11, 0))
    reprogramar_reserva(r, nuevo)
    assert r.inicio == nuevo
    assert r.fin == nuevo + timedelta(minutes=60)
    assert r.asistencia_confirmada is False


def test_reprogramar_a_horario_ocupado_falla(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    from app.reservas.service import ReservaError
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, duracion=60)
    r1 = _reserva(neg, rec, serv, proximo_lunes, hora=9)
    # Segundo cliente ocupa las 11:00.
    cli2 = obtener_o_crear_cliente(neg.id, "Bob", email="bob@test.com")
    crear_reserva(neg.id, serv, rec, cli2, datetime.combine(proximo_lunes, time(11, 0)),
                  estado=EstadoReservaEnum.CONFIRMADO)
    try:
        reprogramar_reserva(r1, datetime.combine(proximo_lunes, time(11, 0)))
        assert False, "debería fallar por horario ocupado"
    except ReservaError:
        pass


def test_cancelar_con_reembolso_dentro_de_plazo(crear_negocio, crear_recurso, crear_servicio):
    neg, _ = crear_negocio()
    neg.reembolso_sena_horas = 24
    db.session.commit()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    # Reserva lejana (48 h) con seña aprobada; la armo directo para controlar la fecha.
    from app.models.reserva import Reserva
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    inicio = datetime.now() + timedelta(hours=48)
    r = Reserva(negocio_id=neg.id, codigo="ABCD1234", cliente_id=cli.id,
                servicio_id=serv.id, recurso_id=rec.id, inicio=inicio,
                fin=inicio + timedelta(minutes=60), estado=EstadoReservaEnum.CONFIRMADO,
                precio=Decimal("1000"))
    db.session.add(r)
    db.session.flush()
    db.session.add(Pago(negocio_id=neg.id, reserva_id=r.id, monto=Decimal("300"),
                        estado=PagoEstadoEnum.APROBADO, proveedor=ProveedorPagoEnum.TRANSFERENCIA,
                        es_sena=True))
    db.session.commit()

    _, reembolsada = cancelar_reserva(r, neg, por_cliente=True)
    assert r.estado == EstadoReservaEnum.CANCELADO
    assert reembolsada is True
    assert r.pagos[0].estado == PagoEstadoEnum.REEMBOLSADO


def test_cancelar_fuera_de_plazo_no_reembolsa(crear_negocio, crear_recurso, crear_servicio):
    neg, _ = crear_negocio()
    neg.reembolso_sena_horas = 24
    db.session.commit()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    from app.models.reserva import Reserva
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    inicio = datetime.now() + timedelta(hours=2)   # dentro de 2 h: ya no reembolsa
    r = Reserva(negocio_id=neg.id, codigo="EFGH5678", cliente_id=cli.id,
                servicio_id=serv.id, recurso_id=rec.id, inicio=inicio,
                fin=inicio + timedelta(minutes=60), estado=EstadoReservaEnum.CONFIRMADO,
                precio=Decimal("1000"))
    db.session.add(r)
    db.session.flush()
    db.session.add(Pago(negocio_id=neg.id, reserva_id=r.id, monto=Decimal("300"),
                        estado=PagoEstadoEnum.APROBADO, proveedor=ProveedorPagoEnum.TRANSFERENCIA,
                        es_sena=True))
    db.session.commit()

    _, reembolsada = cancelar_reserva(r, neg, por_cliente=True)
    assert r.estado == EstadoReservaEnum.CANCELADO
    assert reembolsada is False
    assert r.pagos[0].estado == PagoEstadoEnum.APROBADO   # no se tocó


def test_confirmar_asistencia_por_link(client, crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    resp = client.post(f"/{neg.slug}/reserva/{r.codigo}/asistir", follow_redirects=False)
    assert resp.status_code in (301, 302)
    db.session.refresh(r)
    assert r.asistencia_confirmada is True
