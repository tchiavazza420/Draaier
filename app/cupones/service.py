"""
app/cupones/service.py
----------------------
Lógica de cupones / gift cards de descuento.

- generar_codigo: código corto único por negocio.
- cupon_vigente_para: dado el código guardado en la sesión, devuelve el cupón
  si sigue vigente y aplica al servicio que se está reservando.
- La clave de sesión es por negocio: session['promo'] = {'neg': id, 'codigo': X}.
"""

import secrets
import string

from flask import session

from app.extensions import db
from app.models.cupon import Cupon

_ALFABETO = string.ascii_uppercase + string.digits
_SESSION_KEY = "promo"


def generar_codigo(negocio_id, largo=6):
    """Código corto único dentro del negocio (ej. 'A1B2C3')."""
    for _ in range(20):
        codigo = "".join(secrets.choice(_ALFABETO) for _ in range(largo))
        existe = Cupon.query.filter_by(negocio_id=negocio_id, codigo=codigo).first()
        if existe is None:
            return codigo
    return "".join(secrets.choice(_ALFABETO) for _ in range(largo + 2))


def buscar(negocio_id, codigo):
    if not codigo:
        return None
    return Cupon.query.filter_by(
        negocio_id=negocio_id, codigo=(codigo or "").strip().upper()).first()


def guardar_en_sesion(negocio_id, codigo):
    session[_SESSION_KEY] = {"neg": negocio_id, "codigo": codigo}


def limpiar_sesion():
    session.pop(_SESSION_KEY, None)


def cupon_de_sesion(negocio_id):
    """Devuelve el cupón guardado en sesión para este negocio (o None)."""
    data = session.get(_SESSION_KEY)
    if not data or data.get("neg") != negocio_id:
        return None
    return buscar(negocio_id, data.get("codigo"))


def cupon_vigente_para(negocio_id, servicio):
    """Cupón de la sesión si está vigente y aplica al servicio dado."""
    c = cupon_de_sesion(negocio_id)
    if c and c.vigente and c.aplica_a(servicio):
        return c
    return None


def registrar_uso(cupon):
    cupon.usos = (cupon.usos or 0) + 1
    db.session.commit()
