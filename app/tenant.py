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


def query_tenant(model_class, negocio_id):
    """
    Devuelve una query de `model_class` YA filtrada por negocio_id.

    Usar SIEMPRE esto (en lugar de model_class.query) para modelos tenant:
    garantiza que jamás se listen datos de otro negocio.
    """
    return model_class.query.filter_by(negocio_id=negocio_id)


def obtener_tenant_o_404(model_class, negocio_id, obj_id):
    """
    Trae un objeto por id PERO exigiendo que pertenezca al negocio dado.

    Si el id existe pero es de otro negocio, responde 404 (no 403): así no
    revelamos siquiera la existencia del recurso ajeno. Esta es la defensa
    central contra IDOR (acceso a recursos por id manipulado).
    """
    obj = model_class.query.filter_by(id=obj_id, negocio_id=negocio_id).first()
    if obj is None:
        abort(404)
    return obj
