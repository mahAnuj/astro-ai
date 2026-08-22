"""Panchang pages — today's almanac and the dated archive (issue #154).

Owns:
    GET /panchang              today's Panchang for the resolved city
    GET /panchang/{date_str}   per-day archive URL (SEO audit #132 Phase 2)

plus the shared ``_render_panchang`` renderer both routes delegate to.

Deliberately does NOT own ``_PANCHANG_STRIP_CACHE`` /
``panchang_strip_for_city``: those live in routes/deps.py and belong to the homepage hot path (#144)
and live in ``routes/home.py``. Nothing here reads them.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — in particular
``from astro_ai import festivals`` must stay absolute, since a relative
import would resolve to a sibling route module, not the real one. Nothing
here may import ``astro_ai.main``.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from astro_ai import festivals
from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
from astro_ai.routes.deps import _lang, _no_cdn_cache, _pretty_date, templates
from astro_ai.session import load_collection

router = APIRouter()


def _render_panchang(request: Request, target_date, city: str = "") -> HTMLResponse:
    """Shared Panchang renderer — powers both /panchang (today) and
    /panchang/{YYYY-MM-DD} (archive URLs — SEO audit #132 Phase 2).

    City resolution priority:
      1. ?city= query param (form-submitted or shared link)
      2. Saved active chart's birth_place if user has one
      3. Default 'Mumbai, India' (largest Indian-Vedic user base)

    Panchang is location-dependent (sunrise/sunset shifts change Rahu
    Kaal, Abhijit, Choghadiya). Compute via compute_panchang against a
    throwaway chart_for_loc; degrade gracefully to Mumbai if geocoding
    fails.

    `target_date` is a `datetime.date` — the day whose panchang we want.
    """
    from astro_ai.muhurat import _choghadiya_windows as _choghadiya
    from datetime import datetime as _datetime, timedelta as _timedelta
    from zoneinfo import ZoneInfo as _ZoneInfo
    resolved_city = (city or "").strip()
    error = False
    if not resolved_city:
        saved = load_collection(request).active
        resolved_city = (saved.birth_place if saved else "") or "Mumbai, India"
    # Anchor the compute at local noon on the target date so daily-shifting
    # signals (tithi, sunrise, choghadiya) fall on the intended day.
    def _target_moment(chart) -> _datetime:
        tz = _ZoneInfo(chart.birth_tz)
        return _datetime(target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=tz)
    try:
        chart_for_loc = compute_chart("2000-01-01", "12:00", resolved_city)
        p = compute_panchang(chart_for_loc, when=_target_moment(chart_for_loc))
    except Exception:
        error = True
        resolved_city = "Mumbai, India"
        try:
            chart_for_loc = compute_chart("2000-01-01", "12:00", resolved_city)
            p = compute_panchang(chart_for_loc, when=_target_moment(chart_for_loc))
        except Exception:
            p = None
            chart_for_loc = None
    choghadiya_windows = []
    moon_info = None
    if p and chart_for_loc:
        try:
            choghadiya_windows = _choghadiya(p.weekday, p.sunrise, p.sunset)
        except Exception:
            choghadiya_windows = []
        try:
            transit = compute_transit_snapshot(chart_for_loc, when=_target_moment(chart_for_loc))
            moon = next((pl for pl in transit.planets if pl.name == "Moon"), None)
            if moon:
                moon_info = {"rashi": moon.rashi, "nakshatra": moon.nakshatra}
        except Exception:
            moon_info = None
    lang = _lang(request)
    today_iso = date.today().isoformat()
    target_iso = target_date.isoformat()
    is_today = (target_iso == today_iso)
    # Prev / next day for navigation on archive pages (skip on today to
    # keep the today URL clean).
    from datetime import timedelta as _td
    prev_day = (target_date - _td(days=1)).isoformat()
    next_day = (target_date + _td(days=1)).isoformat()
    return templates.TemplateResponse(
        request, "panchang.html",
        {
            "p": p,
            "city": city or resolved_city,
            "city_display": resolved_city,
            "today_date": target_iso,       # the rendered day (used by <time> element)
            "today_pretty": _pretty_date(target_iso, lang),
            "is_today": is_today,
            "true_today_iso": today_iso,
            "prev_day": prev_day,
            "next_day": next_day,
            "choghadiya": choghadiya_windows,
            "moon_info": moon_info,
            # Keyed off target_date, not today — an archive URL for a festival
            # date must surface that date's festival (issue #132 cross-link).
            # ALL festivals, not the first: this callout and the /festivals hub
            # render the same day and must not disagree about it. 2026-01-14 is
            # both Makar Sankranti and Pongal; the singular lookup showed one.
            "festivals_on_date": festivals.festivals_for_date(target_date),
            "error": error,
            "lang": lang,
        },
    )


@router.get("/panchang", response_class=HTMLResponse)
async def panchang_page(request: Request, city: str = "") -> HTMLResponse:
    """Today's Panchang. Delegates to _render_panchang with today's date."""
    return _no_cdn_cache(_render_panchang(request, date.today(), city))


@router.get("/panchang/{date_str}", response_class=HTMLResponse)
async def panchang_archive(request: Request, date_str: str, city: str = "") -> HTMLResponse:
    """Panchang for a specific YYYY-MM-DD (SEO audit #132 Phase 2).

    Each historical / future day gets its own indexable URL. Rolling 90-day
    window sitemap ensures Google discovers a fresh 3-month archive. Older
    dates still work by direct link — they just don't sit in the sitemap.
    """
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Bad date", "message": f"'{date_str}' is not a valid YYYY-MM-DD date. Try /panchang for today."},
            status_code=404,
        )
    # Sanity-guard against absurd dates (Swiss Ephemeris breaks pre-1800 /
    # post-2400). Also blocks crawlers from generating 100M URLs.
    if target.year < 1900 or target.year > 2100:
        return _no_cdn_cache(templates.TemplateResponse(
            request, "error.html",
            {"title": "Out-of-range date", "message": "Panchang is available for dates between 1900 and 2100."},
            status_code=400,
        ))
    return _no_cdn_cache(_render_panchang(request, target, city))


