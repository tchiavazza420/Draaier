"""
app/planes.py
-------------
Catálogo de planes comerciales de AgenPro.

Dos grupos:
  - Independiente (1 profesional, precio FIJO): básico / pro / premium.
  - Locales (precio POR PUESTO): starter / business.
      precio = precio_base (incluye `prof_base` profesionales)
               + precio_adicional por cada profesional extra, hasta `max_prof`.
      WhatsApp incluido = `wa_por_prof` mensajes por profesional contratado.

Todos son pagos; solo Básico tiene 14 días de prueba sin tarjeta.
Precios en ARS mensuales. El pago anual da 2 meses gratis (pagás 10 meses).
"""

from app.models.negocio import PlanEnum

# Meses que se cobran en el plan anual (2 gratis sobre 12).
MESES_ANUAL = 10
PRUEBA_DIAS = 14

# Packs de mensajes de WhatsApp extra (se pueden comprar en cualquier plan).
PACKS_WHATSAPP = [
    {"cantidad": 100, "precio": 8000},
    {"cantidad": 300, "precio": 22000},
    {"cantidad": 600, "precio": 40000},
    {"cantidad": 1000, "precio": 65000},
]


PLANES = {
    # ---------- Independiente (precio fijo, 1 profesional) ----------
    PlanEnum.BASICO.value: {
        "nombre": "Básico", "grupo": "Independiente", "tipo": "fijo",
        "precio": 9000, "max_prof": 1, "wa_incluido": 0,
        "prueba_dias": PRUEBA_DIAS,
        "resumen": "Para empezar. 14 días de prueba, sin tarjeta.",
        "features": [
            "1 profesional (vos)", "Reservas online ilimitadas",
            "Tu página pública propia", "Recordatorios por email",
        ],
        "no": ["Cobro de señas", "WhatsApp", "Reportes", "Marketplace"],
    },
    PlanEnum.PRO.value: {
        "nombre": "Pro", "grupo": "Independiente", "tipo": "fijo",
        "precio": 20000, "max_prof": 1, "wa_incluido": 100,
        "resumen": "Para profesionales que cobran señas.",
        "features": [
            "1 profesional (vos)", "Cobro de señas (Mercado Pago)",
            "Recordatorios por email y WhatsApp",
            "Reportes e ingresos", "Personalización de tu página",
        ],
        "no": ["Marketplace destacado", "Multi-staff"],
    },
    PlanEnum.PREMIUM.value: {
        "nombre": "Premium", "grupo": "Independiente", "tipo": "fijo",
        "precio": 45000, "max_prof": 1, "wa_incluido": 500,
        "resumen": "Todo, con presencia destacada en el marketplace.",
        "features": [
            "1 profesional (vos)", "Todo lo de Pro",
            "Página sin marca AgenPro (white-label)",
            "Aparición destacada en el Marketplace", "Reseñas y reputación",
            "Soporte prioritario",
        ],
        "no": ["Multi-staff"],
    },
    # ---------- Locales (precio por puesto) ----------
    PlanEnum.STARTER.value: {
        "nombre": "Starter", "grupo": "Locales", "tipo": "puesto",
        "precio_base": 45000, "prof_base": 2, "precio_adicional": 18000,
        "max_prof": 5, "wa_por_prof": 100,
        "resumen": "Para locales chicos con equipo. Pagás por profesional.",
        "features": [
            "Desde 2 profesionales (hasta 5)",
            "$18.000 por cada profesional adicional",
            "Multi-staff (varios usuarios)", "Cobro de señas",
            "Recordatorios por email y WhatsApp", "Reportes",
        ],
        "no": ["Marketplace destacado"],
    },
    PlanEnum.BUSINESS.value: {
        "nombre": "Business", "grupo": "Locales", "tipo": "puesto",
        "precio_base": 135000, "prof_base": 5, "precio_adicional": 25000,
        "max_prof": 15, "wa_por_prof": 300,
        "resumen": "Para locales en crecimiento. Pagás por profesional.",
        "features": [
            "Desde 5 profesionales (hasta 15)",
            "$25.000 por cada profesional adicional",
            "Todo lo de Starter",
            "Página sin marca AgenPro (white-label)",
            "Marketplace destacado", "Personalización avanzada",
        ],
        "no": [],
    },
}

# Orden de aparición en la página de planes (Enterprise fuera de catálogo).
ORDEN = [
    PlanEnum.BASICO.value, PlanEnum.PRO.value, PlanEnum.PREMIUM.value,
    PlanEnum.STARTER.value, PlanEnum.BUSINESS.value,
]


# ======================================================================
#  Helpers
# ======================================================================
def info_plan(plan_enum):
    """Devuelve el dict de info de un PlanEnum (o None)."""
    if plan_enum is None:
        return None
    return PLANES.get(plan_enum.value)


def es_por_puesto(plan):
    """True si el plan cobra por puesto (Locales)."""
    return plan.get("tipo") == "puesto"


def precio_desde(plan):
    """Precio mensual de referencia (mínimo): fijo => precio; puesto => base."""
    return plan["precio_base"] if es_por_puesto(plan) else plan["precio"]


def precio_para(plan, n_prof):
    """
    Precio mensual para `n_prof` profesionales.
    - Fijo: siempre el precio del plan.
    - Puesto: base + adicional por cada profesional por encima de prof_base,
      acotado entre prof_base y max_prof.
    """
    if not es_por_puesto(plan):
        return plan["precio"]
    seats = max(plan["prof_base"], min(n_prof, plan["max_prof"]))
    extra = seats - plan["prof_base"]
    return plan["precio_base"] + extra * plan["precio_adicional"]


def precio_anual(plan):
    """Precio anual (con 2 meses gratis) sobre el precio de referencia."""
    return precio_desde(plan) * MESES_ANUAL


def max_prof_de(plan_enum):
    """Máximo de profesionales/agendas del plan. Sin plan: 1."""
    plan = info_plan(plan_enum)
    return plan["max_prof"] if plan else 1


# Alias histórico usado por el módulo de recursos (límite de agendas).
def limite_agendas_de(plan_enum):
    """Máximo de agendas (= profesionales) según el plan. Sin plan: 1."""
    return max_prof_de(plan_enum)


def wa_incluidos_para(plan_enum, n_prof):
    """
    Mensajes de WhatsApp incluidos por mes según el plan y la cantidad de
    profesionales contratados.
    - Fijo: el valor fijo del plan.
    - Puesto: wa_por_prof × profesionales (mínimo prof_base, máximo max_prof).
    """
    plan = info_plan(plan_enum)
    if plan is None:
        return 0
    if not es_por_puesto(plan):
        return plan.get("wa_incluido", 0)
    seats = max(plan["prof_base"], min(n_prof or 0, plan["max_prof"]))
    return plan["wa_por_prof"] * seats


def wa_incluidos_catalogo(plan_enum):
    """
    Valor de WhatsApp para mostrar en el catálogo (sin saber profesionales):
    - Fijo: el número fijo.
    - Puesto: el mínimo garantizado (wa_por_prof × prof_base).
    """
    plan = info_plan(plan_enum)
    if plan is None:
        return 0
    if not es_por_puesto(plan):
        return plan.get("wa_incluido", 0)
    return plan["wa_por_prof"] * plan["prof_base"]
