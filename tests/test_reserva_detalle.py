"""
tests/test_reserva_detalle.py
-----------------------------
Detalle de reserva enriquecido: cobro de saldo manual y asistencia rápida.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.cliente import Cliente
from app.models.reserva import Reserva, EstadoReservaEnum
from app.models.pago import Pago, PagoEstadoEnum, ProveedorPagoEnum


def _reserva(neg, rec, serv, precio=10000, estado=EstadoReservaEnum.CONFIRMADO):
    import uuid
    cli = Cliente(negocio_id=neg.id, nombre="Cli", telefono="+5493510000000", email="c@x.com")
    db.session.add(cli); db.session.flush()
    ini = datetime.now() + timedelta(days=1)
    r = Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:10].upper(),
                cliente_id=cli.id, servicio_id=serv.id, recurso_id=rec.id,
                inicio=ini, fin=ini + timedelta(hours=1), estado=estado, precio=precio)
    db.session.add(r); db.session.commit()
    return r


def test_detalle_muestra_cobros(client, crear_negocio, crear_recurso, crear_servicio, login):
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])
    r = _reserva(neg, rec, serv, precio=10000)
    # una seña aprobada de 3000
    db.session.add(Pago(negocio_id=neg.id, reserva_id=r.id, monto=Decimal("3000"),
                        estado=PagoEstadoEnum.APROBADO, proveedor=ProveedorPagoEnum.MERCADOPAGO,
                        es_sena=True, concepto="sena"))
    db.session.commit()
    login(dueno.email)
    html = client.get(f"/panel/reservas/{r.id}").get_data(as_text=True)
    assert "Cobros" in html and "Saldo" in html
    assert "Registrar cobro del saldo" in html  # hay saldo pendiente


def test_cobrar_saldo_registra_pago(client, crear_negocio, crear_recurso, crear_servicio, login):
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])
    r = _reserva(neg, rec, serv, precio=10000)
    login(dueno.email)
    client.post(f"/panel/reservas/{r.id}/cobrar-saldo")
    pagos = Pago.query.filter_by(reserva_id=r.id, estado=PagoEstadoEnum.APROBADO).all()
    assert len(pagos) == 1 and pagos[0].monto == Decimal("10000")
    assert pagos[0].proveedor == ProveedorPagoEnum.MANUAL


def test_dashboard_avisa_turnos_por_cerrar(client, crear_negocio, crear_recurso, crear_servicio, login):
    """Turno confirmado cuyo horario ya pasó aparece como 'por cerrar' en el dashboard."""
    import uuid
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])
    cli = Cliente(negocio_id=neg.id, nombre="Pasado", telefono="+5493510000000", email="p@x.com")
    db.session.add(cli); db.session.flush()
    ini = datetime.now() - timedelta(hours=3)
    r = Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:10].upper(),
                cliente_id=cli.id, servicio_id=serv.id, recurso_id=rec.id,
                inicio=ini, fin=ini + timedelta(hours=1),
                estado=EstadoReservaEnum.CONFIRMADO, precio=5000)
    db.session.add(r); db.session.commit()
    login(dueno.email)
    html = client.get("/panel/").get_data(as_text=True)
    assert "Tenés" in html and "por cerrar" in html


def test_dashboard_no_avisa_si_finalizado(client, crear_negocio, crear_recurso, crear_servicio, login):
    """Un turno pasado pero ya finalizado no se cuenta como 'por cerrar'."""
    import uuid
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])
    cli = Cliente(negocio_id=neg.id, nombre="Cerrado", telefono="+5493510000001", email="c2@x.com")
    db.session.add(cli); db.session.flush()
    ini = datetime.now() - timedelta(hours=3)
    r = Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:10].upper(),
                cliente_id=cli.id, servicio_id=serv.id, recurso_id=rec.id,
                inicio=ini, fin=ini + timedelta(hours=1),
                estado=EstadoReservaEnum.FINALIZADO, precio=5000)
    db.session.add(r); db.session.commit()
    login(dueno.email)
    html = client.get("/panel/").get_data(as_text=True)
    assert "Tenés" not in html


def test_asistencia_rapida_atendido(client, crear_negocio, crear_recurso, crear_servicio, login):
    """Botón 'Atendido': confirmado -> finalizado directo."""
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg); serv = crear_servicio(neg, [rec])
    r = _reserva(neg, rec, serv, estado=EstadoReservaEnum.CONFIRMADO)
    login(dueno.email)
    client.post(f"/panel/reservas/{r.id}/estado", data={"estado": "finalizado"})
    db.session.refresh(r)
    assert r.estado == EstadoReservaEnum.FINALIZADO
