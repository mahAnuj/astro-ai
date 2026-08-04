"""FastAPI app — form, natal reading, today's transits, cookie-persisted seeker."""

from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
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


# Module-level logger used by the LLM-error handlers throughout this file
# (log.exception "…LLM generation failed" — one such call per LLM route).
# Before this existed, every one of those error paths crashed with
# NameError, converting a graceful "LLM temporarily unavailable" page into
# a bare 500. Any new error-path code in this module should use this
# logger, not an ad-hoc import.
import logging
log = logging.getLogger(__name__)


def _fire_error_alert(request, err: Exception, source: str) -> None:
    """Send a Telegram alert with the low-level error details. Best-effort.

    Called from every LLM error path so we get pinged the moment a user
    hits a provider outage / rate limit / crash. Never raises — Telegram
    alerts must not add failure modes to already-failed request paths.
    """
    try:
        import traceback as _tb
        _u = load_user(request) if request is not None else None
        _user_email = _u.email if _u else ""
        _path = request.url.path if request is not None else ""
        _method = request.method if request is not None else ""
        _tb_str = _tb.format_exc()
        notify.error_seen(
            source=source,
            error_type=type(err).__name__,
            error_message=str(err) or repr(err),
            path=_path, method=_method,
            user_email=_user_email,
            traceback_str=_tb_str,
        )
        # Persistent record so /admin/activity can show error history.
        events.record(
            type="error",
            email=_user_email,
            data={
                "source": source,
                "error_type": type(err).__name__,
                "error_message": (str(err) or repr(err))[:500],
                "path": _path, "method": _method,
                # Keep last ~1500 chars of traceback for post-hoc diagnosis.
                "traceback": _tb_str[-1500:] if _tb_str else "",
            },
        )
    except Exception:  # noqa: BLE001 — alert must never mask original error
        log.debug("notify.error_seen fire failed (swallowed)", exc_info=True)


def _llm_error_friendly(err: Exception) -> tuple[str, str]:
    """Translate an internal LLM error into a user-friendly (title, message).

    Rate-limit / high-demand errors get a distinct, retry-encouraging copy.
    Any other error gets a generic apology — the raw exception class name and
    message are NEVER exposed to the user (they leak internals and confuse
    non-technical seekers). Full details are logged server-side for debugging.
    """
    if isinstance(err, AllProvidersExhausted):
        return (
            "High demand right now",
            "🙏 Many seekers are asking questions at the same time. "
            "Please try again in a couple of minutes — your input is safe "
            "to re-submit exactly as you typed it.",
        )
    return (
        "Something went wrong",
        "We couldn't complete the reading this time. Please try again in "
        "a moment — your input is safe to re-submit exactly as you typed it.",
    )
from astro_ai import cache, daily_cache, email_sender, events, feedback, festivals, learn_registry, notify, shloks, snapshots, storage, subscribers, trivia, users
import time as _time
from astro_ai.session import (
    SUPPORTED_LANGS,
    ChartCollection,
    SessionUser,
    clear_collection,
    clear_user,
    load_ask_usage,
    load_collection,
    load_lang,
    load_user,
    save_ask_usage,
    save_collection,
    save_lang,
    save_session_atomic,
    save_user,
)


def _lang(request: Request) -> str:
    """Backwards-compat alias — read lang from the combined __session cookie."""
    return load_lang(request)


def _save_collection_synced(response: Response, collection: ChartCollection, request: Request) -> None:
    """Save a ChartCollection to the cookie AND (if signed in) to users.json.

    Wrapper around session.save_collection that ensures signed-in users'
    chart state stays in sync across their devices. Anonymous users get
    exactly the previous behaviour (cookie-only). Silent failure on
    users.json write — cookie remains the source of truth for THIS
    session either way.
    """
    save_collection(response, collection, request)
    user = load_user(request)
    if user is not None:
        try:
            users.save_charts(user.sub, collection)
        except Exception as err:
            import logging
            logging.getLogger(__name__).warning(
                "chart sync to users.json failed for %s: %s", user.email, err
            )


_basic_auth = HTTPBasic(realm="Bhagya admin")
_ADMIN_DEV_FALLBACK = "bhagya-dev-only-CHANGE-ME"


def require_admin(creds: HTTPBasicCredentials = Depends(_basic_auth)) -> None:
    """HTTP Basic Auth gate for admin routes.

    Username must be 'admin'; password comes from the ADMIN_PASSWORD env var.
    If unset, falls back to a clearly-flagged dev placeholder so local
    development still works — but the var MUST be set before any deploy.
    `secrets.compare_digest` is used on both sides to dodge timing attacks.
    """
    expected_password = os.environ.get("ADMIN_PASSWORD", _ADMIN_DEV_FALLBACK)
    ok_user = secrets.compare_digest(creds.username, "admin")
    ok_pass = secrets.compare_digest(creds.password, expected_password)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": 'Basic realm="Bhagya admin"'},
        )


# Hindi month names for _pretty_date() — English strftime gives us "July"
# etc. natively but there's no locale-friendly way to get "जुलाई" without
# pulling in a full ICU dependency, so we spell it out. Month order is
# Jan=1 .. Dec=12; index 0 is a placeholder to keep month numbers 1-indexed.
_HINDI_MONTHS: tuple[str, ...] = (
    "", "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
    "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
)


def _pretty_date(iso_date: str, lang: str = "en") -> str:
    """Format an ISO date as human-friendly text for user-facing titles.

    ISO dates ('2026-07-31') in page titles kill click-through — external
    SEO audit flagged this specifically. Use this helper anywhere a date
    lands in a `<title>`, `<h1>`, or visible page chrome. Keep the raw ISO
    form for machine-readable slots (`<time datetime="...">`, sitemap
    lastmod, JSON-LD datePublished).

    English → "31 July 2026" (drops weekday — daily-content pages don't need
    the extra length; the current-day framing is already implied).
    Hindi   → "31 जुलाई 2026" (Devanagari digits look wrong here — most Indian
    UIs use Arabic numerals even in Hindi, matching AstroSage / mPanchang).
    """
    from datetime import date as _date
    try:
        d = _date.fromisoformat(iso_date)
    except (TypeError, ValueError):
        return iso_date  # last-resort — bad input should not break rendering
    if lang == "hi":
        return f"{d.day} {_HINDI_MONTHS[d.month]} {d.year}"
    return d.strftime("%-d %B %Y")


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


