# Integraciones — WhatsApp, Pagos y Recordatorios

Estado real de cada integración y cómo activarlas en producción (Render).
Todas las variables se cargan en **Render → tu servicio web → Environment**.

---

## 1) WhatsApp (recordatorios y confirmaciones)

**Estado: listo en código.** Usa la **WhatsApp Cloud API** de Meta. Sin
credenciales, los mensajes van a una bandeja de desarrollo (no se envían). Con
credenciales, se envían de verdad y se descuentan de los créditos del plan.

### Variables a configurar
```
WHATSAPP_TOKEN=<token permanente de la app de Meta>
WHATSAPP_PHONE_ID=<Phone Number ID del número>
WHATSAPP_API_VERSION=v21.0   (opcional, ya viene por default)
```

### Cómo obtenerlas (resumen)
1. Entrá a **developers.facebook.com** → creá una app tipo **Business**.
2. Agregá el producto **WhatsApp**. Te dan un número de prueba y un
   **Phone Number ID** (ese es `WHATSAPP_PHONE_ID`).
3. Para producción: agregá tu número real, verificá el **Business Manager** y
   generá un **token permanente** (System User Token) → `WHATSAPP_TOKEN`.
4. Las **plantillas** (templates): los mensajes fuera de la ventana de 24 h
   requieren plantillas aprobadas por Meta. Para recordatorios conviene crear
   una plantilla de utilidad y aprobarla. (Hoy enviamos texto plano, que sirve
   dentro de la ventana de 24 h; para recordatorios proactivos vas a querer
   migrar a plantillas — avisame y lo adapto.)

> Importante: el saldo de WhatsApp del plan se consume **solo** cuando hay
> credenciales reales. En modo bandeja no se cobra.

### Recordatorios con plantilla aprobada (fuera de la ventana de 24 h)
Meta solo permite mensajes **proactivos** (recordatorios) mediante una
**plantilla aprobada**. Creá una plantilla de categoría *Utilidad* con 3
variables en el cuerpo (nombre, servicio, fecha/hora), por ejemplo:

> Hola {{1}}, te recordamos tu turno de {{2}} el {{3}}. ¡Te esperamos!

Una vez aprobada, seteá en Render:
```
WHATSAPP_TEMPLATE_RECORDATORIO=<nombre exacto de la plantilla>
WHATSAPP_TEMPLATE_IDIOMA=es_AR   (o el código de idioma con que la aprobaste)
```
Con esto, los recordatorios salen como plantilla (sirven aunque el cliente no
haya escrito en las últimas 24 h). Sin esta variable, se manda texto plano
(solo válido dentro de la ventana de 24 h).

---

## 2) Pagos (señas) — Mercado Pago

La única pasarela es **Mercado Pago (Checkout Pro)**. Igual cubre la mayoría de
los medios: **tarjetas (incluida Naranja), dinero en cuenta y MODO** se pagan
desde el mismo checkout de MP, así que no hace falta integrarlos por separado.

### 2.1) Suscripciones de planes (cuenta de la plataforma)
Los pagos de **planes** los cobra AgenPro a su propia cuenta:
```
MERCADOPAGO_ACCESS_TOKEN=<access token de producción APP_USR-...>
MERCADOPAGO_PUBLIC_KEY=<public key>
```

### 2.2) Señas — cada negocio conecta SU Mercado Pago (OAuth "Connect")
El negocio **no pega ningún token**: en **Configuración** toca
**“🔗 Conectar con Mercado Pago”**, autoriza en MP y volvemos con sus tokens
guardados. A partir de ahí, las señas se cobran **directo a su cuenta**.

Para que el botón funcione, registrá **nuestra** aplicación de Mercado Pago y
cargá sus credenciales en Render:
```
MP_CLIENT_ID=<App ID numérico de la app de MP>
MP_CLIENT_SECRET=<Client Secret de la app>
MP_MARKETPLACE_FEE=0   (opcional: % de comisión que retiene la plataforma)
```

