"""
app/errors.py
-------------
Excepciones HTTP propias.

Werkzeug no trae registrada la 402 (Payment Required) en su aborter, así que
la definimos como HTTPException para poder usar `raise PagoRequerido()`.
La usamos cuando un negocio con suscripción vencida intenta operar.
"""

from werkzeug.exceptions import HTTPException


class PagoRequerido(HTTPException):
    code = 402
    description = (
        "La suscripción del negocio está vencida. "
        "Regularizá el pago para volver a operar."
    )
