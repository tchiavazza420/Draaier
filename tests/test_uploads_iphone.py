"""
tests/test_uploads_iphone.py
----------------------------
Casos límite de subida de imágenes desde un iPhone:
  - extensión .HEIC en mayúsculas (nombre típico IMG_1234.HEIC),
  - archivo sin extensión (al compartir desde algunas apps iOS),
  - foto grande estilo cámara moderna (24MP).
"""

import io

import pillow_heif
from PIL import Image


def _heic_bytes(w=320, h=240):
    img = Image.new("RGB", (w, h), (180, 120, 90))
    hf = pillow_heif.from_pillow(img)
    buf = io.BytesIO()
    hf.save(buf, quality=80)
    buf.seek(0)
    return buf


def test_galeria_acepta_heic_mayusculas(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    login(dueno.email)
    r = client.post(
        "/panel/galeria",
        data={"fotos": (_heic_bytes(), "IMG_1234.HEIC")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "no permitido" not in html and "No pudimos leer" not in html


def test_galeria_archivo_sin_extension(client, crear_negocio, login):
    """Algunas apps de iOS comparten la foto sin extensión: la acepta igual
    (la valida Pillow al abrirla; siempre se re-encodea a WebP)."""
    neg, dueno = crear_negocio()
    login(dueno.email)
    r = client.post(
        "/panel/galeria",
        data={"fotos": (_heic_bytes(), "image")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "no permitido" not in html and "No pudimos leer" not in html


def test_galeria_rechaza_archivo_no_imagen_sin_extension(client, crear_negocio, login):
    """Un archivo sin extensión que NO es imagen se rechaza con mensaje claro."""
    neg, dueno = crear_negocio()
    login(dueno.email)
    r = client.post(
        "/panel/galeria",
        data={"fotos": (io.BytesIO(b"esto no es una imagen"), "documento")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "No pudimos leer" in r.get_data(as_text=True)


def test_galeria_foto_24mp(client, crear_negocio, login):
    neg, dueno = crear_negocio()
    login(dueno.email)
    import time
    t0 = time.time()
    r = client.post(
        "/panel/galeria",
        data={"fotos": (_heic_bytes(5712, 4284), "IMG_5678.heic")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    dt = time.time() - t0
    html = r.get_data(as_text=True)
    print(f"24MP => {dt:.1f}s")
    assert r.status_code == 200
    assert "no permitido" not in html and "No pudimos leer" not in html
