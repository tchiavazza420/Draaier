"""
tests/test_recurso_personalizacion.py
-------------------------------------
La personalización del profesional (frase, color de acento, habilidades, redes,
estilo de cabecera) se guarda y se muestra en su página pública.
"""

from app.models.recurso import Recurso


def test_guardar_personalizacion_completa(client, crear_negocio):
    neg, dueno = crear_negocio(email="perso@test.com")
    client.post("/auth/login", data={"email": "perso@test.com", "password": "clave1234"})

    r = client.post("/panel/recursos/nuevo", data={
        "nombre": "Sofía Pérez", "especialidad": "Colorista",
        "frase": "Tu mejor versión ✨", "descripcion": "8 años pintando.",
        "habilidades": "Balayage, Colorimetría , Peinados",
        "anios_experiencia": "8", "color_acento": "#ff5733",
        "estilo_cabecera": "solido", "instagram": "@sofi", "whatsapp": "+5491100",
        "capacidad": "1", "activo": "y",
    }, follow_redirects=False)
    assert r.status_code == 302

    rec = Recurso.query.filter_by(negocio_id=neg.id, nombre="Sofía Pérez").first()
    assert rec is not None
    assert rec.frase == "Tu mejor versión ✨"
    assert rec.color_acento == "#ff5733"
    assert rec.estilo_cabecera == "solido"
    assert rec.anios_experiencia == 8
    assert rec.habilidades_lista == ["Balayage", "Colorimetría", "Peinados"]
    assert rec.instagram == "@sofi"


def test_color_acento_vacio_hereda_negocio(client, crear_negocio):
    """Si no manda color_acento, queda None (la página usa el del negocio)."""
    neg, dueno = crear_negocio(email="hereda@test.com")
    client.post("/auth/login", data={"email": "hereda@test.com", "password": "clave1234"})
    client.post("/panel/recursos/nuevo", data={
        "nombre": "Mara", "capacidad": "1", "activo": "y",
        "color_acento": "", "estilo_cabecera": "degradado",
    })
    rec = Recurso.query.filter_by(negocio_id=neg.id, nombre="Mara").first()
    assert rec is not None
    assert rec.color_acento is None


def test_pagina_publica_muestra_personalizacion(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, nombre="Juli Barber")
    rec.especialidad = "Barbero"
    rec.frase = "Cortes con actitud"
    rec.habilidades = "Fade, Barba, Diseños"
    rec.color_acento = "#10b981"
    from app.extensions import db
    db.session.commit()

    r = client.get(f"/{neg.slug}/recurso/{rec.slug}")
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Cortes con actitud" in html
    assert "Barbero" in html
    assert "Fade" in html and "Diseños" in html
    assert "#10b981" in html  # color de acento aplicado
