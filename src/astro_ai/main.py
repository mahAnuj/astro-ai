"""FastAPI app — form, natal reading, today's transits, cookie-persisted seeker."""

from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from astro_ai.chart import (
    compute_bhagya_score,
    ChartError,
    compute_chart,
    compute_dasha_state,
    compute_gochar_impacts,
    compute_kaal_sarp,
    compute_life_chapters,
    compute_dashamsa_chart,
    compute_manglik_details,
    compute_navamsha_chart,
    compute_panchang,
    compute_sade_sati_details,
    compute_transit_events,
    compute_transit_snapshot,
    compute_varshaphala,
    compute_vedic_flags,
    compute_yogas,
    symbol_for_rashi_label,
)
from astro_ai.i18n import translate as _i18n_translate
from astro_ai.llm import (
    BirthDetails,
    generate_ask_answer,
    generate_daily_reading,
    generate_dasha_deep_dive,
    generate_matching_narrative,
    generate_outlook_reading,
    generate_rashifal,
    generate_reading,
    parse_intro_and_sections,
    parse_sectioned_reading,
)
from astro_ai.matching import compute_guna_milan
from astro_ai import providers as llm_providers
from astro_ai.providers import AllProvidersExhausted

# --- transitional (#154): re-exported for routes not yet extracted; pruned in the cleanup commit
# These names now live in astro_ai.routes.*. Every route still defined below
# references them unqualified, so they are imported back into this namespace
# rather than rewritten at ~200 call sites — the split stays a pure move and
# each subsequent extraction commit shrinks this list. Position matters: the
# deps import must run before anything that reads the environment, because it
# owns the load_dotenv() calls that used to sit at module scope here.
from astro_ai.routes.deps import (
    ASK_PROMPT_PATH,
    DAILY_PROMPT_PATH,
    DASHA_DEEP_DIVE_PROMPT_PATH,
    MATCHING_PROMPT_PATH,
    MONTHLY_PROMPT_PATH,
    PROMPT_PATH,
    RASHIFAL_PROMPT_PATH,
    STATIC_DIR,
    YEARLY_PROMPT_PATH,
    _ask_cta_ctx,
    _ask_quota_bump,
    _ask_quota_remaining,
    _HINDI_MONTHS,
    _lang,
    _no_cdn_cache,
    _pretty_date,
    _pretty_weekday,
    _safe_redirect_target,
    _save_collection_synced,
    _site_url,
    require_admin,
    templates,
)
from astro_ai.routes.llm_support import _cached, _fire_error_alert, _llm_error_friendly
# --- end transitional


# Module-level logger used by the LLM-error handlers throughout this file
# (log.exception "…LLM generation failed" — one such call per LLM route).
# Before this existed, every one of those error paths crashed with
# NameError, converting a graceful "LLM temporarily unavailable" page into
# a bare 500. Any new error-path code in this module should use this
# logger, not an ad-hoc import.
import logging
log = logging.getLogger(__name__)


from astro_ai import cache, daily_cache, email_sender, events, feedback, festivals, learn_registry, notify, shloks, snapshots, storage, subscribers, trivia, trust_bar, users
import time as _time
from astro_ai.session import (
    SUPPORTED_LANGS,
    ChartCollection,
    SavedMatching,
    SessionUser,
    clear_collection,
    clear_user,
    load_ask_usage,
    load_collection,
    load_lang,
    load_last_matching,
    load_user,
    save_ask_usage,
    save_collection,
    save_lang,
    save_last_matching,
    save_session_atomic,
    save_user,
)


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
from astro_ai.routes import seo as _seo_routes
app.include_router(_seo_routes.router)


from astro_ai.routes import panchang as _panchang_routes
app.include_router(_panchang_routes.router)


from astro_ai.routes import festivals as _festivals_routes
app.include_router(_festivals_routes.router)


from astro_ai.routes import pages as _pages_routes
app.include_router(_pages_routes.router)


from astro_ai.routes import home as _home_routes
app.include_router(_home_routes.router)
# Re-exported, not redefined: scripts/perf_homepage.py --stages reaches into
# astro_ai.main for `templates`, `_HOMEPAGE_PANCHANG_CACHE` and
# `_homepage_panchang_cached`, and degrades to "n/a (not in this tree)" —
# which reads like a pass — if they disappear. These names bind to the SAME
# objects routes/home.py uses; there is exactly one cache dict in the process.
from astro_ai.routes.home import _HOMEPAGE_PANCHANG_CACHE, _homepage_panchang_cached


