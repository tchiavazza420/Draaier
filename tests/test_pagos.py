"""Tests del flujo de pagos (seña, modo simulación)."""

from datetime import datetime, time
from decimal import Decimal

from app.models.reserva import EstadoReservaEnum
from app.models.pago import Pago, PagoEstadoEnum
from app.reservas.service import crear_reserva, obtener_o_crear_cliente
from app.pagos.service import iniciar_pago_sena, aprobar_pago, rechazar_pago


def _reserva_con_sena(neg, rec, serv, lunes):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    return crear_reserva(neg.id, serv, rec, cli, datetime.combine(lunes, time(9, 0)),
                         estado=EstadoReservaEnum.PENDIENTE_PAGO)


def test_pago_aprobado_confirma_reserva(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("2000"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)

    pago, url = iniciar_pago_sena(reserva, serv)
    assert pago.estado == PagoEstadoEnum.PENDIENTE
    assert pago.monto == Decimal("2000")
    assert "checkout-simulado" in url  # sin token MP -> simulado

    aprobar_pago(pago)
    assert pago.estado == PagoEstadoEnum.APROBADO
    assert reserva.estado == EstadoReservaEnum.CONFIRMADO


def test_pago_rechazado_mantiene_pendiente(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("1000"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)

    pago, _ = iniciar_pago_sena(reserva, serv)
    rechazar_pago(pago)
    assert pago.estado == PagoEstadoEnum.RECHAZADO
    assert reserva.estado == EstadoReservaEnum.PENDIENTE_PAGO


def test_gateway_segun_metodo_del_negocio(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """El método de pago del negocio determina la pasarela; sin token -> simulado."""
    from app.extensions import db
    from app.models.negocio import MetodoPagoEnum
    from app.models.pago import ProveedorPagoEnum
    from app.pagos.gateways import gateway_para
    from app.pagos import naranja_x, modo

    neg, _ = crear_negocio()
    neg.metodo_pago = MetodoPagoEnum.NARANJA_X
    db.session.commit()

    gw, prov = gateway_para(neg)
    assert gw is naranja_x and prov == ProveedorPagoEnum.NARANJA_X

    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("1500"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)
    pago, url = iniciar_pago_sena(reserva, serv)
    # Sin credenciales de Naranja X -> checkout simulado, proveedor SIMULADO
    assert "checkout-simulado" in url
    assert pago.proveedor == ProveedorPagoEnum.SIMULADO
    # Y el flujo de aprobación confirma igual
    aprobar_pago(pago)
    assert reserva.estado == EstadoReservaEnum.CONFIRMADO

    # Modo también mapea correctamente
    neg.metodo_pago = MetodoPagoEnum.MODO
    db.session.commit()
    gw2, prov2 = gateway_para(neg)
    assert gw2 is modo and prov2 == ProveedorPagoEnum.MODO


def test_aprobacion_idempotente(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("500"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)
    pago, _ = iniciar_pago_sena(reserva, serv)
    aprobar_pago(pago)
    aprobar_pago(pago)  # segunda vez no rompe
    assert Pago.query.filter_by(reserva_id=reserva.id).count() == 1
    assert pago.estado == PagoEstadoEnum.APROBADO
