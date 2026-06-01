"""
app/auth/utils.py
-----------------
Utilidades específicas del registro de negocios.

La lógica de slug vive en app/slugs.py (compartida). Aquí solo definimos
los slugs reservados y el generador para el slug GLOBAL del negocio.
"""

from app.slugs import generar_slug_unico_global
from app.models.negocio import Negocio


# Rutas/prefijos del sistema que no pueden ser tomados como slug de negocio.
SLUGS_RESERVADOS = {
    "auth", "panel", "admin", "api", "health", "static",
    "login", "logout", "registro", "marketplace", "super-admin",
    "pagos", "webhooks", "reservas", "recursos", "servicios", "clientes",
}


def generar_slug_unico(nombre):
    """Slug único y global para un Negocio nuevo, evitando los reservados."""
    return generar_slug_unico_global(
        Negocio, nombre, reservados=SLUGS_RESERVADOS
    )
