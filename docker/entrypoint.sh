#!/bin/sh
# ---------------------------------------------------------------------------
# Entrypoint: espera a Postgres y, solo en el servicio web (RUN_MIGRATIONS=1),
# aplica migraciones y siembra los roles. Luego ejecuta el comando recibido
# (gunicorn / celery worker / celery beat).
# ---------------------------------------------------------------------------
set -e

echo "Esperando a PostgreSQL..."
python - <<'PY'
import os, time
import psycopg
url = os.environ["DATABASE_URL"].replace("+psycopg", "")
for intento in range(60):
    try:
        psycopg.connect(url, connect_timeout=3).close()
        print("PostgreSQL listo.")
        break
    except Exception as exc:
        print(f"  ...todavía no ({exc}). Reintentando.")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL no estuvo disponible a tiempo.")
PY

if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "Aplicando migraciones..."
    flask db upgrade
    echo "Sembrando roles del sistema..."
    flask seed-roles
fi

exec "$@"
