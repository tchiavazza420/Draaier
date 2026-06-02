/* Service Worker — Draaier PWA
   Estrategia:
   - Precache del "app shell" mínimo (offline básico).
   - Network-first para navegación (HTML siempre fresco; cae a caché si no hay red).
   - Cache-first para estáticos (rápido).
   No cachea peticiones POST ni rutas de panel/pagos (datos sensibles/dinámicos).
*/
const CACHE = "draaier-v3";
const APP_SHELL = [
  "/",
  "/static/css/app.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Solo GET; nunca interferir con POST (reservas, pagos, login, etc.).
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // No cachear panel ni pagos (siempre datos vivos).
  if (url.pathname.startsWith("/panel") || url.pathname.startsWith("/pagos")) {
    return;
  }

  // Estáticos: cache-first.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // Navegación / HTML: network-first con fallback a caché.
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("/")))
  );
});
