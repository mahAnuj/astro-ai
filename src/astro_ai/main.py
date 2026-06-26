"""FastAPI app — form, natal reading, today's transits, cookie-persisted seeker."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_gochar_impacts,
    compute_manglik_details,
    compute_marriage_profile,
    compute_panchang,
    compute_sade_sati_details,
    compute_transit_snapshot,
    compute_vedic_flags,
    compute_wealth_profile,
)
from astro_ai.i18n import translate as _i18n_translate
from astro_ai.llm import (
    BirthDetails,
    generate_daily_reading,
    generate_outlook_reading,
    generate_reading,
    parse_sectioned_reading,
)
from astro_ai.matching import compute_guna_milan
from astro_ai.session import (
    ChartCollection,
    clear_collection,
    load_collection,
    save_collection,
)

# Language preference is stored in its own cookie (separate from the chart
# collection — it's a UI/reading-output preference, not chart data).
LANG_COOKIE = "astro_ai_lang"
SUPPORTED_LANGS = {"en", "hi"}


def _lang(request: Request) -> str:
    """Read the seeker's language preference cookie; defaults to English."""
    candidate = request.cookies.get(LANG_COOKIE, "en")
    return candidate if candidate in SUPPORTED_LANGS else "en"

# override=True so .env edits actually take effect when uvicorn reloads —
# otherwise the first-loaded values stick for the lifetime of the process
# and editing .env feels silently broken.
load_dotenv(override=True)

# Project layout: src/astro_ai/main.py → templates and production prompts live
# alongside the code. The sibling `evals/` folder is the prompt-evaluation
# sub-project (separate concern, not a runtime dependency).
HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
PROMPTS_DIR = HERE / "prompts"
PROMPT_PATH = PROMPTS_DIR / "natal.txt"
DAILY_PROMPT_PATH = PROMPTS_DIR / "daily.txt"
MONTHLY_PROMPT_PATH = PROMPTS_DIR / "monthly.txt"
YEARLY_PROMPT_PATH = PROMPTS_DIR / "yearly.txt"

app = FastAPI(title="astro-ai", version="0.0.1")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Expose i18n to every template as `t(key, **kwargs)`. Templates pass the
# current `lang` (also injected per-request) into the call.
templates.env.globals["t"] = _i18n_translate


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Form for new visitors, chart-list + form for returning seekers."""
    collection = load_collection(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "collection": collection,
            "saved": collection.active,
            "lang": _lang(request),
        },
    )


@app.post("/reading", response_class=HTMLResponse)
async def reading(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> HTMLResponse:
    """Take the form submission, call the LLM, render the reading."""
    details = BirthDetails(
        name=name.strip(),
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place.strip(),
    )
    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "API key not configured",
                "message": (
                    "The server can't reach the LLM because OPENAI_API_KEY isn't set. "
                    "Copy .env.example to .env, paste your key, and the dev server will "
                    "pick it up on the next request."
                ),
            },
            status_code=503,
        )
    try:
        chart = compute_chart(
            birth_date=details.birth_date,
            birth_time=details.birth_time,
            place=details.birth_place,
        )
    except ChartError as err:
        # Most commonly a geocoding miss — surface as friendly form-level message.
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    try:
        reading_text = generate_reading(details, chart=chart, prompt_path=PROMPT_PATH)
    except Exception as err:  # upstream LLM error → friendly page, not stack trace
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate a reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
        )
    response = templates.TemplateResponse(
        request,
        "result.html",
        {"details": details, "reading": reading_text, "chart": chart},
    )
    # Append to the seeker's collection (or reactivate the matching saved chart).
    try:
        collection = load_collection(request).add(details)
    except ValueError as err:
        # Hit the chart-cap. Surface as friendly error rather than swallow.
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart limit reached", "message": str(err)},
            status_code=400,
        )
    save_collection(response, collection)
    return response


@app.get("/natal", response_class=HTMLResponse)
async def natal(request: Request) -> HTMLResponse:
    """Re-render the natal reading for the currently active saved chart."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/", status_code=303)
    return await _render_natal_for(request, saved.to_birth_details())


async def _render_natal_for(request: Request, details: BirthDetails) -> HTMLResponse:
    """Shared natal-reading renderer used by both GET /natal and POST /reading."""
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
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
    flags = compute_vedic_flags(chart)
    lang = _lang(request)
    try:
        reading_text = generate_reading(
            details, chart=chart, flags=flags, prompt_path=PROMPT_PATH, lang=lang
        )
    except Exception as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate a reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
        )
    sections = parse_sectioned_reading(reading_text)
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "details": details,
            "reading": reading_text,
            "sections": sections,
            "chart": chart,
            "flags": flags,
            "lang": lang,
            # Structured insight panels — see chart.py for shape.
            "marriage": compute_marriage_profile(chart),
            "wealth":   compute_wealth_profile(chart),
            "manglik":  compute_manglik_details(chart),
            "sade_sati":compute_sade_sati_details(chart),
        },
    )


@app.get("/today", response_class=HTMLResponse)
async def today(request: Request) -> HTMLResponse:
    """Today's personalised Vedic reading using the active saved chart."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/", status_code=303)
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

    try:
        reading_text = generate_daily_reading(
            saved_details,
            natal=natal,
            transit=transit,
            flags=flags,
            panchang=panchang,
            prompt_path=DAILY_PROMPT_PATH,
            lang=lang,
        )
    except Exception as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate today's reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
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
            "lang": lang,
        },
    )


@app.post("/lang")
async def set_lang(
    request: Request,
    lang: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Switch reading language; persisted in its own cookie."""
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    response = RedirectResponse(_safe_redirect_target(next), status_code=303)
    response.set_cookie(
        LANG_COOKIE,
        lang,
        max_age=60 * 60 * 24 * 365 * 5,  # 5 years
        httponly=False,  # readable from JS (purely a UI preference)
        samesite="lax",
        secure=False,
    )
    return response


