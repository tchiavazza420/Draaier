"""
app/planes.py
-------------
Catálogo de planes comerciales de Draaier.

Estructura: dos grupos (Independiente / Locales), 3 planes cada uno.
Todos son pagos; solo Básico tiene 14 días de prueba sin tarjeta.
Precios en ARS mensuales. El pago anual da 2 meses gratis (pagás 10 meses).
"""

from app.models.negocio import PlanEnum

# Meses que se cobran en el plan anual (2 gratis sobre 12).
MESES_ANUAL = 10
PRUEBA_DIAS = 14

# Packs de mensajes de WhatsApp extra (se pueden comprar en cualquier plan).
# Precio: $2.500 cada 100 mensajes. Se usan/renuevan dentro del mes.
PACKS_WHATSAPP = [
    {"cantidad": 100, "precio": 2500},
    {"cantidad": 300, "precio": 7500},
    {"cantidad": 600, "precio": 15000},
    {"cantidad": 1000, "precio": 25000},
]

# Mensajes de WhatsApp incluidos por plan, por mes (None = ilimitado).
WA_INCLUIDOS = {
    PlanEnum.BASICO.value: 0,
    PlanEnum.PRO.value: 100,
    PlanEnum.PREMIUM.value: 500,
    PlanEnum.STARTER.value: 200,
    PlanEnum.BUSINESS.value: 600,
    PlanEnum.ENTERPRISE.value: None,   # ilimitado
}


def wa_incluidos_de(plan_enum):
    """Mensajes de WhatsApp incluidos por mes según el plan (None=ilimitado)."""
    if plan_enum is None:
        return 0
    return WA_INCLUIDOS.get(plan_enum.value, 0)


# Máximo de agendas (reservables) por plan (None = ilimitado).
# Independiente = 1 agenda (para una sola persona). Locales = varias.
LIMITE_AGENDAS = {
    PlanEnum.BASICO.value: 1,
    PlanEnum.PRO.value: 1,
    PlanEnum.PREMIUM.value: 1,
    PlanEnum.STARTER.value: 5,
    PlanEnum.BUSINESS.value: 15,
    PlanEnum.ENTERPRISE.value: None,   # ilimitado
}


def limite_agendas_de(plan_enum):
    """Máximo de agendas según el plan (None = ilimitado). Sin plan: 1."""
    if plan_enum is None:
        return 1
    return LIMITE_AGENDAS.get(plan_enum.value, 1)


PLANES = {
    PlanEnum.BASICO.value: {
        "nombre": "Básico", "grupo": "Independiente", "precio": 9000,
        "prueba_dias": PRUEBA_DIAS,
        "resumen": "Para empezar. 14 días de prueba, sin tarjeta.",
        "features": [
            "1 agenda (para vos)", "Reservas online ilimitadas",
            "Tu página pública propia", "Recordatorios por email",
        ],
        "no": ["Cobro de señas", "WhatsApp", "Reportes", "Marketplace"],
    },
    PlanEnum.PRO.value: {
        "nombre": "Pro", "grupo": "Independiente", "precio": 18000,
        "resumen": "Para profesionales que cobran señas.",
        "features": [
            "1 agenda (para vos)", "Cobro de señas (Mercado Pago / Naranja X / Modo)",
            "Recordatorios por email y WhatsApp", "Reportes e ingresos",
            "Personalización de tu página",
        ],
        "no": ["Marketplace destacado", "Multi-staff"],
    },
    PlanEnum.PREMIUM.value: {
        "nombre": "Premium", "grupo": "Independiente", "precio": 30000,
        "resumen": "Todo, con presencia destacada en el marketplace.",
        "features": [
            "1 agenda (para vos)", "Todo lo de Pro",
            "Aparición destacada en el Marketplace", "Reseñas y reputación",
            "Soporte prioritario",
        ],
        "no": ["Multi-staff"],
    },
    PlanEnum.STARTER.value: {
        "nombre": "Starter", "grupo": "Locales", "precio": 35000,
        "resumen": "Para locales chicos con equipo.",
        "features": [
            "Hasta 5 agendas", "Multi-staff (varios usuarios)",
            "Cobro de señas", "Recordatorios por email y WhatsApp", "Reportes",
        ],
        "no": ["Marketplace destacado"],
    },
    PlanEnum.BUSINESS.value: {
        "nombre": "Business", "grupo": "Locales", "precio": 55000,
        "resumen": "Para locales en crecimiento.",
        "features": [
            "Hasta 15 agendas", "Todo lo de Starter",
            "Marketplace destacado", "Personalización avanzada",
        ],
        "no": [],
    },
    PlanEnum.ENTERPRISE.value: {
        "nombre": "Enterprise", "grupo": "Locales", "precio": 95000,
        "desde": True,  # "Desde $95.000", escalable según necesidades
        "resumen": "Para cadenas y alto volumen. Escala con vos.",
        "features": [
            "Agendas y staff ilimitados", "Todo lo de Business",
            "Soporte dedicado", "Integraciones a medida",
        ],
        "no": [],
    },
}

ORDEN = [
    PlanEnum.BASICO.value, PlanEnum.PRO.value, PlanEnum.PREMIUM.value,
    PlanEnum.STARTER.value, PlanEnum.BUSINESS.value, PlanEnum.ENTERPRISE.value,
]


def precio_anual(plan):
    """Precio anual (con 2 meses gratis) a partir del dict de plan."""
    return plan["precio"] * MESES_ANUAL


def info_plan(plan_enum):
    """Devuelve el dict de info de un PlanEnum (o None)."""
    if plan_enum is None:
        return None
    return PLANES.get(plan_enum.value)
