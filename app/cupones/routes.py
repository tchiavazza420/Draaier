"""
app/cupones/routes.py
---------------------
Panel de cupones / gift cards (crear, listar, activar/desactivar, eliminar).
La aplicación del descuento al reservar y el link público viven en el módulo
público (publico/routes.py) y el servicio (cupones/service.py).
"""

from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, current_app,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.cupon import Cupon
from app.models.servicio import Servicio
from app.cupones import service as cupones

cupones_bp = Blueprint("cupones", __name__)
_ROLES = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


@cupones_bp.route("/")
@login_required
@rol_required(*_ROLES)
def listar():
    items = (query_tenant(Cupon, _neg())
             .order_by(Cupon.activo.desc(), Cupon.created_at.desc()).all())
    servicios = (query_tenant(Servicio, _neg())
                 .filter_by(activo=True).order_by(Servicio.nombre).all())
    base = current_app.config.get("SITE_URL", "").rstrip("/")
    return render_template("cupones/listar.html", cupones=items, servicios=servicios,
                           negocio=current_user.negocio, base_url=base)


@cupones_bp.route("/nuevo", methods=["POST"])
@login_required
@rol_required(*_ROLES)
@negocio_operativo_required
def nuevo():
    from decimal import Decimal
    tipo = request.form.get("tipo", "porcentaje")
    try:
        valor = Decimal(str(request.form.get("valor") or "0"))
    except Exception:
        valor = Decimal("0")
    if valor <= 0 or (tipo == "porcentaje" and valor > 100):
        flash("Valor de descuento inválido.", "danger")
        return redirect(url_for("cupones.listar"))

    servicio_id = request.form.get("servicio_id", type=int) or None
    if servicio_id:  # validar que el servicio sea del negocio
        obtener_tenant_o_404(Servicio, _neg(), servicio_id)

    usos_max = request.form.get("usos_max", type=int) or None
    vence = None
    vence_str = (request.form.get("vence") or "").strip()
    if vence_str:
        try:
            vence = datetime.strptime(vence_str, "%Y-%m-%d")
        except ValueError:
            vence = None

    cupon = Cupon(
        negocio_id=_neg(),
        codigo=cupones.generar_codigo(_neg()),
        descripcion=(request.form.get("descripcion") or "").strip() or None,
        tipo="monto" if tipo == "monto" else "porcentaje",
        valor=valor, servicio_id=servicio_id,
        usos_max=usos_max, vence=vence, activo=True,
    )
    db.session.add(cupon)
    db.session.commit()
    flash(f"Cupón {cupon.codigo} creado ({cupon.etiqueta}).", "success")
    return redirect(url_for("cupones.listar"))


@cupones_bp.route("/<int:cupon_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES)
@negocio_operativo_required
def toggle(cupon_id):
    c = obtener_tenant_o_404(Cupon, _neg(), cupon_id)
    c.activo = not c.activo
    db.session.commit()
    flash(f"Cupón {c.codigo} {'activado' if c.activo else 'desactivado'}.", "info")
    return redirect(url_for("cupones.listar"))


@cupones_bp.route("/<int:cupon_id>/eliminar", methods=["POST"])
@login_required
@rol_required(*_ROLES)
@negocio_operativo_required
def eliminar(cupon_id):
    c = obtener_tenant_o_404(Cupon, _neg(), cupon_id)
    codigo = c.codigo
    db.session.delete(c)
    db.session.commit()
    flash(f"Cupón {codigo} eliminado.", "success")
    return redirect(url_for("cupones.listar"))
