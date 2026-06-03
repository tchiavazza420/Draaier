"""
app/auth/forms.py
-----------------
Formularios de autenticación con Flask-WTF (incluye protección CSRF
automática gracias al SECRET_KEY configurado).

- RegistroNegocioForm: alta de un negocio nuevo + su usuario dueño.
- LoginForm: inicio de sesión.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Regexp,
)

from app.models.negocio import RUBROS_BELLEZA


class RegistroNegocioForm(FlaskForm):
    """Registro combinado: datos del negocio + credenciales del dueño."""

    # --- Datos del negocio ---
    nombre_negocio = StringField(
        "Nombre del negocio",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    rubro = SelectField(
        "Rubro",
        validators=[DataRequired()],
        # Las choices se cargan en __init__ desde el enum.
    )
    ciudad = StringField(
        "Ciudad",
        validators=[Length(max=80)],
    )

    # --- Datos del dueño ---
    nombre = StringField(
        "Tu nombre",
        validators=[DataRequired(), Length(min=2, max=80)],
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(),
            Length(min=8, message="Mínimo 8 caracteres."),
            Regexp(
                r"^(?=.*[A-Za-z])(?=.*\d).+$",
                message="Debe incluir al menos una letra y un número.",
            ),
        ],
    )
    password2 = PasswordField(
        "Repetir contraseña",
        validators=[
            DataRequired(),
            EqualTo("password", message="Las contraseñas no coinciden."),
        ],
    )

    submit = SubmitField("Crear mi cuenta")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo rubros de belleza/estética.
        self.rubro.choices = [
            (r.value, r.value.replace("_", " ").title()) for r in RUBROS_BELLEZA
        ]


class LoginForm(FlaskForm):
    """Inicio de sesión por email + contraseña."""

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired()],
    )
    remember = BooleanField("Mantener sesión iniciada")
    submit = SubmitField("Ingresar")
