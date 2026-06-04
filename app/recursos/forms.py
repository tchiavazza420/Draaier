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
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


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
    frase = StringField(
        "Frase / lema",
        validators=[Optional(), Length(max=160)],
    )
    foto = FileField("Foto de perfil", validators=[
        Optional(), FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes.")])
    banner = FileField("Portada", validators=[
        Optional(), FileAllowed(["png", "jpg", "jpeg", "webp", "gif"], "Solo imágenes.")])
    descripcion = TextAreaField(
        "Bio / descripción",
        validators=[Optional(), Length(max=2000)],
    )
    habilidades = StringField(
        "Habilidades (separadas por coma)",
        validators=[Optional(), Length(max=400)],
    )
    anios_experiencia = IntegerField(
        "Años de experiencia",
        validators=[Optional(), NumberRange(min=0, max=80)],
    )
    color_acento = StringField(
        "Color de acento",
        validators=[Optional(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="Color inválido.")],
    )
    estilo_cabecera = SelectField(
        "Estilo de cabecera",
        choices=[("degradado", "Degradado"), ("solido", "Color sólido"),
                 ("foto", "Foto de portada")],
        default="degradado",
    )
    # validate_choice=False: si llega un valor fuera de catálogo (POST
    # manipulado), no falla el form; la ruta lo mapea al default seguro.
    tipografia = SelectField("Tipografía", default="Plus Jakarta Sans", validate_choice=False)
    estilo_pagina = SelectField("Estilo de página", default="minimal", validate_choice=False)
    forma_foto = SelectField("Forma de la foto", default="circulo", validate_choice=False)

    # --- Page-builder: fondo ---
    fondo_tipo = SelectField("Fondo", default="gradiente", validate_choice=False)
    fondo_patron = SelectField("Patrón", default="puntos", validate_choice=False)
    _color = lambda label: StringField(label, validators=[  # noqa: E731
        Optional(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="Color inválido.")])
    fondo_color = _color("Color de fondo")
    fondo_color2 = _color("Color de fondo 2")
    # --- Botones ---
    boton_estilo = SelectField("Estilo de botones", default="sombra_suave", validate_choice=False)
    boton_forma = SelectField("Forma de botones", default="redondo", validate_choice=False)
    color_boton = _color("Color de botones")
    color_boton_texto = _color("Texto de botones")
    color_titulos = _color("Color de títulos")
    # --- Cabecera ---
    avatar_tamano = SelectField("Tamaño del avatar", default="grande", validate_choice=False)
    mostrar_portada = BooleanField("Mostrar portada", default=True)
    portada_efecto = SelectField("Efecto de portada", default="original", validate_choice=False)
    # --- Redes ---
    instagram = StringField("Instagram", validators=[Optional(), Length(max=120)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=40)])
    tiktok = StringField("TikTok", validators=[Optional(), Length(max=120)])
    pinterest = StringField("Pinterest", validators=[Optional(), Length(max=120)])
    facebook = StringField("Facebook (URL)", validators=[Optional(), Length(max=120)])

    capacidad = IntegerField(
        "Cupos por turno",
        validators=[DataRequired(), NumberRange(min=1, max=10000)],
        default=1,
    )
    activo = BooleanField("Activo", default=True)
    submit = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Poblamos las opciones de personalización desde el catálogo.
        from app.recursos import opciones as o
        self.tipografia.choices = [(f[0], f[1]) for f in o.FUENTES]
        self.estilo_pagina.choices = list(o.ESTILOS_PAGINA)
        self.forma_foto.choices = list(o.FORMAS_FOTO)
        self.fondo_tipo.choices = list(o.FONDOS)
        self.fondo_patron.choices = list(o.PATRONES)
        self.boton_estilo.choices = list(o.BOTON_ESTILOS)
        self.boton_forma.choices = list(o.BOTON_FORMAS)
        self.avatar_tamano.choices = list(o.AVATAR_TAMANOS)
        self.portada_efecto.choices = list(o.PORTADA_EFECTOS)
