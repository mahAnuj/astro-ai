"""The 413 that took `/kundli` down, and the two guards that stop it recurring.

Production, on the natal path:

    Error code: 413 - Request too large for model 'openai/gpt-oss-120b'
    ... tokens per minute (TPM): Limit 8000, Requested 8562

Two separate defects had to line up for that to become a dead page, and each
one is tested here because each can regress on its own:

1. **Nothing measured the request.** `prompts/natal.txt` had grown to
   18,095 B — 4,332 tokens, over half the entire per-minute budget — and the
   chart data on a busy chart added another 3,687. Nothing on the path knew,
   so the request went out oversized and came back 413.

2. **The chain treated a size failure as a rate failure.** Groq sends the 413
   with `"code": "rate_limit_exceeded"`, the openai SDK has no 413 subclass so
   it arrived as a generic `APIStatusError`, and the `except APIError` branch
   logged "trying next in chain" and re-sent the identical bytes to `groq20` —
   which shares the same 8,000 TPM cap and returned the same 413. Waiting and
   retrying cannot make a too-large request fit, so that second call was pure
   latency on the way to the error page.

These tests use fakes rather than the live API on purpose: the assertions are
about what THIS code does with a 413 and with a byte count, and a test that
needed a Groq key would not run in CI or in a fresh checkout.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_ai import llm, providers
from astro_ai.chart import (
    compute_chart,
    compute_dasha_state,
    compute_life_chapters,
    compute_vedic_flags,
)

PROMPT = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "prompts" / "natal.txt"
FIXTURES = Path(__file__).resolve().parent / "kundali-qa-fixtures.json"

# The largest of the eight golden charts, measured 2026-09-05: an uncancelled
# Manglik block plus five topic summaries is the worst case the corpus offers.
BIGGEST_CHART = "cancer-lagna-manglik-exempt"


def _fixture(key: str) -> dict:
    return json.loads(FIXTURES.read_text())[key]


def _message(key: str, *, budget: int | None) -> str:
    fx = _fixture(key)
    chart = compute_chart(fx["birth_date"], fx["birth_time"], fx["birth_place"])
    details = llm.BirthDetails(
        fx.get("name", ""), fx["birth_date"], fx["birth_time"], fx["birth_place"]
    )
    return llm._format_seeker_message(
        details,
        chart,
        compute_vedic_flags(chart),
        compute_life_chapters(chart),
        compute_dasha_state(chart),
        token_budget=budget,
    )


# --------------------------------------------------------------------------
# 1. the request fits
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_the_whole_request_fits_under_the_tpm_ceiling(lang):
    """The regression test for the outage itself.

    Both messages, on the biggest chart we have, in both languages, priced
    with the same estimator the runtime guard uses. If this fails the site is
    shipping requests that Groq will refuse — which is exactly the state
    `/kundli` was in.
    """
    system = llm._system_prompt(PROMPT, lang)
    budget = (
        providers.REQUEST_TOKEN_CEILING
        - providers.REQUEST_TOKEN_MARGIN
        - providers.estimate_prose_tokens(system)
    )
    total = providers.estimate_prose_tokens(system) + providers.estimate_data_tokens(
        _message(BIGGEST_CHART, budget=budget)
    )
    assert total <= providers.REQUEST_TOKEN_CEILING - providers.REQUEST_TOKEN_MARGIN, (
        f"[{lang}] the assembled request is ~{total:,} tok against a ceiling of "
        f"{providers.REQUEST_TOKEN_CEILING:,} less a {providers.REQUEST_TOKEN_MARGIN:,} "
        f"margin. Groq refuses this with a 413 and no amount of retrying helps."
    )


def test_generate_reading_actually_applies_the_budget(monkeypatch):
    """The wiring, not the mechanism.

    Every other test here calls `_format_seeker_message` with a budget worked
    out by hand, so all of them stay green if `generate_reading` stops passing
    one — the guard is then dead code and the next oversized chart 413s exactly
    as before. Found by `scripts/mutate_behaviour_suite.py`, which dropped the
    `token_budget=budget` argument at the call site and watched the whole file
    pass anyway.

    So this one goes through the real entry point and captures what it would
    have sent.
    """
    sent: dict = {}

    def fake_chat(messages, route):
        sent["messages"] = messages
        return "## Personality & Character\nx"

    monkeypatch.setattr(llm.providers, "chat", fake_chat)
    # A ceiling low enough that the guard MUST shed something. If the budget
    # is not being passed through, the message comes out whole.
    monkeypatch.setattr(llm.providers, "REQUEST_TOKEN_CEILING", 5_000)

    fx = _fixture(BIGGEST_CHART)
    chart = compute_chart(fx["birth_date"], fx["birth_time"], fx["birth_place"])
    llm.generate_reading(
        llm.BirthDetails(fx.get("name", ""), fx["birth_date"],
                         fx["birth_time"], fx["birth_place"]),
        chart=chart,
        flags=compute_vedic_flags(chart),
        life_chapters=compute_life_chapters(chart),
        prompt_path=PROMPT,
        dasha_state=compute_dasha_state(chart),
    )
    user = sent["messages"][1]["content"]
    assert user != _message(BIGGEST_CHART, budget=None), (
        "generate_reading sent the full user message under a ceiling that "
        "cannot fit it — the size guard is not wired to the request that "
        "actually goes out"
    )


def test_the_guard_does_not_fire_on_an_ordinary_chart():
    """A guard that degrades every reading has not fixed anything.

    Shedding is a last resort. With the budget the runtime actually computes,
    the biggest of the golden charts must come through whole — same bytes as
    with no guard at all.
    """
    system = llm._system_prompt(PROMPT, "en")
    budget = (
        providers.REQUEST_TOKEN_CEILING
        - providers.REQUEST_TOKEN_MARGIN
        - providers.estimate_prose_tokens(system)
    )
    assert _message(BIGGEST_CHART, budget=budget) == _message(BIGGEST_CHART, budget=None)


# --------------------------------------------------------------------------
# 2. when it does not fit, it degrades in the declared order
# --------------------------------------------------------------------------


def test_an_impossible_budget_never_sheds_a_verdict_block():
    """The blocks ranked 0 are the ones the PAGE also renders.

    Drop the Manglik detail or the yogas from the prompt and the prose starts
    disagreeing with the panel printed beside it — which is the #176 failure
    class, and far worse than a thinner reading. So even at a budget nothing
    can satisfy, they stay, and the guard logs an error instead.
    """
    msg = _message(BIGGEST_CHART, budget=100)
    assert "MANGLIK DETAIL" in msg
    assert "YOGAS DETECTED" in msg
    assert "HOUSE LORD PLACEMENTS" in msg
    assert "PLANET DIGNITY" in msg


def test_topic_summaries_are_trimmed_entry_by_entry_before_being_dropped():
    """Dropping all five summaries to save fifty tokens is a bad trade.

    `topic_summaries_for_chart` returns them in its documented priority order,
    so the tail is the least relevant. A budget that is only slightly tight
    must cost the reading one summary, not all of them.
    """
    whole = _message(BIGGEST_CHART, budget=None)
    n_whole = whole.count("    Link: /learn/")
    assert n_whole >= 3, "fixture no longer produces enough summaries to test trimming"

    # A budget just under the whole message: one entry should go, not the block.
    tight = providers.estimate_data_tokens(whole) - 30
    trimmed = _message(BIGGEST_CHART, budget=tight)
    n_trimmed = trimmed.count("    Link: /learn/")
    assert 0 < n_trimmed < n_whole, (
        f"a {30}-token overage cost {n_whole - n_trimmed} of {n_whole} summaries "
        f"(block still present: {'RELEVANT TOPIC SUMMARIES' in trimmed}). It should "
        f"cost one entry."
    )


def test_the_shed_order_is_summaries_then_colour_then_cross_checks():
    """The order is a decision, not an accident — so it is asserted.

    Squeezing the budget progressively must remove things in the documented
    priority: all the topic summaries before any aspect/nakshatra colour, and
    all of those before the D-9 and D-10 cross-checks.
    """
    # These must be the REAL block headers. Two of them were guessed the first
    # time ("--- ASPECTS", "--- PLANET NAKSHATRAS") against actual headers of
    # "--- CLASSICAL ASPECTS (special drishti ...)" and "--- PLANET NAKSHATRA
    # PLACEMENTS (finer layer than sign)", so those two rungs never matched and
    # the middle of the ordering went untested — swapping the nakshatra and D-9
    # ranks inverted the declared order with the whole file still green.
    MARKERS = (
        ("summaries", "--- RELEVANT TOPIC SUMMARIES"),
        ("aspects", "--- CLASSICAL ASPECTS"),
        ("nakshatras", "--- PLANET NAKSHATRA PLACEMENTS"),
        ("d10", "--- D-10 DASHAMSA ---"),
        ("d9", "--- D-9 NAVAMSHA ---"),
    )

    def present(budget: int) -> set[str]:
        msg = _message(BIGGEST_CHART, budget=budget)
        return {name for name, marker in MARKERS if marker in msg}

    # Anti-vacuity: every marker must actually occur in an unshed message. A
    # marker that never matches silently removes its rung from the assertions
    # below, which is exactly how this test went half-blind.
    whole_msg = _message(BIGGEST_CHART, budget=None)
    unmatched = [name for name, marker in MARKERS if marker not in whole_msg]
    assert not unmatched, (
        f"{unmatched} never appear in an unshed message, so those rungs of the "
        f"ordering are not being tested at all. Fix the markers, not this assert."
    )

    # Sheds worst-first, so this is the order things must DISAPPEAR in.
    SHED_ORDER = ["summaries", "aspects", "nakshatras", "d10", "d9"]

    full = providers.estimate_data_tokens(whole_msg)
    steps = [present(full - n) for n in range(0, 2200, 50)]

    for tighter, looser in zip(steps[1:], steps):
        assert tighter <= looser, (
            f"{sorted(looser - tighter)} came BACK as the budget tightened: "
            f"{sorted(looser)} -> {sorted(tighter)}"
        )

    # The real assertion, over every rung: if a block is gone, everything the
    # declared order sheds BEFORE it must be gone too. This is what catches an
    # inverted rank, and it is checked pairwise rather than only at the ends —
    # the previous version compared summaries against the cross-checks only, so
    # swapping the nakshatra and D-9 ranks left it green.
    for step in steps:
        for i, later in enumerate(SHED_ORDER):
            if later in step:  # survived, so everything shed earlier must be gone
                continue
            still_here = [e for e in SHED_ORDER[:i] if e in step]
            assert not still_here, (
                f"{later!r} was shed while {still_here} were still in the message. "
                f"The declared order sheds {SHED_ORDER} — see _shed_to_fit, where "
                f"the ranks are called 'a DECISION, not an implementation detail'."
            )

    # Anti-vacuity for the ladder itself: it has to get tight enough to exercise
    # every rung, or the loop above passes by never shedding anything.
    reached = {name for name in SHED_ORDER if any(name not in s for s in steps)}
    assert reached == set(SHED_ORDER), (
        f"the budget ladder never shed {sorted(set(SHED_ORDER) - reached)}, so "
        f"those rungs went untested — widen the ladder"
    )


# --------------------------------------------------------------------------
# 3. a 413 is not a rate limit
# --------------------------------------------------------------------------


class _FakeStatusError(Exception):
    """Stands in for the SDK's APIStatusError, which is what a 413 arrives as."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_a_413_is_recognised_as_structural():
    too_large = _FakeStatusError(
        413,
        "Request too large for model `openai/gpt-oss-120b` on tokens per minute "
        "(TPM): Limit 8000, Requested 8562",
    )
    assert providers._is_request_too_large(too_large)


