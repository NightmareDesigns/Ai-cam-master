/**
 * AI-Cam Service Worker — NightmareDesigns
 *
 * Caches UI shell assets so the app loads instantly and renders even when
 * the device cannot reach the backend.  API calls (cameras, events, streams)
 * still require the server to be reachable.
 *
 * Strategy
 * --------
 * Static assets  → Cache-first (fast; re-fetched in background on change)
 * Navigation     → Network-first with offline fallback
 * API (/api/*)   → Network-only (live data)
 * Streams        → Network-only (MJPEG / WebSocket)
 */

const CACHE_VERSION = "aicam-v1";

const SHELL_ASSETS = [
  "/",
  "/cameras",
  "/events",
  "/settings",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/dashboard.js",
  "/static/js/cameras.js",
  "/static/js/events.js",
  "/static/js/settings.js",
  "/static/icons/icon.svg",
  "/static/img/offline.svg",
];

// ── Install: pre-cache the app shell ─────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ───────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE_VERSION)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch: routing logic ──────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Pass through non-GET requests and cross-origin requests unchanged.
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // Network-only: live streams and WebSocket upgrades.
  if (
    url.pathname.startsWith("/stream/") ||
    url.pathname.startsWith("/ws/") ||
    url.pathname.startsWith("/snapshot/")
  ) {
    return;
  }

  // Network-only: REST API calls (always need fresh data).
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Cache-first: static assets (CSS, JS, images, icons).
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
            }
            return response;
          })
      )
    );
    return;
  }

  // Network-first: HTML pages — fall back to cache when offline.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
