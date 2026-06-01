"""
app/models/negocio.py
---------------------
Modelo Negocio = el TENANT del sistema.

Cada negocio es una unidad aislada. Su `slug` único alimenta las URLs
públicas (/slug-negocio) y la resolución multi-tenant por path.

Los campos de suscripción se incluyen como base; la lógica completa de
facturación (Mercado Pago, planes, ciclos) se desarrolla en el módulo de
pagos. Aquí solo dejamos el estado mínimo necesario para la regla de
negocio: "al vencer, el negocio puede leer pero no crear".
"""

import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class RubroEnum(enum.Enum):
    """Rubro del negocio. Sirve para el filtrado del marketplace."""
    MANICURA = "manicura"
    PELUQUERIA = "peluqueria"
    BARBERIA = "barberia"
    LASHISTA = "lashista"
    ESTETICA = "estetica"
    SPA = "spa"
    PSICOLOGIA = "psicologia"
    NUTRICION = "nutricion"
    CONSULTORIO = "consultorio"
    CANCHA_FUTBOL = "cancha_futbol"
    CANCHA_PADEL = "cancha_padel"
    TENIS = "tenis"
    COWORKING = "coworking"
    SALA_REUNIONES = "sala_reuniones"
    OTRO = "otro"


class PlanEnum(enum.Enum):
    """
    Planes comerciales.
    Independiente: basico / pro / premium.
    Locales:       starter / business / enterprise.
    """
    BASICO = "basico"
    PRO = "pro"
    PREMIUM = "premium"
    STARTER = "starter"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class EstadoSuscripcionEnum(enum.Enum):
    """Estado de la suscripción del negocio."""
    TRIAL = "trial"          # prueba gratuita (solo plan Básico, 14 días)
    ACTIVA = "activa"        # pago al día
    VENCIDA = "vencida"      # venció: solo lectura
    CANCELADA = "cancelada"  # dada de baja


class Negocio(TimestampMixin, db.Model):
    """El tenant. Todo el sistema se aísla por negocio.id."""

    __tablename__ = "negocios"

    id = db.Column(db.Integer, primary_key=True)

    # --- Identidad pública ---
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    rubro = db.Column(
        db.Enum(RubroEnum, native_enum=False, length=30),
        nullable=False,
        default=RubroEnum.OTRO,
    )

    # --- Contacto / ubicación (para marketplace) ---
    email = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(40), nullable=True)
    ciudad = db.Column(db.String(80), nullable=True, index=True)

    # --- Marketplace ---
    visible_marketplace = db.Column(db.Boolean, nullable=False, default=False)

    # --- Estado general ---
    activo = db.Column(db.Boolean, nullable=False, default=True)

    # --- Suscripción (base; la facturación va en el módulo de pagos) ---
    plan = db.Column(
        db.Enum(PlanEnum, native_enum=False, length=20),
        nullable=True,
    )
    estado_suscripcion = db.Column(
        db.Enum(EstadoSuscripcionEnum, native_enum=False, length=20),
        nullable=False,
        default=EstadoSuscripcionEnum.TRIAL,
    )
    trial_fin = db.Column(db.DateTime(timezone=True), nullable=True)
    suscripcion_fin = db.Column(db.DateTime(timezone=True), nullable=True)

    # --- Relaciones ---
    usuarios = db.relationship(
        "Usuario",
        back_populates="negocio",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def puede_operar(self):
        """
        Regla de negocio del brief: un negocio con suscripción TRIAL o ACTIVA
        puede crear reservas/clientes/recursos. Si está VENCIDA o CANCELADA,
        solo puede leer. También exige que el negocio esté activo.
        """
        return self.activo and self.estado_suscripcion in (
            EstadoSuscripcionEnum.TRIAL,
            EstadoSuscripcionEnum.ACTIVA,
        )

    def __repr__(self):
        return f"<Negocio {self.id} {self.slug!r}>"
