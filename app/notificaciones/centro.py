"""
app/notificaciones/centro.py
----------------------------
Centro de notificaciones in-app (campanita del panel). Crea y consulta los
avisos que ve el dueño dentro de la app. Es tolerante a fallos: si crear una
notificación falla, nunca debe romper el flujo principal (reserva, pago, etc.).
"""

from flask import current_app

from app.extensions import db
from app.models.notificacion import Notificacion

# Cuántas notificaciones conservar por negocio (se podan las más viejas leídas).
_MAX_POR_NEGOCIO = 100


def crear(negocio_id, tipo, titulo, mensaje=None, url=None):
    """Crea una notificación in-app. No lanza: loguea y sigue ante un error."""
    if not negocio_id:
        return None
    try:
        n = Notificacion(
            negocio_id=negocio_id, tipo=tipo, titulo=titulo,
            mensaje=(mensaje or None), url=(url or None), leida=False,
        )
        db.session.add(n)
        db.session.commit()
        _podar(negocio_id)
        return n
    except Exception:
        db.session.rollback()
        current_app.logger.exception("No se pudo crear notificación in-app")
        return None


def _podar(negocio_id):
    """Borra las notificaciones leídas más viejas si se supera el tope."""
    try:
        total = Notificacion.query.filter_by(negocio_id=negocio_id).count()
        if total <= _MAX_POR_NEGOCIO:
            return
        sobrantes = (
            Notificacion.query
            .filter_by(negocio_id=negocio_id, leida=True)
            .order_by(Notificacion.created_at.asc())
            .limit(total - _MAX_POR_NEGOCIO)
            .all()
        )
        for n in sobrantes:
            db.session.delete(n)
        db.session.commit()
    except Exception:
        db.session.rollback()


def contar_no_leidas(negocio_id):
    if not negocio_id:
        return 0
    return Notificacion.query.filter_by(negocio_id=negocio_id, leida=False).count()


def listar(negocio_id, limite=20):
    if not negocio_id:
        return []
    return (
        Notificacion.query
        .filter_by(negocio_id=negocio_id)
        .order_by(Notificacion.leida.asc(), Notificacion.created_at.desc())
        .limit(limite)
        .all()
    )


def marcar_leida(negocio_id, notif_id):
    n = Notificacion.query.filter_by(id=notif_id, negocio_id=negocio_id).first()
    if n and not n.leida:
        n.leida = True
        db.session.commit()
    return n


def marcar_todas(negocio_id):
    Notificacion.query.filter_by(negocio_id=negocio_id, leida=False).update({"leida": True})
    db.session.commit()
