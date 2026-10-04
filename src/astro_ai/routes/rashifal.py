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
import time as _time
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from astro_ai import daily_cache, festivals, hindi_pages
from astro_ai.i18n import translate as t
from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
from astro_ai.llm import parse_sectioned_reading
from astro_ai import providers as llm_providers
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    RASHIFAL_PROMPT_PATH,
    _lang,
    _lang_prefix,
    _no_cdn_cache,
    _pretty_date,
    panchang_strip_ctx,
    templates,
)
from astro_ai.routes.llm_support import _fire_error_alert, _llm_error_friendly

log = logging.getLogger(__name__)

_REGEN_COOLDOWN_S = 300.0
"""Seconds before retrying a rashi whose generation failed the quality gate."""

_regen_failures: dict[str, float] = {}


def _reading_error_fragment(slug: str, is_rate: bool, msg: str,
                            lang: str = "en") -> str:
    """Card-shaped retry block for the HTMX flip-card path.

    Both error paths render through this: a live generation failure and a
    cooldown-suppressed retry. `msg` is the BODY only — the heading comes from
    `is_rate`, so passing a full sentence duplicates it on the card. The cooldown path used to
    `raise HTTPException(503)`, which escapes the route before `is_htmx` is
    consulted and renders the whole 81 KB error page — and base.html sets
    `responseHandling: [{"code": ".*", "swap": true}]`, so htmx swaps that
    entire document, <head> and duplicate script tags included, into a flip
    card sized for a paragraph.
    """
    # `lang` was added after QA found that the Hindi hub's tiles — which this
    # branch's own fix pointed at /hi/ — rendered this card with English
    # chrome whose "Try again" re-fetched the ENGLISH fragment. Pressing retry
    # on a Hindi card therefore swapped in an English reading, and burnt an
    # English generation the reader could not use (QA 2026-10-04).
    prefix = "/hi" if lang == "hi" and hindi_pages.is_hindi_published(f"/rashifal/{slug}") else ""
    icon = "\U0001F549\uFE0F" if is_rate else "\u26A0\uFE0F"
    head = t(lang, "rashifal_card_busy" if is_rate else "rashifal_card_failed")
    return (
        '<div class="h-full flex flex-col items-center justify-center text-center gap-3 p-4">'
        f'  <div class="text-3xl" aria-hidden="true">{icon}</div>'
        f'  <div class="text-sm font-semibold text-stone-800">{head}</div>'
        f'  <div class="text-xs text-stone-600 leading-relaxed">{msg}</div>'
        '  <div class="flex gap-2 pt-1">'
        f'    <button type="button" class="text-xs text-astro-700 hover:text-astro-800 hover:underline font-semibold" '
        f'            hx-get="{prefix}/rashifal/{slug}" hx-target="closest [data-card-front]" hx-swap="innerHTML" '
        f'            hx-headers=\'{{"HX-Rashifal-Fragment": "1"}}\'>{t(lang, "rashifal_card_retry")}</button>'
        '    <span class="text-stone-300">\u00B7</span>'
        f'    <a href="{prefix}/rashifal/{slug}" class="text-xs text-astro-700 hover:text-astro-800 hover:underline font-semibold">{t(lang, "rashifal_card_open")}</a>'
        '  </div>'
        '</div>'
    )


def _regen_blocked(cache_key: str) -> bool:
    return _time.monotonic() - _regen_failures.get(cache_key, -_REGEN_COOLDOWN_S) < _REGEN_COOLDOWN_S


