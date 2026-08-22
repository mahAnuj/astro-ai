"""Homepage (issue #154).

Owns:
    GET /   the homepage — form for new visitors, chart list for returning ones

The Panchang-strip day cache used to live here. It is now
``routes/deps.py:panchang_strip_for_city`` — the rashifal pages need the same
windows, and one cache shared beats two that drift.

This is the #144 hot path — 32 GCS reads → 0, ~19.9s → ~5ms. Four invariants
this module exists to protect:

1. ``index`` is a plain ``def``, NOT ``async def``. It does blocking I/O and
   contains no ``await``, so Starlette runs it on the threadpool; as a
   coroutine one slow homepage stalled every other request on the instance.
2. The Panchang-strip day cache is defined in ONE place and nowhere else.
   Two dicts would mean the reader's stays empty forever and the strip
   recomputes on every request while every GCS counter still reads zero —
   invisible to ``scripts/perf_homepage.py``. It moved to ``routes/deps.py``
   as ``panchang_strip_for_city`` when the rashifal pages became a second
   consumer; the invariant is unchanged, only its address. Import it, never
   re-implement it.
3. ``trust_bar`` is imported at MODULE level, never inside ``index``.
4. This module must NOT import ``astro_ai.storage``, ``astro_ai.events``,
   ``astro_ai.users`` or ``astro_ai.subscribers``. ``index`` only ever reaches
   them through ``trust_bar``'s memoised, stale-while-revalidate path; a direct
   import here is how a per-request GCS round-trip creeps back onto the
   homepage.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from astro_ai import trust_bar
from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
from astro_ai.routes.deps import _lang, _no_cdn_cache, panchang_strip_for_city, templates
from astro_ai.session import load_collection

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, needs_chart: str | None = None) -> HTMLResponse:
    """Form for new visitors, chart-list + form for returning seekers.

    `?needs_chart=<feature>` is set when other routes redirect here because
    no saved chart exists yet. We surface a brief banner naming the feature
    the seeker tried to reach, so the redirect isn't silent.

    Deliberately a plain `def`, not `async def` (issue #144): the body does
    blocking I/O and contains no `await`, so Starlette runs it in a worker
    thread instead of on the single event loop this container has. As an
    `async def` one slow homepage stalled every other request on the
    instance — a static `GET /sw.js` was measured at 55s behind it.
    """
    collection = load_collection(request)
    # Trust-bar counts + thresholds live in astro_ai.trust_bar. The counts are
    # cached per process (stale-while-revalidate), so this call makes zero GCS
    # requests in steady state and never blocks; see that module for why zeros
    # are the safe default.
    _trust = trust_bar.counts()
    _trust_min = trust_bar.minimums()
    # Panchang strip for the homepage masthead (user's request — always
    # visible without click-away). Cached daily per city via
    # _homepage_panchang_cached — after first computation for a given
    # (date, city) pair the same instance serves subsequent homepage
    # loads with no LLM, no geocode, no swiss-ephemeris compute.
    _city_pref = "Mumbai, India"
    if collection.active and collection.active.birth_place:
        _city_pref = collection.active.birth_place
    _panchang_strip, _panchang_moon, _panchang_city = panchang_strip_for_city(_city_pref)
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
            # Trust bar counts — templates ALSO check the *_min companions
            # so a pill only renders when count >= min. Simpler than passing
            # a pre-gated bool because the template can format the number
            # with commas and pluralization directly.
            "trust_users": _trust["users"],
            "trust_users_min": _trust_min["users"],
            "trust_subscribers": _trust["subscribers"],
            "trust_subscribers_min": _trust_min["subscribers"],
            "trust_kundlis": _trust["kundlis"],
            "trust_kundlis_min": _trust_min["kundlis"],
            "trust_asks": _trust["asks"],
            "trust_asks_min": _trust_min["asks"],
            "panchang_strip": _panchang_strip,
            "panchang_moon": _panchang_moon,
            "panchang_city": _panchang_city.split(",")[0] if _panchang_city else "",
            "user_moon_slug": _user_moon_slug,
            "user_moon_display": _user_moon_display,
        },
    ))


