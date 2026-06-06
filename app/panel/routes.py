"""
app/panel/routes.py
-------------------
Área privada del negocio (requiere sesión).

El dashboard es mínimo por ahora: confirma que el login y el aislamiento
por tenant funcionan, mostrando los datos del negocio del usuario logueado.
Se irá ampliando con reservas, recursos, agenda, etc.
"""

from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db, csrf
from app.auth.decorators import rol_required
from app.models.negocio import RubroEnum, TemplatePublicoEnum, PlanEnum
from app.panel.forms import NegocioConfigForm, PersonalizacionForm, MensajesForm
from app.uploads import guardar_imagen
from app.planes import (
    PLANES, ORDEN, info_plan, precio_anual, precio_desde,
    es_por_puesto, wa_incluidos_catalogo,
)

panel_bp = Blueprint("panel", __name__)


@panel_bp.route("/")
@login_required
def dashboard():
    """Tablero principal del negocio."""
    from app.whatsapp_creditos import estado as wa_estado

    negocio = current_user.negocio

    # Días restantes de prueba (si está en trial).
    dias_trial_restantes = None
    if negocio and negocio.trial_fin:
        delta = negocio.trial_fin - datetime.now(timezone.utc)
        dias_trial_restantes = max(delta.days, 0)

    # WhatsApp: saldo del mes + fecha de renovación (1° del próximo mes).
    wa = wa_estado(negocio)
    hoy = datetime.now()
    if hoy.month == 12:
        wa_renueva = datetime(hoy.year + 1, 1, 1)
    else:
        wa_renueva = datetime(hoy.year, hoy.month + 1, 1)

    # --- Onboarding: primeros pasos para dejar el salón listo ---
    onboarding = _estado_onboarding(negocio)

    # --- Métricas del día ---
    hoy_metricas = _metricas_del_dia(negocio)

    # Saludo según la hora.
    h = hoy.hour
    saludo = "Buenos días" if h < 13 else ("Buenas tardes" if h < 20 else "Buenas noches")

    return render_template(
        "panel/dashboard.html",
        negocio=negocio,
        dias_trial_restantes=dias_trial_restantes,
        wa=wa, wa_renueva=wa_renueva,
        plan_vence=negocio.vencimiento,
        onboarding=onboarding,
        hoy=hoy_metricas, saludo=saludo,
    )


def _metricas_del_dia(negocio):
    """
    Resumen del día (estilo agora): cobros (cobrado/pendiente), asistencias
    (completadas/ausentes/sin confirmar) y la agenda del día completa.
    """
    from datetime import date, time as _time
    from app.models.reserva import Reserva, EstadoReservaEnum as E

    ini = datetime.combine(date.today(), _time.min)
    fin = ini + timedelta(days=1)
    ahora = datetime.now()

    # Turnos de hoy que cuentan (no cancelados/reprogramados).
    agenda = (
        Reserva.query.filter_by(negocio_id=negocio.id)
        .filter(Reserva.inicio >= ini, Reserva.inicio < fin)
        .filter(Reserva.estado.in_([
            E.PENDIENTE_PAGO, E.CONFIRMADO, E.EN_PROCESO, E.FINALIZADO, E.AUSENTE,
        ]))
        .order_by(Reserva.inicio).all()
    )

    finalizados = [r for r in agenda if r.estado == E.FINALIZADO]
    a_cobrar = [r for r in agenda if r.estado in (E.CONFIRMADO, E.EN_PROCESO)]
    ausentes = [r for r in agenda if r.estado == E.AUSENTE]
    sin_confirmar = [r for r in agenda if r.estado == E.PENDIENTE_PAGO]
    atendibles = [r for r in agenda if r.estado != E.AUSENTE]

    cobrado = sum((r.precio or 0) for r in finalizados)
    pendiente = sum((r.precio or 0) for r in a_cobrar)
    meta = cobrado + pendiente  # objetivo del día = lo agendado

    return {
        "agenda": agenda,
        "total": len(agenda),
        "cobrado": cobrado,
        "pendiente": pendiente,
        "meta": meta,
        "pct_cobrado": round(cobrado / meta * 100) if meta else 0,
        "completados": len(finalizados),
        "atendibles": len(atendibles),
        "pct_asistencia": round(len(finalizados) / len(atendibles) * 100) if atendibles else 0,
        "ausentes": len(ausentes),
        "sin_confirmar": len(sin_confirmar),
        "proximos": [r for r in agenda if r.fin >= ahora and r.estado != E.AUSENTE][:5],
    }


