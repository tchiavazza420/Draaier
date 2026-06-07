# Activar Celery + Redis (envíos asíncronos) — paso a paso

## ¿Para qué sirve?
Hoy las notificaciones (email, WhatsApp, push) se mandan **dentro del request
web**: cuando alguien reserva, la web espera a que se envíen antes de responder.
Funciona perfecto con poco volumen, pero a medida que crece:

- El cliente **espera** a que termine el envío (la página tarda más).
- Si hay muchas reservas a la vez, la web se **satura**.

Con **Celery + Redis**, los envíos se hacen en **segundo plano** (un proceso
"worker" aparte): la web responde **al instante** y aguanta muchos más usuarios.
Además, si un envío falla, se puede **reintentar** sin afectar la reserva.

> Es **opcional**. Mientras `CELERY_EAGER=true` (lo de hoy), todo funciona sin
> Redis ni worker. Esto es para **escalar** cuando tengas volumen.

---

## Qué vas a crear en Render (3 cosas)
1. **Redis** (un servicio "Key Value") → la cola de tareas.
2. **Worker** (un servicio aparte) → procesa los envíos en segundo plano.
3. Un par de **variables** en la web y en el worker.

Hay dos caminos: **A) por Blueprint** (editar `render.yaml` y sincronizar) o
**B) a mano** en el panel de Render. Recomiendo el **B** si ya tenés los
servicios creados.

---

## Camino A — Por Blueprint (render.yaml)
En `render.yaml` ya está la sección lista, **comentada**, al final del archivo
(bloque "ESCALADO A ASYNC"). Para activarla:

1. **Descomentá** ese bloque (Redis + worker + beat). Quitá los `#` del inicio
   de cada línea de esa sección.
2. En el servicio **web**, cambiá:
   ```
   CELERY_EAGER = "false"
   ```
   y agregá la variable `REDIS_URL` tomada del servicio Redis (en el yaml:
   `fromService: { type: keyvalue, name: reservas-redis, property: connectionString }`).
3. Subí el cambio y en Render: **Blueprint → Sync**. Render crea Redis + worker y
   reinicia la web.

> El **beat** (scheduler) **no hace falta**: los recordatorios ya los dispara el
> Cron Job (`/tareas/correr`). Podés dejar el beat comentado.

---

## Camino B — A mano en el panel de Render (recomendado)

### 1) Crear Redis
- Render → **New → Key Value** (Redis).
- Nombre: `reservas-redis`. Plan: el más chico (Starter alcanza).
- ** Maxmemory policy**: `noeviction` (o `allkeys-lru`).
- Crealo y copiá su **Internal Connection String** (algo como
  `redis://red-xxxx:6379`).

### 2) Crear el Worker
- Render → **New → Background Worker**.
- Conectalo al **mismo repo** (rama `master`).
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:**
  ```
  celery -A celery_worker.celery worker --loglevel=info --concurrency=2
  ```
- **Environment**: cargá **las MISMAS variables que la web** (esto es clave: el
  worker es el que ahora envía, así que necesita todas las credenciales):
  ```
  FLASK_APP=run.py
  CELERY_EAGER=false
  REDIS_URL=<Internal Connection String del Redis>
  DATABASE_URL=<el mismo de la web>
  SECRET_KEY=<el mismo de la web>
  SITE_URL=https://www.agenpro.com.ar
  # --- envíos (los mismos que la web) ---
  MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
  WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_API_VERSION
  WHATSAPP_TEMPLATE_CONFIRMACION, WHATSAPP_TEMPLATE_RECORDATORIO, WHATSAPP_TEMPLATE_IDIOMA
  CLOUDINARY_URL
  VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIM_EMAIL
  ```

### 3) Tocar la Web
- Render → servicio **web** → **Environment**:
  ```
  CELERY_EAGER=false
  REDIS_URL=<el mismo Internal Connection String del Redis>
  ```
- **Save** → la web redeploya.

---

## Cómo verificar que anda
1. Esperá a que **web** y **worker** queden en *Live*.
2. En el worker → **Logs**: tenés que ver algo como
   `celery@... ready.` y las colas conectadas a Redis.
3. Hacé una **reserva de prueba**. En los logs del **worker** debería aparecer
   una tarea `tareas.notificar_reserva` procesándose, y te llega el email/WhatsApp.
4. La web debería responder más rápido (no espera el envío).

> Si el worker no levanta: casi siempre es `REDIS_URL` mal (usá la **Internal**,
> no la externa) o falta `DATABASE_URL` en el worker.

---

## Notas
- El **Cron de recordatorios** (`/tareas/correr`) sigue funcionando igual: ese
  endpoint llama a la lógica **directo** (no por Celery), así que no depende del
  worker. Lo que pasa a segundo plano son las notificaciones por evento
  (confirmación, "turno nuevo", cancelación, etc.).
- Costo: Redis + Worker suman un poco al plan de Render. Tenelo en cuenta solo
  cuando el volumen lo justifique.
- Para **volver atrás**: poné `CELERY_EAGER=true` en la web (vuelve a enviar
  sincrónico) y podés pausar el worker/Redis.
