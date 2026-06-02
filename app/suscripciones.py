"""
app/suscripciones.py
--------------------
Rutinas de mantenimiento de suscripciones, reutilizadas por el CLI y por las
tareas programadas de Celery (DRY).
"""

from app.extensions import db
from app.models.negocio import Negocio, EstadoSuscripcionEnum


def vencer_suscripciones():
    """
    Marca como VENCIDA toda suscripción TRIAL/ACTIVA cuya vigencia ya pasó.
    Devuelve la cantidad de negocios afectados.
    """
    candidatos = Negocio.query.filter(
        Negocio.estado_suscripcion.in_([
            EstadoSuscripcionEnum.TRIAL, EstadoSuscripcionEnum.ACTIVA,
        ])
    ).all()
    vencidos = 0
    for neg in candidatos:
        if neg.esta_vencido:
            neg.estado_suscripcion = EstadoSuscripcionEnum.VENCIDA
            vencidos += 1
    db.session.commit()
    return vencidos
