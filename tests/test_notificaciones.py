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
