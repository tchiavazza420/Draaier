"""Tests del motor de disponibilidad (cálculo de slots)."""

from datetime import time, datetime, timedelta

from app.models.horario import HorarioAtencion, Bloqueo
from app.disponibilidad.service import calcular_slots
from app.extensions import db


def _horas(slots):
    return [s[0].strftime("%H:%M") for s in slots]


def test_slots_basicos(crear_negocio, crear_recurso, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, hora_inicio=time(9, 0), hora_fin=time(11, 0))  # 9-11
    slots = calcular_slots(rec, proximo_lunes, 60)
    assert _horas(slots) == ["09:00", "10:00"]


def test_turno_partido(crear_negocio, crear_recurso, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    # Segunda franja el mismo día
    db.session.add(HorarioAtencion(negocio_id=neg.id, recurso_id=rec.id, dia_semana=0,
                                   hora_inicio=time(16, 0), hora_fin=time(18, 0)))
    db.session.commit()
    slots = calcular_slots(rec, proximo_lunes, 60)
    assert _horas(slots) == ["09:00", "10:00", "16:00", "17:00"]


def test_bloqueo_resta_slots(crear_negocio, crear_recurso, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, hora_inicio=time(9, 0), hora_fin=time(12, 0))  # 9,10,11
    db.session.add(Bloqueo(negocio_id=neg.id, recurso_id=rec.id,
                           inicio=datetime.combine(proximo_lunes, time(10, 0)),
                           fin=datetime.combine(proximo_lunes, time(11, 0))))
    db.session.commit()
    slots = calcular_slots(rec, proximo_lunes, 60)
    assert "10:00" not in _horas(slots)
    assert "09:00" in _horas(slots) and "11:00" in _horas(slots)


def test_dia_sin_horario(crear_negocio, crear_recurso, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, dia=0)  # solo lunes
    martes = proximo_lunes + timedelta(days=1)
    assert calcular_slots(rec, martes, 60) == []


def test_agregar_horario_varios_dias_incluido_lunes(client, crear_negocio):
    """El form de horarios crea franjas para varios días, incluido el Lunes (0)."""
    from app.models.tipo_recurso import TipoRecurso
    from app.models.recurso import Recurso
    neg, _ = crear_negocio(email="hor@test.com")
    tipo = TipoRecurso(negocio_id=neg.id, nombre="T", slug="t")
    db.session.add(tipo); db.session.flush()
    rec = Recurso(negocio_id=neg.id, tipo_recurso_id=tipo.id, nombre="R", slug="r", capacidad=1)
    db.session.add(rec); db.session.commit()

    client.post("/auth/login", data={"email": "hor@test.com", "password": "clave1234"})
    r = client.post(f"/panel/disponibilidad/recurso/{rec.id}/horario", data={
        "dias": ["0", "1", "2"],            # Lunes, Martes, Miércoles
        "hora_inicio": "09:00", "hora_fin": "18:00",
    }, follow_redirects=False)
    assert r.status_code == 302

    dias = {h.dia_semana for h in HorarioAtencion.query.filter_by(recurso_id=rec.id).all()}
    assert dias == {0, 1, 2}   # incluye el Lunes (antes fallaba por DataRequired)


def test_capacidad_y_ocupados(crear_negocio, crear_recurso, proximo_lunes):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, capacidad=1, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    ocupados = [(datetime.combine(proximo_lunes, time(9, 0)),
                 datetime.combine(proximo_lunes, time(10, 0)))]
    slots = calcular_slots(rec, proximo_lunes, 60, ocupados=ocupados)
    assert "09:00" not in _horas(slots)
    assert "10:00" in _horas(slots)
