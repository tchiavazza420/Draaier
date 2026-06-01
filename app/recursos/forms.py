"""
app/recursos/forms.py
---------------------
Formularios del módulo de recursos (Flask-WTF + CSRF).

- TipoRecursoForm: alta/edición de un tipo de recurso.
- RecursoForm: alta/edición de un recurso. El campo `tipo_recurso` se llena
  dinámicamente con los tipos del negocio actual (se pasan al construir el
  formulario, nunca se confía en valores arbitrarios del cliente).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class TipoRecursoForm(FlaskForm):
    nombre = StringField(
        "Nombre del tipo",
        validators=[DataRequired(), Length(min=2, max=60)],
    )
    activo = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar")


class RecursoForm(FlaskForm):
    tipo_recurso = SelectField(
        "Tipo de recurso",
        coerce=int,
        validators=[DataRequired(message="Elegí un tipo.")],
    )
    nombre = StringField(
        "Nombre del recurso",
        validators=[DataRequired(), Length(min=1, max=120)],
    )
    capacidad = IntegerField(
        "Capacidad (cupos simultáneos)",
        validators=[DataRequired(), NumberRange(min=1, max=10000)],
        default=1,
    )
    descripcion = TextAreaField(
        "Descripción",
        validators=[Optional(), Length(max=2000)],
    )
    activo = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar")

    def __init__(self, tipos=None, *args, **kwargs):
        """
        `tipos` es la lista de TipoRecurso del negocio actual. Sus ids
        definen las únicas opciones válidas del select (anti-manipulación).
        """
        super().__init__(*args, **kwargs)
        self.tipo_recurso.choices = [
            (t.id, t.nombre) for t in (tipos or [])
        ]