def _regen_fail(cache_key: str) -> None:
    _regen_failures[cache_key] = _time.monotonic()
    if len(_regen_failures) > 64:                      # 12 rashis x 2 langs, with slack
        _regen_failures.clear()

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
            # Deliberately NOT localised: this fires only when the operator
            # has not configured a key, so the audience is the operator, and
            # `msg` is operational English. `lang` is still passed so the
            # document declares the language it is actually in.
            {"title": "API key not configured", "message": msg, "lang": "en"},
            status_code=503,
        )

    # Per-rashi daily cache — key: rashifal_{slug}, e.g. rashifal_aries.
    cache_key = f"{canonical_slug}-{lang}"
    cached = daily_cache.get("rashifal_single", cache_key, today_iso)
    reading_body: str | None = cached.get("body") if cached else None

    # Re-gate what came out of the cache (#215). `_shared_three_tier` has done
    # this on every GCS and SQLite hit for a long time; this path never did, so
    # a blank or truncated body written once was served for the REST OF THE DAY
    # with no healthy retry. Evidence it happened: the 2026-08-20 leo, libra and
    # virgo fixtures all carry `body: ""`.
    #
    # This is the same failure shape as the outage fixed in ed5cb2c — an empty
    # completion treated as a valid answer — one layer up. That fix stops new
    # blanks being produced; it does nothing about a blank already on disk, and
    # nothing about a degraded entry written by an older build.
    if reading_body is not None:
        ok, reason = llm_providers.passes_quality(reading_body, "rashifal_single")
        if not ok:
            log.warning("rashifal_single: discarding cached %s (%s) — regenerating",
                        cache_key, reason)
            reading_body = None

    # Bound the retry. Discarding a bad entry is right; discarding it on every
    # pageview and regenerating each time is one live LLM call per view, all
    # day, per rashi — on the quota that caused a 21-day outage. So a rashi
    # whose generation just failed the gate is left alone for a short while.
    #
    # This suppresses REGENERATION only. The reader still gets the friendly
    # error path below and we still get the alert, so it cannot become the
    # silent blank page a previous degraded-state marker produced — and it
    # self-heals after the cooldown without anyone intervening.
    if reading_body is None and _regen_blocked(cache_key):
        log.warning("rashifal_single: %s failed generation recently — not retrying yet", cache_key)
        # RETURN, do not raise. A raise escapes before `is_htmx` is consulted
        # and htmx swaps a full document into the flip card. No alert here
        # either: the generation that armed the cooldown already fired one,
        # and re-alerting on every suppressed request is how an alert channel
        # becomes noise nobody reads.
        # Body only — _reading_error_fragment supplies the heading from
        # is_rate, so passing the full sentence printed it twice on the card.
        _cool_msg = t(lang, "rashifal_card_cool_msg")
        if is_htmx:
            return HTMLResponse(
                _reading_error_fragment(canonical_slug, True, _cool_msg, lang),
                status_code=503,
            )
        return _no_cdn_cache(templates.TemplateResponse(
            request, "error.html",
            # lang, like the generation-failure branch below. rashifal.py has
            # THREE English-only degraded exits and QA round 2 fixed only one;
            # this is the most reachable of the three, because
            # _REGEN_COOLDOWN_S = 300 sends every request for this rashi+lang
            # here for five minutes after a single gate failure (QA 2026-10-04).
            {"title": t(lang, "rashifal_not_ready_title"),
             "message": t(lang, "rashifal_not_ready_msg"),
             "lang": lang},
            status_code=503,
        ))

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
            # NEVER STORE A VALUE THE READ GATE WILL REJECT.
            #
            # providers.chat gates `raw`; this stores sections[0][1]. When raw
            # passes and the first section does not, the read gate above
            # discards it, we regenerate, store the same failing value, and
            # repeat — one live LLM call per pageview, all day, per rashi. The
            # #215 fix would have traded a bounded content defect (a blank
            # served all day, zero LLM calls) for an unbounded cost defect, on
            # the quota that caused a 21-day outage.
            #
            # Triggered by the model emitting more than one `## ` heading, or a
            # body landing in the narrow band between the raw and section
            # lengths. _shared_three_tier cannot loop this way because it gates
            # and stores the SAME value; this path did not.
            ok, reason = llm_providers.passes_quality(reading_body, "rashifal_single")
            if not ok:
                _regen_fail(cache_key)
                raise RuntimeError(
                    f"generated body failed the quality gate ({reason}) — "
                    f"raw was {len(raw)} chars, first section {len(reading_body)}"
                )
            daily_cache.put("rashifal_single", cache_key, {
                "body": reading_body,
                "rashi_slug": canonical_slug,
                "lang": lang,
            }, today_iso)
        except Exception as err:
            log.exception("rashifal single-rashi generation failed for %s", canonical_slug)
            _fire_error_alert(request, err, f"rashifal_single:{canonical_slug}")
            _title, _msg = _llm_error_friendly(err, lang)
            if is_htmx:
                # Fragment path — return a card-shaped retry block, not the
                # generic 'safe to re-submit your input' message (there is
                # no form to re-submit here; a card flip). Give a clear
                # retry button that re-fires HTMX + a link to the full
                # standalone page as a fallback.
                is_rate = isinstance(err, AllProvidersExhausted)
                fragment_html = _reading_error_fragment(
                    canonical_slug, is_rate,
                    t(lang, "rashifal_card_rate_msg") if is_rate else _msg,
                    lang,
                )
                return HTMLResponse(
                    fragment_html,
                    status_code=503 if is_rate else 502,
                )
            return templates.TemplateResponse(
                request, "error.html",
                {"title": _title, "message": _msg, "lang": lang},
                status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
            )

    # Common template context.
    from astro_ai.llm import _RASHI_ANCHORS
    anchor = _RASHI_ANCHORS[idx]
    # The fragment's "open full page" link AND its WhatsApp share URL are both
    # built from this (_rashifal_card_content.html). Hardcoded to
    # /rashifal/{slug}, the Hindi card served from /hi/rashifal's tiles carried
    # a Hindi reading whose two links both ejected the reader to English, and
    # shared the English URL. The #124 change that made those tiles fetch
    # Hindi is what created that path (QA 2026-10-04).
    #
    # Keyed on the PATH via _lang_prefix, not on `lang == "hi"` alone. With a
    # `hi` cookie the ENGLISH url renders Hindi too, and that page's permalink
    # must stay English because that is the URL it is published at.
    #
    # The comment here used to claim exactly this while the code below it did
    # the opposite — so at /rashifal/aries with a `hi` cookie the fragment's
    # permalink was /hi/rashifal/aries while the full page's self_path was
    # /rashifal/aries, two parts of one page disagreeing about its own URL.
    # Benign for readers, and the same split _lang_prefix's path condition
    # exists to prevent (QA 2026-10-04).
    permalink = f"/rashifal/{canonical_slug}"
    if _lang_prefix(lang, request.url.path):
        permalink = hindi_pages.hindi_url(permalink) or permalink

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
        "permalink": permalink,
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