Cómo dar de alta la app (una sola vez):
1. **mercadopago.com.ar/developers** → **Tus integraciones** → crear aplicación.
   Producto: **Pagos online / Checkout Pro**, con **OAuth** habilitado.
2. En la app, agregá la **Redirect URI**:
   `https://www.agenpro.com.ar/pagos/mp/callback` (debe coincidir EXACTO).
3. Copiá **App ID** → `MP_CLIENT_ID` y **Client Secret** → `MP_CLIENT_SECRET`.
4. Listo: cada negocio ve el botón “Conectar con Mercado Pago” en Configuración.

### 2.3) Señas por transferencia (alias/CBU) — todos los planes
Si el negocio **no** usa Mercado Pago, puede cobrar la seña por **transferencia**:
en *Configuración* carga su **alias o CBU** (y titular). En la reserva pública,
el cliente ve el alias y transfiere; el negocio **confirma el pago a mano** desde
el detalle de la reserva (botón "✓ Confirmar seña recibida"). No requiere
credenciales ni configuración extra. Si el negocio tiene MP conectado, se usa MP;
si no, y hay alias, se usa transferencia.

### 2.4) Monto o porcentaje de la seña (por servicio)
La seña se define **en cada servicio** (Servicios → editar): se elige
**Monto fijo ($)** o **Porcentaje del precio (%)**. El porcentaje se calcula
sobre el precio del servicio al momento de reservar.

Notas técnicas:
- Guardamos `access_token`, `refresh_token`, `user_id`, `public_key` y la
  expiración por negocio; el token se **refresca solo** cuando vence.
- El webhook (`/pagos/webhook/mercadopago?neg=<id>`) reconcilia cada seña con el
  token del negocio correspondiente.
- `auto_return` exige `back_urls` en **https** → ya lo cubre `SITE_URL`. En local
  (http) o si el negocio **no conectó** su cuenta, la seña cae a un **checkout
  simulado** interno (útil para desarrollo / probar sin cobrar).

---

## 2.5) Notificaciones push (PWA) + aviso de turno nuevo al negocio

Cuando un cliente reserva desde la página pública, **al negocio le llega un
aviso de "turno nuevo"** por:
- **Email** (a `negocio.email`) — siempre.
- **WhatsApp** (al número del negocio) — si WhatsApp está configurado y hay saldo.
- **Push** en el celular/navegador — si el dueño instaló la PWA y aceptó las
  notificaciones, y hay claves VAPID cargadas.

Para reservas con **seña**, el aviso se manda cuando se **aprueba el pago**.

### Activar el push (Web Push / VAPID)
Generá **una vez** el par de claves VAPID y cargalas en Render:
```
VAPID_PUBLIC_KEY=<clave pública>
VAPID_PRIVATE_KEY=<clave privada>
VAPID_CLAIM_EMAIL=mailto:soporte@agenpro.com.ar
```
Cómo generarlas (con el venv del proyecto):
```
python -c "from py_vapid import Vapid01; v=Vapid01(); v.generate_keys(); import base64; \
print('PUBLIC =', base64.urlsafe_b64encode(v.public_key.public_bytes(__import__('cryptography').hazmat.primitives.serialization.Encoding.X962, __import__('cryptography').hazmat.primitives.serialization.PublicFormat.UncompressedPoint)).rstrip(b'=').decode()); \
print('PRIVATE=', base64.urlsafe_b64encode(v.private_key.private_numbers().private_value.to_bytes(32,'big')).rstrip(b'=').decode())"
```
> Más simple: `pip install py-vapid` ya trae el comando `vapid --gen` / `vapid --applicationServerKey`. La **public key** es la que el front usa como
> `applicationServerKey`; ya la inyectamos sola en el panel desde
> `VAPID_PUBLIC_KEY`.

Sin claves VAPID, el push queda deshabilitado (el email y el WhatsApp al negocio
siguen funcionando). El push **requiere HTTPS** (en producción ya lo tenés).

---

## 2.b) Email (Brevo / SMTP)

