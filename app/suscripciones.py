"""
app/suscripciones.py
--------------------
Rutinas de mantenimiento de suscripciones, reutilizadas por el CLI y por las
tareas programadas de Celery (DRY).
"""

from app.extensions import db
from app.models.negocio import Negocio, EstadoSuscripcionEnum


def vencer_suscripciones():
    """
    Marca como VENCIDA toda suscripción TRIAL/ACTIVA cuya vigencia ya pasó.
    Devuelve la cantidad de negocios afectados.
    """
    candidatos = Negocio.query.filter(
        Negocio.estado_suscripcion.in_([
            EstadoSuscripcionEnum.TRIAL, EstadoSuscripcionEnum.ACTIVA,
        ])
    ).all()
    from app.notificaciones import centro
    vencidos = 0
    afectados = []
    for neg in candidatos:
        if neg.esta_vencido:
            neg.estado_suscripcion = EstadoSuscripcionEnum.VENCIDA
            afectados.append(neg.id)
            vencidos += 1
    db.session.commit()
    # Aviso in-app de vencimiento (campanita).
    for neg_id in afectados:
        centro.crear(neg_id, "vencimiento", "Tu suscripción venció",
                     "Renová tu plan para seguir recibiendo reservas.",
                     url=None)
    return vencidos


def avisar_vencimientos_proximos(dias=3):
    """
    Crea un aviso in-app para los negocios cuya suscripción vence dentro de
    `dias` días (y todavía está vigente). Devuelve la cantidad avisada.
    Evita duplicar: solo avisa si no hay un aviso de vencimiento sin leer.
    """
    from datetime import datetime, timezone, timedelta
    from app.notificaciones import centro
    from app.models.notificacion import Notificacion

    limite = datetime.now(timezone.utc) + timedelta(days=dias)
    candidatos = Negocio.query.filter(
        Negocio.estado_suscripcion.in_([
            EstadoSuscripcionEnum.TRIAL, EstadoSuscripcionEnum.ACTIVA,
        ])
    ).all()
    avisados = 0
    for neg in candidatos:
        fin = neg.vencimiento
        if fin is None:
            continue
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < fin <= limite:
            ya = Notificacion.query.filter_by(
                negocio_id=neg.id, tipo="vencimiento", leida=False).first()
            if ya is None:
                centro.crear(neg.id, "vencimiento", "Tu suscripción vence pronto",
                             f"Vence el {fin.strftime('%d/%m')}. Renová para no cortar el servicio.")
                avisados += 1
    return avisados
