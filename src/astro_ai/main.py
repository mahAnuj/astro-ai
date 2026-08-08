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


def _rashifal_teaser(body: str, sentences: int = 2) -> str:
    """Pull the first ~2 sentences of a rashi body for the scannable teaser.

    Used by both the web /rashifal accordion and the daily email <details>
    summary. Keeps the visible-by-default snippet short enough to scan all
    12 rashis in seconds; the rest reveals on click/tap.
    """
    import re as _re
    parts = _re.split(r"(?<=[.!?])\s+", (body or "").strip())
    teaser = " ".join(parts[:sentences]).strip()
    if len(parts) > sentences and not teaser.endswith(("...", "…")):
        # No ellipsis — the "Read full" button makes the truncation explicit.
        pass
    return teaser


def _daily_rashifal_text(
    *, lang: str, today_iso: str, cache_key: str, storage_key: str, call_fn,
) -> str:
    """Fetch today's Rashifal text with a Tier-0 daily JSON file in front.

    Read order:
      Tier 0  — data/daily_cache/rashifal/{date}-{lang}.json   (this instance, today)
      Tier 1  — GCS blob rashifal/{date}-{lang}-{promptfp}.txt (cross-instance)
      Tier 2  — SQLite key rashifal:{date}:{lang}:{promptfp}   (this instance)
      Tier 3  — LLM generation (12 per-rashi parallel calls)

    Every write propagates UP to fill the tier-0 file, so the FIRST request of
    the day pays the cold-generate cost and every subsequent same-day request
    on the same instance is a single-file read. The file is human-readable —
    `cat data/daily_cache/rashifal/{date}-{lang}.json` shows exactly what
    users are seeing today.
    """
    hit = daily_cache.get("rashifal", lang, today_iso)
    if hit is not None and isinstance(hit.get("text"), str) and hit["text"].strip():
        cache.log_call("rashifal", lang, cache_hit=True)
        return hit["text"]

    text = _shared_three_tier(
        route="rashifal",
        cache_key=cache_key,
        storage_key=storage_key,
        lang=lang,
        call_fn=call_fn,
    )
    # Write the tier-0 file so subsequent same-day/same-instance reads skip
    # everything below. Payload is intentionally verbose for humans debugging
    # why today's Rashifal looks a certain way.
    daily_cache.put("rashifal", lang, {
        "text": text,
        "lang": lang,
        "date_iso": today_iso,
    }, today_iso)
    return text


def _shared_three_tier(
    *, route: str, cache_key: str, storage_key: str, lang: str, call_fn,
) -> str:
    """3-tier cache for content that's identical across users: GCS → SQLite → LLM.

    Use this for routes where every visitor would get the same LLM output
    (e.g. Rashifal — today only). Per-chart routes should stick with
    `_cached`; GCS gives them nothing because the SQLite key is unique per
    user anyway.

    Cache writes propagate UP: a GCS hit also populates SQLite so the same
    instance skips the GCS round-trip next time; a fresh generation populates
    both layers.
    """
    # Tier 1: GCS — survives Cloud Run cold starts.
    persistent = storage.get(storage_key)
    if persistent is not None:
        ok, reason = llm_providers.passes_quality(persistent, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            cache.put(cache_key, persistent, route=route, ttl_days=1)  # warm SQLite
            return persistent
        log.warning("shared cache GCS: bad entry for route=%s (%s) — regenerating", route, reason)

    # Tier 2: SQLite — per-instance, alive while the container is.
    sqlite_hit = cache.get(cache_key)
    if sqlite_hit is not None:
        ok, reason = llm_providers.passes_quality(sqlite_hit, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            storage.put(storage_key, sqlite_hit)  # backfill GCS
            return sqlite_hit
        log.warning("shared cache SQLite: bad entry for route=%s (%s) — regenerating", route, reason)

    # Tier 3: LLM generation. Persist to both layers.
    started = _time.time()
    text = call_fn()
    latency_ms = int((_time.time() - started) * 1000)
    in_tok = cache.estimate_tokens(text) * 2
    out_tok = cache.estimate_tokens(text)
    cache.put(cache_key, text, route=route, ttl_days=1,
              input_tokens=in_tok, output_tokens=out_tok)
    cache.log_call(route, lang, cache_hit=False,
                   input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency_ms)
    storage.put(storage_key, text)
    return text


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


@app.get("/kundli/card")
async def kundli_cosmic_card(request: Request) -> Response:
    """Cosmic Card (Issue #113) — shareable 1080×1920 SVG of the user's chart.

    Served as image/svg+xml so browsers render it inline; social platforms
    (WhatsApp, Instagram, Twitter) accept SVG as og:image on most modern
    stacks. Users can right-click "Save as" for a copy.

    Ships as SVG (not PNG) to avoid new deps (Pillow / cairosvg / Playwright).
    A future PNG-rasterize path can wrap this if platforms reject the SVG.
    """
    saved = load_collection(request).active
    if saved is None:
        # Guard against no-chart access — redirect to form.
        return RedirectResponse("/?needs_chart=card", status_code=303)
    details = saved.to_birth_details()
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:cosmic_card")
        return Response("Could not render card: " + str(err), status_code=400)

    display_name = (details.name or "").strip() or ""
    moon = next((p for p in chart.planets if p.name == "Moon"), None)
    sun = next((p for p in chart.planets if p.name == "Sun"), None)
    manglik = compute_manglik_details(chart)
    sade_sati = compute_sade_sati_details(chart)

    tpl = templates.env.get_template("cosmic_card.svg")
    svg = tpl.render(
        details=details,
        chart=chart,
        display_name=display_name,
        moon_nakshatra=(moon.nakshatra if moon else ""),
        lagna_glyph=symbol_for_rashi_label(chart.lagna_rashi),
        moon_glyph=symbol_for_rashi_label(moon.rashi) if moon else "",
        sun_glyph=symbol_for_rashi_label(sun.rashi) if sun else "",
        manglik=manglik,
        sade_sati=sade_sati,
    )
    # Cache for 1h since chart details rarely change; browsers + Fastly cache too.
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="cosmic-card-{details.name or "kundli"}.svg"',
        },
    )


@app.get("/today", response_class=HTMLResponse)
async def today(request: Request) -> HTMLResponse:
    """Today's personalised Vedic reading using the active saved chart."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=today", status_code=303)
    saved_details = saved.to_birth_details()

    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )

    transit = compute_transit_snapshot(natal)
    flags = compute_vedic_flags(natal)
    panchang = compute_panchang(natal)
    gochar_impacts = compute_gochar_impacts(natal)
    lang = _lang(request)

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "API key not configured",
                "message": (
                    "The server can't reach the LLM because OPENAI_API_KEY isn't set. "
                    "Add it to .env and reload."
                ),
            },
            status_code=503,
        )

    chart_fp = cache.fingerprint_chart(
        saved_details.birth_date, saved_details.birth_time, saved_details.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(DAILY_PROMPT_PATH)
    cache_key = f"today:{chart_fp}:{date.today().isoformat()}:{lang}:{prompt_fp}"
    try:
        reading_text = _cached(
            cache_key, route="today", lang=lang, ttl_days=1,
            call_fn=lambda: generate_daily_reading(
                saved_details,
                natal=natal,
                transit=transit,
                flags=flags,
                panchang=panchang,
                prompt_path=DAILY_PROMPT_PATH,
                lang=lang,
            ),
        )
    except Exception as err:
        log.exception("today's outlook LLM generation failed")
        _fire_error_alert(request, err, "today")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": _title,
                "message": _msg,
            },
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    return templates.TemplateResponse(
        request,
        "today.html",
        {
            "details": saved_details,
            "natal": natal,
            "transit": transit,
            "flags": flags,
            "panchang": panchang,
            "gochar_impacts": gochar_impacts,
            "reading": reading_text,
            "today_date": date.today().isoformat(),
            "today_pretty": _pretty_date(date.today().isoformat(), lang),
            "lang": lang,
        },
    )


@app.post("/lang")
async def set_lang(
    request: Request,
    lang: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Switch reading language; persisted in the combined __session cookie."""
    response = RedirectResponse(_safe_redirect_target(next), status_code=303)
    save_lang(response, lang, request)
    return response


