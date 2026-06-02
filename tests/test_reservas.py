"""Tests del motor de reservas: doble-reserva, capacidad y estados."""

from datetime import datetime, time

import pytest

from app.models.reserva import EstadoReservaEnum
from app.reservas.service import (
    crear_reserva, cambiar_estado, obtener_o_crear_cliente, ReservaError,
)


def _inicio(lunes, h=9):
    return datetime.combine(lunes, time(h, 0))


def test_crear_reserva_ok(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, duracion=60, precio=1500)
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    r = crear_reserva(neg.id, serv, rec, cli, _inicio(proximo_lunes))
    assert r.estado == EstadoReservaEnum.PENDIENTE_PAGO
    assert r.precio == 1500  # snapshot
    assert r.codigo


def test_anti_doble_reserva(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, capacidad=1)
    serv = crear_servicio(neg, rec)
    c1 = obtener_o_crear_cliente(neg.id, "A", email="a@test.com")
    crear_reserva(neg.id, serv, rec, c1, _inicio(proximo_lunes))
    c2 = obtener_o_crear_cliente(neg.id, "B", email="b@test.com")
    with pytest.raises(ReservaError):
        crear_reserva(neg.id, serv, rec, c2, _inicio(proximo_lunes))


def test_capacidad_multiple(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, capacidad=2)
    serv = crear_servicio(neg, rec)
    for i, email in enumerate(["a@t.com", "b@t.com"]):
        cli = obtener_o_crear_cliente(neg.id, f"C{i}", email=email)
        crear_reserva(neg.id, serv, rec, cli, _inicio(proximo_lunes))  # 2 cupos OK
    c3 = obtener_o_crear_cliente(neg.id, "C3", email="c@t.com")
    with pytest.raises(ReservaError):
        crear_reserva(neg.id, serv, rec, c3, _inicio(proximo_lunes))  # 3ro falla


def test_transiciones_estado(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    cli = obtener_o_crear_cliente(neg.id, "A", email="a@test.com")
    r = crear_reserva(neg.id, serv, rec, cli, _inicio(proximo_lunes),
                      estado=EstadoReservaEnum.CONFIRMADO)
    cambiar_estado(r, EstadoReservaEnum.EN_PROCESO)
    cambiar_estado(r, EstadoReservaEnum.FINALIZADO)
    assert r.estado == EstadoReservaEnum.FINALIZADO
    with pytest.raises(ReservaError):
        cambiar_estado(r, EstadoReservaEnum.CONFIRMADO)  # no se puede des-finalizar


def test_recurso_no_presta_servicio(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec1 = crear_recurso(neg)
    rec2 = crear_recurso(neg)
    serv = crear_servicio(neg, rec1)  # solo rec1 presta serv
    cli = obtener_o_crear_cliente(neg.id, "A", email="a@test.com")
    with pytest.raises(ReservaError):
        crear_reserva(neg.id, serv, rec2, cli, _inicio(proximo_lunes))
