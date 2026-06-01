"""
app/models/__init__.py
----------------------
Punto único de importación de modelos.

Importar todos los modelos acá garantiza que SQLAlchemy y Alembic
(Flask-Migrate) los registren al cargar el paquete. El factory llama a
register_models(), que importa este paquete.
"""

from app.models.negocio import (
    Negocio,
    RubroEnum,
    PlanEnum,
    EstadoSuscripcionEnum,
)
from app.models.rol import Rol, RolEnum
from app.models.usuario import Usuario
from app.models.tipo_recurso import TipoRecurso
from app.models.recurso import Recurso
from app.models.servicio import Servicio, servicio_recurso

__all__ = [
    "Negocio",
    "RubroEnum",
    "PlanEnum",
    "EstadoSuscripcionEnum",
    "Rol",
    "RolEnum",
    "Usuario",
    "TipoRecurso",
    "Recurso",
    "Servicio",
    "servicio_recurso",
]
