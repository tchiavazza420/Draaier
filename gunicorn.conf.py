"""
gunicorn.conf.py
----------------
Configuración del servidor WSGI de producción.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
worker_class = "sync"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = os.environ.get("LOG_LEVEL", "info")