# ─── Google Sign-In auth endpoints ──────────────────────────────────────────
# GIS flow: browser gets an ID token from Google, POSTs it here. We verify
# the token against Google's public keys (signature, expiry, audience) and
# persist the resulting user into the same __session cookie. No password
# management, no OAuth redirect dance.


@app.post("/auth/google")
async def auth_google(
    request: Request,
    credential: str = Form(...),
) -> JSONResponse:
    """Verify a Google Identity Services ID token and start a signed-in session.

    The `credential` is a JWT from the GIS button callback on the frontend.
    We validate it against Google's public keys with the expected audience
    (our GOOGLE_CLIENT_ID). On success we store {email, name, sub, since}
    in the session cookie. The client then reloads / navigates as needed.
    """
    from datetime import datetime, timezone
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        return JSONResponse(
            {"ok": False, "error": "Google Sign-In not configured on server."},
            status_code=503,
        )
    try:
        info = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=30,  # small tolerance for clock drift
        )
    except ValueError as err:
        # Bad signature, wrong audience, expired token — treat all as auth failure.
        return JSONResponse(
            {"ok": False, "error": f"Invalid Google credential: {err}"},
            status_code=401,
        )

    # Only email-verified accounts are accepted — otherwise anyone can
    # sign in with an arbitrary unverified email.
    if not info.get("email") or not info.get("email_verified"):
        return JSONResponse(
            {"ok": False, "error": "Google account email is not verified."},
            status_code=401,
        )

    user = SessionUser(
        email=str(info["email"]).lower(),
        name=str(info.get("name", "")),
        sub=str(info["sub"]),
        since=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    )
    # Persist to users.json — silent failure on storage error (auth still
    # succeeds; user just isn't in our persistent record). Cookie is the
    # source-of-truth for THIS session; users.json is for cross-device
    # continuity, Premium subscription tracking, and analytics.
    _is_new_user = False
    try:
        _ok, _is_new_user = users.upsert_user(sub=user.sub, email=user.email, name=user.name)
    except Exception as err:
        # Log and continue — never let a storage hiccup block sign-in.
        import logging
        logging.getLogger(__name__).warning(
            "users.upsert_user failed for %s: %s", user.email, err
        )
    notify.new_signin(email=user.email, name=user.name, first_time=_is_new_user)

    # Cross-device chart sync: merge (this device's charts) ∪ (user's
    # cross-device charts) and write the union back to BOTH the cookie
    # and users.json. Signed-in users' charts follow them across devices;
    # anonymous / storage-unavailable paths silently keep the cookie as-is.
    response = JSONResponse({"ok": True, "email": user.email, "name": user.name})
    merged: ChartCollection | None = None
    try:
        cookie_collection = load_collection(request)
        user_collection = users.load_charts(user.sub)
        merged = users.merge_collections(cookie=cookie_collection, user=user_collection)
        users.save_charts(user.sub, merged)  # silent no-op if storage unavailable
    except Exception as err:
        log.exception("chart sync on sign-in failed for %s", user.email)
        _fire_error_alert(request, err, "auth:chart_sync")
        merged = None  # leave existing cookie charts untouched on failure

    # SINGLE atomic cookie write — write user AND merged collection in one
    # go. Doing two consecutive save_xxx() calls (save_collection then
    # save_user) would result in the second overwriting the first because
    # both re-read the request cookie (which hasn't seen the first write).
    # See session.save_session_atomic docstring for the exact failure mode.
    save_session_atomic(response, request, user=user, collection=merged)
    return response


