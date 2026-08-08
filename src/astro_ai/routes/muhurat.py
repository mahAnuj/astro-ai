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

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from astro_ai import notify
from astro_ai.chart import compute_chart
from astro_ai.routes.deps import _lang, templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import load_collection, load_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/muhurat/{event_slug}", response_class=HTMLResponse)
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


@router.get("/muhurat", response_class=HTMLResponse)
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
