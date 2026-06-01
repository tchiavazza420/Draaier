"""
app/cli.py
----------
Comandos de línea de comandos personalizados (flask <comando>).

- seed-roles: crea los roles del sistema si no existen. Es idempotente:
  podés correrlo varias veces sin duplicar nada.
"""

import click

from app.extensions import db
from app.models.rol import Rol, RolEnum


# Descripciones de cada rol del sistema.
_ROLES_SISTEMA = {
    RolEnum.SUPER_ADMIN.value: "Administra toda la plataforma (cross-tenant).",
    RolEnum.DUENO.value: "Dueño del negocio. Acceso total dentro de su negocio.",
    RolEnum.STAFF.value: "Empleado o profesional con acceso limitado.",
}


def register_commands(app):
    """Registra los comandos CLI en la aplicación."""

    @app.cli.command("seed-roles")
    def seed_roles():
        """Crea los roles del sistema (idempotente)."""
        creados = 0
        for nombre, descripcion in _ROLES_SISTEMA.items():
            existente = Rol.query.filter_by(nombre=nombre).first()
            if existente is None:
                db.session.add(
                    Rol(nombre=nombre, descripcion=descripcion, es_sistema=True)
                )
                creados += 1
        db.session.commit()
        click.echo(f"Roles del sistema asegurados. Nuevos creados: {creados}")
