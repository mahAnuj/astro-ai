"""Vimshottari Dasha — the period timeline and its long-form reading (issue #154).

Owns:
    GET /dasha            the Mahadasha/Antardasha timeline for the active chart,
                          falling back to an indexable landing page when no chart
                          cookie is set (SEO audit #123)
    GET /dasha/deep-dive  personalised LLM reading of the current period pair,
                          cached per (chart fingerprint, antardasha)

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from astro_ai import cache
from astro_ai.chart import ChartError, compute_chart, compute_dasha_state
from astro_ai.llm import generate_dasha_deep_dive, parse_sectioned_reading
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import DASHA_DEEP_DIVE_PROMPT_PATH, _lang, templates
from astro_ai.routes.llm_support import _cached, _fire_error_alert, _llm_error_friendly
from astro_ai.session import load_collection

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dasha", response_class=HTMLResponse)
async def dasha(request: Request) -> HTMLResponse:
    """Vimshottari Dasha timeline for the active saved chart.

    Same landing/result split as /kundli (SEO audit #123). When no chart
    cookie is set, render the /dasha explainer + birth-form so Googlebot
    has an indexable page. The old redirect-to-home meant /dasha had zero
    SEO presence.
    """
    saved = load_collection(request).active
    if saved is None:
        return templates.TemplateResponse(
            request, "dasha_landing.html",
            {"lang": _lang(request)},
        )
    saved_details = saved.to_birth_details()
    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    return templates.TemplateResponse(
        request,
        "dasha.html",
        {
            "details": saved_details,
            "natal": natal,
            "dasha": compute_dasha_state(natal),
            "lang": _lang(request),
        },
    )


@router.get("/dasha/deep-dive", response_class=HTMLResponse)
async def dasha_deep_dive(request: Request) -> HTMLResponse:
    """Long-form personalised reading of the current Mahadasha + Antardasha.

    Goes deeper than the timeline at /dasha: looks at where the period
    lords actually sit in this seeker's chart, explains the interaction,
    forecasts the next Antardasha, and lists remedies tied to the current
    Antardasha lord. Cached by (chart fingerprint, antardasha id) so we
    only burn an LLM call once per active Antardasha — periods last weeks
    to months so this is heavily reused.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=dasha", status_code=303)
    saved_details = saved.to_birth_details()
    try:
        natal = compute_chart(saved_details.birth_date, saved_details.birth_time, saved_details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    dasha = compute_dasha_state(natal)
    lang = _lang(request)

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured",
             "message": "Add OPENAI_API_KEY (or set up BHAGYA_LLM_PROVIDERS) before generating readings."},
            status_code=503,
        )

    # Cache key: chart fingerprint + antardasha start (changes when antardasha
    # rolls over) + prompt fingerprint (changes when we tune the prompt) + lang.
    chart_fp = cache.fingerprint_chart(
        saved_details.birth_date, saved_details.birth_time, saved_details.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(DASHA_DEEP_DIVE_PROMPT_PATH)
    antar_id = f"{dasha.antardasha.lord}-{dasha.antardasha.start.isoformat()}"
    cache_key = f"dasha_deep_dive:{chart_fp}:{antar_id}:{prompt_fp}:{lang}"

    try:
        text = _cached(
            cache_key=cache_key,
            route="dasha_deep_dive",
            lang=lang,
            ttl_days=None,  # never expire on its own — antar_id in key handles invalidation
            call_fn=lambda: generate_dasha_deep_dive(
                chart=natal, dasha=dasha,
                prompt_path=DASHA_DEEP_DIVE_PROMPT_PATH, lang=lang,
            ),
        )
    except Exception as err:
        log.exception("dasha deep dive LLM generation failed")
        _fire_error_alert(request, err, "dasha")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": _title, "message": _msg},
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    sections = parse_sectioned_reading(text)
    return templates.TemplateResponse(
        request,
        "dasha_deep_dive.html",
        {
            "details": saved_details,
            "natal": natal,
            "dasha": dasha,
            "sections": sections,
            "lang": lang,
        },
    )
