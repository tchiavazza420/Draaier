"""
app/publico/routes.py
---------------------
Páginas públicas del negocio, resueltas por slug: /<slug-negocio>.

Por ahora es un perfil mínimo que demuestra la resolución de tenant por
path. En el módulo de marketplace/páginas públicas se ampliará con banner,
servicios, galería, reseñas y el flujo de reserva.

IMPORTANTE: este blueprint se registra SIN url_prefix y con una ruta
catch-all /<slug>. Por eso debe registrarse el ÚLTIMO, para que las rutas
específicas (/auth, /panel, /health) tengan prioridad. Además, utils.py
reserva esos nombres para que ningún negocio pueda tomarlos como slug.
"""

from flask import Blueprint, render_template, abort

from app.tenant import cargar_negocio_por_slug
from app.models.recurso import Recurso
from app.models.servicio import Servicio

publico_bp = Blueprint("publico", __name__)


@publico_bp.route("/<slug>")
def perfil_negocio(slug):
    """Perfil público del negocio identificado por su slug."""
    negocio = cargar_negocio_por_slug(slug)
    recursos = (
        Recurso.query
        .filter_by(negocio_id=negocio.id, activo=True)
        .order_by(Recurso.nombre)
        .all()
    )
    servicios = (
        Servicio.query
        .filter_by(negocio_id=negocio.id, activo=True)
        .order_by(Servicio.nombre)
        .all()
    )
    return render_template(
        "publico/perfil.html",
        negocio=negocio, recursos=recursos, servicios=servicios,
    )


@publico_bp.route("/<slug>/servicio/<servicio_slug>")
def perfil_servicio(slug, servicio_slug):
    """Perfil público de un servicio: /slug-negocio/servicio/slug-servicio."""
    negocio = cargar_negocio_por_slug(slug)
    servicio = Servicio.query.filter_by(
        negocio_id=negocio.id, slug=servicio_slug, activo=True
    ).first()
    if servicio is None:
        abort(404)
    return render_template("publico/servicio.html", negocio=negocio, servicio=servicio)


@publico_bp.route("/<slug>/recurso/<recurso_slug>")
def perfil_recurso(slug, recurso_slug):
    """
    Perfil público de un recurso concreto:
    /slug-negocio/recurso/slug-recurso.
    """
    negocio = cargar_negocio_por_slug(slug)
    recurso = Recurso.query.filter_by(
        negocio_id=negocio.id, slug=recurso_slug, activo=True
    ).first()
    if recurso is None:
        abort(404)
    return render_template("publico/recurso.html", negocio=negocio, recurso=recurso)
