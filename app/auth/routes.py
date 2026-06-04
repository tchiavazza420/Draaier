"""
app/auth/routes.py
------------------
Rutas de autenticación: registro de negocio, login y logout.

También registra el user_loader de Flask-Login (cómo recuperar un Usuario
a partir del id guardado en la sesión).

El registro crea, en una sola transacción atómica:
  1) el Negocio (tenant) con slug único y trial de 14 días,
  2) el Usuario dueño asociado a ese negocio.
Si algo falla, se hace rollback completo: no quedan negocios "a medias".
"""

from datetime import datetime, timezone, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, login_manager
from app.models.negocio import Negocio, RubroEnum, PlanEnum, EstadoSuscripcionEnum
from app.models.rol import Rol, RolEnum
from app.models.usuario import Usuario
from app.auth.forms import RegistroNegocioForm, LoginForm
from app.auth.utils import generar_slug_unico

auth_bp = Blueprint("auth", __name__)

# Duración de la prueba gratuita (solo plan Básico), según el brief.
DIAS_TRIAL = 14


@login_manager.user_loader
def load_user(user_id):
    """Recupera el usuario de la sesión. Flask-Login lo llama en cada request."""
    return db.session.get(Usuario, int(user_id))


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    """Alta de un negocio nuevo + su usuario dueño."""
    # Si ya hay sesión activa, no tiene sentido registrarse.
    if current_user.is_authenticated:
        return redirect(url_for("panel.dashboard"))

    form = RegistroNegocioForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        # El email es único global: verificamos antes de crear nada.
        if Usuario.query.filter_by(email=email).first() is not None:
            flash("Ya existe una cuenta con ese email.", "danger")
            return render_template("auth/registro.html", form=form)

        # Rol dueño (sembrado en el Paso 2).
        rol_dueno = Rol.query.filter_by(nombre=RolEnum.DUENO.value).first()
        if rol_dueno is None:
            # Salvaguarda: si faltara el seed, lo avisamos claramente.
            flash("Error de configuración: faltan los roles del sistema. "
                  "Ejecutá 'flask seed-roles'.", "danger")
            return render_template("auth/registro.html", form=form)

        try:
            ahora = datetime.now(timezone.utc)

            negocio = Negocio(
                slug=generar_slug_unico(form.nombre_negocio.data),
                nombre=form.nombre_negocio.data.strip(),
                rubro=RubroEnum(form.rubro.data),
                email=email,
                ciudad=(form.ciudad.data or "").strip() or None,
                visible_marketplace=False,
                activo=True,
                plan=PlanEnum.BASICO,
                estado_suscripcion=EstadoSuscripcionEnum.TRIAL,
                trial_fin=ahora + timedelta(days=DIAS_TRIAL),
            )
            db.session.add(negocio)
            db.session.flush()  # obtiene negocio.id sin cerrar la transacción

            dueno = Usuario(
                negocio_id=negocio.id,
                rol_id=rol_dueno.id,
                nombre=form.nombre.data.strip(),
                email=email,
                activo=True,
            )
            dueno.set_password(form.password.data)
            db.session.add(dueno)
            db.session.flush()

            # En planes individuales el profesional es el propio dueño: lo
            # creamos automáticamente con su nombre (no hace falta cargarlo).
            from app.recursos.service import crear_profesional_default
            crear_profesional_default(negocio.id, dueno.nombre)

            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("No pudimos crear tu cuenta. Intentá nuevamente.", "danger")
            return render_template("auth/registro.html", form=form)

        # Inicia sesión automáticamente tras el registro.
        login_user(dueno)
        flash(f"¡Bienvenido/a! Tu negocio '{negocio.nombre}' fue creado. "
              f"Tenés {DIAS_TRIAL} días de prueba gratis.", "success")
        return redirect(url_for("panel.dashboard"))

    return render_template("auth/registro.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión por email + contraseña."""
    if current_user.is_authenticated:
        return redirect(url_for("panel.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()

        # Mensaje genérico: no revelamos si el email existe o no (seguridad).
        if usuario is None or not usuario.check_password(form.password.data):
            flash("Email o contraseña incorrectos.", "danger")
            return render_template("auth/login.html", form=form)

        if not usuario.activo:
            flash("Tu cuenta está desactivada. Contactá al soporte.", "warning")
            return render_template("auth/login.html", form=form)

        login_user(usuario, remember=form.remember.data)
        usuario.ultimo_acceso = datetime.now(timezone.utc)
        db.session.commit()

        # Respeta el destino original (?next=...) si es seguro (mismo sitio).
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            # El super_admin va a su panel de plataforma; el resto, al panel del negocio.
            next_page = (
                url_for("super_admin.dashboard")
                if usuario.es_super_admin else url_for("panel.dashboard")
            )
        return redirect(next_page)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesión actual."""
    logout_user()
    flash("Cerraste sesión correctamente.", "info")
    return redirect(url_for("auth.login"))
