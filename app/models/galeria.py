"""
app/models/galeria.py
---------------------
GaleriaFoto: fotos que el negocio sube para mostrar en su página pública
(trabajos, local, equipo). Es un modelo tenant.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class GaleriaFoto(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "galeria_fotos"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    filename = db.Column(db.String(200), nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<GaleriaFoto {self.id} neg={self.negocio_id}>"
