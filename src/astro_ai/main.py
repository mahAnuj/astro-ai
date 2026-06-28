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
    ChartError,
    compute_chart,
    compute_dasha_state,
    compute_gochar_impacts,
    compute_life_chapters,
    compute_manglik_details,
    compute_marriage_profile,
    compute_panchang,
    compute_sade_sati_details,
    compute_transit_events,
    compute_transit_snapshot,
    compute_varshaphala,
    compute_vedic_flags,
    compute_wealth_profile,
    symbol_for_rashi_label,
)
from astro_ai.i18n import translate as _i18n_translate
from astro_ai.llm import (
    BirthDetails,
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
from astro_ai import cache, email_sender, feedback, festivals, shloks, storage, subscribers, trivia
import time as _time
from astro_ai.session import (
    SUPPORTED_LANGS,
    ChartCollection,
    clear_collection,
    load_collection,
    load_lang,
    save_collection,
    save_lang,
)


def _lang(request: Request) -> str:
    """Backwards-compat alias — read lang from the combined __session cookie."""
    return load_lang(request)


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
        cache.log_call(route, lang, cache_hit=True)
        cache.put(cache_key, persistent, route=route, ttl_days=1)  # warm SQLite
        return persistent

    # Tier 2: SQLite — per-instance, alive while the container is.
    sqlite_hit = cache.get(cache_key)
    if sqlite_hit is not None:
        cache.log_call(route, lang, cache_hit=True)
        storage.put(storage_key, sqlite_hit)  # backfill GCS
        return sqlite_hit

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
    """
    hit = cache.get(cache_key)
    if hit is not None:
        cache.log_call(route, lang, cache_hit=True)
        return hit
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
load_dotenv(override=True)

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
RASHIFAL_PROMPT_PATH = PROMPTS_DIR / "rashifal.txt"
DASHA_DEEP_DIVE_PROMPT_PATH = PROMPTS_DIR / "dasha_deep_dive.txt"

app = FastAPI(title="astro-ai", version="0.0.1")
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
    ]
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, needs_chart: str | None = None) -> HTMLResponse:
    """Form for new visitors, chart-list + form for returning seekers.

    `?needs_chart=<feature>` is set when other routes redirect here because
    no saved chart exists yet. We surface a brief banner naming the feature
    the seeker tried to reach, so the redirect isn't silent.
    """
    collection = load_collection(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "collection": collection,
            "saved": collection.active,
            "lang": _lang(request),
            "needs_chart_for": needs_chart,
        },
    )


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
    save_collection(response, collection, request)
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
    """Render the Janma Kundli reading for the currently active saved chart."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=kundli", status_code=303)
    return await _render_natal_for(request, saved.to_birth_details())


async def _render_natal_for(request: Request, details: BirthDetails) -> HTMLResponse:
    """Shared natal-reading renderer used by both GET /natal and POST /reading."""
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
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
    lang = _lang(request)
    chart_fp = cache.fingerprint_chart(details.birth_date, details.birth_time, details.birth_place)
    prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
    cache_key = f"natal:{chart_fp}:{lang}:{prompt_fp}"
    try:
        reading_text = _cached(
            cache_key, route="natal", lang=lang, ttl_days=None,
            call_fn=lambda: generate_reading(
                details, chart=chart, flags=flags, life_chapters=life_chapters,
                prompt_path=PROMPT_PATH, lang=lang,
            ),
        )
    except Exception as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate a reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
        )
    sections = parse_sectioned_reading(reading_text)
    sade_sati = compute_sade_sati_details(chart)

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
            # Structured insight panels — see chart.py for shape.
            "marriage": compute_marriage_profile(chart),
            "wealth":   compute_wealth_profile(chart),
            "manglik":  compute_manglik_details(chart),
            "sade_sati": sade_sati,
            "dasha":    compute_dasha_state(chart),
            # Pre-computed SS timeline values for the panel.
            "sade_sati_progress": ss_progress,
            "sade_sati_elapsed_years": ss_elapsed_years,
            "sade_sati_remaining_years": ss_remaining_years,
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
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate today's reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
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
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate the reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
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
        },
    )


