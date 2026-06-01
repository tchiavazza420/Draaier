"""
app/reservas/routes.py
----------------------
Gestión de reservas en el panel (estilo "Actividad"): listado con filtros,
detalle, cambios de estado y alta manual (para reservas tomadas por teléfono
o en el mostrador).

Todo aislado por current_user.negocio_id. La creación reusa el servicio de
reservas (validación de disponibilidad + anti doble-reserva).
"""

from datetime import datetime, date

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.recurso import Recurso
from app.models.servicio import Servicio
from app.models.reserva import Reserva, EstadoReservaEnum
from app.disponibilidad.service import calcular_slots_servicio
from app.reservas.service import (
    crear_reserva, cambiar_estado, obtener_o_crear_cliente,
    ocupados_por_servicio, ReservaError,
)

reservas_bp = Blueprint("reservas", __name__)

_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


# ======================================================================
#  LISTADO (Actividad)
# ======================================================================
@reservas_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    estado = request.args.get("estado", type=str)
    fecha_str = request.args.get("fecha", type=str)

    q = query_tenant(Reserva, _neg())
    if estado:
        try:
            q = q.filter(Reserva.estado == EstadoReservaEnum(estado))
        except ValueError:
            pass
    if fecha_str:
        try:
            f = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            ini = datetime.combine(f, datetime.min.time())
            q = q.filter(Reserva.inicio >= ini, Reserva.inicio < ini.replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    reservas = q.order_by(Reserva.inicio.desc()).limit(200).all()
    return render_template(
        "reservas/listar.html",
        reservas=reservas, estados=EstadoReservaEnum,
        filtro_estado=estado, filtro_fecha=fecha_str,
    )


@reservas_bp.route("/<int:reserva_id>")
@login_required
@rol_required(*_ROLES_PANEL)
def detalle(reserva_id):
    reserva = obtener_tenant_o_404(Reserva, _neg(), reserva_id)
    return render_template(
        "reservas/detalle.html", reserva=reserva, estados=EstadoReservaEnum,
    )


@reservas_bp.route("/<int:reserva_id>/estado", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def estado(reserva_id):
    reserva = obtener_tenant_o_404(Reserva, _neg(), reserva_id)
    nuevo = request.form.get("estado", type=str)
    try:
        cambiar_estado(reserva, EstadoReservaEnum(nuevo))
        flash(f"Reserva {reserva.codigo}: estado actualizado a {reserva.estado.value}.", "success")
    except (ValueError, ReservaError) as exc:
        flash(str(exc) or "Estado inválido.", "danger")
    return redirect(request.referrer or url_for("reservas.listar"))


# ======================================================================
#  ALTA MANUAL
# ======================================================================
@reservas_bp.route("/nueva")
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def nueva():
    servicios = (
        query_tenant(Servicio, _neg())
        .filter_by(activo=True).order_by(Servicio.nombre).all()
    )
    return render_template(
        "reservas/nueva.html", servicios=servicios, hoy=date.today().isoformat(),
    )


@reservas_bp.route("/nueva/slots")
@login_required
@rol_required(*_ROLES_PANEL)
def nueva_slots():
    """HTMX: slots clickeables para el alta manual."""
    servicio_id = request.args.get("servicio_id", type=int)
    fecha_str = request.args.get("fecha", type=str)
    servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id) if servicio_id else None

    fecha, slots, error = None, [], None
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
    except ValueError:
        error = "Fecha inválida."
    if servicio and fecha and not error:
        ahora = datetime.now() if fecha == date.today() else None
        slots = calcular_slots_servicio(
            servicio, fecha, ahora=ahora,
            ocupados_por_recurso=ocupados_por_servicio(servicio, fecha),
        )

    return render_template(
        "reservas/_slots_form.html",
        servicio=servicio, fecha=fecha, slots=slots, error=error,
    )


@reservas_bp.route("/nueva", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def nueva_crear():
    servicio = obtener_tenant_o_404(Servicio, _neg(), request.form.get("servicio_id", type=int))
    recurso = obtener_tenant_o_404(Recurso, _neg(), request.form.get("recurso_id", type=int))
    inicio_str = request.form.get("inicio", type=str)
    nombre = (request.form.get("nombre") or "").strip()
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    notas = request.form.get("notas")

    if not nombre:
        flash("El nombre del cliente es obligatorio.", "danger")
        return redirect(url_for("reservas.nueva"))
    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        flash("Horario inválido.", "danger")
        return redirect(url_for("reservas.nueva"))

    try:
        cliente = obtener_o_crear_cliente(_neg(), nombre, email, telefono)
        reserva = crear_reserva(
            _neg(), servicio, recurso, cliente, inicio,
            estado=EstadoReservaEnum.CONFIRMADO, notas=notas,
        )
    except ReservaError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("reservas.nueva"))

    flash(f"Reserva {reserva.codigo} creada.", "success")
    return redirect(url_for("reservas.detalle", reserva_id=reserva.id))
