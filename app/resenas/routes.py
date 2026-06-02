"""
app/resenas/routes.py
---------------------
Gestión de reseñas en el panel: listar, responder y solicitar ocultar al
Super Admin (el negocio NO puede ocultar por su cuenta).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.auth.decorators import rol_required
from app.models.resena import Resena
from app.resenas.service import responder_resena

resenas_bp = Blueprint("resenas", __name__)
_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


@resenas_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    resenas = (
        query_tenant(Resena, _neg())
        .order_by(Resena.created_at.desc())
        .all()
    )
    return render_template("resenas/listar.html", resenas=resenas)


@resenas_bp.route("/<int:resena_id>/responder", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
def responder(resena_id):
    resena = obtener_tenant_o_404(Resena, _neg(), resena_id)
    responder_resena(resena, request.form.get("respuesta"))
    flash("Respuesta guardada.", "success")
    return redirect(url_for("resenas.listar"))


@resenas_bp.route("/<int:resena_id>/solicitar-ocultar", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
def solicitar_ocultar(resena_id):
    resena = obtener_tenant_o_404(Resena, _neg(), resena_id)
    resena.solicita_ocultar = True
    db.session.commit()
    flash("Solicitud enviada al administrador. La reseña sigue visible hasta su revisión.", "info")
    return redirect(url_for("resenas.listar"))
