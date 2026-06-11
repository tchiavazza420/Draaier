"""
tests/test_clientes_unificar.py
-------------------------------
Clientes sin duplicar: match por teléfono normalizado al reservar y
unificación de fichas repetidas (las reservas se mueven a una sola).
"""

from app.extensions import db
from app.models.cliente import Cliente
from app.models.reserva import Reserva
from app.reservas.service import obtener_o_crear_cliente, _telefono_normalizado


def test_telefono_normalizado_variantes():
    assert _telefono_normalizado("+54 9 351 555-0000") == "3515550000"
    assert _telefono_normalizado("0351 15-555-0000") != ""  # variante con 15
    assert _telefono_normalizado("3515550000") == "3515550000"


def test_reusa_cliente_por_telefono_sin_email(crear_negocio):
    """Reserva sin email pero mismo teléfono: NO crea un duplicado."""
    neg, _ = crear_negocio()
    c1 = obtener_o_crear_cliente(neg.id, "Caro", email="caro@x.com",
                                 telefono="+54 9 351 555-0000")
    db.session.commit()
    c2 = obtener_o_crear_cliente(neg.id, "Caro", email=None,
                                 telefono="351 555 0000")
    assert c2.id == c1.id


def test_no_fusiona_familiares_con_mismo_telefono(crear_negocio):
    """Mismo teléfono pero emails distintos => personas distintas."""
    neg, _ = crear_negocio()
    c1 = obtener_o_crear_cliente(neg.id, "Mamá", email="mama@x.com",
                                 telefono="3515550000")
    db.session.commit()
    c2 = obtener_o_crear_cliente(neg.id, "Hija", email="hija@x.com",
                                 telefono="3515550000")
    assert c2.id != c1.id


def test_unificar_mueve_reservas(client, crear_negocio, crear_recurso, crear_servicio, login):
    """La unificación junta el historial en una sola ficha y borra la repetida."""
    import uuid
    from datetime import datetime, timedelta
    from app.models.reserva import EstadoReservaEnum

    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])

    a = Cliente(negocio_id=neg.id, nombre="Caro", email="caro@x.com", telefono="+5493515550000")
    b = Cliente(negocio_id=neg.id, nombre="Caro", email=None, telefono="351 555-0000")
    db.session.add_all([a, b]); db.session.flush()
    ini = datetime.now() + timedelta(days=1)
    for cli in (a, b):
        db.session.add(Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:8].upper(),
                               cliente_id=cli.id, servicio_id=serv.id, recurso_id=rec.id,
                               inicio=ini, fin=ini + timedelta(hours=1),
                               estado=EstadoReservaEnum.CONFIRMADO, precio=1000))
        ini += timedelta(hours=2)
    db.session.commit()
    a_id, b_id = a.id, b.id

    login(dueno.email)
    r = client.post("/panel/clientes/unificar", follow_redirects=True)
    assert r.status_code == 200

    assert db.session.get(Cliente, b_id) is None          # la repetida se borró
    quedan = Reserva.query.filter_by(cliente_id=a_id).count()
    assert quedan == 2                                     # historial completo
