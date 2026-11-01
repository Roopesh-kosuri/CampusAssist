// CampusAssist Progressive Web App (PWA) Service Worker - v2
const CACHE_NAME = "campusassist-v2";
const ASSETS_TO_CACHE = [
  "/",
  "/manifest.json",
  "/favicon.ico",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png"
];

// Install: pre-cache static application shell and activate immediately
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn("ServiceWorker pre-cache partial warning:", err);
      });
    })
  );
});

// Activate: delete old cache versions (including v1) immediately and claim clients
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("Removing legacy cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Network-first for HTML pages and API queries, Cache-fallback if offline
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. API endpoints: Network-first
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => response)
        .catch(() => {
          return new Response(
            JSON.stringify({
              error: true,
              detail: "You are currently offline. Connect to internet to query CampusAssist."
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

  // 2. HTML Navigation & document requests: NETWORK-FIRST so new UI updates show instantly!
  if (event.request.mode === "navigate" || event.request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return networkResponse;
        })
        .catch(() => caches.match("/") || caches.match(event.request))
    );
    return;
  }

  // 3. Static assets (images, icons, manifest): Stale-while-revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && event.request.method === "GET") {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
