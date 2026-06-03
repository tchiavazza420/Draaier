"""
tests/test_super_admin_eliminar.py
----------------------------------
El Super Admin puede eliminar por completo un negocio de prueba (con todos sus
datos: reservas, servicios, profesionales, etc.), y la confirmación por slug
protege de borrados accidentales.
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db as _db
from app.models.negocio import Negocio
from app.models.reserva import Reserva, EstadoReservaEnum
from app.models.servicio import Servicio
from app.models.recurso import Recurso
from app.models.cliente import Cliente


@pytest.fixture
def super_admin(app):
    """Crea (o reutiliza) un super admin y devuelve su email."""
    from app.models.rol import Rol, RolEnum
    from app.models.usuario import Usuario
    rol = Rol.query.filter_by(nombre=RolEnum.SUPER_ADMIN.value).first()
    u = Usuario(negocio_id=None, rol_id=rol.id, nombre="Root",
                email="root@admin.com", activo=True)
    u.set_password("clave1234")
    _db.session.add(u)
    _db.session.commit()
    return u.email


def _crear_reserva(negocio, recurso, servicio):
    import uuid
    cli = Cliente(negocio_id=negocio.id, nombre="Cliente", telefono="123")
    _db.session.add(cli)
    _db.session.flush()
    r = Reserva(
        negocio_id=negocio.id, codigo=uuid.uuid4().hex[:10].upper(),
        cliente_id=cli.id, servicio_id=servicio.id,
        recurso_id=recurso.id, inicio=datetime.now() + timedelta(days=1),
        fin=datetime.now() + timedelta(days=1, hours=1),
        estado=EstadoReservaEnum.CONFIRMADO,
    )
    _db.session.add(r)
    _db.session.commit()
    return r


def test_eliminar_negocio_con_datos(client, crear_negocio, crear_recurso,
                                    crear_servicio, login, super_admin):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg)
    serv = crear_servicio(neg, [rec])
    _crear_reserva(neg, rec, serv)
    nid, slug = neg.id, neg.slug

    login(super_admin)
    r = client.post(f"/super-admin/negocios/{nid}/eliminar",
                    data={"confirmar": slug}, follow_redirects=True)
    assert r.status_code == 200
    assert _db.session.get(Negocio, nid) is None
    # Cascada: no quedan datos del negocio.
    assert Reserva.query.filter_by(negocio_id=nid).count() == 0
    assert Servicio.query.filter_by(negocio_id=nid).count() == 0
    assert Recurso.query.filter_by(negocio_id=nid).count() == 0


def test_eliminar_requiere_slug_correcto(client, crear_negocio, login, super_admin):
    neg, _ = crear_negocio()
    nid = neg.id

    login(super_admin)
    r = client.post(f"/super-admin/negocios/{nid}/eliminar",
                    data={"confirmar": "slug-equivocado"}, follow_redirects=True)
    assert r.status_code == 200
    # No se borró.
    assert _db.session.get(Negocio, nid) is not None


def test_eliminar_requiere_super_admin(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    nid = neg.id
    login(dueno.email)  # dueño normal, no super admin
    r = client.post(f"/super-admin/negocios/{nid}/eliminar",
                    data={"confirmar": neg.slug})
    assert r.status_code in (302, 403)
    assert _db.session.get(Negocio, nid) is not None
