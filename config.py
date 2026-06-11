"""
config.py
---------
Configuración centralizada de la aplicación.

Usamos clases por entorno (Development / Production / Testing) y elegimos
una con la variable FLASK_ENV. Todas las claves sensibles se leen desde el
archivo .env mediante python-dotenv, nunca se hardcodean.
"""

import os
from dotenv import load_dotenv

# Carga el archivo .env ubicado en la raíz del proyecto hacia os.environ.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def _normalizar_db_url(url):
    """
    Normaliza la URL de la base para forzar el driver psycopg v3.

    Plataformas como Render/Railway/Heroku entregan 'postgres://' o
    'postgresql://' (que SQLAlchemy mapearía a psycopg2, no instalado).
    Reescribimos al esquema 'postgresql+psycopg://'.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class BaseConfig:
    """Configuración común a todos los entornos."""

    # Clave para firmar sesiones y tokens CSRF. Obligatoria.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # --- SQLAlchemy ---
    SQLALCHEMY_DATABASE_URI = _normalizar_db_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # desactivado: consume memoria sin aportar

    # Opciones del pool de conexiones, pensadas para producción.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # verifica la conexión antes de usarla (evita conexiones muertas)
        "pool_recycle": 280,     # recicla conexiones antes del timeout típico de PostgreSQL
    }

    # --- Redis ---
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # --- Celery (tareas asíncronas y programadas) ---
    # Por defecto corre en modo EAGER (síncrono, sin Redis) para que la app
    # funcione sin infraestructura extra. En producción: CELERY_EAGER=false +
    # levantar Redis y un worker (ver docker-compose).
    CELERY = {
        "broker_url": os.environ.get("CELERY_BROKER_URL", REDIS_URL),
        "result_backend": os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL),
        "task_always_eager": os.environ.get("CELERY_EAGER", "true").lower() == "true",
        "task_eager_propagates": False,
        "task_ignore_result": True,
        "timezone": "UTC",
        "broker_connection_retry_on_startup": True,
    }

    # --- Pasarela de pago (Mercado Pago) ---
    # Sin access token, el checkout cae a MODO SIMULACIÓN (interno, para
    # desarrollo). Con token de producción (APP_USR-…), cobra de verdad.
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_PUBLIC_KEY = os.environ.get("MERCADOPAGO_PUBLIC_KEY")

    # --- Conexión OAuth (Mercado Pago Connect / Marketplace) ---
    # El negocio conecta su cuenta con un clic (no pega tokens). Estos son los
    # datos de NUESTRA aplicación de Mercado Pago (panel de desarrollador):
    #   MP_CLIENT_ID     = App ID (numérico)
    #   MP_CLIENT_SECRET = Client Secret de la app
    # El redirect_uri debe estar registrado en la app y apuntar al callback.
    MP_CLIENT_ID = os.environ.get("MP_CLIENT_ID")
    MP_CLIENT_SECRET = os.environ.get("MP_CLIENT_SECRET")
    # Comisión (%) que retiene la plataforma sobre cada seña (0 = sin comisión).
    MP_MARKETPLACE_FEE = float(os.environ.get("MP_MARKETPLACE_FEE", "0") or 0)

    # URL base pública del sitio (para back_urls y webhooks de Mercado Pago).
    SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:5000")

    # --- Notificaciones push (Web Push / VAPID) ---
    # Generá el par de claves una vez (ver INTEGRACIONES.md) y cargalas en
    # Render. Sin claves, las suscripciones push quedan deshabilitadas.
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:soporte@agenpro.com.ar")

    # Versión de assets para cache-busting del CSS/JS. Bumpear (o setear por
    # env) en cada cambio visual fuerza a bajar el CSS fresco aunque haya un
    # service worker viejo cacheando la URL anterior.
    ASSET_VERSION = os.environ.get("ASSET_VERSION", "27")

    # Token secreto para el endpoint de tareas programadas (/tareas/correr).
    # Lo usa un cron externo (cron-job.org / GitHub Actions) para disparar los
    # recordatorios y el vencimiento de suscripciones en plan free (sin worker).
    CRON_TOKEN = os.environ.get("CRON_TOKEN")

    # --- Email (Flask-Mail) ---
    # Sin MAIL_SERVER, las notificaciones van a una bandeja de desarrollo
    # (no se envían de verdad, pero se registran y son testeables).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "AgenPro <no-reply@reservas.local>"
    )

    # --- WhatsApp (Cloud API de Meta) ---
    # Sin token/phone-id, las notificaciones WA van a una bandeja de desarrollo
    # (testeable). Con credenciales, se envían por la API real.
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
    WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
    WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")
    # Plantilla aprobada por Meta para recordatorios proactivos (fuera de la
    # ventana de 24 h). Si está seteada, los recordatorios se envían como
    # template (3 variables: nombre, servicio, fecha/hora). Si no, texto plano.
    WHATSAPP_TEMPLATE_RECORDATORIO = os.environ.get("WHATSAPP_TEMPLATE_RECORDATORIO")
    # Plantilla para la CONFIRMACIÓN de reserva (mensaje proactivo a un cliente
    # nuevo que no escribió antes: sin plantilla, Meta no lo entrega).
    WHATSAPP_TEMPLATE_CONFIRMACION = os.environ.get("WHATSAPP_TEMPLATE_CONFIRMACION")
    WHATSAPP_TEMPLATE_IDIOMA = os.environ.get("WHATSAPP_TEMPLATE_IDIOMA", "es_AR")

    # --- Almacenamiento de imágenes ---
    # Con CLOUDINARY_URL (cloudinary://api_key:api_secret@cloud_name) las
    # imágenes se suben a Cloudinary (recomendado en producción: el disco de
    # Render es efímero). Sin esa variable, se guardan en disco local.
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")

    # --- Uploads locales (fallback dev) ---
    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    # Tope del request completo. Las fotos de celular (HEIC/JPG de 12MP) pesan
    # varios MB y el editor puede subir logo + banner + foto juntos, así que el
    # límite tiene que ser holgado (se comprime server-side a WebP igual).
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB por request
    # heic/heif: formato por defecto de las fotos de iPhone (se convierten a WebP).
    IMAGENES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif", "heic", "heif"}


class DevelopmentConfig(BaseConfig):
    """Entorno local de desarrollo."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # poné True si querés ver el SQL generado en consola


class ProductionConfig(BaseConfig):
    """Entorno de producción."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(BaseConfig):
    """Entorno para tests automatizados."""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # facilita testear formularios sin token CSRF


# Mapa para seleccionar la configuración por nombre.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Devuelve la clase de configuración según FLASK_ENV (default: development)."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
