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


class WhatsAppError(Exception):
    """Error de la API de WhatsApp con el detalle real que devuelve Meta."""


def _post(body):
    """
    Hace el POST a la API de Meta y, ante un error HTTP, registra y devuelve el
    cuerpo del error (que explica la causa: ventana de 24 h, plantilla con
    parámetros que no coinciden, número no habilitado, token vencido, etc.).
    Devuelve (ok: bool, detalle: str).
    """
    cfg = current_app.config
    url = f"https://graph.facebook.com/{cfg['WHATSAPP_API_VERSION']}/{cfg['WHATSAPP_PHONE_ID']}/messages"
    headers = {"Authorization": f"Bearer {cfg['WHATSAPP_TOKEN']}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        current_app.logger.error("[WHATSAPP] Fallo de red: %s", exc)
        return False, f"Fallo de red: {exc}"

    if resp.status_code >= 400:
        # El cuerpo de Meta trae error.code + error.message + error_data.details.
        try:
            err = resp.json().get("error", {})
            detalle = f"({err.get('code')}) {err.get('message')}"
            sub = (err.get("error_data") or {}).get("details")
            if sub:
                detalle += f" — {sub}"
        except Exception:
            detalle = resp.text[:300]
        current_app.logger.error(
            "[WHATSAPP] Meta rechazó el envío (HTTP %s): %s", resp.status_code, detalle)
        return False, detalle
    return True, "ok"


def enviar_whatsapp(telefono, texto):
    """
    Envía un mensaje de texto por WhatsApp. Si no hay teléfono, no hace nada.
    Devuelve True si se envió (o se registró en la bandeja dev).

    OJO: Meta solo entrega texto libre dentro de la ventana de 24 h (después de
    que el cliente te escribió). Para mensajes proactivos hay que usar
    enviar_whatsapp_template con una plantilla aprobada.
    """
    numero = _normalizar(telefono)
    if not numero:
        return False

    if not esta_configurado():
        BANDEJA_WA.append({"to": numero, "body": texto})
        current_app.logger.info("[WHATSAPP-DEV] Para %s: %s", numero, texto[:60])
        return True

    ok, detalle = _post({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto},
    })
    if not ok:
        raise WhatsAppError(detalle)
    return True


def enviar_whatsapp_template(telefono, template_name, parametros, idioma=None):
    """
    Envía un mensaje de PLANTILLA aprobada por Meta (para mensajes proactivos
    fuera de la ventana de 24 h). `parametros` son las variables del cuerpo
    (en orden). Si no hay credenciales, va a la bandeja de desarrollo.
    """
    numero = _normalizar(telefono)
    if not numero:
        return False
    cfg = current_app.config
    idioma = idioma or cfg.get("WHATSAPP_TEMPLATE_IDIOMA", "es_AR")

    if not esta_configurado():
        BANDEJA_WA.append({"to": numero, "body": f"[template:{template_name}] {parametros}"})
        current_app.logger.info("[WHATSAPP-DEV] Template %s para %s", template_name, numero)
        return True

    componentes = []
    if parametros:
        componentes.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in parametros],
        })
    ok, detalle = _post({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": idioma},
            "components": componentes,
        },
    })
    if not ok:
        raise WhatsAppError(detalle)
    return True
