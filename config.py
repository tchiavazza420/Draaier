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

    # --- Pasarelas de pago ---
    # Sin access token, cada pasarela cae a MODO SIMULACIÓN (checkout interno
    # para desarrollo). Con token, usa la API real.
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_PUBLIC_KEY = os.environ.get("MERCADOPAGO_PUBLIC_KEY")
    NARANJA_X_ACCESS_TOKEN = os.environ.get("NARANJA_X_ACCESS_TOKEN")
    MODO_ACCESS_TOKEN = os.environ.get("MODO_ACCESS_TOKEN")

    # URL base pública del sitio (para back_urls y webhooks de Mercado Pago).
    SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:5000")

    # --- Email (Flask-Mail) ---
    # Sin MAIL_SERVER, las notificaciones van a una bandeja de desarrollo
    # (no se envían de verdad, pero se registran y son testeables).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "Reservas SaaS <no-reply@reservas.local>"
    )

    # --- WhatsApp (Cloud API de Meta) ---
    # Sin token/phone-id, las notificaciones WA van a una bandeja de desarrollo
    # (testeable). Con credenciales, se envían por la API real.
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
    WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
    WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

    # --- Uploads (logo / banner) ---
    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB máximo por archivo
    IMAGENES_PERMITIDAS = {"png", "jpg", "jpeg", "webp", "gif"}


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
