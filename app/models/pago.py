"""
app/models/pago.py
------------------
Pago: un cobro asociado a una reserva (seña o pago total).

El cobro se hace con Mercado Pago (Checkout Pro). El campo `proveedor`
distingue además los pagos simulados (desarrollo) y los manuales (efectivo).
El `external_id` guarda el id del pago en el proveedor; `preference_id` el id
de la preferencia/checkout.

Estados:
  - pendiente : creado, esperando que el cliente pague.
  - aprobado  : pago acreditado → la reserva se confirma.
  - rechazado : pago fallido/cancelado.
  - reembolsado : devuelto.
"""

import enum

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class PagoEstadoEnum(enum.Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    REEMBOLSADO = "reembolsado"


class ProveedorPagoEnum(enum.Enum):
    MERCADOPAGO = "mercadopago"
    SIMULADO = "simulado"   # checkout interno de desarrollo (sin credenciales)
    MANUAL = "manual"       # registrado a mano por el negocio (efectivo, etc.)


class Pago(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    # Nullable: los pagos de SUSCRIPCIÓN (planes) no están atados a una reserva.
    reserva_id = db.Column(
        db.Integer, db.ForeignKey("reservas.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    # Qué se está pagando: "sena" (reserva) o "suscripcion" (plan).
    concepto = db.Column(db.String(20), nullable=False, default="sena")
    # Para suscripción: el plan que se activa al aprobarse (PlanEnum.value).
    plan_destino = db.Column(db.String(20), nullable=True)

    monto = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(
        db.Enum(PagoEstadoEnum, native_enum=False, length=20),
        nullable=False, default=PagoEstadoEnum.PENDIENTE, index=True,
    )
    proveedor = db.Column(
        db.Enum(ProveedorPagoEnum, native_enum=False, length=20),
        nullable=False, default=ProveedorPagoEnum.MERCADOPAGO,
    )
    es_sena = db.Column(db.Boolean, nullable=False, default=True)

    preference_id = db.Column(db.String(120), nullable=True)
    external_id = db.Column(db.String(120), nullable=True, index=True)
    init_point = db.Column(db.String(500), nullable=True)  # URL de checkout

    reserva = db.relationship("Reserva", backref=db.backref("pagos", lazy="selectin"))

    def __repr__(self):
        return f"<Pago {self.id} {self.estado.value} ${self.monto} reserva={self.reserva_id}>"
