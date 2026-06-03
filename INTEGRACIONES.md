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

**Estado: listo, falta engancharle un disparador.** La lógica de recordatorios
(reservas del día siguiente) y de vencimiento de suscripciones ya existe. En el
plan **free de Render no hay Celery beat ni cron**, así que la disparamos con un
**cron externo gratis** que pega a un endpoint protegido.

### Endpoint
```
POST /tareas/correr?dias=1
Header:  X-Cron-Token: <CRON_TOKEN>
```
Devuelve JSON con `recordatorios_enviados` y `suscripciones_vencidas`. Si no hay
`CRON_TOKEN` configurado, el endpoint está deshabilitado (404).

### Variable
```
CRON_TOKEN=<un secreto largo y aleatorio>
```
(El `render.yaml` ya lo genera automáticamente si desplegás por Blueprint.)

### Opción A — GitHub Actions (incluida, gratis)
Ya hay un workflow en `.github/workflows/recordatorios.yml` que corre todos los
días ~08:00 (hora Argentina). Solo cargá **dos secrets** en el repo
(**Settings → Secrets and variables → Actions → New repository secret**):

| Secret      | Valor                                   |
|-------------|-----------------------------------------|
| `SITE_URL`  | `https://www.agenpro.com.ar`            |
| `CRON_TOKEN`| el **mismo** valor que pusiste en Render |

Podés probarlo a mano desde la pestaña **Actions → Recordatorios diarios → Run
workflow**.

### Opción B — cron-job.org (sin tocar GitHub)
1. Creá una cuenta gratis en **cron-job.org**.
2. Nuevo cronjob: URL `https://www.agenpro.com.ar/tareas/correr?dias=1`,
   método **POST**, header `X-Cron-Token: <tu CRON_TOKEN>`, schedule diario.

> Tip: en Render free el servicio “se duerme” por inactividad. El propio
> llamado del cron lo despierta; la primera request puede tardar unos segundos.
