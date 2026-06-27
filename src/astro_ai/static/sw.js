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

const CACHE_VERSION = 'bhagya-v3';  // bump after every static-asset change
const STATIC_CACHE = `${CACHE_VERSION}-static`;

// Assets we want available offline as soon as the SW installs.
// Critical: do NOT precache `/` — the homepage renders the user's saved
// charts from their cookie. A cached homepage shows whatever charts existed
// when the SW first installed (often empty), and the network-first override
// can race with form submissions. Static-only precache keeps the install
// banner working without risking the user-personalised pages.
const PRECACHE_URLS = [
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

  // HTML pages: NEVER cache. Every Bhagya page is cookie-personalized
  // (saved charts on home, active chart on /today, language preference
  // everywhere). Caching means one user/session sees another's state, or
  // a fresh-cookie navigation sees the pre-cookie cached version. Just
  // pass-through to network so the server-rendered, cookie-aware response
  // always reaches the user. Offline-mode HTML is sacrificed but readings
  // need network anyway (LLM calls).
  event.respondWith(fetch(req));
});
