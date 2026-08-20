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
    seeker_role = _seeker_role(saved, _last) if effective_ctx == "matching" else None
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
                             context=effective_ctx, pair_fp=pair_fp,
                             role=seeker_role)
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
            # The COPY needs this too, not just the cache key. For a third-party
            # seeker the page promised "both birth charts" while exactly one was
            # sent, and offered a "Both charts" toggle for a match that is not
            # theirs. QA caught it as OBS-2; it shipped live in 3ae9dc1 because
            # the prompt became role-aware and the copy did not.
            "seeker_role": seeker_role,
            "answer": answer,
            "remaining_today": _ask_quota_remaining(request),
        },
    )


_ASK_CATEGORIES = {"general", "career", "marriage", "money", "health",
                   "spiritual", "travel", "relationships"}


def _ask_cache_key(saved, question: str, category: str, lang: str,
                    context: str = "chart", pair_fp: str | None = None,
                    role: str | None = None) -> str:
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
    prompt_fp = _base_prompt_fp = cache.fingerprint_prompt(ASK_PROMPT_PATH)
    # The overlay is part of the system prompt, so it must be part of the key.
    # Without this, editing ask_matching.txt or ask_numerology.txt would leave
    # every answer written under the old overlay sitting in the cache —
    # `prompt_fp` only fingerprints ask.txt.
    role = role or "other"          # see _ask_overlay_path — normalise once, here
    _overlay = _ask_overlay_path(context, role)
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
    if context == "matching" and not pair_fp:
        # Rebuilt from the BASE prompt fingerprint. Returning `base` here left
        # the matching overlay's fingerprint in the key, making this a third
        # keyspace rather than the chart key the comment promised.
        # Defensive: a matching key with no pair fingerprint would also carry no
        # `matchrules`, and so would survive a koota scoring change — the exact
        # hazard matchrules exists to prevent. Callers should never reach here
        # (both handlers derive context and fingerprint from the same record),
        # so treat it as chart rather than emitting a half-formed matching key.
        return f"ask:{chart_fp}:{q_fp}:{category}:{_base_prompt_fp}:{lang}"
    if context == "matching" and pair_fp:
        # matchrules for exactly the reason numrules exists above. The Ashtakoota
        # scoring now reaches the prompt, and `prompt_fp` fingerprints only the
        # prompt FILE — so a koota rule change would otherwise leave prose in the
        # cache quoting a total /matching no longer computes. The Muhurta
        # Chintamani pass moved several kootas, some by whole verdict bands.
        # `role` is in the key because it changes the ANSWER: it decides whose
        # chart is sent as the partner's, and whether a partner chart is sent at
        # all. Without it, a same-DOB couple plus a rename could serve a
        # "you and your partner" answer to someone who is neither — the two
        # states share a chart fingerprint, since fingerprint_chart hashes birth
        # details and not the name.
        key = f"{key}:pair={pair_fp}:role={role}:matchrules={MATCHING_RULES_VERSION}"
    return key


def _seeker_role(saved, last) -> str:
    """Which of the matched pair the seeker is: "groom", "bride" or "other".

    Cheap — string comparison only, no chart and no geocode — so BOTH handlers
    can call it. That matters twice over: POST uses it to pick whose chart is
    the partner's, and both use it as a cache-key component, so it must be
    derivable without the expensive work POST does.

    Identity is by DATE OF BIRTH first. Two differing birth dates identify the
    pair on their own, which is the ordinary case, and /matching labels both
    name fields "(optional)" — requiring a name there silently dropped the
    partner's chart for anyone who left them blank or spelled them differently
    from their saved chart. Names are consulted ONLY when both parties share a
    birth date, where the DOB genuinely cannot disambiguate; if the names are
    missing there too, neither matches and the seeker is treated as a third
    party, which is the safe outcome.
    """
    if last is None:
        return "other"
    same_dob = last.groom_birth_date == last.bride_birth_date

    def _is(name, dob) -> bool:
        if saved.birth_date != dob:
            return False
        if not same_dob:
            return True
        # str() because a drifted session schema can hand us a non-string name
        # and .strip() on an int raises. `saved.name` is left as-is: a
        # non-string there already 500s the page in display_name() long before
        # this runs, so coercing it here would only hide a louder bug.
        n = (str(name) if name else "").strip().lower()
        mine = (saved.name or "").strip().lower()
        return bool(n) and bool(mine) and n == mine

    if _is(last.groom_name, last.groom_birth_date):
        return "groom"
    if _is(last.bride_name, last.bride_birth_date):
        return "bride"
    return "other"


