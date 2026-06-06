"""
app/reservas/service.py
-----------------------
Lógica central de reservas: creación con validación de disponibilidad y
prevención de doble-reserva, además de transiciones de estado.

Anti doble-reserva (concurrencia)
---------------------------------
Dos clientes podrían pedir el mismo turno al mismo tiempo. Para evitar que
ambos lo tomen, usamos un ADVISORY LOCK de PostgreSQL por recurso:
pg_advisory_xact_lock(recurso_id). El lock:
  - serializa las reservas del MISMO recurso (las de otros recursos no se
    bloquean entre sí),
  - se libera solo al terminar la transacción (commit o rollback).
Dentro del lock recalculamos la disponibilidad real (con las reservas
vigentes como "ocupados") y recién ahí insertamos. Así es imposible superar
la capacidad del recurso, incluso bajo carga concurrente.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import text

from app.extensions import db
from app.models.cliente import Cliente
from app.models.reserva import Reserva, EstadoReservaEnum, ESTADOS_QUE_OCUPAN
from app.disponibilidad.service import calcular_slots


class ReservaError(Exception):
    """Error de dominio al reservar (mensaje apto para mostrar al usuario)."""


# ----------------------------------------------------------------------
#  Clientes (find-or-create dentro del negocio)
# ----------------------------------------------------------------------
def obtener_o_crear_cliente(negocio_id, nombre, email=None, telefono=None):
    """
    Busca un cliente por email dentro del negocio; si no existe (o no hay
    email) lo crea. Deja el objeto en la sesión y hace flush para tener id.
    """
    email = (email or "").strip().lower() or None
    telefono = (telefono or "").strip() or None
    nombre = nombre.strip()

    cliente = None
    if email:
        cliente = Cliente.query.filter_by(negocio_id=negocio_id, email=email).first()

    if cliente is None:
        cliente = Cliente(negocio_id=negocio_id, nombre=nombre, email=email, telefono=telefono)
        db.session.add(cliente)
    else:
        # Completar datos faltantes sin pisar los existentes.
        if not cliente.telefono and telefono:
            cliente.telefono = telefono
        if nombre:
            cliente.nombre = nombre

    db.session.flush()
    return cliente


# ----------------------------------------------------------------------
#  Disponibilidad ocupada por reservas
# ----------------------------------------------------------------------
def reservas_ocupadas(recurso_id, fecha, excluir_id=None):
    """
    Intervalos (inicio, fin) ocupados por reservas vigentes de un recurso en
    una fecha. Solo cuentan los estados que ocupan (ver ESTADOS_QUE_OCUPAN).
    """
    dia_ini = datetime.combine(fecha, datetime.min.time())
    dia_fin = dia_ini + timedelta(days=1)
    q = (
        Reserva.query
        .filter(Reserva.recurso_id == recurso_id)
        .filter(Reserva.estado.in_(ESTADOS_QUE_OCUPAN))
        .filter(Reserva.inicio < dia_fin, Reserva.fin > dia_ini)
    )
    if excluir_id is not None:
        q = q.filter(Reserva.id != excluir_id)
    return [(r.inicio, r.fin) for r in q.all()]


def ocupados_por_servicio(servicio, fecha):
    """
    Dict {recurso_id: [(inicio, fin), ...]} con las reservas vigentes de cada
    recurso del servicio en una fecha. Se inyecta en calcular_slots_servicio
    para que la disponibilidad mostrada descuente lo ya reservado.
    """
    return {rec.id: reservas_ocupadas(rec.id, fecha) for rec in servicio.recursos}


# ----------------------------------------------------------------------
#  Creación de reserva
# ----------------------------------------------------------------------
def crear_reserva(negocio_id, servicio, recurso, cliente, inicio,
                  estado=EstadoReservaEnum.PENDIENTE_PAGO, notas=None,
                  precio=None, cupon_codigo=None):
    """
    Crea una reserva validando que el turno esté realmente disponible.
    Lanza ReservaError si algo no cuadra. Hace commit al final.

    `precio`: si se pasa, congela ese valor (ej. precio con descuento de cupón);
    si no, usa el precio del servicio. `cupon_codigo`: referencia del cupón usado.

    Precondición: servicio, recurso y cliente pertenecen al negocio (lo
    garantizan las rutas con los helpers tenant-aware).
    """
    # 1) El recurso debe prestar ese servicio.
    if recurso not in servicio.recursos:
        raise ReservaError("El recurso seleccionado no presta este servicio.")

    fin = inicio + timedelta(minutes=servicio.duracion_minutos)

    # 2) Lock por recurso: serializa reservas concurrentes del mismo recurso.
    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:k)"), {"k": int(recurso.id)}
    )

    # 3) Recalcular disponibilidad REAL ya con el lock tomado.
    ocupados = reservas_ocupadas(recurso.id, inicio.date())
    slots = calcular_slots(
        recurso, inicio.date(), servicio.duracion_minutos, ocupados=ocupados
    )
    inicios_disponibles = {s[0] for s in slots}
    if inicio not in inicios_disponibles:
        raise ReservaError("Ese turno ya no está disponible. Probá con otro horario.")

    # 4) Crear la reserva (precio congelado como snapshot).
    reserva = Reserva(
        negocio_id=negocio_id,
        codigo=_generar_codigo(),
        cliente_id=cliente.id,
        servicio_id=servicio.id,
        recurso_id=recurso.id,
        inicio=inicio,
        fin=fin,
        estado=estado,
        precio=servicio.precio if precio is None else precio,
        cupon_codigo=cupon_codigo,
        notas=(notas or "").strip() or None,
    )
    db.session.add(reserva)
    db.session.commit()
    return reserva


# ----------------------------------------------------------------------
#  Transiciones de estado
# ----------------------------------------------------------------------
# Transiciones permitidas desde cada estado.
_TRANSICIONES = {
    EstadoReservaEnum.PENDIENTE_PAGO: {
        EstadoReservaEnum.CONFIRMADO, EstadoReservaEnum.CANCELADO,
    },
    EstadoReservaEnum.CONFIRMADO: {
        EstadoReservaEnum.EN_PROCESO, EstadoReservaEnum.FINALIZADO,
        EstadoReservaEnum.CANCELADO, EstadoReservaEnum.AUSENTE,
        EstadoReservaEnum.REPROGRAMADO,
    },
    EstadoReservaEnum.EN_PROCESO: {
        EstadoReservaEnum.FINALIZADO, EstadoReservaEnum.CANCELADO,
    },
    EstadoReservaEnum.FINALIZADO: set(),
    EstadoReservaEnum.CANCELADO: set(),
    EstadoReservaEnum.AUSENTE: set(),
    EstadoReservaEnum.REPROGRAMADO: set(),
}


def cambiar_estado(reserva, nuevo_estado):
    """Aplica una transición de estado válida o lanza ReservaError."""
    if nuevo_estado == reserva.estado:
        return reserva
    permitidas = _TRANSICIONES.get(reserva.estado, set())
    if nuevo_estado not in permitidas:
        raise ReservaError(
            f"No se puede pasar de '{reserva.estado.value}' a '{nuevo_estado.value}'."
        )
    reserva.estado = nuevo_estado
    db.session.commit()
    return reserva


# ----------------------------------------------------------------------
#  Reprogramación
# ----------------------------------------------------------------------
def reprogramar_reserva(reserva, nuevo_inicio):
    """
    Mueve la reserva a `nuevo_inicio` validando disponibilidad real del recurso
    (excluyéndose a sí misma). Mantiene el estado. Lanza ReservaError si el
    nuevo horario no está disponible o el estado no permite reprogramar.
    """
    if reserva.estado not in (EstadoReservaEnum.PENDIENTE_PAGO,
                              EstadoReservaEnum.CONFIRMADO):
        raise ReservaError("Esta reserva no se puede reprogramar.")

    servicio = reserva.servicio
    recurso = reserva.recurso
    fin = nuevo_inicio + timedelta(minutes=servicio.duracion_minutos)

    db.session.execute(
        text("SELECT pg_advisory_xact_lock(:k)"), {"k": int(recurso.id)}
    )
    ocupados = reservas_ocupadas(recurso.id, nuevo_inicio.date(), excluir_id=reserva.id)
    slots = calcular_slots(
        recurso, nuevo_inicio.date(), servicio.duracion_minutos, ocupados=ocupados
    )
    if nuevo_inicio not in {s[0] for s in slots}:
        raise ReservaError("Ese horario no está disponible. Probá con otro.")

    reserva.inicio = nuevo_inicio
    reserva.fin = fin
    # Al reprogramar, se vuelve a pedir confirmación de asistencia.
    reserva.asistencia_confirmada = False
    db.session.commit()
    return reserva


# ----------------------------------------------------------------------
#  Cancelación (con política de reembolso de seña)
# ----------------------------------------------------------------------
def horas_hasta(reserva, ahora=None):
    """Horas (float) que faltan para el inicio del turno (hora local naive)."""
    ahora = ahora or datetime.now()
    return (reserva.inicio - ahora).total_seconds() / 3600.0


def dentro_de_plazo(reserva, horas, ahora=None):
    """
    True si todavía falta al menos `horas` para el turno (permite la acción).
    `horas` None => no permitido; 0 => permitido siempre que no haya empezado.
    """
    if horas is None:
        return False
    return horas_hasta(reserva, ahora) >= horas


def cliente_puede_gestionar(reserva, negocio, ahora=None):
    """¿El cliente puede cancelar/reprogramar online según la política?"""
    if reserva.estado not in (EstadoReservaEnum.PENDIENTE_PAGO,
                              EstadoReservaEnum.CONFIRMADO):
        return False
    return dentro_de_plazo(reserva, negocio.cancelacion_horas, ahora)


def cancelar_reserva(reserva, negocio=None, por_cliente=False, ahora=None):
    """
    Cancela la reserva (estado CANCELADO) y, si corresponde por la política de
    reembolso del negocio, marca la seña pagada como REEMBOLSADA.
    Devuelve (reserva, reembolsada: bool).
    """
    from app.models.pago import Pago, PagoEstadoEnum
    if reserva.estado in (EstadoReservaEnum.CANCELADO, EstadoReservaEnum.FINALIZADO,
                          EstadoReservaEnum.AUSENTE, EstadoReservaEnum.REPROGRAMADO):
        raise ReservaError("Esta reserva no se puede cancelar.")

    reembolsada = False
    if negocio is not None and dentro_de_plazo(reserva, negocio.reembolso_sena_horas, ahora):
        senas = [p for p in reserva.pagos
                 if p.es_sena and p.estado == PagoEstadoEnum.APROBADO]
        for p in senas:
            p.estado = PagoEstadoEnum.REEMBOLSADO
            reembolsada = True

    reserva.estado = EstadoReservaEnum.CANCELADO
    db.session.commit()
    return reserva, reembolsada


def _generar_codigo():
    """Código corto y único para referencia pública de la reserva."""
    for _ in range(10):
        codigo = uuid.uuid4().hex[:8].upper()
        if Reserva.query.filter_by(codigo=codigo).first() is None:
            return codigo
    # Extremadamente improbable: fallback más largo.
    return uuid.uuid4().hex[:12].upper()
