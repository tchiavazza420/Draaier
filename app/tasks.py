"""
app/tasks.py
------------
Tareas Celery. Reciben ids (serializables), recargan los objetos y delegan en
la lógica de dominio. Se registran como shared_task (ligadas a la instancia
Celery por defecto creada en make_celery()).

En modo eager (sin Redis) `.delay()` ejecuta estas tareas sincrónicamente.
"""

from celery import shared_task


@shared_task(name="tareas.notificar_reserva", ignore_result=True)
def notificar_reserva(reserva_id, tipo, url_pago=None):
    """Envía la notificación por email correspondiente a una reserva."""
    from app.extensions import db
    from app.models.reserva import Reserva
    from app.notificaciones import service

    reserva = db.session.get(Reserva, reserva_id)
    if reserva is None:
        return
    if tipo == "confirmada":
        service._enviar_confirmada(reserva)
    elif tipo == "pendiente":
        service._enviar_pendiente(reserva, url_pago)
    elif tipo == "recordatorio":
        service._enviar_recordatorio(reserva)


@shared_task(name="tareas.recordatorios")
def recordatorios(dias=1):
    """Batch de recordatorios para las reservas a `dias` de distancia."""
    from app.notificaciones.service import enviar_recordatorios
    return enviar_recordatorios(dias)


@shared_task(name="tareas.vencer_suscripciones")
def vencer_suscripciones():
    """Marca como vencidas las suscripciones expiradas."""
    from app.suscripciones import vencer_suscripciones as _vencer
    return _vencer()
