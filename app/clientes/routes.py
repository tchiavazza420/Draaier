"""
app/clientes/routes.py
----------------------
CRM básico: listado de clientes del negocio y ficha con su historial de
reservas. Todo aislado por negocio.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.auth.decorators import rol_required
from app.models.cliente import Cliente
from app.models.reserva import Reserva

clientes_bp = Blueprint("clientes", __name__)
_ROLES_PANEL = ("dueno", "staff")


def _neg():
    return current_user.negocio_id


@clientes_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    buscar = (request.args.get("q") or "").strip()
    q = query_tenant(Cliente, _neg())
    if buscar:
        like = f"%{buscar}%"
        q = q.filter(
            (Cliente.nombre.ilike(like)) | (Cliente.email.ilike(like)) |
            (Cliente.telefono.ilike(like))
        )
    clientes = q.order_by(Cliente.nombre).limit(300).all()
    return render_template("clientes/listar.html", clientes=clientes, buscar=buscar)


@clientes_bp.route("/unificar", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
def unificar():
    """
    Fusiona clientes duplicados: si dos fichas comparten teléfono (normalizado)
    o email, las reservas y reseñas se mueven a la más antigua y la repetida se
    borra. Así el historial queda completo en UNA sola ficha.
    """
    from app.models.resena import Resena
    from app.reservas.service import _telefono_normalizado

    clientes = query_tenant(Cliente, _neg()).order_by(Cliente.id).all()
    por_clave, fusionados = {}, 0
    for c in clientes:
        claves = []
        tel = _telefono_normalizado(c.telefono)
        if tel:
            claves.append(("tel", tel))
        if c.email:
            claves.append(("email", c.email.lower()))
        principal = next((por_clave[k] for k in claves if k in por_clave), None)
        # Mismo teléfono pero emails DISTINTOS => probablemente personas que
        # comparten número (familia): no se fusionan.
        if principal is not None and c.email and principal.email \
                and c.email.lower() != principal.email.lower():
            principal = None
        if principal is None:
            for k in claves:
                por_clave.setdefault(k, c)
            continue
        # Mover el historial vía ORM (la relación tiene delete-orphan: si
        # borráramos sin mover primero, se llevaría las reservas puestas).
        for r in list(c.reservas):
            r.cliente = principal
        for rs in Resena.query.filter_by(cliente_id=c.id).all():
            rs.cliente_id = principal.id
        faltan_email = c.email if not principal.email else None
        faltan_tel = c.telefono if not principal.telefono else None
        db.session.delete(c)
        db.session.flush()  # libera el unique de email antes de copiarlo
        if faltan_email:
            principal.email = faltan_email
        if faltan_tel:
            principal.telefono = faltan_tel
        fusionados += 1
        for k in claves:
            por_clave.setdefault(k, principal)

    db.session.commit()
    if fusionados:
        flash(f"Unifiqué {fusionados} ficha(s) duplicada(s): el historial quedó completo.", "success")
    else:
        flash("No encontré duplicados (mismo teléfono o email).", "info")
    return redirect(url_for("clientes.listar"))


@clientes_bp.route("/<int:cliente_id>")
@login_required
@rol_required(*_ROLES_PANEL)
def detalle(cliente_id):
    from datetime import datetime
    from app.models.reserva import EstadoReservaEnum

    cliente = obtener_tenant_o_404(Cliente, _neg(), cliente_id)
    reservas = (
        query_tenant(Reserva, _neg())
        .filter_by(cliente_id=cliente.id)
        .order_by(Reserva.inicio.desc())
        .all()
    )
    ahora = datetime.now()
    finalizadas = [r for r in reservas if r.estado == EstadoReservaEnum.FINALIZADO]
    ausentes = [r for r in reservas if r.estado == EstadoReservaEnum.AUSENTE]
    metricas = {
        "visitas": len(finalizadas),
        "total_gastado": sum((r.precio or 0) for r in finalizadas),
        "ultima": finalizadas[0].inicio if finalizadas else None,
        "proxima": min((r.inicio for r in reservas
                        if r.inicio >= ahora and r.estado == EstadoReservaEnum.CONFIRMADO),
                       default=None),
        "total": len(reservas),
        "ausencias": len(ausentes),
    }
    return render_template("clientes/detalle.html", cliente=cliente,
                           reservas=reservas, m=metricas)