def _cached(
    cache_key: str,
    *,
    route: str,
    lang: str,
    ttl_days: int | None,
    call_fn,
) -> str:
    """Cache-wrap an LLM call. Logs every attempt (hit or miss) for /admin/usage.

    `call_fn` is a zero-arg callable that returns the LLM text. We do the
    cache-check and the per-route logging here so every reading benefits from
    the same observability surface without duplicating boilerplate.

    Self-healing: if the cached text fails the same quality check that the
    provider chain uses (e.g. missing '## Heading' markers), we treat it as
    a miss and re-generate — silently cleaning up any garbage that snuck
    into the cache before quality-gating was live.
    """
    hit = cache.get(cache_key)
    if hit is not None:
        ok, reason = llm_providers.passes_quality(hit, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            return hit
        log.warning(
            "cache: dropping bad entry for route=%s (%s) — will regenerate",
            route, reason,
        )
        # Fall through to regeneration; the fresh call will overwrite.
    started = _time.time()
    text = call_fn()
    latency_ms = int((_time.time() - started) * 1000)
    in_tok = cache.estimate_tokens(text) * 2  # input ≈ 2x output for our prompts (rough)
    out_tok = cache.estimate_tokens(text)
    cache.put(cache_key, text, route=route, ttl_days=ttl_days,
              input_tokens=in_tok, output_tokens=out_tok)
    cache.log_call(route, lang, cache_hit=False,
                   input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency_ms)
    return text

# override=True so .env edits actually take effect when uvicorn reloads —
# otherwise the first-loaded values stick for the lifetime of the process
# and editing .env feels silently broken.
# Load order: .env (committed defaults) → .env.local (git-ignored local
# overrides, e.g. dev secrets that shouldn't live in .env). .env.local wins
# on any key it defines.
load_dotenv(override=True)
load_dotenv(".env.local", override=True)

# Project layout: src/astro_ai/main.py → templates and production prompts live
# alongside the code. The sibling `evals/` folder is the prompt-evaluation
# sub-project (separate concern, not a runtime dependency).
HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
PROMPTS_DIR = HERE / "prompts"
STATIC_DIR = HERE / "static"
PROMPT_PATH = PROMPTS_DIR / "natal.txt"
DAILY_PROMPT_PATH = PROMPTS_DIR / "daily.txt"
MONTHLY_PROMPT_PATH = PROMPTS_DIR / "monthly.txt"
YEARLY_PROMPT_PATH = PROMPTS_DIR / "yearly.txt"
MATCHING_PROMPT_PATH = PROMPTS_DIR / "matching.txt"
RASHIFAL_PROMPT_PATH = PROMPTS_DIR / "rashifal_single.txt"
DASHA_DEEP_DIVE_PROMPT_PATH = PROMPTS_DIR / "dasha_deep_dive.txt"
ASK_PROMPT_PATH = PROMPTS_DIR / "ask.txt"

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


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Safety net — fires a Telegram alert for any truly unhandled 500 and
    returns a bare Internal Server Error so the request finishes cleanly.

    This ONLY fires when nothing else caught the exception (e.g. the pre-log-
    NameError incident on 2026-07-27). Handled LLM errors don't reach here
    because they return template responses inline.
    """
    log.exception("unhandled exception in request handler")
    _fire_error_alert(request, exc, "unhandled")
    return Response("Internal Server Error", status_code=500)


# Serve the PWA manifest, service worker, and icons from /static/.
# StaticFiles mounts must precede route definitions for the most specific
# path to win, but FastAPI's router handles this correctly either way.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Expose i18n to every template as `t(key, **kwargs)`. Templates pass the
# current `lang` (also injected per-request) into the call.
templates.env.globals["t"] = _i18n_translate
# current_year used by nav labels like "Horoscope 2026" — auto-updates yearly.
templates.env.globals["current_year"] = lambda: date.today().year


# slug → title lookup for the linkify filter (renders anchors with the
# article's proper title instead of the raw slug URL).
from .learn_registry import ARTICLES as _ARTICLES
_ARTICLE_TITLE_BY_SLUG: dict[str, str] = {
    a.slug: (a.seo_title.strip() or a.title.strip()) for a in _ARTICLES
}


def _linkify_learn(text: str) -> str:
    """Convert plain "/learn/<slug>/" occurrences in LLM output into <a href> tags.

    The natal / matching / ask LLM prompts instruct the model to emit cross-links
    as bare slug paths (e.g. "For more, see our Vimshottari Dasha guide →
    /learn/vimshottari-dasha-explained/"). This filter turns those into real
    clickable anchors when the reading is rendered.

    Anchor label is the article's title (via slug lookup) — much nicer to read
    than the raw URL. Unknown slugs fall back to the URL as label so nothing
    silently disappears.

    Escapes HTML first (defence-in-depth against LLM injecting tags), then
    substitutes the /learn/<slug>/ pattern with an anchor. Returns Markup so
    Jinja does not re-escape the anchor.
    """
    import html as _html
    import re as _re
    from markupsafe import Markup

    escaped = _html.escape(text or "")
    # Only match well-formed slugs (lowercase letters, digits, hyphens).
    pattern = _re.compile(r"/learn/([a-z0-9][a-z0-9-]*[a-z0-9])/")

    def _replace(match):
        slug = match.group(1)
        title = _ARTICLE_TITLE_BY_SLUG.get(slug, f"/learn/{slug}/")
        return (
            f'<a href="/learn/{slug}/" '
            f'class="text-astro-700 hover:text-astro-800 underline underline-offset-2">'
            f'{_html.escape(title)}</a>'
        )

    return Markup(pattern.sub(_replace, escaped))


templates.env.filters["linkify_learn"] = _linkify_learn


def _site_url() -> str:
    """Canonical site URL for SEO meta + email links.

    Returned by the Jinja global `site_url` and used by sitemap.xml etc.
    Defaults to the production custom domain; override per-environment with
    BHAGYA_SITE_URL when running on a staging/preview deploy.
    """
    return os.environ.get("BHAGYA_SITE_URL", "").rstrip("/") or "https://shubhagya.com"


# Expose site_url to every template so canonical/OG/JSON-LD tags can build
# absolute URLs without each handler passing it in.
templates.env.globals["site_url"] = _site_url()
# GA4 measurement ID — base.html conditionally loads gtag.js when set.
# Leave unset in local dev / preview so analytics don't pollute the prod
# property with junk events.
templates.env.globals["ga4_measurement_id"] = os.environ.get("GA4_MEASUREMENT_ID", "").strip()
# Microsoft Clarity project ID — for session recordings + heatmaps. Free,
# complements GA4. Loaded only when set (skip on dev / preview).
templates.env.globals["clarity_project_id"] = os.environ.get("CLARITY_PROJECT_ID", "").strip()
# Google Identity Services client ID — templates use this to render the
# Sign-In button. Safe to expose publicly (it's the OAuth client ID, not the
# secret). Empty in dev if unset; sign-in button hides itself in that case.
templates.env.globals["google_client_id"] = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
# Request-scoped current user helper — templates call {{ load_current_user(request) }}
# at the top of _nav.html / _account_menu.html to decide what to render.
# Fast: just deserialises the cookie.
templates.env.globals["load_current_user"] = load_user


def _is_subscribed(email: str | None) -> bool:
    """Template helper — does this email have an active Rashifal subscription?

    Used by the daily-Rashifal CTA on the homepage so signed-in subscribers
    see a "you're subscribed" state instead of being nudged to subscribe
    again. Empty/None email returns False.
    """
    if not email:
        return False
    return subscribers.find_by_email(email.strip().lower()) is not None


templates.env.globals["is_subscribed"] = _is_subscribed


def _user_age_bucket(request: Request) -> str:
    """Derive the seeker's age bucket from their saved chart's birthdate.

    Returns one of: 'under-18', '18-24', '25-34', '35-44', '45-54', '55+',
    or '' when there's no saved chart yet. Sent to GA4 as a user property
    so we can slice every event by age cohort — answers questions like
    "do 25-34 users subscribe to daily Rashifal more often than 45-54?".

    Privacy: we NEVER expose the raw birthdate to analytics — only the
    bucket. The chart cookie itself is HMAC-signed and HttpOnly, the bucket
    is computed server-side and the value sent is one of 6 broad ranges.
    """
    collection = load_collection(request)
    if not collection.active:
        return ""
    try:
        birth_year = int(collection.active.birth_date[:4])
        age = date.today().year - birth_year
    except (ValueError, TypeError):
        return ""
    if age < 18:  return "under-18"
    if age < 25:  return "18-24"
    if age < 35:  return "25-34"
    if age < 45:  return "35-44"
    if age < 55:  return "45-54"
    return "55+"


# Expose as a template function: {{ user_age_bucket(request) }} in any
# template (Jinja's TemplateResponse provides `request` to all templates).
templates.env.globals["user_age_bucket"] = _user_age_bucket


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap() -> Response:
    """XML sitemap for search engines.

    Lists every crawlable, publicly accessible page. Excluded: chart-specific
    pages that need a user-supplied chart (/today, /kundli, /monthly, /yearly,
    /dasha — Google won't reach them anyway without cookies), and /admin/usage
    (also blocked in robots.txt for defense-in-depth).

    The yearly horoscope path /yearly takes its title from the current year,
    so updates implicitly via the current_year template global.
    """
    base = _site_url()
    today = date.today().isoformat()
    # changefreq + priority are hints — Google mostly ignores them but other
    # search engines (Bing, Yandex) still use them as ranking signals.
    pages = [
        ("/",         "daily",   "1.0"),
        ("/rashifal", "daily",   "0.9"),
        ("/matching", "monthly", "0.7"),
        ("/learn/",   "weekly",  "0.8"),
        # Tools
        ("/muhurat",         "monthly", "0.7"),
        ("/manglik-check",   "monthly", "0.7"),
        ("/sade-sati-check", "monthly", "0.7"),
        ("/kaal-sarp-check", "monthly", "0.7"),
        ("/numerology",      "monthly", "0.7"),
        ("/numerology/compatibility", "monthly", "0.7"),
        ("/kundli",          "monthly", "0.8"),
        ("/dasha",           "monthly", "0.7"),
        ("/panchang",        "daily",   "0.8"),
        ("/about",           "monthly", "0.5"),
    ]
    # Muhurat per-event landing pages — evergreen SEO copy per event type.
    from astro_ai.muhurat import EVENT_LANDING
    for event_key, landing in EVENT_LANDING.items():
        pages.append((f"/muhurat/{landing['slug']}", "monthly", "0.7"))
    # Per-rashi Rashifal URLs — 12 daily-fresh pages Google can rank
    # independently for 'aries daily horoscope' etc.
    from astro_ai.llm import RASHI_CANONICAL_SLUGS as _RASHI_SLUGS_FOR_SITEMAP
    for _slug in _RASHI_SLUGS_FOR_SITEMAP:
        pages.append((f"/rashifal/{_slug}", "daily", "0.7"))
    # Rolling 90-day Panchang archive — 30 past + today + 59 future so
    # Google discovers 'panchang for {upcoming date}' queries + can still
    # serve retrospective 'what was tithi on {past date}' searches.
    # SEO audit #132 Phase 2.
    from datetime import timedelta as _td
    _today = date.today()
    for _offset in range(-30, 60):
        _d = _today + _td(days=_offset)
        pages.append((f"/panchang/{_d.isoformat()}", "daily", "0.5"))
    # Auto-include every learning article so Google can crawl them all from
    # one place. New articles dropped into learn_registry appear here
    # automatically — no sitemap maintenance.
    for a in learn_registry.all_articles():
        pages.append((f"/learn/{a.slug}/", "monthly", "0.7"))
    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, freq, prio in pages:
        body += "  <url>\n"
        body += f"    <loc>{base}{path}</loc>\n"
        body += f"    <lastmod>{today}</lastmod>\n"
        body += f"    <changefreq>{freq}</changefreq>\n"
        body += f"    <priority>{prio}</priority>\n"
        body += "  </url>\n"
    body += "</urlset>\n"
    return Response(content=body, media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots() -> Response:
    """Crawler directives.

    Allows everything except /admin/* (auth-gated; no point indexing). Points
    crawlers at the sitemap so they discover all canonical URLs without having
    to follow internal links.
    """
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        # Snapshot pages are user-shared, ephemeral (30-day TTL), and
        # contain PII (birth details). Not for indexing.
        "Disallow: /r/\n"
        f"\nSitemap: {_site_url()}/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain")


@app.get("/sw.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    """Serve the PWA service worker from the root path.

    Why not just /static/sw.js: a service worker's "scope" defaults to the
    path it was served from. Serving at /static/sw.js would limit caching
    to /static/* requests. Serving at /sw.js gives it scope `/`, so it can
    intercept and cache HTML pages too.

    Cache-Control: no-cache means the browser revalidates the SW file on
    every load — critical for being able to ship SW updates without users
    being stuck on a stale version forever.
    """
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


def _render_panchang(request: Request, target_date, city: str = "") -> HTMLResponse:
    """Shared Panchang renderer — powers both /panchang (today) and
    /panchang/{YYYY-MM-DD} (archive URLs — SEO audit #132 Phase 2).

    City resolution priority:
      1. ?city= query param (form-submitted or shared link)
      2. Saved active chart's birth_place if user has one
      3. Default 'Mumbai, India' (largest Indian-Vedic user base)

    Panchang is location-dependent (sunrise/sunset shifts change Rahu
    Kaal, Abhijit, Choghadiya). Compute via compute_panchang against a
    throwaway chart_for_loc; degrade gracefully to Mumbai if geocoding
    fails.

    `target_date` is a `datetime.date` — the day whose panchang we want.
    """
    from astro_ai.muhurat import _choghadiya_windows as _choghadiya
    from datetime import datetime as _datetime, timedelta as _timedelta
    from zoneinfo import ZoneInfo as _ZoneInfo
    resolved_city = (city or "").strip()
    error = False
    if not resolved_city:
        saved = load_collection(request).active
        resolved_city = (saved.birth_place if saved else "") or "Mumbai, India"
    # Anchor the compute at local noon on the target date so daily-shifting
    # signals (tithi, sunrise, choghadiya) fall on the intended day.
    def _target_moment(chart) -> _datetime:
        tz = _ZoneInfo(chart.birth_tz)
        return _datetime(target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=tz)
    try:
        chart_for_loc = compute_chart("2000-01-01", "12:00", resolved_city)
        p = compute_panchang(chart_for_loc, when=_target_moment(chart_for_loc))
    except Exception:
        error = True
        resolved_city = "Mumbai, India"
        try:
            chart_for_loc = compute_chart("2000-01-01", "12:00", resolved_city)
            p = compute_panchang(chart_for_loc, when=_target_moment(chart_for_loc))
        except Exception:
            p = None
            chart_for_loc = None
    choghadiya_windows = []
    moon_info = None
    if p and chart_for_loc:
        try:
            choghadiya_windows = _choghadiya(p.weekday, p.sunrise, p.sunset)
        except Exception:
            choghadiya_windows = []
        try:
            transit = compute_transit_snapshot(chart_for_loc, when=_target_moment(chart_for_loc))
            moon = next((pl for pl in transit.planets if pl.name == "Moon"), None)
            if moon:
                moon_info = {"rashi": moon.rashi, "nakshatra": moon.nakshatra}
        except Exception:
            moon_info = None
    lang = _lang(request)
    today_iso = date.today().isoformat()
    target_iso = target_date.isoformat()
    is_today = (target_iso == today_iso)
    # Prev / next day for navigation on archive pages (skip on today to
    # keep the today URL clean).
    from datetime import timedelta as _td
    prev_day = (target_date - _td(days=1)).isoformat()
    next_day = (target_date + _td(days=1)).isoformat()
    return templates.TemplateResponse(
        request, "panchang.html",
        {
            "p": p,
            "city": city or resolved_city,
            "city_display": resolved_city,
            "today_date": target_iso,       # the rendered day (used by <time> element)
            "today_pretty": _pretty_date(target_iso, lang),
            "is_today": is_today,
            "true_today_iso": today_iso,
            "prev_day": prev_day,
            "next_day": next_day,
            "choghadiya": choghadiya_windows,
            "moon_info": moon_info,
            "error": error,
            "lang": lang,
        },
    )


@app.get("/panchang", response_class=HTMLResponse)
async def panchang_page(request: Request, city: str = "") -> HTMLResponse:
    """Today's Panchang. Delegates to _render_panchang with today's date."""
    return _no_cdn_cache(_render_panchang(request, date.today(), city))


# In-process daily cache for the homepage Panchang strip. Keyed by
# (today_iso, city_lower). First homepage load for a given (date, city)
# pair runs the full compute chain (geocode + chart + panchang + transit
# snapshot ≈ 200ms cold on first hit); every subsequent same-day load
# on the same instance is a dict lookup.
_HOMEPAGE_PANCHANG_CACHE: dict[tuple, tuple] = {}


def _homepage_panchang_cached(city: str) -> tuple:
    """Return (panchang, moon_info, city_display) — cached per day/city.

    Uses date.today() implicitly so a new day naturally busts the cache.
    Cache is per-process (Cloud Run instances rebuild once each per day),
    which is fine — the compute is <200ms so cold-start latency is
    negligible.
    """
    today = date.today().isoformat()
    key = (today, (city or "").strip().lower())
    if key in _HOMEPAGE_PANCHANG_CACHE:
        return _HOMEPAGE_PANCHANG_CACHE[key]
    resolved_city = city or "Mumbai, India"
    try:
        chart_for_loc = compute_chart("2000-01-01", "12:00", resolved_city)
        p = compute_panchang(chart_for_loc)
        transit = compute_transit_snapshot(chart_for_loc)
        moon = next((pl for pl in transit.planets if pl.name == "Moon"), None)
        moon_info = {"rashi": moon.rashi, "nakshatra": moon.nakshatra} if moon else None
        display = resolved_city.split(",")[0]
        result = (p, moon_info, display)
    except Exception:
        result = (None, None, "")
    _HOMEPAGE_PANCHANG_CACHE[key] = result
    # Prevent unbounded growth if many cities are queried across a day.
    # After ~100 unique entries, drop everything older than today.
    if len(_HOMEPAGE_PANCHANG_CACHE) > 100:
        _HOMEPAGE_PANCHANG_CACHE.clear()
        _HOMEPAGE_PANCHANG_CACHE[key] = result
    return result


@app.get("/panchang/{date_str}", response_class=HTMLResponse)
async def panchang_archive(request: Request, date_str: str, city: str = "") -> HTMLResponse:
    """Panchang for a specific YYYY-MM-DD (SEO audit #132 Phase 2).

    Each historical / future day gets its own indexable URL. Rolling 90-day
    window sitemap ensures Google discovers a fresh 3-month archive. Older
    dates still work by direct link — they just don't sit in the sitemap.
    """
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Bad date", "message": f"'{date_str}' is not a valid YYYY-MM-DD date. Try /panchang for today."},
            status_code=404,
        )
    # Sanity-guard against absurd dates (Swiss Ephemeris breaks pre-1800 /
    # post-2400). Also blocks crawlers from generating 100M URLs.
    if target.year < 1900 or target.year > 2100:
        return _no_cdn_cache(templates.TemplateResponse(
            request, "error.html",
            {"title": "Out-of-range date", "message": "Panchang is available for dates between 1900 and 2100."},
            status_code=400,
        ))
    return _no_cdn_cache(_render_panchang(request, target, city))


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request) -> HTMLResponse:
    """About page — editorial principles, classical sources, team.

    E-E-A-T signal for Google (SEO audit #125): named entity behind the
    content, cited classical sources, contact-visible. Linked from the
    footer of every page via _nav.html.
    """
    return templates.TemplateResponse(
        request, "about.html", {"lang": _lang(request)},
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, needs_chart: str | None = None) -> HTMLResponse:
    """Form for new visitors, chart-list + form for returning seekers.

    `?needs_chart=<feature>` is set when other routes redirect here because
    no saved chart exists yet. We surface a brief banner naming the feature
    the seeker tried to reach, so the redirect isn't silent.
    """
    collection = load_collection(request)
    # Trust bar counts (SEO audit #134) — real numbers only. Never fake,
    # never round up. If we have zero of something, don't render that pill.
    try:
        _users_ct = users.count()
    except Exception:
        _users_ct = 0
    try:
        _subs_ct = subscribers.count()
    except Exception:
        _subs_ct = 0
    # Panchang strip for the homepage masthead (user's request — always
    # visible without click-away). Cached daily per city via
    # _homepage_panchang_cached — after first computation for a given
    # (date, city) pair the same instance serves subsequent homepage
    # loads with no LLM, no geocode, no swiss-ephemeris compute.
    _city_pref = "Mumbai, India"
    if collection.active and collection.active.birth_place:
        _city_pref = collection.active.birth_place
    _panchang_strip, _panchang_moon, _panchang_city = _homepage_panchang_cached(_city_pref)
    # Signed-in / has-chart flow: compute the user's natal Moon rashi so
    # the homepage can show 'Welcome back — your Rashifal is ready' with
    # their sign name and a direct link to /rashifal/{slug}. Cheap once
    # we know the birth details, and only fires when user has a chart.
    _user_moon_slug = None
    _user_moon_display = None
    if collection.active:
        try:
            _uc = collection.active
            _u_chart = compute_chart(_uc.birth_date, _uc.birth_time, _uc.birth_place)
            _u_moon = next((p for p in _u_chart.planets if p.name == "Moon"), None)
            if _u_moon:
                # Map rashi name (English or 'English (Sanskrit)') to canonical slug
                from astro_ai.llm import RASHI_SLUG_TO_INDEX, RASHI_CANONICAL_SLUGS
                _rashi_key = _u_moon.rashi.split(" ")[0].split("(")[0].strip().lower()
                _idx = RASHI_SLUG_TO_INDEX.get(_rashi_key)
                if _idx is not None:
                    _user_moon_slug = RASHI_CANONICAL_SLUGS[_idx]
                    _user_moon_display = _u_moon.rashi
        except Exception:
            pass
    return _no_cdn_cache(templates.TemplateResponse(
        request,
        "index.html",
        {
            "collection": collection,
            "saved": collection.active,
            "lang": _lang(request),
            "needs_chart_for": needs_chart,
            "trust_users": _users_ct,
            "trust_subscribers": _subs_ct,
            "panchang_strip": _panchang_strip,
            "panchang_moon": _panchang_moon,
            "panchang_city": _panchang_city.split(",")[0] if _panchang_city else "",
            "user_moon_slug": _user_moon_slug,
            "user_moon_display": _user_moon_display,
        },
    ))


@app.post("/reading")
async def reading(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> Response:
    """Form submission → save chart to cookie → 303 redirect to GET /kundli.

    Post-Redirect-Get pattern. The actual reading renders at GET /kundli,
    not here. Benefits:
      - Browser URL bar shows `/kundli` after submission (bookmarkable,
        matches the term users actually search for).
      - Refreshing the result page doesn't re-submit the form.
      - The lang picker's `next` field captures `/kundli` (a valid GET
        route) instead of `/reading` (POST only — which used to return
        a JSON 405 when the lang form tried to redirect back to it).
      - Back button works correctly.
    """
    details = BirthDetails(
        name=name.strip(),
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place.strip(),
    )
    # Validate chart math + geocoding up-front so the user sees birth-date
    # / city errors immediately instead of after a redirect dance.
    try:
        compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:reading_form")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    # Cap check before saving so we don't accept a chart we can't store.
    try:
        collection = load_collection(request).add(details)
    except ValueError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart limit reached", "message": str(err)},
            status_code=400,
        )
    response = RedirectResponse("/kundli", status_code=303)
    _save_collection_synced(response, collection, request)
    # notify.kundli_generated fires from _render_natal_for after the LLM
    # succeeds — that way the notification includes the model that actually
    # served the request. Firing here would fire on form submit, before the
    # LLM even runs (redirect target renders it).
    return response


@app.get("/reading")
async def reading_get() -> RedirectResponse:
    """Safety net for any stale GET to /reading (bookmarks, lang next=, etc.)."""
    return RedirectResponse("/kundli", status_code=303)


@app.get("/natal", include_in_schema=False)
async def natal_legacy_redirect() -> RedirectResponse:
    """Old URL — kept so existing bookmarks, SEO indexes, and any cached
    SW responses still work. Permanent redirect to the renamed canonical
    /kundli route."""
    return RedirectResponse("/kundli", status_code=301)


@app.get("/kundli", response_class=HTMLResponse)
async def kundli(request: Request) -> HTMLResponse:
    """Render the Janma Kundli reading for the currently active saved chart.

    When no chart is saved (typical for Googlebot + first-time visitors)
    we render an SEO landing page with the birth-details form inline instead
    of redirecting to home. Before this change (SEO audit #123) Googlebot
    was 303-redirected to '/' with a canonical pointing at '/', so /kundli
    had no indexable page of its own — competitors' /kundli URLs sat on
    2,000-word explainers while ours was invisible in search.
    """
    saved = load_collection(request).active
    if saved is None:
        return templates.TemplateResponse(
            request, "kundli_landing.html",
            {"lang": _lang(request)},
        )
    return await _render_natal_for(request, saved.to_birth_details(), chart_id=saved.id)


async def _render_natal_for(request: Request, details: BirthDetails,
                            chart_id: str = "") -> HTMLResponse:
    """Shared natal-reading renderer used by both GET /natal and POST /reading."""
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:natal_render")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
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
    flags = compute_vedic_flags(chart)
    life_chapters = compute_life_chapters(chart)
    dasha_state = compute_dasha_state(chart)
    lang = _lang(request)
    chart_fp = cache.fingerprint_chart(details.birth_date, details.birth_time, details.birth_place)
    prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
    cache_key = f"natal:{chart_fp}:{lang}:{prompt_fp}"
    try:
        reading_text = _cached(
            cache_key, route="natal", lang=lang, ttl_days=None,
            call_fn=lambda: generate_reading(
                details, chart=chart, flags=flags, life_chapters=life_chapters,
                prompt_path=PROMPT_PATH, lang=lang, dasha_state=dasha_state,
            ),
        )
    except Exception as err:
        log.exception("natal LLM generation failed")
        _fire_error_alert(request, err, "natal")
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
    sections = parse_sectioned_reading(reading_text)
    sade_sati = compute_sade_sati_details(chart)

    # Fire owner-notification NOW (after LLM succeeded) so we know the
    # exact model that served this Kundli. `last_used_model()` reads the
    # per-request contextvar set by providers.chat(). Empty string on
    # cache hits — nothing was called this request, so no model to report.
    _u_natal = load_user(request)
    notify.kundli_generated(
        name=details.name, birth_date=details.birth_date,
        birth_time=details.birth_time, birth_place=details.birth_place,
        lang=lang, user_email=(_u_natal.email if _u_natal else ""),
        model=llm_providers.last_used_model(),
    )
    events.record(
        type="form_kundli",
        email=(_u_natal.email if _u_natal else ""),
        data={
            "name": details.name, "birth_date": details.birth_date,
            "birth_time": details.birth_time, "birth_place": details.birth_place,
            "lang": lang, "model": llm_providers.last_used_model(),
        },
    )

    # Persist to signed-in user's reading history so they can revisit it
    # from any device. Best-effort — never fails the render.
    _signed_in = load_user(request)
    if _signed_in and _signed_in.sub:
        _title = f"{details.name}'s Kundli reading" if details.name else "Kundli reading"
        try:
            users.save_reading(
                sub=_signed_in.sub,
                kind="natal",
                chart_id=chart_id,
                title=_title,
                body=reading_text,
                meta={"birth_date": details.birth_date,
                      "birth_place": details.birth_place},
            )
        except Exception:  # noqa: BLE001 — history is best-effort
            log.warning("save_reading(natal) failed for %s", _signed_in.sub)

    # Pre-compute SS progress for the template (Jinja can't do date arithmetic cleanly).
    ss_progress = 0
    ss_elapsed_years = 0.0
    ss_remaining_years = 0.0
    if sade_sati.is_active and sade_sati.overall_start and sade_sati.overall_end:
        today = date.today()
        total_days = (sade_sati.overall_end - sade_sati.overall_start).days
        elapsed_days = max(0, min(total_days, (today - sade_sati.overall_start).days))
        ss_progress = int(elapsed_days / total_days * 100) if total_days else 0
        ss_elapsed_years = round(elapsed_days / 365.25, 1)
        ss_remaining_years = round((total_days - elapsed_days) / 365.25, 1)

    # Zodiac glyphs for the three summary chips (Lagna, Moon, Sun).
    moon_plt = next(p for p in chart.planets if p.name == "Moon")
    sun_plt  = next(p for p in chart.planets if p.name == "Sun")
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "details": details,
            "reading": reading_text,
            "sections": sections,
            "chart": chart,
            "flags": flags,
            "lang": lang,
            "lagna_glyph": symbol_for_rashi_label(chart.lagna_rashi),
            "moon_glyph":  symbol_for_rashi_label(moon_plt.rashi),
            "sun_glyph":   symbol_for_rashi_label(sun_plt.rashi),
            **_ask_cta_ctx(request, hint="about your chart"),
            # Bhagya Score — 0-100 gamified 'current chapter weather' reading.
            # Aggregates yogas, doshas, dashas, dignities into one number
            # with 'why' drivers for transparency. Feature spec in
            # chart.py compute_bhagya_score.
            "bhagya_score": compute_bhagya_score(chart),
            # Structured insight panels — see chart.py for shape.
            "manglik":  compute_manglik_details(chart),
            "navamsha_chart": compute_navamsha_chart(chart),
            "dashamsa_chart": compute_dashamsa_chart(chart),
            "yogas":    compute_yogas(chart),
            "sade_sati": sade_sati,
            "dasha":    compute_dasha_state(chart),
            # Pre-computed SS timeline values for the panel.
            "sade_sati_progress": ss_progress,
            "sade_sati_elapsed_years": ss_elapsed_years,
            "sade_sati_remaining_years": ss_remaining_years,
        },
    )


_EMAIL_KUNDLI_LAST_SENT: dict[str, float] = {}
_EMAIL_KUNDLI_MIN_INTERVAL_SEC = 60.0  # user can email themselves at most once per minute


@app.post("/email/kundli-reading")
async def email_kundli_reading(request: Request) -> JSONResponse:
    """Email the signed-in user their most-recent saved Kundli reading.

    Auth-gated (only signed-in users, sending to their own address) so
    there's no abuse vector — a caller can never target a third-party
    email. Rate-limited per-user in-memory to prevent hammering.
    """
    user = load_user(request)
    if not user or not user.sub or not user.email:
        return JSONResponse({"ok": False, "error": "sign_in_required"}, status_code=401)

    import time
    now = time.time()
    last = _EMAIL_KUNDLI_LAST_SENT.get(user.sub, 0.0)
    if now - last < _EMAIL_KUNDLI_MIN_INTERVAL_SEC:
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)

    readings = users.list_readings(user.sub, limit=5)
    kundli_reading = next((r for r in readings if r.kind == "natal"), None)
    if not kundli_reading:
        return JSONResponse({"ok": False, "error": "no_reading"}, status_code=404)

    lang = _lang(request)
    sections = parse_sectioned_reading(kundli_reading.body)

    saved_chart = load_collection(request).active
    chart_ctx = None
    birth_details_ctx = None
    if saved_chart is not None:
        details = saved_chart.to_birth_details()
        birth_details_ctx = {
            "name": details.name,
            "birth_date": details.birth_date,
            "birth_time": details.birth_time,
            "birth_place": details.birth_place,
        }
        try:
            chart_ctx = compute_chart(details.birth_date, details.birth_time, details.birth_place)
        except Exception:  # noqa: BLE001 — chart is best-effort for the email header
            chart_ctx = None

    ctx = {
        "lang": lang,
        "site_url": _site_url(),
        "user_name": user.name or "",
        "birth_details": birth_details_ctx,
        "chart": chart_ctx,
        "sections": sections,
        "unsubscribe_url": "",  # transactional — no subscription list to leave
    }
    html = templates.env.get_template("email/kundli_reading.html").render(**ctx)
    subject = (
        "आपकी कुंडली रीडिंग — Shubh Bhagya"
        if lang == "hi"
        else "Your Kundli Reading — Shubh Bhagya"
    )
    ok = email_sender.send(user.email, subject=subject, html=html)
    if ok:
        _EMAIL_KUNDLI_LAST_SENT[user.sub] = now
        return JSONResponse({"ok": True, "email": user.email})
    # Brevo failed — infra issue worth an alert (rate limit, key rotation,
    # network flake). Raise an exception object so _fire_error_alert has
    # something structured to report.
    _fire_error_alert(request, RuntimeError(f"Brevo send failed for {user.email}"), "email:kundli")
    return JSONResponse({"ok": False, "error": "send_failed"}, status_code=502)


# Per-user rate limit on snapshot creation — 5/day/user cap. Keeps casual
# WhatsApp-share behaviour cheap but prevents someone from generating a
# thousand snapshots and bloating the storage bucket.
_SNAPSHOT_CREATED_TODAY: dict[str, list[float]] = {}
_SNAPSHOT_DAILY_CAP = 5


def _snapshot_rate_ok(key: str) -> bool:
    """True if `key` (user sub or IP) hasn't exceeded today's snapshot cap."""
    import time as _t
    now = _t.time()
    day_ago = now - 86400
    hits = [t for t in _SNAPSHOT_CREATED_TODAY.get(key, []) if t > day_ago]
    if len(hits) >= _SNAPSHOT_DAILY_CAP:
        _SNAPSHOT_CREATED_TODAY[key] = hits
        return False
    hits.append(now)
    _SNAPSHOT_CREATED_TODAY[key] = hits
    return True


@app.post("/kundli/snapshot")
async def create_kundli_snapshot(request: Request) -> JSONResponse:
    """Create a public read-only snapshot of the caller's active Kundli reading.

    Returns a short URL the caller can paste into WhatsApp or any messenger;
    the URL renders a public, expiry-gated view of the exact reading. See
    snapshots.py for storage + expiry semantics (30-day TTL).

    Requires: an active chart in the session cookie AND (if signed in) a
    saved reading in the user's history; anonymous callers get the reading
    text from the fresh render path — no signed-in requirement for the
    happy path because most /kundli visitors are anonymous.
    """
    saved = load_collection(request).active
    if saved is None:
        return JSONResponse({"ok": False, "error": "no_chart"}, status_code=400)

    # Rate-limit by signed-in sub if available, else by client IP. Loose but
    # sufficient for MVP; a real abuse case would need per-IP + captcha.
    user = load_user(request)
    rate_key = user.sub if (user and user.sub) else (
        request.client.host if request.client else "unknown"
    )
    if not _snapshot_rate_ok(rate_key):
        return JSONResponse(
            {"ok": False, "error": "rate_limited",
             "message": "Too many share links created today. Try again tomorrow."},
            status_code=429,
        )

    # Get the reading text — prefer the persisted reading (signed-in users),
    # else regenerate from cache. Regeneration path is fast — cache hits
    # for the same chart+lang; only cold-cache visitors take the LLM hit.
    details = saved.to_birth_details()
    lang = _lang(request)

    reading_text = None
    if user and user.sub:
        readings = users.list_readings(user.sub, limit=10)
        for r in readings:
            if r.kind == "natal":
                reading_text = r.body
                break

    if reading_text is None:
        # Anonymous or no saved reading — synth from cache (or LLM if missed).
        try:
            chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
            flags = compute_vedic_flags(chart)
            life_chapters = compute_life_chapters(chart)
            dasha_state = compute_dasha_state(chart)
            chart_fp = cache.fingerprint_chart(details.birth_date, details.birth_time, details.birth_place)
            prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
            cache_key = f"natal:{chart_fp}:{lang}:{prompt_fp}"
            reading_text = _cached(
                cache_key, route="natal", lang=lang, ttl_days=None,
                call_fn=lambda: generate_reading(
                    details, chart=chart, flags=flags, life_chapters=life_chapters,
                    prompt_path=PROMPT_PATH, lang=lang, dasha_state=dasha_state,
                ),
            )
        except Exception as err:  # noqa: BLE001 — snapshot can't be built without a reading
            log.exception("snapshot: reading generation failed")
            _fire_error_alert(request, err, "snapshot:reading")
            return JSONResponse(
                {"ok": False, "error": "reading_unavailable"},
                status_code=502,
            )

    birth_details_dict = {
        "name": details.name or "",
        "birth_date": details.birth_date,
        "birth_time": details.birth_time,
        "birth_place": details.birth_place,
    }
    snap = snapshots.create(
        birth_details=birth_details_dict,
        reading_text=reading_text,
        lang=lang,
        created_by_sub=(user.sub if (user and user.sub) else ""),
    )
    if snap is None:
        # Storage unavailable (no GCS bucket configured OR write failed).
        # Fall back to a graceful error rather than a broken WhatsApp share.
        _fire_error_alert(
            request, RuntimeError("snapshots.create returned None (GCS + local fallback both failed)"),
            "snapshot:storage",
        )
        return JSONResponse(
            {"ok": False, "error": "storage_unavailable",
             "message": "Sharing is temporarily unavailable. Please try again later."},
            status_code=503,
        )
    return JSONResponse({
        "ok": True,
        "id": snap.id,
        "url": f"{_site_url()}/r/{snap.id}",
        "expires_at": snap.expires_at,
    })


@app.get("/r/{short_id}", response_class=HTMLResponse)
async def view_kundli_snapshot(request: Request, short_id: str) -> HTMLResponse:
    """Public read-only render of a shared Kundli snapshot.

    Renders the sender's reading (chart + LLM sections + flags) with a
    prominent 'Get your own free reading' CTA. No edit/regenerate paths;
    no session-state mutation. Expired snapshots 404.
    """
    snap = snapshots.load(short_id)
    if snap is None:
        return templates.TemplateResponse(
            request,
            "snapshot_expired.html",
            {"lang": _lang(request), "short_id": short_id},
            status_code=404,
        )

    # Re-compute chart deterministically from birth details — cheaper than
    # storing the full chart object in the snapshot, and always fresh with
    # any chart.py improvements shipped since the snapshot was created.
    try:
        chart = compute_chart(
            snap.birth_details.get("birth_date", ""),
            snap.birth_details.get("birth_time", ""),
            snap.birth_details.get("birth_place", ""),
        )
    except ChartError as err:
        _fire_error_alert(request, err, "snapshot:view")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't render shared reading", "message": str(err)},
            status_code=400,
        )

    sections = parse_sectioned_reading(snap.reading_text)
    sade_sati = compute_sade_sati_details(chart)
    moon_plt = next(p for p in chart.planets if p.name == "Moon")
    sun_plt = next(p for p in chart.planets if p.name == "Sun")

    ss_progress = 0
    ss_elapsed_years = 0.0
    ss_remaining_years = 0.0
    if sade_sati.is_active and sade_sati.overall_start and sade_sati.overall_end:
        today = date.today()
        total_days = (sade_sati.overall_end - sade_sati.overall_start).days
        elapsed_days = max(0, min(total_days, (today - sade_sati.overall_start).days))
        ss_progress = int(elapsed_days / total_days * 100) if total_days else 0
        ss_elapsed_years = round(elapsed_days / 365.25, 1)
        ss_remaining_years = round((total_days - elapsed_days) / 365.25, 1)

    # Rebuild BirthDetails so result.html can treat this like a normal render.
    details = BirthDetails(
        name=snap.birth_details.get("name", ""),
        birth_date=snap.birth_details.get("birth_date", ""),
        birth_time=snap.birth_details.get("birth_time", ""),
        birth_place=snap.birth_details.get("birth_place", ""),
    )
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "details": details,
            "reading": snap.reading_text,
            "sections": sections,
            "chart": chart,
            "flags": compute_vedic_flags(chart),
            "lang": snap.lang,
            "lagna_glyph": symbol_for_rashi_label(chart.lagna_rashi),
            "moon_glyph": symbol_for_rashi_label(moon_plt.rashi),
            "sun_glyph": symbol_for_rashi_label(sun_plt.rashi),
            "manglik": compute_manglik_details(chart),
            "navamsha_chart": compute_navamsha_chart(chart),
            "dashamsa_chart": compute_dashamsa_chart(chart),
            "yogas": compute_yogas(chart),
            "sade_sati": sade_sati,
            "dasha": compute_dasha_state(chart),
            "sade_sati_progress": ss_progress,
            "sade_sati_elapsed_years": ss_elapsed_years,
            "sade_sati_remaining_years": ss_remaining_years,
            # Snapshot-mode flag — result.html hides interactive controls
            # (bookmark/email/sign-in/return-triggers) when this is set.
            "is_snapshot": True,
            "snapshot": snap,
        },
    )


# ─── Standalone dosha checkers (issues #109 / #110 / #111) ────────────
#
# Purpose: dedicated SEO landing pages that rank for high-intent standalone
# queries like "manglik dosh check", "sade sati calculator", "kaal sarp
# dosh check" — which currently go to competitors because we bundle every
# dosha inside /kundli. Each checker reuses chart.py compute functions;
# no LLM call. Sub-1s response. Form details flow through the cookie so
# a user can continue to /kundli with pre-filled birth details.

def _dosha_form_ctx(page_title: str, page_lead: str, form_action: str,
                    submit_label: str, meta_desc: str,
                    prefill: dict | None = None,
                    error: str | None = None) -> dict:
    """Shared context for the dosha_check_form.html template."""
    return {
        "page_title": page_title,
        "page_lead": page_lead,
        "form_action": form_action,
        "submit_label": submit_label,
        "page_meta_description": meta_desc,
        "prefill": prefill,
        "error": error,
    }


def _prefill_from_cookie(request: Request) -> dict | None:
    """If the user's session cookie has an active saved chart, prefill the form."""
    saved = load_collection(request).active
    if saved is None:
        return None
    return {
        "name": saved.name or "",
        "birth_date": saved.birth_date,
        "birth_time": saved.birth_time,
        "birth_place": saved.birth_place,
    }


def _dosha_details_from_form(name: str, birth_date: str, birth_time: str,
                              birth_place: str) -> BirthDetails:
    return BirthDetails(
        name=(name or "").strip(),
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=(birth_place or "").strip(),
    )


@app.get("/manglik-check", response_class=HTMLResponse)
async def manglik_check_form(request: Request) -> HTMLResponse:
    """Standalone Manglik Dosh checker form (Issue #109)."""
    return templates.TemplateResponse(
        request, "dosha_check_form.html",
        _dosha_form_ctx(
            page_title="Free Manglik Dosh Check — With Classical Cancellation Rules",
            page_lead="Instant Mangal Dosh diagnosis from your birth details, with every classical cancellation rule applied. Free, no sign-up.",
            form_action="/manglik-check",
            submit_label="Check Manglik Dosh →",
            meta_desc="Free Manglik Dosh Check — instant diagnosis with all classical cancellation rules applied. No sign-up. Chart-based, honest, no upsell.",
            prefill=_prefill_from_cookie(request),
        ),
    )


@app.post("/manglik-check", response_class=HTMLResponse)
async def manglik_check_result(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> HTMLResponse:
    details = _dosha_details_from_form(name, birth_date, birth_time, birth_place)
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:manglik_check")
        return templates.TemplateResponse(
            request, "dosha_check_form.html",
            _dosha_form_ctx(
                page_title="Free Manglik Dosh Check — With Classical Cancellation Rules",
                page_lead="Instant Mangal Dosh diagnosis from your birth details, with every classical cancellation rule applied. Free, no sign-up.",
                form_action="/manglik-check",
                submit_label="Check Manglik Dosh →",
                meta_desc="Free Manglik Dosh Check — instant diagnosis with all classical cancellation rules applied. No sign-up. Chart-based, honest, no upsell.",
                prefill={"name": name, "birth_date": birth_date, "birth_time": birth_time, "birth_place": birth_place},
                error=str(err),
            ),
            status_code=400,
        )
    # Persist to session so /kundli can pick up the same chart if user continues.
    try:
        collection = load_collection(request).add(details)
    except ValueError:
        collection = None
    manglik = compute_manglik_details(chart)
    try:
        _u = load_user(request)
        notify.dosha_checked(
            dosha_type="Manglik",
            birth_place=details.birth_place,
            is_present=manglik.is_manglik,
            extra=f"{manglik.effective_status}, {manglik.severity}" if manglik.is_manglik else "",
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    response = templates.TemplateResponse(
        request, "manglik_check_result.html",
        {"details": details, "manglik": manglik, "lang": _lang(request)},
    )
    if collection is not None:
        _save_collection_synced(response, collection, request)
    return response


@app.get("/sade-sati-check", response_class=HTMLResponse)
async def sade_sati_check_form(request: Request) -> HTMLResponse:
    """Standalone Sade Sati report form (Issue #110)."""
    return templates.TemplateResponse(
        request, "dosha_check_form.html",
        _dosha_form_ctx(
            page_title="Free Sade Sati Report — Start & End Dates, Current Phase",
            page_lead="Instant Sade Sati status: which phase (rising/peak/setting), when it started, when it ends. No sign-up.",
            form_action="/sade-sati-check",
            submit_label="Check Sade Sati →",
            meta_desc="Free Sade Sati Report — instant phase check (rising/peak/setting) with start and end dates. Chart-based, honest, no upsell.",
            prefill=_prefill_from_cookie(request),
        ),
    )


@app.post("/sade-sati-check", response_class=HTMLResponse)
async def sade_sati_check_result(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> HTMLResponse:
    details = _dosha_details_from_form(name, birth_date, birth_time, birth_place)
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:sade_sati_check")
        return templates.TemplateResponse(
            request, "dosha_check_form.html",
            _dosha_form_ctx(
                page_title="Free Sade Sati Report — Start & End Dates, Current Phase",
                page_lead="Instant Sade Sati status: which phase (rising/peak/setting), when it started, when it ends. No sign-up.",
                form_action="/sade-sati-check",
                submit_label="Check Sade Sati →",
                meta_desc="Free Sade Sati Report — instant phase check with start and end dates.",
                prefill={"name": name, "birth_date": birth_date, "birth_time": birth_time, "birth_place": birth_place},
                error=str(err),
            ),
            status_code=400,
        )
    try:
        collection = load_collection(request).add(details)
    except ValueError:
        collection = None
    sade_sati = compute_sade_sati_details(chart)
    try:
        _u = load_user(request)
        if sade_sati.is_active:
            _extra = f"{sade_sati.phase or ''} phase"
        elif sade_sati.ashtama_shani:
            _extra = "Ashtama Shani (8H from Moon)"
        elif sade_sati.kantaka_shani:
            _extra = "Kantaka Shani (4H from Moon)"
        else:
            _extra = f"Saturn in H{sade_sati.saturn_house_from_moon} from Moon"
        notify.dosha_checked(
            dosha_type="Sade Sati",
            birth_place=details.birth_place,
            is_present=(sade_sati.is_active or sade_sati.ashtama_shani or sade_sati.kantaka_shani),
            extra=_extra,
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    response = templates.TemplateResponse(
        request, "sade_sati_check_result.html",
        {"details": details, "sade_sati": sade_sati, "lang": _lang(request)},
    )
    if collection is not None:
        _save_collection_synced(response, collection, request)
    return response


@app.get("/kaal-sarp-check", response_class=HTMLResponse)
async def kaal_sarp_check_form(request: Request) -> HTMLResponse:
    """Standalone Kaal Sarp geometry check (Issue #111).

    Framing rewritten 2026-08-04 after classical-source review:
    Kaal Sarp Yoga is not defined in BPHS / Brihat Jataka / Saravali /
    Phaladeepika / Jataka Parijata / Uttara Kalamrita — it is a
    20th-century Indian classification. The form and result page are
    now honest about this; see kaal_sarp_check_result.html for the
    top-of-page caveat citing K.N. Rao and B.V. Raman.
    """
    return templates.TemplateResponse(
        request, "dosha_check_form.html",
        _dosha_form_ctx(
            page_title="Kaal Sarp geometry check — honest, classical-source-checked",
            page_lead="Detect the Kaal Sarp geometry in your chart (all seven non-shadow planets on one side of the Rahu-Ketu axis) with a transparent note about where this classification actually comes from — it is not defined in the classical Sanskrit Jyotish texts we cite elsewhere on this site.",
            form_action="/kaal-sarp-check",
            submit_label="Check the geometry →",
            meta_desc="Honest Kaal Sarp Yoga check with classical-source transparency. We detect the geometric pattern and are upfront that Kaal Sarp is not in the classical Vedic texts — it is a 20th-century Indian classification widely debated even among respected astrologers.",
            prefill=_prefill_from_cookie(request),
        ),
    )


@app.post("/kaal-sarp-check", response_class=HTMLResponse)
async def kaal_sarp_check_result(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> HTMLResponse:
    details = _dosha_details_from_form(name, birth_date, birth_time, birth_place)
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:kaal_sarp_check")
        return templates.TemplateResponse(
            request, "dosha_check_form.html",
            _dosha_form_ctx(
                page_title="Free Kaal Sarp Dosh Check — With Type Classification",
                page_lead="Instant Kaal Sarp Dosh diagnosis — full or partial, plus which of the 12 named types applies.",
                form_action="/kaal-sarp-check",
                submit_label="Check Kaal Sarp Dosh →",
                meta_desc="Free Kaal Sarp Dosh Check with type classification.",
                prefill={"name": name, "birth_date": birth_date, "birth_time": birth_time, "birth_place": birth_place},
                error=str(err),
            ),
            status_code=400,
        )
    try:
        collection = load_collection(request).add(details)
    except ValueError:
        collection = None
    kaal_sarp = compute_kaal_sarp(chart)
    try:
        _u = load_user(request)
        notify.dosha_checked(
            dosha_type="Kaal Sarp",
            birth_place=details.birth_place,
            is_present=kaal_sarp.is_present,
            extra=(kaal_sarp.type_name or "") if kaal_sarp.is_present else "",
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    response = templates.TemplateResponse(
        request, "kaal_sarp_check_result.html",
        {"details": details, "kaal_sarp": kaal_sarp, "lang": _lang(request)},
    )
    if collection is not None:
        _save_collection_synced(response, collection, request)
    return response


@app.get("/muhurat/{event_slug}", response_class=HTMLResponse)
async def muhurat_landing(request: Request, event_slug: str) -> HTMLResponse:
    """Per-event Muhurat landing page (Issue #108).

    /muhurat/vivah, /muhurat/griha-pravesh, /muhurat/namkaran, /muhurat/vidyarambh,
    /muhurat/business. Renders evergreen classical intro + embedded finder form
    pre-selected to the event type. Slug (with hyphens) maps to EVENT_RULES key
    (with underscores) via replace.
    """
    from datetime import date as _date
    from astro_ai.muhurat import EVENT_RULES, EVENT_LANDING
    # Accept both hyphenated URL slugs and underscored keys for robustness.
    event_key = event_slug.replace("-", "_")
    landing = EVENT_LANDING.get(event_key)
    rules = EVENT_RULES.get(event_key)
    if landing is None or rules is None:
        raise HTTPException(status_code=404, detail=f"Unknown event type: {event_slug}")
    saved = load_collection(request).active
    prefill_city = saved.birth_place if saved else ""
    return templates.TemplateResponse(
        request, "muhurat_landing.html",
        {"landing": landing, "event_key": event_key,
         "event_label": rules["label"],
         "prefill_city": prefill_city,
         "prefill_start": _date.today().isoformat(),
         "has_saved_chart": saved is not None,
         "lang": _lang(request)},
    )


@app.get("/muhurat", response_class=HTMLResponse)
async def muhurat_finder_form(request: Request) -> HTMLResponse:
    """Muhurat Finder (Issue #108) — 5 classical event types with optional
    personal-chart matching (Tara Bala + Chandra Bala + Sade Sati + Dasha
    caution when a saved chart is in session).
    """
    from datetime import date as _date
    from astro_ai.muhurat import EVENT_RULES
    saved = load_collection(request).active
    prefill_city = saved.birth_place if saved else ""
    event_types = [(k, v["label"]) for k, v in EVENT_RULES.items()]
    return templates.TemplateResponse(
        request, "muhurat_finder.html",
        {"candidates": None, "error": None, "lang": _lang(request),
         "prefill_city": prefill_city,
         "prefill_start": _date.today().isoformat(),
         "event_types": event_types,
         "selected_event": "vivah",
         "has_saved_chart": saved is not None,
         "use_personal": False},
    )


@app.post("/muhurat", response_class=HTMLResponse)
async def muhurat_finder_compute(
    request: Request,
    event_type: str = Form("vivah"),
    city: str = Form(...),
    start_date: str = Form(...),
    days: int = Form(60),
    use_personal: str = Form(""),
    # Couple mode (Vivah only) — optional bride + groom birth details.
    # If both partners' full birth details are provided, we compute per
    # candidate Tara/Chandra Bala for BOTH partners + Manglik + Sade Sati
    # cautions per partner. Real astrologers require both charts for
    # wedding dates.
    bride_name: str = Form(""),
    bride_dob: str = Form(""),
    bride_time: str = Form(""),
    bride_place: str = Form(""),
    groom_name: str = Form(""),
    groom_dob: str = Form(""),
    groom_time: str = Form(""),
    groom_place: str = Form(""),
    # Namkaran only — child's birth details to derive first-letter suggestions
    # from Moon nakshatra pada at birth. Optional; empty = show generic table.
    child_dob: str = Form(""),
    child_time: str = Form(""),
    child_place: str = Form(""),
) -> HTMLResponse:
    from astro_ai import muhurat as _muhurat
    from datetime import date as _date
    event_types = [(k, v["label"]) for k, v in _muhurat.EVENT_RULES.items()]
    saved = load_collection(request).active
    has_saved_chart = saved is not None
    wants_personal = bool(use_personal) and has_saved_chart

    if event_type not in _muhurat.EVENT_RULES:
        return templates.TemplateResponse(
            request, "muhurat_finder.html",
            {"candidates": None, "error": f"Unknown event type: {event_type}",
             "lang": _lang(request), "prefill_city": city, "prefill_start": start_date,
             "event_types": event_types, "selected_event": event_type,
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal},
            status_code=400,
        )
    try:
        start = _date.fromisoformat(start_date)
    except ValueError:
        return templates.TemplateResponse(
            request, "muhurat_finder.html",
            {"candidates": None, "error": "Invalid start date.", "lang": _lang(request),
             "prefill_city": city, "prefill_start": start_date,
             "event_types": event_types, "selected_event": event_type,
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal},
            status_code=400,
        )

    personal_chart = None
    personal_chart_error = ""
    if wants_personal:
        try:
            details = saved.to_birth_details()
            personal_chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
        except Exception as err:  # noqa: BLE001
            personal_chart_error = f"Could not compute your chart for personal matching: {err}"

    # Couple mode — only for Vivah when BOTH partners' details are provided.
    bride_chart = None
    groom_chart = None
    couple_error = ""
    if event_type == "vivah" and bride_dob and bride_time and bride_place and groom_dob and groom_time and groom_place:
        try:
            bride_chart = compute_chart(bride_dob, bride_time, bride_place)
            groom_chart = compute_chart(groom_dob, groom_time, groom_place)
        except Exception as err:  # noqa: BLE001
            couple_error = f"Couple mode disabled — could not compute partner charts: {err}"
            bride_chart = None
            groom_chart = None

    # Namkaran — child's birth chart to derive first-letter suggestions.
    child_first_letter = ""
    child_all_letters: tuple[str, ...] = ()
    child_nakshatra = ""
    child_pada = 0
    if event_type == "namkaran" and child_dob and child_time and child_place:
        try:
            child_chart = compute_chart(child_dob, child_time, child_place)
            child_nakshatra, child_pada = _muhurat._child_moon_pada(child_chart)
            child_first_letter, child_all_letters = _muhurat._namkaran_first_letters(child_nakshatra, child_pada)
        except Exception:
            pass

    try:
        candidates = _muhurat.find_candidates(
            event_type, city=city, start=start, days=int(days),
            personal_chart=personal_chart,
            bride_chart=bride_chart, groom_chart=groom_chart,
        )
    except Exception as err:  # noqa: BLE001
        _fire_error_alert(request, err, f"muhurat:compute:{event_type}")
        return templates.TemplateResponse(
            request, "muhurat_finder.html",
            {"candidates": None, "error": f"Could not compute muhurats: {err}",
             "lang": _lang(request), "prefill_city": city, "prefill_start": start_date,
             "event_types": event_types, "selected_event": event_type,
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal},
            status_code=500,
        )
    event_label = _muhurat.EVENT_RULES[event_type]["label"]
    try:
        _u = load_user(request)
        _good_count = sum(1 for c in candidates if c.rating != "avoid")
        notify.muhurat_computed(
            event_type=event_label, city=city, days_range=int(days),
            good_count=_good_count,
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    return templates.TemplateResponse(
        request, "muhurat_finder.html",
        {"candidates": candidates, "city": city, "start_date": start_date,
         "prefill_city": city, "prefill_start": start_date,
         "error": (personal_chart_error or couple_error) or None,
         "event_types": event_types, "selected_event": event_type,
         "event_label": event_label,
         "has_saved_chart": has_saved_chart, "use_personal": wants_personal,
         "personal_active": personal_chart is not None,
         "couple_active": (bride_chart is not None and groom_chart is not None),
         "prefill_bride_name": bride_name, "prefill_bride_dob": bride_dob,
         "prefill_bride_time": bride_time, "prefill_bride_place": bride_place,
         "prefill_groom_name": groom_name, "prefill_groom_dob": groom_dob,
         "prefill_groom_time": groom_time, "prefill_groom_place": groom_place,
         "prefill_child_dob": child_dob, "prefill_child_time": child_time,
         "prefill_child_place": child_place,
         "child_first_letter": child_first_letter,
         "child_all_letters": child_all_letters,
         "child_nakshatra": child_nakshatra,
         "child_pada": child_pada,
         "lang": _lang(request)},
    )


@app.get("/numerology", response_class=HTMLResponse)
async def numerology_form(request: Request) -> HTMLResponse:
    """Numerology calculator form (Issue #112).

    Positioned as complementary to Vedic astrology, not a replacement.
    Pure math + interpretation strings — no LLM call.
    """
    return templates.TemplateResponse(
        request, "numerology.html",
        {
            "page_title": "Free Numerology Calculator — Chaldean, Pythagorean, and Lo Shu (with honest tradition note)",
            "page_meta": "Free numerology calculator using Chaldean (Cheiro) and Pythagorean systems plus the Chinese Lo Shu grid. Life Path, Destiny/Expression, Soul Urge, Personality, Name Number, per-Life-Path profile, Personal Year, Karmic Debt (13/14/16/19), traditional per-number practices, and 2-person compatibility. Honest about tradition: these systems are 19th-20th century Western and ancient Chinese, not classical Vedic Jyotish. No signup.",
            "reading": None,
            "error": None,
            "lang": _lang(request),
        },
    )


@app.post("/numerology", response_class=HTMLResponse)
async def numerology_calculate(
    request: Request,
    name: str = Form(...),
    birth_date: str = Form(...),
    system: str = Form("chaldean"),
) -> HTMLResponse:
    """Compute numerology reading (Issue #112)."""
    from astro_ai import numerology as _num
    name = (name or "").strip()
    if not name or len(name) < 2:
        return templates.TemplateResponse(
            request, "numerology.html",
            {
                "page_title": "Free Numerology Calculator",
                "page_meta": "Free numerology calculator with Chaldean + Pythagorean systems.",
                "reading": None,
                "error": "Please enter your full name (at least 2 characters).",
                "lang": _lang(request),
            },
            status_code=400,
        )
    if system not in ("chaldean", "pythagorean"):
        system = "chaldean"
    try:
        reading = _num.compute(name=name, birth_date=birth_date, system=system)
    except Exception as err:  # noqa: BLE001
        _fire_error_alert(request, err, "numerology:compute")
        return templates.TemplateResponse(
            request, "numerology.html",
            {"page_title": "Free Numerology Calculator",
             "page_meta": "Free numerology calculator.", "reading": None,
             "error": f"Couldn't compute: {err}", "lang": _lang(request)},
            status_code=400,
        )
    try:
        _u = load_user(request)
        notify.numerology_computed(
            name=reading.name, system=system,
            life_path=int(reading.life_path),
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    # Numerology-only Bhagya Score — separate from the chart-based one on
    # /kundli. Sources signals purely from the numerology reading so
    # users who compute numerology first (without a Kundli) still get a
    # headline number.
    from astro_ai.numerology import compute_numerology_bhagya_score as _num_bhagya
    return templates.TemplateResponse(
        request, "numerology.html",
        {
            "page_title": f"Numerology Reading for {reading.name} — Life Path {reading.life_path}",
            "page_meta": f"Free numerology reading for {reading.name}: Life Path {reading.life_path}, Destiny {reading.destiny}, Soul Urge {reading.soul_urge}, Personality {reading.personality}, Name Number {reading.name_number}. Character profile, life challenges, career fields, best partners, traditional per-number practices, and the Chinese Lo Shu birth-number matrix. Framework is modern Western (Chaldean/Pythagorean) + ancient Chinese, not classical Vedic Jyotish.",
            "reading": reading,
            "num_bhagya_score": _num_bhagya(reading),
            "error": None,
            "lang": _lang(request),
            **_ask_cta_ctx(request, hint="about your chart (numerology-related life questions)"),
        },
    )


@app.get("/numerology/compatibility", response_class=HTMLResponse)
async def numerology_compat_form(request: Request) -> HTMLResponse:
    """Numerology compatibility form (Issue #120 Phase 2) — 2-person pairing."""
    return templates.TemplateResponse(
        request, "numerology_compat.html",
        {
            "page_title": "Numerology Compatibility — 2-Person Pairing Check",
            "page_meta": "Free numerology compatibility check — Life Path + Birthday + Destiny pair verdicts using the modern Chaldean/Pythagorean framework (not classical Vedic Jyotish). General / marriage / business contexts.",
            "compat": None, "error": None, "lang": _lang(request),
        },
    )


@app.post("/numerology/compatibility", response_class=HTMLResponse)
async def numerology_compat_compute(
    request: Request,
    name_a: str = Form(...),
    birth_date_a: str = Form(...),
    name_b: str = Form(...),
    birth_date_b: str = Form(...),
    context: str = Form("general"),
) -> HTMLResponse:
    from astro_ai import numerology as _num
    name_a = (name_a or "").strip()
    name_b = (name_b or "").strip()
    if not name_a or not name_b or len(name_a) < 2 or len(name_b) < 2:
        return templates.TemplateResponse(
            request, "numerology_compat.html",
            {"page_title": "Numerology Compatibility",
             "page_meta": "Free numerology compatibility check.",
             "compat": None,
             "error": "Please enter both names (at least 2 characters each).",
             "lang": _lang(request)},
            status_code=400,
        )
    if context not in ("general", "marriage", "business"):
        context = "general"
    try:
        compat = _num.compute_compatibility(name_a, birth_date_a, name_b, birth_date_b, context=context)
    except Exception as err:  # noqa: BLE001
        _fire_error_alert(request, err, "numerology:compat")
        return templates.TemplateResponse(
            request, "numerology_compat.html",
            {"page_title": "Numerology Compatibility",
             "page_meta": "Free numerology compatibility check.",
             "compat": None,
             "error": f"Couldn't compute: {err}",
             "lang": _lang(request)},
            status_code=400,
        )
    return templates.TemplateResponse(
        request, "numerology_compat.html",
        {
            "page_title": f"Compatibility: {compat.person_a_name} × {compat.person_b_name}",
            "page_meta": f"Numerology compatibility {compat.person_a_name} + {compat.person_b_name}: {compat.overall_score}/100. {compat.overall_summary[:100]}",
            "compat": compat, "context": context,
            "error": None,
            "lang": _lang(request),
        },
    )


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
        "festival": festivals.festival_for_date(today),
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


@app.get("/admin/usage", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_usage(request: Request, days: int = 1) -> HTMLResponse:
    """Observability page — recent LLM-call counts grouped by route + cache hit rate.

    Protected by HTTP Basic Auth (username 'admin', password from
    ADMIN_PASSWORD env var). Browser shows the standard login prompt.
    """
    from astro_ai import llm_stats
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
    # Persistent-user counts — separate from Rashifal email subscribers.
    # These are people who signed in with Google (may or may not be subscribed
    # to daily emails).
    user_count = users.count()
    subscriber_count = subscribers.count()
    # Per-model / per-route LLM call breakdown for the same window.
    llm_stats_summary = llm_stats.range_summary(days=days)
    return templates.TemplateResponse(
        request, "admin_usage.html",
        {
            "lang": _lang(request),
            "summary": summary,
            "days": days,
            "user_count": user_count,
            "subscriber_count": subscriber_count,
            "llm_stats": llm_stats_summary,
        },
    )


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
async def ask_form(request: Request, q: str | None = None, c: str | None = None) -> HTMLResponse:
    """Free-form Q&A about the seeker's chart.

    GET shows the question form. If `q` and `c` are present (after a POST
    redirect or cache-hit re-visit), the answer is rendered alongside the
    form so the user can ask follow-ups.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
    answer = None
    if q:
        # Render a previously-asked question by re-running the cached lookup.
        # POST handler stores the (question, category) and we look it up.
        answer = _ask_lookup(saved, q, c or "general", lang)
    return templates.TemplateResponse(
        request, "ask.html",
        {
            "lang": lang,
            "active_chart": saved,
            "current_question": q or "",
            "current_category": c or "general",
            "answer": answer,
            "remaining_today": _ask_quota_remaining(request),
        },
    )


# Daily per-cookie quota. Tight at 3/day while we're on free LLM tiers —
# one motivated user can't drain Groq/Cerebras's daily quota for everyone.
# Bump this when we have paid LLM capacity or revenue covering the cost.
_ASK_DAILY_LIMIT = 3
_ASK_CATEGORIES = {"general", "career", "marriage", "money", "health",
                   "spiritual", "travel", "relationships"}


def _is_localhost(request: Request) -> bool:
    """True when the request is from the developer's own machine.

    Used to bypass the /ask daily quota during local development so the dev
    can exercise the feature freely without exhausting the production limit.
    Covers IPv4 loopback, IPv6 loopback, and the "localhost" hostname.
    """
    client = request.client
    if client is None:
        return False
    return client.host in {"127.0.0.1", "localhost", "::1"}


def _no_cdn_cache(resp: Response) -> Response:
    """Stamp response with headers that stop CDN edge caches from
    snapshotting the page across deploys.

    External re-audit caught /rashifal being served from a stale Fastly
    snapshot even though the site had been deployed with fixes. Root
    cause: Cloud Run sends `cache-control: private` by default which
    SHOULD prevent shared-cache storage, but Fastly's default config
    snapshots aggressively on non-cookie'd anonymous fetches. Stronger
    directives fix that.

    Applied only to pages whose content changes daily (Rashifal,
    Panchang) — for evergreen /learn/ articles or static tool pages,
    the default cache-control is fine and desirable.
    """
    resp.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    # CDN-specific opt-out signals (Fastly / Cloudflare / GCP CDN all
    # honour at least one of these — belt-and-braces is cheap here).
    resp.headers["CDN-Cache-Control"] = "no-store"
    resp.headers["Surrogate-Control"] = "no-store"
    return resp


def _ask_cta_ctx(request: Request, hint: str = "about your chart") -> dict:
    """Build the context dict for the shared _ask_cta.html partial.

    Any result page that wants to show the 'Ask 3 free questions' CTA
    just merges this into its TemplateResponse context. Handles:
      - Detecting a saved chart (has_saved_chart)
      - Reading today's remaining quota
      - Passing the per-page phrasing hint ('about your chart' vs
        'about your numerology' vs 'about your Kundli match')
    """
    try:
        has_saved_chart = load_collection(request).active is not None
    except Exception:
        has_saved_chart = False
    return {
        "has_saved_chart": has_saved_chart,
        "ask_remaining": _ask_quota_remaining(request),
        "ask_context_hint": hint,
    }


def _ask_quota_remaining(request: Request) -> int:
    """Read today's remaining ask count from the session cookie.

    Localhost bypasses the quota entirely — returns a large sentinel so
    the UI shows plenty of remaining questions during local development.
    """
    if _is_localhost(request):
        return 9999
    stored_date, used = load_ask_usage(request)
    today = date.today().isoformat()
    if stored_date != today:
        return _ASK_DAILY_LIMIT
    return max(0, _ASK_DAILY_LIMIT - used)


def _ask_quota_bump(request: Request, response: Response) -> None:
    """Increment today's count on the response cookie.

    Localhost skips the increment so local dev exercises the feature
    without touching production-shaped state.
    """
    if _is_localhost(request):
        return
    stored_date, used = load_ask_usage(request)
    today = date.today().isoformat()
    new_count = (used + 1) if stored_date == today else 1
    save_ask_usage(response, request, today, new_count)


def _ask_cache_key(saved, question: str, category: str, lang: str) -> str:
    """Stable cache key for an (chart, question, category) combination."""
    chart_fp = cache.fingerprint_chart(
        saved.birth_date, saved.birth_time, saved.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(ASK_PROMPT_PATH)
    # Python's hash() is randomised per-process; use a stable hash so the
    # cache key survives container restarts.
    import hashlib
    q_fp = hashlib.sha1(question.strip().encode("utf-8")).hexdigest()[:16]
    return f"ask:{chart_fp}:{q_fp}:{category}:{prompt_fp}:{lang}"


def _ask_lookup(saved, question: str, category: str, lang: str) -> str | None:
    """Look up an already-cached answer without burning a fresh LLM call."""
    return cache.get(_ask_cache_key(saved, question, category, lang))


@app.post("/ask")
async def ask_submit(
    request: Request,
    question: str = Form(""),
    category: str = Form("general"),
) -> Response:
    """Submit a question. PRG-style: validate → generate → cache → 303 to GET."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
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
    cache_key = _ask_cache_key(saved, question, category, lang)
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

    # Notify owner of the Q&A submission. Fires on both fresh and cached
    # generations; the dedup window in notify.py suppresses rapid re-fires.
    # `model` is populated only on fresh generations (contextvar set by
    # providers.chat()); cache hits show blank model.
    _u_ask = load_user(request)
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
        },
    )

    # Redirect with the question + category in the URL so refresh doesn't
    # re-submit, the user can bookmark / share the URL, and back/forward
    # works naturally. Only bump the quota on a fresh generation.
    from urllib.parse import urlencode
    response = RedirectResponse(
        f"/ask?{urlencode({'q': question, 'c': category})}", status_code=303
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
    if os.environ.get("OPENAI_API_KEY"):
        try:
            g_fp = cache.fingerprint_chart(g_birth_date, g_birth_time, g_birth_place)
            b_fp = cache.fingerprint_chart(b_birth_date, b_birth_time, b_birth_place)
            # Sort so the order of the two people doesn't matter for cache hits.
            pair_key = ":".join(sorted([g_fp, b_fp]))
            prompt_fp = cache.fingerprint_prompt(MATCHING_PROMPT_PATH)
            cache_key = f"matching:{pair_key}:{lang}:{prompt_fp}"
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

    # Fire notify AFTER narrative attempt so `model` reflects the LLM that
    # actually served (empty if narrative was skipped or failed).
    _u_match = load_user(request)
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

    return templates.TemplateResponse(
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


def _safe_redirect_target(candidate: str) -> str:
    """Allow only same-origin paths in `next=` redirects (open-redirect guard)."""
    return candidate if candidate.startswith("/") and not candidate.startswith("//") else "/"


def cli() -> None:
    """Entry point for the `astro-ai` console script: starts uvicorn on localhost:8000."""
    uvicorn.run("astro_ai.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    cli()