@app.post("/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:
    """Sign the user out — clears the user portion of the session cookie."""
    response = JSONResponse({"ok": True})
    clear_user(response, request)
    return response


@app.get("/account", response_class=HTMLResponse)
async def account(request: Request) -> HTMLResponse:
    """Signed-in user profile page — email, saved charts, sign-out.

    Redirects home if not signed in (soft nudge: they can click the Sign In
    button in nav from wherever). Later this page will show Premium status
    and manage-subscription controls.
    """
    user = load_user(request)
    if user is None:
        return RedirectResponse("/", status_code=303)
    collection = load_collection(request)
    # Prefer persisted created_at from users.json — accurate "member since"
    # that survives sign-out / cookie clear. Falls back to the session
    # cookie's `since` (this-session-only) if the persistent record is
    # missing (e.g. storage was unavailable when they first signed in).
    persisted = users.find_by_sub(user.sub)
    member_since = (persisted.created_at if persisted else user.since) or user.since
    return templates.TemplateResponse(
        request, "account.html",
        {
            "current_user": user,
            "charts": collection.charts,
            "active_id": collection.active_id,
            "saved_charts_count": len(collection.charts),
            "member_since": member_since,
            "lang": _lang(request),
        },
    )


@app.get("/monthly", response_class=HTMLResponse)
async def monthly(request: Request) -> HTMLResponse:
    """30-day outlook for the active saved chart."""
    return await _render_outlook(
        request,
        active_page="monthly",
        prompt_path=MONTHLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="monthly_title",
        title_anon_key="monthly_title_anon",
        subtitle_key="monthly_subtitle",
        reading_label_key="monthly_reading",
        window_label="30 days",
        events_days=30,
        events_step_days=1,
        events_planets=("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
        include_varshaphala=False,
    )


@app.get("/yearly", response_class=HTMLResponse)
async def yearly(request: Request) -> HTMLResponse:
    """12-month outlook for the active saved chart, with Varshaphala (annual chart)."""
    return await _render_outlook(
        request,
        active_page="yearly",
        prompt_path=YEARLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="yearly_title",
        title_anon_key="yearly_title_anon",
        subtitle_key="yearly_subtitle",
        reading_label_key="yearly_reading",
        window_label="12 months",
        events_days=365,
        events_step_days=7,
        # For yearly: weekly steps + drop Sun (changes every month — noisy).
        events_planets=("Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
        include_varshaphala=True,
    )


async def _render_outlook(
    request: Request,
    *,
    active_page: str,
    prompt_path: Path,
    template_name: str,
    title_key: str,
    title_anon_key: str,
    subtitle_key: str,
    reading_label_key: str,
    window_label: str,
    events_days: int,
    events_step_days: int,
    events_planets: tuple[str, ...],
    include_varshaphala: bool = False,
) -> HTMLResponse:
    """Shared monthly/yearly renderer — same flow, different prompt + labels + scan window."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse(f"/?needs_chart={active_page}", status_code=303)
    saved_details = saved.to_birth_details()

    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )

    transit = compute_transit_snapshot(natal)
    flags = compute_vedic_flags(natal)
    gochar_impacts = compute_gochar_impacts(natal)
    events = compute_transit_events(
        natal, days=events_days, step_days=events_step_days, planets=events_planets
    )
    lang = _lang(request)

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "API key not configured",
                "message": "The server can't reach the LLM because OPENAI_API_KEY isn't set. Add it to .env and reload.",
            },
            status_code=503,
        )

    chart_fp = cache.fingerprint_chart(
        saved_details.birth_date, saved_details.birth_time, saved_details.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(prompt_path)
    today_str = date.today().isoformat()
    # Monthly: bucket by week (cache for 7 days); Yearly: bucket by month (30 days).
    if active_page == "monthly":
        bucket = f"week-{date.today().isocalendar()[0]}-{date.today().isocalendar()[1]}"
        ttl = 7
    else:
        bucket = date.today().strftime("%Y-%m")  # year-month
        ttl = 30
    cache_key = f"{active_page}:{chart_fp}:{bucket}:{lang}:{prompt_fp}"
    try:
        reading_text = _cached(
            cache_key, route=active_page, lang=lang, ttl_days=ttl,
            call_fn=lambda: generate_outlook_reading(
                saved_details,
                natal=natal,
                transit=transit,
                flags=flags,
                gochar_impacts=gochar_impacts,
                events=events,
                prompt_path=prompt_path,
                lang=lang,
            ),
        )
    except Exception as err:
        log.exception("outlook LLM generation failed")
        _fire_error_alert(request, err, "outlook")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": _title,
                "message": _msg,
            },
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    # Split the LLM output: time-segmented prose intro + 5 life-area cards.
    intro, sections = parse_intro_and_sections(reading_text)
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "active_page": active_page,
            "details": saved_details,
            "natal": natal,
            "transit": transit,
            "flags": flags,
            "gochar_impacts": gochar_impacts,
            "events": events,
            "varshaphala": compute_varshaphala(natal) if include_varshaphala else None,
            "reading": reading_text,
            "reading_intro": intro,
            "reading_sections": sections,
            "lang": lang,
            "title_key": title_key,
            "title_anon_key": title_anon_key,
            "subtitle_key": subtitle_key,
            "reading_label_key": reading_label_key,
            "window_label": window_label,
            "today_date": date.today().isoformat(),
            "today_pretty": _pretty_date(date.today().isoformat(), lang),
        },
    )


@app.get("/rashifal", response_class=HTMLResponse)
async def rashifal(request: Request) -> HTMLResponse:
    """Rashifal landing — 12 flip cards, one per Moon sign.

    Zero LLM traffic on this page. Users tap their sign to reveal today's
    reading (fetched via HTMX GET /rashifal/{slug}). This replaces the
    old 'render all 12 sections upfront' flow that made cold-cache visits
    slow AND caused AllProvidersExhausted when many LLM calls fired at
    once. Now each user costs exactly one LLM call for their own sign —
    unless another visitor already warmed the cache for that rashi today.
    """
    lang = _lang(request)
    today_iso = date.today().isoformat()
    return _no_cdn_cache(templates.TemplateResponse(
        request, "rashifal_grid.html",
        {
            "lang": lang,
            "today_date": today_iso,
            "today_pretty": _pretty_date(today_iso, lang),
        },
    ))


# Per-rashi metadata used by /rashifal/{rashi} — mirrors _RASHI_ANCHORS
# in llm.py plus the presentation-only glyph + colour that main.py needs
# for the standalone-page hero. Kept in main.py rather than llm.py to
# avoid coupling the LLM layer to UI concerns.
_RASHIFAL_UI_META: dict[str, dict[str, str]] = {
    "aries":       {"glyph": "♈", "glyph_color": "text-orange-700",  "element": "fire",  "quality": "Movable",  "lord": "Mars",     "sa": "Mesha"},
    "taurus":      {"glyph": "♉", "glyph_color": "text-emerald-700", "element": "earth", "quality": "Fixed",    "lord": "Venus",    "sa": "Vrishabha"},
    "gemini":      {"glyph": "♊", "glyph_color": "text-sky-700",     "element": "air",   "quality": "Dual",     "lord": "Mercury",  "sa": "Mithuna"},
    "cancer":      {"glyph": "♋", "glyph_color": "text-teal-700",    "element": "water", "quality": "Movable",  "lord": "Moon",     "sa": "Karka"},
    "leo":         {"glyph": "♌", "glyph_color": "text-orange-700",  "element": "fire",  "quality": "Fixed",    "lord": "Sun",      "sa": "Simha"},
    "virgo":       {"glyph": "♍", "glyph_color": "text-emerald-700", "element": "earth", "quality": "Dual",     "lord": "Mercury",  "sa": "Kanya"},
    "libra":       {"glyph": "♎", "glyph_color": "text-sky-700",     "element": "air",   "quality": "Movable",  "lord": "Venus",    "sa": "Tula"},
    "scorpio":     {"glyph": "♏", "glyph_color": "text-teal-700",    "element": "water", "quality": "Fixed",    "lord": "Mars",     "sa": "Vrishchika"},
    "sagittarius": {"glyph": "♐", "glyph_color": "text-orange-700",  "element": "fire",  "quality": "Dual",     "lord": "Jupiter",  "sa": "Dhanu"},
    "capricorn":   {"glyph": "♑", "glyph_color": "text-emerald-700", "element": "earth", "quality": "Movable",  "lord": "Saturn",   "sa": "Makara"},
    "aquarius":    {"glyph": "♒", "glyph_color": "text-sky-700",     "element": "air",   "quality": "Fixed",    "lord": "Saturn",   "sa": "Kumbha"},
    "pisces":      {"glyph": "♓", "glyph_color": "text-teal-700",    "element": "water", "quality": "Dual",     "lord": "Jupiter",  "sa": "Meena"},
}


@app.get("/rashifal/{rashi}", response_class=HTMLResponse)
async def rashifal_single(request: Request, rashi: str) -> HTMLResponse:
    """One rashi's daily reading. Serves 2 use cases:

    1. HTMX fragment — triggered by clicking a flip card on /rashifal.
       We detect via the HX-Request header and return just the reading
       content (rendered by _rashifal_card_content.html) for injection
       into the card's front face.

    2. Full standalone page — /rashifal/aries as a direct-visit URL.
       This is the SEO play: 12 daily-fresh indexable pages, each with
       Article JSON-LD schema and a canonical URL. Renders in
       rashifal_single.html.

    LLM cost: exactly ONE call per (rashi, lang, date) tuple, cached
    for the rest of the day via daily_cache. When 100 users hit /rashifal
    and each taps their own sign, worst case is 12 LLM calls across the
    day (one per rashi), not 100.
    """
    from astro_ai.llm import (
        RASHI_SLUG_TO_INDEX, RASHI_CANONICAL_SLUGS,
        generate_rashifal_for_rashi,
    )
    slug = (rashi or "").strip().lower()
    idx = RASHI_SLUG_TO_INDEX.get(slug)
    if idx is None:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Unknown rashi",
             "message": f"'{rashi}' is not one of the 12 rashis. Try /rashifal to pick your Moon sign."},
            status_code=404,
        )
    canonical_slug = RASHI_CANONICAL_SLUGS[idx]
    ui = _RASHIFAL_UI_META[canonical_slug]
    lang = _lang(request)
    today_iso = date.today().isoformat()
    # `hx-boost=true` on <body> means EVERY internal link sends HX-Request,
    # so we can't use the generic HX-Request header to decide fragment vs
    # full-page. The card-click on /rashifal grid explicitly sets
    # HX-Rashifal-Fragment=1 via hx-headers — check that instead so direct
    # URL bar navigation to /rashifal/aries always renders the full page.
    is_htmx = request.headers.get("hx-rashifal-fragment") == "1"

    if not os.environ.get("OPENAI_API_KEY"):
        msg = "Rashifal is temporarily unavailable — API key not configured."
        if is_htmx:
            return HTMLResponse(f'<div class="text-sm text-stone-600 p-2">{msg}</div>', status_code=503)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured", "message": msg},
            status_code=503,
        )

    # Per-rashi daily cache — key: rashifal_{slug}, e.g. rashifal_aries.
    cache_key = f"{canonical_slug}-{lang}"
    cached = daily_cache.get("rashifal_single", cache_key, today_iso)
    reading_body: str | None = cached.get("body") if cached else None

    if reading_body is None:
        # Generate. Wrap in the same try/except pattern the old route had
        # so an LLM failure returns a friendly-error response.
        try:
            neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
            transit = compute_transit_snapshot(neutral_chart)
            panchang_now = compute_panchang(neutral_chart)
            # DELIBERATELY singular — see the note at the /panchang call site.
            # llm._build_rashifal_day_signals takes `dict | None` and emits one
            # "Today is X" sentence into an already-crowded signal block; a list
            # would raise AttributeError there. festivals.festival_for_date()
            # tie-breaks in registry order, which puts the pan-Indian festival
            # first, so the one-slot prompt gets the right one.
            festival_now = festivals.festival_for_date(date.today())
            raw = generate_rashifal_for_rashi(
                rashi_index=idx, transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                panchang=panchang_now, festival=festival_now,
            )
            # Strip the '## Rashi / Sanskrit' heading line — we render our own.
            sections = parse_sectioned_reading(raw)
            reading_body = sections[0][1] if sections else raw
            daily_cache.put("rashifal_single", cache_key, {
                "body": reading_body,
                "rashi_slug": canonical_slug,
                "lang": lang,
            }, today_iso)
        except Exception as err:
            log.exception("rashifal single-rashi generation failed for %s", canonical_slug)
            _fire_error_alert(request, err, f"rashifal_single:{canonical_slug}")
            _title, _msg = _llm_error_friendly(err)
            if is_htmx:
                # Fragment path — return a card-shaped retry block, not the
                # generic 'safe to re-submit your input' message (there is
                # no form to re-submit here; a card flip). Give a clear
                # retry button that re-fires HTMX + a link to the full
                # standalone page as a fallback.
                is_rate = isinstance(err, AllProvidersExhausted)
                fragment_html = (
                    '<div class="h-full flex flex-col items-center justify-center text-center gap-3 p-4">'
                    f'  <div class="text-3xl" aria-hidden="true">{"🕉️" if is_rate else "⚠️"}</div>'
                    f'  <div class="text-sm font-semibold text-stone-800">{"Still gathering today\'s sky…" if is_rate else "Reading could not load"}</div>'
                    f'  <div class="text-xs text-stone-600 leading-relaxed">{"Experiencing high traffic. Try again in a minute." if is_rate else _msg}</div>'
                    '  <div class="flex gap-2 pt-1">'
                    f'    <button type="button" class="text-xs text-astro-700 hover:text-astro-800 hover:underline font-semibold" '
                    f'            hx-get="/rashifal/{canonical_slug}" hx-target="closest [data-card-front]" hx-swap="innerHTML" '
                    f'            hx-headers=\'{{"HX-Rashifal-Fragment": "1"}}\'>Try again</button>'
                    '    <span class="text-stone-300">·</span>'
                    f'    <a href="/rashifal/{canonical_slug}" class="text-xs text-astro-700 hover:text-astro-800 hover:underline font-semibold">Open full page</a>'
                    '  </div>'
                    '</div>'
                )
                return HTMLResponse(
                    fragment_html,
                    status_code=503 if is_rate else 502,
                )
            return templates.TemplateResponse(
                request, "error.html",
                {"title": _title, "message": _msg},
                status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
            )

    # Common template context.
    from astro_ai.llm import _RASHI_ANCHORS
    anchor = _RASHI_ANCHORS[idx]
    ctx = {
        "rashi_slug": canonical_slug,
        "rashi_en": anchor["en"],
        "rashi_sa": anchor["sa"],
        "glyph": ui["glyph"],
        "glyph_color": ui["glyph_color"],
        "element": ui["element"],
        "quality": ui["quality"],
        "lord": ui["lord"],
        "reading_body": reading_body,
        "today_date": today_iso,
        "today_pretty": _pretty_date(today_iso, lang),
        "permalink": f"/rashifal/{canonical_slug}",
        "lang": lang,
    }
    template = "_rashifal_card_content.html" if is_htmx else "rashifal_single.html"
    # Only cache-harden the full-page render; the HTMX fragment is
    # per-user-session content that Fastly ignores anyway (POST-like).
    resp = templates.TemplateResponse(request, template, ctx)
    return resp if is_htmx else _no_cdn_cache(resp)


@app.post("/subscribe/lookup")
async def subscribe_lookup(email: str = Form(...)) -> JSONResponse:
    """Return the current preferences for a subscriber, or defaults if unknown.

    Called from the subscribe modal on email input (debounced) so the form
    prefills with the subscriber's existing lang / city / rashi choices. This
    prevents the silent reset that happens when a returning subscriber submits
    the form with default field values — the `subscribe()` upsert overwrites
    lang and rashi unconditionally.

    Same shape returned for subscribed and unsubscribed emails; the
    `subscribed` flag distinguishes them so the UI can show a "welcome back"
    hint. Not privacy-perfect (an attacker can enumerate) but proportional
    for a public astrology mailing list at this scale.
    """
    sub = subscribers.find_by_email(email)
    if sub is None:
        return JSONResponse({
            "ok": True, "subscribed": False,
            "lang": "en", "city": "", "rashi": "all",
        })
    return JSONResponse({
        "ok": True, "subscribed": True,
        "lang": sub.get("lang", "en"),
        "city": sub.get("city", ""),
        "rashi": sub.get("rashi", "all"),
    })


@app.post("/subscribe")
async def subscribe(request: Request,
                    email: str = Form(...),
                    lang: str = Form("en"),
                    city: str = Form(""),
                    rashi: str = Form("all")) -> JSONResponse:
    """Add an email to the daily-Rashifal subscriber list.

    Called from the modal in _subscribe_modal.html via fetch(). Returns JSON
    `{ok: true}` on success or `{ok: false, error: "..."}` so the frontend
    can show inline feedback without a full page reload.

    Side effect: sends a one-off welcome email to brand-new subscribers
    (skipped for re-subscribes). Welcome failure is logged but doesn't
    block the success response — the subscription itself already saved.
    """
    ok, is_new, msg = subscribers.subscribe(email, lang, city, rashi)
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    if is_new:
        try:
            _send_welcome_email(email, lang, city, rashi)
        except Exception as err:
            # Log and continue — the user is already subscribed; missing
            # welcome is a minor degradation, not a failure.
            import logging
            logging.getLogger(__name__).warning("welcome email failed for %s: %s", email, err)
        # Only notify on brand-new subscriptions, not re-subscribes.
        notify.subscribed(email=email, source=(city or "unknown"), lang=lang)
    return JSONResponse({"ok": True})


def _panchang_for_city(city: str | None, request_cache: dict | None = None):
    """Compute today's Panchang for a city. Returns None when no city given.

    Panchang (sunrise, Rahu Kaal, Abhijit Muhurta) is location-dependent —
    Delhi's times don't match Bangalore's. Rather than show wrong times,
    skip the Panchang section entirely when the subscriber hasn't told us
    where they are. Empty/blank/whitespace-only city all count as "no city".

    `request_cache` is keyed by city string and shared across the send loop
    so 200 Mumbai subscribers don't each trigger a Nominatim lookup.
    """
    resolved = (city or "").strip()
    if not resolved:
        return None
    if request_cache is not None and resolved in request_cache:
        return request_cache[resolved]
    try:
        # compute_chart's only job here is to geocode + give lat/lon/tz;
        # the date+time are throwaway. ~50-200ms incl. Nominatim lookup.
        chart_for_loc = compute_chart("2000-01-01", "12:00", resolved)
        p = compute_panchang(chart_for_loc)
    except Exception:
        # Couldn't geocode this city — degrade gracefully to no-Panchang
        # rather than guessing with a wrong location.
        p = None
    if request_cache is not None and p is not None:
        request_cache[resolved] = p
    return p


def _email_context(*, lang: str, city: str | None, request_cache: dict | None = None) -> dict:
    """Build the per-subscriber template context shared by daily + welcome emails.

    All the date/shlok/festival/trivia lookups are deterministic for a given
    date + lang, so they're computed once per (lang, date) and reused inside
    the same send call. Panchang is per-city.
    """
    today = date.today()
    panchang = _panchang_for_city(city, request_cache=request_cache)
    return {
        "lang": lang,
        "today_iso": today.isoformat(),
        "today_pretty": today.strftime("%A, %d %B %Y"),
        "panchang": panchang,
        "shlok": shloks.shlok_for_date(today),
        # ALL festivals, not the first. The email callout is a factual
        # "what day is it" block with room to repeat, so dropping the second
        # festival on a shared date (Makar Sankranti + Pongal, 2026-01-14) is
        # plain data loss to the subscriber. Both email templates loop over
        # this and render nothing when the list is empty.
        "festivals": festivals.festivals_for_date(today),
        "trivia": trivia.trivia_for_date(today),
        "site_url": _site_url(),
    }


def _filter_rashi_sections(sections: list, rashi: str) -> list:
    """If a subscriber chose a single rashi, return just that card. Otherwise
    return all 12. Matches by the English slug (first word of "Aries / Mesha")."""
    if not rashi or rashi == "all":
        return sections
    return [s for s in sections
            if s[1].split('/')[0].strip().lower() == rashi.lower()] or sections


def _send_welcome_email(email: str, lang: str, city: str = "", rashi: str = "all") -> bool:
    """Send the one-off welcome email to a newly-subscribed user.

    Embeds today's Rashifal + Panchang + shlok + trivia so the first email
    delivers immediate value, not just a "you're subscribed" confirmation.
    Reuses _shared_three_tier so the Rashifal piggybacks on the same daily
    generation the morning blast uses — zero extra LLM cost.
    """
    today_iso = date.today().isoformat()
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)

    # Build today's Rashifal sections (may trigger generation if cold).
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
        transit = compute_transit_snapshot(neutral_chart)
        text = _daily_rashifal_text(
            lang=lang,
            today_iso=today_iso,
            cache_key=f"rashifal:{today_iso}:{lang}:{prompt_fp}",
            storage_key=f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt",
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                panchang=compute_panchang(neutral_chart),
                # Singular by design — the LLM prompt has one festival slot
                # (llm.py takes `dict | None`). The welcome email's own
                # festival CALLOUT does show all of them; this only shapes
                # the generated prose.
                festival=festivals.festival_for_date(date.today()),
            ),
        )
        sections = [
            (symbol_for_rashi_label(title) or "✦", title, _rashifal_teaser(body), body)
            for title, body in parse_sectioned_reading(text)
        ]
    except Exception:
        # If Rashifal generation fails entirely, send the rest of the
        # welcome anyway — better than blocking on a missed reading.
        sections = []

    ctx = _email_context(lang=lang, city=city)
    ctx["rashifal_sections"] = _filter_rashi_sections(sections, rashi)
    ctx["unsubscribe_url"] = (
        f"{ctx['site_url']}/unsubscribe?email={email}"
        f"&token={subscribers.unsubscribe_token(email)}"
    )

    html = templates.env.get_template("email/welcome.html").render(**ctx)
    subject = (
        "Shubh Bhagya में स्वागत है — कल से दैनिक राशिफल शुरू"
        if lang == "hi"
        else "Welcome to Shubh Bhagya — your daily Rashifal starts tomorrow"
    )
    return email_sender.send(email, subject=subject, html=html)


@app.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(request: Request, email: str = "", token: str = "") -> HTMLResponse:
    """One-click unsubscribe landing page. Linked from every email's footer.

    Token is an HMAC of the email signed with our cookie secret, so we can't
    be tricked into removing arbitrary addresses by URL-tampering attackers.
    """
    if not email or not token or not subscribers.verify_unsubscribe_token(email, token):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Invalid unsubscribe link",
             "message": "This link looks broken. Please reply to one of your Bhagya emails and we'll remove you manually."},
            status_code=400,
        )
    ok, _ = subscribers.unsubscribe(email)
    title = "You're unsubscribed" if ok else "Couldn't process right now"
    body = ("We've removed your email from Bhagya's daily Rashifal list. You can resubscribe anytime."
            if ok else "Please try again in a minute, or reply to one of our emails.")
    return templates.TemplateResponse(
        request, "error.html",
        {"title": title, "message": body},
        status_code=200 if ok else 503,
    )


@app.post("/admin/send-daily-rashifal", dependencies=[Depends(require_admin)])
async def send_daily_rashifal(request: Request) -> JSONResponse:
    """Send today's Rashifal email to every active subscriber.

    Triggered by Cloud Scheduler at 7 AM IST daily. Auth-gated by basic auth
    so a leaked URL can't drain Brevo quota. Reads (or generates if needed)
    today's Rashifal per language, then per-subscriber sends via Brevo.
    """
    today_iso = date.today().isoformat()
    today_pretty = date.today().strftime("%A, %d %B %Y")
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)
    site_url = _site_url()

    # Build the Rashifal section list for each language we actually need.
    # We trigger generation via _shared_three_tier so cold-start days still
    # produce content rather than emailing empty bodies.
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
    except ChartError as err:
        return JSONResponse({"ok": False, "error": f"Couldn't compute reference chart: {err}"}, status_code=500)
    transit = compute_transit_snapshot(neutral_chart)

    sections_by_lang: dict[str, list] = {}
    for lang in ("en", "hi"):
        cache_key = f"rashifal:{today_iso}:{lang}:{prompt_fp}"
        storage_key = f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt"
        try:
            text = _daily_rashifal_text(
                lang=lang,
                today_iso=today_iso,
                cache_key=cache_key,
                storage_key=storage_key,
                call_fn=lambda lang=lang: generate_rashifal(
                    transit=transit, today_iso=today_iso,
                    prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                    panchang=compute_panchang(neutral_chart),
                    # Singular by design — one festival slot in the prompt
                    # (llm.py takes `dict | None`), and this is the daily
                    # blast: a type error here fails the whole 7 AM send.
                    # The email's festival callout renders all of them.
                    festival=festivals.festival_for_date(date.today()),
                ),
            )
            sections_by_lang[lang] = [
                (symbol_for_rashi_label(title) or "✦", title, _rashifal_teaser(body), body)
                for title, body in parse_sectioned_reading(text)
            ]
        except Exception as err:
            log.exception("rashifal (per-rashi API) LLM generation failed")
            _fire_error_alert(request, err, "rashifal_api")
            _title, _msg = _llm_error_friendly(err)
            return JSONResponse(
                {"ok": False, "error": _msg},
                status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
            )

    # Render + send per subscriber. Panchang is per-city, cached across
    # the send so subscribers sharing a city only trigger one geocode.
    template = templates.env.get_template("email/daily_rashifal.html")
    panchang_cache: dict = {}
    sent = failed = 0
    failures: list[str] = []
    for sub in subscribers.list_subscribers():
        lang = sub.get("lang", "en")
        if lang not in sections_by_lang:
            lang = "en"

        ctx = _email_context(lang=lang, city=sub.get("city", ""),
                             request_cache=panchang_cache)
        ctx["rashifal_sections"] = _filter_rashi_sections(
            sections_by_lang[lang], sub.get("rashi", "all")
        )
        ctx["unsubscribe_url"] = (
            f"{site_url}/unsubscribe?email={sub['email']}"
            f"&token={subscribers.unsubscribe_token(sub['email'])}"
        )
        html = template.render(**ctx)
        subject = "आज का राशिफल — Shubh Bhagya" if lang == "hi" else "Today's Rashifal — Shubh Bhagya"
        ok = email_sender.send(sub["email"], subject=subject, html=html)
        if ok:
            sent += 1
        else:
            failed += 1
            failures.append(sub["email"])

    return JSONResponse({
        "ok": True,
        "date": today_iso,
        "total_subscribers": len(subscribers.list_subscribers()),
        "sent": sent,
        "failed": failed,
        "failed_emails": failures[:20],  # cap so we don't return MB-sized lists
    })


@app.post("/feedback")
async def submit_feedback(
    request: Request,
    type: str = Form("other"),
    message: str = Form(""),
    email: str = Form(""),
    page: str = Form(""),
) -> JSONResponse:
    """Persist a feedback entry to GCS + notify admin via email.

    Called from the floating feedback widget via fetch(). Returns JSON
    `{ok: true}` on success or `{ok: false, error: ...}` for inline
    error display in the modal.
    """
    user_agent = request.headers.get("user-agent", "")
    ok, msg, entry = feedback.add(
        type=type, message=message, email=email,
        page=page, user_agent=user_agent,
    )
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)

    # Telegram alert for the owner — feedback should never sit unread.
    try:
        notify.feedback_submitted(
            type=entry["type"] if entry else type,
            message=entry["message"] if entry else message,
            page=entry.get("page", "") if entry else page,
            email=entry.get("email", "") if entry else email,
        )
    except Exception:
        pass

    # Notify admin via email so feedback doesn't sit unread in a GCS file.
    # Best-effort — failure to email shouldn't fail the user's submit.
    try:
        admin_to = os.environ.get("BHAGYA_EMAIL_FROM", "").strip()
        if admin_to and entry:
            label = {"problem": "🐛 Problem", "feature": "✨ Feature request",
                     "other": "💬 Feedback"}.get(entry["type"], "Feedback")
            html = (
                f"<p><strong>{label}</strong> via {entry['page'] or 'unknown page'}</p>"
                f"<blockquote style='border-left:3px solid #6b21a8;padding:8px 12px;"
                f"margin:8px 0;background:#faf7f2;'>{entry['message']}</blockquote>"
                f"<p style='font-size:12px;color:#78716c;'>"
                f"From: {entry['email'] or '(anonymous)'}<br>"
                f"At: {entry['ts']}<br>"
                f"ID: <code>{entry['id']}</code></p>"
            )
            email_sender.send(admin_to, subject=f"[Shubh Bhagya feedback] {label}", html=html)
    except Exception as err:
        import logging
        logging.getLogger(__name__).warning("admin feedback notification failed: %s", err)

    return JSONResponse({"ok": True})


@app.get("/learn/", response_class=HTMLResponse)
async def learn_index(request: Request) -> HTMLResponse:
    """Hub page listing every learning article. Public, indexable, no auth."""
    return templates.TemplateResponse(
        request,
        "learn_index.html",
        {
            "lang": _lang(request),
            "articles": learn_registry.all_articles(),
        },
    )


@app.get("/learn/{slug}/", response_class=HTMLResponse)
async def learn_article(request: Request, slug: str) -> HTMLResponse:
    """Render one learning article. Each article is a hand-written Jinja
    template at templates/learn/<slug>.html that extends learn_article_base.
    Registry holds metadata (title, summary, FAQs, related links)."""
    article = learn_registry.get_article(slug)
    if article is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        f"learn/{slug}.html",
        {
            "lang": _lang(request),
            "article": article,
            "related": learn_registry.related_articles(slug),
        },
    )


@app.get("/admin/feedback", response_class=HTMLResponse,
         dependencies=[Depends(require_admin)])
async def admin_feedback(request: Request) -> HTMLResponse:
    """List every feedback entry, most recent first. Auth-gated like /admin/usage."""
    return templates.TemplateResponse(
        request, "admin_feedback.html",
        {"lang": _lang(request), "entries": feedback.list_all()},
    )


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_dashboard(request: Request, days: int = 1) -> HTMLResponse:
    """Admin landing dashboard — cross-cutting metrics from every subsystem.

    Sections:
      - Headline KPIs: Kundli / Ask / Matching / Errors counts for the window
      - LLM usage: token spend, cache hit rate, per-route/model/provider (formerly its own page)
      - Community: signed-in users, Rashifal subscribers, feedback count
      - Recent activity mini-feed with links to the per-type deep-dive pages

    Deep-dive pages: /admin/activity, /admin/subscribers, /admin/feedback.

    Protected by HTTP Basic Auth (username 'admin', password from
    ADMIN_PASSWORD env var). Browser shows the standard login prompt.
    """
    from astro_ai import llm_stats, feedback
    # Persistent (GCS) usage summary — survives Cloud Run cold starts and
    # deploys, unlike the SQLite version which lives in /tmp and resets on
    # every push. We supplement with cache_entries from SQLite (that count
    # IS instance-scoped but doesn't matter across restarts).
    summary = llm_stats.usage_summary(days=days)
    try:
        sqlite_summary = cache.usage_summary(days=days)
        summary["cache_entries"] = sqlite_summary.get("cache_entries", 0)
    except Exception:  # noqa: BLE001
        pass
    # Community counts. Users = Google sign-in persisted; subscribers = daily
    # Rashifal email opt-in; feedback = feedback widget submissions.
    user_count = users.count()
    subscriber_count = subscribers.count()
    feedback_count = feedback.count()
    # Per-model / per-route LLM call breakdown for the same window.
    llm_stats_summary = llm_stats.range_summary(days=days)
    # Event counts per type (form_kundli / form_ask / form_matching / error) —
    # backs the four headline KPI cards.
    event_totals = events.counts_by_type(days=days)
    # Recent-activity mini-feed: last N events across all types, newest first.
    recent_events = events.recent(days=days, limit=10)
    recent_errors = events.recent(types=["error"], days=days, limit=3)
    return templates.TemplateResponse(
        request, "admin_dashboard.html",
        {
            "lang": _lang(request),
            "summary": summary,
            "days": days,
            "user_count": user_count,
            "subscriber_count": subscriber_count,
            "feedback_count": feedback_count,
            "llm_stats": llm_stats_summary,
            "event_totals": event_totals,
            "recent_events": recent_events,
            "recent_errors": recent_errors,
        },
    )


@app.get("/admin/usage", include_in_schema=False)
async def admin_usage_redirect(days: int = 1) -> RedirectResponse:
    """Old URL — /admin/usage merged into the main /admin dashboard on
    2026-08-06. Permanent redirect so bookmarks and any linked-to URLs
    continue to work."""
    return RedirectResponse(f"/admin?days={days}", status_code=301)


@app.get("/admin/activity", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_activity(request: Request, days: int = 7, limit: int = 200) -> HTMLResponse:
    """Recent form submissions, Ask questions, and errors — auth-gated.

    Query params: days=1|7|30, limit=100|200|500.
    """
    kundlis = events.recent(types=["form_kundli"], days=days, limit=limit)
    matches = events.recent(types=["form_matching"], days=days, limit=limit)
    asks = events.recent(types=["form_ask"], days=days, limit=limit)
    errs = events.recent(types=["error"], days=days, limit=limit)
    totals = events.counts_by_type(days=days)
    return templates.TemplateResponse(
        request, "admin_activity.html",
        {
            "lang": _lang(request),
            "days": days, "limit": limit,
            "kundlis": kundlis, "matches": matches, "asks": asks, "errors": errs,
            "totals": totals,
        },
    )


@app.get("/admin/insights", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_insights(request: Request, days: int = 30,
                         refresh: int = 0) -> HTMLResponse:
    """Audience-shape aggregates — who's actually using the site.

    Runs `profiling.audience_summary(days)`, which reads from the existing
    GCS events log (no new collection). Cached per-day at the profiling
    layer, so repeated loads within an hour are cheap. `?refresh=1` forces
    a re-aggregate — useful right after new features change the substrate.

    See GitHub issue #140 for the dimension list and roadmap (Phase 1
    covers cheap dims; rashi + intent-NLP land in later phases).
    """
    from astro_ai import profiling
    summary = profiling.audience_summary(days=days, force_refresh=bool(refresh))
    return templates.TemplateResponse(
        request, "admin_insights.html",
        {"lang": _lang(request), "days": days, "summary": summary},
    )


@app.get("/admin/subscribers", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_subscribers(request: Request) -> HTMLResponse:
    """Full Rashifal-email subscriber list — auth-gated."""
    subs = subscribers.list_subscribers()
    # Newest first — subscribers.list_subscribers order is insertion order.
    subs_sorted = sorted(subs, key=lambda s: s.get("subscribed_at", ""), reverse=True)
    return templates.TemplateResponse(
        request, "admin_subscribers.html",
        {
            "lang": _lang(request),
            "subscribers": subs_sorted,
            "total": len(subs_sorted),
        },
    )


@app.get("/dasha", response_class=HTMLResponse)
async def dasha(request: Request) -> HTMLResponse:
    """Vimshottari Dasha timeline for the active saved chart.

    Same landing/result split as /kundli (SEO audit #123). When no chart
    cookie is set, render the /dasha explainer + birth-form so Googlebot
    has an indexable page. The old redirect-to-home meant /dasha had zero
    SEO presence.
    """
    saved = load_collection(request).active
    if saved is None:
        return templates.TemplateResponse(
            request, "dasha_landing.html",
            {"lang": _lang(request)},
        )
    saved_details = saved.to_birth_details()
    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    return templates.TemplateResponse(
        request,
        "dasha.html",
        {
            "details": saved_details,
            "natal": natal,
            "dasha": compute_dasha_state(natal),
            "lang": _lang(request),
        },
    )


@app.get("/dasha/deep-dive", response_class=HTMLResponse)
async def dasha_deep_dive(request: Request) -> HTMLResponse:
    """Long-form personalised reading of the current Mahadasha + Antardasha.

    Goes deeper than the timeline at /dasha: looks at where the period
    lords actually sit in this seeker's chart, explains the interaction,
    forecasts the next Antardasha, and lists remedies tied to the current
    Antardasha lord. Cached by (chart fingerprint, antardasha id) so we
    only burn an LLM call once per active Antardasha — periods last weeks
    to months so this is heavily reused.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=dasha", status_code=303)
    saved_details = saved.to_birth_details()
    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    dasha = compute_dasha_state(natal)
    lang = _lang(request)

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured",
             "message": "Add OPENAI_API_KEY (or set up BHAGYA_LLM_PROVIDERS) before generating readings."},
            status_code=503,
        )

    # Cache key: chart fingerprint + antardasha start (changes when antardasha
    # rolls over) + prompt fingerprint (changes when we tune the prompt) + lang.
    chart_fp = cache.fingerprint_chart(
        saved_details.birth_date, saved_details.birth_time, saved_details.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(DASHA_DEEP_DIVE_PROMPT_PATH)
    antar_id = f"{dasha.antardasha.lord}-{dasha.antardasha.start.isoformat()}"
    cache_key = f"dasha_deep_dive:{chart_fp}:{antar_id}:{prompt_fp}:{lang}"

    try:
        text = _cached(
            cache_key=cache_key,
            route="dasha_deep_dive",
            lang=lang,
            ttl_days=None,  # never expire on its own — antar_id in key handles invalidation
            call_fn=lambda: generate_dasha_deep_dive(
                chart=natal, dasha=dasha,
                prompt_path=DASHA_DEEP_DIVE_PROMPT_PATH, lang=lang,
            ),
        )
    except Exception as err:
        log.exception("dasha deep dive LLM generation failed")
        _fire_error_alert(request, err, "dasha")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": _title, "message": _msg},
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    sections = parse_sectioned_reading(text)
    return templates.TemplateResponse(
        request,
        "dasha_deep_dive.html",
        {
            "details": saved_details,
            "natal": natal,
            "dasha": dasha,
            "sections": sections,
            "lang": lang,
        },
    )


@app.get("/ask", response_class=HTMLResponse)
async def ask_form(request: Request, q: str | None = None,
                   c: str | None = None, ctx: str | None = None) -> HTMLResponse:
    """Free-form Q&A about the seeker's chart.

    GET shows the question form. If `q` and `c` are present (after a POST
    redirect or cache-hit re-visit), the answer is rendered alongside the
    form so the user can ask follow-ups.

    `ctx` selects the context type — "chart" (default) or "numerology".
    Preserved as a hidden form field so "Ask another" from within a
    numerology-context session stays in numerology-context.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
    context = ctx if ctx in ("chart", "numerology", "matching") else "chart"
    answer = None
    if q:
        # Render a previously-asked question by re-running the cached lookup.
        # POST handler stores the (question, category) and we look it up.
        answer = _ask_lookup(saved, q, c or "general", lang, context=context)
    return templates.TemplateResponse(
        request, "ask.html",
        {
            "lang": lang,
            "active_chart": saved,
            "current_question": q or "",
            "current_category": c or "general",
            "current_context": context,
            "answer": answer,
            "remaining_today": _ask_quota_remaining(request),
        },
    )


_ASK_CATEGORIES = {"general", "career", "marriage", "money", "health",
                   "spiritual", "travel", "relationships"}


def _ask_cache_key(saved, question: str, category: str, lang: str,
                    context: str = "chart") -> str:
    """Stable cache key for an (chart, question, category, context) tuple.

    `context` (chart|numerology) is baked in so the same question asked
    with a different context source doesn't collide — a numerology-
    context answer references the numbers, a chart-context answer
    doesn't; they are legitimately different responses.
    """
    chart_fp = cache.fingerprint_chart(
        saved.birth_date, saved.birth_time, saved.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(ASK_PROMPT_PATH)
    # Python's hash() is randomised per-process; use a stable hash so the
    # cache key survives container restarts.
    import hashlib
    q_fp = hashlib.sha1(question.strip().encode("utf-8")).hexdigest()[:16]
    base = f"ask:{chart_fp}:{q_fp}:{category}:{prompt_fp}:{lang}"
    return base if context == "chart" else f"{base}:ctx={context}"


def _ask_lookup(saved, question: str, category: str, lang: str,
                context: str = "chart") -> str | None:
    """Look up an already-cached answer without burning a fresh LLM call."""
    return cache.get(_ask_cache_key(saved, question, category, lang, context=context))


@app.post("/ask")
async def ask_submit(
    request: Request,
    question: str = Form(""),
    category: str = Form("general"),
    context: str = Form("chart"),
) -> Response:
    """Submit a question. PRG-style: validate → generate → cache → 303 to GET.

    `context` is one of:
      - "chart" (default): natal chart + current dasha + flags only
      - "numerology": also pass the seeker's numerology reading, computed
        from the saved chart's own name+birth_date so no extra data
        collection is required. Enables numerology-flavoured follow-ups
        from /numerology to be answered against BOTH the numbers and
        the chart.
      - "matching": also pass the "other partner" chart from the user's
        most recent /matching submission (stored in the session cookie).
        Enables follow-ups like "is this a good career-alignment match?"
        that need BOTH charts. If the seeker's saved chart matches one
        of the two matching parties, the OTHER party is passed; else
        the groom chart is passed as the partner by default.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
    if context not in ("chart", "numerology", "matching"):
        context = "chart"
    question = (question or "").strip()
    if not question or len(question) < 5:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang,
                "active_chart": saved,
                "current_question": question,
                "current_category": category,
                "answer": None,
                "error": "Please write a question of at least a few words.",
                "remaining_today": _ask_quota_remaining(request),
            },
            status_code=400,
        )
    if len(question) > 600:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang, "active_chart": saved,
                "current_question": question[:600], "current_category": category,
                "answer": None,
                "error": "Question is too long (max 600 characters).",
                "remaining_today": _ask_quota_remaining(request),
            },
            status_code=400,
        )
    if category not in _ASK_CATEGORIES:
        category = "general"
    if _ask_quota_remaining(request) <= 0:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang, "active_chart": saved,
                "current_question": question, "current_category": category,
                "answer": None,
                "error": "You've used today's question quota. Come back tomorrow.",
                "remaining_today": 0,
            },
            status_code=429,
        )

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured",
             "message": "Add OPENAI_API_KEY (or set BHAGYA_LLM_PROVIDERS) before asking."},
            status_code=503,
        )

    # Cache key includes question fingerprint so re-asking the same question
    # serves instantly from cache. Counts against quota only on first ask.
    try:
        chart = compute_chart(saved.birth_date, saved.birth_time, saved.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    dasha = compute_dasha_state(chart)
    flags = compute_vedic_flags(chart)

    # Numerology context: compute the reading from the saved chart's own
    # name + birth_date so users asking follow-ups from /numerology get
    # answers that reference BOTH their numbers and their chart. No
    # extra data collection needed. birth_date on the saved record is
    # already a str (session.ChartRecord). Silently skipped if reading
    # fails — we still answer chart-only rather than error the user out.
    numerology_reading = None
    if context == "numerology":
        try:
            from astro_ai.numerology import compute as _num_compute
            numerology_reading = _num_compute(
                saved.name or "Seeker",
                saved.birth_date,
                system="chaldean",
            )
        except Exception:
            log.debug("numerology context load failed for /ask", exc_info=True)

    # Matching context: recover the partner chart from the last-matching
    # cookie set by POST /matching. If the seeker's saved chart matches
    # one of the two matching parties (by name + DOB), the OTHER party
    # is treated as the partner; else default to the groom.
    partner_chart = None
    partner_label = "partner"
    if context == "matching":
        last = load_last_matching(request)
        if last is None:
            # No recent matching to draw from; downgrade to chart-only.
            context = "chart"
        else:
            def _same(saved_c, name: str, dob: str) -> bool:
                return (saved_c.birth_date == dob
                        and (saved_c.name or "").strip().lower() == (name or "").strip().lower())
            seeker_is_groom = _same(saved, last.groom_name, last.groom_birth_date)
            seeker_is_bride = _same(saved, last.bride_name, last.bride_birth_date)
            if seeker_is_groom or not seeker_is_bride:
                # Seeker identifies with groom (or default): partner = bride
                p_name = last.bride_name or "Bride"
                p_dob, p_time, p_place = (last.bride_birth_date,
                                          last.bride_birth_time,
                                          last.bride_birth_place)
                partner_label = "partner (bride from your Kundli match)"
            else:
                # Seeker identifies with bride: partner = groom
                p_name = last.groom_name or "Groom"
                p_dob, p_time, p_place = (last.groom_birth_date,
                                          last.groom_birth_time,
                                          last.groom_birth_place)
                partner_label = "partner (groom from your Kundli match)"
            try:
                partner_chart = compute_chart(p_dob, p_time, p_place)
            except Exception:
                log.debug("partner chart compute failed for /ask matching context", exc_info=True)
                partner_chart = None
                context = "chart"

    # Cache key includes context so the same question asked from
    # /numerology (with numerology context) does not collide with the
    # same question asked from /kundli (chart-only).
    cache_key = _ask_cache_key(saved, question, category, lang, context=context)
    was_cached = cache.get(cache_key) is not None
    try:
        answer_text = _cached(
            cache_key=cache_key,
            route="ask",
            lang=lang,
            ttl_days=None,
            call_fn=lambda: generate_ask_answer(
                chart=chart, dasha=dasha, flags=flags,
                question=question, category=category,
                prompt_path=ASK_PROMPT_PATH, lang=lang,
                numerology_reading=numerology_reading,
                partner_chart=partner_chart,
                partner_label=partner_label,
            ),
        )
    except Exception as err:
        log.exception("ask LLM generation failed")
        _fire_error_alert(request, err, "ask")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": _title, "message": _msg},
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    # Save the Ask answer to the signed-in user's reading history so they can
    # revisit past questions from /account. Best-effort — never fails the
    # redirect. Only saves fresh generations (not cache hits) to avoid dupes.
    if not was_cached:
        _signed_in = load_user(request)
        if _signed_in and _signed_in.sub and answer_text:
            try:
                users.save_reading(
                    sub=_signed_in.sub,
                    kind="ask",
                    chart_id=saved.id,
                    title=question[:80] + ("…" if len(question) > 80 else ""),
                    body=answer_text,
                    meta={"question": question, "category": category},
                )
            except Exception:  # noqa: BLE001 — history is best-effort
                log.warning("save_reading(ask) failed for %s", _signed_in.sub)

    # Notify owner ONLY on fresh generation (cache-hit re-asks would spam
    # Telegram). But RECORD the event either way — we want /admin/activity
    # to show every question the user actually asked, including re-asks
    # that were served from cache. The `cache_hit` flag distinguishes them.
    _u_ask = load_user(request)
    if not was_cached:
        notify.ask_submitted(
            question=question, category=category, lang=lang,
            user_email=(_u_ask.email if _u_ask else ""),
            model=llm_providers.last_used_model(),
        )
    events.record(
        type="form_ask",
        email=(_u_ask.email if _u_ask else ""),
        data={
            "question": question, "category": category, "lang": lang,
            "model": llm_providers.last_used_model(),
            # Answer body persisted (truncated to 4000 chars) so
            # /admin/activity can spot-check Q&A quality across all
            # Cloud Run instances — SQLite cache is per-instance +
            # ephemeral, but events go to GCS. Truncation guards
            # against a single runaway answer bloating the daily
            # events blob; ~4KB × 5000 events/day = ~20MB max.
            "answer": (answer_text or "")[:4000],
            "context": context,
            "cache_hit": was_cached,
        },
    )

    # Redirect with the question + category (+ context) in the URL so
    # refresh doesn't re-submit, the user can bookmark / share the URL,
    # back/forward work naturally, and a follow-up "Ask another" from
    # the same context stays in the same context. Only bump the quota
    # on a fresh generation.
    from urllib.parse import urlencode
    _redirect_params = {"q": question, "c": category}
    if context != "chart":
        _redirect_params["ctx"] = context
    response = RedirectResponse(
        f"/ask?{urlencode(_redirect_params)}", status_code=303
    )
    if not was_cached:
        _ask_quota_bump(request, response)
    return response


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
