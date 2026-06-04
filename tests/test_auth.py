"""Tests de autenticación y registro de negocios."""

from app.models.usuario import Usuario
from app.models.negocio import Negocio, EstadoSuscripcionEnum


def test_registro_crea_negocio_y_dueno(client):
    r = client.post("/auth/registro", data={
        "nombre_negocio": "Mi Negocio", "rubro": "barberia", "ciudad": "Cordoba",
        "nombre": "Juan", "email": "juan@test.com",
        "password": "clave1234", "password2": "clave1234",
    }, follow_redirects=False)
    assert r.status_code == 302

    u = Usuario.query.filter_by(email="juan@test.com").first()
    assert u is not None
    assert u.es_dueno
    assert u.password_hash != "clave1234"  # nunca en texto plano
    from app.extensions import db
    neg = db.session.get(Negocio, u.negocio_id)
    assert neg.slug == "mi-negocio"
    assert neg.estado_suscripcion == EstadoSuscripcionEnum.TRIAL

    # Plan individual: el profesional (el dueño) se crea automáticamente.
    from app.models.recurso import Recurso
    profesionales = Recurso.query.filter_by(negocio_id=neg.id).all()
    assert len(profesionales) == 1
    assert profesionales[0].nombre == "Juan"


def test_email_duplicado_rechazado(client, crear_negocio):
    neg, dueno = crear_negocio(email="dup@test.com")
    r = client.post("/auth/registro", data={
        "nombre_negocio": "Otro", "rubro": "spa", "ciudad": "X",
        "nombre": "Pepe", "email": "dup@test.com",
        "password": "clave1234", "password2": "clave1234",
    })
    assert b"Ya existe una cuenta" in r.data
    assert Usuario.query.filter_by(email="dup@test.com").count() == 1


def test_login_correcto_e_incorrecto(client, crear_negocio):
    neg, dueno = crear_negocio(email="login@test.com")
    # incorrecto
    r = client.post("/auth/login", data={"email": "login@test.com", "password": "mala"})
    assert "incorrectos" in r.get_data(as_text=True)
    # correcto
    r = client.post("/auth/login", data={"email": "login@test.com", "password": "clave1234"},
                    follow_redirects=False)
    assert r.status_code == 302
    assert "/panel" in r.headers["Location"]


def test_panel_requiere_login(client):
    r = client.get("/panel/", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.headers["Location"]


def test_slug_unico_entre_negocios(crear_negocio):
    """generar_slug_unico evita colisiones agregando sufijo numérico."""
    from app.extensions import db
    from app.auth.utils import generar_slug_unico

    n1, _ = crear_negocio(nombre="Nails Studio")
    n1.slug = "nails-studio"   # fijamos el slug base existente
    db.session.commit()

    assert generar_slug_unico("Nails Studio") == "nails-studio-2"
    assert generar_slug_unico("Barber Shop") == "barber-shop"
