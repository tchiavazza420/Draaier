"""
app/pagos/modo.py
-----------------
Adaptador de pasarela MODO (misma interfaz que mercadopago.py).

Sin MODO_ACCESS_TOKEN, esta_configurado() devuelve False y el flujo cae a
modo simulación. Con token, haría las llamadas reales a la API de MODO.
"""

import requests
from flask import current_app

API_BASE = "https://merchants.preprod.modo.com.ar"  # ajustar a prod/credenciales
TIMEOUT = 15


def esta_configurado():
    return bool(current_app.config.get("MODO_ACCESS_TOKEN"))


def _headers():
    token = current_app.config["MODO_ACCESS_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def crear_preferencia(pago, titulo, back_url_base, notification_url):
    """Crea la intención de pago y devuelve (referencia, url_checkout)."""
    body = {
        "price": float(pago.monto),
        "currency": "ARS",
        "description": titulo,
        "external_intention_id": str(pago.id),
        "return_url": back_url_base,
        "webhook_url": notification_url,
    }
    resp = requests.post(f"{API_BASE}/payment-intention", json=body, headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("id"), data.get("qr") or data.get("checkout_url")


def obtener_pago(payment_id):
    resp = requests.get(f"{API_BASE}/payment-intention/{payment_id}", headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