def _estado_onboarding(negocio):
    """
    Calcula el progreso de configuración inicial del salón a partir de los
    datos ya cargados (no guarda estado: es siempre la foto real).
    Devuelve dict con los pasos, cuántos están completos y el % de avance.
    """
    from app.models.recurso import Recurso
    from app.models.servicio import Servicio
    from app.models.horario import HorarioAtencion

    nid = negocio.id
    tiene_prof = db.session.query(Recurso.id).filter_by(negocio_id=nid).first() is not None
    tiene_serv = db.session.query(Servicio.id).filter_by(negocio_id=nid).first() is not None
    tiene_horario = db.session.query(HorarioAtencion.id).filter_by(negocio_id=nid).first() is not None
    personalizado = bool(negocio.logo_filename or negocio.descripcion_publica)
    visible = bool(negocio.visible_marketplace)

    pasos = [
        {"clave": "profesional", "ok": tiene_prof, "icono": "💇",
         "titulo": "Cargá tu primer profesional",
         "texto": "Quien atiende y tiene su agenda.",
         "url": url_for("recursos.recurso_nuevo"), "cta": "Agregar profesional"},
        {"clave": "servicio", "ok": tiene_serv, "icono": "✂️",
         "titulo": "Creá un servicio",
         "texto": "Elegí de los típicos de tu rubro con un clic.",
         "url": url_for("servicios.sugeridos"), "cta": "Ver sugeridos"},
        {"clave": "horario", "ok": tiene_horario, "icono": "⏰",
         "titulo": "Definí tus horarios",
         "texto": "Cuándo atendés, para mostrar turnos disponibles.",
         "url": url_for("disponibilidad.index"), "cta": "Configurar horarios"},
        {"clave": "personalizar", "ok": personalizado, "icono": "🎨",
         "titulo": "Personalizá tu página",
         "texto": "Subí tu logo y contá de qué se trata tu salón.",
         "url": url_for("panel.personalizacion"), "cta": "Personalizar"},
        {"clave": "publicar", "ok": visible, "icono": "🌐",
         "titulo": "Publicá en el marketplace",
         "texto": "Hacé visible tu salón para recibir clientes nuevos.",
         "url": url_for("panel.configuracion"), "cta": "Hacer visible"},
    ]
    completos = sum(1 for p in pasos if p["ok"])
    total = len(pasos)
    return {
        "pasos": pasos,
        "completos": completos,
        "total": total,
        "porcentaje": round(completos / total * 100),
        "completo": completos == total,
    }


@panel_bp.route("/plan")
@login_required
@rol_required("dueno")
def plan():
    """Muestra el plan actual, qué incluye, y permite cambiarlo."""
    negocio = current_user.negocio
    # Datos derivados por plan para la vista (precio de referencia, anual, WA).
    precios_mes = {k: precio_desde(p) for k, p in PLANES.items()}
    precios_anuales = {k: precio_anual(p) for k, p in PLANES.items()}
    wa_incluidos = {k: wa_incluidos_catalogo(PlanEnum(k)) for k in PLANES}
    por_puesto = {k: es_por_puesto(p) for k, p in PLANES.items()}
    return render_template(
        "panel/plan.html",
        negocio=negocio, planes=PLANES, orden=ORDEN,
        precios_mes=precios_mes, precios_anuales=precios_anuales,
        wa_incluidos=wa_incluidos, por_puesto=por_puesto,
        plan_actual=info_plan(negocio.plan),
        plan_actual_key=negocio.plan.value if negocio.plan else None,
    )


