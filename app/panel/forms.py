"""
app/panel/forms.py
------------------
Formularios de configuración del negocio (datos públicos + marketplace).
La personalización visual (logo, colores, etc.) se agrega en el Paso 12.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Email, Regexp

from app.models.negocio import RUBROS_BELLEZA, TemplatePublicoEnum

_HEX = Regexp(r"^#[0-9A-Fa-f]{6}$", message="Color hex, ej: #0d6efd.")
_FUENTES = ["Inter", "Roboto", "Poppins", "Montserrat", "Lora", "Nunito"]


class NegocioConfigForm(FlaskForm):
    nombre = StringField("Nombre del negocio", validators=[DataRequired(), Length(min=2, max=120)])
    rubro = SelectField("Rubro", validators=[DataRequired()])
    ciudad = StringField("Ciudad", validators=[Optional(), Length(max=80)])
    direccion = StringField("Dirección (para el mapa)", validators=[Optional(), Length(max=200)])
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=40)])
    email = StringField("Email de contacto", validators=[DataRequired(), Email(), Length(max=120)])
    visible_marketplace = BooleanField("Aparecer en el Marketplace público")
    submit = SubmitField("Guardar cambios")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubro.choices = [(r.value, r.value.replace("_", " ").title()) for r in RUBROS_BELLEZA]


class MensajesForm(FlaskForm):
    notif_confirmacion = BooleanField("Avisar al cliente cuando reserva")
    notif_recordatorio = BooleanField("Enviar recordatorio antes del turno")
    notif_canal_email = BooleanField("Por email")
    notif_canal_whatsapp = BooleanField("Por WhatsApp")
    mensaje_firma = StringField("Firma / saludo final", validators=[Optional(), Length(max=280)])
    submit = SubmitField("Guardar mensajes")


class PersonalizacionForm(FlaskForm):
    logo = FileField("Logo", validators=[
        Optional(), FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes.")])
    banner = FileField("Banner", validators=[
        Optional(), FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes.")])
    color_primario = StringField("Color primario", validators=[DataRequired(), _HEX], default="#0d6efd")
    color_secundario = StringField("Color secundario", validators=[DataRequired(), _HEX], default="#111827")
    tipografia = SelectField("Tipografía", choices=[(f, f) for f in _FUENTES])
    template_publico = SelectField("Plantilla visual")
    descripcion_publica = TextAreaField("Descripción pública", validators=[Optional(), Length(max=2000)])
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    facebook = StringField("Facebook", validators=[Optional(), Length(max=120)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=40)])
    submit = SubmitField("Guardar personalización")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_publico.choices = [
            (t.value, t.value.title()) for t in TemplatePublicoEnum
        ]
