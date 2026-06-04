"""
app/pagos/service.py
--------------------
Lógica de pagos: iniciar el cobro de una seña y conciliar su resultado con
el estado de la reserva.

Regla central:
  - Pago aprobado  -> la reserva pasa de PENDIENTE_PAGO a CONFIRMADO.
  - Pago rechazado -> la reserva queda PENDIENTE_PAGO (el cliente reintenta).

Funciona con Mercado Pago real (si hay token) o en modo simulación.
"""

from decimal import Decimal

from flask import current_app, url_for

from app.extensions import db
from app.models.pago import Pago, PagoEstadoEnum, ProveedorPagoEnum
from app.models.reserva import EstadoReservaEnum
from app.pagos import mercadopago


class PagoError(Exception):
    """Error de dominio en el flujo de pagos."""


def iniciar_pago_sena(reserva, servicio):
    """
    Crea un Pago de seña para la reserva y devuelve (pago, url_checkout).

    Cobra con Mercado Pago (Checkout Pro). Si no hay credenciales configuradas,
    cae a checkout simulado (desarrollo).
    """
    monto = servicio.sena_monto or Decimal("0")
    if monto <= 0:
        raise PagoError("El servicio no tiene un monto de seña válido.")

    simulado = not mercadopago.esta_configurado()

    pago = Pago(
        negocio_id=reserva.negocio_id,
        reserva_id=reserva.id,
        monto=monto,
        estado=PagoEstadoEnum.PENDIENTE,
        proveedor=ProveedorPagoEnum.SIMULADO if simulado else ProveedorPagoEnum.MERCADOPAGO,
        es_sena=True,
    )
    db.session.add(pago)
    db.session.flush()  # id disponible para external_reference / back_urls

    if simulado:
        url = url_for("pagos.checkout_simulado", pago_id=pago.id)
    else:
        back = current_app.config["SITE_URL"] + url_for("pagos.retorno")
        notif = current_app.config["SITE_URL"] + url_for("pagos.webhook_mercadopago")
        titulo = f"Seña - {servicio.nombre}"
        ref, checkout_url = mercadopago.crear_preferencia(pago, titulo, back, notif)
        pago.preference_id = ref
        pago.init_point = checkout_url
        url = checkout_url

    db.session.commit()
    return pago, url


def aprobar_pago(pago, external_id=None):
    """Marca el pago como aprobado y confirma la reserva (idempotente)."""
    if pago.estado == PagoEstadoEnum.APROBADO:
        return pago
    pago.estado = PagoEstadoEnum.APROBADO
    if external_id:
        pago.external_id = str(external_id)

    reserva = pago.reserva
    if reserva.estado == EstadoReservaEnum.PENDIENTE_PAGO:
        reserva.estado = EstadoReservaEnum.CONFIRMADO
    db.session.commit()
    return pago


def rechazar_pago(pago, external_id=None):
    """Marca el pago como rechazado. La reserva sigue pendiente de pago."""
    if pago.estado == PagoEstadoEnum.APROBADO:
        return pago  # no pisar un pago ya aprobado
    pago.estado = PagoEstadoEnum.RECHAZADO
    if external_id:
        pago.external_id = str(external_id)
    db.session.commit()
    return pago


def procesar_notificacion_mp(payment_id):
    """
    Concilia una notificación de Mercado Pago: consulta el pago real y
    actualiza el Pago local + la reserva según su estado.
    """
    data = mercadopago.obtener_pago(payment_id)
    estado_mp = data.get("status")
    external_reference = data.get("external_reference")
    if not external_reference:
        return None

    pago = db.session.get(Pago, int(external_reference))
    if pago is None:
        return None

    if estado_mp == "approved":
        ya_confirmada = pago.estado == PagoEstadoEnum.APROBADO
        aprobar_pago(pago, external_id=payment_id)
        if not ya_confirmada:
            from app.notificaciones.service import notificar_reserva_confirmada
            notificar_reserva_confirmada(pago.reserva)
    elif estado_mp in ("rejected", "cancelled"):
        rechazar_pago(pago, external_id=payment_id)
    return pago
