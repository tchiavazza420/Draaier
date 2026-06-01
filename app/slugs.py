"""
app/slugs.py
------------
Utilidades de slug compartidas por todo el proyecto.

- slugify(): texto -> slug URL-safe (sin acentos ni símbolos).
- generar_slug_unico_global(): unicidad a nivel de toda la tabla (ej: Negocio).
- generar_slug_unico_scoped(): unicidad DENTRO de un negocio (ej: Recurso),
  porque dos negocios distintos sí pueden tener ambos "cancha-1".
"""

import re
import unicodedata


def slugify(texto):
    """
    Convierte un texto en slug: minúsculas, sin acentos, espacios y símbolos
    reemplazados por guiones. Ej: "Cancha N°1 (Techada)" -> "cancha-n-1-techada".
    """
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-{2,}", "-", texto).strip("-")
    return texto or "item"


def generar_slug_unico_global(model_class, nombre, slug_field="slug",
                              reservados=None, exclude_id=None):
    """
    Slug único a nivel de toda la tabla.

    - reservados: conjunto de slugs prohibidos (colisión con rutas, etc.).
    - exclude_id: id a ignorar (útil al editar, para no chocar consigo mismo).
    """
    base = slugify(nombre)
    if reservados and base in reservados:
        base = f"{base}-1"

    slug = base
    contador = 2
    while _existe(model_class, slug_field, slug, exclude_id=exclude_id):
        slug = f"{base}-{contador}"
        contador += 1
    return slug


def generar_slug_unico_scoped(model_class, nombre, negocio_id,
                              slug_field="slug", exclude_id=None):
    """Slug único DENTRO de un negocio (filtra por negocio_id)."""
    base = slugify(nombre)
    slug = base
    contador = 2
    while _existe(model_class, slug_field, slug,
                  negocio_id=negocio_id, exclude_id=exclude_id):
        slug = f"{base}-{contador}"
        contador += 1
    return slug


def _existe(model_class, slug_field, slug, negocio_id=None, exclude_id=None):
    """True si ya existe una fila con ese slug (respetando scope y exclusión)."""
    filtros = {slug_field: slug}
    if negocio_id is not None:
        filtros["negocio_id"] = negocio_id
    query = model_class.query.filter_by(**filtros)
    if exclude_id is not None:
        query = query.filter(model_class.id != exclude_id)
    return query.first() is not None
