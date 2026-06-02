"""
app/reportes/routes.py
----------------------
Reportes del negocio: panel de métricas por rango de fechas y export CSV.
"""

import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user

from app.auth.decorators import rol_required
from app.reportes.service import metricas, reservas_para_export

reportes_bp = Blueprint("reportes", __name__)
_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


def _parse_rango():
    """Lee desde/hasta de la query; default últimos 30 días."""
    hoy = date.today()
    try:
        desde = datetime.strptime(request.args["desde"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        desde = hoy - timedelta(days=29)
    try:
        hasta = datetime.strptime(request.args["hasta"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        hasta = hoy
    if hasta < desde:
        desde, hasta = hasta, desde
    return desde, hasta


@reportes_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def index():
    desde, hasta = _parse_rango()
    datos = metricas(_neg(), desde, hasta)
    return render_template(
        "reportes/index.html",
        m=datos, desde=desde.isoformat(), hasta=hasta.isoformat(),
    )


@reportes_bp.route("/export.csv")
@login_required
@rol_required(*_ROLES_PANEL)
def export_csv():
    desde, hasta = _parse_rango()
    reservas = reservas_para_export(_neg(), desde, hasta)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Codigo", "Fecha", "Hora", "Servicio", "Recurso", "Cliente",
                     "Email", "Telefono", "Estado", "Precio"])
    for r in reservas:
        writer.writerow([
            r.codigo, r.inicio.strftime("%Y-%m-%d"), r.inicio.strftime("%H:%M"),
            r.servicio.nombre, r.recurso.nombre, r.cliente.nombre,
            r.cliente.email or "", r.cliente.telefono or "",
            r.estado.value, f"{r.precio:.2f}",
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reservas_{desde}_{hasta}.csv"},
    )
