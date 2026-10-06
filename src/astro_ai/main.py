"""FastAPI app assembly — the application object and nothing that answers a request.

Owns: the FastAPI instance, the X-Forwarded-Host rewrite middleware, the two
exception handlers, the /static mount, and the router registration below. Every
route lives in astro_ai.routes.* as of issue #154.
"""

from __future__ import annotations

import contextlib
import logging
import time

import uvicorn
from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import Scope
from fastapi.staticfiles import StaticFiles

from astro_ai.routes.deps import STATIC_DIR, templates
from astro_ai.routes.llm_support import _fire_error_alert

# Route modules, imported as one block (#154). The app.include_router() calls
# stay further down in their original relative order — that order IS the route
# registration order, so it is deliberately not sorted or grouped here.
from astro_ai.routes import seo as _seo_routes
from astro_ai.routes import panchang as _panchang_routes
from astro_ai.routes import festivals as _festivals_routes
from astro_ai.routes import pages as _pages_routes
from astro_ai.routes import home as _home_routes
from astro_ai.routes import kundli as _kundli_routes
from astro_ai.routes import dosha as _dosha_routes
from astro_ai.routes import muhurat as _muhurat_routes
from astro_ai.routes import numerology as _numerology_routes
from astro_ai.routes import kundli_card as _kundli_card_routes
from astro_ai.routes import today as _today_routes
from astro_ai.routes import account as _account_routes
from astro_ai.routes import outlook as _outlook_routes
from astro_ai.routes import rashifal as _rashifal_routes
from astro_ai.routes import hindi as _hindi_routes
from astro_ai.routes import subscribe as _subscribe_routes
from astro_ai.routes import feedback as _feedback_routes
from astro_ai.routes import learn as _learn_routes
from astro_ai.routes import admin as _admin_routes
from astro_ai.routes import dasha as _dasha_routes
from astro_ai.routes import ask as _ask_routes
from astro_ai.routes import matching as _matching_routes
from astro_ai.routes import charts as _charts_routes
# Added after the #154 splice, so it goes last in both blocks below — it
# owns a brand-new path (/health) and cannot shadow any existing route.
from astro_ai.routes import health as _health_routes
# Re-exported, not redefined: scripts/perf_homepage.py --stages reaches into
# astro_ai.main for `templates`, `_PANCHANG_STRIP_CACHE` and
# `panchang_strip_for_city`, and degrades to "n/a (not in this tree)" —
# which reads like a pass — if they disappear. These names bind to the SAME
# objects the route modules use; there is exactly one cache dict in the process.
# They moved from routes/home.py to routes/deps.py when the rashifal pages
# became a second consumer of the same computed windows.
from astro_ai.routes.deps import _PANCHANG_STRIP_CACHE, panchang_strip_for_city  # noqa: F401


# Module-level logger. The unhandled-exception handler below is the last
# safety net in the process, so it must never itself raise NameError on `log`.
log = logging.getLogger(__name__)


