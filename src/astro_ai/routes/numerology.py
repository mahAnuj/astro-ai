"""Numerology calculator and 2-person compatibility (issue #154).

Owns:
    GET  /numerology                the calculator form (issue #112)
    POST /numerology                Chaldean reading + Lo Shu grid
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
            "page_title": "Free Numerology Calculator — Chaldean (Cheiro) and Lo Shu (with honest tradition note)",
            "page_meta": "Free numerology calculator using the Chaldean (Cheiro) system plus the Chinese Lo Shu grid. Life Path, Destiny/Expression, Soul Urge, Personality, Name Number, per-Life-Path profile, Personal Year, Karmic Debt (13/14/16/19), traditional per-number practices, and 2-person compatibility. Honest about tradition: these systems are 19th-20th century Western and ancient Chinese, not classical Vedic Jyotish. No signup.",
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
) -> HTMLResponse:
    """Compute numerology reading (Issue #112)."""
    from astro_ai import numerology as _num
    name = (name or "").strip()
    if not name or len(name) < 2:
        return templates.TemplateResponse(
            request, "numerology.html",
            {
                "page_title": "Free Numerology Calculator",
                "page_meta": "Free numerology calculator using the Chaldean (Cheiro) system.",
                "reading": None,
                "error": "Please enter your full name (at least 2 characters).",
                "lang": _lang(request),
            },
            status_code=400,
        )
    # A name with no Latin letters cannot be scored, so refuse it rather than
    # render four zeros (#168). Both letter tables are defined over the 26
    # Latin letters only; no source in knowledge/*.md gives a Devanagari (or
    # any other script) letter-to-number mapping, so there is no correct
    # number to compute. Transliterating silently would be worse than
    # refusing — different romanisations of the same Hindi name reduce to
    # different numbers, so we would be presenting an arbitrary pick as fact.
    # Reuses _clean_name so this test can never drift from the cleaning the
    # calculation itself does; the length-2 floor mirrors the check above.
    if len(_num._clean_name(name)) < 2:
        return templates.TemplateResponse(
            request, "numerology.html",
            {
                "page_title": "Free Numerology Calculator",
                "page_meta": "Free numerology calculator using the Chaldean (Cheiro) system.",
                "reading": None,
                "error": "Please enter your name in English letters — the Chaldean letter values are defined over the Latin alphabet, so a name written in Devanagari or another script can't be scored.",
                "lang": _lang(request),
            },
            status_code=400,
        )
    # No `system` form field since #202. A stale client or a bookmarked POST
    # may still send one; FastAPI ignores unknown form fields, so such a
    # request now quietly gets the Chaldean reading rather than an error —
    # which is the right outcome, since Chaldean was already the default.
    try:
        reading = _num.compute(name=name, birth_date=birth_date)
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
            name=reading.name, system=reading.system,
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
            # Destiny and Name Number are the same quantity (#167 — name_number
            # is an alias of destiny), so print it once under both labels
            # rather than twice with the same value.
            "page_meta": f"Free numerology reading for {reading.name}: Life Path {reading.life_path}, Destiny/Name Number {reading.destiny}, Soul Urge {reading.soul_urge}, Personality {reading.personality}. Character profile, life challenges, career fields, best partners, traditional per-number practices, and the Chinese Lo Shu birth-number matrix. Framework is modern Western (Chaldean) + ancient Chinese, not classical Vedic Jyotish.",
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
            "page_meta": "Free numerology compatibility check — Life Path + Birthday + Destiny pair verdicts using the modern Chaldean framework (not classical Vedic Jyotish). General / marriage / business contexts.",
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
    # Same unscoreable-name guard as POST /numerology (#168) — either side
    # being non-Latin silently zeroes the destiny component of the score, so
    # name the offending side instead of scoring around it.
    _unscoreable = [
        label for label, value in (("the first name", name_a), ("the second name", name_b))
        if len(_num._clean_name(value)) < 2
    ]
    if _unscoreable:
        _which = "both names" if len(_unscoreable) == 2 else _unscoreable[0]
        return templates.TemplateResponse(
            request, "numerology_compat.html",
            {"page_title": "Numerology Compatibility",
             "page_meta": "Free numerology compatibility check.",
             "compat": None,
             "error": f"Please enter {_which} in English letters — the Chaldean letter values are defined over the Latin alphabet, so a name written in Devanagari or another script can't be scored.",
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
