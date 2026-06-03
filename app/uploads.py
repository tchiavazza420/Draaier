"""
app/uploads.py
--------------
Helper de subida de imágenes (logo / banner / foto de profesional / galería).

Guarda los archivos en static/uploads/<negocio_id>/ con un nombre único.
Antes de guardar, **comprime y redimensiona** con Pillow y los convierte a
WebP (mucho más liviano), respetando la orientación EXIF y la transparencia.
Devuelve la ruta relativa para guardar en la base. Valida extensión.
"""

import os
import uuid

from flask import current_app
from PIL import Image, ImageOps

# Lado máximo (px) del lado más largo, según el uso. El resto se reescala
# proporcionalmente. Default si el prefijo no está en el mapa.
_MAX_LADO = {
    "logo": 512,
    "profesional": 800,
    "portada": 1600,
    "banner": 1600,
    "galeria": 1400,
}
_MAX_DEFAULT = 1280
_CALIDAD_WEBP = 82


def _extension_ok(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["IMAGENES_PERMITIDAS"]


def guardar_imagen(file_storage, negocio_id, prefijo):
    """
    Procesa y guarda una imagen subida; devuelve su ruta relativa dentro de
    /static (ej: 'uploads/3/profesional-ab12.webp'), o None si no se subió
    archivo. Lanza ValueError si el formato es inválido o el archivo no es
    una imagen legible.
    """
    if not file_storage or not file_storage.filename:
        return None
    if not _extension_ok(file_storage.filename):
        raise ValueError("Formato de imagen no permitido (usá png, jpg, webp o gif).")

    try:
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img)  # respeta la orientación de la cámara
    except Exception:
        raise ValueError("No pudimos leer la imagen. Probá con otro archivo.")

    # Transparencia: si la tiene, la conservamos (RGBA); si no, RGB.
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    # Redimensionado proporcional al lado máximo del uso.
    max_lado = _MAX_LADO.get(prefijo, _MAX_DEFAULT)
    img.thumbnail((max_lado, max_lado), Image.LANCZOS)

    nombre = f"{prefijo}-{uuid.uuid4().hex[:8]}.webp"
    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], str(negocio_id))
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre)
    img.save(destino, "WEBP", quality=_CALIDAD_WEBP, method=6)

    # Ruta relativa a /static para url_for('static', filename=...).
    return f"uploads/{negocio_id}/{nombre}"
