"""Numerology calculator and 2-person compatibility (issue #154).

Owns:
    GET  /numerology                the calculator form (issue #112)
    POST /numerology                Chaldean / Pythagorean reading + Lo Shu grid
    GET  /numerology/compatibility  the pairing form (issue #120 phase 2)
    POST /numerology/compatibility  the pair verdict

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``).

NOTE on imports: this module is ``astro_ai.routes.numerology`` and shadows the
real ``astro_ai.numerology``. Every import here — including the function-local
``from astro_ai import numerology as _num`` and
``from astro_ai.numerology import compute_numerology_bhagya_score`` — must
therefore stay ABSOLUTE. A relative import would resolve to this module and
fail as a confusing AttributeError rather than an ImportError. Nothing here
may import ``astro_ai.main``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from astro_ai import notify
from astro_ai.routes.deps import _ask_cta_ctx, _lang, templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import load_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/numerology", response_class=HTMLResponse)
async def numerology_form(request: Request) -> HTMLResponse:
    """Numerology calculator form (Issue #112).

    Positioned as complementary to Vedic astrology, not a replacement.
    Pure math + interpretation strings — no LLM call.
    """
    return templates.TemplateResponse(
        request, "numerology.html",
        {
            "page_title": "Free Numerology Calculator — Chaldean, Pythagorean, and Lo Shu (with honest tradition note)",
            "page_meta": "Free numerology calculator using Chaldean (Cheiro) and Pythagorean systems plus the Chinese Lo Shu grid. Life Path, Destiny/Expression, Soul Urge, Personality, Name Number, per-Life-Path profile, Personal Year, Karmic Debt (13/14/16/19), traditional per-number practices, and 2-person compatibility. Honest about tradition: these systems are 19th-20th century Western and ancient Chinese, not classical Vedic Jyotish. No signup.",
            "reading": None,
            "error": None,
            "lang": _lang(request),
        },
    )


@router.post("/numerology", response_class=HTMLResponse)
async def numerology_calculate(
    request: Request,
    name: str = Form(...),
    birth_date: str = Form(...),
    system: str = Form("chaldean"),
) -> HTMLResponse:
    """Compute numerology reading (Issue #112)."""
    from astro_ai import numerology as _num
    name = (name or "").strip()
    if not name or len(name) < 2:
        return templates.TemplateResponse(
            request, "numerology.html",
            {
                "page_title": "Free Numerology Calculator",
                "page_meta": "Free numerology calculator with Chaldean + Pythagorean systems.",
                "reading": None,
                "error": "Please enter your full name (at least 2 characters).",
                "lang": _lang(request),
            },
            status_code=400,
        )
    if system not in ("chaldean", "pythagorean"):
        system = "chaldean"
    try:
        reading = _num.compute(name=name, birth_date=birth_date, system=system)
    except Exception as err:  # noqa: BLE001
        _fire_error_alert(request, err, "numerology:compute")
        return templates.TemplateResponse(
            request, "numerology.html",
            {"page_title": "Free Numerology Calculator",
             "page_meta": "Free numerology calculator.", "reading": None,
             "error": f"Couldn't compute: {err}", "lang": _lang(request)},
            status_code=400,
        )
    try:
        _u = load_user(request)
        notify.numerology_computed(
            name=reading.name, system=system,
            life_path=int(reading.life_path),
            user_email=(_u.email if _u else ""),
        )
    except Exception:
        pass
    # Numerology-only Bhagya Score — separate from the chart-based one on
    # /kundli. Sources signals purely from the numerology reading so
    # users who compute numerology first (without a Kundli) still get a
    # headline number.
    from astro_ai.numerology import compute_numerology_bhagya_score as _num_bhagya
    return templates.TemplateResponse(
        request, "numerology.html",
        {
            "page_title": f"Numerology Reading for {reading.name} — Life Path {reading.life_path}",
            "page_meta": f"Free numerology reading for {reading.name}: Life Path {reading.life_path}, Destiny {reading.destiny}, Soul Urge {reading.soul_urge}, Personality {reading.personality}, Name Number {reading.name_number}. Character profile, life challenges, career fields, best partners, traditional per-number practices, and the Chinese Lo Shu birth-number matrix. Framework is modern Western (Chaldean/Pythagorean) + ancient Chinese, not classical Vedic Jyotish.",
            "reading": reading,
            "num_bhagya_score": _num_bhagya(reading, lang=_lang(request)),
            "error": None,
            "lang": _lang(request),
            **_ask_cta_ctx(request, hint="about your chart (numerology-related life questions)"),
        },
    )


@router.get("/numerology/compatibility", response_class=HTMLResponse)
async def numerology_compat_form(request: Request) -> HTMLResponse:
    """Numerology compatibility form (Issue #120 Phase 2) — 2-person pairing."""
    return templates.TemplateResponse(
        request, "numerology_compat.html",
        {
            "page_title": "Numerology Compatibility — 2-Person Pairing Check",
            "page_meta": "Free numerology compatibility check — Life Path + Birthday + Destiny pair verdicts using the modern Chaldean/Pythagorean framework (not classical Vedic Jyotish). General / marriage / business contexts.",
            "compat": None, "error": None, "lang": _lang(request),
        },
    )


@router.post("/numerology/compatibility", response_class=HTMLResponse)
async def numerology_compat_compute(
    request: Request,
    name_a: str = Form(...),
    birth_date_a: str = Form(...),
    name_b: str = Form(...),
    birth_date_b: str = Form(...),
    context: str = Form("general"),
) -> HTMLResponse:
    from astro_ai import numerology as _num
    name_a = (name_a or "").strip()
    name_b = (name_b or "").strip()
    if not name_a or not name_b or len(name_a) < 2 or len(name_b) < 2:
        return templates.TemplateResponse(
            request, "numerology_compat.html",
            {"page_title": "Numerology Compatibility",
             "page_meta": "Free numerology compatibility check.",
             "compat": None,
             "error": "Please enter both names (at least 2 characters each).",
             "lang": _lang(request)},
            status_code=400,
        )
    if context not in ("general", "marriage", "business"):
        context = "general"
    try:
        compat = _num.compute_compatibility(name_a, birth_date_a, name_b, birth_date_b, context=context)
    except Exception as err:  # noqa: BLE001
        _fire_error_alert(request, err, "numerology:compat")
        return templates.TemplateResponse(
            request, "numerology_compat.html",
            {"page_title": "Numerology Compatibility",
             "page_meta": "Free numerology compatibility check.",
             "compat": None,
             "error": f"Couldn't compute: {err}",
             "lang": _lang(request)},
            status_code=400,
        )
    return templates.TemplateResponse(
        request, "numerology_compat.html",
        {
            "page_title": f"Compatibility: {compat.person_a_name} × {compat.person_b_name}",
            "page_meta": f"Numerology compatibility {compat.person_a_name} + {compat.person_b_name}: {compat.overall_score}/100. {compat.overall_summary[:100]}",
            "compat": compat, "context": context,
            "error": None,
            "lang": _lang(request),
        },
    )
