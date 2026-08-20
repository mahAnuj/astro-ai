"""Kundli matching — Ashtakoot Guna Milan for two charts (issue #154).

Owns:
    GET  /matching  the two-seeker form, offering saved charts on either side
    POST /matching  compute the guna scores, add the cached LLM narrative, and
                    persist both partners in the session so /ask?ctx=matching
                    can recover them for a follow-up question

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only. Note this module SHADOWS the top-level
``astro_ai.matching`` engine within the ``astro_ai.routes`` package, so
``compute_guna_milan`` must always be reached by its absolute name; a relative
import here would self-import and fail obscurely.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from astro_ai import cache, events, notify
from astro_ai import providers as llm_providers
from astro_ai.chart import ChartError, compute_chart
from astro_ai.llm import generate_matching_narrative, parse_sectioned_reading
from astro_ai.matching import compute_guna_milan
from astro_ai.routes.deps import (
    MATCHING_PROMPT_PATH,
    _ask_cta_ctx,
    _seeker_role,
    _lang,
    templates,
)
from astro_ai.routes.llm_support import _cached, _fire_error_alert
from astro_ai.session import (
    SavedMatching,
    load_collection,
    load_user,
    save_last_matching,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/matching", response_class=HTMLResponse)
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


@router.post("/matching", response_class=HTMLResponse)
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
        _fire_error_alert(request, err, "chart:matching")
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
    # Track whether the LLM narrative was served from cache — used below
    # to gate owner-notify + activity event to fresh generations only.
    # Defaults to False (no LLM = no cache = fresh POST worth notifying).
    was_cached = False
    # Set by the call_fn closure below when the LLM is actually invoked (#183).
    # Declared out here so the except handler can read it even if the failure
    # happened before the closure was built.
    llm_invoked = [False]
    if os.environ.get("OPENAI_API_KEY"):
        try:
            g_fp = cache.fingerprint_chart(g_birth_date, g_birth_time, g_birth_place)
            b_fp = cache.fingerprint_chart(b_birth_date, b_birth_time, b_birth_place)
            # Sort so the order of the two people doesn't matter for cache hits.
            pair_key = ":".join(sorted([g_fp, b_fp]))
            prompt_fp = cache.fingerprint_prompt(MATCHING_PROMPT_PATH)
            cache_key = f"matching:{pair_key}:{lang}:{prompt_fp}"
            # Record whether the LLM was ACTUALLY invoked, rather than
            # pre-checking the cache (#183). The old line was
            #     was_cached = cache.get(cache_key) is not None
            # evaluated before _cached(), and `_cached` is self-healing: a
            # cached entry that fails the quality check is dropped and
            # REGENERATED. So cache.get() could return non-None, the LLM be
            # called anyway, and that call raise — leaving was_cached True and
            # silently skipping both owner-notify and the form_matching event
            # for what was, from the user's side, a fresh match.
            #
            # A one-element list rather than a plain name because the closure
            # has to write to it and this is a module-level async handler, not
            # a nested function where `nonlocal` would apply.
            def _generate() -> str:
                llm_invoked[0] = True
                return generate_matching_narrative(
                    groom_name=g_name.strip(),
                    bride_name=b_name.strip(),
                    groom_chart=groom_chart,
                    bride_chart=bride_chart,
                    guna=guna,
                    prompt_path=MATCHING_PROMPT_PATH,
                    lang=lang,
                )

            narrative_text = _cached(
                cache_key, route="matching", lang=lang, ttl_days=None,
                call_fn=_generate,
            )
            was_cached = not llm_invoked[0]
            narrative_sections = parse_sectioned_reading(narrative_text)
        except Exception as err:
            # Best-effort soft-fail: user still sees scores + table. But we
            # DO want to know — silent swallow was hiding LLM issues.
            log.exception("matching narrative LLM failed (scores still returned)")
            _fire_error_alert(request, err, "matching:narrative")
            narrative_sections = []  # surface as no-narrative; scores still render
            # If the failure happened while generating, this was a fresh match
            # from the user's side and must still notify (#183). If it failed
            # before the LLM was reached, llm_invoked stays False and this
            # correctly reports "not cached" — the pre-#183 default for a
            # request that never got as far as the cache.
            was_cached = not llm_invoked[0]

    # Fire notify + activity event ONLY on fresh matching. A cache hit
    # means the same pair was matched before in this window — the user
    # is re-viewing, not doing a new match. Also protects against browser
    # refresh / back-nav / prefetch re-firing. `model` (empty on cache
    # hit) is reported when we do fire.
    _u_match = load_user(request)
    if not was_cached:
        notify.matching_done(
            groom_name=g_name.strip(), groom_dob=g_birth_date,
            bride_name=b_name.strip(), bride_dob=b_birth_date,
            total_score=f"{guna.total_awarded:g}/{guna.total_max} · {guna.overall_verdict}",
            lang=lang, user_email=(_u_match.email if _u_match else ""),
            model=llm_providers.last_used_model(),
        )
        events.record(
            type="form_matching",
            email=(_u_match.email if _u_match else ""),
            data={
                "groom_name": g_name.strip(), "groom_dob": g_birth_date,
                "bride_name": b_name.strip(), "bride_dob": b_birth_date,
                "total_score": f"{guna.total_awarded:g}/{guna.total_max}",
                "verdict": guna.overall_verdict, "lang": lang,
                "model": llm_providers.last_used_model(),
            },
        )

    response = templates.TemplateResponse(
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
            "groom_chart": groom_chart,
            "bride_chart": bride_chart,
            # The CTA card must know whether the person running this match is
            # IN it. A parent matching two children was told "Ask 3 free
            # questions about YOUR match today … using both birth charts" —
            # false on the most prominent surface there is, the card they see
            # the moment the result renders. /ask was made role-aware first;
            # this is the same defect on the page one step earlier.
            "seeker_role": _seeker_role(
                load_collection(request).active,
                SavedMatching(
                    groom_name=g_name.strip(), groom_birth_date=g_birth_date,
                    groom_birth_time=g_birth_time, groom_birth_place=g_birth_place.strip(),
                    bride_name=b_name.strip(), bride_birth_date=b_birth_date,
                    bride_birth_time=b_birth_time, bride_birth_place=b_birth_place.strip(),
                ),
            ) if load_collection(request).active else None,
            **_ask_cta_ctx(request, hint="about your Kundli match"),
        },
    )
    # Persist the two partners in the session so /ask?ctx=matching can
    # recover both charts on a follow-up question without asking the
    # user to re-enter. Kept as one of the fields of the combined
    # __session cookie (24h TTL, same as the collection).
    save_last_matching(response, request, SavedMatching(
        groom_name=g_name.strip(), groom_birth_date=g_birth_date,
        groom_birth_time=g_birth_time, groom_birth_place=g_birth_place.strip(),
        bride_name=b_name.strip(), bride_birth_date=b_birth_date,
        bride_birth_time=b_birth_time, bride_birth_place=b_birth_place.strip(),
    ))
    return response
