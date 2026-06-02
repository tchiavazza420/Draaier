"""
celery_worker.py
----------------
Punto de entrada para el worker y el scheduler (beat) de Celery.

Producción (con Redis levantado y CELERY_EAGER=false):
    celery -A celery_worker.celery worker --loglevel=info
    celery -A celery_worker.celery beat   --loglevel=info

En desarrollo, con CELERY_EAGER=true (default), no hace falta worker: las
tareas corren sincrónicamente dentro de la app.
"""

from app import create_app

flask_app = create_app()
celery = flask_app.extensions["celery"]
