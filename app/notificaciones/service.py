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
from app.notificaciones.whatsapp import enviar_whatsapp


def _negocio(reserva):
    return db.session.get(Negocio, reserva.negocio_id)


def _email(neg, *args, **kwargs):
    """Envía email solo si el negocio tiene el canal email activo."""
    if neg is None or neg.notif_canal_email:
        try:
            enviar_email(*args, **kwargs)
        except Exception:
            current_app.logger.exception("Fallo enviando email")


def _wa(reserva, negocio, texto):
    """Envía WhatsApp si el negocio lo activó y el cliente tiene teléfono."""
    if negocio is not None and not negocio.notif_canal_whatsapp:
        return
    try:
        if reserva.cliente and reserva.cliente.telefono:
            firma = (negocio.mensaje_firma if negocio and negocio.mensaje_firma else "")
            enviar_whatsapp(reserva.cliente.telefono, texto + (f"\n{firma}" if firma else ""))
    except Exception:
        current_app.logger.exception("Fallo enviando WhatsApp %s", reserva.codigo)


def _detalle(reserva):
    return (f"{reserva.servicio.nombre} el {reserva.inicio.strftime('%d/%m a las %H:%M')} "
            f"({reserva.recurso.nombre})")


# ----------------------------------------------------------------------
#  Senders reales (respetan los toggles de mensajes automáticos del negocio).
# ----------------------------------------------------------------------
def _enviar_confirmada(reserva):
    neg = _negocio(reserva)
    if neg is not None and not neg.notif_confirmacion:
        return
    _email(neg, reserva.cliente.email,
           f"Reserva confirmada · {reserva.servicio.nombre}",
           "reserva_confirmada", reserva=reserva, negocio=neg)
    _wa(reserva, neg, f"✅ ¡Reserva confirmada! {_detalle(reserva)}. Código {reserva.codigo}.")


def _enviar_pendiente(reserva, url_pago=None):
    neg = _negocio(reserva)
    _email(neg, reserva.cliente.email,
           f"Tu reserva está pendiente de pago · {reserva.servicio.nombre}",
           "reserva_pendiente", reserva=reserva, negocio=neg, url_pago=url_pago)
    msg = f"⏳ Reservá tu turno: {_detalle(reserva)}."
    if url_pago:
        msg += f" Pagá la seña acá: {url_pago}"
    _wa(reserva, neg, msg)


def _enviar_recordatorio(reserva):
    neg = _negocio(reserva)
    if neg is not None and not neg.notif_recordatorio:
        return
    _email(neg, reserva.cliente.email,
           f"Recordatorio de tu turno · {reserva.servicio.nombre}",
           "recordatorio", reserva=reserva, negocio=neg)
    _wa(reserva, neg, f"⏰ Te recordamos tu turno: {_detalle(reserva)}. ¡Te esperamos!")


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
