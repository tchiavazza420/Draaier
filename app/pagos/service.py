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
from app.models.negocio import Negocio
from app.models.pago import Pago, PagoEstadoEnum, ProveedorPagoEnum
from app.models.reserva import EstadoReservaEnum
from app.pagos import mercadopago


class PagoError(Exception):
    """Error de dominio en el flujo de pagos."""


# ======================================================================
#  Conexión de la cuenta de Mercado Pago del negocio (OAuth "Connect")
# ======================================================================
def _expira_dt(expires_in):
    from datetime import datetime, timezone, timedelta
    try:
        segs = int(expires_in)
    except (TypeError, ValueError):
        segs = 0
    return datetime.now(timezone.utc) + timedelta(seconds=max(segs - 60, 0))


def conectar_negocio_mp(negocio, datos):
    """Guarda en el negocio los tokens devueltos por Mercado Pago tras el OAuth."""
    negocio.mercadopago_token = datos.get("access_token")
    negocio.mp_refresh_token = datos.get("refresh_token")
    negocio.mp_user_id = str(datos.get("user_id")) if datos.get("user_id") else None
    negocio.mp_public_key = datos.get("public_key")
    negocio.mp_token_expira = _expira_dt(datos.get("expires_in"))
    db.session.commit()
    return negocio


def desconectar_negocio_mp(negocio):
    """Olvida la conexión de Mercado Pago del negocio."""
    negocio.mercadopago_token = None
    negocio.mp_refresh_token = None
    negocio.mp_user_id = None
    negocio.mp_public_key = None
    negocio.mp_token_expira = None
    db.session.commit()
    return negocio


def token_mp_vigente(negocio):
    """
    Devuelve un access_token usable para el negocio, refrescándolo si está por
    vencer. Si el negocio no conectó su cuenta, devuelve None.
    """
    if not negocio or not negocio.mercadopago_token:
        return None
    from datetime import datetime, timezone
    exp = negocio.mp_token_expira
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc) and negocio.mp_refresh_token:
            try:
                datos = mercadopago.refrescar_token(negocio.mp_refresh_token)
                conectar_negocio_mp(negocio, datos)
            except Exception:
                pass  # si falla el refresh, intentamos con el token actual
    return negocio.mercadopago_token


def iniciar_pago_sena(reserva, servicio):
    """
    Crea un Pago de seña para la reserva y devuelve (pago, url_checkout).

    Cobra con Mercado Pago (Checkout Pro). Si no hay credenciales configuradas,
    cae a checkout simulado (desarrollo).
    """
    monto = servicio.sena_calculada or Decimal("0")
    if monto <= 0:
        raise PagoError("El servicio no tiene un monto de seña válido.")

    # La seña se cobra a la cuenta de Mercado Pago DEL NEGOCIO (conectada por
    # OAuth). Sin conexión, cae a checkout simulado (probar sin cobrar).
    negocio = db.session.get(Negocio, reserva.negocio_id)
    token_neg = token_mp_vigente(negocio)
    simulado = not token_neg

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
        # El webhook lleva el negocio para reconciliar con SU token.
        notif = current_app.config["SITE_URL"] + url_for(
            "pagos.webhook_mercadopago", neg=reserva.negocio_id)
        titulo = f"Seña - {servicio.nombre}"
        ref, checkout_url = mercadopago.crear_preferencia(pago, titulo, back, notif, token=token_neg)
        pago.preference_id = ref
        pago.init_point = checkout_url
        url = checkout_url

    db.session.commit()
    return pago, url


def iniciar_pago_transferencia(reserva, servicio):
    """
    Crea un Pago de seña por TRANSFERENCIA (pendiente). El cliente transfiere
    al alias del negocio; el negocio confirma el pago a mano desde el panel.
    Devuelve el pago.
    """
    monto = servicio.sena_calculada or Decimal("0")
    if monto <= 0:
        raise PagoError("El servicio no tiene un monto de seña válido.")

    pago = Pago(
        negocio_id=reserva.negocio_id,
        reserva_id=reserva.id,
        monto=monto,
        estado=PagoEstadoEnum.PENDIENTE,
        proveedor=ProveedorPagoEnum.TRANSFERENCIA,
        es_sena=True,
    )
    db.session.add(pago)
    db.session.commit()
    return pago


def iniciar_pago_plan(negocio, plan_key, precio):
    """
    Crea un Pago de SUSCRIPCIÓN (plan) y devuelve (pago, url_checkout).
    Cobra con Mercado Pago; sin credenciales cae a checkout simulado.
    """
    if precio <= 0:
        raise PagoError("Plan sin precio válido.")

    simulado = not mercadopago.esta_configurado()
    pago = Pago(
        negocio_id=negocio.id, reserva_id=None,
        concepto="suscripcion", plan_destino=plan_key,
        monto=Decimal(str(precio)), estado=PagoEstadoEnum.PENDIENTE,
        proveedor=ProveedorPagoEnum.SIMULADO if simulado else ProveedorPagoEnum.MERCADOPAGO,
        es_sena=False,
    )
    db.session.add(pago)
    db.session.flush()

    if simulado:
        url = url_for("pagos.checkout_simulado", pago_id=pago.id)
    else:
        from app.planes import PLANES
        back = current_app.config["SITE_URL"] + url_for("pagos.retorno")
        notif = current_app.config["SITE_URL"] + url_for("pagos.webhook_mercadopago")
        titulo = f"AgenPro · Plan {PLANES[plan_key]['nombre']}"
        ref, checkout_url = mercadopago.crear_preferencia(pago, titulo, back, notif)
        pago.preference_id = ref
        pago.init_point = checkout_url
        url = checkout_url

    db.session.commit()
    return pago, url


