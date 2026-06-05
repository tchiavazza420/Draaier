"""
tests/test_notif_centro.py
--------------------------
Centro de notificaciones in-app (campanita): creación en eventos, contador,
marcar leídas y rutas del panel.
"""

from datetime import datetime, time

from app.extensions import db
from app.models.reserva import EstadoReservaEnum
from app.models.notificacion import Notificacion
from app.reservas.service import (
    crear_reserva, obtener_o_crear_cliente, cancelar_reserva,
)
from app.notificaciones import centro
from app.notificaciones.service import notificar_negocio_nueva_reserva


def _reserva(neg, rec, serv, lunes, estado=EstadoReservaEnum.CONFIRMADO):
    cli = obtener_o_crear_cliente(neg.id, "Ana", email="ana@test.com", telefono="+5491100000000")
    return crear_reserva(neg.id, serv, rec, cli, datetime.combine(lunes, time(9, 0)), estado=estado)


def test_crear_y_contar_no_leidas(crear_negocio):
    neg, _ = crear_negocio()
    centro.crear(neg.id, "info", "Hola", "mensaje")
    centro.crear(neg.id, "reserva", "Otra")
    assert centro.contar_no_leidas(neg.id) == 2
    centro.marcar_todas(neg.id)
    assert centro.contar_no_leidas(neg.id) == 0


def test_nueva_reserva_genera_notificacion(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    notificar_negocio_nueva_reserva(r)   # eager -> sync
    notifs = Notificacion.query.filter_by(negocio_id=neg.id, tipo="reserva").all()
    assert len(notifs) == 1
    assert "Nuevo turno" in notifs[0].titulo
    assert notifs[0].url is not None


def test_cancelar_genera_notificacion(crear_negocio, crear_recurso, crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, rec)
    r = _reserva(neg, rec, serv, proximo_lunes)

    from app.notificaciones.service import notificar_reserva_cancelada
    cancelar_reserva(r, neg, por_cliente=True)
    notificar_reserva_cancelada(r)
    assert Notificacion.query.filter_by(negocio_id=neg.id, tipo="cancelacion").count() == 1


def test_aislamiento_por_negocio(crear_negocio):
    n1, _ = crear_negocio(email="a@x.com")
    n2, _ = crear_negocio(email="b@x.com")
    centro.crear(n1.id, "info", "Solo n1")
    assert centro.contar_no_leidas(n1.id) == 1
    assert centro.contar_no_leidas(n2.id) == 0


def test_ruta_marcar_leida_redirige(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    n = centro.crear(neg.id, "info", "Hola", url="/panel/")
    login(dueno.email)
    r = client.post(f"/panel/notificaciones/{n.id}/leer", follow_redirects=False)
    assert r.status_code in (301, 302)
    db.session.refresh(n)
    assert n.leida is True


def test_pagina_notificaciones_lista(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    centro.crear(neg.id, "reserva", "Turno de prueba", "detalle")
    login(dueno.email)
    html = client.get("/panel/notificaciones").get_data(as_text=True)
    assert "Turno de prueba" in html
