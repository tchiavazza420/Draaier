"""
app/planes.py
-------------
Catálogo de planes comerciales (del brief). Define qué incluye cada plan.

El cobro real va por el módulo de pagos/suscripciones; acá solo describimos
los planes y sus features para mostrarlos y permitir elegir/cambiar.
"""

from app.models.negocio import PlanEnum

# grupo: "Independiente" (1 agenda) o "Locales" (varios recursos/staff)
PLANES = {
    PlanEnum.BASICO.value: {
        "nombre": "Básico", "grupo": "Independiente", "precio": 0,
        "resumen": "Para arrancar. 14 días gratis.",
        "features": [
            "1 reservable (vos)", "Reservas online ilimitadas",
            "Página pública propia", "Recordatorios por email",
        ],
        "no": ["Cobro de señas", "WhatsApp", "Reportes", "Marketplace"],
    },
    PlanEnum.PRO.value: {
        "nombre": "Pro", "grupo": "Independiente", "precio": 8000,
        "resumen": "Para profesionales que cobran señas.",
        "features": [
            "Hasta 3 reservables", "Cobro de señas (Mercado Pago/Naranja/Modo)",
            "Recordatorios por email y WhatsApp", "Reportes e ingresos",
            "Personalización de tu página",
        ],
        "no": ["Marketplace destacado", "Multi-staff"],
    },
    PlanEnum.PREMIUM.value: {
        "nombre": "Premium", "grupo": "Independiente", "precio": 14000,
        "resumen": "Todo, con presencia en el marketplace.",
        "features": [
            "Reservables ilimitados", "Todo lo de Pro",
            "Aparición destacada en el Marketplace", "Reseñas y reputación",
            "Soporte prioritario",
        ],
        "no": [],
    },
    PlanEnum.STARTER.value: {
        "nombre": "Starter", "grupo": "Locales", "precio": 12000,
        "resumen": "Para locales chicos con equipo.",
        "features": [
            "Hasta 5 reservables", "Multi-staff (varios usuarios)",
            "Cobro de señas", "Recordatorios email y WhatsApp", "Reportes",
        ],
        "no": ["Marketplace destacado"],
    },
    PlanEnum.BUSINESS.value: {
        "nombre": "Business", "grupo": "Locales", "precio": 22000,
        "resumen": "Para locales en crecimiento.",
        "features": [
            "Hasta 15 reservables", "Todo lo de Starter",
            "Marketplace destacado", "Personalización avanzada",
        ],
        "no": [],
    },
    PlanEnum.ENTERPRISE.value: {
        "nombre": "Enterprise", "grupo": "Locales", "precio": 40000,
        "resumen": "Para cadenas y alto volumen.",
        "features": [
            "Reservables y staff ilimitados", "Todo lo de Business",
            "Soporte dedicado", "Integraciones a medida",
        ],
        "no": [],
    },
}

ORDEN = [
    PlanEnum.BASICO.value, PlanEnum.PRO.value, PlanEnum.PREMIUM.value,
    PlanEnum.STARTER.value, PlanEnum.BUSINESS.value, PlanEnum.ENTERPRISE.value,
]


def info_plan(plan_enum):
    """Devuelve el dict de info de un PlanEnum (o None)."""
    if plan_enum is None:
        return None
    return PLANES.get(plan_enum.value)