from astro_ai.routes import kundli as _kundli_routes
app.include_router(_kundli_routes.router)


from astro_ai.routes import dosha as _dosha_routes
app.include_router(_dosha_routes.router)


from astro_ai.routes import muhurat as _muhurat_routes
app.include_router(_muhurat_routes.router)


from astro_ai.routes import numerology as _numerology_routes
app.include_router(_numerology_routes.router)


from astro_ai.routes import kundli_card as _kundli_card_routes
app.include_router(_kundli_card_routes.router)


from astro_ai.routes import today as _today_routes
app.include_router(_today_routes.router)


from astro_ai.routes import account as _account_routes
app.include_router(_account_routes.router)


from astro_ai.routes import outlook as _outlook_routes
app.include_router(_outlook_routes.router)


from astro_ai.routes import rashifal as _rashifal_routes
app.include_router(_rashifal_routes.router)


from astro_ai.routes import subscribe as _subscribe_routes
app.include_router(_subscribe_routes.router)


from astro_ai.routes import feedback as _feedback_routes
app.include_router(_feedback_routes.router)


from astro_ai.routes import learn as _learn_routes
app.include_router(_learn_routes.router)


from astro_ai.routes import admin as _admin_routes
app.include_router(_admin_routes.router)


from astro_ai.routes import dasha as _dasha_routes
app.include_router(_dasha_routes.router)


from astro_ai.routes import ask as _ask_routes
app.include_router(_ask_routes.router)


@app.get("/matching", response_class=HTMLResponse)
async def matching_form(request: Request) -> HTMLResponse:
    """Form for two seekers — collects birth details for both, no auth needed.

    Passes the saved-chart collection so each side of the form can offer a
    "pick from saved" dropdown that auto-fills the four fields client-side.
    """
    return templates.TemplateResponse(
        request,
        "matching.html",
        {
            "lang": _lang(request),
            "collection": load_collection(request),
        },
    )


