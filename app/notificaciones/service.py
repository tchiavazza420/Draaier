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
from app.notificaciones.whatsapp import (
    enviar_whatsapp, enviar_whatsapp_template, esta_configurado as _wa_configurado,
)


def _negocio(reserva):
    return db.session.get(Negocio, reserva.negocio_id)


def _email(neg, *args, **kwargs):
    """Envía email solo si el negocio tiene el canal email activo."""
    if neg is None or neg.notif_canal_email:
        try:
            enviar_email(*args, **kwargs)
        except Exception:
            current_app.logger.exception("Fallo enviando email")


def _wa(reserva, negocio, texto, template=None):
    """
    Envía WhatsApp si el negocio lo activó, hay saldo y el cliente tiene tel.
    Si `template` (dict {name, params}) está dado y hay una plantilla
    configurada, envía como plantilla aprobada (para mensajes proactivos).
    """
    if negocio is not None and not negocio.notif_canal_whatsapp:
        return
    if not (reserva.cliente and reserva.cliente.telefono):
        return
    # Solo en producción (WhatsApp configurado) se consume crédito y se exige
    # saldo. En modo dev (bandeja) no se cobra ni limita.
    if negocio is not None and _wa_configurado():
        from app.whatsapp_creditos import consumir as _consumir_wa
        if not _consumir_wa(negocio):
            current_app.logger.info("Sin saldo de WhatsApp, no se envía %s", reserva.codigo)
            return
    try:
        if template and template.get("name"):
            enviar_whatsapp_template(
                reserva.cliente.telefono, template["name"], template.get("params", []))
        else:
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


def _avisar_negocio_nueva(reserva):
    """
    Avisa al NEGOCIO/profesional que entró un turno nuevo desde la página
    pública: email al negocio + WhatsApp (si tiene número y hay saldo) + push.
    No depende de los toggles de notificación al cliente.
    """
    neg = _negocio(reserva)
    if neg is None:
        return

    # 1) Email al negocio (siempre que tenga email).
    try:
        enviar_email(neg.email,
                     f"Nuevo turno · {reserva.servicio.nombre} ({reserva.inicio.strftime('%d/%m %H:%M')})",
                     "negocio_nueva_reserva", reserva=reserva, negocio=neg)
    except Exception:
        current_app.logger.exception("Fallo email aviso negocio")

    # 2) WhatsApp al negocio (a SU número), si está configurado y hay saldo.
    if neg.whatsapp and _wa_configurado():
        try:
            from app.whatsapp_creditos import consumir as _consumir_wa
            if _consumir_wa(neg):
                enviar_whatsapp(
                    neg.whatsapp,
                    f"📅 Nuevo turno: {_detalle(reserva)}. Cliente: {reserva.cliente.nombre}"
                    + (f" ({reserva.cliente.telefono})" if reserva.cliente.telefono else ""))
        except Exception:
            current_app.logger.exception("Fallo WhatsApp aviso negocio")

    # 3) Push al panel (si hay VAPID configurado y suscripciones).
    try:
        from app.notificaciones import push
        push.enviar_a_negocio(
            neg.id, "Nuevo turno 📅",
            f"{reserva.cliente.nombre} · {_detalle(reserva)}", url="/panel")
    except Exception:
        current_app.logger.exception("Fallo push aviso negocio")


def _enviar_reprogramada(reserva):
    """Avisa al cliente que su turno se movió a un nuevo horario."""
    neg = _negocio(reserva)
    _email(neg, reserva.cliente.email,
           f"Tu turno se reprogramó · {reserva.servicio.nombre}",
           "reserva_reprogramada", reserva=reserva, negocio=neg)
    _wa(reserva, neg, f"📅 Reprogramamos tu turno: {_detalle(reserva)}. Código {reserva.codigo}.")