def test_a_413_is_caught_by_its_status_even_when_the_message_says_nothing():
    """The status code has to be sufficient on its own.

    Groq's 413 happens to spell out "Request too large", so a detector built
    only on that string passes every test written from Groq's wording — and
    `scripts/mutate_behaviour_suite.py` proved it, disabling the status-code
    branch entirely without turning any test red. Another provider, or Groq
    after a wording change, sends a 413 that the string test misses, and the
    chain goes back to burning a second call on a model with the same cap.
    """
    terse = _FakeStatusError(413, "Payload Too Large")
    assert providers._is_request_too_large(terse)
    assert providers._is_request_too_large(_FakeStatusError(413, ""))


def test_a_plain_rate_limit_is_not_mistaken_for_a_size_failure():
    """The distinction the outage turned on.

    Groq labels the 413 `rate_limit_exceeded`, so matching on the words "rate
    limit" would classify every ordinary 429 as unfixable and stop the chain
    from falling through — turning a recoverable blip into a dead page. The
    status code is what separates them.
    """
    ordinary = _FakeStatusError(429, "Rate limit reached for model, please retry")
    assert not providers._is_request_too_large(ordinary)


def test_a_413_stops_the_chain_retrying_the_same_host(monkeypatch):
    """The end-to-end behaviour, through `chat()` — not just the predicate.

    Every other 413 test here calls `_is_request_too_large` directly, and all
    of them passed while `chat()` raised `AttributeError: 'ProviderConfig'
    object has no attribute 'base_url'` on the very first 413 — turning the
    handling of a 413 into a 502. The field is `api_base`. Nothing caught it
    until the route was exercised against a running server, so the gap gets a
    test rather than a note.

    Two providers on the same host and one on another. The 413 must stop the
    same-host one being tried, must NOT stop the other host, and must surface
    as RequestTooLarge.
    """
    calls: list[str] = []
    groq = "https://api.groq.com/openai/v1"
    chain = [
        providers.ProviderConfig("groq120", groq, "openai/gpt-oss-120b", "GROQ_API_KEY"),
        providers.ProviderConfig("groq20", groq, "openai/gpt-oss-20b", "GROQ_API_KEY"),
        providers.ProviderConfig("openai", None, "gpt-4o-mini", "OPENAI_API_KEY"),
    ]

    def fake_call_one(provider, messages):
        calls.append(provider.name)
        if provider.api_base == groq:
            raise _FakeStatusError(413, "Request too large for model")
        raise _FakeStatusError(500, "some other host, some other failure")

    monkeypatch.setattr(providers, "_ordered_for_request", lambda: chain)
    monkeypatch.setattr(providers, "_call_one", fake_call_one)

    with pytest.raises(providers.RequestTooLarge):
        providers.chat(messages=[{"role": "user", "content": "x"}], route="natal")

    assert "groq20" not in calls, (
        f"the chain re-sent an oversized request to a second model on the same "
        f"host after a 413 (calls: {calls}); it shares the 8,000 TPM cap and "
        f"returns the same 413"
    )
    assert "openai" in calls, (
        f"the chain stopped entirely on a 413 (calls: {calls}) — a provider on "
        f"another host has a different ceiling and is exactly the fallback that "
        f"should catch an oversized request"
    )


