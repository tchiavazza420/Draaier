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
from datetime import datetime, timezone

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


class TemplatePublicoEnum(enum.Enum):
    """Plantilla visual de la página pública del negocio."""
    MINIMAL = "minimal"
    ELEGANTE = "elegante"
    MODERNO = "moderno"
    PREMIUM = "premium"


class MetodoPagoEnum(enum.Enum):
    """Pasarela de pago que el negocio usa para cobrar señas."""
    MERCADOPAGO = "mercadopago"
    NARANJA_X = "naranja_x"
    MODO = "modo"


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

    # --- Pasarela de pago preferida (para cobrar señas) ---
    metodo_pago = db.Column(
        db.Enum(MetodoPagoEnum, native_enum=False, length=20),
        nullable=False, default=MetodoPagoEnum.MERCADOPAGO,
    )

    # --- Personalización / branding ---
    logo_filename = db.Column(db.String(200), nullable=True)
    banner_filename = db.Column(db.String(200), nullable=True)
    color_primario = db.Column(db.String(7), nullable=False, default="#0d6efd")
    color_secundario = db.Column(db.String(7), nullable=False, default="#111827")
    tipografia = db.Column(db.String(60), nullable=False, default="Inter")
    template_publico = db.Column(
        db.Enum(TemplatePublicoEnum, native_enum=False, length=20),
        nullable=False, default=TemplatePublicoEnum.MINIMAL,
    )
    descripcion_publica = db.Column(db.Text, nullable=True)
    instagram = db.Column(db.String(120), nullable=True)
    facebook = db.Column(db.String(120), nullable=True)
    whatsapp = db.Column(db.String(40), nullable=True)

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
    def vencimiento(self):
        """Fecha de fin vigente según el estado (trial o suscripción), o None."""
        if self.estado_suscripcion == EstadoSuscripcionEnum.TRIAL:
            return self.trial_fin
        if self.estado_suscripcion == EstadoSuscripcionEnum.ACTIVA:
            return self.suscripcion_fin
        return None

    @property
    def esta_vencido(self):
        """True si la vigencia (trial o suscripción) ya pasó."""
        fin = self.vencimiento
        if fin is None:
            return False
        ahora = datetime.now(timezone.utc)
        # Comparación robusta aunque la fecha venga naive de la DB.
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        return fin < ahora

    @property
    def puede_operar(self):
        """
        Regla del brief: un negocio con suscripción TRIAL o ACTIVA y VIGENTE
        puede crear reservas/clientes/recursos. Si venció (trial o pago),
        está VENCIDA/CANCELADA, o está inactivo, solo puede leer.
        """
        if not self.activo:
            return False
        if self.estado_suscripcion not in (
            EstadoSuscripcionEnum.TRIAL, EstadoSuscripcionEnum.ACTIVA
        ):
            return False
        return not self.esta_vencido

    def __repr__(self):
        return f"<Negocio {self.id} {self.slug!r}>"
