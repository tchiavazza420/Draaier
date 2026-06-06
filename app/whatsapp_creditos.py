"""
app/whatsapp_creditos.py
------------------------
Gestión de créditos de mensajes de WhatsApp por negocio.

Modelo: cada plan incluye N mensajes por mes (None = ilimitado). Además el
negocio puede comprar packs extra. TODO se renueva cada mes: al cambiar de
mes se reinician los usados y los comprados.

Disponible = (incluidos + extra_comprados) - usados   [o ilimitado].
"""

from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.planes import wa_incluidos_para

# Los packs comprados valen 30 días desde la compra.
DIAS_VIGENCIA_PACK = 30


def _periodo_actual():
    return datetime.now().strftime("%Y-%m")


def _expirar_extra_si_corresponde(negocio):
    """Si los mensajes comprados vencieron (30 días), los pone en 0. No commitea."""
    vence = negocio.wa_extra_vence
    if vence is None:
        return False
    if vence.tzinfo is None:
        vence = vence.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= vence:
        negocio.wa_extra = 0
        negocio.wa_extra_vence = None
        return True
    return False


def _wa_incluidos(negocio):
    """
    Mensajes incluidos por mes del negocio. En planes por puesto (Locales)
    depende de cuántos profesionales tenga cargados; en los fijos es constante.
    """
    from app.models.recurso import Recurso
    n_prof = Recurso.query.filter_by(negocio_id=negocio.id).count()
    return wa_incluidos_para(negocio.plan, n_prof)


def _renovar_si_corresponde(negocio):
    """
    Reinicia los mensajes USADOS al cambiar de mes (los incluidos del plan se
    renuevan mensualmente). Los comprados NO se tocan acá: vencen a los 30 días
    de la compra (ver _expirar_extra_si_corresponde). No commitea.
    """
    cambio = False
    actual = _periodo_actual()
    if negocio.wa_periodo != actual:
        negocio.wa_periodo = actual
        negocio.wa_usados = 0
        cambio = True
    if _expirar_extra_si_corresponde(negocio):
        cambio = True
    return cambio


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
                "usados": negocio.wa_usados, "disponibles": None, "ilimitado": True,
                "extra_vence": negocio.wa_extra_vence}
    disponibles = max(0, incluidos + negocio.wa_extra - negocio.wa_usados)
    return {"incluidos": incluidos, "extra": negocio.wa_extra,
            "usados": negocio.wa_usados, "disponibles": disponibles, "ilimitado": False,
            "extra_vence": negocio.wa_extra_vence}


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
    """
    Suma `cantidad` mensajes comprados, válidos por 30 días desde HOY.
    Comprar de nuevo extiende la vigencia (renueva los 30 días).
    """
    _renovar_si_corresponde(negocio)
    negocio.wa_extra += int(cantidad)
    negocio.wa_extra_vence = datetime.now(timezone.utc) + timedelta(days=DIAS_VIGENCIA_PACK)
    db.session.commit()
    return estado(negocio)
