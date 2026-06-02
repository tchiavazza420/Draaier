"""
app/panel/forms.py
------------------
Formularios de configuración del negocio (datos públicos + marketplace).
La personalización visual (logo, colores, etc.) se agrega en el Paso 12.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email

from app.models.negocio import RubroEnum


class NegocioConfigForm(FlaskForm):
    nombre = StringField("Nombre del negocio", validators=[DataRequired(), Length(min=2, max=120)])
    rubro = SelectField("Rubro", validators=[DataRequired()])
    ciudad = StringField("Ciudad", validators=[Optional(), Length(max=80)])
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=40)])
    email = StringField("Email de contacto", validators=[DataRequired(), Email(), Length(max=120)])
    visible_marketplace = BooleanField("Aparecer en el Marketplace público")
    submit = SubmitField("Guardar cambios")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubro.choices = [(r.value, r.value.replace("_", " ").title()) for r in RubroEnum]
