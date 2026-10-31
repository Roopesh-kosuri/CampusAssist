// CampusAssist Progressive Web App (PWA) Service Worker
const CACHE_NAME = "campusassist-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/index.html",
  "/static/manifest.json",
  "/static/favicon.ico",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png"
];

// Install: pre-cache static application shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn("ServiceWorker pre-cache partial failure:", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean up older cache versions
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for static assets
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // API endpoints: Network-first
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => response)
        .catch(() => {
          return new Response(
            JSON.stringify({
              error: true,
              detail: "You are currently offline. Connect to LPU Wi-Fi to query CampusAssist."
            }),
            {
              headers: { "Content-Type": "application/json" },
              status: 503
            }
          );
        })
    );
    return;
  }

  // Static shell: Cache-first, falling back to network
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && event.request.method === "GET") {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return networkResponse;
        })
        .catch(() => {
          if (event.request.headers.get("accept")?.includes("text/html")) {
            return caches.match("/");
          }
        });
    })
  );
});
