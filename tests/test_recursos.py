"""Tests de recursos: CRUD y aislamiento multi-tenant (anti-IDOR)."""

import pytest

from app.extensions import db
from app.models.recurso import Recurso
from app.models.tipo_recurso import TipoRecurso


def test_crear_recurso_via_panel(client, crear_negocio):
    neg, dueno = crear_negocio(email="r@test.com")
    client.post("/auth/login", data={"email": "r@test.com", "password": "clave1234"})
    client.post("/panel/recursos/tipos/nuevo", data={"nombre": "Cancha", "activo": "y"})
    tipo = TipoRecurso.query.filter_by(negocio_id=neg.id).first()
    assert tipo is not None
    r = client.post("/panel/recursos/nuevo", data={
        "tipo_recurso": str(tipo.id), "nombre": "Cancha 1", "capacidad": "1", "activo": "y",
    }, follow_redirects=False)
    assert r.status_code == 302
    assert Recurso.query.filter_by(negocio_id=neg.id, nombre="Cancha 1").count() == 1


def test_aislamiento_no_edita_recurso_ajeno(client, crear_negocio, crear_recurso):
    neg_a, dueno_a = crear_negocio(email="a@test.com")
    neg_b, dueno_b = crear_negocio(email="b@test.com")
    rec_b = crear_recurso(neg_b, nombre="De B")

    # A logueado intenta editar el recurso de B -> 404 (no revela existencia)
    client.post("/auth/login", data={"email": "a@test.com", "password": "clave1234"})
    r = client.get(f"/panel/recursos/{rec_b.id}/editar")
    assert r.status_code == 404
    r = client.post(f"/panel/recursos/{rec_b.id}/toggle")
    assert r.status_code == 404


def test_limite_agendas_por_plan(client, crear_negocio):
    """Plan Independiente (Básico) = 1 agenda: no deja crear una segunda."""
    from app.models.negocio import PlanEnum
    neg, dueno = crear_negocio(email="lim@test.com")
    neg.plan = PlanEnum.BASICO       # límite 1
    tipo = TipoRecurso(negocio_id=neg.id, nombre="T", slug="t-lim")
    db.session.add(tipo); db.session.flush()
    db.session.add(Recurso(negocio_id=neg.id, tipo_recurso_id=tipo.id,
                           nombre="Agenda 1", slug="a1", capacidad=1))
    db.session.commit()

    client.post("/auth/login", data={"email": "lim@test.com", "password": "clave1234"})
    r = client.post("/panel/recursos/nuevo", data={
        "tipo_recurso": str(tipo.id), "nombre": "Agenda 2", "capacidad": "1", "activo": "y",
    }, follow_redirects=False)
    assert r.status_code == 302 and "/panel/plan" in r.headers["Location"]
    assert Recurso.query.filter_by(negocio_id=neg.id).count() == 1


def test_capacidad_invalida_rechazada_por_form(client, crear_negocio):
    """El formulario del panel rechaza capacidad < 1 (no crea el recurso)."""
    neg, dueno = crear_negocio(email="cap@test.com")
    client.post("/auth/login", data={"email": "cap@test.com", "password": "clave1234"})
    tipo = TipoRecurso(negocio_id=neg.id, nombre="T", slug="t-cap")
    db.session.add(tipo)
    db.session.commit()
    client.post("/panel/recursos/nuevo", data={
        "tipo_recurso": str(tipo.id), "nombre": "Mala", "capacidad": "0", "activo": "y",
    })
    assert Recurso.query.filter_by(negocio_id=neg.id, nombre="Mala").count() == 0


def test_capacidad_constraint_db(crear_negocio):
    """La base de datos rechaza capacidad < 1 (CheckConstraint), backstop final."""
    neg, dueno = crear_negocio()
    tipo = TipoRecurso(negocio_id=neg.id, nombre="T", slug="t-db")
    db.session.add(tipo)
    db.session.flush()
    db.session.add(Recurso(negocio_id=neg.id, tipo_recurso_id=tipo.id,
                           nombre="Mala", slug="mala", capacidad=0))
    with pytest.raises(Exception):
        db.session.commit()
    db.session.rollback()
