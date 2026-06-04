"""
app/recursos/service.py
-----------------------
Lógica reutilizable de recursos (profesionales).

`crear_profesional_default`: en los planes individuales (Independiente) el
profesional es el propio dueño, así que no tiene sentido pedirle que lo cargue
a mano. Esta función crea un profesional por defecto con los datos que ya
ingresó (su nombre), si el negocio todavía no tiene ninguno.
"""

from app.extensions import db
from app.models.tipo_recurso import TipoRecurso
from app.models.recurso import Recurso
from app.slugs import generar_slug_unico_scoped


def crear_profesional_default(negocio_id, nombre):
    """
    Crea (si no existe ya) un profesional por defecto para el negocio, con el
    nombre dado. Devuelve el Recurso creado o el existente. No commitea.
    """
    existente = Recurso.query.filter_by(negocio_id=negocio_id).first()
    if existente is not None:
        return existente

    tipo = TipoRecurso.query.filter_by(negocio_id=negocio_id).first()
    if tipo is None:
        tipo = TipoRecurso(
            negocio_id=negocio_id, nombre="General",
            slug=generar_slug_unico_scoped(TipoRecurso, "General", negocio_id),
            activo=True,
        )
        db.session.add(tipo)
        db.session.flush()

    nombre = (nombre or "").strip() or "Profesional"
    recurso = Recurso(
        negocio_id=negocio_id, tipo_recurso_id=tipo.id, nombre=nombre,
        slug=generar_slug_unico_scoped(Recurso, nombre, negocio_id),
        capacidad=1, activo=True,
    )
    db.session.add(recurso)
    return recurso
