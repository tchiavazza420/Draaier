"""
app/models/reserva.py
---------------------
Reserva: el turno reservado. Conecta cliente + servicio + recurso en una
franja de tiempo, con un estado del ciclo de vida.

Estados (del brief):
  - pendiente_pago : creada, esperando pago/seña.
  - confirmado     : confirmada (pago hecho o no requerido).
  - en_proceso     : en curso (el cliente está siendo atendido / jugando).
  - finalizado     : completada.
  - cancelado      : anulada (libera el turno).
  - ausente        : el cliente no se presentó (libera el turno).
  - reprogramado   : movida a otro horario (esta instancia ya no ocupa).

Tiempos en hora local naive (consistente con el motor de disponibilidad).
El precio se "congela" al reservar (snapshot), para que cambios futuros de
tarifa no alteren reservas ya tomadas.
"""

import enum

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class EstadoReservaEnum(enum.Enum):
    PENDIENTE_PAGO = "pendiente_pago"
    CONFIRMADO = "confirmado"
    EN_PROCESO = "en_proceso"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"
    AUSENTE = "ausente"
    REPROGRAMADO = "reprogramado"


# Estados que OCUPAN el turno (cuentan contra la capacidad del recurso).
# Los demás (cancelado, ausente, reprogramado) liberan el horario.
ESTADOS_QUE_OCUPAN = (
    EstadoReservaEnum.PENDIENTE_PAGO,
    EstadoReservaEnum.CONFIRMADO,
    EstadoReservaEnum.EN_PROCESO,
    EstadoReservaEnum.FINALIZADO,
)


class Reserva(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "reservas"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    codigo = db.Column(db.String(12), unique=True, nullable=False, index=True)

    cliente_id = db.Column(
        db.Integer, db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    servicio_id = db.Column(
        db.Integer, db.ForeignKey("servicios.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    recurso_id = db.Column(
        db.Integer, db.ForeignKey("recursos.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    inicio = db.Column(db.DateTime, nullable=False)
    fin = db.Column(db.DateTime, nullable=False)

    estado = db.Column(
        db.Enum(EstadoReservaEnum, native_enum=False, length=20),
        nullable=False, default=EstadoReservaEnum.PENDIENTE_PAGO, index=True,
    )

    # Snapshot del precio al momento de reservar.
    precio = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notas = db.Column(db.Text, nullable=True)

    # True cuando ya se le pidió la reseña al cliente (evita repetir el envío).
    resena_pedida = db.Column(db.Boolean, nullable=False, default=False)

    # --- Relaciones ---
    cliente = db.relationship("Cliente", back_populates="reservas")
    servicio = db.relationship("Servicio")
    recurso = db.relationship("Recurso")

    __table_args__ = (
        db.CheckConstraint("fin > inicio", name="ck_reserva_rango"),
        db.Index("ix_reserva_recurso_inicio", "recurso_id", "inicio"),
        db.Index("ix_reserva_negocio_inicio", "negocio_id", "inicio"),
    )

    @property
    def ocupa(self):
        """True si esta reserva cuenta contra la capacidad (ocupa el turno)."""
        return self.estado in ESTADOS_QUE_OCUPAN

    def __repr__(self):
        return f"<Reserva {self.codigo} {self.estado.value} {self.inicio} rec={self.recurso_id}>"
