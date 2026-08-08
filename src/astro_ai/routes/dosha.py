"""Standalone dosha checkers (issue #154).

Owns:
    GET/POST /manglik-check      Manglik Dosh (issue #109)
    GET/POST /sade-sati-check    Sade Sati report (issue #110)
    GET/POST /kaal-sarp-check    Kaal Sarp geometry (issue #111)

plus the three helpers the six routes share: ``_dosha_form_ctx``,
``_prefill_from_cookie`` and ``_dosha_details_from_form``.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from astro_ai import notify
from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_kaal_sarp,
    compute_manglik_details,
    compute_sade_sati_details,
)
from astro_ai.llm import BirthDetails
from astro_ai.routes.deps import _lang, _save_collection_synced, templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import load_collection, load_user

router = APIRouter()


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
                    error: str | None = None,
                    show_ksy_caveat: bool = False) -> dict:
    """Shared context for the dosha_check_form.html template.

    `show_ksy_caveat` renders the Kaal Sarp classical-source honesty
    partial above the form — used by /kaal-sarp-check so users see the
    caveat before entering their birth details, not just after submit.
    """
    return {
        "page_title": page_title,
        "page_lead": page_lead,
        "form_action": form_action,
        "submit_label": submit_label,
        "page_meta_description": meta_desc,
        "prefill": prefill,
        "error": error,
        "show_ksy_caveat": show_ksy_caveat,
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


@router.get("/manglik-check", response_class=HTMLResponse)
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


@router.post("/manglik-check", response_class=HTMLResponse)
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


@router.get("/sade-sati-check", response_class=HTMLResponse)
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


@router.post("/sade-sati-check", response_class=HTMLResponse)
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


@router.get("/kaal-sarp-check", response_class=HTMLResponse)
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
            show_ksy_caveat=True,
        ),
    )


@router.post("/kaal-sarp-check", response_class=HTMLResponse)
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
                page_title="Kaal Sarp geometry check — honest, classical-source-checked",
                page_lead="Detect the Kaal Sarp geometry in your chart (all seven non-shadow planets on one side of the Rahu-Ketu axis) with a transparent note about where this classification actually comes from — it is not defined in the classical Sanskrit Jyotish texts we cite elsewhere on this site.",
                form_action="/kaal-sarp-check",
                submit_label="Check the geometry →",
                meta_desc="Honest Kaal Sarp Yoga check with classical-source transparency.",
                prefill={"name": name, "birth_date": birth_date, "birth_time": birth_time, "birth_place": birth_place},
                error=str(err),
                show_ksy_caveat=True,
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


