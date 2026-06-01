"""
app/models/tipo_recurso.py
--------------------------
TipoRecurso: categoría de recurso que CADA negocio define a su medida.

Ejemplos según el rubro:
  - Peluquería: "Profesional"
  - Club de pádel: "Cancha"
  - Consultorio: "Box", "Consultorio"
  - Coworking: "Sala", "Escritorio"

Es un modelo tenant (hereda TenantMixin): el slug es único POR negocio,
no global, porque dos negocios pueden tener ambos un tipo "Cancha".
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class TipoRecurso(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "tipos_recurso"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin (NOT NULL, indexado, ON DELETE CASCADE).

    nombre = db.Column(db.String(60), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relaciones ---
    recursos = db.relationship(
        "Recurso",
        back_populates="tipo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Slug único dentro del negocio (no global).
        db.UniqueConstraint("negocio_id", "slug", name="uq_tiporecurso_negocio_slug"),
    )

    def __repr__(self):
        return f"<TipoRecurso {self.id} {self.nombre!r} neg={self.negocio_id}>"
