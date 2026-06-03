# AgenPro — Puesta en producción (runbook completo)

Guía paso a paso para dejar AgenPro online, con dominio propio, pagos reales,
emails y WhatsApp. Hacé las fases en orden; cada una funciona por sí sola.

---

## FASE 0 — Pasar las mejoras a producción

Render está conectado a la rama `master`. Para que se actualice:

- **Opción rápida:** mergeá el Pull Request `mejoras-draaier` en GitHub
  (botón **Merge pull request**). Render redeploya solo.
- Cada vez que en el futuro hagas `git push` a `master`, Render vuelve a
  desplegar automáticamente.

---

## FASE 1 — Verificar que está online

1. En Render, esperá que **reservas-web** quede en **Live**. Te da una URL
   `https://reservas-web-xxxx.onrender.com`.
2. Entrá: deberías ver el landing de AgenPro.
3. Creá tu **Super Admin** (administrador de la plataforma). En Render →
   servicio **reservas-web** → pestaña **Shell**:
   ```bash
   flask crear-super-admin tu@email.com UnaClaveSegura123
   ```
4. Probá: registrá un negocio de prueba y hacé una reserva. Todo funciona en
   modo simulado hasta que cargues las credenciales reales (fases siguientes).

> ⚠️ Plan free de Render: si nadie entra por ~15 min, la app "se duerme" y la
> primera carga tarda ~30-50s. Se soluciona con el plan Starter (US$7/mes).

---

## FASE 2 — Dominio propio (ej: draaier.com)

1. **Comprá el dominio** en Cloudflare, Namecheap o (para .com.ar) nic.ar.
2. En Render → **reservas-web → Settings → Custom Domains → Add**. Agregá:
   - `draaier.com`
   - `www.draaier.com`
3. Render te muestra los registros DNS a cargar (un **CNAME** para `www` y un
   **A/ALIAS** para la raíz). Copialos exactos.
4. En el panel DNS de tu registrador, creá esos registros. Guardá.
5. En minutos Render valida el dominio y emite el **HTTPS automático** 🔒.
6. **IMPORTANTE:** en Render → **reservas-web → Environment**, seteá:
   ```
   SITE_URL = https://draaier.com
   ```
   (necesario para que los pagos y webhooks usen tu dominio).

---

## FASE 3 — Pagos reales (Mercado Pago)

Cada negocio puede elegir su pasarela; arrancamos con Mercado Pago (el más
usado en Argentina).

1. Entrá a **https://www.mercadopago.com.ar/developers** con la cuenta de
   Mercado Pago del negocio (o la tuya como plataforma).
2. **Tus integraciones → Crear aplicación** (tipo: pagos online / Checkout Pro).
3. En **Credenciales de producción**, copiá el **Access Token** (empieza con
   `APP_USR-...`) y la **Public Key**.
4. En Render → **reservas-web → Environment**, agregá:
   ```
   MERCADOPAGO_ACCESS_TOKEN = APP_USR-...    (tu access token de producción)
   MERCADOPAGO_PUBLIC_KEY   = APP_USR-...    (tu public key)
   ```
5. Guardá (Render redeploya). Desde ahora, cuando un servicio tenga seña, el
   cliente paga por el **Checkout Pro real** y la reserva se confirma sola al
   acreditarse (vía webhook).

**Webhook:** la app ya envía el `notification_url` correcto
(`https://TU-DOMINIO/pagos/webhook/mercadopago`) en cada pago. No tenés que
configurarlo a mano, pero podés verificarlo en el panel de MP.

**Probar sin cobrar de verdad:** usá las **credenciales de prueba** (sandbox)
y las tarjetas de test de Mercado Pago antes de pasar a producción.

> **Naranja X / Modo:** mismo mecanismo. Conseguí el token del comercio y
> cargá `NARANJA_X_ACCESS_TOKEN` o `MODO_ACCESS_TOKEN`. Sin token, esa pasarela
> sigue en modo simulado. El negocio elige su pasarela en Configuración.

