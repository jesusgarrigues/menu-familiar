/* Service worker: la app abre al instante y se puede consultar sin conexión. */
const VERSION = "v6";
const SHELL = `shell-${VERSION}`;
const DATA = `data-${VERSION}`;
const ASSETS = [
  "/",
  "/static/styles.css?v=6",
  "/static/app.js?v=6",
  "/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon.svg",
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(SHELL).then(c => c.addAll(ASSETS)).catch(() => {}).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => ![SHELL, DATA].includes(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/login") || url.pathname.startsWith("/logout") || url.pathname.endsWith("/pdf")) return;

  // Datos: primero la red; si no hay conexión, lo último guardado
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(req).then(res => {
        // Respuesta de redirección (sesión de Cloudflare Access caducada): se pasa tal cual para que la página recargue
        if (res.ok && res.type === "basic") { const copy = res.clone(); caches.open(DATA).then(c => c.put(req, copy)); }
        return res;
      }).catch(() => caches.match(req).then(r => r || new Response(JSON.stringify({ error: "Sin conexión" }), {
        status: 503, headers: { "Content-Type": "application/json" } })))
    );
    return;
  }

  // Página: primero la red (para coger versiones nuevas), con copia de respaldo
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then(res => {
        if (res.ok && !res.redirected) { const copy = res.clone(); caches.open(SHELL).then(c => c.put("/", copy)); }
        return res;
      }).catch(() => caches.match("/"))
    );
    return;
  }

  // Estáticos: caché y actualización en segundo plano
  event.respondWith(
    caches.match(req).then(cached => {
      const net = fetch(req).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(SHELL).then(c => c.put(req, copy)); }
        return res;
      }).catch(() => cached);
      return cached || net;
    })
  );
});
