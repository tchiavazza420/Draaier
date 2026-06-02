"""
app/panel/routes.py
-------------------
Área privada del negocio (requiere sesión).

El dashboard es mínimo por ahora: confirma que el login y el aislamiento
por tenant funcionan, mostrando los datos del negocio del usuario logueado.
Se irá ampliando con reservas, recursos, agenda, etc.
"""

from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.auth.decorators import rol_required
from app.models.negocio import RubroEnum, TemplatePublicoEnum
from app.panel.forms import NegocioConfigForm, PersonalizacionForm
from app.uploads import guardar_imagen

panel_bp = Blueprint("panel", __name__)


@panel_bp.route("/")
@login_required
def dashboard():
    """Tablero principal del negocio."""
    negocio = current_user.negocio

    # Días restantes de prueba (si está en trial).
    dias_trial_restantes = None
    if negocio and negocio.trial_fin:
        delta = negocio.trial_fin - datetime.now(timezone.utc)
        dias_trial_restantes = max(delta.days, 0)

    return render_template(
        "panel/dashboard.html",
        negocio=negocio,
        dias_trial_restantes=dias_trial_restantes,
    )


@panel_bp.route("/configuracion", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def configuracion():
    """Configuración del negocio: datos públicos y visibilidad en marketplace."""
    negocio = current_user.negocio
    form = NegocioConfigForm(obj=negocio)
    if form.validate_on_submit():
        negocio.nombre = form.nombre.data.strip()
        negocio.rubro = RubroEnum(form.rubro.data)
        negocio.ciudad = (form.ciudad.data or "").strip() or None
        negocio.telefono = (form.telefono.data or "").strip() or None
        negocio.email = form.email.data.strip().lower()
        negocio.visible_marketplace = form.visible_marketplace.data
        db.session.commit()
        flash("Configuración actualizada.", "success")
        return redirect(url_for("panel.configuracion"))
    # En GET, preseleccionar el rubro actual.
    if not form.is_submitted():
        form.rubro.data = negocio.rubro.value
    return render_template("panel/configuracion.html", form=form, negocio=negocio)


@panel_bp.route("/personalizacion", methods=["GET", "POST"])
@login_required
@rol_required("dueno")
def personalizacion():
    """Branding del negocio: logo, banner, colores, tipografía, redes, plantilla."""
    negocio = current_user.negocio
    form = PersonalizacionForm(obj=negocio)
    if form.validate_on_submit():
        try:
            ruta_logo = guardar_imagen(form.logo.data, negocio.id, "logo")
            ruta_banner = guardar_imagen(form.banner.data, negocio.id, "banner")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("panel.personalizacion"))

        if ruta_logo:
            negocio.logo_filename = ruta_logo
        if ruta_banner:
            negocio.banner_filename = ruta_banner
        negocio.color_primario = form.color_primario.data
        negocio.color_secundario = form.color_secundario.data
        negocio.tipografia = form.tipografia.data
        negocio.template_publico = TemplatePublicoEnum(form.template_publico.data)
        negocio.descripcion_publica = (form.descripcion_publica.data or "").strip() or None
        negocio.instagram = (form.instagram.data or "").strip() or None
        negocio.facebook = (form.facebook.data or "").strip() or None
        negocio.whatsapp = (form.whatsapp.data or "").strip() or None
        db.session.commit()
        flash("Personalización guardada.", "success")
        return redirect(url_for("panel.personalizacion"))

    if not form.is_submitted():
        form.template_publico.data = negocio.template_publico.value
        form.tipografia.data = negocio.tipografia
    return render_template("panel/personalizacion.html", form=form, negocio=negocio)
