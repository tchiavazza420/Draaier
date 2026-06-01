"""
app/notificaciones/service.py
-----------------------------
Composición y envío de notificaciones de negocio (eventos de reservas).

Cada función es tolerante a fallos: si algo del envío falla, se loguea pero
NO se propaga, para no romper el flujo principal (una reserva válida no debe
fallar porque el email no salió).
"""

from flask import current_app

from app.models.negocio import Negocio
from app.extensions import db
from app.notificaciones.email import enviar_email


def _negocio(reserva):
    return db.session.get(Negocio, reserva.negocio_id)


def notificar_reserva_confirmada(reserva):
    """Email al cliente avisando que su reserva quedó confirmada."""
    try:
        enviar_email(
            reserva.cliente.email,
            f"Reserva confirmada · {reserva.servicio.nombre}",
            "reserva_confirmada",
            reserva=reserva, negocio=_negocio(reserva),
        )
    except Exception:
        current_app.logger.exception("Fallo al notificar reserva confirmada %s", reserva.codigo)


def notificar_reserva_pendiente(reserva, url_pago=None):
    """Email al cliente con el detalle de la reserva pendiente de pago."""
    try:
        enviar_email(
            reserva.cliente.email,
            f"Tu reserva está pendiente de pago · {reserva.servicio.nombre}",
            "reserva_pendiente",
            reserva=reserva, negocio=_negocio(reserva), url_pago=url_pago,
        )
    except Exception:
        current_app.logger.exception("Fallo al notificar reserva pendiente %s", reserva.codigo)


def notificar_recordatorio(reserva):
    """Email recordatorio previo al turno."""
    try:
        enviar_email(
            reserva.cliente.email,
            f"Recordatorio de tu turno · {reserva.servicio.nombre}",
            "recordatorio",
            reserva=reserva, negocio=_negocio(reserva),
        )
    except Exception:
        current_app.logger.exception("Fallo al enviar recordatorio %s", reserva.codigo)
