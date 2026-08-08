"""FastAPI app assembly — the application object and nothing that answers a request.

Owns: the FastAPI instance, the X-Forwarded-Host rewrite middleware, the two
exception handlers, the /static mount, and the router registration below. Every
route lives in astro_ai.routes.* as of issue #154.
"""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
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
from astro_ai.routes import subscribe as _subscribe_routes
from astro_ai.routes import feedback as _feedback_routes
from astro_ai.routes import learn as _learn_routes
from astro_ai.routes import admin as _admin_routes
from astro_ai.routes import dasha as _dasha_routes
from astro_ai.routes import ask as _ask_routes
from astro_ai.routes import matching as _matching_routes
from astro_ai.routes import charts as _charts_routes
# Re-exported, not redefined: scripts/perf_homepage.py --stages reaches into
# astro_ai.main for `templates`, `_HOMEPAGE_PANCHANG_CACHE` and
# `_homepage_panchang_cached`, and degrades to "n/a (not in this tree)" —
# which reads like a pass — if they disappear. These names bind to the SAME
# objects routes/home.py uses; there is exactly one cache dict in the process.
from astro_ai.routes.home import _HOMEPAGE_PANCHANG_CACHE, _homepage_panchang_cached  # noqa: F401


# Module-level logger. The unhandled-exception handler below is the last
# safety net in the process, so it must never itself raise NameError on `log`.
log = logging.getLogger(__name__)


app = FastAPI(title="astro-ai", version="0.0.1")


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


# Serve the PWA manifest, service worker, and icons from /static/.
# StaticFiles mounts must precede route definitions for the most specific
# path to win, but FastAPI's router handles this correctly either way.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
app.include_router(_subscribe_routes.router)
app.include_router(_feedback_routes.router)
app.include_router(_learn_routes.router)
app.include_router(_admin_routes.router)
app.include_router(_dasha_routes.router)
app.include_router(_ask_routes.router)
app.include_router(_matching_routes.router)
app.include_router(_charts_routes.router)


def cli() -> None:
    """Entry point for the `astro-ai` console script: starts uvicorn on localhost:8000."""
    uvicorn.run("astro_ai.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    cli()
