"""
app/tenant.py
-------------
Resolución multi-tenant por PATH (/slug-negocio).

En las páginas públicas el negocio se identifica por su slug en la URL.
cargar_negocio_por_slug() lo busca y, si existe, lo deja disponible en
flask.g.negocio para que cualquier vista o template lo use sin volver a
consultarlo.

Para el PANEL privado el tenant NO viene de la URL sino de la sesión
(current_user.negocio): el dueño/staff ya está atado a su negocio.
"""

from flask import g, abort

from app.models.negocio import Negocio


def cargar_negocio_por_slug(slug):
    """
    Busca un negocio activo por slug y lo guarda en g.negocio.
    Aborta con 404 si no existe o está inactivo.
    """
    negocio = Negocio.query.filter_by(slug=slug, activo=True).first()
    if negocio is None:
        abort(404)
    g.negocio = negocio
    return negocio
