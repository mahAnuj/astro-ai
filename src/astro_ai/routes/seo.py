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
from astro_ai.hindi_pages import hindi_url, hreflang_alternates
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

    Hindi twins (#124): a page listed by ``hindi_pages`` also gets its /hi/
    URL as its own <url> entry, and BOTH entries carry the same three
    xhtml:link hreflang annotations. Reciprocity is what makes Google honour
    hreflang at all — an annotation that is not mirrored on the other side is
    discarded. Pages with no Hindi version get no annotations whatsoever.
    """
    base = _site_url()
    today = date.today().isoformat()
    # changefreq + priority are hints — Google mostly ignores them but other
    # search engines (Bing, Yandex) still use them as ranking signals.
    #
    # The 4th element is <lastmod>, and None means OMIT THE ELEMENT. Until
    # #124 every URL here was stamped with today's date, including /learn/
    # articles untouched since June. Google learns to discount an always-today
    # lastmod and the discount is site-wide, so ~187 false stamps were
    # devaluing the signal on the 13 URLs that are genuinely regenerated daily.
    # None wherever we have no real source of truth: an absent lastmod is
    # honest and free, an invented one is the defect in a new hat. A
    # hand-maintained date table for the static pages was considered and
    # rejected — nobody would maintain it, and a stale hand-typed date is the
    # same lie more slowly.
    pages = [
        ("/",         "daily",   "1.0", None),
        ("/rashifal", "daily",   "0.9", today),   # 06:30/06:45 warm jobs rewrite it
        ("/matching", "monthly", "0.7", None),
        ("/learn/",   "weekly",  "0.8", None),
        # Tools
        ("/muhurat",         "monthly", "0.7", None),
        ("/manglik-check",   "monthly", "0.7", None),
        ("/sade-sati-check", "monthly", "0.7", None),
        ("/kaal-sarp-check", "monthly", "0.7", None),
        ("/numerology",      "monthly", "0.7", None),
        ("/numerology/compatibility", "monthly", "0.7", None),
        ("/kundli",          "monthly", "0.8", None),
        ("/dasha",           "monthly", "0.7", None),
        ("/panchang",        "daily",   "0.8", None),
        ("/festivals",       "weekly",  "0.7", None),
        ("/about",           "monthly", "0.5", None),
        ("/privacy",         "yearly",  "0.3", None),
        ("/terms",           "yearly",  "0.3", None),
    ]
    # Muhurat per-event landing pages — evergreen SEO copy per event type.
    from astro_ai.muhurat import EVENT_LANDING
    for event_key, landing in EVENT_LANDING.items():
        # Evergreen copy with no edit date behind it — no lastmod.
        pages.append((f"/muhurat/{landing['slug']}", "monthly", "0.7", None))
    # Per-rashi Rashifal URLs — 12 daily-fresh pages Google can rank
    # independently for 'aries daily horoscope' etc.
    from astro_ai.llm import RASHI_CANONICAL_SLUGS as _RASHI_SLUGS_FOR_SITEMAP
    for _slug in _RASHI_SLUGS_FOR_SITEMAP:
        pages.append((f"/rashifal/{_slug}", "daily", "0.7", today))
    # Rolling 90-day Panchang archive — 30 past + today + 59 future so
    # Google discovers 'panchang for {upcoming date}' queries + can still
    # serve retrospective 'what was tithi on {past date}' searches.
    # SEO audit #132 Phase 2.
    from datetime import timedelta as _td
    _today = date.today()
    for _offset in range(-30, 60):
        _d = _today + _td(days=_offset)
        # A past or present date's panchang is fixed by the ephemeris and does
        # not change afterwards, so the date itself IS its lastmod. Future
        # dates get none: a lastmod in the future asserts an edit that has not
        # happened, and Google discards it anyway.
        _lastmod = _d.isoformat() if _d <= _today else None
        pages.append((f"/panchang/{_d.isoformat()}", "daily", "0.5", _lastmod))
    # Auto-include every learning article so Google can crawl them all from
    # one place. New articles dropped into learn_registry appear here
    # automatically — no sitemap maintenance.
    for a in learn_registry.all_articles():
        # Article.last_updated is "YYYY-MM"; day-1 is the only defensible
        # rendering of a month-granular edit date into <lastmod>'s W3C date.
        pages.append((f"/learn/{a.slug}/", "monthly", "0.7", f"{a.last_updated}-01"))

    def _url_entry(loc: str, freq: str, prio: str, lastmod: str | None,
                   alternates: list[tuple[str, str]]) -> str:
        entry = "  <url>\n"
        entry += f"    <loc>{base}{loc}</loc>\n"
        if lastmod:
            entry += f"    <lastmod>{lastmod}</lastmod>\n"
        entry += f"    <changefreq>{freq}</changefreq>\n"
        entry += f"    <priority>{prio}</priority>\n"
        for tag, href in alternates:
            entry += f'    <xhtml:link rel="alternate" hreflang="{tag}" href="{href}"/>\n'
        entry += "  </url>\n"
        return entry

    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    )
    for path, freq, prio, lastmod in pages:
        # Empty for every unpublished page, which is the whole point — see
        # hindi_pages.hreflang_alternates. base_url is passed so _site_url()
        # is read once per request rather than once per URL.
        alternates = hreflang_alternates(path, base_url=base)
        body += _url_entry(path, freq, prio, lastmod, alternates)
        hi_path = hindi_url(path)  # None unless this page is Hindi-published
        if hi_path is not None:
            # Same lastmod/freq/priority and the SAME annotation list: the two
            # entries describe one page in two languages, not two pages.
            body += _url_entry(hi_path, freq, prio, lastmod, alternates)
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


