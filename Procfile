release: flask db upgrade && flask seed-roles
web: gunicorn -c gunicorn.conf.py wsgi:app
worker: celery -A celery_worker.celery worker --loglevel=info
beat: celery -A celery_worker.celery beat --loglevel=info
