"""
app/pagos/routes.py
-------------------
Rutas de pago: retorno del checkout, webhook de Mercado Pago y el checkout
simulado para desarrollo (cuando no hay credenciales).

El webhook se exime de CSRF porque lo invoca Mercado Pago (servidor externo),
no un formulario del sitio. Su seguridad se basa en RE-CONSULTAR el pago a la
API de MP (nunca confiamos en el cuerpo de la notificación).
"""

import secrets

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    session, current_app,
)
from flask_login import login_required, current_user

from app.extensions import db, csrf
from app.models.pago import Pago, PagoEstadoEnum
from app.models.negocio import Negocio
from app.pagos import service, mercadopago

pagos_bp = Blueprint("pagos", __name__)


# ======================================================================
#  CONEXIÓN OAuth con Mercado Pago ("Connect" — un clic, sin pegar token)
# ======================================================================
def _redirect_uri():
    return current_app.config["SITE_URL"] + url_for("pagos.mp_callback")


@pagos_bp.route("/mp/conectar")
@login_required
def mp_conectar():
    """Manda al negocio a Mercado Pago para autorizar la conexión de su cuenta."""
    if not getattr(current_user, "negocio", None):
        abort(403)
    if not mercadopago.oauth_configurado():
        flash("La conexión con Mercado Pago no está disponible todavía.", "warning")
        return redirect(url_for("panel.configuracion"))
    state = secrets.token_urlsafe(24)
    session["mp_oauth_state"] = state
    return redirect(mercadopago.url_autorizacion(state, _redirect_uri()))


@pagos_bp.route("/mp/callback")
@login_required
def mp_callback():
    """Vuelta de Mercado Pago: canjeamos el code por los tokens del negocio."""
    negocio = getattr(current_user, "negocio", None)
    if not negocio:
        abort(403)

    error = request.args.get("error")
    code = request.args.get("code")
    state = request.args.get("state")
    state_ok = state and state == session.pop("mp_oauth_state", None)

    if error or not code or not state_ok:
        flash("No se pudo conectar Mercado Pago. Probá de nuevo.", "danger")
        return redirect(url_for("panel.configuracion"))

    try:
        datos = mercadopago.intercambiar_codigo(code, _redirect_uri())
        service.conectar_negocio_mp(negocio, datos)
        flash("¡Mercado Pago conectado! Ya podés cobrar señas a tu cuenta. 💳", "success")
    except Exception:
        flash("Mercado Pago rechazó la conexión. Revisá e intentá otra vez.", "danger")
    return redirect(url_for("panel.configuracion"))


@pagos_bp.route("/mp/desconectar", methods=["POST"])
@login_required
def mp_desconectar():
    """Olvida la conexión de Mercado Pago del negocio."""
    negocio = getattr(current_user, "negocio", None)
    if not negocio:
        abort(403)
    service.desconectar_negocio_mp(negocio)
    flash("Desconectaste Mercado Pago. Las señas quedan en modo de prueba.", "info")
    return redirect(url_for("panel.configuracion"))


@pagos_bp.route("/retorno")
def retorno():
    """
    Página de retorno tras el checkout (back_urls de Mercado Pago).
    Muestra el estado; la confirmación definitiva llega por webhook.
    """
    estado = request.args.get("estado", "pending")
    return render_template("pagos/retorno.html", estado=estado)


@pagos_bp.route("/webhook/mercadopago", methods=["POST"])
@csrf.exempt
def webhook_mercadopago():
    """Recibe notificaciones de Mercado Pago y concilia el pago."""
    # ?neg=<id> indica una seña (cuenta del negocio); sin él, es la plataforma.
    neg_id = request.args.get("neg", type=int)
    token = None
    if neg_id:
        negocio = db.session.get(Negocio, neg_id)
        token = negocio.mercadopago_token if negocio else None
    if not mercadopago.esta_configurado(token):
        abort(404)

    # MP envía el id del pago por querystring (?id= o ?data.id=) o en el body.
    payment_id = (
        request.args.get("data.id")
        or request.args.get("id")
        or (request.get_json(silent=True) or {}).get("data", {}).get("id")
    )
    tipo = request.args.get("type") or (request.get_json(silent=True) or {}).get("type")

    if payment_id and (tipo in (None, "payment")):
        try:
            service.procesar_notificacion_mp(payment_id, token=token)
        except Exception:
            # Devolvemos 200 igual para que MP no reintente en loop ante
            # errores no recuperables; el estado se puede reconciliar luego.
            return "", 200
    return "", 200


# ======================================================================
#  CHECKOUT SIMULADO (solo cuando NO hay credenciales de Mercado Pago)
# ======================================================================
@pagos_bp.route("/<int:pago_id>/checkout-simulado")
def checkout_simulado(pago_id):
    """Pantalla de desarrollo para aprobar/rechazar un pago sin pasarela real."""
    if mercadopago.esta_configurado():
        abort(404)
    pago = db.session.get(Pago, pago_id)
    if pago is None:
        abort(404)
    return render_template("pagos/checkout_simulado.html", pago=pago)


@pagos_bp.route("/<int:pago_id>/simular", methods=["POST"])
def simular(pago_id):
    """Aplica el resultado elegido en el checkout simulado."""
    if mercadopago.esta_configurado():
        abort(404)
    pago = db.session.get(Pago, pago_id)
    if pago is None:
        abort(404)

    resultado = request.form.get("resultado")
    es_suscripcion = pago.concepto == "suscripcion"
    es_pack_wa = pago.concepto == "whatsapp_pack"

    if resultado == "aprobado":
        service.aprobar_pago(pago, external_id=f"SIM-{pago.id}")
        if es_suscripcion:
            flash("Pago aprobado (simulado). ¡Plan activado!", "success")
        elif es_pack_wa:
            flash(f"Pago aprobado (simulado). ¡Sumaste {pago.plan_destino} mensajes de WhatsApp!", "success")
        else:
            from app.notificaciones.service import (
                notificar_reserva_confirmada, notificar_negocio_nueva_reserva,
            )
            notificar_reserva_confirmada(pago.reserva)
            notificar_negocio_nueva_reserva(pago.reserva)
            flash("Pago aprobado (simulado). ¡Reserva confirmada!", "success")
    else:
        service.rechazar_pago(pago, external_id=f"SIM-{pago.id}")
        flash("Pago rechazado (simulado).", "warning")

    # Redirección según el concepto del pago.
    if es_suscripcion:
        return redirect(url_for("panel.plan"))
    if es_pack_wa:
        return redirect(url_for("panel.mensajes"))
    negocio = db.session.get(Negocio, pago.reserva.negocio_id)
    return redirect(url_for(
        "publico.reserva_confirmacion", slug=negocio.slug, codigo=pago.reserva.codigo
    ))
