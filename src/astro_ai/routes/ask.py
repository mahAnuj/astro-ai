"""/ask — free-form Q&A answered against the seeker's own chart (issue #154).

Owns:
    GET  /ask  the question form, re-rendering a cached answer when q/c are set
    POST /ask  validate → quota-check → generate → cache → 303 back to the GET

plus the ask-only helpers ``_ASK_CATEGORIES``, ``_ask_cache_key`` and
``_ask_lookup``. The daily-quota helpers and ``_ask_cta_ctx`` live in
``astro_ai.routes.deps`` because other routes share them.

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from astro_ai import cache, events, notify, users
from astro_ai import providers as llm_providers
from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_dasha_state,
    compute_vedic_flags,
)
from astro_ai.llm import generate_ask_answer
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    ASK_OVERLAY_PATHS,
    ASK_PROMPT_PATH,
    _ask_quota_bump,
    _ask_quota_remaining,
    _lang,
    templates,
)
from astro_ai.matching import MATCHING_RULES_VERSION, compute_guna_milan
from astro_ai.routes.llm_support import _cached, _fire_error_alert, _llm_error_friendly
from astro_ai.session import load_collection, load_last_matching, load_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ask", response_class=HTMLResponse)
async def ask_form(request: Request, q: str | None = None,
                   c: str | None = None, ctx: str | None = None) -> HTMLResponse:
    """Free-form Q&A about the seeker's chart.

    GET shows the question form. If `q` and `c` are present (after a POST
    redirect or cache-hit re-visit), the answer is rendered alongside the
    form so the user can ask follow-ups.

    `ctx` selects the context type — "chart" (default), "numerology" or
    "matching". Preserved as a hidden form field so "Ask another" from
    within a numerology-context session stays in numerology-context.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
    context = ctx if ctx in ("chart", "numerology", "matching") else "chart"
    # Availability, names and the cache key all come from the COOKIE alone —
    # no chart computed, nothing geocoded. GET must stay cheap: it renders on
    # every visit, including for a seeker who has asked nothing.
    _last, matching_names, pair_fp = _matching_record(request)
    matching_available = _last is not None

    # A downgrade here is decided by the record's presence, not by whether the
    # partner's chart happens to compute. Deciding it on compute success used to
    # mean a transient geocoder outage changed the cache key, missed the entry,
    # and silently blanked an answer the seeker had already paid a question for.
    effective_ctx = ("matching" if (context == "matching" and matching_available)
                     else ("chart" if context == "matching" else context))
    if effective_ctx != "matching":
        pair_fp = None

    answer = None
    if q:
        # Render a previously-asked question by re-running the cached lookup.
        # POST handler stores the (question, category) and we look it up.
        # The partner fingerprint and the *effective* context are both part of
        # the cache key, so GET has to repeat exactly what POST did or it would
        # look up a key POST never wrote and the answer would never re-render
        # (#181) — hence one resolver call shared by header and lookup.
        answer = _ask_lookup(saved, q, c or "general", lang,
                             context=effective_ctx, pair_fp=pair_fp)
    return templates.TemplateResponse(
        request, "ask.html",
        {
            "lang": lang,
            "active_chart": saved,
            "current_question": q or "",
            "current_category": c or "general",
            # The EFFECTIVE context, not the requested one — see above.
            "current_context": effective_ctx,
            "matching_names": matching_names,
            "matching_available": matching_available,
            "answer": answer,
            "remaining_today": _ask_quota_remaining(request),
        },
    )


_ASK_CATEGORIES = {"general", "career", "marriage", "money", "health",
                   "spiritual", "travel", "relationships"}


