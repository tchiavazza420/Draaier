"""Tests de la página de planes (ver / cambiar)."""

from app.extensions import db
from app.models.negocio import PlanEnum


def test_ver_y_cambiar_plan(client, crear_negocio):
    neg, _ = crear_negocio(email="plan@test.com")
    neg.plan = PlanEnum.BASICO
    db.session.commit()
    client.post("/auth/login", data={"email": "plan@test.com", "password": "clave1234"})

    # Ver planes: muestra el actual y las opciones
    html = client.get("/panel/plan").get_data(as_text=True)
    assert "Básico" in html and "Pro" in html and "Premium" in html

    # Cambiar a Pro
    r = client.post("/panel/plan/cambiar", data={"plan": "pro"}, follow_redirects=False)
    assert r.status_code == 302
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.PRO

    # Plan inválido no rompe ni cambia
    client.post("/panel/plan/cambiar", data={"plan": "inexistente"})
    db.session.refresh(neg)
    assert neg.plan == PlanEnum.PRO
