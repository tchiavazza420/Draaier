"""Tests de la página de planes (ver / cambiar / cobrar)."""

from app.extensions import db
from app.models.negocio import PlanEnum, EstadoSuscripcionEnum
from app.models.pago import Pago, PagoEstadoEnum


def test_ver_planes(client, crear_negocio):
    neg, _ = crear_negocio(email="plan@test.com")
    neg.plan = PlanEnum.BASICO
    db.session.commit()
    client.post("/auth/login", data={"email": "plan@test.com", "password": "clave1234"})
    html = client.get("/panel/plan").get_data(as_text=True)
    assert "Básico" in html and "Pro" in html and "Premium" in html


def test_plan_pago_va_al_checkout_y_se_activa_al_aprobar(client, crear_negocio):
    """Elegir un plan pago NO lo activa al instante: cobra y se activa al pagar."""
    neg, _ = crear_negocio(email="pago@test.com")
    neg.plan = PlanEnum.BASICO
    db.session.commit()
    client.post("/auth/login", data={"email": "pago@test.com", "password": "clave1234"})

    # Elegir Pro -> redirige al checkout (simulado, sin credenciales MP).
    r = client.post("/panel/plan/cambiar", data={"plan": "pro"}, follow_redirects=False)
    assert r.status_code == 302
    assert "checkout-simulado" in r.headers["Location"]
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.BASICO   # todavía NO cambió (no pagó)

    pago = Pago.query.filter_by(negocio_id=neg.id, concepto="suscripcion").first()
    assert pago is not None and pago.plan_destino == "pro"
    assert pago.estado == PagoEstadoEnum.PENDIENTE

    # Simular pago aprobado -> el plan se activa.
    client.post(f"/pagos/{pago.id}/simular", data={"resultado": "aprobado"})
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.PRO
    assert neg.estado_suscripcion == EstadoSuscripcionEnum.ACTIVA
    assert neg.suscripcion_fin is not None


def test_basico_se_activa_directo(client, crear_negocio):
    """Básico es el plan de entrada con prueba: se activa sin pasar por pago."""
    neg, _ = crear_negocio(email="bas@test.com")
    neg.plan = PlanEnum.PRO
    db.session.commit()
    client.post("/auth/login", data={"email": "bas@test.com", "password": "clave1234"})
    r = client.post("/panel/plan/cambiar", data={"plan": "basico"}, follow_redirects=False)
    assert r.status_code == 302
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.BASICO


def test_plan_invalido_no_rompe(client, crear_negocio):
    neg, _ = crear_negocio(email="inv@test.com")
    neg.plan = PlanEnum.BASICO
    db.session.commit()
    client.post("/auth/login", data={"email": "inv@test.com", "password": "clave1234"})
    client.post("/panel/plan/cambiar", data={"plan": "inexistente"})
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.BASICO
