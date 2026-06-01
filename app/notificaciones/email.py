"""
app/notificaciones/email.py
---------------------------
Capa de envío de emails.

Si hay MAIL_SERVER configurado, envía de verdad con Flask-Mail. Si no
(desarrollo), guarda el mensaje en BANDEJA_DEV y lo loguea, sin fallar.
Esto permite probar todo el flujo de notificaciones sin un SMTP real.

El envío es síncrono por ahora. Está preparado para moverse a Celery (cola
de tareas) cuando incorporemos Redis: bastará con envolver enviar_email en
una task y llamarla con .delay().
"""

from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail

# Bandeja de desarrollo: lista de dicts {to, subject, body}. Útil en tests.
BANDEJA_DEV = []


def _mail_configurado():
    return bool(current_app.config.get("MAIL_SERVER"))


def enviar_email(destinatario, asunto, template, **contexto):
    """
    Renderiza `emails/<template>.html` y .txt y envía el email.
    Si no hay destinatario, no hace nada (cliente sin email).
    """
    if not destinatario:
        return False

    html = render_template(f"emails/{template}.html", **contexto)
    try:
        texto = render_template(f"emails/{template}.txt", **contexto)
    except Exception:
        texto = None

    if not _mail_configurado():
        # Modo desarrollo: registrar en la bandeja y loguear.
        BANDEJA_DEV.append({"to": destinatario, "subject": asunto, "body": html})
        current_app.logger.info("[EMAIL-DEV] Para %s · %s", destinatario, asunto)
        return True

    msg = Message(subject=asunto, recipients=[destinatario])
    msg.html = html
    if texto:
        msg.body = texto
    mail.send(msg)
    return True
