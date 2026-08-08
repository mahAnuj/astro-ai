"""Crawler- and browser-facing infrastructure files (issue #154).

Owns:
    GET /sitemap.xml   XML sitemap (static pages + generated muhurat / rashifal
                       / panchang-archive / learn URLs)
    GET /robots.txt    crawler directives
    GET /sw.js         PWA service worker, served from root for scope `/`

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from astro_ai import learn_registry
from astro_ai.routes.deps import STATIC_DIR, _site_url

router = APIRouter()


@router.get("/sitemap.xml", include_in_schema=False)
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
        ("/festivals",       "weekly",  "0.7"),
        ("/about",           "monthly", "0.5"),
        ("/privacy",         "yearly",  "0.3"),
        ("/terms",           "yearly",  "0.3"),
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


@router.get("/robots.txt", include_in_schema=False)
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


@router.get("/sw.js", include_in_schema=False)
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


