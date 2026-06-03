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
from app.uploads import guardar_imagen

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
def _categoria_default():
    """
    Devuelve una categoría para asignar a los profesionales. Como ya no
    mostramos categorías en la UI, usamos la primera que exista o creamos una
    "General" oculta (TipoRecurso sigue existiendo en el modelo).
    """
    cat = query_tenant(TipoRecurso, _neg()).first()
    if cat is None:
        cat = TipoRecurso(
            negocio_id=_neg(), nombre="General",
            slug=generar_slug_unico_scoped(TipoRecurso, "General", _neg()),
            activo=True,
        )
        db.session.add(cat)
        db.session.flush()
    return cat


@recursos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_nuevo():
    # Límite de profesionales según el plan (Independiente = 1; Locales = varios).
    from app.planes import limite_agendas_de
    limite = limite_agendas_de(current_user.negocio.plan)
    if limite is not None:
        actuales = query_tenant(Recurso, _neg()).count()
        if actuales >= limite:
            flash(f"Tu plan permite hasta {limite} profesional(es). "
                  f"Subí de plan para agregar más.", "warning")
            return redirect(url_for("panel.plan"))

    form = RecursoForm()
    if form.validate_on_submit():
        try:
            foto = guardar_imagen(form.foto.data, _neg(), "profesional")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo profesional", recurso=None)
        recurso = Recurso(
            negocio_id=_neg(),
            tipo_recurso_id=_categoria_default().id,
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(Recurso, form.nombre.data, _neg()),
            especialidad=(form.especialidad.data or "").strip() or None,
            foto_filename=foto,
            descripcion=(form.descripcion.data or "").strip() or None,
            capacidad=form.capacidad.data,
            activo=form.activo.data,
        )
        db.session.add(recurso)
        db.session.commit()
        flash(f"Profesional '{recurso.nombre}' creado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo profesional", recurso=None)


@recursos_bp.route("/<int:recurso_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_editar(recurso_id):
    recurso = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    form = RecursoForm(obj=recurso)
    if form.validate_on_submit():
        # Si subió una foto nueva, la guardamos; si no, conservamos la actual.
        try:
            nueva_foto = guardar_imagen(form.foto.data, _neg(), "profesional")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("recursos/recurso_form.html", form=form,
                                   titulo="Editar profesional", recurso=recurso)
        if nueva_foto:
            recurso.foto_filename = nueva_foto

        if form.nombre.data.strip() != recurso.nombre:
            recurso.slug = generar_slug_unico_scoped(
                Recurso, form.nombre.data, _neg(), exclude_id=recurso.id
            )
        recurso.nombre = form.nombre.data.strip()
        recurso.especialidad = (form.especialidad.data or "").strip() or None
        recurso.capacidad = form.capacidad.data
        recurso.descripcion = (form.descripcion.data or "").strip() or None
        recurso.activo = form.activo.data
        db.session.commit()
        flash("Profesional actualizado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/recurso_form.html", form=form,
                           titulo="Editar profesional", recurso=recurso)


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
