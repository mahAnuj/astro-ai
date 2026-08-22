"""Daily rashifal — the 12-card grid and the per-rashi reading (issue #154).

Owns:
    GET /rashifal          the flip-card landing page (zero LLM traffic)
    GET /rashifal/{rashi}  one rashi's daily reading, served both as the HTMX
                           card fragment and as the standalone SEO page

plus ``_RASHIFAL_UI_META``, the presentation-only per-rashi glyph/colour table
the standalone hero needs.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import os
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from astro_ai import daily_cache, festivals
from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
from astro_ai.llm import parse_sectioned_reading
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    RASHIFAL_PROMPT_PATH,
    _lang,
    _no_cdn_cache,
    _pretty_date,
    panchang_strip_ctx,
    templates,
)
from astro_ai.routes.llm_support import _fire_error_alert, _llm_error_friendly

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/rashifal", response_class=HTMLResponse)
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
            # The reading names Rahu Kaal and Abhijit but never clocks them,
            # because one national text cannot. This is where the reader's own
            # computed times come from. Cached per (day, city); no new compute.
            **panchang_strip_ctx(request),
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


@router.get("/rashifal/{rashi}", response_class=HTMLResponse)
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
        # See the grid route — the seeker's own Rahu Kaal / Abhijit, since the
        # reading itself is forbidden from stating a clock time.
        **panchang_strip_ctx(request),
    }
    template = "_rashifal_card_content.html" if is_htmx else "rashifal_single.html"
    # Only cache-harden the full-page render; the HTMX fragment is
    # per-user-session content that Fastly ignores anyway (POST-like).
    resp = templates.TemplateResponse(request, template, ctx)
    return resp if is_htmx else _no_cdn_cache(resp)
