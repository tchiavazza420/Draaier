"""
app/servicios/routes.py
-----------------------
CRUD de servicios en el panel del negocio.

Mismas garantías que recursos: todo filtrado por current_user.negocio_id
con los helpers tenant-aware, escritura bloqueada si la suscripción venció.

Al asignar recursos a un servicio, se validan uno por uno contra el negocio
(obtener_tenant_o_404): impide vincular recursos ajenos manipulando el form.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.slugs import generar_slug_unico_scoped
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.recurso import Recurso
from app.models.servicio import Servicio
from app.servicios.forms import ServicioForm

servicios_bp = Blueprint("servicios", __name__)

_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


def _recursos_activos():
    """Recursos activos del negocio, para poblar el select del formulario."""
    return (
        query_tenant(Recurso, _neg())
        .filter_by(activo=True)
        .order_by(Recurso.nombre)
        .all()
    )


def _resolver_recursos(ids):
    """
    Convierte una lista de ids enviada por el form en objetos Recurso,
    exigiendo que cada uno pertenezca al negocio (anti-manipulación).
    """
    seleccionados = []
    for rid in ids:
        seleccionados.append(obtener_tenant_o_404(Recurso, _neg(), rid))
    return seleccionados


@servicios_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    servicios = (
        query_tenant(Servicio, _neg())
        .order_by(Servicio.activo.desc(), Servicio.nombre.asc())
        .all()
    )
    return render_template("servicios/listar.html", servicios=servicios)


@servicios_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def nuevo():
    form = ServicioForm(recursos_disponibles=_recursos_activos())
    if form.validate_on_submit():
        servicio = Servicio(
            negocio_id=_neg(),
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(Servicio, form.nombre.data, _neg()),
            descripcion=(form.descripcion.data or "").strip() or None,
            duracion_minutos=form.duracion_minutos.data,
            precio=form.precio.data,
            color=form.color.data,
            requiere_sena=form.requiere_sena.data,
            sena_monto=form.sena_monto.data if form.requiere_sena.data else None,
            activo=form.activo.data,
        )
        servicio.recursos = _resolver_recursos(form.recursos.data)
        db.session.add(servicio)
        db.session.commit()
        flash(f"Servicio '{servicio.nombre}' creado.", "success")
        return redirect(url_for("servicios.listar"))
    return render_template("servicios/form.html", form=form, titulo="Nuevo servicio")


@servicios_bp.route("/<int:servicio_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def editar(servicio_id):
    servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id)
    form = ServicioForm(recursos_disponibles=_recursos_activos(), obj=servicio)
    # En GET preseleccionamos los recursos ya vinculados.
    if request.method == "GET":
        form.recursos.data = [r.id for r in servicio.recursos]

    if form.validate_on_submit():
        if form.nombre.data.strip() != servicio.nombre:
            servicio.slug = generar_slug_unico_scoped(
                Servicio, form.nombre.data, _neg(), exclude_id=servicio.id
            )
        servicio.nombre = form.nombre.data.strip()
        servicio.descripcion = (form.descripcion.data or "").strip() or None
        servicio.duracion_minutos = form.duracion_minutos.data
        servicio.precio = form.precio.data
        servicio.color = form.color.data
        servicio.requiere_sena = form.requiere_sena.data
        servicio.sena_monto = form.sena_monto.data if form.requiere_sena.data else None
        servicio.activo = form.activo.data
        servicio.recursos = _resolver_recursos(form.recursos.data)
        db.session.commit()
        flash("Servicio actualizado.", "success")
        return redirect(url_for("servicios.listar"))
    return render_template("servicios/form.html", form=form, titulo="Editar servicio")


@servicios_bp.route("/<int:servicio_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def toggle(servicio_id):
    servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id)
    servicio.activo = not servicio.activo
    db.session.commit()
    flash(f"Servicio {'activado' if servicio.activo else 'desactivado'}.", "info")
    return redirect(url_for("servicios.listar"))
