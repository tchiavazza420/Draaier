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
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class TipoRecursoForm(FlaskForm):
    nombre = StringField(
        "Nombre de la categoría",
        validators=[DataRequired(), Length(min=2, max=60)],
    )
    activo = BooleanField("Activa", default=True)
    submit = SubmitField("Guardar")


class RecursoForm(FlaskForm):
    nombre = StringField(
        "Nombre del profesional",
        validators=[DataRequired(), Length(min=1, max=120)],
    )
    especialidad = StringField(
        "Especialidad",
        validators=[Optional(), Length(max=80)],
    )
    foto = FileField("Foto", validators=[
        Optional(), FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes.")])
    descripcion = TextAreaField(
        "Bio / descripción",
        validators=[Optional(), Length(max=2000)],
    )
    capacidad = IntegerField(
        "Cupos por turno",
        validators=[DataRequired(), NumberRange(min=1, max=10000)],
        default=1,
    )
    activo = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar")
