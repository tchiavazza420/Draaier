# Configurar WhatsApp en AgenPro (paso a paso)

AgenPro envía confirmaciones y recordatorios por **WhatsApp Cloud API** (la API
oficial de Meta, gratis para empezar). Sin credenciales, los mensajes van a una
bandeja de desarrollo (no se envían). Con credenciales, se envían de verdad.

> Resultado final: cargar **3 variables** en Render
> (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_API_VERSION`).

---

## Antes de empezar (requisitos)

- Una cuenta de **Facebook** (te va a hacer de admin).
- Un **número de celular** para el WhatsApp del negocio que **NO** esté usado
  hoy en la app de WhatsApp/WhatsApp Business. Si querés usar tu número actual,
  primero hay que **borrar esa cuenta de WhatsApp** en el teléfono (el número
  pasa a la API). Para probar, Meta te da un **número de prueba gratis**, así
  que podés arrancar sin tocar tu número.
- 10–15 minutos.

---

## Parte 1 — Crear la app en Meta

1. Entrá a **https://developers.facebook.com/** e iniciá sesión con tu Facebook.
2. Aceptá los términos de desarrollador si te los pide (botón **Comenzar**).
3. Arriba a la derecha: **Mis aplicaciones → Crear aplicación**.
4. En "¿Qué quieres que haga tu aplicación?" elegí **Otro** → **Siguiente**.
5. Tipo de aplicación: **Empresa (Business)** → **Siguiente**.
6. Nombre de la app: `AgenPro` (o el que quieras), tu email, y la cuenta
   comercial (si no tenés, deja la que ofrece) → **Crear aplicación**.
   Te puede pedir tu contraseña de Facebook.

## Parte 2 — Agregar WhatsApp

1. En el panel de la app, buscá la tarjeta **WhatsApp** → **Configurar**.
2. Te pide una **cuenta de WhatsApp Business**: dejá la que crea por defecto o
   creá una nueva → **Continuar**.
3. Ya estás en **WhatsApp → Configuración de la API** (o "API Setup"). Esta
   pantalla tiene TODO lo que necesitás. Quedate acá.

## Parte 3 — Sacar los 2 datos clave

En esa pantalla "Configuración de la API" vas a ver:

### a) Identificador del número de teléfono (`WHATSAPP_PHONE_ID`)
- Hay un desplegable **"Desde"** con un número de prueba ya creado.
- Debajo dice **"Identificador del número de teléfono"** (Phone number ID) —
  es un número largo, ej: `123456789012345`. **Ese es tu `WHATSAPP_PHONE_ID`.**
  ⚠️ NO es el número de teléfono en sí; es el ID que está al lado.

### b) Token de acceso (`WHATSAPP_TOKEN`)
- En la misma pantalla hay un **"Token de acceso temporal"** (un texto largo
  que empieza con `EAA...`). **Ese es tu `WHATSAPP_TOKEN`** para probar.
- ⚠️ **Dura solo 24 horas.** Sirve para probar ya; para producción necesitás un
  token permanente (ver Parte 6).

### Probar en el momento
En esa misma pantalla, en "Para:" agregá tu propio número de WhatsApp (con
código de país, ej. `+54 9 351 ...`), te llega un código por WhatsApp para
verificarlo, y mandá el mensaje de prueba con el botón **Enviar mensaje**. Si te
llega, la API funciona. 🎉

---

## Parte 4 — Cargar las variables en Render

En tu servicio web de Render → **Environment** → agregá:

```
WHATSAPP_TOKEN=EAA...           (el token de la Parte 3b)
WHATSAPP_PHONE_ID=123456789012345   (el Phone number ID de la Parte 3a)
WHATSAPP_API_VERSION=v21.0      (opcional; ya viene por default)
```

Guardá y dejá que Render redeploye. Listo: AgenPro ya envía por WhatsApp.

> Para mandarte a vos mismo desde AgenPro mientras estás con el **número de
> prueba** de Meta, tu número tiene que estar en la lista de **destinatarios
> permitidos** (la misma de la Parte 3). Con el número de producción ya verificado
> podés escribirle a cualquiera (con las reglas de plantillas, ver abajo).

---

## Parte 5 — ⚠️ Importante: la ventana de 24 h y las plantillas

Meta tiene una regla clave:

- **Dentro de 24 h** de que el cliente te escribió, podés mandarle **mensajes de
  texto libres** (así funciona hoy AgenPro: confirmaciones cuando el cliente
  acaba de reservar/escribir).
- **Fuera de esas 24 h** (ej: un **recordatorio** el día anterior, sin que el
  cliente haya escrito), Meta **solo** deja enviar **plantillas aprobadas**
  (Message Templates). Un texto libre fuera de ventana **se rechaza**.

### Qué significa para vos
- **Confirmaciones al reservar:** funcionan ya (el cliente acaba de interactuar).
- **Recordatorios proactivos del día anterior:** necesitan una **plantilla
  aprobada**. Hoy AgenPro manda texto plano, así que esos recordatorios pueden
  rechazarse fuera de ventana.

> Si querés recordatorios proactivos por WhatsApp al 100%, **avisame y agrego el
> envío por plantilla** en el código (es un cambio chico). Vos creás y aprobás
> la plantilla en Meta y yo la conecto.

### Cómo crear una plantilla (para cuando lo hagamos)
1. **WhatsApp → Administrar plantillas** (Message Templates) → **Crear plantilla**.
2. Categoría **Utilidad** (utility), idioma **Español**.
3. Cuerpo, ej:
   `Hola {{1}}, te recordamos tu turno de {{2}} el {{3}}. ¡Te esperamos!`
   (los `{{1}}`, `{{2}}`, `{{3}}` son variables que completa el sistema).
4. Enviar a revisión. Meta la aprueba normalmente en minutos/horas.

---

## Parte 6 — Token permanente (para producción)

El token temporal vence en 24 h. Para que no se corte, generá un **token de
usuario del sistema** (no expira):

1. **https://business.facebook.com/** → **Configuración del negocio**
   (Business Settings).
2. **Usuarios → Usuarios del sistema** → **Agregar** → nombre `agenpro-bot`,
   rol **Administrador** → crear.
3. Con ese usuario seleccionado: **Agregar activos** → **Aplicaciones** →
   elegí tu app `AgenPro` → permiso **Control total** → guardar.
4. (Si aplica) Agregá también el activo **Cuenta de WhatsApp** con control total.
5. Botón **Generar token nuevo** → elegí la app `AgenPro` → marcá los permisos
   **`whatsapp_business_messaging`** y **`whatsapp_business_management`** →
   **Generar token**.
6. Copiá ese token (empieza con `EAA...`) y **reemplazá `WHATSAPP_TOKEN`** en
   Render por este. Este **no vence**.

> Guardá el token en un lugar seguro; Meta lo muestra una sola vez.

---

## Parte 7 — Pasar a producción con tu número real (opcional)

Mientras usás el número de prueba alcanza para probar. Para usar **tu número**:

1. En **WhatsApp → Configuración de la API**, botón **Agregar número de
   teléfono**. Cargá tu número (debe estar **libre** de WhatsApp).
2. Verificalo por SMS o llamada.
3. Completá el **perfil del negocio** y verificá tu **empresa** (Business
   Verification) en Business Settings — Meta lo pide para enviar a volumen.
4. Cuando esté verificado, ese número queda como `WHATSAPP_PHONE_ID` de
   producción (actualizá la variable en Render con el nuevo ID).

---

## Cómo saber si está andando

- **Sin credenciales:** los mensajes quedan en la bandeja de desarrollo (no se
  envían). Es el modo por defecto.
- **Con credenciales:** AgenPro pega a `graph.facebook.com/v21.0/<PHONE_ID>/
  messages`. Si algo falla, lo vas a ver en los **logs de Render**.
- **Saldo:** recordá que cada plan de AgenPro incluye X mensajes/mes y podés
  comprar packs. Eso se descuenta **solo** cuando WhatsApp está configurado de
  verdad (con credenciales).

## Problemas comunes

| Síntoma | Causa / solución |
|---|---|
| No llega nada y no hay error | Faltan `WHATSAPP_TOKEN` o `WHATSAPP_PHONE_ID` → está en modo bandeja. |
| Error 401 / token | El token venció (el temporal dura 24 h) → usá el **token permanente** (Parte 6). |
| Error “recipient not in allowed list” | Con número de prueba, el destino tiene que estar en la lista de permitidos (Parte 3). |
| El recordatorio del día anterior no llega | Fuera de la ventana de 24 h → necesitás **plantilla aprobada** (Parte 5). |
| Usé el número de teléfono en vez del ID | `WHATSAPP_PHONE_ID` es el **Identificador** largo, no el número. |

---

### Resumen ultra-corto
1. developers.facebook.com → crear app **Business** → agregar **WhatsApp**.
2. Copiar **Phone number ID** y **token** de la pantalla "Configuración de la API".
3. Cargar `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_ID` en Render.
4. Para que no venza: generar **token permanente** (usuario del sistema).
5. Para recordatorios proactivos: crear **plantilla** (Parte 5, abajo).

---

## Parte 5 — Recordatorios con plantilla aprobada (paso a paso)

Meta solo permite mensajes **proactivos** (recordatorios fuera de la ventana de
24 h) usando una **plantilla aprobada**. El código ya está listo y espera una
plantilla con **3 variables en este orden: nombre, servicio, fecha/hora**.

### A) Crear y aprobar la plantilla en Meta
1. **business.facebook.com** → **WhatsApp Manager** → **Plantillas de mensajes**
   → **Crear plantilla**.
2. **Categoría:** **Utilidad** (no Marketing).
3. **Nombre:** minúsculas con guiones bajos, ej. `recordatorio_turno`
   (anotalo: va tal cual en Render).
4. **Idioma:** Español (Argentina). Anotá el código exacto (`es_AR`, a veces `es`).
5. **Cuerpo:** pegá este texto (3 variables):
   ```
   Hola {{1}}, te recordamos tu turno de {{2}} el {{3}}. ¡Te esperamos!
   ```
   - `{{1}}` = nombre del cliente
   - `{{2}}` = servicio
   - `{{3}}` = fecha y hora (ej: "12/06 a las 15:30")
6. **Ejemplos:** completá valores de muestra (Sofía / Corte de pelo / 12/06 15:30).
7. **Enviar** → queda *En revisión*. Aprobación: de minutos a 24 h.

### B) Cargar en Render
Cuando esté **Aprobada**, en **Render → Environment**:
```
WHATSAPP_TEMPLATE_RECORDATORIO=recordatorio_turno
WHATSAPP_TEMPLATE_IDIOMA=es_AR
```
(El nombre y el idioma deben coincidir EXACTO con la plantilla.)

### C) Cómo queda
- Los recordatorios diarios salen como **plantilla** (sirven aunque el cliente
  no haya escrito en 24 h). Sin estas variables, se manda texto plano.
- Probarlo: Render → cron `agenpro-recordatorios` → **Trigger Run** con un turno
  de mañana cargado.

> ⚠️ Si hacés la plantilla con otra cantidad/orden de variables, no va a
> coincidir con lo que envía el sistema. Si querés otro texto, avisá y ajusto el
> código para que matchee.
