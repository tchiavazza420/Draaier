"""
app/models/resena.py
--------------------
Reseña: calificación + comentario de un cliente sobre una reserva finalizada.

Reglas del brief:
  - Solo puede reseñar quien tuvo una reserva FINALIZADA (y pagada).
  - Una reseña por reserva.
  - El negocio NO puede ocultar reseñas: solo responderlas. Para ocultar,
    debe solicitarlo al Super Admin (campo solicita_ocultar). Solo el Super
    Admin puede marcar oculta=True.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class Resena(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "resenas"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    cliente_id = db.Column(
        db.Integer, db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reserva_id = db.Column(
        db.Integer, db.ForeignKey("reservas.id", ondelete="CASCADE"),
        nullable=False, unique=True,  # una reseña por reserva
    )

    calificacion = db.Column(db.SmallInteger, nullable=False)  # 1..5
    comentario = db.Column(db.Text, nullable=True)

    # Respuesta del negocio (puede responder, no ocultar).
    respuesta = db.Column(db.Text, nullable=True)
    respondida_at = db.Column(db.DateTime, nullable=True)

    # Moderación: solo el Super Admin puede ocultar. El negocio solo solicita.
    oculta = db.Column(db.Boolean, nullable=False, default=False)
    solicita_ocultar = db.Column(db.Boolean, nullable=False, default=False)

    cliente = db.relationship("Cliente")
    reserva = db.relationship("Reserva")

    __table_args__ = (
        db.CheckConstraint("calificacion >= 1 AND calificacion <= 5", name="ck_resena_calificacion"),
    )

    def __repr__(self):
        return f"<Resena {self.id} {self.calificacion}★ neg={self.negocio_id}>"
