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
    from app.models.resena import Resena
    from app.models.galeria import GaleriaFoto
    from app.resenas.service import rating_negocio
    promedio, cantidad = rating_negocio(negocio.id)
    resenas = (
        Resena.query.filter_by(negocio_id=negocio.id, oculta=False)
        .order_by(Resena.created_at.desc()).limit(10).all()
    )
    galeria = (
        GaleriaFoto.query.filter_by(negocio_id=negocio.id)
        .order_by(GaleriaFoto.orden, GaleriaFoto.id).limit(12).all()
    )
    # Plan individual (un solo profesional): la página principal ES la página
    # del profesional (la que se edita en el page-builder). Así lo que ves y
    # compartís es el diseño que personalizaste.
    if len(recursos) == 1:
        return render_template(
            "publico/recurso.html",
            negocio=negocio, recurso=recursos[0], galeria=galeria,
            rating_promedio=promedio, rating_cantidad=cantidad, resenas=resenas,
            principal=True,
        )
    return render_template(
        "publico/perfil.html",
        negocio=negocio, recursos=recursos, servicios=servicios,
        rating_promedio=promedio, rating_cantidad=cantidad, resenas=resenas,
        galeria=galeria,
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
        # Negocio con suscripción vencida: no recibe reservas (solo lectura).
        flash("Este negocio no está recibiendo reservas en este momento.", "warning")
        return redirect(url_for("publico.perfil_negocio", slug=slug))

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

    # Si el servicio pide seña, la reserva nace PENDIENTE_PAGO y se confirma
    # al acreditarse el pago. Si no, se confirma directo.
    requiere_sena = servicio.requiere_sena and servicio.sena_calculada > 0
    estado_inicial = (
        EstadoReservaEnum.PENDIENTE_PAGO if requiere_sena else EstadoReservaEnum.CONFIRMADO
    )

    try:
        cliente = obtener_o_crear_cliente(negocio.id, nombre, email, telefono)
        reserva = crear_reserva(
            negocio.id, servicio, recurso, cliente, inicio, estado=estado_inicial,
        )
    except ReservaError as exc:
        db.session.rollback()
        flash(str(exc), "warning")
        return redirect(url_for("publico.perfil_servicio", slug=slug, servicio_slug=servicio.slug))

    from app.notificaciones.service import (
        notificar_reserva_confirmada, notificar_reserva_pendiente,
        notificar_negocio_nueva_reserva,
    )

    if requiere_sena:
        from app.pagos.service import (
            iniciar_pago_sena, iniciar_pago_transferencia, PagoError,
        )
        # Método de cobro de la seña:
        #  - Mercado Pago conectado  -> checkout online.
        #  - Si no, alias cargado    -> transferencia (el negocio confirma a mano).
        #  - Si no hay ninguno       -> checkout simulado (desarrollo).
        if not negocio.mp_conectado and negocio.acepta_transferencia:
            try:
                iniciar_pago_transferencia(reserva, servicio)
            except PagoError as exc:
                flash(str(exc), "warning")
            notificar_reserva_pendiente(reserva)
            # Avisamos al negocio: tiene que confirmar la transferencia.
            notificar_negocio_nueva_reserva(reserva)
            return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=reserva.codigo))

        try:
            _, url_checkout = iniciar_pago_sena(reserva, servicio)
        except PagoError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=reserva.codigo))
        notificar_reserva_pendiente(reserva, url_pago=url_checkout)
        # El aviso al negocio para reservas con seña se manda al aprobarse el pago.
        return redirect(url_checkout)

    notificar_reserva_confirmada(reserva)
    notificar_negocio_nueva_reserva(reserva)  # "te entró un turno nuevo"
    return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=reserva.codigo))


