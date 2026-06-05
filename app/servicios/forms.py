"""
app/servicios/forms.py
----------------------
Formulario de servicios (Flask-WTF + CSRF).

El campo `recursos` es una selección múltiple cuyas opciones se cargan
dinámicamente con los recursos del negocio actual: nunca se confía en ids
arbitrarios enviados por el cliente.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, IntegerField, DecimalField,
    SelectMultipleField, BooleanField, SubmitField, RadioField,
)
from wtforms.validators import (
    DataRequired, Length, NumberRange, Optional, Regexp, ValidationError,
)


class ServicioForm(FlaskForm):
    nombre = StringField(
        "Nombre del servicio",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    duracion_minutos = IntegerField(
        "Duración (minutos)",
        validators=[DataRequired(), NumberRange(min=1, max=1440)],
        default=30,
    )
    precio = DecimalField(
        "Precio",
        places=2,
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    color = StringField(
        "Color (agenda)",
        validators=[
            DataRequired(),
            Regexp(r"^#[0-9A-Fa-f]{6}$", message="Usá un color hex, ej: #3b82f6."),
        ],
        default="#3b82f6",
    )
    recursos = SelectMultipleField(
        "¿Quién/qué lo realiza?",
        coerce=int,
        validators=[Optional()],
    )
    requiere_sena = BooleanField("Requiere seña para reservar", default=False)
    sena_tipo = RadioField(
        "Tipo de seña",
        choices=[("monto", "Monto fijo ($)"), ("porcentaje", "Porcentaje del precio (%)")],
        default="monto",
    )
    sena_monto = DecimalField(
        "Monto de la seña",
        places=2,
        validators=[Optional(), NumberRange(min=0)],
    )
    sena_porcentaje = IntegerField(
        "Porcentaje de la seña",
        validators=[Optional(), NumberRange(min=1, max=100)],
    )
    descripcion = TextAreaField(
        "Descripción",
        validators=[Optional(), Length(max=2000)],
    )
    activo = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar")

    def validate_sena_monto(self, field):
        if (self.requiere_sena.data and self.sena_tipo.data == "monto"
                and not field.data):
            raise ValidationError("Indicá el monto de la seña o desactivá la opción.")

    def validate_sena_porcentaje(self, field):
        if (self.requiere_sena.data and self.sena_tipo.data == "porcentaje"
                and not field.data):
            raise ValidationError("Indicá el porcentaje de la seña o desactivá la opción.")

    def __init__(self, recursos_disponibles=None, *args, **kwargs):
        """`recursos_disponibles`: lista de Recurso del negocio (define opciones)."""
        super().__init__(*args, **kwargs)
        self.recursos.choices = [
            (r.id, f"{r.nombre} · {r.tipo.nombre}")
            for r in (recursos_disponibles or [])
        ]
