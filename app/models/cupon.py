"""
app/models/cupon.py
-------------------
Cupon: gift card / código de descuento que el profesional crea y comparte
(por WhatsApp). El cliente abre el link y reserva con el descuento ya aplicado.

- tipo = "porcentaje" (valor 1..100) o "monto" (valor en $ fijo).
- servicio_id: si está, el cupón aplica solo a ese servicio; si es None, a todos.
- usos_max: tope de usos (None = ilimitado). vence: fecha opcional de caducidad.
"""

from decimal import Decimal
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class Cupon(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "cupones"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    codigo = db.Column(db.String(24), nullable=False, index=True)
    descripcion = db.Column(db.String(120), nullable=True)
    tipo = db.Column(db.String(12), nullable=False, default="porcentaje")  # porcentaje | monto
    valor = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    servicio_id = db.Column(
        db.Integer, db.ForeignKey("servicios.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    activo = db.Column(db.Boolean, nullable=False, default=True)
    vence = db.Column(db.DateTime(timezone=True), nullable=True)
    usos_max = db.Column(db.Integer, nullable=True)
    usos = db.Column(db.Integer, nullable=False, default=0)

    servicio = db.relationship("Servicio")

    __table_args__ = (
        db.UniqueConstraint("negocio_id", "codigo", name="uq_cupon_negocio_codigo"),
    )

    @property
    def vencido(self):
        if self.vence is None:
            return False
        v = self.vence if self.vence.tzinfo else self.vence.replace(tzinfo=timezone.utc)
        return v < datetime.now(timezone.utc)

    @property
    def agotado(self):
        return self.usos_max is not None and self.usos >= self.usos_max

    @property
    def vigente(self):
        return self.activo and not self.vencido and not self.agotado

    @property
    def etiqueta(self):
        if self.tipo == "porcentaje":
            return f"{int(self.valor)}% OFF"
        return f"${'%g' % self.valor} OFF"

    def aplica_a(self, servicio):
        return self.servicio_id is None or self.servicio_id == servicio.id

    def descuento_sobre(self, precio):
        precio = Decimal(precio or 0)
        if self.tipo == "porcentaje":
            d = precio * Decimal(self.valor) / Decimal(100)
        else:
            d = Decimal(self.valor)
        return min(d, precio)  # nunca más que el precio

    def precio_final(self, precio):
        precio = Decimal(precio or 0)
        return (precio - self.descuento_sobre(precio)).quantize(Decimal("0.01"))

    def __repr__(self):
        return f"<Cupon {self.codigo} {self.etiqueta} neg={self.negocio_id}>"
