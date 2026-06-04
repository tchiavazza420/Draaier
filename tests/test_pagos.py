"""Tests del flujo de pagos (seña, modo simulación)."""

from datetime import datetime, time
from decimal import Decimal

from app.models.reserva import EstadoReservaEnum
from app.models.pago import Pago, PagoEstadoEnum
from app.reservas.service import crear_reserva, obtener_o_crear_cliente
from app.pagos.service import iniciar_pago_sena, aprobar_pago, rechazar_pago


def _reserva_con_sena(neg, rec, serv, lunes):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com")
    return crear_reserva(neg.id, serv, rec, cli, datetime.combine(lunes, time(9, 0)),
                         estado=EstadoReservaEnum.PENDIENTE_PAGO)


def test_pago_aprobado_confirma_reserva(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("2000"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)

    pago, url = iniciar_pago_sena(reserva, serv)
    assert pago.estado == PagoEstadoEnum.PENDIENTE
    assert pago.monto == Decimal("2000")
    assert "checkout-simulado" in url  # sin token MP -> simulado

    aprobar_pago(pago)
    assert pago.estado == PagoEstadoEnum.APROBADO
    assert reserva.estado == EstadoReservaEnum.CONFIRMADO


def test_pago_rechazado_mantiene_pendiente(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("1000"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)

    pago, _ = iniciar_pago_sena(reserva, serv)
    rechazar_pago(pago)
    assert pago.estado == PagoEstadoEnum.RECHAZADO
    assert reserva.estado == EstadoReservaEnum.PENDIENTE_PAGO


def test_pago_sin_credenciales_cae_a_simulado(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    """Sin MERCADOPAGO_ACCESS_TOKEN, el cobro de la seña cae a checkout simulado."""
    from app.models.pago import ProveedorPagoEnum

    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("1500"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)

    pago, url = iniciar_pago_sena(reserva, serv)
    # Sin credenciales -> checkout simulado, proveedor SIMULADO
    assert "checkout-simulado" in url
    assert pago.proveedor == ProveedorPagoEnum.SIMULADO
    # Y el flujo de aprobación confirma la reserva igual
    aprobar_pago(pago)
    assert reserva.estado == EstadoReservaEnum.CONFIRMADO


def test_conectar_mp_redirige_a_autorizacion(client, crear_negocio, login, monkeypatch):
    """El botón 'Conectar' manda al negocio a la URL de autorización de MP."""
    from app.pagos import mercadopago
    neg, dueno = crear_negocio()
    login(dueno.email)
    monkeypatch.setattr(mercadopago, "oauth_configurado", lambda: True)
    monkeypatch.setattr(mercadopago, "url_autorizacion",
                        lambda state, ru: f"https://auth.mp/authorization?state={state}")

    r = client.get("/pagos/mp/conectar", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].startswith("https://auth.mp/authorization")


def test_callback_mp_guarda_tokens(client, crear_negocio, login, monkeypatch):
    """El callback canjea el code y deja el negocio conectado."""
    from app.pagos import mercadopago
    from app.models.negocio import Negocio
    from app.extensions import db
    neg, dueno = crear_negocio()
    login(dueno.email)

    monkeypatch.setattr(mercadopago, "oauth_configurado", lambda: True)
    monkeypatch.setattr(mercadopago, "url_autorizacion",
                        lambda state, ru: f"https://auth.mp/x?state={state}")
    monkeypatch.setattr(mercadopago, "intercambiar_codigo", lambda code, ru: {
        "access_token": "APP_USR-neg", "refresh_token": "TG-ref",
        "user_id": 12345, "public_key": "APP_USR-pub", "expires_in": 15552000,
    })

    # Primero conectar para fijar el state en sesión.
    client.get("/pagos/mp/conectar", follow_redirects=False)
    with client.session_transaction() as s:
        state = s["mp_oauth_state"]

    r = client.get(f"/pagos/mp/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302

    actualizado = db.session.get(Negocio, neg.id)
    assert actualizado.mp_conectado is True
    assert actualizado.mercadopago_token == "APP_USR-neg"
    assert actualizado.mp_user_id == "12345"


def test_callback_mp_rechaza_state_invalido(client, crear_negocio, login, monkeypatch):
    """Sin state válido (CSRF), el callback no conecta nada."""
    from app.pagos import mercadopago
    from app.models.negocio import Negocio
    from app.extensions import db
    neg, dueno = crear_negocio()
    login(dueno.email)
    monkeypatch.setattr(mercadopago, "intercambiar_codigo",
                        lambda code, ru: (_ for _ in ()).throw(AssertionError("no debe llamarse")))

    r = client.get("/pagos/mp/callback?code=abc&state=falso", follow_redirects=False)
    assert r.status_code == 302
    assert db.session.get(Negocio, neg.id).mp_conectado is False


def test_aprobacion_idempotente(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, requiere_sena=True, sena_monto=Decimal("500"))
    reserva = _reserva_con_sena(neg, rec, serv, proximo_lunes)
    pago, _ = iniciar_pago_sena(reserva, serv)
    aprobar_pago(pago)
    aprobar_pago(pago)  # segunda vez no rompe
    assert Pago.query.filter_by(reserva_id=reserva.id).count() == 1
    assert pago.estado == PagoEstadoEnum.APROBADO