@publico_bp.route("/<slug>/reserva/<codigo>")
def reserva_confirmacion(slug, codigo):
    """Confirmación / comprobante de la reserva."""
    negocio = cargar_negocio_por_slug(slug)
    reserva = Reserva.query.filter_by(negocio_id=negocio.id, codigo=codigo).first()
    if reserva is None:
        abort(404)
    from app.resenas.service import puede_resenar
    from urllib.parse import quote

    # Link "Agregar a Google Calendar".
    fmt = "%Y%m%dT%H%M%S"
    cal_text = quote(f"{reserva.servicio.nombre} · {negocio.nombre}")
    cal_dates = f"{reserva.inicio.strftime(fmt)}/{reserva.fin.strftime(fmt)}"
    cal_det = quote(f"Reserva {reserva.codigo} con {reserva.recurso.nombre}.")
    cal_loc = quote(negocio.ciudad or negocio.nombre)
    gcal_url = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={cal_text}&dates={cal_dates}&details={cal_det}&location={cal_loc}"
    )

    # Aviso por WhatsApp (al WhatsApp del negocio si lo tiene; si no, share libre).
    msg = quote(
        f"¡Hola {negocio.nombre}! Reservé un turno: {reserva.servicio.nombre} "
        f"el {reserva.inicio.strftime('%d/%m a las %H:%M')}. Código {reserva.codigo}."
    )
    if negocio.whatsapp:
        num = negocio.whatsapp.replace("+", "").replace(" ", "")
        wa_url = f"https://wa.me/{num}?text={msg}"
    else:
        wa_url = f"https://wa.me/?text={msg}"

    # Si la seña es por transferencia y sigue pendiente, mostramos el alias.
    transferencia = None
    if reserva.estado == EstadoReservaEnum.PENDIENTE_PAGO and negocio.acepta_transferencia:
        from app.models.pago import ProveedorPagoEnum, PagoEstadoEnum
        transferencia = next(
            (p for p in reserva.pagos
             if p.proveedor == ProveedorPagoEnum.TRANSFERENCIA
             and p.estado == PagoEstadoEnum.PENDIENTE),
            None,
        )

    return render_template(
        "publico/reserva_ok.html",
        negocio=negocio, reserva=reserva, puede_resenar=puede_resenar(reserva),
        gcal_url=gcal_url, wa_url=wa_url, transferencia=transferencia,
    )


@publico_bp.route("/<slug>/reserva/<codigo>/resena", methods=["GET", "POST"])
def reserva_resena(slug, codigo):
    """Permite reseñar una reserva finalizada (acceso por código)."""
    from app.resenas.service import puede_resenar, crear_resena, ResenaError
    negocio = cargar_negocio_por_slug(slug)
    reserva = Reserva.query.filter_by(negocio_id=negocio.id, codigo=codigo).first()
    if reserva is None:
        abort(404)

    if not puede_resenar(reserva):
        flash("Esta reserva no está disponible para reseñar.", "warning")
        return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=codigo))

    if request.method == "POST":
        try:
            calificacion = int(request.form.get("calificacion", 0))
        except (ValueError, TypeError):
            calificacion = 0
        try:
            crear_resena(reserva, calificacion, request.form.get("comentario"))
        except ResenaError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("publico.reserva_resena", slug=slug, codigo=codigo))
        flash("¡Gracias por tu reseña!", "success")
        return redirect(url_for("publico.reserva_confirmacion", slug=slug, codigo=codigo))

    return render_template("publico/resena_form.html", negocio=negocio, reserva=reserva)


@publico_bp.route("/<slug>/recurso/<recurso_slug>")
def perfil_recurso(slug, recurso_slug):
    """Perfil público de un recurso: /slug-negocio/recurso/slug-recurso."""
    negocio = cargar_negocio_por_slug(slug)
    recurso = Recurso.query.filter_by(
        negocio_id=negocio.id, slug=recurso_slug, activo=True
    ).first()
    if recurso is None:
        abort(404)
    from app.models.galeria import GaleriaFoto
    from app.models.resena import Resena
    from app.resenas.service import rating_negocio
    galeria = (
        GaleriaFoto.query.filter_by(negocio_id=negocio.id)
        .order_by(GaleriaFoto.orden, GaleriaFoto.id).limit(9).all()
    )
    promedio, cantidad = rating_negocio(negocio.id)
    resenas = (
        Resena.query.filter_by(negocio_id=negocio.id, oculta=False)
        .order_by(Resena.created_at.desc()).limit(6).all()
    )
    return render_template("publico/recurso.html", negocio=negocio, recurso=recurso,
                           galeria=galeria, rating_promedio=promedio,
                           rating_cantidad=cantidad, resenas=resenas)
