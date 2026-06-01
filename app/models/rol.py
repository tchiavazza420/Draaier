"""
app/models/rol.py
-----------------
Modelo Rol = catálogo de roles del sistema.

Roles del sistema (globales, no atados a un negocio):
  - SUPER_ADMIN: administra toda la plataforma (cross-tenant).
  - DUENO:       dueño de un negocio, acceso total dentro de su negocio.
  - STAFF:       empleado/profesional con acceso limitado.

Diseño: cada Usuario tiene UN rol (rol_id). Mantener Rol como tabla (en
lugar de un simple Enum) permite, más adelante, sumar roles personalizados
por negocio y un sistema de permisos granular sin reescribir el modelo.
"""

import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class RolEnum(enum.Enum):
    """Identificadores estables de los roles del sistema."""
    SUPER_ADMIN = "super_admin"
    DUENO = "dueno"
    STAFF = "staff"


class Rol(TimestampMixin, db.Model):
    """Catálogo de roles. Se siembra con los roles del sistema."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)

    # Nombre estable y único (coincide con RolEnum.value).
    nombre = db.Column(db.String(40), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.String(160), nullable=True)

    # Marca los roles base del sistema (no editables/eliminables por usuarios).
    es_sistema = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relaciones ---
    usuarios = db.relationship("Usuario", back_populates="rol")

    def __repr__(self):
        return f"<Rol {self.nombre!r}>"