def iniciar_pago_pack_whatsapp(negocio, cantidad, precio):
    """
    Crea un Pago por un PACK de mensajes de WhatsApp y devuelve (pago, url).
    Cobra con Mercado Pago (credenciales de la plataforma); sin credenciales
    cae a checkout simulado. El pack se acredita recién al APROBARSE el pago.
    La cantidad viaja en plan_destino (string) para no sumar columnas.
    """
    if precio <= 0:
        raise PagoError("Pack sin precio válido.")

    simulado = not mercadopago.esta_configurado()
    pago = Pago(
        negocio_id=negocio.id, reserva_id=None,
        concepto="whatsapp_pack", plan_destino=str(int(cantidad)),
        monto=Decimal(str(precio)), estado=PagoEstadoEnum.PENDIENTE,
        proveedor=ProveedorPagoEnum.SIMULADO if simulado else ProveedorPagoEnum.MERCADOPAGO,
        es_sena=False,
    )
    db.session.add(pago)
    db.session.flush()

    if simulado:
        url = url_for("pagos.checkout_simulado", pago_id=pago.id)
    else:
        back = current_app.config["SITE_URL"] + url_for("pagos.retorno")
        notif = current_app.config["SITE_URL"] + url_for("pagos.webhook_mercadopago")
        titulo = f"AgenPro · {int(cantidad)} mensajes de WhatsApp"
        ref, checkout_url = mercadopago.crear_preferencia(pago, titulo, back, notif)
        pago.preference_id = ref
        pago.init_point = checkout_url
        url = checkout_url

    db.session.commit()
    return pago, url


def _acreditar_pack_whatsapp(pago):
    """Acredita el pack de mensajes pagado (cantidad en plan_destino)."""
    from app.whatsapp_creditos import comprar_pack
    negocio = db.session.get(Negocio, pago.negocio_id)
    if negocio is None:
        return
    try:
        cantidad = int(pago.plan_destino or 0)
    except (TypeError, ValueError):
        return
    if cantidad > 0:
        comprar_pack(negocio, cantidad)


def _activar_suscripcion(pago):
    """Activa el plan pagado en el negocio (suscripción ACTIVA por 30 días)."""
    from datetime import datetime, timezone, timedelta
    from app.models.negocio import Negocio, PlanEnum, EstadoSuscripcionEnum
    negocio = db.session.get(Negocio, pago.negocio_id)
    if negocio is None or not pago.plan_destino:
        return
    try:
        negocio.plan = PlanEnum(pago.plan_destino)
    except ValueError:
        return
    negocio.estado_suscripcion = EstadoSuscripcionEnum.ACTIVA
    negocio.suscripcion_fin = datetime.now(timezone.utc) + timedelta(days=30)


def aprobar_pago(pago, external_id=None):
    """Marca el pago como aprobado y aplica su efecto (idempotente)."""
    if pago.estado == PagoEstadoEnum.APROBADO:
        return pago
    pago.estado = PagoEstadoEnum.APROBADO
    if external_id:
        pago.external_id = str(external_id)

    if pago.concepto == "suscripcion":
        _activar_suscripcion(pago)
    elif pago.concepto == "whatsapp_pack":
        _acreditar_pack_whatsapp(pago)
    elif pago.reserva and pago.reserva.estado == EstadoReservaEnum.PENDIENTE_PAGO:
        pago.reserva.estado = EstadoReservaEnum.CONFIRMADO
    db.session.commit()

    # Notificación in-app de pago recibido (señas/pagos de reserva).
    if pago.concepto != "suscripcion" and pago.es_sena:
        try:
            from flask import url_for
            from app.notificaciones import centro
            url = (url_for("reservas.detalle", reserva_id=pago.reserva_id)
                   if pago.reserva_id else None)
            centro.crear(pago.negocio_id, "pago", "Pago recibido",
                         f"Seña de ${pago.monto}"
                         + (f" · {pago.reserva.cliente.nombre}" if pago.reserva else ""),
                         url=url)
        except Exception:
            pass
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


def procesar_notificacion_mp(payment_id, token=None):
    """
    Concilia una notificación de Mercado Pago: consulta el pago real (con el
    token del negocio para señas, o la plataforma) y actualiza el Pago local.
    """
    data = mercadopago.obtener_pago(payment_id, token=token)
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
        if not ya_confirmada and pago.reserva is not None:
            from app.notificaciones.service import (
                notificar_reserva_confirmada, notificar_negocio_nueva_reserva,
            )
            notificar_reserva_confirmada(pago.reserva)
            notificar_negocio_nueva_reserva(pago.reserva)
    elif estado_mp in ("rejected", "cancelled"):
        rechazar_pago(pago, external_id=payment_id)
    return pago
