"""
tests/conftest.py
-----------------
Configuración de pytest: app de test sobre una base de datos AISLADA
(reservas_saas_test), esquema creado una vez por sesión y datos limpiados
antes de cada test. Incluye factories para armar escenarios rápido.

La base de test se deriva de DATABASE_URL agregando el sufijo '_test' al
nombre de la base, salvo que se defina TEST_DATABASE_URL.
"""

import os
from datetime import time, datetime, timedelta, date, timezone

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db as _db
from config import TestingConfig


def _test_db_uri():
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = os.environ.get("DATABASE_URL", "")
    if "/" in base:
        head, name = base.rsplit("/", 1)
        return f"{head}/{name}_test"
    raise RuntimeError("Configurá DATABASE_URL o TEST_DATABASE_URL para correr los tests.")


class TestConfig(TestingConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = _test_db_uri()
    # Permite url_for() fuera de un request (p. ej. iniciar_pago_sena en tests).
    SERVER_NAME = "localhost"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"


# ----------------------------------------------------------------------
#  App + esquema (una vez por sesión)
# ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def _ctx(app):
    """
    Cada test corre dentro de un app context, con las tablas limpias y los
    roles del sistema sembrados. Así las factories y las aserciones ORM
    funcionan sin abrir contextos manualmente.
    """
    ctx = app.app_context()
    ctx.push()
    tablas = reversed(_db.metadata.sorted_tables)
    for t in tablas:
        if t.name == "alembic_version":
            continue
        _db.session.execute(text(f'TRUNCATE TABLE "{t.name}" RESTART IDENTITY CASCADE'))
    _db.session.commit()
    _sembrar_roles()
    yield
    _db.session.remove()
    ctx.pop()


def _sembrar_roles():
    from app.models.rol import Rol, RolEnum
    for nombre in (RolEnum.SUPER_ADMIN.value, RolEnum.DUENO.value, RolEnum.STAFF.value):
        if Rol.query.filter_by(nombre=nombre).first() is None:
            _db.session.add(Rol(nombre=nombre, es_sistema=True))
    _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


# ----------------------------------------------------------------------
#  Factories (devuelven objetos ya commiteados)
# ----------------------------------------------------------------------
@pytest.fixture
def crear_negocio(app):
    """Crea un negocio + usuario dueño. Devuelve (negocio, dueno)."""
    from app.models.negocio import Negocio, RubroEnum, PlanEnum, EstadoSuscripcionEnum
    from app.models.rol import Rol, RolEnum
    from app.models.usuario import Usuario

    contador = {"n": 0}

    def _factory(nombre="Negocio Test", rubro=RubroEnum.PELUQUERIA, ciudad="Cordoba",
                 email=None, visible_marketplace=False):
        contador["n"] += 1
        email = email or f"dueno{contador['n']}@test.com"
        rol = Rol.query.filter_by(nombre=RolEnum.DUENO.value).first()
        neg = Negocio(
            slug=f"neg-{contador['n']}", nombre=nombre, rubro=rubro, email=email,
            ciudad=ciudad, visible_marketplace=visible_marketplace,
            plan=PlanEnum.BASICO, estado_suscripcion=EstadoSuscripcionEnum.TRIAL,
            trial_fin=datetime.now(timezone.utc) + timedelta(days=14),
        )
        _db.session.add(neg)
        _db.session.flush()
        dueno = Usuario(negocio_id=neg.id, rol_id=rol.id, nombre="Dueno", email=email, activo=True)
        dueno.set_password("clave1234")
        _db.session.add(dueno)
        _db.session.commit()
        return neg, dueno

    return _factory


@pytest.fixture
def crear_recurso(app):
    """Crea un recurso con un horario semanal. Devuelve el recurso."""
    from app.models.tipo_recurso import TipoRecurso
    from app.models.recurso import Recurso
    from app.models.horario import HorarioAtencion

    contador = {"n": 0}

    def _factory(negocio, nombre="Recurso", capacidad=1, dia=0,
                 hora_inicio=time(9, 0), hora_fin=time(18, 0)):
        contador["n"] += 1
        tipo = TipoRecurso(negocio_id=negocio.id, nombre="Tipo", slug=f"tipo-{contador['n']}")
        _db.session.add(tipo)
        _db.session.flush()
        rec = Recurso(negocio_id=negocio.id, tipo_recurso_id=tipo.id, nombre=nombre,
                      slug=f"rec-{contador['n']}", capacidad=capacidad, activo=True)
        _db.session.add(rec)
        _db.session.flush()
        _db.session.add(HorarioAtencion(
            negocio_id=negocio.id, recurso_id=rec.id, dia_semana=dia,
            hora_inicio=hora_inicio, hora_fin=hora_fin, activo=True))
        _db.session.commit()
        return rec

    return _factory


@pytest.fixture
def crear_servicio(app):
    """Crea un servicio asociado a recursos. Devuelve el servicio."""
    from app.models.servicio import Servicio

    contador = {"n": 0}

    def _factory(negocio, recursos, nombre="Servicio", duracion=60, precio=1000,
                 requiere_sena=False, sena_monto=None):
        contador["n"] += 1
        s = Servicio(negocio_id=negocio.id, nombre=nombre, slug=f"serv-{contador['n']}",
                     duracion_minutos=duracion, precio=precio,
                     requiere_sena=requiere_sena, sena_monto=sena_monto)
        _db.session.add(s)
        _db.session.flush()
        s.recursos = recursos if isinstance(recursos, list) else [recursos]
        _db.session.commit()
        return s

    return _factory


@pytest.fixture
def proximo_lunes():
    """Un lunes futuro (determinista para horarios dia_semana=0)."""
    hoy = date.today()
    return hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)


@pytest.fixture
def login(client):
    """Loguea a un usuario por email/password en el client de test."""
    def _login(email, password="clave1234"):
        return client.post("/auth/login", data={"email": email, "password": password},
                           follow_redirects=False)
    return _login
