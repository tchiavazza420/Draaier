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
from app.extensions import db, migrate, login_manager, csrf, mail


def create_app(config_class=None):
    """Crea, configura y devuelve la aplicación Flask."""
    app = Flask(__name__)

    # 1) Configuración
    app.config.from_object(config_class or get_config())

    # 2) Inicialización de extensiones (vinculación tardía con la app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # 3) Modelos: se importan para que Flask-Migrate los detecte.
    #    (Vacío por ahora; se completa en el Paso 2.)
    register_models()

    # 4) Blueprints (módulos de la aplicación)
    register_blueprints(app)

    # 5) Comandos CLI personalizados (flask seed-roles, etc.)
    from app.cli import register_commands
    register_commands(app)

    return app


def register_models():
    """
    Importa los modelos para que SQLAlchemy/Alembic los registren.

    Basta con importar el paquete app.models (su __init__ trae Negocio,
    Usuario, Rol, etc.). Centralizar esto evita modelos 'huérfanos' que
    las migraciones no detectan.
    """
    import app.models  # noqa: F401 - import con efecto de registro


def register_blueprints(app):
    """
    Registra todos los blueprints de la aplicación.

    El orden importa: 'publico' usa una ruta catch-all /<slug> y debe ir
    ÚLTIMO para que /auth, /panel y /health tengan prioridad.
    """
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.panel.routes import panel_bp
    from app.recursos.routes import recursos_bp
    from app.servicios.routes import servicios_bp
    from app.disponibilidad.routes import disponibilidad_bp
    from app.reservas.routes import reservas_bp
    from app.pagos.routes import pagos_bp
    from app.clientes.routes import clientes_bp
    from app.resenas.routes import resenas_bp
    from app.marketplace.routes import marketplace_bp
    from app.publico.routes import publico_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(panel_bp, url_prefix="/panel")
    app.register_blueprint(recursos_bp, url_prefix="/panel/recursos")
    app.register_blueprint(servicios_bp, url_prefix="/panel/servicios")
    app.register_blueprint(disponibilidad_bp, url_prefix="/panel/disponibilidad")
    app.register_blueprint(reservas_bp, url_prefix="/panel/reservas")
    app.register_blueprint(clientes_bp, url_prefix="/panel/clientes")
    app.register_blueprint(resenas_bp, url_prefix="/panel/resenas")
    app.register_blueprint(pagos_bp, url_prefix="/pagos")
    app.register_blueprint(publico_bp)  # catch-all /<slug>: SIEMPRE el último
