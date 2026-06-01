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

from flask import Blueprint, render_template

from app.tenant import cargar_negocio_por_slug

publico_bp = Blueprint("publico", __name__)


@publico_bp.route("/<slug>")
def perfil_negocio(slug):
    """Perfil público del negocio identificado por su slug."""
    negocio = cargar_negocio_por_slug(slug)
    return render_template("publico/perfil.html", negocio=negocio)
