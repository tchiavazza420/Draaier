"""
tests/test_cupones.py
---------------------
Cupones / gift cards: modelo, panel, link público y descuento aplicado al reservar.
"""

from datetime import datetime, time
from decimal import Decimal

from app.extensions import db
from app.models.cupon import Cupon
from app.models.reserva import Reserva, EstadoReservaEnum


def _cupon(neg, tipo="porcentaje", valor=20, servicio=None, **kw):
    c = Cupon(negocio_id=neg.id, codigo=kw.pop("codigo", "TEST10"),
              tipo=tipo, valor=Decimal(str(valor)),
              servicio_id=(servicio.id if servicio else None), activo=True, **kw)
    db.session.add(c); db.session.commit()
    return c


def test_modelo_descuento_porcentaje_y_monto(crear_negocio):
    neg, _ = crear_negocio()
    pct = _cupon(neg, "porcentaje", 25, codigo="PCT25")
    assert pct.etiqueta == "25% OFF"
    assert pct.precio_final(1000) == Decimal("750.00")

    fijo = _cupon(neg, "monto", 300, codigo="OFF300")
    assert fijo.precio_final(1000) == Decimal("700.00")
    # Nunca descuenta más que el precio.
    assert fijo.precio_final(200) == Decimal("0.00")


def test_panel_crear_cupon(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    login(dueno.email)
    r = client.post("/panel/cupones/nuevo", data={
        "tipo": "porcentaje", "valor": "15", "descripcion": "Promo"},
        follow_redirects=True)
    assert r.status_code == 200
    c = Cupon.query.filter_by(negocio_id=neg.id).first()
    assert c is not None and c.tipo == "porcentaje" and int(c.valor) == 15


def test_promo_guarda_sesion_y_redirige(client, crear_negocio):
    neg, _ = crear_negocio()
    _cupon(neg, "porcentaje", 20, codigo="WELCOME")
    r = client.get(f"/{neg.slug}/promo/WELCOME", follow_redirects=False)
    assert r.status_code in (301, 302)
    with client.session_transaction() as s:
        assert s["promo"]["codigo"] == "WELCOME" and s["promo"]["neg"] == neg.id


def test_promo_invalido_no_guarda(client, crear_negocio):
    neg, _ = crear_negocio()
    r = client.get(f"/{neg.slug}/promo/NOEXISTE", follow_redirects=False)
    assert r.status_code in (301, 302)
    with client.session_transaction() as s:
        assert "promo" not in s


def test_reserva_con_cupon_aplica_descuento(client, crear_negocio, crear_recurso,
                                            crear_servicio, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, nombre="Sol")
    serv = crear_servicio(neg, rec, nombre="Corte", precio=1000)  # sin seña
    _cupon(neg, "porcentaje", 20, codigo="VEINTE")

    # 1) El cliente abre el link del cupón (queda en sesión).
    client.get(f"/{neg.slug}/promo/VEINTE")
    # 2) Reserva un turno disponible (lunes 09:00).
    inicio = datetime.combine(proximo_lunes, time(9, 0)).strftime("%Y-%m-%dT%H:%M")
    r = client.post(f"/{neg.slug}/reservar", data={
        "servicio": serv.slug, "recurso": rec.id, "inicio": inicio,
        "nombre": "Ana", "email": "ana@test.com",
    }, follow_redirects=False)
    assert r.status_code in (301, 302)

    reserva = Reserva.query.filter_by(negocio_id=neg.id).first()
    assert reserva is not None
    assert reserva.estado == EstadoReservaEnum.CONFIRMADO
    assert reserva.precio == Decimal("800.00")     # 1000 - 20%
    assert reserva.cupon_codigo == "VEINTE"

    c = Cupon.query.filter_by(negocio_id=neg.id, codigo="VEINTE").first()
    assert c.usos == 1
