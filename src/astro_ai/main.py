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
    compute_dasha_state,
    compute_gochar_impacts,
    compute_life_chapters,
    compute_manglik_details,
    compute_marriage_profile,
    compute_panchang,
    compute_sade_sati_details,
    compute_transit_events,
    compute_transit_snapshot,
    compute_varshaphala,
    compute_vedic_flags,
    compute_wealth_profile,
)
from astro_ai.i18n import translate as _i18n_translate
from astro_ai.llm import (
    BirthDetails,
    generate_daily_reading,
    generate_matching_narrative,
    generate_outlook_reading,
    generate_reading,
    parse_intro_and_sections,
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
MATCHING_PROMPT_PATH = PROMPTS_DIR / "matching.txt"

app = FastAPI(title="astro-ai", version="0.0.1")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Expose i18n to every template as `t(key, **kwargs)`. Templates pass the
# current `lang` (also injected per-request) into the call.
templates.env.globals["t"] = _i18n_translate
# current_year used by nav labels like "Horoscope 2026" — auto-updates yearly.
templates.env.globals["current_year"] = lambda: date.today().year


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, needs_chart: str | None = None) -> HTMLResponse:
    """Form for new visitors, chart-list + form for returning seekers.

    `?needs_chart=<feature>` is set when other routes redirect here because
    no saved chart exists yet. We surface a brief banner naming the feature
    the seeker tried to reach, so the redirect isn't silent.
    """
    collection = load_collection(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "collection": collection,
            "saved": collection.active,
            "lang": _lang(request),
            "needs_chart_for": needs_chart,
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
    """Form submission → save chart to cookie collection → render natal reading.

    Delegates rendering to `_render_natal_for` so this POST path produces the
    same fully-populated page as GET /natal — sectioned reading + Marriage /
    Wealth / Manglik / Sade Sati / Dasha panels. Saves to cookie only when
    the reading actually renders OK; chart-cap errors short-circuit before
    the expensive LLM call.
    """
    details = BirthDetails(
        name=name.strip(),
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place.strip(),
    )
    # Cap check up-front so we don't spend an LLM call only to fail the save.
    try:
        collection = load_collection(request).add(details)
    except ValueError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart limit reached", "message": str(err)},
            status_code=400,
        )
    response = await _render_natal_for(request, details)
    if response.status_code == 200:
        save_collection(response, collection)
    return response


@app.get("/natal", response_class=HTMLResponse)
async def natal(request: Request) -> HTMLResponse:
    """Re-render the natal reading for the currently active saved chart."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=natal", status_code=303)
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
    life_chapters = compute_life_chapters(chart)
    lang = _lang(request)
    try:
        reading_text = generate_reading(
            details, chart=chart, flags=flags, life_chapters=life_chapters,
            prompt_path=PROMPT_PATH, lang=lang,
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
            "dasha":    compute_dasha_state(chart),
        },
    )


@app.get("/today", response_class=HTMLResponse)
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
        active_page="monthly",
        prompt_path=MONTHLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="monthly_title",
        title_anon_key="monthly_title_anon",
        subtitle_key="monthly_subtitle",
        reading_label_key="monthly_reading",
        window_label="30 days",
        events_days=30,
        events_step_days=1,
        events_planets=("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
        include_varshaphala=False,
    )


@app.get("/yearly", response_class=HTMLResponse)
async def yearly(request: Request) -> HTMLResponse:
    """12-month outlook for the active saved chart, with Varshaphala (annual chart)."""
    return await _render_outlook(
        request,
        active_page="yearly",
        prompt_path=YEARLY_PROMPT_PATH,
        template_name="outlook.html",
        title_key="yearly_title",
        title_anon_key="yearly_title_anon",
        subtitle_key="yearly_subtitle",
        reading_label_key="yearly_reading",
        window_label="12 months",
        events_days=365,
        events_step_days=7,
        # For yearly: weekly steps + drop Sun (changes every month — noisy).
        events_planets=("Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
        include_varshaphala=True,
    )


async def _render_outlook(
    request: Request,
    *,
    active_page: str,
    prompt_path: Path,
    template_name: str,
    title_key: str,
    title_anon_key: str,
    subtitle_key: str,
    reading_label_key: str,
    window_label: str,
    events_days: int,
    events_step_days: int,
    events_planets: tuple[str, ...],
    include_varshaphala: bool = False,
) -> HTMLResponse:
    """Shared monthly/yearly renderer — same flow, different prompt + labels + scan window."""
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse(f"/?needs_chart={active_page}", status_code=303)
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
    events = compute_transit_events(
        natal, days=events_days, step_days=events_step_days, planets=events_planets
    )
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
            events=events,
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

    # Split the LLM output: time-segmented prose intro + 5 life-area cards.
    intro, sections = parse_intro_and_sections(reading_text)
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "active_page": active_page,
            "details": saved_details,
            "natal": natal,
            "transit": transit,
            "flags": flags,
            "gochar_impacts": gochar_impacts,
            "events": events,
            "varshaphala": compute_varshaphala(natal) if include_varshaphala else None,
            "reading": reading_text,
            "reading_intro": intro,
            "reading_sections": sections,
            "lang": lang,
            "title_key": title_key,
            "title_anon_key": title_anon_key,
            "subtitle_key": subtitle_key,
            "reading_label_key": reading_label_key,
            "window_label": window_label,
            "today_date": date.today().isoformat(),
        },
    )


@app.get("/dasha", response_class=HTMLResponse)
async def dasha(request: Request) -> HTMLResponse:
    """Vimshottari Dasha timeline for the active saved chart."""
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


@app.get("/matching", response_class=HTMLResponse)
async def matching_form(request: Request) -> HTMLResponse:
    """Form for two seekers — collects birth details for both, no auth needed.

    Passes the saved-chart collection so each side of the form can offer a
    "pick from saved" dropdown that auto-fills the four fields client-side.
    """
    return templates.TemplateResponse(
        request,
        "matching.html",
        {
            "lang": _lang(request),
            "collection": load_collection(request),
        },
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

    # LLM narrative — sectioned compatibility reading. Best-effort; if the LLM
    # call fails we still show the scores + table, just without the prose.
    narrative_sections: list[tuple[str, str]] = []
    if os.environ.get("OPENAI_API_KEY"):
        try:
            narrative_text = generate_matching_narrative(
                groom_name=g_name.strip(),
                bride_name=b_name.strip(),
                groom_chart=groom_chart,
                bride_chart=bride_chart,
                guna=guna,
                prompt_path=MATCHING_PROMPT_PATH,
                lang=lang,
            )
            narrative_sections = parse_sectioned_reading(narrative_text)
        except Exception:
            narrative_sections = []  # surface as no-narrative; scores still render

    return templates.TemplateResponse(
        request,
        "matching_result.html",
        {
            "lang": lang,
            "guna": guna,
            "verdict_key": verdict_key,
            "sections": narrative_sections,
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
