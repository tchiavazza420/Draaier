"""
app/pagos/mercadopago.py
------------------------
Cliente fino de la API de Mercado Pago (Checkout Pro) sobre `requests`.

Si no hay MERCADOPAGO_ACCESS_TOKEN configurado, `esta_configurado()` devuelve
False y el módulo de pagos cae a MODO SIMULACIÓN (checkout interno), de modo
que todo el flujo es probable en desarrollo sin credenciales reales.
"""

import requests
from flask import current_app

API_BASE = "https://api.mercadopago.com"
TIMEOUT = 15


def token_plataforma():
    """Access token de la plataforma (para cobrar las suscripciones de planes)."""
    return current_app.config.get("MERCADOPAGO_ACCESS_TOKEN")


def esta_configurado(token=None):
    """True si hay access token (el dado, o el de la plataforma)."""
    return bool(token or token_plataforma())


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def crear_preferencia(pago, titulo, back_url_base, notification_url, token=None):
    """
    Crea una preferencia de Checkout Pro y devuelve (preference_id, init_point).
    `token`: access token a usar (el del negocio para señas, o la plataforma).
    Lanza requests.HTTPError si la API responde error.
    """
    token = token or token_plataforma()
    body = {
        "items": [{
            "title": titulo,
            "quantity": 1,
            "unit_price": float(pago.monto),
            "currency_id": "ARS",
        }],
        "external_reference": str(pago.id),
        "back_urls": {
            "success": f"{back_url_base}?estado=success",
            "failure": f"{back_url_base}?estado=failure",
            "pending": f"{back_url_base}?estado=pending",
        },
        "auto_return": "approved",
        "notification_url": notification_url,
    }
    resp = requests.post(
        f"{API_BASE}/checkout/preferences",
        json=body, headers=_headers(token), timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("id"), data.get("init_point")


def obtener_pago(payment_id, token=None):
    """
    Consulta el estado de un pago en Mercado Pago con el token dado.
    Devuelve dict con al menos {status, external_reference}.
    """
    token = token or token_plataforma()
    resp = requests.get(
        f"{API_BASE}/v1/payments/{payment_id}",
        headers=_headers(token), timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
