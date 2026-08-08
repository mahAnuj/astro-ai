"""Today's personalised reading (issue #154).

Owns:
    GET /today   the day's LLM reading for the active saved chart, keyed on
                 chart fingerprint + date + language + prompt fingerprint

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import os
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from astro_ai import cache
from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_gochar_impacts,
    compute_panchang,
    compute_transit_snapshot,
    compute_vedic_flags,
)
from astro_ai.llm import generate_daily_reading
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    DAILY_PROMPT_PATH,
    _lang,
    _pretty_date,
    templates,
)
from astro_ai.routes.llm_support import _cached, _fire_error_alert, _llm_error_friendly
from astro_ai.session import load_collection

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/today", response_class=HTMLResponse)
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
        log.exception("today's outlook LLM generation failed")
        _fire_error_alert(request, err, "today")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": _title,
                "message": _msg,
            },
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
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
            "today_pretty": _pretty_date(date.today().isoformat(), lang),
            "lang": lang,
        },
    )