def _ask_cache_key(saved, question: str, category: str, lang: str,
                    context: str = "chart", pair_fp: str | None = None) -> str:
    """Stable cache key for a (chart, question, category, context, partner) tuple.

    `context` is one of chart|numerology|matching and is baked in so the
    same question asked with a different context source doesn't collide —
    a numerology-context answer references the numbers, a chart-context
    answer doesn't; they are legitimately different responses.

    `pair_fp` is an ORDERED fingerprint of the matched couple, groom first,
    included **only** for context="matching". Two properties matter and both
    were learned from bugs:

    * WHO. Asking "are we compatible?" after matching partner A and then again
      after matching partner B returned A's answer — a compatibility reading
      about the wrong person, served silently (#181). The seeker's own chart
      fingerprint cannot identify a two-chart reading.
    * WHICH ROLE. This was a bare partner fingerprint until QA found that it
      cannot distinguish "Anuj is the groom" from "Anuj is the bride". Varna
      and Gana are scored directionally, so those two orders produce different
      totals — measured 21.5 vs 20.5 on one couple — yet hit the same key, and
      the cached prose for one direction was served over a page showing the
      other. Ordering the fingerprint fixes it.

    The other contexts derive purely from the seeker's saved chart, which
    `chart_fp` already covers.

    Key shapes:

        chart       ask:{chart_fp}:{q_fp}:{category}:{prompt_fp}:{lang}
        numerology  …:ctx=numerology:numrules={NUMEROLOGY_RULES_VERSION}
        matching    …:ctx=matching:pair={groom_fp}~{bride_fp}:matchrules={MATCHING_RULES_VERSION}

    where `prompt_fp` additionally carries the overlay's fingerprint for the
    two contexts that have one.

    Numerology diverged from its pre-#181 shape on purpose: the reduction
    rules changed (#162/#164/#169), so answers cached under the old rules
    name a Life Path that /numerology no longer computes, and the rules
    version must invalidate them.

    This docstring used to end "Chart and matching are still byte-identical to
    pre-#181, so their existing cache entries stay valid." That was true when
    written and is not any more, which is the whole reason `matchrules` now
    exists: the Ashtakoota scoring reaches the prompt, and the Muhurta
    Chintamani pass moved several kootas — some by whole verdict bands. A note
    describing a property the code no longer has is the drift this repo keeps
    paying for, so it is corrected here rather than left standing.
    """
    chart_fp = cache.fingerprint_chart(
        saved.birth_date, saved.birth_time, saved.birth_place
    )
    prompt_fp = cache.fingerprint_prompt(ASK_PROMPT_PATH)
    # The overlay is part of the system prompt, so it must be part of the key.
    # Without this, editing ask_matching.txt or ask_numerology.txt would leave
    # every answer written under the old overlay sitting in the cache —
    # `prompt_fp` only fingerprints ask.txt.
    _overlay = _ask_overlay_path(context)
    if _overlay is not None:
        prompt_fp = f"{prompt_fp}+{cache.fingerprint_prompt(_overlay)}"
    # Python's hash() is randomised per-process; use a stable hash so the
    # cache key survives container restarts.
    import hashlib
    from astro_ai.numerology import NUMEROLOGY_RULES_VERSION
    q_fp = hashlib.sha1(question.strip().encode("utf-8")).hexdigest()[:16]
    base = f"ask:{chart_fp}:{q_fp}:{category}:{prompt_fp}:{lang}"
    if context == "chart":
        return base
    key = f"{base}:ctx={context}"
    if context == "numerology":
        # The numerology reading is regenerated per request from the saved
        # chart, but the ANSWER is cached — and prompt_fp fingerprints only
        # the prompt file, not the computation. Without this component, a
        # rules change (#162/#164/#169) leaves LLM prose naming the old Life
        # Path in the cache while /numerology renders the new one, for ~13.5%
        # of birth dates. Bump NUMEROLOGY_RULES_VERSION on any rule change.
        key = f"{key}:numrules={NUMEROLOGY_RULES_VERSION}"
    if context == "matching" and pair_fp:
        # matchrules for exactly the reason numrules exists above. The Ashtakoota
        # scoring now reaches the prompt, and `prompt_fp` fingerprints only the
        # prompt FILE — so a koota rule change would otherwise leave prose in the
        # cache quoting a total /matching no longer computes. The Muhurta
        # Chintamani pass moved several kootas, some by whole verdict bands.
        key = f"{key}:pair={pair_fp}:matchrules={MATCHING_RULES_VERSION}"
    return key


