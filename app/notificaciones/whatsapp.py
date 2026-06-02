"""
app/notificaciones/whatsapp.py
------------------------------
Envío de mensajes por WhatsApp Cloud API (Meta).

Si no hay WHATSAPP_TOKEN + WHATSAPP_PHONE_ID configurados, los mensajes van a
BANDEJA_WA (bandeja de desarrollo, testeable) y se loguean, sin fallar. Con
credenciales, se envían por la API real de WhatsApp.
"""

import re

import requests
from flask import current_app

# Bandeja de desarrollo: lista de dicts {to, body}. Útil en tests.
BANDEJA_WA = []

TIMEOUT = 15


def esta_configurado():
    cfg = current_app.config
    return bool(cfg.get("WHATSAPP_TOKEN") and cfg.get("WHATSAPP_PHONE_ID"))


def _normalizar(telefono):
    """Deja solo dígitos (formato internacional que espera WhatsApp)."""
    return re.sub(r"\D", "", telefono or "")


def enviar_whatsapp(telefono, texto):
    """
    Envía un mensaje de texto por WhatsApp. Si no hay teléfono, no hace nada.
    Devuelve True si se envió (o se registró en la bandeja dev).
    """
    numero = _normalizar(telefono)
    if not numero:
        return False

    if not esta_configurado():
        BANDEJA_WA.append({"to": numero, "body": texto})
        current_app.logger.info("[WHATSAPP-DEV] Para %s: %s", numero, texto[:60])
        return True

    cfg = current_app.config
    url = f"https://graph.facebook.com/{cfg['WHATSAPP_API_VERSION']}/{cfg['WHATSAPP_PHONE_ID']}/messages"
    headers = {"Authorization": f"Bearer {cfg['WHATSAPP_TOKEN']}", "Content-Type": "application/json"}
    body = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto},
    }
    resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return True