@panel_bp.route("/pagos")
@login_required
@rol_required("dueno")
def pagos():
    """Panel de señas: cobradas, pendientes y total, con el detalle reciente."""
    from app.models.pago import Pago, PagoEstadoEnum

    negocio = current_user.negocio
    pagos = (
        Pago.query.filter_by(negocio_id=negocio.id)
        .order_by(Pago.created_at.desc()).limit(100).all()
    )
    aprobados = [p for p in pagos if p.estado == PagoEstadoEnum.APROBADO]
    pendientes = [p for p in pagos if p.estado == PagoEstadoEnum.PENDIENTE]
    resumen = {
        "cobrado": sum((p.monto or 0) for p in aprobados),
        "pendiente": sum((p.monto or 0) for p in pendientes),
        "n_aprobados": len(aprobados),
        "n_pendientes": len(pendientes),
    }
    return render_template("panel/pagos.html", negocio=negocio, pagos=pagos, r=resumen)


@panel_bp.route("/disenar")
@login_required
@rol_required("dueno")
def disenar_pagina():
    """
    Atajo a la personalización REAL de la página (el page-builder del
    profesional). Si hay un solo profesional (plan individual) va directo a
    editarlo; si hay varios, a la lista para elegir; si no hay, a crearlo.
    """
    from app.models.recurso import Recurso
    recs = (Recurso.query.filter_by(negocio_id=current_user.negocio_id)
            .order_by(Recurso.id).all())
    if len(recs) == 1:
        return redirect(url_for("recursos.recurso_editar", recurso_id=recs[0].id))
    if not recs:
        return redirect(url_for("recursos.recurso_nuevo"))
    return redirect(url_for("recursos.listar"))


@panel_bp.route("/plan/cambiar", methods=["POST"])
@login_required
@rol_required("dueno")
def plan_cambiar():
    """
    Cambia el plan del negocio. El cobro real iría por el módulo de pagos;
    acá se aplica el cambio (en planes pagos quedaría pendiente de pago hasta
    acreditar, pero lo dejamos efectivo para la demo).
    """
    negocio = current_user.negocio
    elegido = request.form.get("plan")
    if elegido not in PLANES:
        flash("Plan inválido.", "danger")
        return redirect(url_for("panel.plan"))

    if negocio.plan and negocio.plan.value == elegido:
        flash("Ya tenés ese plan.", "info")
        return redirect(url_for("panel.plan"))

    # Básico = plan de entrada con 14 días de prueba: se activa directo.
    if elegido == PlanEnum.BASICO.value:
        negocio.plan = PlanEnum.BASICO
        db.session.commit()
        flash("Tu plan ahora es Básico (incluye 14 días de prueba).", "success")
        return redirect(url_for("panel.plan"))

    # Planes pagos: se cobran con Mercado Pago (checkout). El plan se activa al
    # acreditarse el pago (webhook / checkout simulado).
    from app.pagos.service import iniciar_pago_plan, PagoError
    from app.planes import precio_desde
    try:
        _pago, url = iniciar_pago_plan(negocio, elegido, precio_desde(PLANES[elegido]))
    except PagoError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("panel.plan"))
    flash("Te llevamos al pago para activar tu plan.", "info")
    return redirect(url)


