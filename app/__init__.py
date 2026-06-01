"""
app/__init__.py
---------------
Application Factory.

create_app() construye y configura una instancia de Flask. Centralizar la
creación acá nos permite:
  - tener múltiples configuraciones (dev / prod / testing),
  - registrar blueprints de forma ordenada y escalable,
  - testear creando apps aisladas.

A medida que avancemos, cada módulo (auth, negocios, reservas, etc.) se
registrará como blueprint dentro de register_blueprints().
"""

from flask import Flask

from config import get_config
from app.extensions import db, migrate, login_manager


def create_app(config_class=None):
    """Crea, configura y devuelve la aplicación Flask."""
    app = Flask(__name__)

    # 1) Configuración
    app.config.from_object(config_class or get_config())

    # 2) Inicialización de extensiones (vinculación tardía con la app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # 3) Modelos: se importan para que Flask-Migrate los detecte.
    #    (Vacío por ahora; se completa en el Paso 2.)
    register_models()

    # 4) Blueprints (módulos de la aplicación)
    register_blueprints(app)

    return app


def register_models():
    """
    Importa los modelos para que SQLAlchemy/Alembic los registren.

    En el Paso 2 agregaremos aquí los imports de Negocio, Usuario, Rol, etc.
    Mantener este punto centralizado evita modelos 'huérfanos' que las
    migraciones no detectan.
    """
    # Ejemplo de lo que vendrá:  from app.models import negocio, usuario, rol
    pass


def register_blueprints(app):
    """Registra todos los blueprints de la aplicación."""
    from app.main.routes import main_bp
    app.register_blueprint(main_bp)

    # En próximos pasos:
    # from app.auth.routes import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/auth")
