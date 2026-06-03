"""
app/recursos/routes.py
----------------------
CRUD de tipos de recurso y recursos, dentro del panel del negocio.

TODAS las consultas se hacen con los helpers tenant-aware (query_tenant /
obtener_tenant_o_404) usando current_user.negocio_id: es imposible ver o
editar recursos de otro negocio aunque se manipule el id en la URL.

Autorización:
  - login + rol dueño/staff para todo.
  - escritura (crear/editar/activar) además exige negocio_operativo_required:
    si la suscripción venció, el negocio queda en solo lectura.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.slugs import generar_slug_unico_scoped
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.tipo_recurso import TipoRecurso
from app.models.recurso import Recurso
from app.recursos.forms import TipoRecursoForm, RecursoForm

recursos_bp = Blueprint("recursos", __name__)

# Roles autorizados a administrar recursos.
_ROLES_PANEL = ("dueno", "staff")


def _neg():
    """negocio_id del usuario logueado (atajo legible)."""
    return current_user.negocio_id


# ======================================================================
#  LISTADO GENERAL
# ======================================================================
@recursos_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    """Lista recursos y tipos del negocio actual."""
    recursos = (
        query_tenant(Recurso, _neg())
        .order_by(Recurso.activo.desc(), Recurso.nombre.asc())
        .all()
    )
    tipos = query_tenant(TipoRecurso, _neg()).order_by(TipoRecurso.nombre).all()
    return render_template("recursos/listar.html", recursos=recursos, tipos=tipos)


# ======================================================================
#  TIPOS DE RECURSO
# ======================================================================
@recursos_bp.route("/tipos/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_nuevo():
    form = TipoRecursoForm()
    if form.validate_on_submit():
        tipo = TipoRecurso(
            negocio_id=_neg(),
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(TipoRecurso, form.nombre.data, _neg()),
            activo=form.activo.data,
        )
        db.session.add(tipo)
        db.session.commit()
        flash(f"Tipo '{tipo.nombre}' creado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/tipo_form.html", form=form, titulo="Nuevo tipo de recurso")


@recursos_bp.route("/tipos/<int:tipo_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_editar(tipo_id):
    tipo = obtener_tenant_o_404(TipoRecurso, _neg(), tipo_id)
    form = TipoRecursoForm(obj=tipo)
    if form.validate_on_submit():
        # Si cambió el nombre, regeneramos el slug (excluyéndose a sí mismo).
        if form.nombre.data.strip() != tipo.nombre:
            tipo.slug = generar_slug_unico_scoped(
                TipoRecurso, form.nombre.data, _neg(), exclude_id=tipo.id
            )
        tipo.nombre = form.nombre.data.strip()
        tipo.activo = form.activo.data
        db.session.commit()
        flash("Tipo actualizado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/tipo_form.html", form=form, titulo="Editar tipo de recurso")


@recursos_bp.route("/tipos/<int:tipo_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_toggle(tipo_id):
    """Activa/desactiva un tipo (baja lógica, nunca borrado físico)."""
    tipo = obtener_tenant_o_404(TipoRecurso, _neg(), tipo_id)
    tipo.activo = not tipo.activo
    db.session.commit()
    flash(f"Tipo {'activado' if tipo.activo else 'desactivado'}.", "info")
    return redirect(url_for("recursos.listar"))


# ======================================================================
#  RECURSOS
# ======================================================================
def _tipos_del_negocio():
    return query_tenant(TipoRecurso, _neg()).order_by(TipoRecurso.nombre).all()


@recursos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_nuevo():
    # Límite de agendas según el plan (Independiente = 1; Locales = varias).
    from app.planes import limite_agendas_de
    limite = limite_agendas_de(current_user.negocio.plan)
    if limite is not None:
        actuales = query_tenant(Recurso, _neg()).count()
        if actuales >= limite:
            flash(f"Tu plan permite hasta {limite} agenda(s). "
                  f"Subí de plan para agregar más.", "warning")
            return redirect(url_for("panel.plan"))

    tipos = _tipos_del_negocio()
    if not tipos:
        flash("Primero creá al menos una categoría.", "warning")
        return redirect(url_for("recursos.tipo_nuevo"))

    form = RecursoForm(tipos=tipos)
    if form.validate_on_submit():
        # Doble verificación: el tipo elegido debe pertenecer al negocio.
        obtener_tenant_o_404(TipoRecurso, _neg(), form.tipo_recurso.data)
        recurso = Recurso(
            negocio_id=_neg(),
            tipo_recurso_id=form.tipo_recurso.data,
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(Recurso, form.nombre.data, _neg()),
            descripcion=(form.descripcion.data or "").strip() or None,
            capacidad=form.capacidad.data,
            activo=form.activo.data,
        )
        db.session.add(recurso)
        db.session.commit()
        flash(f"Recurso '{recurso.nombre}' creado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo recurso")


@recursos_bp.route("/<int:recurso_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_editar(recurso_id):
    recurso = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    tipos = _tipos_del_negocio()
    form = RecursoForm(tipos=tipos, obj=recurso)
    # En GET, preseleccionamos el tipo actual.
    if request.method == "GET":
        form.tipo_recurso.data = recurso.tipo_recurso_id

    if form.validate_on_submit():
        obtener_tenant_o_404(TipoRecurso, _neg(), form.tipo_recurso.data)
        if form.nombre.data.strip() != recurso.nombre:
            recurso.slug = generar_slug_unico_scoped(
                Recurso, form.nombre.data, _neg(), exclude_id=recurso.id
            )
        recurso.tipo_recurso_id = form.tipo_recurso.data
        recurso.nombre = form.nombre.data.strip()
        recurso.capacidad = form.capacidad.data
        recurso.descripcion = (form.descripcion.data or "").strip() or None
        recurso.activo = form.activo.data
        db.session.commit()
        flash("Recurso actualizado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/recurso_form.html", form=form, titulo="Editar recurso")


@recursos_bp.route("/<int:recurso_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_toggle(recurso_id):
    recurso = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    recurso.activo = not recurso.activo
    db.session.commit()
    flash(f"Recurso {'activado' if recurso.activo else 'desactivado'}.", "info")
    return redirect(url_for("recursos.listar"))
