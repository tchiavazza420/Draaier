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


def test_slug_unico_entre_negocios(app):
    """Dos negocios con el mismo nombre obtienen slugs distintos.

    Se usan clients separados porque el registro auto-loguea: con el mismo
    client, el segundo registro sería rechazado por sesión ya activa.
    """
    for email in ("a@test.com", "b@test.com"):
        c = app.test_client()
        c.post("/auth/registro", data={
            "nombre_negocio": "Nails Studio", "rubro": "manicura", "ciudad": "X",
            "nombre": "Owner", "email": email,
            "password": "clave1234", "password2": "clave1234",
        })
    slugs = {n.slug for n in Negocio.query.all()}
    assert "nails-studio" in slugs
    assert "nails-studio-2" in slugs
