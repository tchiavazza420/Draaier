# Guía de Deploy

El proyecto está listo para desplegarse de tres formas. En todas, la app
corre en modo producción (`FLASK_ENV=production`, `CELERY_EAGER=false`) con
Postgres + Redis + worker + beat.

> **Importante:** generá un `SECRET_KEY` real:
> `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Opción A — Render (recomendado para empezar, tiene plan free)

1. Subí el repo a GitHub.
2. En [Render](https://render.com): **New → Blueprint** y elegí el repo.
3. Render detecta `render.yaml` y crea: web + worker + beat + Postgres + Redis.
   - `SECRET_KEY` se genera solo; `DATABASE_URL` y `REDIS_URL` se inyectan.
   - Las migraciones y el seed de roles corren en `preDeployCommand`.
4. (Opcional) En el servicio **reservas-web → Environment**, agregá las claves
   de pagos/email/WhatsApp que quieras activar:
   `MERCADOPAGO_ACCESS_TOKEN`, `MAIL_SERVER`/`MAIL_USERNAME`/`MAIL_PASSWORD`,
   `WHATSAPP_TOKEN`/`WHATSAPP_PHONE_ID`, y `SITE_URL` (la URL pública de Render).
5. Deploy. Cuando esté arriba, creá el super admin desde el **Shell** del
   servicio web: `flask crear-super-admin tu@email.com TuClaveSegura`.

---

## Opción B — Railway

1. Subí el repo a GitHub e importalo en [Railway](https://railway.app).
2. Agregá los plugins **PostgreSQL** y **Redis** (inyectan `DATABASE_URL` y
   `REDIS_URL` automáticamente).
3. Railway usa el `Procfile`:
   - `release`: corre migraciones + seed de roles en cada deploy.
   - `web`: gunicorn (Railway setea `PORT`, que `gunicorn.conf.py` respeta).
   - `worker` y `beat`: agregalos como servicios extra apuntando al mismo repo
     con start command `celery -A celery_worker.celery worker` / `... beat`.
4. Variables a setear: `SECRET_KEY`, `FLASK_ENV=production`,
   `CELERY_EAGER=false`, `SITE_URL`, y las claves opcionales de pagos/email/WA.
5. Crear super admin desde la consola del servicio:
   `flask crear-super-admin tu@email.com TuClaveSegura`.

---

## Opción C — VPS propio (Docker)

Cualquier servidor con Docker:

```bash
git clone <tu-repo> && cd <repo>
cp .env.docker.example .env.docker     # completar SECRET_KEY y secretos
docker compose up -d --build           # http://servidor:8000
docker compose exec web flask crear-super-admin tu@email.com TuClave
```

Para HTTPS, poné un reverse proxy (Caddy o Nginx) delante del puerto 8000.
Ejemplo mínimo con Caddy (`Caddyfile`):

```
tudominio.com {
    reverse_proxy localhost:8000
}
```

---

## Checklist post-deploy

- [ ] `SECRET_KEY` fuerte y único.
- [ ] `SITE_URL` apunta a la URL pública (necesario para back_urls/webhooks de pago).
- [ ] Super admin creado (`flask crear-super-admin`).
- [ ] Credenciales reales de Mercado Pago / email / WhatsApp si vas a usarlos
      (sin ellas, funcionan en modo simulación/bandeja dev).
- [ ] Worker y beat corriendo (recordatorios y vencimientos automáticos).
