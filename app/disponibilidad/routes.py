"""
app/disponibilidad/routes.py
----------------------------
Panel de disponibilidad: gestión de horarios por recurso, bloqueos, y una
vista previa de slots calculados en tiempo real (con HTMX, sin recargar).

Todo aislado por current_user.negocio_id con los helpers tenant-aware.
"""

from datetime import datetime, date

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.recurso import Recurso
from app.models.servicio import Servicio
from app.models.horario import HorarioAtencion, Bloqueo, DIAS_SEMANA
from app.disponibilidad.forms import HorarioForm, BloqueoForm
from app.disponibilidad.service import calcular_slots_servicio

disponibilidad_bp = Blueprint("disponibilidad", __name__)

_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


# ======================================================================
#  OVERVIEW: elegir recurso a configurar
# ======================================================================
@disponibilidad_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def index():
    recursos = query_tenant(Recurso, _neg()).order_by(Recurso.nombre).all()
    return render_template("disponibilidad/index.html", recursos=recursos)


# ======================================================================
#  HORARIOS + BLOQUEOS de un recurso
# ======================================================================
@disponibilidad_bp.route("/recurso/<int:recurso_id>")
@login_required
@rol_required(*_ROLES_PANEL)
def recurso(recurso_id):
    rec = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    horarios = (
        query_tenant(HorarioAtencion, _neg())
        .filter_by(recurso_id=rec.id)
        .order_by(HorarioAtencion.dia_semana, HorarioAtencion.hora_inicio)
        .all()
    )
    # Bloqueos del recurso + globales del negocio, vigentes o futuros.
    bloqueos = (
        query_tenant(Bloqueo, _neg())
        .filter((Bloqueo.recurso_id == rec.id) | (Bloqueo.recurso_id.is_(None)))
        .order_by(Bloqueo.inicio.desc())
        .limit(50)
        .all()
    )
    recursos_negocio = query_tenant(Recurso, _neg()).order_by(Recurso.nombre).all()

    horario_form = HorarioForm()
    bloqueo_form = BloqueoForm(recursos=recursos_negocio)
    # Preseleccionar este recurso en el form de bloqueo.
    bloqueo_form.recurso_id.data = rec.id

    # Agrupar horarios por día para mostrarlos ordenados.
    horarios_por_dia = {i: [] for i in range(7)}
    for h in horarios:
        horarios_por_dia[h.dia_semana].append(h)

    return render_template(
        "disponibilidad/recurso.html",
        recurso=rec, horarios_por_dia=horarios_por_dia, dias=DIAS_SEMANA,
        bloqueos=bloqueos, horario_form=horario_form, bloqueo_form=bloqueo_form,
    )


@disponibilidad_bp.route("/recurso/<int:recurso_id>/horario", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def horario_agregar(recurso_id):
    rec = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    form = HorarioForm()
    if form.validate_on_submit():
        ini, fin = form.hora_inicio_time, form.hora_fin_time
        creadas = 0
        for dia in form.dias.data:
            # Evita duplicar la misma franja exacta en el mismo día.
            existe = HorarioAtencion.query.filter_by(
                negocio_id=_neg(), recurso_id=rec.id, dia_semana=dia,
                hora_inicio=ini, hora_fin=fin,
            ).first()
            if existe is None:
                db.session.add(HorarioAtencion(
                    negocio_id=_neg(), recurso_id=rec.id, dia_semana=dia,
                    hora_inicio=ini, hora_fin=fin, activo=True,
                ))
                creadas += 1
        db.session.commit()
        flash(f"{creadas} franja(s) horaria(s) agregada(s).", "success")
    else:
        _flashear_errores(form)
    return redirect(url_for("disponibilidad.recurso", recurso_id=rec.id))


@disponibilidad_bp.route("/horario/<int:horario_id>/eliminar", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def horario_eliminar(horario_id):
    h = obtener_tenant_o_404(HorarioAtencion, _neg(), horario_id)
    rid = h.recurso_id
    db.session.delete(h)
    db.session.commit()
    flash("Franja eliminada.", "info")
    return redirect(url_for("disponibilidad.recurso", recurso_id=rid))


@disponibilidad_bp.route("/recurso/<int:recurso_id>/bloqueo", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def bloqueo_agregar(recurso_id):
    rec = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    recursos_negocio = query_tenant(Recurso, _neg()).order_by(Recurso.nombre).all()
    form = BloqueoForm(recursos=recursos_negocio)
    if form.validate_on_submit():
        # recurso_id == 0 -> bloqueo global del negocio (NULL).
        rid = form.recurso_id.data or None
        if rid is not None:
            obtener_tenant_o_404(Recurso, _neg(), rid)  # valida pertenencia
        db.session.add(Bloqueo(
            negocio_id=_neg(),
            recurso_id=rid,
            inicio=form.inicio.data,
            fin=form.fin.data,
            motivo=(form.motivo.data or "").strip() or None,
        ))
        db.session.commit()
        flash("Bloqueo agregado.", "success")
    else:
        _flashear_errores(form)
    return redirect(url_for("disponibilidad.recurso", recurso_id=rec.id))


@disponibilidad_bp.route("/bloqueo/<int:bloqueo_id>/eliminar", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def bloqueo_eliminar(bloqueo_id):
    b = obtener_tenant_o_404(Bloqueo, _neg(), bloqueo_id)
    volver = request.form.get("recurso_id", type=int)
    db.session.delete(b)
    db.session.commit()
    flash("Bloqueo eliminado.", "info")
    if volver:
        return redirect(url_for("disponibilidad.recurso", recurso_id=volver))
    return redirect(url_for("disponibilidad.index"))


# ======================================================================
#  VISTA PREVIA DE DISPONIBILIDAD (HTMX)
# ======================================================================
@disponibilidad_bp.route("/preview")
@login_required
@rol_required(*_ROLES_PANEL)
def preview():
    """Página con el selector de servicio + fecha. Los slots se cargan por HTMX."""
    servicios = (
        query_tenant(Servicio, _neg())
        .filter_by(activo=True)
        .order_by(Servicio.nombre)
        .all()
    )
    return render_template(
        "disponibilidad/preview.html",
        servicios=servicios, hoy=date.today().isoformat(),
    )


@disponibilidad_bp.route("/slots")
@login_required
@rol_required(*_ROLES_PANEL)
def slots():
    """
    Endpoint HTMX: devuelve el parcial con los slots de un servicio en una
    fecha. Sin reservas todavía (Paso 6), así que ocupados va vacío.
    """
    servicio_id = request.args.get("servicio_id", type=int)
    fecha_str = request.args.get("fecha", type=str)

    servicio = None
    fecha = None
    error = None

    if servicio_id:
        servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id)
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
    except ValueError:
        error = "Fecha inválida."

    slots = []
    if servicio and fecha and not error:
        from app.reservas.service import ocupados_por_servicio
        ahora = datetime.now() if fecha == date.today() else None
        slots = calcular_slots_servicio(
            servicio, fecha, ahora=ahora,
            ocupados_por_recurso=ocupados_por_servicio(servicio, fecha),
        )

    return render_template(
        "disponibilidad/_slots.html",
        servicio=servicio, fecha=fecha, slots=slots, error=error,
    )


# ----------------------------------------------------------------------
def _flashear_errores(form):
    for campo, errores in form.errors.items():
        for e in errores:
            flash(e, "danger")
