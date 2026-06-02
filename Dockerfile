# ---- Imagen de la aplicación (web, worker y beat usan la misma) ----
FROM python:3.12-slim

# Buenas prácticas: no escribir .pyc, salida sin buffer.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=run.py

WORKDIR /app

# psycopg[binary] trae libpq embebido, así que no hacen falta libs del sistema.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker/entrypoint.sh

EXPOSE 8000

# El entrypoint espera a Postgres y (en web) corre migraciones + seed.
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
