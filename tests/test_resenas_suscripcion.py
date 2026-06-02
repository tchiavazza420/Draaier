"""Tests de reseñas (elegibilidad) y enforcement de suscripción."""

from datetime import datetime, time, timezone, timedelta

import pytest

from app.extensions import db
from app.models.reserva import EstadoReservaEnum
from app.models.negocio import EstadoSuscripcionEnum
from app.reservas.service import crear_reserva, obtener_o_crear_cliente
from app.resenas.service import puede_resenar, crear_resena, rating_negocio, ResenaError


def _reserva(neg, rec, serv, lunes, estado=EstadoReservaEnum.CONFIRMADO):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    return crear_reserva(neg.id, serv, rec, cli, datetime.combine(lunes, time(9, 0)), estado=estado)


def test_solo_finalizada_es_reseñable(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes, estado=EstadoReservaEnum.CONFIRMADO)
    assert puede_resenar(r) is False
    r.estado = EstadoReservaEnum.FINALIZADO
    db.session.commit()
    assert puede_resenar(r) is True


def test_una_resena_por_reserva_y_rating(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes, estado=EstadoReservaEnum.FINALIZADO)
    crear_resena(r, 4, "Muy bueno")
    with pytest.raises(ResenaError):
        crear_resena(r, 5, "otra")  # doble reseña
    promedio, cantidad = rating_negocio(neg.id)
    assert promedio == 4.0 and cantidad == 1


def test_puede_operar_segun_vencimiento(crear_negocio):
    neg, _ = crear_negocio()
    ahora = datetime.now(timezone.utc)
    # Trial vigente
    neg.estado_suscripcion = EstadoSuscripcionEnum.TRIAL
    neg.trial_fin = ahora + timedelta(days=3)
    db.session.commit()
    assert neg.puede_operar is True
    # Trial expirado
    neg.trial_fin = ahora - timedelta(days=1)
    db.session.commit()
    assert neg.esta_vencido is True
    assert neg.puede_operar is False


def test_cli_vencer_suscripciones(app, crear_negocio):
    neg, _ = crear_negocio()
    neg.estado_suscripcion = EstadoSuscripcionEnum.TRIAL
    neg.trial_fin = datetime.now(timezone.utc) - timedelta(days=1)
    db.session.commit()
    runner = app.test_cli_runner()
    out = runner.invoke(args=["vencer-suscripciones"]).output
    assert "Suscripciones vencidas: 1" in out
    db.session.refresh(neg)
    assert neg.estado_suscripcion == EstadoSuscripcionEnum.VENCIDA
