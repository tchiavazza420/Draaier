"""
app/auth/decorators.py
----------------------
Decoradores de autorización.

- rol_required(*roles): exige que el usuario tenga uno de los roles dados.
- super_admin_required: atajo para exigir el rol super_admin.
- negocio_operativo_required: bloquea acciones de escritura si la suscripción
  del negocio está vencida/cancelada (regla del brief: "al vencer, solo lectura").

Se apoyan en Flask-Login (current_user). Combinarlos siempre DESPUÉS de
@login_required para garantizar que haya un usuario autenticado.
"""

from functools import wraps

from flask import abort
from flask_login import current_user

from app.errors import PagoRequerido


def rol_required(*roles_permitidos):
    """
    Permite el acceso solo si current_user tiene uno de los roles indicados.
    Uso:  @rol_required("dueno", "super_admin")
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.rol is None or current_user.rol.nombre not in roles_permitidos:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def super_admin_required(view):
    """Atajo: solo el super_admin de la plataforma."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.es_super_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def negocio_operativo_required(view):
    """
    Bloquea la acción si el negocio del usuario no puede operar
    (suscripción vencida/cancelada o negocio inactivo). Devuelve 402
    (Payment Required) para diferenciarlo de un 403 de permisos.
    El super_admin queda exento.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.es_super_admin:
            return view(*args, **kwargs)
        negocio = current_user.negocio
        if negocio is None or not negocio.puede_operar:
            raise PagoRequerido()
        return view(*args, **kwargs)
    return wrapped
