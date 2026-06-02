"""Tests del marketplace público (visibilidad y filtros)."""

from app.extensions import db


def test_solo_visibles_aparecen(client, crear_negocio):
    visible, _ = crear_negocio(nombre="Visible SA", visible_marketplace=True, ciudad="Cordoba")
    oculto, _ = crear_negocio(nombre="Oculto SA", visible_marketplace=False, ciudad="Cordoba")
    html = client.get("/marketplace").get_data(as_text=True)
    assert "Visible SA" in html
    assert "Oculto SA" not in html


def test_filtro_por_ciudad(client, crear_negocio):
    crear_negocio(nombre="Cordobesa", visible_marketplace=True, ciudad="Cordoba")
    html = client.get("/marketplace?ciudad=Mendoza").get_data(as_text=True)
    assert "Cordobesa" not in html
    html = client.get("/marketplace?ciudad=Cordoba").get_data(as_text=True)
    assert "Cordobesa" in html


def test_busqueda_por_servicio(client, crear_negocio, crear_recurso, crear_servicio):
    neg, _ = crear_negocio(nombre="Barber XYZ", visible_marketplace=True)
    rec = crear_recurso(neg)
    crear_servicio(neg, rec, nombre="Corte Fade")
    html = client.get("/marketplace?q=Fade").get_data(as_text=True)
    assert "Barber XYZ" in html
