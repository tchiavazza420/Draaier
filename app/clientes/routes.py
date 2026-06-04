"""
app/clientes/routes.py
----------------------
CRM básico: listado de clientes del negocio y ficha con su historial de
reservas. Todo aislado por negocio.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

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
