"""
app/panel/routes.py
-------------------
Área privada del negocio (requiere sesión).

El dashboard es mínimo por ahora: confirma que el login y el aislamiento
por tenant funcionan, mostrando los datos del negocio del usuario logueado.
Se irá ampliando con reservas, recursos, agenda, etc.
"""

from datetime import datetime, timezone

from flask import Blueprint, render_template
from flask_login import login_required, current_user

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
