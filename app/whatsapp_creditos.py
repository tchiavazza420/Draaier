"""
app/whatsapp_creditos.py
------------------------
Gestión de créditos de mensajes de WhatsApp por negocio.

Modelo: cada plan incluye N mensajes por mes (None = ilimitado). Además el
negocio puede comprar packs extra. TODO se renueva cada mes: al cambiar de
mes se reinician los usados y los comprados.

Disponible = (incluidos + extra_comprados) - usados   [o ilimitado].
"""

from datetime import datetime

from app.extensions import db
from app.planes import wa_incluidos_para


def _periodo_actual():
    return datetime.now().strftime("%Y-%m")


def _wa_incluidos(negocio):
    """
    Mensajes incluidos por mes del negocio. En planes por puesto (Locales)
    depende de cuántos profesionales tenga cargados; en los fijos es constante.
    """
    from app.models.recurso import Recurso
    n_prof = Recurso.query.filter_by(negocio_id=negocio.id).count()
    return wa_incluidos_para(negocio.plan, n_prof)


def _renovar_si_corresponde(negocio):
    """Reinicia usados y comprados si cambió el mes. No commitea."""
    actual = _periodo_actual()
    if negocio.wa_periodo != actual:
        negocio.wa_periodo = actual
        negocio.wa_usados = 0
        negocio.wa_extra = 0
        return True
    return False


def es_ilimitado(negocio):
    return _wa_incluidos(negocio) is None


def estado(negocio):
    """
    Devuelve un dict con el estado de créditos del mes actual:
    {incluidos, extra, usados, disponibles, ilimitado}.
    """
    cambio = _renovar_si_corresponde(negocio)
    if cambio:
        db.session.commit()

    incluidos = _wa_incluidos(negocio)
    if incluidos is None:
        return {"incluidos": None, "extra": negocio.wa_extra,
                "usados": negocio.wa_usados, "disponibles": None, "ilimitado": True}
    disponibles = max(0, incluidos + negocio.wa_extra - negocio.wa_usados)
    return {"incluidos": incluidos, "extra": negocio.wa_extra,
            "usados": negocio.wa_usados, "disponibles": disponibles, "ilimitado": False}


def hay_saldo(negocio):
    st = estado(negocio)
    return st["ilimitado"] or st["disponibles"] > 0


def consumir(negocio):
    """
    Descuenta un mensaje si hay saldo. Devuelve True si se pudo (hay que
    enviar), False si no hay saldo. Commitea el contador.
    """
    _renovar_si_corresponde(negocio)
    if not es_ilimitado(negocio):
        incluidos = _wa_incluidos(negocio)
        if (incluidos + negocio.wa_extra - negocio.wa_usados) <= 0:
            db.session.commit()
            return False
    negocio.wa_usados += 1
    db.session.commit()
    return True


def comprar_pack(negocio, cantidad):
    """Agrega `cantidad` de mensajes comprados al saldo del mes."""
    _renovar_si_corresponde(negocio)
    negocio.wa_extra += int(cantidad)
    db.session.commit()
    return estado(negocio)