---

## FASE 4 — Emails reales (confirmaciones y recordatorios)

Sin SMTP, los emails quedan en "modo dev" (no salen). Para enviarlos de verdad,
lo más fácil es un proveedor transaccional gratis (Brevo) o Gmail.

**Opción A — Brevo (recomendado, 300 emails/día gratis):**
1. Creá cuenta en https://www.brevo.com → **SMTP & API → SMTP**.
2. Copiá: servidor `smtp-relay.brevo.com`, puerto `587`, tu login y la clave SMTP.
3. En Render → Environment:
   ```
   MAIL_SERVER = smtp-relay.brevo.com
   MAIL_PORT = 587
   MAIL_USE_TLS = true
   MAIL_USERNAME = (tu login de Brevo)
   MAIL_PASSWORD = (tu clave SMTP de Brevo)
   MAIL_DEFAULT_SENDER = AgenPro <no-reply@draaier.com>
   ```

**Opción B — Gmail:** activá verificación en 2 pasos y creá una "Contraseña de
aplicación". Usá `MAIL_SERVER=smtp.gmail.com`, `MAIL_PORT=587`,
`MAIL_USERNAME=tucorreo@gmail.com`, `MAIL_PASSWORD=(app password)`.

---

## FASE 5 — WhatsApp real (opcional)

WhatsApp usa la **Cloud API de Meta** y requiere setup en Meta (toma un rato):

1. Creá una cuenta en **https://developers.facebook.com** y una **Meta Business**.
2. Creá una app de tipo **Business** y agregá el producto **WhatsApp**.
3. Conseguí: el **Phone Number ID** y un **token permanente** (System User token).
4. En Render → Environment:
   ```
   WHATSAPP_TOKEN = (token permanente)
   WHATSAPP_PHONE_ID = (phone number id)
   ```
5. Mientras no esté configurado, los WhatsApp quedan registrados pero no se
   envían (no rompen nada).

> Para mensajes fuera de la "ventana de 24h", Meta exige **plantillas
> aprobadas**. Para confirmaciones inmediatas (al reservar) suele alcanzar con
> el texto libre.

---

## FASE 6 — Recordatorios y vencimientos automáticos (upgrade)

En el plan free, los recordatorios y el vencimiento de suscripciones NO corren
solos (no hay worker). Dos caminos:

**A) Manual / cron externo (gratis):** corré una vez por día, desde el Shell de
Render o un cron externo (cron-job.org):
```bash
flask enviar-recordatorios
flask vencer-suscripciones
```

**B) Automático (plan pago):** en `render.yaml` están comentados los servicios
`worker`, `beat` y `redis`. Descomentalos, ponelos en plan **Starter**, y en la
web cambiá `CELERY_EAGER` a `false` + agregá `REDIS_URL`. Con eso, Celery beat
manda recordatorios (09:00) y vence suscripciones (00:05) solo.

---

## Checklist final de producción

- [ ] PR mergeado a `master` (Render actualizado).
- [ ] App **Live** en Render.
- [ ] **Super Admin** creado.
- [ ] **Dominio propio** verificado + HTTPS.
- [ ] `SITE_URL` = tu dominio.
- [ ] `SECRET_KEY` fuerte (Render lo genera solo).
- [ ] **Mercado Pago** producción (token + public key) si vas a cobrar.
- [ ] **Email** (Brevo/Gmail) para confirmaciones.
- [ ] (Opcional) **WhatsApp** configurado.
- [ ] (Opcional) **Worker + Redis** para recordatorios automáticos.

## Costos orientativos
- Render free: $0 (con "sueño" tras inactividad). Starter: ~US$7/mes por servicio.
- Postgres free de Render: $0 (límites de tamaño/retención).
- Dominio: ~US$10/año.
- Brevo email: gratis hasta 300/día. Mercado Pago: comisión por venta (sin costo fijo).
