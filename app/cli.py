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
    def enviar_recordatorios_cmd(dias):
        """Envía recordatorios de reservas a N días (cron/Celery beat)."""
        from app.notificaciones.service import enviar_recordatorios
        enviados = enviar_recordatorios(dias)
        objetivo = date.today() + timedelta(days=dias)
        click.echo(f"Recordatorios enviados: {enviados} (para {objetivo.isoformat()}).")

    @app.cli.command("diag-cloudinary")
    def diag_cloudinary():
        """Prueba la conexión con Cloudinary (sube y borra un pixel de test)."""
        url = app.config.get("CLOUDINARY_URL")
        if not url:
            click.echo("CLOUDINARY_URL no está configurada: las imágenes van a disco local.")
            return
        from io import BytesIO
        from PIL import Image
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=url)
        buf = BytesIO()
        Image.new("RGB", (1, 1), (255, 0, 0)).save(buf, "PNG")
        buf.seek(0)
        try:
            res = cloudinary.uploader.upload(
                buf, folder="agenpro/_diag", public_id="ping", overwrite=True, timeout=30,
            )
            click.echo(f"OK: subida de prueba exitosa -> {res['secure_url']}")
            cloudinary.uploader.destroy("agenpro/_diag/ping")
            click.echo("OK: borrado de prueba exitoso. Cloudinary funciona.")
        except Exception as exc:
            click.echo(f"ERROR (http_code={getattr(exc, 'http_code', '?')}): {exc}")
            click.echo("Causas típicas: CLOUDINARY_URL inválida (401) o cuota agotada (420).")

    @app.cli.command("diag-whatsapp")
    @click.argument("numero")
    @click.option("--template", default=None,
                  help="Nombre de la plantilla a probar (ej. el de WHATSAPP_TEMPLATE_CONFIRMACION).")
    @click.option("--idioma", default=None,
                  help="Código de idioma de la plantilla a probar (ej. es, es_AR, es_MX). "
                       "Por defecto usa WHATSAPP_TEMPLATE_IDIOMA.")
    def diag_whatsapp(numero, template, idioma):
        """Manda un WhatsApp de prueba a NUMERO y muestra el error real de Meta."""
        from app.notificaciones import whatsapp as wa
        cfg = app.config
        idioma = idioma or cfg.get("WHATSAPP_TEMPLATE_IDIOMA", "es_AR")
        click.echo(f"WHATSAPP_PHONE_ID: {cfg.get('WHATSAPP_PHONE_ID') or '(vacío)'}")
        click.echo(f"WHATSAPP_API_VERSION: {cfg.get('WHATSAPP_API_VERSION')}")
        click.echo(f"TOKEN cargado: {'sí' if cfg.get('WHATSAPP_TOKEN') else 'NO'}")
        click.echo(f"Configurado (token+phone_id): {wa.esta_configurado()}")
        click.echo(f"Plantilla confirmación: {cfg.get('WHATSAPP_TEMPLATE_CONFIRMACION') or '(no seteada)'}")
        click.echo(f"Plantilla recordatorio: {cfg.get('WHATSAPP_TEMPLATE_RECORDATORIO') or '(no seteada)'}")
        click.echo(f"Idioma plantillas: {cfg.get('WHATSAPP_TEMPLATE_IDIOMA')}")
        click.echo("-" * 50)

        if template:
            # Probamos con 4 parámetros de ejemplo (los que manda la confirmación).
            params = ["Cliente Prueba", "Servicio", "Profesional", "01/01 a las 10:00"]
            click.echo(f"Enviando PLANTILLA '{template}' en idioma '{idioma}' con {len(params)} parámetros…")
            ok, detalle = wa._post({
                "messaging_product": "whatsapp", "to": wa._normalizar(numero),
                "type": "template",
                "template": {"name": template,
                             "language": {"code": idioma},
                             "components": [{"type": "body",
                                 "parameters": [{"type": "text", "text": p} for p in params]}]},
            })
        else:
            click.echo("Enviando mensaje de TEXTO de prueba…")
            ok, detalle = wa._post({
                "messaging_product": "whatsapp", "to": wa._normalizar(numero),
                "type": "text", "text": {"body": "Prueba de AgenPro ✅"},
            })

        if ok:
            click.echo("OK: Meta aceptó el mensaje. Si no llega, revisá abajo las notas.")
        else:
            click.echo(f"ERROR de Meta: {detalle}")
        click.echo("-" * 50)
        click.echo("Notas:")
        click.echo("- (131030) número no está en la lista de prueba → falta verificar el")
        click.echo("  negocio en Meta y agregar medio de pago (modo dev solo manda a 5 números).")
        click.echo("- (131047/131026) ventana de 24 h → el TEXTO libre no se entrega si el")
        click.echo("  cliente no te escribió antes; hay que usar PLANTILLA aprobada.")
        click.echo("- (132000/132001) parámetros de la plantilla no coinciden con los de Meta.")
        click.echo("- (190) token vencido → regenerá el token permanente.")

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

    @app.cli.command("vencer-suscripciones")
    def vencer_suscripciones_cmd():
        """Marca como VENCIDA las suscripciones expiradas (cron/Celery beat)."""
        from app.suscripciones import vencer_suscripciones
        click.echo(f"Suscripciones vencidas: {vencer_suscripciones()}.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Crea un negocio demo con recursos, servicios y reservas de la semana."""
        from datetime import time
        from app.models.negocio import Negocio, RubroEnum, PlanEnum, EstadoSuscripcionEnum
        from app.models.usuario import Usuario
        from app.models.tipo_recurso import TipoRecurso
        from app.models.recurso import Recurso
        from app.models.servicio import Servicio
        from app.models.horario import HorarioAtencion
        from app.models.cliente import Cliente
        from app.models.reserva import Reserva, EstadoReservaEnum
        from app.reservas.service import _generar_codigo

        # Limpieza previa del demo.
        existente = Usuario.query.filter_by(email="demo@demo.com").first()
        if existente:
            neg = db.session.get(Negocio, existente.negocio_id)
            db.session.delete(existente)
            if neg:
                db.session.delete(neg)
            db.session.commit()

        rol = Rol.query.filter_by(nombre=RolEnum.DUENO.value).first()
        neg = Negocio(slug="barberia-demo", nombre="Barbería Demo", rubro=RubroEnum.BARBERIA,
                      email="demo@demo.com", ciudad="Córdoba", visible_marketplace=True,
                      plan=PlanEnum.PRO, estado_suscripcion=EstadoSuscripcionEnum.TRIAL,
                      trial_fin=datetime.now() + timedelta(days=14),
                      color_primario="#7c3aed", color_secundario="#111827")
        db.session.add(neg); db.session.flush()

        dueno = Usuario(negocio_id=neg.id, rol_id=rol.id, nombre="Demo", email="demo@demo.com", activo=True)
        dueno.set_password("demo1234")
        db.session.add(dueno)

        tipo = TipoRecurso(negocio_id=neg.id, nombre="Profesional", slug="profesional")
        db.session.add(tipo); db.session.flush()
        recursos = []
        for nom, sl in [("Sofía", "sofia"), ("Julián", "julian")]:
            r = Recurso(negocio_id=neg.id, tipo_recurso_id=tipo.id, nombre=nom, slug=sl, capacidad=1)
            db.session.add(r); db.session.flush()
            recursos.append(r)
            for dia in range(6):  # lun-sáb
                db.session.add(HorarioAtencion(negocio_id=neg.id, recurso_id=r.id, dia_semana=dia,
                                               hora_inicio=time(9, 0), hora_fin=time(19, 0)))

        servicios = []
        for nom, sl, dur, pr, col in [
            ("Corte", "corte", 30, 4500, "#7c3aed"),
            ("Corte + Barba", "corte-barba", 45, 6500, "#0ea5e9"),
            ("Color", "color", 90, 12000, "#f59e0b"),
        ]:
            s = Servicio(negocio_id=neg.id, nombre=nom, slug=sl, duracion_minutos=dur, precio=pr, color=col)
            db.session.add(s); db.session.flush()
            s.recursos = recursos
            servicios.append(s)

        clientes = []
        for nom, em in [("Lucas Pérez", "lucas@x.com"), ("Mara Gómez", "mara@x.com"),
                        ("Tomás Ruiz", "tomas@x.com"), ("Vale Díaz", "vale@x.com")]:
            c = Cliente(negocio_id=neg.id, nombre=nom, email=em, telefono="+5493510000000")
            db.session.add(c); db.session.flush()
            clientes.append(c)

        # Reservas distribuidas en la semana actual.
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        plan = [
            (0, 10, 0, servicios[0], recursos[0], clientes[0], EstadoReservaEnum.CONFIRMADO),
            (0, 14, 30, servicios[1], recursos[1], clientes[1], EstadoReservaEnum.FINALIZADO),
            (1, 11, 0, servicios[2], recursos[0], clientes[2], EstadoReservaEnum.CONFIRMADO),
            (2, 16, 0, servicios[0], recursos[1], clientes[3], EstadoReservaEnum.PENDIENTE_PAGO),
            (3, 9, 30, servicios[1], recursos[0], clientes[0], EstadoReservaEnum.CONFIRMADO),
            (4, 17, 0, servicios[2], recursos[1], clientes[1], EstadoReservaEnum.CONFIRMADO),
            (5, 12, 0, servicios[0], recursos[0], clientes[2], EstadoReservaEnum.CONFIRMADO),
        ]
        for dia, h, m, serv, rec, cli, est in plan:
            ini = datetime.combine(lunes + timedelta(days=dia), time(h, m))
            db.session.add(Reserva(
                negocio_id=neg.id, codigo=_generar_codigo(), cliente_id=cli.id,
                servicio_id=serv.id, recurso_id=rec.id, inicio=ini,
                fin=ini + timedelta(minutes=serv.duracion_minutos),
                estado=est, precio=serv.precio))

        db.session.commit()
        click.echo("Demo creado: login demo@demo.com / demo1234 · /barberia-demo")
