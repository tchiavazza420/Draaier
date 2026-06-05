"""
app/notificaciones/push.py
---------------------------
Notificaciones Web Push (PWA) hacia el panel del negocio.

- `esta_configurado()`: hay claves VAPID cargadas.
- `guardar_suscripcion()`: alta/idempotente de una suscripción del navegador.
- `enviar_a_negocio()`: manda un push a todas las suscripciones del negocio.

Sin claves VAPID, todo es no-op silencioso (modo desarrollo). Si una
suscripción ya no es válida (410/404), se elimina sola.
"""

import json

from flask import current_app

from app.extensions import db
from app.models.push import PushSubscription


def esta_configurado():
    return bool(current_app.config.get("VAPID_PUBLIC_KEY")
                and current_app.config.get("VAPID_PRIVATE_KEY"))


def clave_publica():
    return current_app.config.get("VAPID_PUBLIC_KEY")


def guardar_suscripcion(negocio_id, usuario_id, sub, user_agent=None):
    """
    Crea o actualiza una suscripción a partir del objeto JSON del navegador
    (`{endpoint, keys:{p256dh, auth}}`). Devuelve la PushSubscription.
    """
    endpoint = (sub or {}).get("endpoint")
    keys = (sub or {}).get("keys") or {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if not (endpoint and p256dh and auth):
        raise ValueError("Suscripción push inválida.")

    existente = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existente is None:
        existente = PushSubscription(endpoint=endpoint)
        db.session.add(existente)
    existente.negocio_id = negocio_id
    existente.usuario_id = usuario_id
    existente.p256dh = p256dh
    existente.auth = auth
    existente.user_agent = (user_agent or "")[:255] or None
    db.session.commit()
    return existente


def _claims():
    return {"sub": current_app.config.get("VAPID_CLAIM_EMAIL", "mailto:soporte@agenpro.com.ar")}


def enviar_a_negocio(negocio_id, titulo, cuerpo, url="/panel"):
    """
    Envía un push a todas las suscripciones del negocio. Devuelve cuántos
    envíos se hicieron. No-op si no hay claves VAPID configuradas.
    """
    if not esta_configurado():
        return 0

    from pywebpush import webpush, WebPushException

    subs = PushSubscription.query.filter_by(negocio_id=negocio_id).all()
    if not subs:
        return 0

    payload = json.dumps({"title": titulo, "body": cuerpo, "url": url})
    private_key = current_app.config["VAPID_PRIVATE_KEY"]
    enviados = 0
    for s in subs:
        try:
            webpush(
                subscription_info=s.to_subscription_info(),
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(_claims()),
                timeout=10,
            )
            enviados += 1
        except WebPushException as exc:
            # 404/410: suscripción muerta -> la borramos.
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                db.session.delete(s)
            else:
                current_app.logger.warning("Push fallido (%s): %s", status, exc)
        except Exception:
            current_app.logger.exception("Error enviando push")
    db.session.commit()
    return enviados