@panel_bp.route("/galeria", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def galeria():
    """Galería de fotos del negocio (subir varias / eliminar)."""
    from app.models.galeria import GaleriaFoto
    negocio = current_user.negocio

    if request.method == "POST":
        archivos = [f for f in request.files.getlist("fotos") if f and f.filename]
        # Tope por tanda: subir demasiadas a la vez puede agotar el tiempo del
        # request. El resto las sube en otra tanda.
        _MAX_TANDA = 12
        if len(archivos) > _MAX_TANDA:
            flash(f"Subí hasta {_MAX_TANDA} fotos por vez. Tomamos las primeras {_MAX_TANDA}.", "warning")
            archivos = archivos[:_MAX_TANDA]
        subidas = 0
        for f in archivos:
            try:
                ruta = guardar_imagen(f, negocio.id, "galeria")
            except ValueError as exc:
                flash(str(exc), "danger")
                continue
            if ruta:
                db.session.add(GaleriaFoto(negocio_id=negocio.id, filename=ruta, orden=0))
                subidas += 1
        db.session.commit()
        if subidas:
            flash(f"{subidas} foto(s) subida(s).", "success")
        return redirect(url_for("panel.galeria"))

    fotos = (
        GaleriaFoto.query.filter_by(negocio_id=negocio.id)
        .order_by(GaleriaFoto.orden, GaleriaFoto.id).all()
    )
    return render_template("panel/galeria.html", fotos=fotos, negocio=negocio)


@panel_bp.route("/galeria/<int:foto_id>/eliminar", methods=["POST"])
@login_required
@rol_required("dueno")
def galeria_eliminar(foto_id):
    from app.models.galeria import GaleriaFoto
    foto = GaleriaFoto.query.filter_by(
        id=foto_id, negocio_id=current_user.negocio_id
    ).first_or_404()
    db.session.delete(foto)
    db.session.commit()
    flash("Foto eliminada.", "info")
    return redirect(url_for("panel.galeria"))


@panel_bp.route("/mensajes", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def mensajes():
    """Configura los mensajes automáticos (qué se envía y por qué canal)."""
    negocio = current_user.negocio
    form = MensajesForm(obj=negocio)
    if form.validate_on_submit():
        negocio.notif_confirmacion = form.notif_confirmacion.data
        negocio.notif_recordatorio = form.notif_recordatorio.data
        negocio.notif_canal_email = form.notif_canal_email.data
        negocio.notif_canal_whatsapp = form.notif_canal_whatsapp.data
        negocio.mensaje_firma = (form.mensaje_firma.data or "").strip() or None
        db.session.commit()
        flash("Mensajes automáticos actualizados.", "success")
        return redirect(url_for("panel.mensajes"))

    from app.whatsapp_creditos import estado as wa_estado
    from app.planes import PACKS_WHATSAPP
    return render_template(
        "panel/mensajes.html", form=form, negocio=negocio,
        wa=wa_estado(negocio), packs=PACKS_WHATSAPP,
    )


@panel_bp.route("/whatsapp/comprar", methods=["POST"])
@login_required
@rol_required("dueno")
def whatsapp_comprar():
    """
    Compra un pack de mensajes de WhatsApp. El cobro real iría por la pasarela
    de pago; en esta versión se acredita al instante (simulado).
    """
    from app.planes import PACKS_WHATSAPP
    from app.whatsapp_creditos import comprar_pack
    cantidad = request.form.get("cantidad", type=int)
    valido = next((p for p in PACKS_WHATSAPP if p["cantidad"] == cantidad), None)
    if valido is None:
        flash("Pack inválido.", "danger")
        return redirect(url_for("panel.mensajes"))
    comprar_pack(current_user.negocio, cantidad)
    flash(f"¡Listo! Sumaste {cantidad} mensajes de WhatsApp, válidos por 30 días (simulado).", "success")
    return redirect(url_for("panel.mensajes"))


@panel_bp.route("/configuracion", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def configuracion():
    """Configuración del negocio: datos públicos y visibilidad en marketplace."""
    negocio = current_user.negocio
    form = NegocioConfigForm(obj=negocio)
    if form.validate_on_submit():
        negocio.nombre = form.nombre.data.strip()
        negocio.rubro = RubroEnum(form.rubro.data)
        negocio.ciudad = (form.ciudad.data or "").strip() or None
        negocio.direccion = (form.direccion.data or "").strip() or None
        negocio.telefono = (form.telefono.data or "").strip() or None
        negocio.email = form.email.data.strip().lower()
        negocio.visible_marketplace = form.visible_marketplace.data
        negocio.cancelacion_horas = form.cancelacion_horas.data
        negocio.reembolso_sena_horas = form.reembolso_sena_horas.data
        db.session.commit()
        flash("Configuración actualizada.", "success")
        return redirect(url_for("panel.configuracion"))
    # En GET, preseleccionar el rubro actual.
    if not form.is_submitted():
        form.rubro.data = negocio.rubro.value
    return render_template("panel/configuracion.html", form=form, negocio=negocio)


@panel_bp.route("/personalizacion", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def personalizacion():
    """Branding del negocio: logo, banner, colores, tipografía, redes, plantilla."""
    negocio = current_user.negocio
    form = PersonalizacionForm(obj=negocio)
    if form.validate_on_submit():
        try:
            ruta_logo = guardar_imagen(form.logo.data, negocio.id, "logo")
            ruta_banner = guardar_imagen(form.banner.data, negocio.id, "banner")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("panel.personalizacion"))

        if ruta_logo:
            negocio.logo_filename = ruta_logo
        if ruta_banner:
            negocio.banner_filename = ruta_banner
        negocio.color_primario = form.color_primario.data
        negocio.color_secundario = form.color_secundario.data
        negocio.tipografia = form.tipografia.data
        negocio.template_publico = TemplatePublicoEnum(form.template_publico.data)
        negocio.descripcion_publica = (form.descripcion_publica.data or "").strip() or None
        negocio.instagram = (form.instagram.data or "").strip() or None
        negocio.facebook = (form.facebook.data or "").strip() or None
        negocio.whatsapp = (form.whatsapp.data or "").strip() or None
        db.session.commit()
        flash("Personalización guardada.", "success")
        return redirect(url_for("panel.personalizacion"))

    if not form.is_submitted():
        form.template_publico.data = negocio.template_publico.value
        form.tipografia.data = negocio.tipografia
    return render_template("panel/personalizacion.html", form=form, negocio=negocio)


# ----------------------------------------------------------------------
#  Notificaciones push (Web Push / PWA)
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
#  Centro de notificaciones (campanita)
# ----------------------------------------------------------------------
@panel_bp.route("/notificaciones")
@login_required
def notificaciones():
    """Historial completo de notificaciones del negocio."""
    from app.notificaciones import centro
    items = centro.listar(current_user.negocio_id, limite=100)
    return render_template("panel/notificaciones.html", items=items)


@panel_bp.route("/notificaciones/<int:notif_id>/leer", methods=["POST"])
@login_required
def notificacion_leer(notif_id):
    """Marca una notificación como leída y va a su destino (si tiene)."""
    from app.notificaciones import centro
    n = centro.marcar_leida(current_user.negocio_id, notif_id)
    destino = n.url if (n and n.url) else url_for("panel.notificaciones")
    return redirect(destino)


@panel_bp.route("/notificaciones/leer-todas", methods=["POST"])
@login_required
def notificaciones_leer_todas():
    from app.notificaciones import centro
    centro.marcar_todas(current_user.negocio_id)
    return redirect(request.referrer or url_for("panel.notificaciones"))


@panel_bp.route("/push/suscribir", methods=["POST"])
@csrf.exempt
@login_required
def push_suscribir():
    """Guarda la suscripción push del navegador del usuario logueado."""
    from flask import jsonify
    from app.notificaciones import push
    if not push.esta_configurado():
        return jsonify(ok=False, error="push no configurado"), 503
    if not current_user.negocio:
        return jsonify(ok=False), 403
    try:
        push.guardar_suscripcion(
            current_user.negocio_id, current_user.id,
            request.get_json(silent=True) or {},
            user_agent=request.headers.get("User-Agent"))
    except ValueError:
        return jsonify(ok=False, error="suscripción inválida"), 400
    return jsonify(ok=True)