@app.get("/rashifal", response_class=HTMLResponse)
async def rashifal(request: Request) -> HTMLResponse:
    """Daily Rashifal — generic predictions for all 12 Moon signs.

    No saved chart needed — readers just scroll to their own rashi. Cached
    per (date, lang) so all visitors share the same generation.
    """
    lang = _lang(request)
    today_iso = date.today().isoformat()
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)
    cache_key = f"rashifal:{today_iso}:{lang}:{prompt_fp}"

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured",
             "message": "Add OPENAI_API_KEY to .env to generate today's Rashifal."},
            status_code=503,
        )

    # Use a low-cost transit reference for the LLM context.
    # Build a "neutral" anchor — Lagna and Moon use a dummy fixed natal so
    # the transit snapshot just reports today's planet positions; we don't
    # use the natal-relative house numbers in the Rashifal prompt anyway.
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute reference chart", "message": str(err)},
            status_code=500,
        )
    transit = compute_transit_snapshot(neutral_chart)

    # Three-tier cache for Rashifal: GCS (cross-instance) → SQLite (per-instance) → LLM.
    # Each tier is written back from below on a miss, so future requests hit
    # the fastest tier available. Storage key includes prompt fingerprint so
    # a prompt edit auto-invalidates yesterday's cache.
    storage_key = f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt"
    try:
        text = _shared_three_tier(
            route="rashifal",
            cache_key=cache_key,
            storage_key=storage_key,
            lang=lang,
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
            ),
        )
    except Exception as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't generate Rashifal",
             "message": f"{type(err).__name__}: {err}"},
            status_code=502,
        )

    # Augment each section with its zodiac glyph (♈♉..♓) for the cards.
    sections_with_glyphs = [
        (symbol_for_rashi_label(title) or "✦", title, body)
        for title, body in parse_sectioned_reading(text)
    ]
    return templates.TemplateResponse(
        request, "rashifal.html",
        {"lang": lang, "today_date": today_iso, "sections": sections_with_glyphs},
    )


@app.post("/subscribe")
async def subscribe(request: Request,
                    email: str = Form(...),
                    lang: str = Form("en"),
                    city: str = Form("")) -> JSONResponse:
    """Add an email to the daily-Rashifal subscriber list.

    Called from the modal in _subscribe_modal.html via fetch(). Returns JSON
    `{ok: true}` on success or `{ok: false, error: "..."}` so the frontend
    can show inline feedback without a full page reload.

    Side effect: sends a one-off welcome email to brand-new subscribers
    (skipped for re-subscribes). Welcome failure is logged but doesn't
    block the success response — the subscription itself already saved.
    """
    ok, is_new, msg = subscribers.subscribe(email, lang, city)
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    if is_new:
        try:
            _send_welcome_email(email, lang, city)
        except Exception as err:
            # Log and continue — the user is already subscribed; missing
            # welcome is a minor degradation, not a failure.
            import logging
            logging.getLogger(__name__).warning("welcome email failed for %s: %s", email, err)
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


def _send_welcome_email(email: str, lang: str, city: str = "") -> bool:
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
        text = _shared_three_tier(
            route="rashifal",
            cache_key=f"rashifal:{today_iso}:{lang}:{prompt_fp}",
            storage_key=f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt",
            lang=lang,
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
            ),
        )
        sections = [
            (symbol_for_rashi_label(title) or "✦", title, body)
            for title, body in parse_sectioned_reading(text)
        ]
    except Exception:
        # If Rashifal generation fails entirely, send the rest of the
        # welcome anyway — better than blocking on a missed reading.
        sections = []

    ctx = _email_context(lang=lang, city=city)
    ctx["rashifal_sections"] = sections
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
            text = _shared_three_tier(
                route="rashifal",
                cache_key=cache_key,
                storage_key=storage_key,
                lang=lang,
                call_fn=lambda lang=lang: generate_rashifal(
                    transit=transit, today_iso=today_iso,
                    prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                ),
            )
            sections_by_lang[lang] = [
                (symbol_for_rashi_label(title) or "✦", title, body)
                for title, body in parse_sectioned_reading(text)
            ]
        except Exception as err:
            return JSONResponse(
                {"ok": False, "error": f"Couldn't load Rashifal ({lang}): {type(err).__name__}: {err}"},
                status_code=502,
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
        ctx["rashifal_sections"] = sections_by_lang[lang]
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
    summary = cache.usage_summary(days=days)
    return templates.TemplateResponse(
        request, "admin_usage.html",
        {"lang": _lang(request), "summary": summary, "days": days},
    )


@app.get("/dasha", response_class=HTMLResponse)
async def dasha(request: Request) -> HTMLResponse:
    """Vimshottari Dasha timeline for the active saved chart."""
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
    chart_fp = cache.fingerprint_chart(natal)
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
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't generate the deep dive",
             "message": f"{type(err).__name__}: {err}"},
            status_code=502,
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
        except Exception:
            narrative_sections = []  # surface as no-narrative; scores still render

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
    save_collection(response, collection, request)
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
    else:
        save_collection(response, collection, request)
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
