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
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Form, HTTPException, Query, Request
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
# Allow-list, not "every event but X": a new event type is opt-in. Four are the events whose rules
# #1058 sourced; vivah joined in #1017 (slice 8) on the auditor's ruling, with a disclosure in the
# template. The list is the finder's own verdict for every event: an interim vivah-only filter of
# Abujha rows lived here until #1346 made Abujha a booster after the exclusions.
LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business", "vivah"})
LANDING_CITY = "New Delhi, India"
# 90 days, not 60: measured on 2026-11-21, 60 days gave `business` exactly five auspicious dates
# with no slack, and 90 gave 11 (griha_pravesh 16, vidyarambh 21, namkaran 19). Compute is ~0.15 s.
LANDING_WINDOW_DAYS = 90
LANDING_SHOW = 5
LANDING_TTL_S = 86400.0

# Shareable GET result (#1336, slice 5 of #1017). A city longer than this is refused before any
# geocode: it becomes an unauthenticated GET that spends a Nominatim lookup on whatever string a
# link carries, and no real place name is near it.
CITY_MAX_CHARS = 100
# R8: when a search finds no auspicious date, scan forward in chunks of this many days, stopping at
# the first chunk with one. Chunked rather than one 365-day call because the common answer is in
# the first chunk (~0.1 s) and one 365-day call is ~0.6 s every time.
NEXT_DATE_CHUNK_DAYS = 60
# "Up to the existing 365-day cap" (#1336) read as 365 days PAST the searched window, not 365 days
# from its start: a 180-day search that found nothing is not told "none in 365 days" after 185.
NEXT_DATE_HORIZON_DAYS = 365


def _share_url(event_type: str, city: str, start: date, days: int) -> str:
    """The GET URL that reproduces one basic-mode search. Absolute, so it survives being pasted.

    `quote`, not `quote_plus`, so a space is %20 and a `&`, `#` or `+` in a city cannot end the
    value. Only these four fields exist in a basic search; personal, couple and Namkaran inputs
    never reach this function, and the route never calls it for a search that used them.
    """
    query = urlencode({"event": event_type, "city": city, "start": start.isoformat(),
                       "days": days}, quote_via=quote)
    return f"{templates.env.globals['site_url']}/muhurat?{query}"


def _next_auspicious_date(event_type: str, city: str, after: date) -> tuple[date | None, date]:
    """The first auspicious date on or after `after`, and the last date scanned.

    Blocking (ephemeris), so it runs in the worker thread that ran the search. Scans 60-day chunks
    until one holds an auspicious row or NEXT_DATE_HORIZON_DAYS have been read. Rows come back
    best-tier-first, so the answer is the EARLIEST auspicious row in the chunk, never `[0]`: that
    would name the best-rated date of the chunk, possibly 50 days after a nearer one. Rating does
    not depend on a chart (personal and couple factors are annotations), so none is passed.
    """
    from astro_ai import muhurat as _muhurat

    end = after + timedelta(days=NEXT_DATE_HORIZON_DAYS)  # exclusive
    cursor = after
    while cursor < end:
        span = min(NEXT_DATE_CHUNK_DAYS, (end - cursor).days)
        chunk = _muhurat.find_candidates(event_type, city, cursor, span)
        hits = [c.d for c in chunk if c.rating in _muhurat.AUSPICIOUS_RATINGS]
        if hits:
            return min(hits), cursor + timedelta(days=span - 1)
        cursor += timedelta(days=span)
    return None, end - timedelta(days=1)


def _search(event_type: str, city: str, start: date, days: int, personal_chart,
            bride_chart, groom_chart):
    """The whole blocking half of a search: the finder, then R8's scan on the zero path.

    One synchronous function so ONE run_in_threadpool hop covers both. `find_candidates` is read
    as a module attribute so a test that patches it applies. Returns (candidates, next_date,
    scanned_until); the last two are None when the window held an auspicious date.
    """
    from astro_ai import muhurat as _muhurat

    candidates = _muhurat.find_candidates(
        event_type, city=city, start=start, days=days,
        personal_chart=personal_chart,
        bride_chart=bride_chart, groom_chart=groom_chart,
    )
    # Same definition as the template's headline: muhurat.AUSPICIOUS_RATINGS, read as an attribute so
    # it is one set and not a copy; caution is not "found".
    if not candidates or any(c.rating in _muhurat.AUSPICIOUS_RATINGS for c in candidates):
        return candidates, None, None
    try:
        next_date, scanned_until = _next_auspicious_date(
            event_type, city, start + timedelta(days=len(candidates)))
    except Exception:  # noqa: BLE001
        # The answer is already computed; a failed look-ahead must not turn it into a 500.
        log.warning("muhurat next-date scan failed for %s", event_type, exc_info=True)
        return candidates, None, None
    return candidates, next_date, scanned_until


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
async def muhurat_finder_form(
    request: Request,
    # Shareable result (#1336, R7 of #1017). Only the four inputs a basic search has; every other
    # query parameter is ignored, so personal, couple and Namkaran modes are impossible here by
    # construction. Strings, so a bad value reaches the same 400 a POST gives, not a 422.
    event: str = Query("vivah"),
    city: str = Query(""),
    start: str = Query(""),
    days: int = Query(60),
) -> HTMLResponse:
    """Muhurat Finder (Issue #108) — 5 classical event types with optional
    personal-chart matching (Tara Bala + Chandra Bala + Sade Sati + Dasha
    caution when a saved chart is in session).

    With `city` and `start` it is the equivalent of the basic-mode POST (#1336), so a result has
    a URL that can be sent to someone. Without both it is the bare form, as ever.
    """
    if city.strip() and start.strip():
        return await _finder_response(
            request, event_type=event, city=city, start_date=start, days=days, via_get=True)
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


