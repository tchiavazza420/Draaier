"""
app/disponibilidad/forms.py
---------------------------
Formularios de horarios y bloqueos.
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, TimeField, StringField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Optional, ValidationError

from app.models.horario import DIAS_SEMANA


class HorarioForm(FlaskForm):
    dia_semana = SelectField(
        "Día",
        coerce=int,
        choices=[(i, nombre) for i, nombre in enumerate(DIAS_SEMANA)],
        validators=[DataRequired()],
    )
    hora_inicio = TimeField("Desde", validators=[DataRequired()])
    hora_fin = TimeField("Hasta", validators=[DataRequired()])
    submit = SubmitField("Agregar franja")

    def validate_hora_fin(self, field):
        if self.hora_inicio.data and field.data and field.data <= self.hora_inicio.data:
            raise ValidationError("La hora de fin debe ser posterior a la de inicio.")


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