@app.post("/matching", response_class=HTMLResponse)
async def matching_result(
    request: Request,
    g_name: str = Form(default=""),
    g_birth_date: str = Form(...),
    g_birth_time: str = Form(...),
    g_birth_place: str = Form(...),
    b_name: str = Form(default=""),
    b_birth_date: str = Form(...),
    b_birth_time: str = Form(...),
    b_birth_place: str = Form(...),
) -> HTMLResponse:
    """Compute and render Ashtakoot Guna Milan for two charts."""
    lang = _lang(request)
    try:
        groom_chart = compute_chart(g_birth_date, g_birth_time, g_birth_place)
        bride_chart = compute_chart(b_birth_date, b_birth_time, b_birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:matching")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the charts", "message": str(err)},
            status_code=400,
        )

    guna = compute_guna_milan(groom_chart, bride_chart)
    verdict_key = {
        "Uttam":            "matching_verdict_uttam",
        "Madhyam":          "matching_verdict_madhyam",
        "Avara":            "matching_verdict_avara",
        "Not recommended":  "matching_verdict_below",
    }[guna.overall_verdict]

    # LLM narrative — sectioned compatibility reading. Best-effort; if the LLM
    # call fails we still show the scores + table, just without the prose.
    narrative_sections: list[tuple[str, str]] = []
    # Track whether the LLM narrative was served from cache — used below
    # to gate owner-notify + activity event to fresh generations only.
    # Defaults to False (no LLM = no cache = fresh POST worth notifying).
    was_cached = False
    if os.environ.get("OPENAI_API_KEY"):
        try:
            g_fp = cache.fingerprint_chart(g_birth_date, g_birth_time, g_birth_place)
            b_fp = cache.fingerprint_chart(b_birth_date, b_birth_time, b_birth_place)
            # Sort so the order of the two people doesn't matter for cache hits.
            pair_key = ":".join(sorted([g_fp, b_fp]))
            prompt_fp = cache.fingerprint_prompt(MATCHING_PROMPT_PATH)
            cache_key = f"matching:{pair_key}:{lang}:{prompt_fp}"
            # Detect cache hit BEFORE _cached() so downstream notify can skip.
            was_cached = cache.get(cache_key) is not None
            narrative_text = _cached(
                cache_key, route="matching", lang=lang, ttl_days=None,
                call_fn=lambda: generate_matching_narrative(
                    groom_name=g_name.strip(),
                    bride_name=b_name.strip(),
                    groom_chart=groom_chart,
                    bride_chart=bride_chart,
                    guna=guna,
                    prompt_path=MATCHING_PROMPT_PATH,
                    lang=lang,
                ),
            )
            narrative_sections = parse_sectioned_reading(narrative_text)
        except Exception as err:
            # Best-effort soft-fail: user still sees scores + table. But we
            # DO want to know — silent swallow was hiding LLM issues.
            log.exception("matching narrative LLM failed (scores still returned)")
            _fire_error_alert(request, err, "matching:narrative")
            narrative_sections = []  # surface as no-narrative; scores still render

    # Fire notify + activity event ONLY on fresh matching. A cache hit
    # means the same pair was matched before in this window — the user
    # is re-viewing, not doing a new match. Also protects against browser
    # refresh / back-nav / prefetch re-firing. `model` (empty on cache
    # hit) is reported when we do fire.
    _u_match = load_user(request)
    if not was_cached:
        notify.matching_done(
            groom_name=g_name.strip(), groom_dob=g_birth_date,
            bride_name=b_name.strip(), bride_dob=b_birth_date,
            total_score=f"{guna.total_awarded:g}/{guna.total_max} · {guna.overall_verdict}",
            lang=lang, user_email=(_u_match.email if _u_match else ""),
            model=llm_providers.last_used_model(),
        )
        events.record(
            type="form_matching",
            email=(_u_match.email if _u_match else ""),
            data={
                "groom_name": g_name.strip(), "groom_dob": g_birth_date,
                "bride_name": b_name.strip(), "bride_dob": b_birth_date,
                "total_score": f"{guna.total_awarded:g}/{guna.total_max}",
                "verdict": guna.overall_verdict, "lang": lang,
                "model": llm_providers.last_used_model(),
            },
        )

    response = templates.TemplateResponse(
        request,
        "matching_result.html",
        {
            "lang": lang,
            "guna": guna,
            "verdict_key": verdict_key,
            "sections": narrative_sections,
            "groom": {
                "name": g_name.strip(), "birth_date": g_birth_date,
                "birth_time": g_birth_time, "birth_place": g_birth_place.strip(),
            },
            "bride": {
                "name": b_name.strip(), "birth_date": b_birth_date,
                "birth_time": b_birth_time, "birth_place": b_birth_place.strip(),
            },
            "groom_chart": groom_chart,
            "bride_chart": bride_chart,
            **_ask_cta_ctx(request, hint="about your Kundli match"),
        },
    )
    # Persist the two partners in the session so /ask?ctx=matching can
    # recover both charts on a follow-up question without asking the
    # user to re-enter. Kept as one of the fields of the combined
    # __session cookie (24h TTL, same as the collection).
    save_last_matching(response, request, SavedMatching(
        groom_name=g_name.strip(), groom_birth_date=g_birth_date,
        groom_birth_time=g_birth_time, groom_birth_place=g_birth_place.strip(),
        bride_name=b_name.strip(), bride_birth_date=b_birth_date,
        bride_birth_time=b_birth_time, bride_birth_place=b_birth_place.strip(),
    ))
    return response


@app.post("/switch")
async def switch(
    request: Request,
    chart_id: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Activate the named saved chart, then redirect to `next` (default home)."""
    collection = load_collection(request).set_active(chart_id)
    response = RedirectResponse(_safe_redirect_target(next), status_code=303)
    _save_collection_synced(response, collection, request)
    return response


@app.post("/delete-chart")
async def delete_chart(
    request: Request,
    chart_id: str = Form(...),
) -> RedirectResponse:
    """Remove a saved chart; if it was active, activate whatever remains first."""
    collection = load_collection(request).remove(chart_id)
    response = RedirectResponse("/", status_code=303)
    if not collection.charts:
        clear_collection(response)
        # Also clear the persisted charts for signed-in users so their
        # cross-device state stays consistent with what they see here.
        user = load_user(request)
        if user is not None:
            try:
                users.save_charts(user.sub, collection)  # empty collection
            except Exception:
                pass
    else:
        _save_collection_synced(response, collection, request)
    return response


@app.post("/reset")
async def reset() -> RedirectResponse:
    """Wipe all saved charts — fresh-start button on the welcome-back panel."""
    response = RedirectResponse("/", status_code=303)
    clear_collection(response)
    return response


def cli() -> None:
    """Entry point for the `astro-ai` console script: starts uvicorn on localhost:8000."""
    uvicorn.run("astro_ai.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    cli()
