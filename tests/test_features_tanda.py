"""
tests/test_features_tanda.py
----------------------------
Tanda de mejoras: métricas del día (dashboard), Open Graph con foto del
profesional y white-label (página pública sin barra de AgenPro) gated por plan.
"""

from datetime import datetime, timedelta

from app.extensions import db
from app.models.negocio import PlanEnum
from app.models.reserva import Reserva, EstadoReservaEnum
from app.models.cliente import Cliente


def _reserva_hoy(neg, rec, serv, hora=10, estado=EstadoReservaEnum.CONFIRMADO, precio=4500):
    import uuid
    cli = Cliente(negocio_id=neg.id, nombre="Cli", telefono="123")
    db.session.add(cli); db.session.flush()
    ini = datetime.now().replace(hour=hora, minute=0, second=0, microsecond=0)
    r = Reserva(negocio_id=neg.id, codigo=uuid.uuid4().hex[:10].upper(),
                cliente_id=cli.id, servicio_id=serv.id, recurso_id=rec.id,
                inicio=ini, fin=ini + timedelta(hours=1), estado=estado, precio=precio)
    db.session.add(r); db.session.commit()
    return r


# ---------- #5 métricas del día ----------
def test_dashboard_metricas_del_dia(client, crear_negocio, crear_recurso, crear_servicio, login):
    neg, dueno = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, [rec])
    _reserva_hoy(neg, rec, serv, precio=5000)
    login(dueno.email)
    html = client.get("/panel/").get_data(as_text=True)
    assert "Turnos hoy" in html
    assert "Ingresos del día" in html
    assert "Próximos turnos" in html


# ---------- #14 Open Graph con foto del profesional ----------
def test_og_usa_foto_del_profesional(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, nombre="Sofi")
    rec.foto_filename = "uploads/1/profesional-ab.webp"
    db.session.commit()
    html = client.get(f"/{neg.slug}/recurso/{rec.slug}").get_data(as_text=True)
    assert 'property="og:image"' in html
    assert "uploads/1/profesional-ab.webp" in html


# ---------- #3 white-label gated ----------
def test_white_label_premium_oculta_navbar(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.PREMIUM
    db.session.commit()
    rec = crear_recurso(neg, nombre="Vale")
    html = client.get(f"/{neg.slug}/recurso/{rec.slug}").get_data(as_text=True)
    # La marca AgenPro del navbar no aparece (página white-label).
    assert "Crear cuenta" not in html
    assert 'class="navbar' not in html


def test_sin_white_label_basico_muestra_navbar(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio()
    neg.plan = PlanEnum.BASICO
    db.session.commit()
    rec = crear_recurso(neg, nombre="Vale")
    html = client.get(f"/{neg.slug}/recurso/{rec.slug}").get_data(as_text=True)
    assert 'class="navbar' in html
