"""
app/marketplace/routes.py
-------------------------
Directorio público de negocios. Lista solo los negocios que activaron
visible_marketplace y están activos. Permite filtrar por ciudad, rubro y
texto (nombre del negocio o de sus servicios), y ordenar por calificación.

No es multi-tenant: justamente cruza todos los negocios. Pero solo expone
los que eligieron aparecer (visible_marketplace=True).
"""

from flask import Blueprint, render_template, request
from sqlalchemy import or_, select

from app.extensions import db
from app.models.negocio import Negocio, RubroEnum
from app.models.servicio import Servicio
from app.resenas.service import rating_negocio

marketplace_bp = Blueprint("marketplace", __name__)


@marketplace_bp.route("/marketplace")
def index():
    texto = (request.args.get("q") or "").strip()
    ciudad = (request.args.get("ciudad") or "").strip()
    rubro = (request.args.get("rubro") or "").strip()
    orden = request.args.get("orden", "rating")

    q = Negocio.query.filter_by(visible_marketplace=True, activo=True)

    if ciudad:
        q = q.filter(Negocio.ciudad.ilike(f"%{ciudad}%"))

    if rubro:
        try:
            q = q.filter(Negocio.rubro == RubroEnum(rubro))
        except ValueError:
            pass

    if texto:
        # Negocios cuyo nombre coincide, o que tienen un servicio que coincide.
        sub = (
            select(Servicio.negocio_id)
            .where(Servicio.activo.is_(True), Servicio.nombre.ilike(f"%{texto}%"))
        )
        q = q.filter(or_(Negocio.nombre.ilike(f"%{texto}%"), Negocio.id.in_(sub)))

    negocios = q.limit(60).all()

    # Calcular rating de cada negocio y armar la lista de resultados.
    resultados = []
    for n in negocios:
        promedio, cantidad = rating_negocio(n.id)
        resultados.append({"negocio": n, "rating": promedio, "cantidad": cantidad})

    if orden == "rating":
        resultados.sort(key=lambda r: (r["rating"] or 0, r["cantidad"]), reverse=True)
    elif orden == "nombre":
        resultados.sort(key=lambda r: r["negocio"].nombre.lower())

    # Ciudades disponibles para el filtro (de negocios visibles).
    ciudades = [
        c[0] for c in (
            db.session.query(Negocio.ciudad)
            .filter(Negocio.visible_marketplace.is_(True), Negocio.activo.is_(True),
                    Negocio.ciudad.isnot(None))
            .distinct().order_by(Negocio.ciudad).all()
        )
    ]

    return render_template(
        "marketplace/index.html",
        resultados=resultados, rubros=RubroEnum, ciudades=ciudades,
        f_q=texto, f_ciudad=ciudad, f_rubro=rubro, f_orden=orden,
    )
