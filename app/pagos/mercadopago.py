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


def esta_configurado():
    """True si hay access token de Mercado Pago."""
    return bool(current_app.config.get("MERCADOPAGO_ACCESS_TOKEN"))


def _headers():
    token = current_app.config["MERCADOPAGO_ACCESS_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def crear_preferencia(pago, titulo, back_url_base, notification_url):
    """
    Crea una preferencia de Checkout Pro y devuelve (preference_id, init_point).
    Lanza requests.HTTPError si la API responde error.
    """
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
        json=body, headers=_headers(), timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("id"), data.get("init_point")


def obtener_pago(payment_id):
    """
    Consulta el estado de un pago en Mercado Pago.
    Devuelve dict con al menos {status, external_reference}.
    """
    resp = requests.get(
        f"{API_BASE}/v1/payments/{payment_id}",
        headers=_headers(), timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
