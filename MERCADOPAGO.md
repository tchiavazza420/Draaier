# Conectar Mercado Pago (paso a paso)

AgenPro cobra las **señas** a la cuenta de Mercado Pago **de cada negocio**, usando
la **conexión OAuth ("Conectar cuentas")**: el negocio toca un botón, autoriza en
Mercado Pago y listo (no se pega ningún token).

Para que ese botón funcione, **vos (la plataforma)** tenés que tener **una
aplicación de Mercado Pago** bien configurada, y cargar sus credenciales en Render.

Si te aparece **"La aplicación no está preparada"** o **no te deja conectarte**,
es casi siempre la **Redirect URI** o que falta algo de la app. Seguí esto:

---

## Parte 1 — Crear / abrir la aplicación en Mercado Pago

1. Entrá a **https://www.mercadopago.com.ar/developers/panel** (con TU cuenta de
   Mercado Pago, la de la plataforma, no la de un negocio).
2. **Tus integraciones** → **Crear aplicación** (o abrí la que ya tenés).
3. Datos de la app:
   - **Nombre:** AgenPro (o el que quieras).
   - **¿Qué producto vas a integrar?** → elegí **Pagos online → Checkout Pro**.
   - **¿Usás una plataforma de e-commerce?** → **No**.
   - **Modelo de integración:** si te pregunta, elegí el que **incluye OAuth /
     "Conectar cuentas de terceros"** (Marketplace). Es lo que permite cobrar a
     la cuenta de otro.
4. **Crear**.

---

## Parte 2 — Configurar la Redirect URI (lo más importante)

1. Dentro de la app → sección **"Tus credenciales" / "Editar"** → buscá
   **"Redirect URIs"** (URLs de redireccionamiento) — suele estar en la parte de
   **OAuth / Conexión de cuentas**.
2. Agregá **exactamente** esta URL (copiá y pegá, sin barra al final):
   ```
   https://www.agenpro.com.ar/pagos/mp/callback
   ```
   ⚠️ Tiene que ser **idéntica**: con `https://`, con `www`, sin `/` final.
   Si la ponés sin `www`, o con barra final, o apuntás a otro dominio → da
   **"la aplicación no está preparada"**.
3. **Guardar**.

---

## Parte 3 — Copiar las credenciales

En la misma app, sección **"Credenciales de producción"**:

- **Client ID** (a veces figura como **App ID**, es un número largo) → lo vas a
  cargar como `MP_CLIENT_ID`.
- **Client Secret** → lo vas a cargar como `MP_CLIENT_SECRET`.

> ⚠️ Usá las de **PRODUCCIÓN**, no las de prueba. Y asegurate de que sean de la
> **misma app** donde cargaste la Redirect URI (si tenés varias apps, es fácil
> mezclarlas).

Si te pide **activar las credenciales de producción** (completar rubro, sitio,
etc.), hacelo: una app sin producción activada también tira "no está preparada".

---

## Parte 4 — Cargar en Render

Render → tu servicio **web** → **Environment** → agregá (o revisá) estas
variables, con los nombres **exactos**:

```
MP_CLIENT_ID=<el Client ID / App ID de producción>
MP_CLIENT_SECRET=<el Client Secret de producción>
```

(Opcional: `MP_MARKETPLACE_FEE=0` → comisión % que retiene la plataforma; 0 = nada.)

**Guardá** → Render redeploya solo. **Esperá a que termine el deploy** antes de
probar.

---

## Parte 5 — Probar la conexión

1. En AgenPro: **Señas** → **"Conectar con Mercado Pago"**.
2. Te lleva a Mercado Pago → **Autorizar / Permitir**.
3. Volvés a AgenPro con el cartel **"¡Mercado Pago conectado!"**.

A partir de ahí, las señas que paguen tus clientes caen **a tu cuenta de Mercado
Pago**.

---

## Si NO funciona — diagnóstico rápido

| Síntoma | Causa más probable | Qué hacer |
|---|---|---|
| El botón "Conectar" no hace nada / dice "no disponible" | Faltan `MP_CLIENT_ID` / `MP_CLIENT_SECRET` en Render (o el deploy no terminó) | Revisá los nombres exactos y esperá el redeploy |
| "La aplicación no está preparada" | La **Redirect URI** no coincide, o falta | Poné exacto `https://www.agenpro.com.ar/pagos/mp/callback` |
| Vuelve con error tras autorizar | Credenciales de **prueba** en vez de producción, o de otra app | Usá las de **producción** de la **misma app** |
| "invalid_client" | `MP_CLIENT_ID`/`SECRET` mal copiados | Copialos de nuevo de "Credenciales de producción" |

> Nota: **no necesitás instalar ningún SDK** (ni PHP ni Python). La integración
> ya está hecha en el código; solo configurás la app de MP y las 2 variables.
