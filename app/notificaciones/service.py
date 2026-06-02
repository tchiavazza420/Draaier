"""
app/notificaciones/service.py
-----------------------------
Notificaciones de negocio (eventos de reservas).

Diseño con Celery:
  - Los senders privados (_enviar_*) hacen el trabajo real (componer + enviar),
    tolerantes a fallos.
  - Las funciones públicas notificar_* DESPACHAN una tarea Celery por id de
    reserva. En modo eager (sin Redis) la tarea corre sincrónicamente; con
    Redis + worker, se procesa en segundo plano.
  - enviar_recordatorios() es un batch usado por el CLI y por Celery beat.
"""

from datetime import date, datetime, timedelta

from flask import current_app

from app.models.negocio import Negocio
from app.extensions import db
from app.notificaciones.email import enviar_email


def _negocio(reserva):
    return db.session.get(Negocio, reserva.negocio_id)


# ----------------------------------------------------------------------
#  Senders reales (corren dentro de la tarea / del worker)
# ----------------------------------------------------------------------
def _enviar_confirmada(reserva):
    try:
        enviar_email(reserva.cliente.email,
                     f"Reserva confirmada · {reserva.servicio.nombre}",
                     "reserva_confirmada", reserva=reserva, negocio=_negocio(reserva))
    except Exception:
        current_app.logger.exception("Fallo notificando confirmada %s", reserva.codigo)


def _enviar_pendiente(reserva, url_pago=None):
    try:
        enviar_email(reserva.cliente.email,
                     f"Tu reserva está pendiente de pago · {reserva.servicio.nombre}",
                     "reserva_pendiente", reserva=reserva, negocio=_negocio(reserva),
                     url_pago=url_pago)
    except Exception:
        current_app.logger.exception("Fallo notificando pendiente %s", reserva.codigo)


def _enviar_recordatorio(reserva):
    try:
        enviar_email(reserva.cliente.email,
                     f"Recordatorio de tu turno · {reserva.servicio.nombre}",
                     "recordatorio", reserva=reserva, negocio=_negocio(reserva))
    except Exception:
        current_app.logger.exception("Fallo enviando recordatorio %s", reserva.codigo)


# ----------------------------------------------------------------------
#  API pública: despacha tareas (async con Redis, sync en modo eager)
# ----------------------------------------------------------------------
def notificar_reserva_confirmada(reserva):
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "confirmada")


def notificar_reserva_pendiente(reserva, url_pago=None):
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "pendiente", url_pago)


def notificar_recordatorio(reserva):
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "recordatorio")


# ----------------------------------------------------------------------
#  Batch de recordatorios (CLI + Celery beat)
# ----------------------------------------------------------------------
def enviar_recordatorios(dias=1):
    """
    Envía recordatorios de las reservas confirmadas que ocurren dentro de
    `dias` días. Devuelve la cantidad enviada.
    """
    from app.models.reserva import Reserva, EstadoReservaEnum

    objetivo = date.today() + timedelta(days=dias)
    ini = datetime.combine(objetivo, datetime.min.time())
    fin = ini + timedelta(days=1)
    reservas = (
        Reserva.query
        .filter(Reserva.estado == EstadoReservaEnum.CONFIRMADO)
        .filter(Reserva.inicio >= ini, Reserva.inicio < fin)
        .all()
    )
    enviados = 0
    for r in reservas:
        if r.cliente and r.cliente.email:
            _enviar_recordatorio(r)
            enviados += 1
    return enviados