def _warm_process_globals() -> None:
    """Pay the one-time per-process init here instead of on a reader's request.

    MEASURED 2026-09-04, local, first request on a fresh process vs the rest:

        GET /   1st request   1.195 s
        GET /   2nd request   0.003 s      (and 0.002-0.003 s thereafter)

    A ~400x cliff, and none of it is homepage work. `cProfile` on the first
    `panchang_strip_for_city("Mumbai, India")` splits it:

        TimezoneFinder()                       0.551 s   one-time, process-global
        Nominatim geocode over the network     0.422 s   one-time per place string
        everything else                       ~0.13  s

    Both are one-time: a SECOND, different city costs 0.048 s, and a repeat
    call 0.000 s. `geocode_place` is `@lru_cache`d and the strip cache is
    per-day-per-city, so this is purely the cost of being a new process.

    With Cloud Run at minScale=0 that new process happens on every scale from
    zero and after every deploy, and the reader who triggers it pays the whole
    cliff. Doing it in the lifespan does NOT make that first reader's wall
    clock worse — Cloud Run already holds their request through container
    startup — and it buys three things:

      1. Nominatim leaves the request path entirely. `geocode_place` passes
         `timeout=10`, so a slow or down Nominatim could hang the HOMEPAGE for
         up to ten seconds. That is the failure worth removing, more than the
         second.
      2. A scale-up from 1 to 2 instances warms the new one before it is given
         traffic, so nobody pays the cliff at all in that case.
      3. The cost becomes visible in the Cloud Run startup logs instead of
         hiding inside one unlucky request.

    REJECTED, with the measurement: `TimezoneFinderL`. It is the documented
    lightweight variant, and it is not lighter here — 0.526 s to construct
    against `TimezoneFinder`'s 0.551 s, a 1.05x difference — while returning
    `Etc/GMT+1` for Reykjavik where the full finder returns
    `Atlantic/Reykjavik`. Reykjavik is one of the polar cities #150 and #227
    are measured against. Nothing gained, correctness lost.

    Never let this raise. A cold start that fails because OpenStreetMap is
    having a bad afternoon is far worse than a slow first request; on failure
    the lazy paths still work exactly as they did before.
    """
    started = time.perf_counter()
    from astro_ai.routes.deps import _STRIP_DEFAULT_CITY, panchang_strip_for_city

    with contextlib.suppress(Exception):
        # One call covers all of it: the strip solve geocodes the city, which
        # constructs TimezoneFinder and warms the Swiss Ephemeris tables.
        panchang_strip_for_city(_STRIP_DEFAULT_CITY)

    # Compile the homepage's template chain. Jinja compiles on first
    # `get_template` and caches in the env, and it is the largest single piece
    # of what the warm-up above does NOT cover: measured 0.074s for these five
    # (index 0.041, base 0.013, nav 0.012, strip 0.005, tab bar 0.003) against
    # 0.224s still left on the first request. The rest is one-off overhead in
    # the response path itself and is not worth another mechanism.
    #
    # Deliberately only the homepage chain, not every template: the first
    # visitor lands here, and compiling all 54 top-level templates plus 76
    # articles would trade a real startup cost for a benefit nobody measured.
    with contextlib.suppress(Exception):
        for _name in ("index.html", "base.html", "_nav.html",
                      "_tab_bar.html", "_panchang_strip.html"):
            templates.env.get_template(_name)

    log.info("warm-up: process globals ready in %.3fs", time.perf_counter() - started)


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Warm before serving. Blocking on purpose — see _warm_process_globals."""
    _warm_process_globals()
    yield


app = FastAPI(title="astro-ai", version="0.0.1", lifespan=_lifespan)


class _RewriteHostFromForwardedMiddleware:
    """Rewrite the Host header from X-Forwarded-Host set by the proxy.

    Cloud Run sits behind Firebase Hosting / Google Frontend. The FE
    sets X-Forwarded-Host: shubhagya.com but leaves the raw Host header
    pointing at the internal Cloud Run URL (bhagya-<hash>.a.run.app).
    FastAPI's automatic slash-redirect (redirect_slashes=True) builds
    Location from request.url, which uses Host → wrong domain.

    uvicorn's --proxy-headers handles X-Forwarded-Proto (scheme) and
    X-Forwarded-For (client IP) but NOT X-Forwarded-Host. This tiny
    middleware fills that gap: rewrites Host + scope['server'] BEFORE
    FastAPI processes the request, so request.url yields the public URL.

    Root-cause fix for Search Console 'Redirect error' where 14 /learn
    URLs were 307-redirecting to the internal run.app hostname.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            fwd_host = None
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-host" and value:
                    # Multiple hosts possible ("a, b") — take the first.
                    fwd_host = value.split(b",")[0].strip()
                    break
            if fwd_host:
                # Immutable list of tuples — rebuild it.
                new_headers = [
                    (b"host", fwd_host) if name == b"host" else (name, value)
                    for name, value in scope["headers"]
                ]
                # Add Host if it was absent (some proxies strip it).
                if not any(n == b"host" for n, _ in scope["headers"]):
                    new_headers.append((b"host", fwd_host))
                scope = dict(scope)
                scope["headers"] = new_headers
                # scope['server'] is used by Starlette's URL() when Host
                # header is absent; keep it in sync just in case.
                try:
                    scope["server"] = (fwd_host.decode("latin-1"), 443)
                except Exception:  # noqa: BLE001
                    pass
        await self.app(scope, receive, send)