async def _finder_response(
    request: Request,
    *,
    event_type: str,
    city: str,
    start_date: str,
    days: int,
    use_personal: str = "",
    bride_name: str = "",
    bride_dob: str = "",
    bride_time: str = "",
    bride_place: str = "",
    groom_name: str = "",
    groom_dob: str = "",
    groom_time: str = "",
    groom_place: str = "",
    child_dob: str = "",
    child_time: str = "",
    child_place: str = "",
    via_get: bool = False,
) -> HTMLResponse:
    """The search behind both POST /muhurat and the shareable GET /muhurat?... (#1336).

    A plain function, not the POST route called from GET: calling the route would leak its
    `Form(...)` defaults (a `Form("")` object is truthy) into every optional field. GET passes only
    event, city, start and days, so every optional field here keeps its "" default.
    `via_get` changes four things and nothing about the dates: the page is noindex with a canonical
    to the event landing, no `notify.muhurat_computed`, no `muhurat_searched` event, and a bad
    city does not page the owner (a crawler or a typo in a shared link is not an outage).
    """
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
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal,
             "via_get": via_get},
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
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal,
             "via_get": via_get},
            status_code=400,
        )
    # Before any geocode: personal mode below and find_candidates both resolve this string.
    if len(city) > CITY_MAX_CHARS:
        return templates.TemplateResponse(
            request, "muhurat_finder.html",
            {"candidates": None, "error": "City is too long.", "lang": _lang(request),
             "prefill_city": city[:CITY_MAX_CHARS], "prefill_start": start_date,
             "event_types": event_types, "selected_event": event_type,
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal,
             "via_get": via_get},
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
        # ONE threadpool hop for the finder and, on the zero path, R8's scan: both are blocking
        # ephemeris work and must not stall the event loop (the #144 shape).
        candidates, next_date, scanned_until = await run_in_threadpool(
            _search, event_type, city, start, int(days),
            personal_chart, bride_chart, groom_chart)
    except Exception as err:  # noqa: BLE001
        if via_get and isinstance(err, ValueError):
            # find_candidates raises ValueError for a city it cannot geocode: a user's typo in a
            # link anyone can craft, not an outage. Anything else still alerts.
            log.warning("muhurat GET: %s", err)
        else:
            _fire_error_alert(request, err, f"muhurat:compute:{event_type}")
        return templates.TemplateResponse(
            request, "muhurat_finder.html",
            {"candidates": None, "error": f"Could not compute muhurats: {err}",
             "lang": _lang(request), "prefill_city": city, "prefill_start": start_date,
             "event_types": event_types, "selected_event": event_type,
             "has_saved_chart": has_saved_chart, "use_personal": wants_personal,
             "via_get": via_get},
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
    # A GET fires neither this nor muhurat_searched (#1336): a link is crawlable and forwardable, so
    # counting its renders would turn the owner's Telegram into a bot meter and move the #1217 and
    # #1218 baselines, which count form submissions. Cost: a person who opens a shared link emits no
    # search event; share-link landings are read from GA4 landing pages instead.
    if not via_get:
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
    muhurat_searched = None if via_get else {
        "event_type": event_type, "days": len(candidates),
        "valid_count": sum(1 for c in candidates if c.rating != "avoid"),
        "mode": analytics_mode,
    }
    # The share link and the next-date link exist only for a basic search: the four fields they
    # carry are the whole of its input. In personal, couple and Namkaran mode the result depends on
    # birth data that must never be put in a URL, so there is no link and the date is plain text.
    # `days` is len(candidates), the clamped value, so the link reproduces what was searched.
    basic = analytics_mode == "basic"
    share_url = _share_url(event_type, city, start, len(candidates)) if basic else ""
    next_valid = None
    if next_date is not None:
        next_valid = {
            "d": next_date, "weekday": next_date.strftime("%A"),
            "link": _share_url(event_type, city, next_date, len(candidates)) if basic else ""}
    return templates.TemplateResponse(
        request, "muhurat_finder.html",
        {"candidates": candidates, "city": city, "start_date": start_date,
         "muhurat_searched": muhurat_searched, "via_get": via_get,
         "share_url": share_url, "next_valid": next_valid,
         "scanned_until": scanned_until if next_date is None else None,
         "next_scan_days": NEXT_DATE_HORIZON_DAYS,
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
    return await _finder_response(
        request, event_type=event_type, city=city, start_date=start_date, days=days,
        use_personal=use_personal,
        bride_name=bride_name, bride_dob=bride_dob, bride_time=bride_time, bride_place=bride_place,
        groom_name=groom_name, groom_dob=groom_dob, groom_time=groom_time, groom_place=groom_place,
        child_dob=child_dob, child_time=child_time, child_place=child_place,
    )
