"""
app/extensions.py
-----------------
Instancias de las extensiones de Flask, creadas SIN aplicación.

Este patrón (instanciar acá y llamar .init_app(app) en el factory) evita
imports circulares y permite que cualquier módulo importe `db`, `migrate`,
etc. sin depender del objeto `app`. Es la base de una arquitectura modular.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect


# ORM. Se vincula a la app en create_app().
db = SQLAlchemy()

# Manejo de migraciones de esquema (Alembic por debajo).
migrate = Migrate()

# Protección CSRF global. Cubre tanto los formularios WTForms (hidden_tag)
# como los formularios HTML manuales que incluyan {{ csrf_token() }}.
# Además registra el global csrf_token() en las plantillas de forma confiable.
csrf = CSRFProtect()

# Gestión de sesiones de usuario. Se configura en el Paso 3 (autenticación).
login_manager = LoginManager()
login_manager.login_view = "auth.login"          # endpoint al que redirige si no hay sesión
login_manager.login_message = "Por favor iniciá sesión para continuar."
login_manager.login_message_category = "warning"
