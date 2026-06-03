# Conectar el dominio www.agenpro.com.ar

Guía paso a paso para apuntar tu dominio comprado a la app en **Render**.
Hay que tocar dos lugares: **Render** (declarar el dominio) y tu **registrador
de DNS** (apuntarlo). El dominio `.com.ar` normalmente se gestiona en
[NIC Argentina](https://nic.ar) o en el panel DNS de quien te lo vendió.

> El blueprint (`render.yaml`) ya declara los dominios y `SITE_URL`. Si ya
> desplegaste con Blueprint, igual conviene verificar en el panel de Render.

---

## 1) Declarar el dominio en Render

1. Entrá a tu servicio web **reservas-web** en el dashboard de Render.
2. Andá a **Settings → Custom Domains**.
3. Agregá **dos** dominios:
   - `www.agenpro.com.ar`  ← el principal
   - `agenpro.com.ar`      ← el "apex" (Render lo redirige al www)
4. Render te va a mostrar, para cada uno, **qué registro DNS crear**. Anotalos.
   Típicamente:
   - Para `www`  → un registro **CNAME** que apunta a algo como
     `reservas-web.onrender.com`
   - Para el apex `agenpro.com.ar` → un registro **A** a la IP que te indique
     Render, o un **ALIAS/ANAME** si tu DNS lo soporta.

---

## 2) Cargar los DNS en tu registrador (NIC.ar u otro)

En el panel de DNS del dominio, creá los registros que te dio Render:

| Tipo  | Nombre / Host        | Valor (lo da Render)              | TTL  |
|-------|----------------------|-----------------------------------|------|
| CNAME | `www`                | `reservas-web.onrender.com`       | 3600 |
| A     | `@` (o `agenpro.com.ar`) | la IP que indica Render       | 3600 |

Notas:
- Si tu DNS **no** permite CNAME en `www` junto con otros registros, usá el que
  Render proponga (a veces ofrece ALIAS/ANAME para el apex).
- En **NIC.ar** quizá tengas que usar sus *delegaciones* a un proveedor de DNS
  (Cloudflare, por ejemplo). Si usás Cloudflare: poné los registros ahí y dejá
  el proxy **en gris (DNS only)** la primera vez, hasta que Render emita el SSL.

---

## 3) Esperar verificación + SSL

- Volvé a Render → Custom Domains. Cuando el DNS propague, cada dominio pasa a
  **Verified** y Render emite el certificado **HTTPS (Let's Encrypt)** solo.
- La propagación puede tardar de minutos a 24–48 hs (según el TTL previo).

---

## 4) Variable de entorno SITE_URL

Ya está en `render.yaml`:

```yaml
- key: SITE_URL
  value: https://www.agenpro.com.ar
```

Sirve para que los **links de los emails**, las **back_urls de pago** y los
**webhooks** usen tu dominio y no la URL `.onrender.com`. Si la cargaste a mano,
verificá que esté en **Settings → Environment** del servicio web y redeployá.

---

## 5) Checklist final

- [ ] `www.agenpro.com.ar` abre la app con candado HTTPS 🔒
- [ ] `agenpro.com.ar` redirige a `www`
- [ ] La PWA se instala desde el celular con el ícono de AgenPro
- [ ] `SITE_URL = https://www.agenpro.com.ar` en el entorno de Render
- [ ] (Si usás pagos reales) actualizar las **URLs de retorno/webhook** en
      Mercado Pago / Naranja X / Modo con el dominio nuevo

---

### Problemas comunes

- **"Certificate pending" mucho tiempo:** casi siempre es el DNS mal cargado o
  el proxy de Cloudflare en naranja. Revisá con `nslookup www.agenpro.com.ar`.
- **Apex no funciona:** algunos DNS no soportan A/ALIAS en el apex; en ese caso
  dejá solo `www` y configurá una redirección de `agenpro.com.ar` → `www`.
- **Mezcla http/https:** con `SITE_URL` en https y el SSL de Render activo no
  debería pasar; si ves contenido mixto, forzá https en los enlaces absolutos.