app.add_middleware(_RewriteHostFromForwardedMiddleware)
# #124 S8 — 301 ?lang=hi onto /hi/{path} where a Hindi URL exists, so the
# Hindi content has exactly one indexable URL. It only redirects, never lets a
# handler render with a mutated path, which is why a middleware is safe here
# and was not for the /hi prefix itself.
#
# ORDERING, corrected: an earlier version of this comment claimed it was added
# after the host rewrite "so it sees the real Host". That is backwards —
# `add_middleware` inserts at index 0, so the LAST added is the OUTERMOST and
# runs FIRST. Measured chain, outermost first: ServerError,
# RedirectLangParam, _RewriteHostFromForwarded. So S8 sees the UN-rewritten
# Host.
#
# That is harmless, and it was verified rather than assumed: S8 emits a
# relative Location and never reads Host, so with
# `X-Forwarded-Host: evil.example.com` the Location is still /hi/rashifal.
# But the stated reason was false, which is the defect class this file's
# neighbours keep being corrected for.
app.add_middleware(_hindi_routes.RedirectLangParamMiddleware)

# ─── Response compression ──────────────────────────────────────────────────
# The site shipped every byte uncompressed until 2026-09-04. Measured against
# production (revision bhagya-00380-t58) with a real GET carrying
# `Accept-Encoding: gzip, br`, headers dumped and the body kept raw:
#
#     homepage HTML   141,191 B served   ->  36,283 B under gzip -9   (-74%)
#     app.css          85,037 B served   ->  13,151 B under gzip -9   (-85%)
#
# No `content-encoding` on either, while `vary: accept-encoding` WAS present —
# something intended to negotiate and nothing ever did. Not an artifact of the
# measuring environment: the same curl through the same proxy gets
# `content-encoding: gzip` from google.com.
#
# The homepage is `no-store` (see _no_cdn_cache), so those ~105 KB were paid on
# EVERY homepage load by every visitor, not only the first. Firebase Hosting
# rewrites `**` to Cloud Run (firebase.json), so compression is the origin's to
# do and nothing upstream was doing it.
#
# minimum_size=500: below that the gzip header and the CPU cost outweigh the
# saving, and tiny JSON replies like /health stay plain.
#
# Deliberately NOT excluding already-compressed types. PNGs and woff2 come back
# barely smaller, so the middleware spends a little CPU for nothing on them —
# accepted, because the static payload here is small and a content-type
# exclusion list is one more thing that has to stay true. If the image surface
# ever grows, revisit with a measurement rather than on principle.
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """HTTP exception handler — catches 404s (unknown routes) + explicit
    HTTPExceptions raised by route handlers.

    404 renders a friendly HTML page pointing users to the main features
    instead of FastAPI's default JSON error. All other 4xx/5xx are
    delegated to the generic error.html template so the response stays
    branded and useful.

    CRITICAL: response headers from the raised exception MUST be preserved.
    The classic case: HTTPException(401, headers={"WWW-Authenticate": "Basic ..."})
    from require_admin. Without the header, browsers don't show the auth
    prompt — the user just sees "Not authenticated" with no way to log in.
    Bug reproduced on /admin 2026-08-06 after the initial 404 handler ship.
    """
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request, "404.html", {}, status_code=404,
        )
    # 401/403/etc. — render the generic error page with the exception detail
    response = templates.TemplateResponse(
        request, "error.html",
        {"title": f"Error {exc.status_code}",
         "message": exc.detail if exc.detail else "An error occurred processing your request."},
        status_code=exc.status_code,
    )
    # Preserve exception headers (e.g. WWW-Authenticate for 401) so the
    # browser can respond appropriately (auth prompt, redirect, etc.).
    if exc.headers:
        for k, v in exc.headers.items():
            response.headers[k] = v
    return response


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Safety net — fires a Telegram alert for any truly unhandled 500 and
    returns a branded error page instead of a bare server-error string.

    This ONLY fires when nothing else caught the exception (e.g. the pre-log-
    NameError incident on 2026-07-27). Handled LLM errors don't reach here
    because they return template responses inline.
    """
    log.exception("unhandled exception in request handler")
    _fire_error_alert(request, exc, "unhandled")
    # Best-effort branded 500 page. Fall back to bare text if the template
    # renderer itself is broken (defensive — template failures during a 500
    # would trigger an infinite loop).
    try:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Something went wrong on our side",
             "message": "The chart engine hit an unexpected error. This has been logged and we'll investigate. If it happened while generating a reading, try refreshing the page — the compute layer is deterministic and the retry usually succeeds."},
            status_code=500,
        )
    except Exception:  # noqa: BLE001
        log.exception("500 template render also failed — returning bare text")
        return Response("Internal Server Error", status_code=500)


class _CachedStaticFiles(StaticFiles):
    """StaticFiles that tells the browser how long it may keep the file.

    Cloud Run answers `cache-control: private` with no `max-age` by default, so
    every static asset was revalidated on every navigation — measured on
    production 2026-09-04:

        GET /static/css/app.css?v=1ced5c16
        cache-control: private        <- no max-age, no immutable
        etag: "d658260c529c4ae7c57fc3f766f03483"

    An ETag makes that a 304 rather than a re-download, but it is still a full
    round trip to asia-south1 per asset per navigation, and #237 gave the
    stylesheet a CONTENT HASH precisely so it would never need one.

    The rule keys on whether the request is content-addressed, because that is
    what makes a long cache safe:

      `?v=<hash>` present -> immutable for a year. The hash is
      `deps._asset_fingerprint`, a sha256 of the file's bytes, so a changed
      file is a changed URL and there is nothing to invalidate.

      no `?v=` -> five minutes. The icons, `analytics.js` and the webmanifest
      are linked at stable URLs, so they must stay re-fetchable.

    `sw.js` is NOT affected and must never be: it is served by its own route at
    `/sw.js` (routes/seo.py:119) so that its scope is `/` rather than
    `/static/`. Giving the service worker an immutable year would make #253
    permanent rather than better.
    """

    def file_response(
        self,
        full_path,
        stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        # Signature mirrored from starlette.staticfiles.StaticFiles rather than
        # taking *args: `scope` is what carries the query string, and sniffing
        # it out of a positional tuple would break silently on a Starlette that
        # reorders them. If this ever raises TypeError after an upgrade, the
        # signature moved and the header is not being set — which is a stale
        # cache, not an outage, so it must fail loudly here rather than be
        # papered over with **kwargs.
        resp = super().file_response(full_path, stat_result, scope, status_code)
        query = scope.get("query_string", b"")
        if b"v=" in query:
            resp.headers["cache-control"] = "public, max-age=31536000, immutable"
        else:
            resp.headers["cache-control"] = "public, max-age=300"
        return resp


# Serve the PWA manifest, service worker, and icons from /static/.
# StaticFiles mounts must precede route definitions for the most specific
# path to win, but FastAPI's router handles this correctly either way.
app.mount("/static", _CachedStaticFiles(directory=str(STATIC_DIR)), name="static")


# --- router registration (#154) -------------------------------------------
# Extracted route modules are spliced in AT THE POSITION THEY USED TO OCCUPY,
# so `app.routes` keeps the exact registration order it had pre-split.
#
# Registration uses `app.include_router(...)`. As of FastAPI 0.138 (the locked
# version) that no longer copies routes into `app.routes` — it appends a lazy
# `_IncludedRouter` marker and resolves the real routes at match time. So
# `app.routes` is not the flat route table any more: tooling that introspects
# it (`scripts/route_inventory.py`, the #154 check harness) must walk
# `fastapi.routing.iter_route_contexts(app.routes)` instead.
app.include_router(_seo_routes.router)
app.include_router(_panchang_routes.router)
app.include_router(_festivals_routes.router)
app.include_router(_pages_routes.router)
app.include_router(_home_routes.router)
app.include_router(_kundli_routes.router)
app.include_router(_dosha_routes.router)
app.include_router(_muhurat_routes.router)
app.include_router(_numerology_routes.router)
app.include_router(_kundli_card_routes.router)
app.include_router(_today_routes.router)
app.include_router(_account_routes.router)
app.include_router(_outlook_routes.router)
app.include_router(_rashifal_routes.router)
# /hi/{path} — after rashifal, whose handlers it awaits (#124)
app.include_router(_hindi_routes.router)
app.include_router(_subscribe_routes.router)
app.include_router(_feedback_routes.router)
app.include_router(_learn_routes.router)
app.include_router(_admin_routes.router)
app.include_router(_dasha_routes.router)
app.include_router(_ask_routes.router)
app.include_router(_matching_routes.router)
app.include_router(_charts_routes.router)
app.include_router(_health_routes.router)


def cli() -> None:
    """Entry point for the `astro-ai` console script: starts uvicorn on localhost:8000."""
    uvicorn.run("astro_ai.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    cli()
