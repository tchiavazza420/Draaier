"""
app/cli.py
----------
Comandos de línea de comandos personalizados (flask <comando>).

- seed-roles: crea los roles del sistema si no existen. Es idempotente:
  podés correrlo varias veces sin duplicar nada.
"""

from datetime import datetime, timedelta, date

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

    @app.cli.command("enviar-recordatorios")
    @click.option("--dias", default=1, help="Días de anticipación (default: 1 = mañana).")
    def enviar_recordatorios(dias):
        """
        Envía recordatorios de las reservas confirmadas que ocurren dentro de
        N días. Pensado para correrse una vez por día (cron/Celery beat).
        """
        from app.models.reserva import Reserva, EstadoReservaEnum
        from app.notificaciones.service import notificar_recordatorio

        objetivo = date.today() + timedelta(days=dias)
        ini = datetime.combine(objetivo, datetime.min.time())
        fin = ini + timedelta(days=1)

        reservas = (
            Reserva.query
            .filter(Reserva.estado == EstadoReservaEnum.CONFIRMADO)
            .filter(Reserva.inicio >= ini, Reserva.inicio < fin)
            .all()
        )
        enviados = 0
        for r in reservas:
            if r.cliente and r.cliente.email:
                notificar_recordatorio(r)
                enviados += 1
        click.echo(f"Recordatorios enviados: {enviados} (para {objetivo.isoformat()}).")

    @app.cli.command("crear-super-admin")
    @click.argument("email")
    @click.argument("password")
    @click.option("--nombre", default="Super Admin")
    def crear_super_admin(email, password, nombre):
        """Crea (o asegura) un usuario Super Admin de la plataforma."""
        from app.models.usuario import Usuario

        email = email.strip().lower()
        rol = Rol.query.filter_by(nombre=RolEnum.SUPER_ADMIN.value).first()
        if rol is None:
            click.echo("Falta el rol super_admin. Ejecutá primero 'flask seed-roles'.")
            return

        u = Usuario.query.filter_by(email=email).first()
        if u is None:
            u = Usuario(nombre=nombre, email=email, rol_id=rol.id, negocio_id=None, activo=True)
            u.set_password(password)
            db.session.add(u)
            accion = "creado"
        else:
            u.rol_id = rol.id
            u.negocio_id = None
            u.set_password(password)
            accion = "actualizado"
        db.session.commit()
        click.echo(f"Super Admin {accion}: {email}")
