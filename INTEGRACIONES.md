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

---

## 2) Pagos (señas)

### MercadoPago — listo y recomendado
Ya lo configuraste. **Checkout Pro de MercadoPago acepta tarjetas (incluida
Naranja), dinero en cuenta y MODO**, así que para la mayoría de los salones
**MercadoPago solo ya cubre esos medios de pago**. No necesitás integrar Naranja
ni MODO por separado salvo que tengas un acuerdo de comercio directo con ellos.

```
MERCADOPAGO_ACCESS_TOKEN=<access token de producción>
MERCADOPAGO_PUBLIC_KEY=<public key>
```

### Naranja X y MODO como pasarelas separadas — scaffold
Los adaptadores (`app/pagos/naranja_x.py`, `app/pagos/modo.py`) están armados
con la **misma interfaz** que MercadoPago, pero los **endpoints y payloads son
placeholders**: Naranja X y MODO **no** tienen una API pública de checkout tan
simple como MercadoPago; requieren **onboarding de comercio** y te entregan sus
specs/credenciales propias.

Para activarlas de verdad necesito de tu lado:
- Que tengas **cuenta de comercio con API** en Naranja X y/o MODO.
- Su **documentación oficial** (endpoints de crear intención de pago, consultar
  estado y formato del webhook) + las credenciales.

Con eso ajusto `API_BASE`, los payloads y la verificación del webhook en cada
adaptador. Mientras tanto, si seteás el token igual, el sistema intenta la
llamada real; sin token, cae a **simulación** (checkout interno para probar).

```
NARANJA_X_ACCESS_TOKEN=<solo si tenés API de comercio>
MODO_ACCESS_TOKEN=<solo si tenés API de comercio>
```

**Recomendación:** dejá MercadoPago como pasarela principal (cubre Naranja y
MODO) y sumamos las otras dos solo si conseguís acceso directo a sus APIs.

---

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
