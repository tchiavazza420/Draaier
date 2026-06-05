"""
app/servicios/routes.py
-----------------------
CRUD de servicios en el panel del negocio.

Mismas garantías que recursos: todo filtrado por current_user.negocio_id
con los helpers tenant-aware, escritura bloqueada si la suscripción venció.

Al asignar recursos a un servicio, se validan uno por uno contra el negocio
(obtener_tenant_o_404): impide vincular recursos ajenos manipulando el form.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.slugs import generar_slug_unico_scoped
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.recurso import Recurso
from app.models.servicio import Servicio
from app.servicios.forms import ServicioForm

servicios_bp = Blueprint("servicios", __name__)

_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


def _recursos_activos():
    """Recursos activos del negocio, para poblar el select del formulario."""
    return (
        query_tenant(Recurso, _neg())
        .filter_by(activo=True)
        .order_by(Recurso.nombre)
        .all()
    )


def _resolver_recursos(ids):
    """
    Convierte una lista de ids enviada por el form en objetos Recurso,
    exigiendo que cada uno pertenezca al negocio (anti-manipulación).
    """
    seleccionados = []
    for rid in ids:
        seleccionados.append(obtener_tenant_o_404(Recurso, _neg(), rid))
    return seleccionados


@servicios_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    servicios = (
        query_tenant(Servicio, _neg())
        .order_by(Servicio.activo.desc(), Servicio.nombre.asc())
        .all()
    )
    return render_template("servicios/listar.html", servicios=servicios)


@servicios_bp.route("/senas", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def senas():
    """
    Configuración masiva de la seña: elegís monto o porcentaje y tildás a qué
    servicios aplicarla, todo de una vez (en vez de editar uno por uno).
    Los servicios tildados quedan con seña; los destildados, sin seña.
    """
    from decimal import Decimal
    servicios = (
        query_tenant(Servicio, _neg())
        .order_by(Servicio.activo.desc(), Servicio.nombre.asc())
        .all()
    )

    if request.method == "POST":
        tipo = request.form.get("sena_tipo", "monto")
        seleccionados = set(request.form.getlist("servicios", type=int))

        # Validar el valor según el tipo.
        monto = porcentaje = None
        if tipo == "porcentaje":
            try:
                porcentaje = int(request.form.get("sena_porcentaje") or 0)
            except (TypeError, ValueError):
                porcentaje = 0
            if seleccionados and not (1 <= porcentaje <= 100):
                flash("El porcentaje de la seña debe estar entre 1 y 100.", "danger")
                return render_template("servicios/senas.html", servicios=servicios)
        else:
            try:
                monto = Decimal(str(request.form.get("sena_monto") or "0"))
            except Exception:
                monto = Decimal("0")
            if seleccionados and monto <= 0:
                flash("Indicá un monto de seña válido.", "danger")
                return render_template("servicios/senas.html", servicios=servicios)

        aplicados = 0
        for s in servicios:
            if s.id in seleccionados:
                s.requiere_sena = True
                if tipo == "porcentaje":
                    s.sena_porcentaje = porcentaje
                    s.sena_monto = None
                else:
                    s.sena_monto = monto
                    s.sena_porcentaje = None
                aplicados += 1
            else:
                s.requiere_sena = False
                s.sena_monto = None
                s.sena_porcentaje = None
        db.session.commit()
        flash(f"Seña aplicada a {aplicados} servicio(s).", "success")
        return redirect(url_for("servicios.senas"))

    return render_template("servicios/senas.html", servicios=servicios)


@servicios_bp.route("/sugeridos", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def sugeridos():
    """
    Onboarding accionable: ofrece servicios típicos del rubro para crearlos de
    a varios con un clic (nombre/duración/precio editables). Cada servicio se
    asigna a todos los profesionales activos para que quede reservable.
    """
    from app.servicios.sugeridos import sugerencias_para
    sugerencias = sugerencias_para(current_user.negocio.rubro)

    if request.method == "POST":
        recursos = _recursos_activos()
        creados = 0
        for i, s in enumerate(sugerencias):
            if not request.form.get(f"sel_{i}"):
                continue
            nombre = (request.form.get(f"nombre_{i}") or s["nombre"]).strip()
            if not nombre:
                continue
            try:
                duracion = max(1, int(request.form.get(f"duracion_{i}") or s["duracion"]))
            except ValueError:
                duracion = s["duracion"]
            try:
                precio = max(0, float(request.form.get(f"precio_{i}") or s["precio"]))
            except ValueError:
                precio = s["precio"]
            servicio = Servicio(
                negocio_id=_neg(), nombre=nombre,
                slug=generar_slug_unico_scoped(Servicio, nombre, _neg()),
                duracion_minutos=duracion, precio=precio, activo=True,
            )
            servicio.recursos = recursos
            db.session.add(servicio)
            creados += 1
        db.session.commit()
        if creados:
            flash(f"¡Listo! Se crearon {creados} servicio(s).", "success")
        else:
            flash("No seleccionaste ningún servicio.", "info")
        return redirect(url_for("servicios.listar"))

    return render_template("servicios/sugeridos.html", sugerencias=sugerencias)


def _aplicar_sena(servicio, form):
    """Guarda la seña según el tipo elegido (monto fijo o porcentaje del precio)."""
    if not form.requiere_sena.data:
        servicio.sena_monto = None
        servicio.sena_porcentaje = None
        return
    if form.sena_tipo.data == "porcentaje":
        servicio.sena_porcentaje = form.sena_porcentaje.data
        servicio.sena_monto = None
    else:
        servicio.sena_monto = form.sena_monto.data
        servicio.sena_porcentaje = None


@servicios_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def nuevo():
    form = ServicioForm(recursos_disponibles=_recursos_activos())
    if form.validate_on_submit():
        servicio = Servicio(
            negocio_id=_neg(),
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(Servicio, form.nombre.data, _neg()),
            descripcion=(form.descripcion.data or "").strip() or None,
            duracion_minutos=form.duracion_minutos.data,
            precio=form.precio.data,
            color=form.color.data,
            requiere_sena=form.requiere_sena.data,
            activo=form.activo.data,
        )
        _aplicar_sena(servicio, form)
        servicio.recursos = _resolver_recursos(form.recursos.data)
        db.session.add(servicio)
        db.session.commit()
        flash(f"Servicio '{servicio.nombre}' creado.", "success")
        return redirect(url_for("servicios.listar"))
    return render_template("servicios/form.html", form=form, titulo="Nuevo servicio")


@servicios_bp.route("/<int:servicio_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def editar(servicio_id):
    servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id)
    form = ServicioForm(recursos_disponibles=_recursos_activos(), obj=servicio)
    # En GET preseleccionamos los recursos ya vinculados y el tipo de seña.
    if request.method == "GET":
        form.recursos.data = [r.id for r in servicio.recursos]
        form.sena_tipo.data = "porcentaje" if servicio.sena_porcentaje else "monto"

    if form.validate_on_submit():
        if form.nombre.data.strip() != servicio.nombre:
            servicio.slug = generar_slug_unico_scoped(
                Servicio, form.nombre.data, _neg(), exclude_id=servicio.id
            )
        servicio.nombre = form.nombre.data.strip()
        servicio.descripcion = (form.descripcion.data or "").strip() or None
        servicio.duracion_minutos = form.duracion_minutos.data
        servicio.precio = form.precio.data
        servicio.color = form.color.data
        servicio.requiere_sena = form.requiere_sena.data
        _aplicar_sena(servicio, form)
        servicio.activo = form.activo.data
        servicio.recursos = _resolver_recursos(form.recursos.data)
        db.session.commit()
        flash("Servicio actualizado.", "success")
        return redirect(url_for("servicios.listar"))
    return render_template("servicios/form.html", form=form, titulo="Editar servicio")


@servicios_bp.route("/<int:servicio_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def toggle(servicio_id):
    servicio = obtener_tenant_o_404(Servicio, _neg(), servicio_id)
    servicio.activo = not servicio.activo
    db.session.commit()
    flash(f"Servicio {'activado' if servicio.activo else 'desactivado'}.", "info")
    return redirect(url_for("servicios.listar"))
