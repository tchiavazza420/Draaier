"""
app/models/notificacion.py
--------------------------
Notificacion: aviso in-app para el panel del negocio (campanita). Distinto de
las notificaciones por email/WhatsApp: esto es el historial que ve el dueño
dentro de la app (reservas, pagos, cancelaciones, reprogramaciones,
vencimientos, etc.).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


# Tipos de notificación (definen el ícono/color en la UI).
TIPOS_NOTIF = {
    "reserva": "📅",
    "pago": "💰",
    "cancelacion": "❌",
    "reprogramacion": "🔁",
    "vencimiento": "⚠️",
    "resena": "⭐",
    "info": "🔔",
}


class Notificacion(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "notificaciones"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    tipo = db.Column(db.String(20), nullable=False, default="info")
    titulo = db.Column(db.String(160), nullable=False)
    mensaje = db.Column(db.String(400), nullable=True)
    url = db.Column(db.String(300), nullable=True)
    leida = db.Column(db.Boolean, nullable=False, default=False, index=True)

    @property
    def icono(self):
        return TIPOS_NOTIF.get(self.tipo, "🔔")

    def __repr__(self):
        return f"<Notificacion {self.id} {self.tipo} neg={self.negocio_id} leida={self.leida}>"