@app.get("/monthly", response_class=HTMLResponse)
async def monthly(request: Request) -> HTMLResponse:
    """30-day outlook for the active saved chart."""
    return await _render_outlook(
        request,
        prompt_path=MONTHLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="monthly_title",
        title_anon_key="monthly_title_anon",
        subtitle_key="monthly_subtitle",
        reading_label_key="monthly_reading",
        window_label="30 days",
    )


@app.get("/yearly", response_class=HTMLResponse)
async def yearly(request: Request) -> HTMLResponse:
    """12-month outlook for the active saved chart."""
    return await _render_outlook(
        request,
        prompt_path=YEARLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="yearly_title",
        title_anon_key="yearly_title_anon",
        subtitle_key="yearly_subtitle",
        reading_label_key="yearly_reading",
        window_label="12 months",
    )


async def _render_outlook(
    request: Request,
    *,
    prompt_path: Path,
    template_name: str,
    title_key: str,
    title_anon_key: str,
    subtitle_key: str,
    reading_label_key: str,
    window_label: str,
) -> HTMLResponse:
    """Shared monthly/yearly renderer — same flow, different prompt + labels."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/", status_code=303)
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
    gochar_impacts = compute_gochar_impacts(natal)
    lang = _lang(request)

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "API key not configured",
                "message": "The server can't reach the LLM because OPENAI_API_KEY isn't set. Add it to .env and reload.",
            },
            status_code=503,
        )

    try:
        reading_text = generate_outlook_reading(
            saved_details,
            natal=natal,
            transit=transit,
            flags=flags,
            gochar_impacts=gochar_impacts,
            prompt_path=prompt_path,
            lang=lang,
        )
    except Exception as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "Couldn't generate the reading",
                "message": f"{type(err).__name__}: {err}",
            },
            status_code=502,
        )

    return templates.TemplateResponse(
        request,
        template_name,
        {
            "details": saved_details,
            "natal": natal,
            "transit": transit,
            "flags": flags,
            "gochar_impacts": gochar_impacts,
            "reading": reading_text,
            "lang": lang,
            "title_key": title_key,
            "title_anon_key": title_anon_key,
            "subtitle_key": subtitle_key,
            "reading_label_key": reading_label_key,
            "window_label": window_label,
            "today_date": date.today().isoformat(),
        },
    )


@app.get("/matching", response_class=HTMLResponse)
async def matching_form(request: Request) -> HTMLResponse:
    """Form for two seekers — collects birth details for both, no auth needed."""
    return templates.TemplateResponse(
        request,
        "matching.html",
        {"lang": _lang(request)},
    )


@app.post("/matching", response_class=HTMLResponse)
async def matching_result(
    request: Request,
    g_name: str = Form(default=""),
    g_birth_date: str = Form(...),
    g_birth_time: str = Form(...),
    g_birth_place: str = Form(...),
    b_name: str = Form(default=""),
    b_birth_date: str = Form(...),
    b_birth_time: str = Form(...),
    b_birth_place: str = Form(...),
) -> HTMLResponse:
    """Compute and render Ashtakoot Guna Milan for two charts."""
    lang = _lang(request)
    try:
        groom_chart = compute_chart(g_birth_date, g_birth_time, g_birth_place)
        bride_chart = compute_chart(b_birth_date, b_birth_time, b_birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the charts", "message": str(err)},
            status_code=400,
        )

    guna = compute_guna_milan(groom_chart, bride_chart)
    verdict_key = {
        "Uttam":            "matching_verdict_uttam",
        "Madhyam":          "matching_verdict_madhyam",
        "Avara":            "matching_verdict_avara",
        "Not recommended":  "matching_verdict_below",
    }[guna.overall_verdict]

    return templates.TemplateResponse(
        request,
        "matching_result.html",
        {
            "lang": lang,
            "guna": guna,
            "verdict_key": verdict_key,
            "groom": {
                "name": g_name.strip(), "birth_date": g_birth_date,
                "birth_time": g_birth_time, "birth_place": g_birth_place.strip(),
            },
            "bride": {
                "name": b_name.strip(), "birth_date": b_birth_date,
                "birth_time": b_birth_time, "birth_place": b_birth_place.strip(),
            },
        },
    )


@app.post("/switch")
async def switch(
    request: Request,
    chart_id: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Activate the named saved chart, then redirect to `next` (default home)."""
    collection = load_collection(request).set_active(chart_id)
    response = RedirectResponse(_safe_redirect_target(next), status_code=303)
    save_collection(response, collection)
    return response


@app.post("/delete-chart")
async def delete_chart(
    request: Request,
    chart_id: str = Form(...),
) -> RedirectResponse:
    """Remove a saved chart; if it was active, activate whatever remains first."""
    collection = load_collection(request).remove(chart_id)
    response = RedirectResponse("/", status_code=303)
    if not collection.charts:
        clear_collection(response)
    else:
        save_collection(response, collection)
    return response


@app.post("/reset")
async def reset() -> RedirectResponse:
    """Wipe all saved charts — fresh-start button on the welcome-back panel."""
    response = RedirectResponse("/", status_code=303)
    clear_collection(response)
    return response


def _safe_redirect_target(candidate: str) -> str:
    """Allow only same-origin paths in `next=` redirects (open-redirect guard)."""
    return candidate if candidate.startswith("/") and not candidate.startswith("//") else "/"


def cli() -> None:
    """Entry point for the `astro-ai` console script: starts uvicorn on localhost:8000."""
    uvicorn.run("astro_ai.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    cli()