def _enviar_cancelada(reserva, reembolsada=False):
    """Avisa al cliente que su turno se canceló (y si se devuelve la seña)."""
    neg = _negocio(reserva)
    extra = " Te devolvemos la seña." if reembolsada else ""
    _email(neg, reserva.cliente.email,
           f"Turno cancelado · {reserva.servicio.nombre}",
           "reserva_cancelada", reserva=reserva, negocio=neg, reembolsada=reembolsada)
    _wa(reserva, neg, f"❌ Tu turno fue cancelado: {_detalle(reserva)}.{extra}")
    # Avisar también al negocio que se liberó el turno (email + push).
    if neg is not None:
        try:
            enviar_email(neg.email,
                         f"Turno cancelado · {reserva.servicio.nombre} ({reserva.inicio.strftime('%d/%m %H:%M')})",
                         "negocio_turno_cancelado", reserva=reserva, negocio=neg,
                         reembolsada=reembolsada)
        except Exception:
            current_app.logger.exception("Fallo email cancelacion al negocio")
        try:
            from app.notificaciones import push
            push.enviar_a_negocio(
                neg.id, "Turno cancelado ❌",
                f"{reserva.cliente.nombre} · {_detalle(reserva)}", url="/panel")
        except Exception:
            current_app.logger.exception("Fallo push cancelacion al negocio")


def _enviar_pedido_resena(reserva):
    """Pide una reseña al cliente tras un turno finalizado (email + WhatsApp)."""
    from flask import url_for
    neg = _negocio(reserva)
    link = current_app.config.get("SITE_URL", "") + url_for(
        "publico.reserva_resena", slug=neg.slug, codigo=reserva.codigo)
    _email(neg, reserva.cliente.email,
           f"¿Cómo estuvo tu turno? · {reserva.servicio.nombre}",
           "pedido_resena", reserva=reserva, negocio=neg, url_resena=link)
    _wa(reserva, neg,
        f"🌟 ¿Cómo estuvo tu turno de {reserva.servicio.nombre}? "
        f"Dejanos tu reseña acá: {link}")


def _enviar_recordatorio(reserva):
    from flask import url_for
    neg = _negocio(reserva)
    if neg is not None and not neg.notif_recordatorio:
        return
    link_asistir = current_app.config.get("SITE_URL", "") + url_for(
        "publico.reserva_confirmar_asistencia", slug=neg.slug, codigo=reserva.codigo)
    _email(neg, reserva.cliente.email,
           f"Recordatorio de tu turno · {reserva.servicio.nombre}",
           "recordatorio", reserva=reserva, negocio=neg, url_asistir=link_asistir)
    # Si hay plantilla aprobada configurada, el recordatorio sale como template
    # (sirve fuera de la ventana de 24 h); si no, como texto plano.
    tpl_name = current_app.config.get("WHATSAPP_TEMPLATE_RECORDATORIO")
    template = None
    if tpl_name:
        template = {"name": tpl_name, "params": [
            reserva.cliente.nombre,
            reserva.servicio.nombre,
            reserva.inicio.strftime("%d/%m a las %H:%M"),
        ]}
    _wa(reserva, neg,
        f"⏰ Te recordamos tu turno: {_detalle(reserva)}. "
        f"Confirmá tu asistencia acá: {link_asistir}",
        template=template)


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


def notificar_negocio_nueva_reserva(reserva):
    """Avisa al negocio que entró un turno nuevo (email + WhatsApp + push)."""
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "negocio_nueva")


def notificar_reserva_reprogramada(reserva):
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "reprogramada")


def notificar_reserva_cancelada(reserva, reembolsada=False):
    from app.tasks import notificar_reserva
    notificar_reserva.delay(reserva.id, "cancelada_reembolso" if reembolsada else "cancelada")


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
        # Se envía si el cliente tiene al menos un canal de contacto
        # (email o teléfono para WhatsApp); cada canal respeta sus toggles.
        if r.cliente and (r.cliente.email or r.cliente.telefono):
            try:
                _enviar_recordatorio(r)
                enviados += 1
            except Exception:
                current_app.logger.exception("Fallo recordatorio reserva %s", r.codigo)
    return enviados


def pedir_resenas():
    """
    Pide reseña a los clientes de turnos FINALIZADOS a los que aún no se les
    pidió (resena_pedida=False) y que tienen un canal de contacto. Marca cada
    uno como pedido para no repetir. Devuelve la cantidad enviada.
    Pensado para correr a diario (cron).
    """
    from app.models.reserva import Reserva, EstadoReservaEnum

    pendientes = (
        Reserva.query
        .filter(Reserva.estado == EstadoReservaEnum.FINALIZADO)
        .filter(Reserva.resena_pedida.is_(False))
        .all()
    )
    enviados = 0
    for r in pendientes:
        if r.cliente and (r.cliente.email or r.cliente.telefono):
            try:
                _enviar_pedido_resena(r)
                enviados += 1
            except Exception:
                current_app.logger.exception("Fallo pedido de reseña reserva %s", r.codigo)
        r.resena_pedida = True
    db.session.commit()
    return enviados
