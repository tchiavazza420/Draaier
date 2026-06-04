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


def test_guardar_page_builder(client, crear_negocio):
    """Se guardan los campos del page-builder (fondo, botones, colores, cabecera, redes)."""
    neg, dueno = crear_negocio(email="pb@test.com")
    client.post("/auth/login", data={"email": "pb@test.com", "password": "clave1234"})
    client.post("/panel/recursos/nuevo", data={
        "nombre": "Juca", "capacidad": "1", "activo": "y",
        "fondo_tipo": "patron", "fondo_patron": "puntos", "fondo_color": "#fff1f2",
        "fondo_color2": "#ffe4e6",
        "boton_estilo": "contorno", "boton_forma": "redondo",
        "color_boton": "#be185d", "color_boton_texto": "#ffffff", "color_titulos": "#83edf1",
        "avatar_tamano": "grande", "mostrar_portada": "y", "portada_efecto": "fade",
        "tiktok": "@juca", "pinterest": "juca", "facebook": "https://fb.com/juca",
    })
    rec = Recurso.query.filter_by(negocio_id=neg.id, nombre="Juca").first()
    assert rec is not None
    assert rec.fondo_tipo == "patron" and rec.fondo_patron == "puntos"
    assert rec.boton_estilo == "contorno" and rec.boton_forma == "redondo"
    assert rec.color_boton == "#be185d" and rec.color_titulos == "#83edf1"
    assert rec.avatar_tamano == "grande" and rec.portada_efecto == "fade"
    assert rec.mostrar_portada is True
    assert rec.tiktok == "@juca" and rec.pinterest == "juca"
    # Y la página pública aplica el fondo con patrón.
    html = client.get(f"/{neg.slug}/recurso/{rec.slug}").get_data(as_text=True)
    assert "pb-fondo-patron" in html and "pb-patron-puntos" in html
    assert "pb-estilo-contorno" in html


def test_guardar_fuente_estilo_y_forma(client, crear_negocio):
    neg, dueno = crear_negocio(email="diseno@test.com")
    client.post("/auth/login", data={"email": "diseno@test.com", "password": "clave1234"})
    client.post("/panel/recursos/nuevo", data={
        "nombre": "Vale", "capacidad": "1", "activo": "y",
        "tipografia": "Playfair Display", "estilo_pagina": "glam", "forma_foto": "hexagono",
        "estilo_cabecera": "degradado",
    })
    rec = Recurso.query.filter_by(negocio_id=neg.id, nombre="Vale").first()
    assert rec is not None
    assert rec.tipografia == "Playfair Display"
    assert rec.estilo_pagina == "glam"
    assert rec.forma_foto == "hexagono"


def test_fuente_invalida_cae_a_default(client, crear_negocio):
    neg, _ = crear_negocio(email="badfont@test.com")
    client.post("/auth/login", data={"email": "badfont@test.com", "password": "clave1234"})
    client.post("/panel/recursos/nuevo", data={
        "nombre": "Tito", "capacidad": "1", "activo": "y",
        "tipografia": "Comic Sans Hackeada", "estilo_pagina": "marciano", "forma_foto": "raro",
    })
    rec = Recurso.query.filter_by(negocio_id=neg.id, nombre="Tito").first()
    assert rec is not None
    assert rec.tipografia == "Plus Jakarta Sans"   # default seguro
    assert rec.estilo_pagina == "minimal"
    assert rec.forma_foto == "circulo"


def test_pagina_publica_aplica_fuente_y_estilo(client, crear_negocio, crear_recurso):
    """La página pública (page-builder) aplica fuente, forma de foto, fondo y botones."""
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, nombre="Eli Glam")
    rec.tipografia = "Cormorant Garamond"
    rec.forma_foto = "rounded"
    rec.fondo_tipo = "gradiente"
    rec.boton_estilo = "contorno"
    rec.boton_forma = "redondo"
    from app.extensions import db
    db.session.commit()
    html = client.get(f"/{neg.slug}/recurso/{rec.slug}").get_data(as_text=True)
    assert "pb-foto-rounded" in html
    assert "pb-fondo-gradiente" in html
    assert "pb-estilo-contorno" in html
    assert "pb-forma-redondo" in html
    assert "Cormorant+Garamond" in html   # link de Google Fonts


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