def test_a_413_does_not_tell_the_seeker_to_try_again_in_a_couple_of_minutes():
    """The distinction has to survive to the page, not stop at the log.

    `RequestTooLarge` subclasses `AllProvidersExhausted`, which is what keeps
    the routes' existing handlers working — and it also meant it inherited the
    high-demand copy: "please try again in a couple of minutes". For a 413 that
    is advice that can never work; the same chart assembles the same oversized
    request every time. Caught by QA, which pointed out the change's own
    argument that 413 and 429 "need OPPOSITE responses" was not reflected
    anywhere the seeker could see.
    """
    from astro_ai.routes.llm_support import _llm_error_friendly

    too_large_title, too_large_msg = _llm_error_friendly(providers.RequestTooLarge("x"))
    busy_title, busy_msg = _llm_error_friendly(providers.AllProvidersExhausted("x"))

    assert too_large_title != busy_title
    assert "couple of minutes" not in too_large_msg, (
        "a 413 is being presented as transient congestion; re-submitting the "
        "same chart produces the same refusal"
    )
    # And the generic path must still be reachable and distinct.
    assert _llm_error_friendly(ValueError("x"))[0] not in (too_large_title, busy_title)


def test_request_too_large_still_renders_the_degraded_page():
    """Routes catch AllProvidersExhausted. RequestTooLarge must stay inside it.

    If it were a sibling rather than a subclass, every `except
    AllProvidersExhausted` in the routes would miss it and a 413 would become
    an unhandled 500 instead of the friendly page.
    """
    assert issubclass(providers.RequestTooLarge, providers.AllProvidersExhausted)


def test_the_token_estimator_never_under_counts_a_real_request():
    """A guard that under-counts waves through exactly what it exists to stop.

    Measured against tiktoken o200k_base on the eight golden charts, the
    estimate must land at or above the real count for both kinds of content.
    tiktoken is a dev dependency, so this skips rather than fails where it is
    absent.
    """
    tiktoken = pytest.importorskip("tiktoken")
    enc = tiktoken.get_encoding("o200k_base")
    system = llm._system_prompt(PROMPT, "en")
    assert providers.estimate_prose_tokens(system) >= len(enc.encode(system)), (
        "the prose estimator now under-counts the system prompt"
    )
    for key in json.loads(FIXTURES.read_text()):
        if key.startswith("_"):
            continue
        user = _message(key, budget=None)
        assert providers.estimate_data_tokens(user) >= len(enc.encode(user)), (
            f"the data estimator under-counts the user message for {key}"
        )
