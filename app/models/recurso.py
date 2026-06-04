"""
app/models/recurso.py
---------------------
Recurso: la unidad reservable del sistema.

El sistema NO gira alrededor de "profesionales" sino de recursos genéricos:
una persona, una cancha, una sala, un consultorio, etc. Cada reserva (en el
módulo de reservas) apuntará a un Recurso.

Campos clave:
  - capacidad: cuántas reservas simultáneas admite el recurso en un mismo
    turno. Manicura/cancha = 1; clase grupal = 20. La disponibilidad real
    se calculará dinámicamente en el módulo de reservas usando este valor.
  - slug: único por negocio, alimenta la URL pública
    /slug-negocio/recurso/slug-recurso.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin, TenantMixin


class Recurso(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "recursos"

    id = db.Column(db.Integer, primary_key=True)
    # negocio_id lo aporta TenantMixin.

    tipo_recurso_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_recurso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # --- Página pública del profesional (personalización propia) ---
    foto_filename = db.Column(db.String(200), nullable=True)
    banner_filename = db.Column(db.String(200), nullable=True)  # portada de su página
    especialidad = db.Column(db.String(80), nullable=True)      # ej: Colorista, Barbero
    frase = db.Column(db.String(160), nullable=True)            # tagline bajo el nombre
    # Color de acento propio (hex). Si es NULL, usa el color del negocio.
    color_acento = db.Column(db.String(7), nullable=True)
    # Estilo visual de la cabecera de su página.
    estilo_cabecera = db.Column(db.String(20), nullable=False, default="degradado")
    # Tipografía (familia de Google Fonts) de su página.
    tipografia = db.Column(db.String(60), nullable=False, default="Plus Jakarta Sans")
    # Tema visual de la página (minimal / elegante / moderno / glam).
    estilo_pagina = db.Column(db.String(20), nullable=False, default="minimal")
    # Forma del avatar (circulo / rounded / hexagono).
    forma_foto = db.Column(db.String(20), nullable=False, default="circulo")
    anios_experiencia = db.Column(db.Integer, nullable=True)
    # Habilidades / etiquetas separadas por coma (se muestran como chips).
    habilidades = db.Column(db.String(400), nullable=True)
    # Redes propias del profesional.
    instagram = db.Column(db.String(120), nullable=True)
    whatsapp = db.Column(db.String(40), nullable=True)
    tiktok = db.Column(db.String(120), nullable=True)
    pinterest = db.Column(db.String(120), nullable=True)
    facebook = db.Column(db.String(120), nullable=True)

    # ====== Page-builder estilo Linktree (todos nullable; defaults app-side) ======
    # Fondo del sitio.
    fondo_tipo = db.Column(db.String(20), nullable=True)     # solido/gradiente/patron/animado
    fondo_color = db.Column(db.String(7), nullable=True)
    fondo_color2 = db.Column(db.String(7), nullable=True)    # 2do color del gradiente
    fondo_patron = db.Column(db.String(20), nullable=True)   # puntos/ondas/cuadricula/diagonal
    # Botones.
    boton_estilo = db.Column(db.String(20), nullable=True)   # solido/cristal/contorno/sombra_suave/sombra_fuerte
    boton_forma = db.Column(db.String(20), nullable=True)    # recto/suave/redondo
    color_boton = db.Column(db.String(7), nullable=True)
    color_boton_texto = db.Column(db.String(7), nullable=True)
    # Colores de texto.
    color_titulos = db.Column(db.String(7), nullable=True)
    # Cabecera.
    avatar_tamano = db.Column(db.String(12), nullable=True)  # pequeno/grande
    mostrar_portada = db.Column(db.Boolean, nullable=True)   # None=True
    portada_efecto = db.Column(db.String(16), nullable=True) # original/blur/gradiente/fade/vineta/duotono

    # Valores por defecto efectivos (si el campo está vacío en la DB).
    _DEFAULTS = {
        "fondo_tipo": "gradiente", "fondo_color": "#fff1f2", "fondo_patron": "none",
        "boton_estilo": "sombra_suave", "boton_forma": "redondo",
        "color_boton": "#6d28d9", "color_boton_texto": "#ffffff",
        "avatar_tamano": "grande", "portada_efecto": "original",
    }

    def estilo(self, campo):
        """Valor efectivo de un campo de estilo (con su default si está vacío)."""
        return getattr(self, campo, None) or self._DEFAULTS.get(campo)

    @property
    def portada_visible(self):
        """True salvo que se haya desactivado explícitamente la portada."""
        return self.mostrar_portada is not False

    @property
    def habilidades_lista(self):
        """Devuelve las habilidades como lista limpia (sin vacíos)."""
        if not self.habilidades:
            return []
        return [h.strip() for h in self.habilidades.split(",") if h.strip()]

    # Cupos simultáneos por turno. >= 1.
    capacidad = db.Column(db.Integer, nullable=False, default=1)

    activo = db.Column(db.Boolean, nullable=False, default=True)

    # --- Relaciones ---
    tipo = db.relationship("TipoRecurso", back_populates="recursos")

    __table_args__ = (
        db.UniqueConstraint("negocio_id", "slug", name="uq_recurso_negocio_slug"),
        db.CheckConstraint("capacidad >= 1", name="ck_recurso_capacidad_min"),
    )

    def __repr__(self):
        return f"<Recurso {self.id} {self.nombre!r} cap={self.capacidad} neg={self.negocio_id}>"
