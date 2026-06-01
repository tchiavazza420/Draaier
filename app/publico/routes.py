"""
app/publico/routes.py
---------------------
Páginas públicas del negocio, resueltas por slug: /<slug-negocio>.

Incluye el FLUJO PÚBLICO DE RESERVA:
  1. /<slug>/servicio/<s>            página del servicio con selector de fecha
  2. /<slug>/reservar/slots          (HTMX) turnos disponibles para la fecha
  3. /<slug>/reservar/form           (HTMX) formulario de datos del cliente
  4. POST /<slug>/reservar           crea la reserva (valida disponibilidad)
  5. /<slug>/reserva/<codigo>        confirmación

IMPORTANTE: este blueprint se registra SIN url_prefix y con rutas que
empiezan con /<slug>. Va ÚLTIMO para que /auth, /panel, etc. tengan
prioridad, y utils.py reserva esos nombres como slugs prohibidos.
"""

from datetime import datetime, date

from flask import Blueprint, render_template, abort, request, redirect, url_for, flash

from app.extensions import db
from app.tenant import cargar_negocio_por_slug
from app.models.recurso import Recurso
from app.models.servicio import Servicio
from app.models.reserva import Reserva, EstadoReservaEnum
from app.disponibilidad.service import calcular_slots_servicio
from app.reservas.service import (
    crear_reserva, obtener_o_crear_cliente, ocupados_por_servicio, ReservaError,
)

publico_bp = Blueprint("publico", __name__)


def _servicio_publico(negocio, servicio_slug):
    s = Servicio.query.filter_by(
        negocio_id=negocio.id, slug=servicio_slug, activo=True
    ).first()
    if s is None:
        abort(404)
    return s


@publico_bp.route("/<slug>")
def perfil_negocio(slug):
    """Perfil público del negocio identificado por su slug."""
    negocio = cargar_negocio_por_slug(slug)
    recursos = (
        Recurso.query.filter_by(negocio_id=negocio.id, activo=True)
        .order_by(Recurso.nombre).all()
    )
    servicios = (
        Servicio.query.filter_by(negocio_id=negocio.id, activo=True)
        .order_by(Servicio.nombre).all()
    )
    return render_template(
        "publico/perfil.html",
        negocio=negocio, recursos=recursos, servicios=servicios,
    )


@publico_bp.route("/<slug>/servicio/<servicio_slug>")
def perfil_servicio(slug, servicio_slug):
    """Página del servicio con el selector de fecha para reservar."""
    negocio = cargar_negocio_por_slug(slug)
    servicio = _servicio_publico(negocio, servicio_slug)
    return render_template(
        "publico/servicio.html",
        negocio=negocio, servicio=servicio, hoy=date.today().isoformat(),
    )


@publico_bp.route("/<slug>/reservar/slots")
def reservar_slots(slug):
    """HTMX: turnos disponibles de un servicio en una fecha (clickeables)."""
    negocio = cargar_negocio_por_slug(slug)
    servicio = _servicio_publico(negocio, request.args.get("servicio", type=str))

    fecha, slots, error = None, [], None
    try:
        f = request.args.get("fecha", type=str)
        fecha = datetime.strptime(f, "%Y-%m-%d").date() if f else None
    except ValueError:
        error = "Fecha inválida."
    if fecha and not error:
        ahora = datetime.now() if fecha == date.today() else None
        slots = calcular_slots_servicio(
            servicio, fecha, ahora=ahora,
            ocupados_por_recurso=ocupados_por_servicio(servicio, fecha),
        )

    return render_template(
        "publico/_slots.html",
        negocio=negocio, servicio=servicio, fecha=fecha, slots=slots, error=error,
    )


@publico_bp.route("/<slug>/reservar/form")
def reservar_form(slug):
    """HTMX: formulario de datos del cliente para un slot elegido."""
    negocio = cargar_negocio_por_slug(slug)
    servicio = _servicio_publico(negocio, request.args.get("servicio", type=str))
    recurso = Recurso.query.filter_by(
        negocio_id=negocio.id, id=request.args.get("recurso", type=int), activo=True
    ).first()
    inicio_str = request.args.get("inicio", type=str)
    if recurso is None or not inicio_str:
        abort(404)
    return render_template(
        "publico/_form_reserva.html",
        negocio=negocio, servicio=servicio, recurso=recurso, inicio=inicio_str,
    )


@publico_bp.route("/<slug>/reservar", methods=["POST"])
def reservar_crear(slug):
    """Crea la reserva pública validando disponibilidad real."""
    negocio = cargar_negocio_por_slug(slug)
    if not negocio.puede_operar:
        abort(402)  # negocio con suscripción vencida no recibe reservas

    servicio = _servicio_publico(negocio, request.form.get("servicio", type=str))
    recurso = Recurso.query.filter_by(
        negocio_id=negocio.id, id=request.form.get("recurso", type=int), activo=True
    ).first()
    if recurso is None:
        abort(404)

    nombre = (request.form.get("nombre") or "").strip()
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    inicio_str = request.form.get("inicio", type=str)

    if not nombre or not (email or telefono):
        flash("Necesitamos tu nombre y un email o teléfono.", "danger")
        return redirect(url_for("publico.perfil_servicio", slug=slug, servicio_slug=servicio.slug))
    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        flash("Horario inválido.", "danger")
        return redirect(url_for("publico.perfil_servicio", slug=slug, servicio_slug=servicio.slug))

    try:
        cliente = obtener_o_crear_cliente(negocio.id, nombre, email, telefono)
        # Sin módulo de pagos todavía: confirmamos directo. Con señas/Mercado
        # Pago, esto nacería como PENDIENTE_PAGO hasta acreditar el pago.
        reserva = crear_reserva(
            negocio.id, servicio, recurso, cliente, inicio,
            estado=EstadoReservaEnum.CONFIRMADO,
        )
    except ReservaError as exc:
        db.session.rollback()
        flash(str(exc), "warning")
        return redirect(url_for("publico.perfil_servicio", slug=slug, servicio_slug=servicio.slug))

    return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=reserva.codigo))


@publico_bp.route("/<slug>/reserva/<codigo>")
def reserva_confirmacion(slug, codigo):
    """Confirmación / comprobante de la reserva."""
    negocio = cargar_negocio_por_slug(slug)
    reserva = Reserva.query.filter_by(negocio_id=negocio.id, codigo=codigo).first()
    if reserva is None:
        abort(404)
    return render_template("publico/reserva_ok.html", negocio=negocio, reserva=reserva)


@publico_bp.route("/<slug>/recurso/<recurso_slug>")
def perfil_recurso(slug, recurso_slug):
    """Perfil público de un recurso: /slug-negocio/recurso/slug-recurso."""
    negocio = cargar_negocio_por_slug(slug)
    recurso = Recurso.query.filter_by(
        negocio_id=negocio.id, slug=recurso_slug, activo=True
    ).first()
    if recurso is None:
        abort(404)
    return render_template("publico/recurso.html", negocio=negocio, recurso=recurso)
