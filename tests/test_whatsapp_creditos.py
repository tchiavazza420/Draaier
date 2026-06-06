"""Tests de créditos de WhatsApp (saldo, consumo, compra, reset mensual)."""

from datetime import datetime, timezone, timedelta

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


def test_reset_mensual_no_borra_comprados(crear_negocio):
    """Al cambiar de mes se reinician los USADOS, pero los comprados (con
    vigencia de 30 días) se mantienen."""
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.PRO
    neg.wa_periodo = "2000-01"
    neg.wa_usados = 80
    neg.wa_extra = 200
    neg.wa_extra_vence = datetime.now(timezone.utc) + timedelta(days=10)  # aún vigente
    db.session.commit()

    st = estado(neg)   # detecta cambio de mes
    assert neg.wa_periodo == _periodo_actual()
    assert st["usados"] == 0          # los usados se reinician
    assert st["extra"] == 200         # los comprados siguen
    assert st["disponibles"] == 300   # 100 incluidos + 200 comprados


def test_pack_vence_a_los_30_dias(crear_negocio):
    """Los comprados se ponen en 0 cuando pasó su vigencia (30 días)."""
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.BASICO        # 0 incluidos
    comprar_pack(neg, 100)
    assert estado(neg)["extra"] == 100

    # Simulamos que el pack venció ayer.
    neg.wa_extra_vence = datetime.now(timezone.utc) - timedelta(days=1)
    db.session.commit()

    st = estado(neg)
    assert st["extra"] == 0 and st["disponibles"] == 0
