"""
app/resenas/service.py
----------------------
Lógica de reseñas: elegibilidad, creación y cálculo de rating.
"""

from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models.resena import Resena
from app.models.reserva import EstadoReservaEnum


class ResenaError(Exception):
    """Error de dominio al reseñar."""


def puede_resenar(reserva):
    """
    True si la reserva es elegible para reseña: debe estar FINALIZADA y no
    tener ya una reseña. (Finalizada implica que pasó por confirmada/pagada.)
    """
    if reserva.estado != EstadoReservaEnum.FINALIZADO:
        return False
    existe = Resena.query.filter_by(reserva_id=reserva.id).first()
    return existe is None


def crear_resena(reserva, calificacion, comentario=None):
    """Crea la reseña validando elegibilidad y rango de calificación."""
    if not puede_resenar(reserva):
        raise ResenaError("Esta reserva no puede reseñarse (debe estar finalizada y sin reseña previa).")
    if calificacion < 1 or calificacion > 5:
        raise ResenaError("La calificación debe estar entre 1 y 5.")

    resena = Resena(
        negocio_id=reserva.negocio_id,
        cliente_id=reserva.cliente_id,
        reserva_id=reserva.id,
        calificacion=calificacion,
        comentario=(comentario or "").strip() or None,
    )
    db.session.add(resena)
    db.session.commit()
    return resena


def responder_resena(resena, texto):
    """El negocio responde una reseña (no puede ocultarla)."""
    resena.respuesta = (texto or "").strip() or None
    resena.respondida_at = datetime.now() if resena.respuesta else None
    db.session.commit()
    return resena


def rating_negocio(negocio_id):
    """Devuelve (promedio_float_o_None, cantidad) de reseñas visibles."""
    promedio, cantidad = (
        db.session.query(func.avg(Resena.calificacion), func.count(Resena.id))
        .filter(Resena.negocio_id == negocio_id, Resena.oculta.is_(False))
        .one()
    )
    return (round(float(promedio), 1) if promedio is not None else None, int(cantidad))
