"""
app/auth/utils.py
-----------------
Utilidades de autenticación/registro.

- slugify(): convierte un nombre en un slug URL-safe (sin acentos ni símbolos).
- generar_slug_unico(): garantiza unicidad agregando sufijos numéricos.
- SLUGS_RESERVADOS: palabras que un negocio NO puede usar como slug porque
  colisionarían con rutas del sistema (/auth, /panel, etc.).
"""

import re
import unicodedata

from app.models.negocio import Negocio


# Rutas/prefijos del sistema que no pueden ser tomados como slug de negocio.
SLUGS_RESERVADOS = {
    "auth", "panel", "admin", "api", "health", "static",
    "login", "logout", "registro", "marketplace", "super-admin",
    "pagos", "webhooks", "reservas", "recursos", "servicios", "clientes",
}


def slugify(texto):
    """
    Convierte un texto en slug: minúsculas, sin acentos, espacios y símbolos
    reemplazados por guiones. Ej: "Julieta Nails & Spa" -> "julieta-nails-spa".
    """
    # Normaliza y elimina marcas diacríticas (acentos).
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    # Reemplaza todo lo que no sea alfanumérico por guiones.
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    # Colapsa guiones repetidos y recorta los de los extremos.
    texto = re.sub(r"-{2,}", "-", texto).strip("-")
    return texto or "negocio"


def generar_slug_unico(nombre):
    """
    Devuelve un slug único para un negocio nuevo.

    Si el slug base está reservado o ya existe, agrega un sufijo numérico
    incremental (-2, -3, ...) hasta encontrar uno libre.
    """
    base = slugify(nombre)

    # Evita colisiones con rutas del sistema.
    if base in SLUGS_RESERVADOS:
        base = f"{base}-negocio"

    slug = base
    contador = 2
    while Negocio.query.filter_by(slug=slug).first() is not None:
        slug = f"{base}-{contador}"
        contador += 1
    return slug
