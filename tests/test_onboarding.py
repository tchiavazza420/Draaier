"""
tests/test_onboarding.py
------------------------
El dashboard muestra la guía de primeros pasos (onboarding) según los datos
reales del negocio, y la oculta cuando está todo configurado.
"""

from app.panel.routes import _estado_onboarding


def test_onboarding_arranca_vacio(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    estado = _estado_onboarding(neg)
    assert estado["completos"] == 0
    assert estado["completo"] is False
    assert estado["porcentaje"] == 0

    login(dueno.email)
    r = client.get("/panel/")
    assert r.status_code == 200
    assert "Configurá tu salón" in r.get_data(as_text=True)


def test_onboarding_avanza_con_profesional_y_servicio(
    client, crear_negocio, crear_recurso, crear_servicio
):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)            # profesional + horario
    crear_servicio(neg, [rec])          # servicio

    estado = _estado_onboarding(neg)
    claves_ok = {p["clave"] for p in estado["pasos"] if p["ok"]}
    assert {"profesional", "servicio", "horario"} <= claves_ok
    assert estado["completos"] >= 3


def test_onboarding_completo_se_oculta(
    client, crear_negocio, crear_recurso, crear_servicio, login
):
    neg, dueno = crear_negocio(visible_marketplace=True)
    rec = crear_recurso(neg)
    crear_servicio(neg, [rec])
    neg.logo_filename = "uploads/1/logo.png"
    neg.descripcion_publica = "Salón de prueba"
    from app.extensions import db
    db.session.commit()

    estado = _estado_onboarding(neg)
    assert estado["completo"] is True
    assert estado["porcentaje"] == 100

    login(dueno.email)
    r = client.get("/panel/")
    assert r.status_code == 200
    assert "Configurá tu salón" not in r.get_data(as_text=True)
