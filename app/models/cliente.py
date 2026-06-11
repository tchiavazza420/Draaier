"""
app/models/cliente.py
---------------------
Cliente: la persona que reserva. NO es un Usuario (no accede al panel).

Es un modelo tenant: cada negocio tiene su propia cartera de clientes. En el
flujo público, al reservar se busca un cliente existente por email dentro del
negocio o se crea uno nuevo (find-or-create).

El módulo de clientes (CRM, historial, etiquetas) se ampliará más adelante;
aquí definimos lo mínimo necesario para asociar reservas.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class Cliente(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    telefono = db.Column(db.String(40), nullable=True)

    reservas = db.relationship(
        "Reserva",
        back_populates="cliente",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Un mismo email no se repite dentro del negocio (cuando hay email).
        db.UniqueConstraint("negocio_id", "email", name="uq_cliente_negocio_email"),
    )

    @property
    def es_nuevo(self):
        """True si el cliente tiene menos de 30 días en la cartera."""
        from datetime import datetime, timedelta, timezone
        if not self.created_at:
            return False
        creado = self.created_at
        if creado.tzinfo is None:
            creado = creado.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - creado < timedelta(days=30)

    def __repr__(self):
        return f"<Cliente {self.id} {self.nombre!r} neg={self.negocio_id}>"
