"""
tests/test_servicios_sugeridos.py
---------------------------------
Onboarding accionable: el asistente sugiere servicios por rubro y crea de a
varios los seleccionados, asignándolos a los profesionales activos.
"""

from app.models.negocio import RubroEnum
from app.models.servicio import Servicio
from app.servicios.sugeridos import sugerencias_para


def test_sugerencias_por_rubro():
    pel = sugerencias_para(RubroEnum.PELUQUERIA)
    assert any(s["nombre"] == "Corte de pelo" for s in pel)
    assert all({"nombre", "duracion", "precio"} <= set(s) for s in pel)
    # Rubro sin lista propia => genérico (no vacío).
    assert sugerencias_para(RubroEnum.OTRO)


def test_ver_asistente(client, crear_negocio):
    neg, _ = crear_negocio(email="sug@test.com", rubro=RubroEnum.BARBERIA)
    client.post("/auth/login", data={"email": "sug@test.com", "password": "clave1234"})
    html = client.get("/panel/servicios/sugeridos").get_data(as_text=True)
    assert "Corte + Barba" in html        # típico de barbería


def test_sena_masiva_aplica_a_seleccionados(client, crear_negocio, crear_recurso, crear_servicio):
    """La config masiva de seña aplica el % a los servicios tildados y limpia el resto."""
    from app.extensions import db
    neg, _ = crear_negocio(email="senas@test.com")
    rec = crear_recurso(neg, nombre="Sol")
    s1 = crear_servicio(neg, rec, nombre="Corte", precio=1000)
    s2 = crear_servicio(neg, rec, nombre="Color", precio=4000, requiere_sena=True, sena_monto=500)
    client.post("/auth/login", data={"email": "senas@test.com", "password": "clave1234"})

    # Aplico 30% solo a s1; s2 (tenía seña fija) queda destildado => sin seña.
    r = client.post("/panel/servicios/senas", data={
        "sena_tipo": "porcentaje", "sena_porcentaje": "30", "servicios": [str(s1.id)],
    }, follow_redirects=True)
    assert r.status_code == 200

    db.session.refresh(s1); db.session.refresh(s2)
    assert s1.requiere_sena is True and s1.sena_porcentaje == 30 and s1.sena_monto is None
    assert s1.sena_calculada == 300                 # 30% de 1000
    assert s2.requiere_sena is False and s2.sena_monto is None


def test_senas_cobro_guarda_alias(client, crear_negocio):
    """El cobro por transferencia se guarda desde la sección de Señas."""
    from app.extensions import db
    from app.models.negocio import Negocio
    neg, _ = crear_negocio(email="cobro@test.com")
    client.post("/auth/login", data={"email": "cobro@test.com", "password": "clave1234"})

    r = client.post("/panel/servicios/senas/cobro", data={
        "alias_transferencia": "mi.alias.mp", "titular_transferencia": "Rocio",
    }, follow_redirects=True)
    assert r.status_code == 200
    actualizado = db.session.get(Negocio, neg.id)
    assert actualizado.alias_transferencia == "mi.alias.mp"
    assert actualizado.titular_transferencia == "Rocio"


def test_crear_seleccionados_asigna_profesionales(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio(email="sug2@test.com", rubro=RubroEnum.MANICURA)
    rec = crear_recurso(neg, nombre="Vale")
    client.post("/auth/login", data={"email": "sug2@test.com", "password": "clave1234"})

    # Selecciona los items 0 y 2, editando precio del 0.
    r = client.post("/panel/servicios/sugeridos", data={
        "sel_0": "on", "nombre_0": "Esmaltado", "duracion_0": "45", "precio_0": "5000",
        "sel_2": "on",
    }, follow_redirects=False)
    assert r.status_code == 302

    servicios = Servicio.query.filter_by(negocio_id=neg.id).all()
    assert len(servicios) == 2
    # Todos quedaron asignados al profesional activo.
    assert all(rec in s.recursos for s in servicios)
    assert any(s.nombre == "Esmaltado" and s.duracion_minutos == 45 for s in servicios)
