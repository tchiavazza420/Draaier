"""
app/super_admin/routes.py
-------------------------
Panel del Super Admin (cross-tenant). A diferencia del resto del sistema,
acá NO se filtra por negocio_id: el Super Admin ve y administra todos los
negocios. Protegido por super_admin_required.

Funciones:
  - Dashboard con métricas globales.
  - Negocios: activar/desactivar, cambiar estado de suscripción y plan.
  - Moderación de reseñas: ocultar/mostrar (incluye las que el negocio
    solicitó ocultar). Solo el Super Admin puede ocultar reseñas.
"""

from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.auth.decorators import super_admin_required
from app.models.negocio import Negocio, EstadoSuscripcionEnum, PlanEnum
from app.models.reserva import Reserva
from app.models.resena import Resena
from app.models.usuario import Usuario

super_admin_bp = Blueprint("super_admin", __name__)


@super_admin_bp.route("/")
@login_required
@super_admin_required
def dashboard():
    metrics = {
        "negocios": Negocio.query.count(),
        "activos": Negocio.query.filter_by(activo=True).count(),
        "en_marketplace": Negocio.query.filter_by(visible_marketplace=True).count(),
        "reservas": Reserva.query.count(),
        "usuarios": Usuario.query.count(),
        "resenas": Resena.query.count(),
        "solicitudes_ocultar": Resena.query.filter_by(solicita_ocultar=True, oculta=False).count(),
    }
    # Distribución por estado de suscripción.
    por_estado = dict(
        db.session.query(Negocio.estado_suscripcion, func.count(Negocio.id))
        .group_by(Negocio.estado_suscripcion).all()
    )
    return render_template("super_admin/dashboard.html", m=metrics, por_estado=por_estado)


@super_admin_bp.route("/negocios")
@login_required
@super_admin_required
def negocios():
    buscar = (request.args.get("q") or "").strip()
    q = Negocio.query
    if buscar:
        like = f"%{buscar}%"
        q = q.filter((Negocio.nombre.ilike(like)) | (Negocio.slug.ilike(like)) | (Negocio.email.ilike(like)))
    lista = q.order_by(Negocio.created_at.desc()).limit(300).all()
    return render_template(
        "super_admin/negocios.html",
        negocios=lista, estados=EstadoSuscripcionEnum, planes=PlanEnum, buscar=buscar,
    )


@super_admin_bp.route("/negocios/<int:negocio_id>/toggle", methods=["POST"])
@login_required
@super_admin_required
def negocio_toggle(negocio_id):
    n = db.session.get(Negocio, negocio_id) or abort(404)
    n.activo = not n.activo
    db.session.commit()
    flash(f"Negocio '{n.nombre}' {'activado' if n.activo else 'desactivado'}.", "info")
    return redirect(request.referrer or url_for("super_admin.negocios"))


@super_admin_bp.route("/negocios/<int:negocio_id>/suscripcion", methods=["POST"])
@login_required
@super_admin_required
def negocio_suscripcion(negocio_id):
    n = db.session.get(Negocio, negocio_id) or abort(404)
    estado = request.form.get("estado")
    plan = request.form.get("plan")
    try:
        n.estado_suscripcion = EstadoSuscripcionEnum(estado)
    except ValueError:
        flash("Estado de suscripción inválido.", "danger")
        return redirect(url_for("super_admin.negocios"))

    if plan:
        try:
            n.plan = PlanEnum(plan)
        except ValueError:
            pass

    # Si se activa, extender la vigencia 30 días (gesto operativo simple).
    if n.estado_suscripcion == EstadoSuscripcionEnum.ACTIVA:
        n.suscripcion_fin = datetime.now(timezone.utc) + timedelta(days=30)

    db.session.commit()
    flash(f"Suscripción de '{n.nombre}' actualizada a {n.estado_suscripcion.value}.", "success")
    return redirect(url_for("super_admin.negocios"))


@super_admin_bp.route("/negocios/<int:negocio_id>/eliminar", methods=["POST"])
@login_required
@super_admin_required
def negocio_eliminar(negocio_id):
    """
    Elimina DEFINITIVAMENTE un negocio y todos sus datos (pensado para borrar
    locales de prueba). Acción irreversible.

    Orden de borrado: primero las reservas (las FK servicio_id/recurso_id son
    RESTRICT, así que hay que removerlas antes; esto cascadea a pagos y reseñas
    por reserva_id). Luego el negocio, cuyo ON DELETE CASCADE en negocio_id
    elimina servicios, recursos, clientes, horarios, bloqueos, galería,
    usuarios y tipos de recurso.
    """
    n = db.session.get(Negocio, negocio_id) or abort(404)

    # Confirmación: el formulario debe enviar el slug exacto del negocio.
    if (request.form.get("confirmar") or "").strip() != n.slug:
        flash("Confirmación incorrecta: escribí el slug del negocio para borrarlo.", "warning")
        return redirect(url_for("super_admin.negocios"))

    nombre = n.nombre
    Reserva.query.filter_by(negocio_id=n.id).delete(synchronize_session=False)
    db.session.delete(n)
    db.session.commit()
    flash(f"Negocio '{nombre}' eliminado por completo.", "success")
    return redirect(url_for("super_admin.negocios"))


@super_admin_bp.route("/resenas")
@login_required
@super_admin_required
def resenas():
    # Prioriza las que tienen solicitud de ocultar pendiente.
    lista = (
        Resena.query
        .order_by(Resena.solicita_ocultar.desc(), Resena.created_at.desc())
        .limit(300).all()
    )
    return render_template("super_admin/resenas.html", resenas=lista)


@super_admin_bp.route("/resenas/<int:resena_id>/ocultar", methods=["POST"])
@login_required
@super_admin_required
def resena_ocultar(resena_id):
    r = db.session.get(Resena, resena_id) or abort(404)
    r.oculta = not r.oculta
    # Al resolver, limpiamos la solicitud.
    r.solicita_ocultar = False
    db.session.commit()
    flash(f"Reseña {'oculta' if r.oculta else 'visible'}.", "info")
    return redirect(url_for("super_admin.resenas"))