**Listo en código** (Flask-Mail). Sin `MAIL_SERVER`, los emails van a una
bandeja de desarrollo. Con SMTP de Brevo, se envían de verdad.

### Variables (Render → Environment)
```
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<tu login SMTP de Brevo, p.ej. 8xxxxx@smtp-brevo.com>
MAIL_PASSWORD=<tu SMTP key de Brevo (NO la clave de tu cuenta)>
MAIL_DEFAULT_SENDER=AgenPro <no-reply@agenpro.com.ar>
```

> Dónde sacar usuario/clave: en Brevo → **SMTP & API → SMTP**. El usuario es el
> "login" que muestra ahí; la password es la **SMTP key** (la generás en esa
> misma pantalla), no la contraseña de tu cuenta.

### ⚠️ Lo más importante: remitente verificado
`MAIL_DEFAULT_SENDER` **debe** usar un email/dominio **verificado** en Brevo
(Senders & Domains). Si mandás desde `no-reply@agenpro.com.ar`, verificá el
dominio `agenpro.com.ar` en Brevo (te da unos registros DNS: SPF, DKIM y
DMARC para agregar en tu DNS). Sin esto, Brevo rechaza o los correos caen en
spam. Es la causa #1 de que "no lleguen los mails".

## 2.c) Imágenes (Cloudinary)

⚠️ **El disco de Render es efímero**: los logos, fotos de profesionales y la
galería **se pierden en cada deploy** si se guardan en disco. Por eso, en
producción usá **Cloudinary** (plan gratis alcanza para arrancar).

### Variable
```
CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>
```
La encontrás en el **Dashboard de Cloudinary** (Account Details → API
Environment variable). Con esa variable, cada imagen subida se comprime a WebP
y se sube a Cloudinary; se guarda la URL en la base. **Sin** la variable, las
imágenes se guardan en disco local (solo para desarrollo).

> Ya está integrado: no hay que tocar código, solo cargar `CLOUDINARY_URL` en
> Render. Las imágenes nuevas van a Cloudinary automáticamente.

## 3) Recordatorios automáticos

**Estado: listo.** La lógica de recordatorios (reservas del día siguiente) y de
vencimiento de suscripciones ya existe, y se dispara con un **Cron Job nativo de
Render** (incluido en tu plan Starter) que pega a un endpoint protegido.

### Endpoint
```
POST /tareas/correr?dias=1
Header:  X-Cron-Token: <CRON_TOKEN>
```
Devuelve JSON con `recordatorios_enviados` y `suscripciones_vencidas`. Si no hay
`CRON_TOKEN` configurado, el endpoint está deshabilitado (404).

### Cómo queda (Render Starter — recomendado)
El `render.yaml` ya define un servicio **`type: cron`** (`agenpro-recordatorios`)
que corre todos los días ~08:00 ARG y le pega al endpoint. Comparte el
`CRON_TOKEN` con la web automáticamente (`fromService`), así que **no tenés que
configurar nada extra**: al desplegar el Blueprint, queda andando.

- Probarlo a mano: Render → servicio `agenpro-recordatorios` → **Trigger Run**.
- Cambiar el horario: editá `schedule` en `render.yaml` (está en UTC).

> Como el cron le pega a la **web**, los envíos usan el mismo entorno (mail,
> WhatsApp, etc.) que ya configuraste. No hay que duplicar variables.

### Respaldo manual (GitHub Actions)
`.github/workflows/recordatorios.yml` quedó como **disparo manual** (Actions →
Run workflow), por si alguna vez querés correrlo a mano. Su `schedule` está
**comentado** para no duplicar envíos con el cron de Render. Si lo usaras como
único disparador, descomentá el `schedule` y cargá los secrets `SITE_URL` y
`CRON_TOKEN` en el repo.

### Alternativa sin Render cron — cron-job.org
1. Cuenta gratis en **cron-job.org**.
2. Nuevo cronjob: URL `https://www.agenpro.com.ar/tareas/correr?dias=1`,
   método **POST**, header `X-Cron-Token: <tu CRON_TOKEN>`, schedule diario.
