"""
wsgi.py
-------
Punto de entrada WSGI para producción (gunicorn).

    gunicorn -c gunicorn.conf.py wsgi:app
"""

from app import create_app

app = create_app()
