"""
app/disponibilidad/forms.py
---------------------------
Formularios de horarios y bloqueos.
"""

from datetime import time

from flask_wtf import FlaskForm
from wtforms import (
    SelectField, SelectMultipleField, StringField, SubmitField,
)
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, InputRequired, Optional, ValidationError

from app.models.horario import DIAS_SEMANA


def _opciones_horas(paso=30):
    """Opciones 'HH:MM' cada `paso` minutos (00:00 .. 23:30)."""
    ops = []
    for minutos in range(0, 24 * 60, paso):
        h, m = divmod(minutos, 60)
        ops.append((f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}"))
    return ops


def _a_time(texto):
    h, m = texto.split(":")
    return time(int(h), int(m))


class HorarioForm(FlaskForm):
    # InputRequired (no DataRequired) para que el Lunes (valor 0) no se trate
    # como "vacío". SelectMultiple permite cargar varios días de una vez.
    dias = SelectMultipleField(
        "Días",
        coerce=int,
        choices=[(i, nombre) for i, nombre in enumerate(DIAS_SEMANA)],
        validators=[InputRequired(message="Elegí al menos un día.")],
    )
    hora_inicio = SelectField("Desde", choices=_opciones_horas(), validators=[InputRequired()])
    hora_fin = SelectField("Hasta", choices=_opciones_horas(), validators=[InputRequired()])
    submit = SubmitField("Agregar")

    def validate_hora_fin(self, field):
        if self.hora_inicio.data and field.data and _a_time(field.data) <= _a_time(self.hora_inicio.data):
            raise ValidationError("La hora de fin debe ser posterior a la de inicio.")

    @property
    def hora_inicio_time(self):
        return _a_time(self.hora_inicio.data)

    @property
    def hora_fin_time(self):
        return _a_time(self.hora_fin.data)


class BloqueoForm(FlaskForm):
    # 0 = "Todo el negocio"; el resto, ids de recursos del negocio.
    recurso_id = SelectField("Aplica a", coerce=int, validators=[Optional()])
    inicio = DateTimeLocalField("Desde", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    fin = DateTimeLocalField("Hasta", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    motivo = StringField("Motivo", validators=[Optional()])
    submit = SubmitField("Agregar bloqueo")

    def __init__(self, recursos=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recurso_id.choices = [(0, "Todo el negocio")] + [
            (r.id, r.nombre) for r in (recursos or [])
        ]

    def validate_fin(self, field):
        if self.inicio.data and field.data and field.data <= self.inicio.data:
            raise ValidationError("La fecha de fin debe ser posterior a la de inicio.")
