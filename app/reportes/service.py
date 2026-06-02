"""
app/reportes/service.py
-----------------------
Cálculo de métricas del negocio para un rango de fechas. Todo filtrado por
negocio_id (multi-tenant).

"Ingresos" = suma del precio (snapshot) de las reservas que cuentan como
ingreso: confirmadas, en proceso o finalizadas (no canceladas/ausentes).
"""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.models.reserva import Reserva, EstadoReservaEnum
from app.models.servicio import Servicio
from app.models.cliente import Cliente

ESTADOS_INGRESO = (
    EstadoReservaEnum.CONFIRMADO,
    EstadoReservaEnum.EN_PROCESO,
    EstadoReservaEnum.FINALIZADO,
)


def _rango(desde, hasta):
    ini = datetime.combine(desde, datetime.min.time())
    fin = datetime.combine(hasta, datetime.min.time()) + timedelta(days=1)
    return ini, fin


def metricas(negocio_id, desde, hasta):
    """Devuelve un dict con las métricas del rango [desde, hasta] (inclusive)."""
    ini, fin = _rango(desde, hasta)
    base = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.inicio >= ini, Reserva.inicio < fin,
    )

    total = base.count()

    # Reservas por estado.
    por_estado = dict(
        db.session.query(Reserva.estado, func.count(Reserva.id))
        .filter(Reserva.negocio_id == negocio_id, Reserva.inicio >= ini, Reserva.inicio < fin)
        .group_by(Reserva.estado).all()
    )

    # Ingresos (suma de precios de reservas que cuentan como ingreso).
    ingresos = (
        db.session.query(func.coalesce(func.sum(Reserva.precio), 0))
        .filter(Reserva.negocio_id == negocio_id, Reserva.inicio >= ini, Reserva.inicio < fin,
                Reserva.estado.in_(ESTADOS_INGRESO))
        .scalar()
    ) or Decimal("0")

    # Reservas por servicio (top 10).
    por_servicio = (
        db.session.query(Servicio.nombre, func.count(Reserva.id), func.coalesce(func.sum(Reserva.precio), 0))
        .join(Reserva, Reserva.servicio_id == Servicio.id)
        .filter(Reserva.negocio_id == negocio_id, Reserva.inicio >= ini, Reserva.inicio < fin)
        .group_by(Servicio.nombre)
        .order_by(func.count(Reserva.id).desc())
        .limit(10).all()
    )

    # Nuevos clientes en el rango.
    nuevos_clientes = (
        Cliente.query.filter(
            Cliente.negocio_id == negocio_id,
            Cliente.created_at >= ini, Cliente.created_at < fin,
        ).count()
    )

    return {
        "total": total,
        "por_estado": {e.value: c for e, c in por_estado.items()},
        "ingresos": ingresos,
        "por_servicio": [
            {"servicio": nom, "reservas": cant, "ingresos": ing}
            for nom, cant, ing in por_servicio
        ],
        "nuevos_clientes": nuevos_clientes,
    }


def reservas_para_export(negocio_id, desde, hasta):
    """Reservas del rango, para exportar a CSV."""
    ini, fin = _rango(desde, hasta)
    return (
        Reserva.query
        .filter(Reserva.negocio_id == negocio_id, Reserva.inicio >= ini, Reserva.inicio < fin)
        .order_by(Reserva.inicio.asc())
        .all()
    )
