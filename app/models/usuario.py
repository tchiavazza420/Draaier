"""
app/models/usuario.py
---------------------
Modelo Usuario = personas que acceden al PANEL de administración.

Incluye: super_admin (negocio_id NULL), dueños y staff (atados a un negocio).
Los CLIENTES que reservan NO son Usuarios: se modelan aparte en el módulo
de clientes, porque tienen otro ciclo de vida y no acceden al panel.

Decisiones:
  - email es único a nivel global → un login simple e inequívoco.
    (Trade-off: una misma persona no puede ser staff de dos negocios con
     el mismo email. Aceptable para V1; revisable si surge la necesidad.)
  - negocio_id es nullable: NULL identifica al super_admin (cross-tenant).
  - La contraseña nunca se guarda en texto plano: solo su hash (Werkzeug).

Hereda UserMixin de Flask-Login para integrarse con el sistema de sesiones
en el Paso 3 (is_authenticated, get_id, etc.).
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models.mixins import TimestampMixin


class Usuario(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    # --- Tenant (NULL = super_admin, sin negocio) ---
    negocio_id = db.Column(
        db.Integer,
        db.ForeignKey("negocios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # --- Rol ---
    rol_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
        index=True,
    )

    # --- Datos personales ---
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=True)

    # --- Credenciales ---
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # --- Estado ---
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acceso = db.Column(db.DateTime(timezone=True), nullable=True)

    # --- Relaciones ---
    negocio = db.relationship("Negocio", back_populates="usuarios")
    rol = db.relationship("Rol", back_populates="usuarios")

    # ------------------------------------------------------------------
    #  Manejo de contraseña
    # ------------------------------------------------------------------
    def set_password(self, password):
        """Genera y almacena el hash de la contraseña (nunca el texto plano)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica una contraseña candidata contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------
    #  Helpers de rol (azúcar para autorización; se usan desde el Paso 3)
    # ------------------------------------------------------------------
    @property
    def es_super_admin(self):
        return self.rol is not None and self.rol.nombre == "super_admin"

    @property
    def es_dueno(self):
        return self.rol is not None and self.rol.nombre == "dueno"

    @property
    def es_staff(self):
        return self.rol is not None and self.rol.nombre == "staff"

    def __repr__(self):
        return f"<Usuario {self.id} {self.email!r}>"
