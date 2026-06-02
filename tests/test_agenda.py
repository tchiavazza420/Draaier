"""Tests de la agenda (eventos JSON para el calendario)."""

from datetime import datetime, time

from app.extensions import db
from app.models.reserva import EstadoReservaEnum
from app.reservas.service import crear_reserva, obtener_o_crear_cliente


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": "clave1234"})


def test_agenda_eventos_json(client, crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio(email="ag@test.com")
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec, nombre="Corte")
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@x.com")
    r = crear_reserva(neg.id, serv, rec, cli, datetime.combine(proximo_lunes, time(9, 0)),
                      estado=EstadoReservaEnum.CONFIRMADO)
    # Una cancelada (no debe aparecer)
    cli2 = obtener_o_crear_cliente(neg.id, "Bob", email="bob@x.com")
    rc = crear_reserva(neg.id, serv, rec, cli2, datetime.combine(proximo_lunes, time(11, 0)),
                       estado=EstadoReservaEnum.CONFIRMADO)
    rc.estado = EstadoReservaEnum.CANCELADO
    db.session.commit()

    _login(client, "ag@test.com")
    resp = client.get("/panel/reservas/agenda/eventos")
    assert resp.status_code == 200
    eventos = resp.get_json()
    titulos = [e["title"] for e in eventos]
    assert any("Corte" in t and "Ana" in t for t in titulos)
    assert not any("Bob" in t for t in titulos)   # cancelada excluida
    # Estructura de evento para FullCalendar
    ev = next(e for e in eventos if "Ana" in e["title"])
    assert ev["start"] and ev["end"] and ev["color"] and ev["url"]


def test_agenda_aislada_por_negocio(client, crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg_a, _ = crear_negocio(email="a@test.com")
    neg_b, _ = crear_negocio(email="b@test.com")
    rec_b = crear_recurso(neg_b)
    serv_b = crear_servicio(neg_b, rec_b, nombre="ServB")
    cli = obtener_o_crear_cliente(neg_b.id, "ClienteB", email="cb@x.com")
    crear_reserva(neg_b.id, serv_b, rec_b, cli, datetime.combine(proximo_lunes, time(9, 0)),
                  estado=EstadoReservaEnum.CONFIRMADO)

    _login(client, "a@test.com")   # negocio A no ve reservas de B
    eventos = client.get("/panel/reservas/agenda/eventos").get_json()
    assert eventos == []
