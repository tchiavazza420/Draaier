"""
app/main/routes.py
------------------
Rutas básicas de la aplicación: home y health check.

El endpoint /health verifica que la conexión a PostgreSQL funcione
ejecutando un "SELECT 1". Sirve para diagnóstico local y, más adelante,
para los health checks de producción (load balancer, Docker, etc.).
"""

from flask import Blueprint, jsonify, render_template, send_from_directory, current_app
from sqlalchemy import text

from app.extensions import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/sw.js")
def service_worker():
    """
    Sirve el service worker desde la raíz para que su scope sea '/'.
    (Si se sirviera desde /static/, solo controlaría /static/.)
    """
    resp = send_from_directory(current_app.static_folder, "sw.js")
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@main_bp.route("/manifest.webmanifest")
def manifest():
    """Sirve el manifest desde la raíz."""
    resp = send_from_directory(current_app.static_folder, "manifest.webmanifest")
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


@main_bp.route("/")
def index():
    """Landing público. Se ampliará con el marketplace más adelante."""
    return render_template("home.html")


@main_bp.route("/health")
def health():
    """
    Health check: confirma que la app responde y que la base de datos
    está accesible. Devuelve 200 si todo OK, 503 si la DB falla.
    """
    db_ok = False
    error = None
    try:
        # Ejecuta una consulta trivial contra PostgreSQL.
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001 - queremos reportar cualquier fallo de DB
        error = str(exc)

    payload = {
        "app_ok": True,
        "database_ok": db_ok,
    }
    if error:
        payload["database_error"] = error

    status_code = 200 if db_ok else 503
    return jsonify(payload), status_code
