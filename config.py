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


class BaseConfig:
    """Configuración común a todos los entornos."""

    # Clave para firmar sesiones y tokens CSRF. Obligatoria.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # --- SQLAlchemy ---
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # desactivado: consume memoria sin aportar

    # Opciones del pool de conexiones, pensadas para producción.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # verifica la conexión antes de usarla (evita conexiones muertas)
        "pool_recycle": 280,     # recicla conexiones antes del timeout típico de PostgreSQL
    }

    # --- Redis (se utilizará desde el módulo de notificaciones/Celery) ---
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


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
