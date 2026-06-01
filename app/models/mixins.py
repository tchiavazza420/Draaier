"""
app/models/mixins.py
--------------------
Mixins reutilizables para los modelos.

- TimestampMixin: agrega created_at / updated_at a cualquier modelo.
- TenantMixin: agrega la columna negocio_id (clave del aislamiento
  multi-tenant). TODO modelo que pertenezca a un negocio (recursos,
  servicios, reservas, clientes, etc.) debe heredar de TenantMixin para
  garantizar que siempre exista la columna de aislamiento.

Los mixins son clases planas (no heredan de db.Model). SQLAlchemy copia
sus columnas a cada modelo concreto que los use.
"""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    """Fecha/hora actual en UTC y timezone-aware (evita ambigüedades de zona)."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Marca de tiempo de creación y última modificación."""

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class TenantMixin:
    """
    Aislamiento multi-tenant.

    Aporta la columna negocio_id (FK a negocios.id), indexada y NOT NULL.
    Cualquier consulta sobre un modelo tenant DEBE filtrar por negocio_id;
    en pasos posteriores agregaremos un helper de query que lo aplica
    automáticamente para evitar fugas de datos entre negocios.

    Nota: Usuario NO usa este mixin porque el super_admin no pertenece a
    ningún negocio (su negocio_id es NULL). Usuario declara su propio
    negocio_id nullable.
    """

    negocio_id = db.Column(
        db.Integer,
        db.ForeignKey("negocios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
