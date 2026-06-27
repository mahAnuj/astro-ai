/* Bhagya service worker.
 *
 * Strategy:
 *   - Cache-first for static assets (manifest, icons, fonts that hit /static/).
 *     These never change between deploys without a version bump.
 *   - Network-first for everything else, with a cached fallback so the app
 *     still loads (showing stale content) when offline.
 *
 * Critical: never cache /admin/usage (auth-gated) or POST requests (forms).
 * Cache versioning: bump CACHE_VERSION on any change to this file so old
 * clients drop their stale cache on the next service-worker install.
 */

const CACHE_VERSION = 'bhagya-v2';  // bump after every static-asset change
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;

// Assets we want available offline as soon as the SW installs.
const PRECACHE_URLS = [
  '/',
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Routes we should never cache (auth-gated or user-specific writes).
const NEVER_CACHE_PREFIXES = ['/admin/', '/lang', '/switch', '/delete-chart', '/reset', '/reading'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())  // activate the new SW immediately
  );
});

self.addEventListener('activate', (event) => {
  // Drop caches from older versions so stale assets don't linger.
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => !k.startsWith(CACHE_VERSION)).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only GET requests are cacheable; let everything else pass straight through.
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Same-origin only — don't try to cache cross-origin CDN scripts (Tailwind, htmx).
  if (url.origin !== self.location.origin) return;

  // Never cache admin or mutating routes.
  if (NEVER_CACHE_PREFIXES.some((p) => url.pathname.startsWith(p))) return;

  // Static assets: cache-first.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // HTML pages: network-first, fall back to cache when offline. This way
  // users always see fresh content when online but get the last-good copy
  // when the network drops mid-train/lift/etc.
  event.respondWith(
    fetch(req).then((res) => {
      // Only cache successful HTML responses (200 OK, content-type text/html).
      if (res.ok && res.headers.get('content-type')?.includes('text/html')) {
        const copy = res.clone();
        caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match('/')))
  );
});
