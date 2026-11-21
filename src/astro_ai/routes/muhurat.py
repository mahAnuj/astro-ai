"""Muhurat Finder — auspicious-window search (issue #154).

Owns:
    GET  /muhurat/{event_slug}  per-event evergreen landing page (issue #108)
    GET  /muhurat               the finder form
    POST /muhurat               the candidate search, with optional personal
                                chart, couple (Vivah) and Namkaran modes

Registration order matters: ``/muhurat/{event_slug}`` is declared BEFORE
``/muhurat`` here exactly as it was in ``main.py``.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``).

NOTE on imports: this module is ``astro_ai.routes.muhurat`` and shadows the
real ``astro_ai.muhurat``. Every import here — including the function-local
``from astro_ai import muhurat as _muhurat`` and
``from astro_ai.muhurat import EVENT_RULES, EVENT_LANDING`` — must therefore
stay ABSOLUTE. A relative import would resolve to this module and fail as a
confusing AttributeError rather than an ImportError. Nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from astro_ai import chart as _chart
from astro_ai import hot_cache, notify
from astro_ai.chart import compute_chart, reading_today
from astro_ai.routes.deps import _lang, _no_cdn_cache, templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import load_collection, load_user

log = logging.getLogger(__name__)

router = APIRouter()

# Landing pages show the next auspicious dates for one fixed city (#1325, slice 6 of #1017).
# Allow-list, not "every event but vivah": a new event type is opt-in. The four are the events
# whose rules #1058 sourced; vivah stays as it was until #1026.
LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business"})
LANDING_CITY = "New Delhi, India"
# 90 days, not 60: measured on 2026-11-21, 60 days gave `business` exactly five auspicious dates
# with no slack, and 90 gave 11 (griha_pravesh 16, vidyarambh 21, namkaran 19). Compute is ~0.15 s.
LANDING_WINDOW_DAYS = 90
LANDING_SHOW = 5
LANDING_TTL_S = 86400.0


def _landing_upcoming(event_key: str, today: date) -> dict | None:
    """The next auspicious dates for one event, from the finder itself (never typed in).

    Runs in a worker thread (blocking: ephemeris plus one Nominatim geocode per process) and is
    cached by the caller. Returns a small plain dict, not the candidates: their choghadiya tables
    are dead weight on a landing page. `None` when the window holds no auspicious date.

    The five EARLIEST auspicious dates, printed in date order. `find_candidates` returns its rows
    best-tier-first, so reading "the finder's order" literally would list the five best-rated dates
    of the window, possibly 80 days out; this page is headed "next", so it sorts by date, which is
    the finder's own tie-break inside a tier (#1325).
    """
    from astro_ai import muhurat as _muhurat
    from astro_ai.muhurat import AUSPICIOUS_RATINGS

    rows = _muhurat.find_candidates(event_key, LANDING_CITY, today, LANDING_WINDOW_DAYS)
    # Read after find_candidates so it is an lru hit, and raise (section omitted) rather than
    # cache a result that cannot name its zone.
    zone = _chart.geocode_place(LANDING_CITY)[2]
    upcoming = sorted((c for c in rows if c.rating in AUSPICIOUS_RATINGS), key=lambda c: c.d)
    if not upcoming:
        return None
    today_tomorrow = []
    if event_key == "griha_pravesh":
        # Same rows as the list: the window starts today, so no second computation.
        by_date = {c.d: c for c in rows}
        for d in (today, today + timedelta(days=1)):
            c = by_date.get(d)
            if c is not None:
                today_tomorrow.append({
                    "d": c.d, "weekday": c.weekday, "rating": c.rating,
                    "valid": c.rating in AUSPICIOUS_RATINGS, "reason": c.reason})
    return {
        "city": LANDING_CITY, "zone": zone, "computed": today, "days": LANDING_WINDOW_DAYS,
        "dates": [{"d": c.d, "weekday": c.weekday, "tithi": c.tithi, "paksha": c.tithi_paksha,
                   "nakshatra": c.nakshatra, "rating": c.rating}
                  for c in upcoming[:LANDING_SHOW]],
        "today_tomorrow": today_tomorrow,
    }


@router.get("/muhurat/{event_slug}", response_class=HTMLResponse)
async def muhurat_landing(request: Request, event_slug: str) -> HTMLResponse:
    """Per-event Muhurat landing page (Issue #108).

    /muhurat/vivah, /muhurat/griha-pravesh, /muhurat/namkaran, /muhurat/vidyarambh,
    /muhurat/business. Renders evergreen classical intro + embedded finder form
    pre-selected to the event type. Slug (with hyphens) maps to EVENT_RULES key
    (with underscores) via replace.
    """
    from astro_ai.muhurat import EVENT_RULES, EVENT_LANDING
    # Accept both hyphenated URL slugs and underscored keys for robustness.
    event_key = event_slug.replace("-", "_")
    landing = EVENT_LANDING.get(event_key)
    rules = EVENT_RULES.get(event_key)
    if landing is None or rules is None:
        raise HTTPException(status_code=404, detail=f"Unknown event type: {event_slug}")
    saved = load_collection(request).active
    prefill_city = saved.birth_place if saved else ""
    today = reading_today()  # read once: the cache key and the window must name the same IST day
    upcoming = None
    if event_key in LANDING_DATES_EVENTS:
        try:
            # get_or_compute, not get_or_refresh: a cold key would hand the first visitor (and a
            # crawler) no list, which is the page this exists to improve. The IST day is in the
            # KEY, so rollover needs no TTL; date.today() is UTC on Cloud Run and lags 5.5 h (#794).
            upcoming = await run_in_threadpool(
                hot_cache.get_or_compute,
                f"muhurat:landing:{event_key}:{today.isoformat()}", LANDING_TTL_S,
                lambda: _landing_upcoming(event_key, today))
        except Exception:
            # A panel must never 500 the page. No _fire_error_alert: a public crawled page and a
            # Nominatim hiccup would page the owner repeatedly; hot_cache collapses repeats.
            log.warning("muhurat landing dates unavailable for %s", event_key, exc_info=True)
            upcoming = None
    # The page now names today and tomorrow, so it is date-dependent (see _no_cdn_cache).
    return _no_cdn_cache(templates.TemplateResponse(
        request, "muhurat_landing.html",
        {"landing": landing, "event_key": event_key,
         "event_label": rules["label"],
         "prefill_city": prefill_city,
         "prefill_start": today.isoformat(),
         "has_saved_chart": saved is not None,
         "upcoming": upcoming,
         "lang": _lang(request)},
    ))


@router.get("/muhurat", response_class=HTMLResponse)
async def muhurat_finder_form(request: Request) -> HTMLResponse:
    """Muhurat Finder (Issue #108) — 5 classical event types with optional
    personal-chart matching (Tara Bala + Chandra Bala + Sade Sati + Dasha
    caution when a saved chart is in session).
    """
    from astro_ai.muhurat import EVENT_RULES
    saved = load_collection(request).active
    prefill_city = saved.birth_place if saved else ""
    event_types = [(k, v["label"]) for k, v in EVENT_RULES.items()]
    return templates.TemplateResponse(
        request, "muhurat_finder.html",
        {"candidates": None, "error": None, "lang": _lang(request),
         "prefill_city": prefill_city,
         "prefill_start": reading_today().isoformat(),
         "event_types": event_types,
         "selected_event": "vivah",
         "has_saved_chart": saved is not None,
         "use_personal": False},
    )


@router.post("/muhurat", response_class=HTMLResponse)
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
    child_alternate_letters: tuple[str, ...] = ()
    child_nakshatra = ""
    child_pada = 0
    if event_type == "namkaran" and child_dob and child_time and child_place:
        try:
            child_chart = compute_chart(child_dob, child_time, child_place)
            child_nakshatra, child_pada = _muhurat._child_moon_pada(child_chart)
            child_first_letter, child_all_letters = _muhurat._namkaran_first_letters(child_nakshatra, child_pada)
            child_alternate_letters = _muhurat._namkaran_alternate_letters(child_nakshatra)
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
    # The zone the finder's clock times are local to (#1322, #1017 R5). find_candidates already
    # geocoded this city (lru_cached), so this is a cache hit, not a second lookup. Module
    # attribute access, not a from-import, so a test that patches chart.geocode_place applies.
    # "" means the page omits the line rather than guess a zone.
    try:
        search_tz = _chart.geocode_place(city)[2]
    except Exception:  # noqa: BLE001
        search_tz = ""
    try:
        _u = load_user(request)
        # Every non-avoid date, caution included. The page headline now counts only
        # excellent/good/acceptable (#1322), so this deliberately differs from it: it keeps the
        # #1218 baseline meaning rather than silently moving it.
        _good_count = sum(1 for c in candidates if c.rating != "avoid")
        notify.muhurat_computed(
            event_type=event_label, city=city, days_range=int(days),
            good_count=_good_count,
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    # muhurat_searched (#1217, #1017 F1): enums and integers only. `mode` is
    # which optional input drove the result, one value. They can overlap (vivah +
    # personal + couple), so the order is fixed: the most specific input wins.
    # Namkaran means the child's chart was computed, not merely that event_type is
    # namkaran (event_type is its own param). `days` is what was searched, as the
    # page's own "N-day search" line counts it; `valid_count` is the non-avoid dates. Since #1322
    # the headline counts only excellent/good/acceptable, so valid_count >= headline: caution
    # dates stay in valid_count to keep the #1218 baseline meaning.
    analytics_mode = ("couple" if (bride_chart is not None and groom_chart is not None)
                      else "namkaran" if child_first_letter
                      else "personal" if personal_chart is not None
                      else "basic")
    muhurat_searched = {
        "event_type": event_type, "days": len(candidates),
        "valid_count": sum(1 for c in candidates if c.rating != "avoid"),
        "mode": analytics_mode,
    }
    return templates.TemplateResponse(
        request, "muhurat_finder.html",
        {"candidates": candidates, "city": city, "start_date": start_date,
         "muhurat_searched": muhurat_searched,
         "search_tz": search_tz,
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
         "child_alternate_letters": child_alternate_letters,
         "child_nakshatra": child_nakshatra,
         "child_pada": child_pada,
         "lang": _lang(request)},
    )