def _ask_overlay_path(context: str):
    """The per-context system-prompt overlay, or None for plain chart asks.

    ONE resolver, used by both `_ask_cache_key` and the generation call. If
    those derived the overlay independently they could disagree, and the answer
    would be generated under one system prompt but cached under another's
    fingerprint — exactly the split-derivation bug #181 was about.
    """
    return ASK_OVERLAY_PATHS.get(context)


def _matching_record(request):
    """Cheap read of the last-matching cookie. NO chart computation, no network.

    Returns ``(last, names, pair_fp)`` — the record, "Groom & Bride" for display,
    and an ORDERED fingerprint of the pair. Any of them may be None.

    Everything here is string work: `cache.fingerprint_chart` is a sha256 of
    "date|time|place", so availability, the header names and the whole cache key
    can be derived without geocoding or computing a single chart. That matters —
    resolving the partner properly calls `compute_chart`, which geocodes through
    Nominatim (rate-limited, 10s timeout), and doing that on every /ask render
    put third-party network I/O on a page-render path. Same class as #144.

    `pair_fp` is ORDERED, groom first. The previous key used only the partner's
    fingerprint, which cannot distinguish "Anuj is the groom" from "Anuj is the
    bride" — and since Varna and Gana are scored directionally, those two score
    differently. Re-matching the same two people with roles swapped therefore hit
    the same cache entry and served the other direction's total over the page.
    That is #181's failure class on a new axis, so direction is now in the key.
    """
    last = load_last_matching(request)
    if last is None:
        return None, None, None
    g = (last.groom_name or "").strip() or "Groom"
    b = (last.bride_name or "").strip() or "Bride"
    try:
        pair_fp = "{}~{}".format(
            cache.fingerprint_chart(last.groom_birth_date, last.groom_birth_time,
                                    last.groom_birth_place),
            cache.fingerprint_chart(last.bride_birth_date, last.bride_birth_time,
                                    last.bride_birth_place),
        )
    except Exception:
        log.debug("malformed last-matching record", exc_info=True)
        return None, None, None
    return last, f"{g} & {b}", pair_fp


def _resolve_matching_partner(request: Request, saved, context: str):
    """Resolve the ctx=matching partner from the last-matching cookie.

    Returns ``(partner_chart, partner_label, partner_fp, effective_context)``.

    Shared by GET and POST /ask deliberately. Both the partner fingerprint
    and the *effective* context (which downgrades "matching" → "chart" when
    there is no matching cookie, or when the partner chart won't compute)
    are part of the cache key, so if the two handlers derived them
    independently the PRG redirect would read a key the POST never wrote and
    the answer would stop rendering. One resolver, one answer (issue #181).

    Partner identification is unchanged: if the seeker's saved chart is the
    groom (name + DOB), the partner is the bride; if the seeker is the bride,
    the partner is the groom; otherwise — including a curious third party —
    the bride is the partner by default.
    """
    if context != "matching":
        return None, "partner", None, context

    last = load_last_matching(request)
    if last is None:
        # No recent matching to draw from; downgrade to chart-only.
        return None, "partner", None, "chart"

    def _same(saved_c, name: str, dob: str) -> bool:
        return (saved_c.birth_date == dob
                and (saved_c.name or "").strip().lower() == (name or "").strip().lower())

    seeker_is_groom = _same(saved, last.groom_name, last.groom_birth_date)
    seeker_is_bride = _same(saved, last.bride_name, last.bride_birth_date)
    if seeker_is_groom or not seeker_is_bride:
        # Seeker identifies with groom (or default): partner = bride
        p_name = last.bride_name or "Bride"
        p_dob, p_time, p_place = (last.bride_birth_date,
                                  last.bride_birth_time,
                                  last.bride_birth_place)
        partner_label = "partner (bride from your Kundli match)"
    else:
        # Seeker identifies with bride: partner = groom
        p_name = last.groom_name or "Groom"
        p_dob, p_time, p_place = (last.groom_birth_date,
                                  last.groom_birth_time,
                                  last.groom_birth_place)
        partner_label = "partner (groom from your Kundli match)"

    # The fingerprint call belongs INSIDE this guard: it is partner-derived
    # work too, and a malformed cookie record (a null birth_place, say) makes
    # it raise before compute_chart is ever reached. A bad partner record must
    # downgrade to chart-only, never 500 the seeker. Leaving it outside is
    # exactly the regression the #181 refactor introduced.
    try:
        partner_fp = cache.fingerprint_chart(p_dob, p_time, p_place)
        partner_chart = compute_chart(p_dob, p_time, p_place)
    except Exception:
        log.debug("partner chart compute failed for /ask matching context", exc_info=True)
        return None, partner_label, None, "chart"
    return partner_chart, partner_label, partner_fp, "matching"


