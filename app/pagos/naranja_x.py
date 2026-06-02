"""
app/pagos/naranja_x.py
----------------------
Adaptador de pasarela Naranja X (misma interfaz que mercadopago.py).

Sin NARANJA_X_ACCESS_TOKEN, esta_configurado() devuelve False y el flujo de
pagos cae a modo simulación (checkout interno). Con token, haría las llamadas
reales a la API de Naranja X (endpoints sujetos a credenciales del comercio).
"""

import requests
from flask import current_app

API_BASE = "https://api.naranjax.com"  # ajustar al endpoint real del comercio
TIMEOUT = 15


def esta_configurado():
    return bool(current_app.config.get("NARANJA_X_ACCESS_TOKEN"))


def _headers():
    token = current_app.config["NARANJA_X_ACCESS_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def crear_preferencia(pago, titulo, back_url_base, notification_url):
    """Crea la orden de pago y devuelve (referencia, url_checkout)."""
    body = {
        "amount": float(pago.monto),
        "currency": "ARS",
        "description": titulo,
        "external_reference": str(pago.id),
        "callback_url": back_url_base,
        "notification_url": notification_url,
    }
    resp = requests.post(f"{API_BASE}/checkout", json=body, headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("id"), data.get("checkout_url")


def obtener_pago(payment_id):
    resp = requests.get(f"{API_BASE}/payments/{payment_id}", headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
