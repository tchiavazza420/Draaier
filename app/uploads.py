"""
app/uploads.py
--------------
Helper de subida de imágenes (logo / banner).

Guarda los archivos en static/uploads/<negocio_id>/ con un nombre único, y
devuelve la ruta relativa para guardar en la base. Valida extensión.
"""

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


def _extension_ok(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["IMAGENES_PERMITIDAS"]


def guardar_imagen(file_storage, negocio_id, prefijo):
    """
    Guarda una imagen subida y devuelve su ruta relativa dentro de /static
    (ej: 'uploads/3/logo-ab12.png'), o None si no se subió archivo válido.
    """
    if not file_storage or not file_storage.filename:
        return None
    if not _extension_ok(file_storage.filename):
        raise ValueError("Formato de imagen no permitido (usá png, jpg, webp o gif).")

    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    nombre = f"{prefijo}-{uuid.uuid4().hex[:8]}.{ext}"

    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], str(negocio_id))
    os.makedirs(carpeta, exist_ok=True)
    file_storage.save(os.path.join(carpeta, nombre))

    # Ruta relativa a /static para url_for('static', filename=...).
    return f"uploads/{negocio_id}/{nombre}"
