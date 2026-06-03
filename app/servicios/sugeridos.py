"""
app/servicios/sugeridos.py
--------------------------
Catálogo de servicios típicos por rubro, para el onboarding accionable.

Cuando un salón recién arranca, en vez de mandarlo a un formulario vacío le
ofrecemos servicios habituales de su rubro (con duración y precio sugeridos,
editables) para crearlos de a varios con un clic.

Los precios son orientativos en ARS; el dueño los ajusta antes de crear.
"""

from app.models.negocio import RubroEnum

# Cada item: (nombre, duración en minutos, precio sugerido)
_SUGERENCIAS = {
    RubroEnum.PELUQUERIA: [
        ("Corte de pelo", 45, 6000),
        ("Corte + Brushing", 60, 9000),
        ("Brushing", 40, 5000),
        ("Coloración", 120, 18000),
        ("Mechas / Balayage", 180, 30000),
        ("Tratamiento de nutrición", 60, 12000),
    ],
    RubroEnum.BARBERIA: [
        ("Corte", 30, 5000),
        ("Barba", 20, 3500),
        ("Corte + Barba", 45, 7500),
        ("Perfilado de cejas", 15, 2000),
        ("Corte niño", 30, 4000),
    ],
    RubroEnum.MANICURA: [
        ("Esmaltado tradicional", 40, 4000),
        ("Esmaltado semipermanente", 60, 6500),
        ("Kapping", 75, 8000),
        ("Soft Gel / Esculpidas", 90, 11000),
        ("Manicura + Pedicura", 90, 10000),
    ],
    RubroEnum.LASHISTA: [
        ("Lifting de pestañas", 60, 9000),
        ("Extensiones pelo a pelo", 120, 15000),
        ("Volumen ruso", 150, 20000),
        ("Perfilado y laminado de cejas", 45, 7000),
    ],
    RubroEnum.ESTETICA: [
        ("Limpieza facial profunda", 60, 10000),
        ("Depilación (sesión)", 30, 8000),
        ("Masaje descontracturante", 60, 12000),
        ("Tratamiento corporal", 75, 14000),
    ],
    RubroEnum.SPA: [
        ("Masaje relajante", 60, 13000),
        ("Circuito de spa", 120, 20000),
        ("Masaje con piedras calientes", 75, 16000),
        ("Facial hidratante", 50, 11000),
    ],
}

# Para rubros sin lista propia: opciones genéricas de belleza.
_GENERICO = [
    ("Turno estándar", 45, 6000),
    ("Turno extendido", 90, 12000),
    ("Consulta", 30, 4000),
]


def sugerencias_para(rubro):
    """Lista de dicts {nombre, duracion, precio} sugeridos para el rubro."""
    items = _SUGERENCIAS.get(rubro, _GENERICO)
    return [{"nombre": n, "duracion": d, "precio": p} for (n, d, p) in items]
