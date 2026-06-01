"""
app/models/servicio.py
----------------------
Servicio: lo que el negocio ofrece y el cliente reserva.

Ejemplos: "Corte de pelo" (30 min, $5000), "Turno de pádel 90'" (90 min,
$8000), "Sesión de psicología" (50 min, $12000).

Relación N:N con Recurso (tabla servicio_recurso): un servicio puede ser
prestado por varios recursos (ej: el corte lo hacen 3 profesionales) y un
recurso puede prestar varios servicios. Esta relación es la base del motor
de disponibilidad: para reservar un servicio, el sistema buscará huecos en
los recursos habilitados para prestarlo.

El precio aquí es el PRECIO BASE (precio fijo). Promociones, señas, precio
por horario/temporada y cupones se construyen sobre esta base en el módulo
de precios/pagos.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


# Tabla de asociación N:N entre servicios y recursos.
# Ambos extremos son tenant-scoped, así que la relación queda implícitamente
# acotada al negocio. ON DELETE CASCADE limpia los vínculos al borrar.
servicio_recurso = db.Table(
    "servicio_recurso",
    db.Column(
        "servicio_id",
        db.ForeignKey("servicios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "recurso_id",
        db.ForeignKey("recursos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Servicio(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "servicios"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    nombre = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Duración del turno, en minutos. La usa el motor de disponibilidad.
    duracion_minutos = db.Column(db.Integer, nullable=False, default=30)

    # Precio base (fijo). Numeric para evitar errores de coma flotante en dinero.
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Color para la agenda/calendario (hex). Mejora la lectura visual.
    color = db.Column(db.String(7), nullable=False, default="#3b82f6")

    activo = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relaciones ---
    recursos = db.relationship(
        "Recurso",
        secondary=servicio_recurso,
        backref=db.backref("servicios", lazy="selectin"),
        lazy="selectin",
    )

    __table_args__ = (
        db.UniqueConstraint("negocio_id", "slug", name="uq_servicio_negocio_slug"),
        db.CheckConstraint("duracion_minutos >= 1", name="ck_servicio_duracion_min"),
        db.CheckConstraint("precio >= 0", name="ck_servicio_precio_no_negativo"),
    )

    @property
    def duracion_legible(self):
        """Devuelve la duración como '1h 30min', '45min', etc."""
        h, m = divmod(self.duracion_minutos, 60)
        partes = []
        if h:
            partes.append(f"{h}h")
        if m:
            partes.append(f"{m}min")
        return " ".join(partes) or "0min"

    def __repr__(self):
        return f"<Servicio {self.id} {self.nombre!r} {self.duracion_minutos}min neg={self.negocio_id}>"
