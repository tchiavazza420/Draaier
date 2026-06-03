"""Tests de créditos de WhatsApp (saldo, consumo, compra, reset mensual)."""

from datetime import datetime

from app.extensions import db
from app.models.negocio import PlanEnum
from app.whatsapp_creditos import estado, consumir, comprar_pack, _periodo_actual


def test_incluidos_por_plan_y_consumo(crear_negocio):
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.PRO          # Pro incluye 100/mes
    db.session.commit()

    st = estado(neg)
    assert st["incluidos"] == 100 and st["disponibles"] == 100 and not st["ilimitado"]

    assert consumir(neg) is True
    assert estado(neg)["usados"] == 1
    assert estado(neg)["disponibles"] == 99


def test_compra_pack_suma_saldo(crear_negocio):
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.BASICO       # Básico incluye 0
    db.session.commit()
    assert estado(neg)["disponibles"] == 0
    assert consumir(neg) is False    # sin saldo, no se puede

    comprar_pack(neg, 300)
    st = estado(neg)
    assert st["extra"] == 300 and st["disponibles"] == 300
    assert consumir(neg) is True
    assert estado(neg)["disponibles"] == 299


def test_incluidos_por_puesto_starter(crear_negocio, crear_recurso):
    """Starter incluye 100 WhatsApp por profesional/mes (mínimo prof_base=2)."""
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.STARTER
    db.session.commit()

    # Sin profesionales cargados: cuenta el mínimo del plan (2 puestos) => 200.
    assert estado(neg)["incluidos"] == 200

    # Con 3 profesionales: 100 x 3 = 300.
    crear_recurso(neg); crear_recurso(neg); crear_recurso(neg)
    assert estado(neg)["incluidos"] == 300


def test_reset_mensual(crear_negocio):
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.PRO
    # Simulamos que el saldo es de un mes anterior, con usados y comprados.
    neg.wa_periodo = "2000-01"
    neg.wa_usados = 80
    neg.wa_extra = 200
    db.session.commit()

    st = estado(neg)   # al consultar, detecta cambio de mes y reinicia
    assert neg.wa_periodo == _periodo_actual()
    assert st["usados"] == 0 and st["extra"] == 0
    assert st["disponibles"] == 100   # solo los incluidos del plan
