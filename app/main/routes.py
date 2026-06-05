"""
app/main/routes.py
------------------
Rutas básicas de la aplicación: home y health check.

El endpoint /health verifica que la conexión a PostgreSQL funcione
ejecutando un "SELECT 1". Sirve para diagnóstico local y, más adelante,
para los health checks de producción (load balancer, Docker, etc.).
"""

from flask import (
    Blueprint, jsonify, render_template, send_from_directory, current_app,
    Response, url_for,
)
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


@main_bp.route("/robots.txt")
def robots():
    """Permite el rastreo y apunta al sitemap."""
    sitemap_url = url_for("main.sitemap", _external=True)
    cuerpo = f"User-agent: *\nAllow: /\nDisallow: /panel/\nDisallow: /super-admin/\nSitemap: {sitemap_url}\n"
    return Response(cuerpo, mimetype="text/plain")


@main_bp.route("/sitemap.xml")
def sitemap():
    """
    Sitemap dinámico: home, marketplace y las páginas públicas de cada negocio
    visible (con sus profesionales). Ayuda al SEO e indexación.
    """
    from app.models.negocio import Negocio
    from app.models.recurso import Recurso

    urls = [
        url_for("main.index", _external=True),
        url_for("marketplace.index", _external=True),
    ]
    negocios = Negocio.query.filter_by(activo=True, visible_marketplace=True).all()
    for n in negocios:
        urls.append(url_for("publico.perfil_negocio", slug=n.slug, _external=True))
        recursos = Recurso.query.filter_by(negocio_id=n.id, activo=True).all()
        for r in recursos:
            urls.append(url_for("publico.perfil_recurso", slug=n.slug,
                                recurso_slug=r.slug, _external=True))

    items = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{items}</urlset>")
    return Response(xml, mimetype="application/xml")


@main_bp.route("/tareas/correr", methods=["GET", "POST"])
def tareas_cron():
    """
    Dispara las tareas programadas (recordatorios + vencer suscripciones).
    Pensado para un cron EXTERNO en plan free (sin Celery beat). Se protege con
    CRON_TOKEN: el llamador debe mandar el token por header 'X-Cron-Token',
    'Authorization: Bearer <token>' o query ?token=.

    Si no hay CRON_TOKEN configurado, el endpoint queda deshabilitado (404).
    """
    from flask import request, abort

    # .strip() en ambos lados: evita el 403 cuando el valor pegado en Render
    # quedó con un espacio o salto de línea final (gotcha típico).
    token_ok = (current_app.config.get("CRON_TOKEN") or "").strip()
    if not token_ok:
        abort(404)  # deshabilitado si no se configuró el secreto

    enviado = (
        request.headers.get("X-Cron-Token")
        or request.headers.get("Authorization", "").removeprefix("Bearer ")
        or request.args.get("token")
        or ""
    ).strip()
    if enviado != token_ok:
        abort(403)

    try:
        dias = int(request.args.get("dias", 1))
    except ValueError:
        dias = 1

    from app.notificaciones.service import enviar_recordatorios, pedir_resenas
    from app.suscripciones import vencer_suscripciones, avisar_vencimientos_proximos

    # Cada tarea se aísla: si una falla, las otras igual corren y el cron NO
    # se marca como fallido (siempre devolvemos 200 con el detalle de errores).
    resultado = {"ok": True, "dias": dias, "errores": []}

    def _correr(nombre, fn):
        try:
            resultado[nombre] = fn()
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("Tarea cron '%s' falló", nombre)
            resultado[nombre] = None
            resultado["errores"].append(f"{nombre}: {exc}")

    _correr("recordatorios_enviados", lambda: enviar_recordatorios(dias))
    _correr("suscripciones_vencidas", vencer_suscripciones)
    _correr("avisos_vencimiento_proximo", lambda: avisar_vencimientos_proximos(3))
    _correr("resenas_pedidas", pedir_resenas)
    return jsonify(resultado)


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
