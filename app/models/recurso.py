"""
app/models/recurso.py
---------------------
Recurso: la unidad reservable del sistema.

El sistema NO gira alrededor de "profesionales" sino de recursos genéricos:
una persona, una cancha, una sala, un consultorio, etc. Cada reserva (en el
módulo de reservas) apuntará a un Recurso.

Campos clave:
  - capacidad: cuántas reservas simultáneas admite el recurso en un mismo
    turno. Manicura/cancha = 1; clase grupal = 20. La disponibilidad real
    se calculará dinámicamente en el módulo de reservas usando este valor.
  - slug: único por negocio, alimenta la URL pública
    /slug-negocio/recurso/slug-recurso.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class Recurso(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "recursos"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    tipo_recurso_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_recurso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Cupos simultáneos por turno. >= 1.
    capacidad = db.Column(db.Integer, nullable=False, default=1)

    activo = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relaciones ---
    tipo = db.relationship("TipoRecurso", back_populates="recursos")

    __table_args__ = (
        db.UniqueConstraint("negocio_id", "slug", name="uq_recurso_negocio_slug"),
        db.CheckConstraint("capacidad >= 1", name="ck_recurso_capacidad_min"),
    )

    def __repr__(self):
        return f"<Recurso {self.id} {self.nombre!r} cap={self.capacidad} neg={self.negocio_id}>"