def _ask_lookup(saved, question: str, category: str, lang: str,
                context: str = "chart", pair_fp: str | None = None) -> str | None:
    """Look up an already-cached answer without burning a fresh LLM call."""
    return cache.get(_ask_cache_key(saved, question, category, lang,
                                    context=context, pair_fp=pair_fp))


@router.post("/ask")
async def ask_submit(
    request: Request,
    question: str = Form(""),
    category: str = Form("general"),
    context: str = Form("chart"),
) -> Response:
    """Submit a question. PRG-style: validate → generate → cache → 303 to GET.

    `context` is one of:
      - "chart" (default): natal chart + current dasha + flags only
      - "numerology": also pass the seeker's numerology reading, computed
        from the saved chart's own name+birth_date so no extra data
        collection is required. Enables numerology-flavoured follow-ups
        from /numerology to be answered against BOTH the numbers and
        the chart.
      - "matching": also pass the "other partner" chart from the user's
        most recent /matching submission (stored in the session cookie).
        Enables follow-ups like "is this a good career-alignment match?"
        that need BOTH charts. If the seeker's saved chart matches one
        of the two matching parties, the OTHER party is passed; else
        the groom chart is passed as the partner by default.
    """
    saved = load_collection(request).active
    if saved is None:
        return RedirectResponse("/?needs_chart=ask", status_code=303)
    lang = _lang(request)
    if context not in ("chart", "numerology", "matching"):
        context = "chart"

    # Every error re-render below must carry the context forward. It did not:
    # a 400 (too short / too long) or a 429 (quota) rebuilt the page WITHOUT
    # current_context, so `{{ current_context or 'chart' }}` rendered "chart",
    # the heading reverted to the single-chart wording and the switcher
    # vanished. The seeker then retyped and submitted in chart context without
    # ever being told the match had been dropped — and on the 429 path they had
    # already spent the question. Harmless while this was cosmetic; it stopped
    # being cosmetic once context started driving the heading and the prompt.
    _last_err, _names_err, _ = _matching_record(request)
    _err_ctx = context if (context != "matching" or _last_err is not None) else "chart"
    _err_extra = {
        "current_context": _err_ctx,
        "matching_names": _names_err,
        "matching_available": _last_err is not None,
    }
    question = (question or "").strip()
    if not question or len(question) < 5:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang,
                "active_chart": saved,
                "current_question": question,
                "current_category": category,
                "answer": None,
                "error": "Please write a question of at least a few words.",
                "remaining_today": _ask_quota_remaining(request),
                **_err_extra,
            },
            status_code=400,
        )
    if len(question) > 600:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang, "active_chart": saved,
                "current_question": question[:600], "current_category": category,
                "answer": None,
                "error": "Question is too long (max 600 characters).",
                "remaining_today": _ask_quota_remaining(request),
                **_err_extra,
            },
            status_code=400,
        )
    if category not in _ASK_CATEGORIES:
        category = "general"
    if _ask_quota_remaining(request) <= 0:
        return templates.TemplateResponse(
            request, "ask.html",
            {
                "lang": lang, "active_chart": saved,
                "current_question": question, "current_category": category,
                "answer": None,
                "error": "You've used today's question quota. Come back tomorrow.",
                "remaining_today": 0,
                **_err_extra,
            },
            status_code=429,
        )

    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "API key not configured",
             "message": "Add OPENAI_API_KEY (or set BHAGYA_LLM_PROVIDERS) before asking."},
            status_code=503,
        )

    # Cache key includes question fingerprint so re-asking the same question
    # serves instantly from cache. Counts against quota only on first ask.
    try:
        chart = compute_chart(saved.birth_date, saved.birth_time, saved.birth_place)
    except ChartError as err:
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    dasha = compute_dasha_state(chart)
    flags = compute_vedic_flags(chart)

    # Numerology context: compute the reading from the saved chart's own
    # name + birth_date so users asking follow-ups from /numerology get
    # answers that reference BOTH their numbers and their chart. No
    # extra data collection needed. birth_date on the saved record is
    # already a str (session.ChartRecord). Silently skipped if reading
    # fails — we still answer chart-only rather than error the user out.
    numerology_reading = None
    if context == "numerology":
        try:
            from astro_ai.numerology import compute as _num_compute
            numerology_reading = _num_compute(
                saved.name or "Seeker",
                saved.birth_date,
            )
        except Exception:
            log.debug("numerology context load failed for /ask", exc_info=True)

    # Matching context: recover the partner chart from the last-matching
    # cookie set by POST /matching. `context` may come back downgraded to
    # "chart" when there is no matching cookie or the partner chart will not
    # compute; the redirect below then drops `ctx` to match.
    partner_chart, partner_label, _unused_fp, context = _resolve_matching_partner(
        request, saved, context
    )

    # The Guna Milan is computed from THE MATCHING RECORD — groom and bride as
    # /matching scored them — never from the seeker's active chart.
    #
    # It used to be built as compute_guna_milan(seeker_chart, partner_chart),
    # which is only correct when the seeker IS one of the matched pair. QA found
    # two ways that fails, both silent and both producing a total no page ever
    # showed, wrapped in a prompt instruction to quote it verbatim:
    #
    #   * a third party. Active chart Priya, match Anuj x Aastha: the page
    #     scored 13/36 for Anuj x Aastha while the block sent 20.5/36 for
    #     Priya x Aastha, under a header naming Anuj & Aastha.
    #   * an anonymous match. Names are OPTIONAL on /matching, so the identity
    #     test matched on an empty string, the seeker became her own partner,
    #     and the block scored her against herself.
    #
    # Deriving from the record removes the identity guess entirely: the numbers
    # now describe the couple the page named, whoever happens to be asking.
    # Recomputed rather than persisted (~0.016ms) because the result serialises
    # to ~3.6KB against a ~4KB cookie budget, and a GCS stash would put a
    # cross-continent read on a hot path (CLAUDE.md, #144).
    guna_milan = None
    guna_pair_label = None
    if context == "matching":
        try:
            last, guna_pair_label, _ = _matching_record(request)
            if last is not None:
                guna_milan = compute_guna_milan(
                    compute_chart(last.groom_birth_date, last.groom_birth_time,
                                  last.groom_birth_place),
                    compute_chart(last.bride_birth_date, last.bride_birth_time,
                                  last.bride_birth_place),
                )
        except Exception:
            # Never fail an answer over the compatibility block; the two natal
            # charts alone still make a usable matching answer.
            guna_milan = None
            log.debug("guna milan compute failed for /ask matching context",
                      exc_info=True)

    # Cache key includes context so the same question asked from
    # /numerology (with numerology context) does not collide with the
    # same question asked from /kundli (chart-only) — and, for matching,
    # the partner fingerprint so two different partners get two different
    # answers instead of the first partner's (issue #181).
    # A failed Guna Milan must not poison the key. `_cached` stores with
    # ttl_days=None (never expires), so one transient compute failure would
    # otherwise cache a matching answer with NO Ashtakoota block under the
    # full-fidelity key, and every later identical ask would be served that
    # degraded answer forever. Marking the degraded generation separately means
    # the next healthy request regenerates instead of inheriting the failure.
    _post_pair_fp = _matching_record(request)[2] if context == "matching" else None
    if context == "matching" and guna_milan is None and _post_pair_fp:
        _post_pair_fp = f"{_post_pair_fp}:noguna"
    cache_key = _ask_cache_key(saved, question, category, lang,
                               context=context, pair_fp=_post_pair_fp)
    was_cached = cache.get(cache_key) is not None
    try:
        answer_text = _cached(
            cache_key=cache_key,
            route="ask",
            lang=lang,
            ttl_days=None,
            call_fn=lambda: generate_ask_answer(
                chart=chart, dasha=dasha, flags=flags,
                question=question, category=category,
                prompt_path=ASK_PROMPT_PATH,
                overlay_path=_ask_overlay_path(context), lang=lang,
                numerology_reading=numerology_reading,
                partner_chart=partner_chart,
                partner_label=partner_label,
                guna_milan=guna_milan,
                guna_pair_label=guna_pair_label,
            ),
        )
    except Exception as err:
        log.exception("ask LLM generation failed")
        _fire_error_alert(request, err, "ask")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": _title, "message": _msg},
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )

    # Save the Ask answer to the signed-in user's reading history so they can
    # revisit past questions from /account. Best-effort — never fails the
    # redirect. Only saves fresh generations (not cache hits) to avoid dupes.
    if not was_cached:
        _signed_in = load_user(request)
        if _signed_in and _signed_in.sub and answer_text:
            try:
                users.save_reading(
                    sub=_signed_in.sub,
                    kind="ask",
                    chart_id=saved.id,
                    title=question[:80] + ("…" if len(question) > 80 else ""),
                    body=answer_text,
                    meta={"question": question, "category": category},
                )
            except Exception:  # noqa: BLE001 — history is best-effort
                log.warning("save_reading(ask) failed for %s", _signed_in.sub)

    # Notify owner ONLY on fresh generation (cache-hit re-asks would spam
    # Telegram). But RECORD the event either way — we want /admin/activity
    # to show every question the user actually asked, including re-asks
    # that were served from cache. The `cache_hit` flag distinguishes them.
    _u_ask = load_user(request)
    if not was_cached:
        notify.ask_submitted(
            question=question, category=category, lang=lang,
            user_email=(_u_ask.email if _u_ask else ""),
            model=llm_providers.last_used_model(),
        )
    events.record(
        type="form_ask",
        email=(_u_ask.email if _u_ask else ""),
        data={
            "question": question, "category": category, "lang": lang,
            "model": llm_providers.last_used_model(),
            # Answer body persisted (truncated to 4000 chars) so
            # /admin/activity can spot-check Q&A quality across all
            # Cloud Run instances — SQLite cache is per-instance +
            # ephemeral, but events go to GCS. Truncation guards
            # against a single runaway answer bloating the daily
            # events blob; ~4KB × 5000 events/day = ~20MB max.
            "answer": (answer_text or "")[:4000],
            "context": context,
            "cache_hit": was_cached,
        },
    )

    # Redirect with the question + category (+ context) in the URL so
    # refresh doesn't re-submit, the user can bookmark / share the URL,
    # back/forward work naturally, and a follow-up "Ask another" from
    # the same context stays in the same context. Only bump the quota
    # on a fresh generation.
    from urllib.parse import urlencode
    _redirect_params = {"q": question, "c": category}
    if context != "chart":
        _redirect_params["ctx"] = context
    response = RedirectResponse(
        f"/ask?{urlencode(_redirect_params)}", status_code=303
    )
    if not was_cached:
        _ask_quota_bump(request, response)
    return response
