"""
app/models/horario.py
---------------------
Disponibilidad: horarios de atención recurrentes y bloqueos puntuales.

HorarioAtencion
  Franja semanal recurrente de un recurso. Ej: "Cancha 1, lunes 09:00–13:00".
  Un recurso puede tener varias filas el mismo día (turno partido: 09–13 y 16–22).
  dia_semana sigue date.weekday(): 0=lunes ... 6=domingo.

Bloqueo
  Período puntual en el que NO hay disponibilidad: vacaciones, feriado,
  mantenimiento de cancha, etc. Se define por rango de fecha/hora.
  Si recurso_id es NULL, el bloqueo aplica a TODO el negocio (ej: feriado).

Ninguna disponibilidad se precalcula: el servicio de slots la deriva en
tiempo real a partir de estas dos tablas (+ las reservas, en el Paso 7).
"""

import enum

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


# Etiquetas legibles de los días (índice = date.weekday()).
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class SemanaEnum(enum.Enum):
    """
    A qué semana aplica una franja, para horarios que se alternan.

    - TODAS: todas las semanas (lo normal).
    - A: semanas con número ISO PAR.
    - B: semanas con número ISO IMPAR.

    Así, cargando una franja como A y otra como B, se intercalan semana a semana.
    """
    TODAS = "todas"
    A = "a"
    B = "b"


def semana_de(fecha):
    """Devuelve SemanaEnum.A o .B según la paridad de la semana ISO de `fecha`."""
    return SemanaEnum.A if (fecha.isocalendar()[1] % 2 == 0) else SemanaEnum.B


class HorarioAtencion(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "horarios_atencion"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    recurso_id = db.Column(
        db.Integer,
        db.ForeignKey("recursos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dia_semana = db.Column(db.SmallInteger, nullable=False)  # 0=lunes ... 6=domingo
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    # A qué semana aplica (para horarios alternados). Por defecto, TODAS.
    semana = db.Column(
        db.Enum(SemanaEnum, native_enum=False, length=10),
        nullable=False, default=SemanaEnum.TODAS,
    )
    activo = db.Column(db.Boolean, nullable=False, default=True)

    recurso = db.relationship("Recurso", backref=db.backref("horarios", lazy="selectin"))

    def aplica_en(self, fecha):
        """True si esta franja rige en la fecha dada (según su semana A/B/TODAS)."""
        if self.semana == SemanaEnum.TODAS:
            return True
        return self.semana == semana_de(fecha)

    __table_args__ = (
        db.CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_horario_dia"),
        db.CheckConstraint("hora_fin > hora_inicio", name="ck_horario_rango"),
        db.Index("ix_horario_recurso_dia", "recurso_id", "dia_semana"),
    )

    @property
    def dia_nombre(self):
        return DIAS_SEMANA[self.dia_semana]

    def __repr__(self):
        return f"<Horario rec={self.recurso_id} d{self.dia_semana} {self.hora_inicio}-{self.hora_fin}>"


class Bloqueo(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "bloqueos"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    # NULL = aplica a todo el negocio (ej: feriado). Con valor = solo ese recurso.
    recurso_id = db.Column(
        db.Integer,
        db.ForeignKey("recursos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Tiempos de dominio en HORA LOCAL del negocio (naive), consistente con
    # HorarioAtencion. La zona horaria por negocio se incorporará más adelante.
    inicio = db.Column(db.DateTime, nullable=False)
    fin = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.String(160), nullable=True)

    recurso = db.relationship("Recurso", backref=db.backref("bloqueos", lazy="selectin"))

    __table_args__ = (
        db.CheckConstraint("fin > inicio", name="ck_bloqueo_rango"),
        db.Index("ix_bloqueo_negocio_inicio", "negocio_id", "inicio"),
    )

    @property
    def es_global(self):
        """True si el bloqueo aplica a todo el negocio (sin recurso puntual)."""
        return self.recurso_id is None

    def __repr__(self):
        return f"<Bloqueo neg={self.negocio_id} rec={self.recurso_id} {self.inicio}->{self.fin}>"
