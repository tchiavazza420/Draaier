"""
app/models/push.py
------------------
PushSubscription: suscripción Web Push (PWA) de un usuario del panel para
recibir notificaciones (por ejemplo, "te entró un turno nuevo").

Cada suscripción pertenece a un negocio (tenant) y a un usuario, y guarda el
`endpoint` + las claves (`p256dh`, `auth`) que entrega el navegador.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class PushSubscription(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)

    def to_subscription_info(self):
        """Formato que espera pywebpush."""
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }

    def __repr__(self):
        return f"<PushSubscription {self.id} neg={self.negocio_id} user={self.usuario_id}>"
