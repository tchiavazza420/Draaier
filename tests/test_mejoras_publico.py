"""
tests/test_mejoras_publico.py
-----------------------------
SEO (robots/sitemap/Open Graph), compresión de imágenes y la grilla de
profesionales en la página pública del local.
"""

import io
import os

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.extensions import db


# ---------- SEO ----------
def test_robots_y_sitemap(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio(visible_marketplace=True)
    crear_recurso(neg, nombre="Sofi")

    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap:" in r.get_data(as_text=True)
    assert "Disallow: /panel/" in r.get_data(as_text=True)

    s = client.get("/sitemap.xml")
    body = s.get_data(as_text=True)
    assert s.status_code == 200 and s.mimetype == "application/xml"
    assert f"/{neg.slug}" in body                 # página del negocio
    assert "<urlset" in body


def test_open_graph_en_pagina_publica(client, crear_negocio):
    neg, _ = crear_negocio()
    neg.descripcion_publica = "El mejor salón de la ciudad"
    db.session.commit()
    html = client.get(f"/{neg.slug}").get_data(as_text=True)
    assert 'property="og:title"' in html
    assert neg.nombre in html
    assert "El mejor salón de la ciudad" in html  # description del negocio


# ---------- Grilla de profesionales ----------
def test_perfil_muestra_profesionales(client, crear_negocio, crear_recurso):
    neg, _ = crear_negocio()
    rec = crear_recurso(neg, nombre="Juli Barber")
    rec.especialidad = "Barbero"
    rec.color_acento = "#10b981"
    db.session.commit()

    html = client.get(f"/{neg.slug}").get_data(as_text=True)
    assert "Nuestro equipo" in html
    assert "Juli Barber" in html and "Barbero" in html
    assert "#10b981" in html


# ---------- Compresión de imágenes ----------
def test_guardar_imagen_comprime_y_redimensiona(app):
    with app.app_context():
        from app.uploads import guardar_imagen
        buf = io.BytesIO()
        Image.new("RGB", (2000, 3000), (120, 40, 200)).save(buf, "JPEG")
        buf.seek(0)
        fs = FileStorage(stream=buf, filename="foto.jpg", content_type="image/jpeg")

        ruta = guardar_imagen(fs, 999, "profesional")
        assert ruta.endswith(".webp")
        full = os.path.join(app.static_folder, ruta.replace("/", os.sep))
        try:
            img = Image.open(full)
            assert img.format == "WEBP"
            assert max(img.size) <= 800       # redimensionado al lado máximo
            img.close()
        finally:
            if os.path.exists(full):
                try:
                    os.remove(full)
                except PermissionError:
                    pass


def test_guardar_imagen_rechaza_no_imagen(app):
    with app.app_context():
        from app.uploads import guardar_imagen
        fs = FileStorage(stream=io.BytesIO(b"no soy una imagen"),
                         filename="x.png", content_type="image/png")
        try:
            guardar_imagen(fs, 999, "profesional")
            assert False, "debería rechazar contenido no-imagen"
        except ValueError:
            pass
