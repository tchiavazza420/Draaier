"""
app/uploads.py
--------------
Subida de imágenes (logo / banner / foto de profesional / galería).

Pipeline:
  1. Validar extensión y abrir con Pillow (respeta EXIF, tolera truncadas).
  2. Redimensionar al lado máximo del uso y comprimir a WebP.
  3. Guardar en el backend:
       - Cloudinary  (si CLOUDINARY_URL está configurado) → devuelve la URL.
       - Disco local (fallback dev) → static/uploads/<negocio_id>/...
         (⚠️ en Render el disco es efímero: usar Cloudinary en producción).

`media_url(valor)` resuelve el valor guardado a una URL usable tanto si es una
URL absoluta (Cloudinary) como una ruta relativa de /static (local).
"""

import os
import uuid
from io import BytesIO

from flask import current_app, url_for
from PIL import Image, ImageOps, ImageFile

# Tolera imágenes levemente truncadas en vez de fallar.
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Soporte para fotos de celular en formato HEIC/HEIF (iPhone y varios Android).
# Si la librería está instalada, registramos el lector para que Pillow las abra.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

# Lado máximo (px) del lado más largo, según el uso.
_MAX_LADO = {
    "logo": 512, "profesional": 800, "portada": 1600,
    "banner": 1600, "galeria": 1400,
}
_MAX_DEFAULT = 1280
_CALIDAD_WEBP = 80
# method 4: buena compresión y MUCHO más rápido que 6 (clave en CPU limitada).
_WEBP_METHOD = 4


def _extension_ok(filename):
    # Sin extensión (algunas apps de iOS comparten así): lo decide Pillow al
    # abrirla — siempre re-encodeamos a WebP, nunca servimos el original.
    if "." not in filename:
        return True
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["IMAGENES_PERMITIDAS"]


def _cloudinary_activo():
    return bool(current_app.config.get("CLOUDINARY_URL"))


def _procesar_a_webp(file_storage, prefijo):
    """Abre, reorienta, redimensiona y comprime la imagen; devuelve bytes WebP."""
    max_lado = _MAX_LADO.get(prefijo, _MAX_DEFAULT)
    try:
        img = Image.open(file_storage.stream)
        # draft(): para JPEG enormes, los decodifica directo a baja resolución
        # (acelera muchísimo el procesado de fotos de celular grandes).
        try:
            img.draft("RGB", (max_lado, max_lado))
        except Exception:
            pass
        img = ImageOps.exif_transpose(img)
    except Exception:
        raise ValueError("No pudimos leer la imagen. Probá con otro archivo (JPG o PNG).")

    img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
    img.thumbnail((max_lado, max_lado), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, "WEBP", quality=_CALIDAD_WEBP, method=_WEBP_METHOD)
    buf.seek(0)
    return buf


def _guardar_local(buf, negocio_id, prefijo):
    nombre = f"{prefijo}-{uuid.uuid4().hex[:8]}.webp"
    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], str(negocio_id))
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, nombre), "wb") as f:
        f.write(buf.getbuffer())
    return f"uploads/{negocio_id}/{nombre}"


def _guardar_cloudinary(buf, negocio_id, prefijo):
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloudinary_url=current_app.config["CLOUDINARY_URL"])

    ultimo = None
    for intento in (1, 2):  # 1 reintento: las fallas de red suelen ser transitorias
        try:
            buf.seek(0)
            res = cloudinary.uploader.upload(
                buf,
                folder=f"agenpro/{negocio_id}",
                public_id=f"{prefijo}-{uuid.uuid4().hex[:8]}",
                resource_type="image",
                format="webp",
                overwrite=True,
                timeout=60,  # no quedarse colgado si la red falla
            )
            return res["secure_url"]
        except Exception as exc:
            ultimo = exc
            current_app.logger.exception(
                "Fallo subiendo imagen a Cloudinary (intento %s, http_code=%s)",
                intento, getattr(exc, "http_code", "?"),
            )

    # Mensaje específico según la causa (el código HTTP viene en la excepción
    # del SDK): credenciales mal o cuota agotada NO se arreglan reintentando.
    code = getattr(ultimo, "http_code", None)
    texto = str(ultimo).lower()
    if code == 401 or "api_key" in texto or "unauthorized" in texto or "invalid" in texto:
        raise ValueError(
            "No pudimos guardar la imagen: el almacenamiento (Cloudinary) rechazó "
            "las credenciales. Revisá CLOUDINARY_URL en el servidor."
        )
    if code == 420 or "rate" in texto or "quota" in texto or "limit" in texto:
        raise ValueError(
            "No pudimos guardar la imagen: se alcanzó el límite del plan de "
            "Cloudinary. Revisá el uso en su dashboard."
        )
    raise ValueError("No pudimos subir la imagen ahora. Probá de nuevo en un momento.")


def guardar_imagen(file_storage, negocio_id, prefijo):
    """
    Procesa y guarda una imagen subida. Devuelve el valor a persistir (URL de
    Cloudinary o ruta relativa local), o None si no se subió archivo. Lanza
    ValueError si el formato es inválido o el archivo no es una imagen.
    """
    if not file_storage or not file_storage.filename:
        return None
    if not _extension_ok(file_storage.filename):
        raise ValueError("Formato de imagen no permitido (usá png, jpg, webp o gif).")

    buf = _procesar_a_webp(file_storage, prefijo)
    if _cloudinary_activo():
        return _guardar_cloudinary(buf, negocio_id, prefijo)
    return _guardar_local(buf, negocio_id, prefijo)


def media_url(valor, external=False):
    """
    URL usable para un valor guardado de imagen:
      - URL absoluta (Cloudinary) → se usa tal cual.
      - Ruta relativa (local) → url_for('static', filename=..., _external=external).
    `external=True` para URLs absolutas (Open Graph, emails).
    """
    if not valor:
        return ""
    if valor.startswith("http://") or valor.startswith("https://"):
        return valor
    return url_for("static", filename=valor, _external=external)
