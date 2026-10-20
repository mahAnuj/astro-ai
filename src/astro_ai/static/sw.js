/* Bhagya service worker.
 *
 * Strategy:
 *   - /static/ URLs carrying a `?v=` fingerprint (app.css): cache-first. The
 *     fingerprint is a content hash, so changed bytes are a changed URL.
 *   - Every other /static/ asset (manifest, icons, analytics.js): stale-while-
 *     revalidate. Served from cache at once, then re-fetched from the origin
 *     with a conditional request and the cache entry replaced, so a changed
 *     file reaches a returning visitor on the visit after next and a
 *     CACHE_VERSION bump is no longer the only eviction path (#253).
 *     Only 2xx responses are ever stored; a transient 404/500 is not kept.
 *   - Network-first for everything else, with a cached fallback so the app
 *     still loads (showing stale content) when offline.
 *
 * Critical: never cache /admin/usage (auth-gated) or POST requests (forms).
 * Cache versioning: bump CACHE_VERSION on any change to this file so old
 * clients drop their stale cache on the next service-worker install.
 */

const CACHE_VERSION = 'bhagya-v4';  // bump on any change to this file
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

// Store a response only if it is a real success. A transient 404/500 (or an
// opaque response, status 0) cached here would be served until the next bump.
function storeIfOk(req, res) {
  if (!res || !res.ok || res.type === 'opaque') return Promise.resolve();
  const copy = res.clone();  // clone synchronously, before the body is consumed
  return caches.open(STATIC_CACHE)
    .then((c) => c.put(req, copy))
    .catch(() => {});  // e.g. 206 partial content is not storable; not fatal
}

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only GET requests are cacheable; let everything else pass straight through.
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Same-origin only — don't try to cache cross-origin CDN scripts (Tailwind, htmx).
  if (url.origin !== self.location.origin) return;

  // Never cache admin or mutating routes.
  if (NEVER_CACHE_PREFIXES.some((p) => url.pathname.startsWith(p))) return;

  // Static assets. Fingerprinted (?v=) URLs are immutable: cache-first.
  // Everything else is stale-while-revalidate (#253).
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((hit) => {
        if (hit && url.searchParams.has('v')) return hit;

        // Revalidation must reach the origin, not the browser's 5-minute HTTP
        // cache (non-fingerprinted assets are served `public, max-age=300`).
        const network = fetch(req, hit ? { cache: 'no-cache' } : undefined).then((res) => {
          event.waitUntil(storeIfOk(req, res));
          return res;
        });

        if (hit) {
          // Answer from cache now; refresh in the background. A failed refresh
          // (offline) is not an error for the visitor, who already has `hit`.
          event.waitUntil(network.catch(() => {}));
          return hit;
        }
        return network;  // no cached copy: wait on the network, let failure surface
      })
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
