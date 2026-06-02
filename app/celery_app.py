"""
app/celery_app.py
-----------------
Integración de Celery con Flask.

make_celery() crea la instancia de Celery configurada desde la app Flask y
con un Task base que ejecuta dentro del app context (para que las tareas
tengan acceso a la base de datos, el mailer, etc.).

Modo EAGER (default en dev): las tareas .delay() corren sincrónicamente en el
mismo proceso, sin necesidad de Redis. En producción (CELERY_EAGER=false) se
encolan en Redis y las procesa un worker.

Programación (Celery beat):
  - recordatorios diarios (09:00 UTC)
  - vencimiento de suscripciones (00:05 UTC)
"""

from celery import Celery, Task
from celery.schedules import crontab


def make_celery(app):
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name, task_cls=FlaskTask)
    celery.conf.update(app.config["CELERY"])
    celery.conf.beat_schedule = {
        "recordatorios-diarios": {
            "task": "tareas.recordatorios",
            "schedule": crontab(hour=9, minute=0),
            "args": (1,),
        },
        "vencer-suscripciones-diario": {
            "task": "tareas.vencer_suscripciones",
            "schedule": crontab(hour=0, minute=5),
        },
    }
    celery.set_default()
    app.extensions["celery"] = celery
    return celery
