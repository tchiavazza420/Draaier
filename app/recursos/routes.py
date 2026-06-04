"""
app/recursos/routes.py
----------------------
CRUD de tipos de recurso y recursos, dentro del panel del negocio.

TODAS las consultas se hacen con los helpers tenant-aware (query_tenant /
obtener_tenant_o_404) usando current_user.negocio_id: es imposible ver o
editar recursos de otro negocio aunque se manipule el id en la URL.

Autorización:
  - login + rol dueño/staff para todo.
  - escritura (crear/editar/activar) además exige negocio_operativo_required:
    si la suscripción venció, el negocio queda en solo lectura.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.tenant import query_tenant, obtener_tenant_o_404
from app.slugs import generar_slug_unico_scoped
from app.auth.decorators import rol_required, negocio_operativo_required
from app.models.tipo_recurso import TipoRecurso
from app.models.recurso import Recurso
from app.recursos.forms import TipoRecursoForm, RecursoForm
from app.uploads import guardar_imagen

recursos_bp = Blueprint("recursos", __name__)

# Roles autorizados a administrar recursos.
_ROLES_PANEL = ("dueno", "staff")


@recursos_bp.app_context_processor
def _inyectar_opciones_profesional():
    """Expone a las plantillas la URL con todas las fuentes (para el preview)
    y si el negocio actual es de plan individual (una sola agenda)."""
    from app.recursos.opciones import url_todas_las_fuentes
    individual = False
    try:
        if current_user.is_authenticated and getattr(current_user, "negocio", None):
            from app.planes import limite_agendas_de
            individual = limite_agendas_de(current_user.negocio.plan) == 1
    except Exception:
        individual = False
    return {"fuentes_url_todas": url_todas_las_fuentes(),
            "es_plan_individual": individual}


def _neg():
    """negocio_id del usuario logueado (atajo legible)."""
    return current_user.negocio_id


# ======================================================================
#  LISTADO GENERAL
# ======================================================================
@recursos_bp.route("/")
@login_required
@rol_required(*_ROLES_PANEL)
def listar():
    """Lista recursos y tipos del negocio actual."""
    recursos = (
        query_tenant(Recurso, _neg())
        .order_by(Recurso.activo.desc(), Recurso.nombre.asc())
        .all()
    )
    tipos = query_tenant(TipoRecurso, _neg()).order_by(TipoRecurso.nombre).all()
    # En planes individuales (límite 1) no se pueden agregar más profesionales.
    from app.planes import limite_agendas_de
    limite = limite_agendas_de(current_user.negocio.plan)
    puede_agregar = (limite is None) or (len(recursos) < limite)
    individual = limite == 1
    return render_template("recursos/listar.html", recursos=recursos, tipos=tipos,
                           puede_agregar=puede_agregar, individual=individual)


# ======================================================================
#  TIPOS DE RECURSO
# ======================================================================
@recursos_bp.route("/tipos/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_nuevo():
    form = TipoRecursoForm()
    if form.validate_on_submit():
        tipo = TipoRecurso(
            negocio_id=_neg(),
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(TipoRecurso, form.nombre.data, _neg()),
            activo=form.activo.data,
        )
        db.session.add(tipo)
        db.session.commit()
        flash(f"Tipo '{tipo.nombre}' creado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/tipo_form.html", form=form, titulo="Nuevo tipo de recurso")


@recursos_bp.route("/tipos/<int:tipo_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_editar(tipo_id):
    tipo = obtener_tenant_o_404(TipoRecurso, _neg(), tipo_id)
    form = TipoRecursoForm(obj=tipo)
    if form.validate_on_submit():
        # Si cambió el nombre, regeneramos el slug (excluyéndose a sí mismo).
        if form.nombre.data.strip() != tipo.nombre:
            tipo.slug = generar_slug_unico_scoped(
                TipoRecurso, form.nombre.data, _neg(), exclude_id=tipo.id
            )
        tipo.nombre = form.nombre.data.strip()
        tipo.activo = form.activo.data
        db.session.commit()
        flash("Tipo actualizado.", "success")
        return redirect(url_for("recursos.listar"))
    return render_template("recursos/tipo_form.html", form=form, titulo="Editar tipo de recurso")


@recursos_bp.route("/tipos/<int:tipo_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def tipo_toggle(tipo_id):
    """Activa/desactiva un tipo (baja lógica, nunca borrado físico)."""
    tipo = obtener_tenant_o_404(TipoRecurso, _neg(), tipo_id)
    tipo.activo = not tipo.activo
    db.session.commit()
    flash(f"Tipo {'activado' if tipo.activo else 'desactivado'}.", "info")
    return redirect(url_for("recursos.listar"))


# ======================================================================
#  RECURSOS
# ======================================================================
def _categoria_default():
    """
    Devuelve una categoría para asignar a los profesionales. Como ya no
    mostramos categorías en la UI, usamos la primera que exista o creamos una
    "General" oculta (TipoRecurso sigue existiendo en el modelo).
    """
    cat = query_tenant(TipoRecurso, _neg()).first()
    if cat is None:
        cat = TipoRecurso(
            negocio_id=_neg(), nombre="General",
            slug=generar_slug_unico_scoped(TipoRecurso, "General", _neg()),
            activo=True,
        )
        db.session.add(cat)
        db.session.flush()
    return cat


def _aplicar_personalizacion(recurso, form):
    """Vuelca los campos de personalización del formulario al recurso."""
    def limpio(v):
        return (v or "").strip() or None

    from app.recursos import opciones as o

    def opcion(valor, validos, default):
        return valor if valor in validos else default

    recurso.especialidad = limpio(form.especialidad.data)
    recurso.frase = limpio(form.frase.data)
    recurso.descripcion = limpio(form.descripcion.data)
    recurso.habilidades = limpio(form.habilidades.data)
    recurso.anios_experiencia = form.anios_experiencia.data
    recurso.color_acento = limpio(form.color_acento.data)
    recurso.estilo_cabecera = form.estilo_cabecera.data or "degradado"

    # Redes.
    recurso.instagram = limpio(form.instagram.data)
    recurso.whatsapp = limpio(form.whatsapp.data)
    recurso.tiktok = limpio(form.tiktok.data)
    recurso.pinterest = limpio(form.pinterest.data)
    recurso.facebook = limpio(form.facebook.data)

    # Tipografía / forma / estilo (validados contra el catálogo).
    recurso.tipografia = opcion(form.tipografia.data, o.FUENTES_VALIDAS, o.FUENTE_DEFAULT)
    recurso.estilo_pagina = opcion(form.estilo_pagina.data, o.ESTILOS_VALIDOS, "minimal")
    recurso.forma_foto = opcion(form.forma_foto.data, o.FORMAS_VALIDAS, "circulo")

    # Page-builder: fondo.
    recurso.fondo_tipo = opcion(form.fondo_tipo.data, o.FONDOS_VALIDOS, "gradiente")
    recurso.fondo_patron = opcion(form.fondo_patron.data, o.PATRONES_VALIDOS, "puntos")
    recurso.fondo_color = limpio(form.fondo_color.data)
    recurso.fondo_color2 = limpio(form.fondo_color2.data)
    # Botones.
    recurso.boton_estilo = opcion(form.boton_estilo.data, o.BOTON_ESTILOS_VALIDOS, "sombra_suave")
    recurso.boton_forma = opcion(form.boton_forma.data, o.BOTON_FORMAS_VALIDAS, "redondo")
    recurso.color_boton = limpio(form.color_boton.data)
    recurso.color_boton_texto = limpio(form.color_boton_texto.data)
    recurso.color_titulos = limpio(form.color_titulos.data)
    # Cabecera.
    recurso.avatar_tamano = opcion(form.avatar_tamano.data, o.AVATAR_TAMANOS_VALIDOS, "grande")
    recurso.avatar_posicion = opcion(form.avatar_posicion.data, o.AVATAR_POSICIONES_VALIDAS, "centro")
    recurso.mostrar_portada = bool(form.mostrar_portada.data)
    recurso.portada_efecto = opcion(form.portada_efecto.data, o.PORTADA_EFECTOS_VALIDOS, "original")


def _guardar_negocio_branding(form):
    """Guarda la marca del negocio (logo, descripción, marketplace) — unificado
    dentro del editor de la página. Devuelve None o un mensaje de error."""
    negocio = current_user.negocio
    try:
        logo = guardar_imagen(form.neg_logo.data, _neg(), "logo")
    except ValueError as exc:
        return str(exc)
    if logo:
        negocio.logo_filename = logo
    negocio.descripcion_publica = (form.neg_descripcion.data or "").strip() or None
    negocio.visible_marketplace = form.neg_visible.data
    return None


def _prefill_negocio_branding(form):
    """Precarga los campos de marca del negocio en GET."""
    negocio = current_user.negocio
    form.neg_descripcion.data = negocio.descripcion_publica
    form.neg_visible.data = negocio.visible_marketplace


@recursos_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_nuevo():
    # Límite de profesionales según el plan (Independiente = 1; Locales = varios).
    from app.planes import limite_agendas_de
    limite = limite_agendas_de(current_user.negocio.plan)
    if limite is not None:
        actuales = query_tenant(Recurso, _neg()).count()
        if actuales >= limite:
            flash(f"Tu plan permite hasta {limite} profesional(es). "
                  f"Subí de plan para agregar más.", "warning")
            return redirect(url_for("panel.plan"))

    form = RecursoForm()
    if form.validate_on_submit():
        try:
            foto = guardar_imagen(form.foto.data, _neg(), "profesional")
            banner = guardar_imagen(form.banner.data, _neg(), "portada")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo profesional", recurso=None)
        recurso = Recurso(
            negocio_id=_neg(),
            tipo_recurso_id=_categoria_default().id,
            nombre=form.nombre.data.strip(),
            slug=generar_slug_unico_scoped(Recurso, form.nombre.data, _neg()),
            foto_filename=foto,
            banner_filename=banner,
            capacidad=form.capacidad.data,
            activo=form.activo.data,
        )
        _aplicar_personalizacion(recurso, form)
        err = _guardar_negocio_branding(form)
        if err:
            flash(err, "danger")
            return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo profesional", recurso=None)
        db.session.add(recurso)
        db.session.commit()
        flash(f"Profesional '{recurso.nombre}' creado.", "success")
        return redirect(url_for("recursos.listar"))
    if not form.is_submitted():
        _prefill_negocio_branding(form)
    return render_template("recursos/recurso_form.html", form=form, titulo="Nuevo profesional", recurso=None)


@recursos_bp.route("/<int:recurso_id>/editar", methods=["GET", "POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_editar(recurso_id):
    recurso = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    form = RecursoForm(obj=recurso)
    if form.validate_on_submit():
        # Si subió imágenes nuevas, las guardamos; si no, conservamos las actuales.
        try:
            nueva_foto = guardar_imagen(form.foto.data, _neg(), "profesional")
            nuevo_banner = guardar_imagen(form.banner.data, _neg(), "portada")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("recursos/recurso_form.html", form=form,
                                   titulo="Editar profesional", recurso=recurso)
        if nueva_foto:
            recurso.foto_filename = nueva_foto
        if nuevo_banner:
            recurso.banner_filename = nuevo_banner

        if form.nombre.data.strip() != recurso.nombre:
            recurso.slug = generar_slug_unico_scoped(
                Recurso, form.nombre.data, _neg(), exclude_id=recurso.id
            )
        recurso.nombre = form.nombre.data.strip()
        recurso.capacidad = form.capacidad.data
        recurso.activo = form.activo.data
        _aplicar_personalizacion(recurso, form)
        err = _guardar_negocio_branding(form)
        if err:
            flash(err, "danger")
            return render_template("recursos/recurso_form.html", form=form,
                                   titulo="Editar profesional", recurso=recurso)
        db.session.commit()
        flash("Página actualizada.", "success")
        return redirect(url_for("recursos.listar"))
    if not form.is_submitted():
        _prefill_negocio_branding(form)
    return render_template("recursos/recurso_form.html", form=form,
                           titulo="Editar profesional", recurso=recurso)


@recursos_bp.route("/<int:recurso_id>/toggle", methods=["POST"])
@login_required
@rol_required(*_ROLES_PANEL)
@negocio_operativo_required
def recurso_toggle(recurso_id):
    recurso = obtener_tenant_o_404(Recurso, _neg(), recurso_id)
    recurso.activo = not recurso.activo
    db.session.commit()
    flash(f"Recurso {'activado' if recurso.activo else 'desactivado'}.", "info")
    return redirect(url_for("recursos.listar"))
