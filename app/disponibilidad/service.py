"""
app/disponibilidad/service.py
-----------------------------
Motor de cálculo de disponibilidad. NADA se precalcula: los slots se derivan
en tiempo real combinando horarios de atención, bloqueos, capacidad del
recurso y las reservas existentes.

Conceptos:
  - "abierto": intervalos en los que el recurso atiende ese día (HorarioAtencion).
  - "bloqueos": intervalos a restar (vacaciones, feriados, mantenimiento).
  - "ocupados": intervalos ya tomados por reservas. En el Paso 6 todavía no
    hay reservas, así que se pasa una lista vacía; el Paso 7 las inyectará.
  - "capacidad": cuántas reservas simultáneas admite el recurso por slot.

Todos los tiempos son hora local del negocio (datetime naive), coherente con
cómo se cargan horarios y bloqueos.
"""

from datetime import datetime, timedelta, time

from app.models.horario import Bloqueo


def calcular_slots(recurso, fecha, duracion_minutos,
                   paso_minutos=None, ocupados=None, ahora=None):
    """
    Slots disponibles de UN recurso en una fecha, para un turno de
    `duracion_minutos`.

    - paso_minutos: cada cuánto arranca un slot (default = duracion_minutos).
    - ocupados: lista de (inicio, fin) ya reservados en ese recurso.
    - ahora: si se pasa, se descartan los slots que empiezan antes de ese
      instante (para no ofrecer turnos en el pasado del día de hoy).

    Devuelve lista ordenada de tuplas (inicio_dt, fin_dt).
    """
    if duracion_minutos <= 0:
        return []

    paso = timedelta(minutes=paso_minutos or duracion_minutos)
    dur = timedelta(minutes=duracion_minutos)
    ocupados = ocupados or []
    capacidad = max(recurso.capacidad, 1)

    horarios = [
        h for h in recurso.horarios
        if h.activo and h.dia_semana == fecha.weekday()
    ]
    if not horarios:
        return []

    bloques = _bloqueos_del_dia(recurso, fecha)

    slots = []
    for h in sorted(horarios, key=lambda x: x.hora_inicio):
        abierto = (_combinar(fecha, h.hora_inicio), _combinar(fecha, h.hora_fin))
        for ini, fin in _restar_intervalos(abierto, bloques):
            t = ini
            while t + dur <= fin:
                s_ini, s_fin = t, t + dur
                if (ahora is None or s_ini >= ahora) and \
                        _hay_cupo(s_ini, s_fin, ocupados, capacidad):
                    slots.append((s_ini, s_fin))
                t += paso
    slots.sort()
    return slots


def calcular_slots_servicio(servicio, fecha, paso_minutos=None,
                            ocupados_por_recurso=None, ahora=None):
    """
    Disponibilidad de un SERVICIO en una fecha, agregando todos sus recursos
    habilitados (activos). Un horario se ofrece si AL MENOS un recurso está
    libre en él.

    - ocupados_por_recurso: dict {recurso_id: [(inicio, fin), ...]} con las
      reservas por recurso (vacío en el Paso 6).

    Devuelve lista ordenada de dicts:
      {"inicio": dt, "fin": dt, "recursos": [Recurso, ...]}
    ordenada por hora de inicio. Los recursos son los disponibles en ese slot.
    """
    ocupados_por_recurso = ocupados_por_recurso or {}
    agregados = {}  # inicio_dt -> {"fin": dt, "recursos": [Recurso]}

    for recurso in servicio.recursos:
        if not recurso.activo:
            continue
        ocupados = ocupados_por_recurso.get(recurso.id, [])
        for s_ini, s_fin in calcular_slots(
            recurso, fecha, servicio.duracion_minutos,
            paso_minutos=paso_minutos, ocupados=ocupados, ahora=ahora,
        ):
            entry = agregados.setdefault(s_ini, {"fin": s_fin, "recursos": []})
            entry["recursos"].append(recurso)

    return [
        {"inicio": ini, "fin": data["fin"], "recursos": data["recursos"]}
        for ini, data in sorted(agregados.items())
    ]


# ----------------------------------------------------------------------
#  Helpers internos de intervalos
# ----------------------------------------------------------------------
def _combinar(fecha, t):
    """date + time -> datetime naive."""
    return datetime.combine(fecha, t)


def _bloqueos_del_dia(recurso, fecha):
    """
    Intervalos (inicio, fin) de los bloqueos que tocan `fecha` y aplican al
    recurso: los suyos propios y los globales del negocio (recurso_id NULL).
    """
    dia_ini = datetime.combine(fecha, time.min)
    dia_fin = dia_ini + timedelta(days=1)
    bloqueos = (
        Bloqueo.query
        .filter(Bloqueo.negocio_id == recurso.negocio_id)
        .filter((Bloqueo.recurso_id == recurso.id) | (Bloqueo.recurso_id.is_(None)))
        .filter(Bloqueo.inicio < dia_fin, Bloqueo.fin > dia_ini)
        .all()
    )
    return [(b.inicio, b.fin) for b in bloqueos]


def _restar_intervalos(base, bloques):
    """
    Resta una lista de intervalos `bloques` del intervalo `base`.
    Devuelve los sub-intervalos contiguos que quedan disponibles.
    """
    resultado = [base]
    for b_ini, b_fin in bloques:
        nuevos = []
        for ini, fin in resultado:
            if b_fin <= ini or b_ini >= fin:
                nuevos.append((ini, fin))           # no se solapan
                continue
            if ini < b_ini:
                nuevos.append((ini, b_ini))          # queda pedazo a la izquierda
            if b_fin < fin:
                nuevos.append((b_fin, fin))          # queda pedazo a la derecha
        resultado = nuevos
    return resultado


def _hay_cupo(s_ini, s_fin, ocupados, capacidad):
    """True si la cantidad de reservas solapadas con el slot < capacidad."""
    solapados = sum(1 for o_ini, o_fin in ocupados if o_ini < s_fin and o_fin > s_ini)
    return solapados < capacidad