def _ask_overlay_path(context: str, role: str | None = None):
    """The per-context system-prompt overlay, or None for plain chart asks.

    ONE resolver, used by both `_ask_cache_key` and the generation call. If
    those derived the overlay independently they could disagree, and the answer
    would be generated under one system prompt but cached under another's
    fingerprint — exactly the split-derivation bug #181 was about.

    `role` splits the matching overlay in two. A single file previously carried
    BOTH shapes — "if a second chart is present… / if only one is present…" —
    and relied on the model noticing which applied. QA made the point precisely:
    the code sent the right blocks, but the guarantee was instructional rather
    than mechanical. Selecting a different file per shape makes it mechanical,
    and as a side effect gives the two shapes distinct prompt fingerprints, so
    a seeker who changes role cannot read the other shape's cached answer.
    """
    # Normalised, not compared loosely. This read `role == "other"` while
    # _ask_cache_key wrote `role or "other"`, so a None role produced a key
    # LABELLED role=other but fingerprinted with the PARTNER overlay — a fourth,
    # self-inconsistent keyspace. Unreachable today (_seeker_role never returns
    # None, and both handlers pass None only for non-matching contexts), but it
    # is a trap for the next caller, and the fix is to make the two agree by
    # construction rather than by both remembering to be careful.
    if context == "matching" and (role or "other") == "other":
        return ASK_OVERLAY_PATHS["matching_third_party"]
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
    try:
        # Inside the try, not above it. These were outside, so a non-string
        # name — a list or an int from a drifted session schema — raised
        # AttributeError on `.strip()` and 500'd a page that runs this helper
        # on EVERY render. The sibling function fifteen lines below carries a
        # comment about exactly this mistake ("a bad partner record must
        # downgrade to chart-only, never 500 the seeker"); this one repeated it.
        g = (str(last.groom_name) if last.groom_name else "").strip() or "Groom"
        b = (str(last.bride_name) if last.bride_name else "").strip() or "Bride"
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


def _ask_lookup(saved, question: str, category: str, lang: str,
                context: str = "chart", pair_fp: str | None = None,
                role: str | None = None) -> str | None:
    """Look up an already-cached answer without burning a fresh LLM call."""
    return cache.get(_ask_cache_key(saved, question, category, lang,
                                    context=context, pair_fp=pair_fp, role=role))


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

    # Matching context. ONE derivation: the record is the single source of
    # truth for whether matching is on, who the couple are, and what they score.
    #
    # This block previously had three: _resolve_matching_partner decided the
    # context, _matching_record supplied the key, and the pair was computed
    # separately. QA found two ways they disagreed, and both ended the same way
    # — POST writing a cache entry under a key GET could never read, so the
    # seeker landed on their own question typed back at them with no answer, no
    # error, and one of three daily questions gone. The worst was a "degraded"
    # :noguna key marker that only POST knew about: a transient geocode failure
    # then produced a PERMANENT blank loop, because every retry hit the cached
    # blank. That is #181's failure class, and the cure for a LOW severity
    # ("might cache a degraded answer forever") had created a HIGH one.
    #
    # So there is no degraded matching state any more. Either the whole match
    # resolves — both charts, the Guna Milan — or the context falls back to
    # plain chart, which is a state GET already renders correctly and can
    # re-derive from the cookie alone. No marker, no split keyspace, nothing
    # for the two handlers to disagree about.
    partner_chart = None
    partner_label = "partner"
    guna_milan = None
    guna_pair_label = None
    if context == "matching":
        last, guna_pair_label, _ = _matching_record(request)
        try:
            if last is None:
                raise ValueError("no usable matching record")
            # Computed ONCE and reused. The previous shape computed four charts
            # per POST — the seeker's and the partner's twice over — which was
            # cheap in CPU (~0.07ms each) but added a third live geocode, and
            # it was precisely that extra geocode that could fail on its own
            # and trip the degraded path above.
            groom_chart = compute_chart(last.groom_birth_date,
                                        last.groom_birth_time,
                                        last.groom_birth_place)
            bride_chart = compute_chart(last.bride_birth_date,
                                        last.bride_birth_time,
                                        last.bride_birth_place)
            guna_milan = compute_guna_milan(groom_chart, bride_chart)

            # Which of the pair the seeker is decides whose chart is labelled
            # "partner". When they are NEITHER — they ran the match for someone
            # else — no partner block is sent at all. Labelling one of the pair
            # as the seeker's partner asserts a relationship that does not
            # exist, and QA measured the effect: the model was handed Aastha
            # under a "PARTNER'S NATAL CHART" header plus a score belonging to
            # Anuj & Aastha, an invitation to tell Priya her compatibility is
            # 25/36. The named Guna Milan block still carries the real couple.
            role = _seeker_role(saved, last)
            if role == "groom":
                partner_chart = bride_chart
                partner_label = "partner (bride from your Kundli match)"
            elif role == "bride":
                partner_chart = groom_chart
                partner_label = "partner (groom from your Kundli match)"
            # role == "other": the seeker ran this match for two other people.
            # No partner block at all — labelling one of the couple as the
            # seeker's partner asserts a relationship that does not exist. The
            # third-party overlay tells the model how to handle that shape.
        except Exception:
            # Anything unresolvable — missing record, bad place, geocoder down
            # — downgrades the whole request to chart context. The redirect
            # below drops `ctx` to match, so the page the seeker lands on and
            # the key it reads agree.
            log.debug("matching context unavailable for /ask; using chart",
                      exc_info=True)
            context = "chart"
            partner_chart = None
            partner_label = "partner"
            guna_milan = None
            guna_pair_label = None

    # For matching, the key carries an ORDERED pair fingerprint (see
    # _ask_cache_key). `context` is only ever "matching" here when that
    # fingerprint exists, so the key can never be a matching key without one.
    _post_last, _, _post_pair_fp = _matching_record(request)
    _post_role = _seeker_role(saved, _post_last) if context == "matching" else None
    if context != "matching":
        _post_pair_fp = None
    cache_key = _ask_cache_key(saved, question, category, lang,
                               context=context, pair_fp=_post_pair_fp,
                               role=_post_role)
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
                overlay_path=_ask_overlay_path(context, _post_role), lang=lang,
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
