"""
app/recursos/opciones.py
------------------------
Opciones de personalización de la página del profesional: fuentes (Google
Fonts) y estilos visuales. Se usan en el formulario (todas, para el preview en
vivo) y en la página pública (solo la elegida).

Todas las fuentes elegidas soportan los pesos 400/600/700 para que los títulos
se vean bien en negrita.
"""

# (familia, etiqueta para el selector, categoría)
FUENTES = [
    ("Plus Jakarta Sans", "Plus Jakarta — Moderna", "sans"),
    ("Poppins", "Poppins — Redondeada", "sans"),
    ("Montserrat", "Montserrat — Limpia", "sans"),
    ("Raleway", "Raleway — Fina y elegante", "sans"),
    ("Josefin Sans", "Josefin Sans — Geométrica", "sans"),
    ("Quicksand", "Quicksand — Suave", "sans"),
    ("Playfair Display", "Playfair — Serif elegante", "serif"),
    ("Cormorant Garamond", "Cormorant — Serif de lujo", "serif"),
    ("Lora", "Lora — Serif clásica", "serif"),
    ("Dancing Script", "Dancing Script — Manuscrita", "script"),
]

FUENTES_VALIDAS = {f[0] for f in FUENTES}
FUENTE_DEFAULT = "Plus Jakarta Sans"

# (valor, etiqueta) — estilo visual de la página (tema).
ESTILOS_PAGINA = [
    ("minimal", "Minimalista"),
    ("elegante", "Elegante"),
    ("moderno", "Moderno"),
    ("glam", "Glam"),
]
ESTILOS_VALIDOS = {e[0] for e in ESTILOS_PAGINA}

# Forma del avatar.
FORMAS_FOTO = [
    ("circulo", "Círculo"),
    ("rounded", "Cuadrado redondeado"),
    ("hexagono", "Hexágono"),
]
FORMAS_VALIDAS = {f[0] for f in FORMAS_FOTO}


def fuentes_css_url(familias):
    """
    Arma la URL de Google Fonts (CSS2) para una o varias familias.
    Ej: fuentes_css_url(["Poppins", "Lora"]).
    """
    if isinstance(familias, str):
        familias = [familias]
    partes = []
    for fam in familias:
        if fam in FUENTES_VALIDAS:
            partes.append("family=" + fam.replace(" ", "+") + ":wght@400;600;700")
    if not partes:
        return ""
    return "https://fonts.googleapis.com/css2?" + "&".join(partes) + "&display=swap"


def url_todas_las_fuentes():
    """URL que precarga TODAS las fuentes (para el preview en vivo del editor)."""
    return fuentes_css_url([f[0] for f in FUENTES])
