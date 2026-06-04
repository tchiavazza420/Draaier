"""
app/pagos/routes.py
-------------------
Rutas de pago: retorno del checkout, webhook de Mercado Pago y el checkout
simulado para desarrollo (cuando no hay credenciales).

El webhook se exime de CSRF porque lo invoca Mercado Pago (servidor externo),
no un formulario del sitio. Su seguridad se basa en RE-CONSULTAR el pago a la
API de MP (nunca confiamos en el cuerpo de la notificación).
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)

from app.extensions import db, csrf
from app.models.pago import Pago, PagoEstadoEnum
from app.models.negocio import Negocio
from app.pagos import service, mercadopago

pagos_bp = Blueprint("pagos", __name__)


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

    if resultado == "aprobado":
        service.aprobar_pago(pago, external_id=f"SIM-{pago.id}")
        if es_suscripcion:
            flash("Pago aprobado (simulado). ¡Plan activado!", "success")
        else:
            from app.notificaciones.service import notificar_reserva_confirmada
            notificar_reserva_confirmada(pago.reserva)
            flash("Pago aprobado (simulado). ¡Reserva confirmada!", "success")
    else:
        service.rechazar_pago(pago, external_id=f"SIM-{pago.id}")
        flash("Pago rechazado (simulado).", "warning")

    # Redirección según el concepto del pago.
    if es_suscripcion:
        return redirect(url_for("panel.plan"))
    negocio = db.session.get(Negocio, pago.reserva.negocio_id)
    return redirect(url_for(
        "publico.reserva_confirmacion", slug=negocio.slug, codigo=pago.reserva.codigo
    ))
