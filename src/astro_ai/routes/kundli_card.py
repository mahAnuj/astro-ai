"""Cosmic Card — the shareable SVG rendering of a saved chart (issue #154).

Owns:
    GET /kundli/card   1080×1920 SVG of the user's saved chart (issue #113)

This is the ONLY route in the app that serves a ``public, max-age`` response.
Its ``Cache-Control`` and ``Content-Disposition`` headers are part of the
contract with the CDN and with social-platform og:image fetchers, so they are
set by hand here and deliberately NOT routed through ``_no_cdn_cache``.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_manglik_details,
    compute_sade_sati_details,
    symbol_for_rashi_label,
)
from astro_ai.routes.deps import templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import load_collection

log = logging.getLogger(__name__)

router = APIRouter()

# Everything outside this set is dropped from the ASCII filename (#180).
_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9 ._-]")
_FILENAME_MAX = 60


def _card_content_disposition(name: str) -> str:
    """Build a safe `Content-Disposition` for the cosmic card (#180).

    The chart name is whatever the seeker typed, and it used to be
    interpolated raw:

        f'inline; filename="cosmic-card-{details.name or "kundli"}.svg"'

    Two problems, one of which the issue under-called. A name containing a
    double quote terminates the quoted string early and silently corrupts the
    header — `Anuj"; evil=1` yields
    `filename="cosmic-card-Anuj"; evil=1.svg"`, i.e. an attacker-chosen
    parameter. And a name containing CR/LF is a response-splitting attempt:
    #180 supposed "Starlette will most likely reject it", but constructing a
    Response with a CRLF-bearing header value **succeeds**. Nothing upstream
    was protecting us.

    Emits both forms per RFC 6266:

    - `filename=` — ASCII only, unsafe characters removed, length capped. This
      is what old clients use, and it is the one that must be unbreakable.
    - `filename*=UTF-8''…` — percent-encoded, so a Devanagari or accented name
      survives intact in modern browsers. Percent-encoding also makes CR/LF
      structurally impossible here: they encode to %0D%0A.

    Clients that understand `filename*` prefer it, so the sanitised ASCII form
    is a fallback rather than a downgrade for most users.
    """
    raw = (name or "").strip()
    ascii_part = _FILENAME_UNSAFE.sub("", raw)[:_FILENAME_MAX].strip() or "kundli"
    utf8_part = quote(f"cosmic-card-{raw[:_FILENAME_MAX] or 'kundli'}.svg", safe="")
    return (
        f'inline; filename="cosmic-card-{ascii_part}.svg"; '
        f"filename*=UTF-8''{utf8_part}"
    )


@router.get("/kundli/card")
async def kundli_cosmic_card(request: Request) -> Response:
    """Cosmic Card (Issue #113) — shareable 1080×1920 SVG of the user's chart.

    Served as image/svg+xml so browsers render it inline; social platforms
    (WhatsApp, Instagram, Twitter) accept SVG as og:image on most modern
    stacks. Users can right-click "Save as" for a copy.

    Ships as SVG (not PNG) to avoid new deps (Pillow / cairosvg / Playwright).
    A future PNG-rasterize path can wrap this if platforms reject the SVG.
    """
    saved = load_collection(request).active
    if saved is None:
        # Guard against no-chart access — redirect to form.
        return RedirectResponse("/?needs_chart=card", status_code=303)
    details = saved.to_birth_details()
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:cosmic_card")
        return Response("Could not render card: " + str(err), status_code=400)

    display_name = (details.name or "").strip() or ""
    moon = next((p for p in chart.planets if p.name == "Moon"), None)
    sun = next((p for p in chart.planets if p.name == "Sun"), None)
    manglik = compute_manglik_details(chart)
    sade_sati = compute_sade_sati_details(chart)

    tpl = templates.env.get_template("cosmic_card.svg")
    svg = tpl.render(
        details=details,
        chart=chart,
        display_name=display_name,
        moon_nakshatra=(moon.nakshatra if moon else ""),
        lagna_glyph=symbol_for_rashi_label(chart.lagna_rashi),
        moon_glyph=symbol_for_rashi_label(moon.rashi) if moon else "",
        sun_glyph=symbol_for_rashi_label(sun.rashi) if sun else "",
        manglik=manglik,
        sade_sati=sade_sati,
    )
    # Cache for 1h since chart details rarely change; browsers + Fastly cache too.
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": _card_content_disposition(details.name),
        },
    )
