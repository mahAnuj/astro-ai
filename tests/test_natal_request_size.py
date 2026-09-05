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
    def present(budget: int) -> set[str]:
        msg = _message(BIGGEST_CHART, budget=budget)
        return {
            name
            for name, marker in (
                ("summaries", "RELEVANT TOPIC SUMMARIES"),
                ("aspects", "--- ASPECTS"),
                ("nakshatras", "--- PLANET NAKSHATRAS"),
                ("d10", "--- D-10 DASHAMSA ---"),
                ("d9", "--- D-9 NAVAMSHA ---"),
            )
            if marker in msg
        }

    whole = _message(BIGGEST_CHART, budget=None)
    full = providers.estimate_data_tokens(whole)
    # Ladder down. Each step must be a subset of the one above it — nothing
    # comes BACK as the budget tightens — and summaries must be gone before
    # the cross-checks are touched.
    steps = [present(b) for b in (full, full - 400, full - 900, full - 1200, full - 1400)]
    for tighter, looser in zip(steps[1:], steps):
        assert tighter <= looser, f"{tighter} is not a subset of {looser}"
    assert any("summaries" not in s for s in steps), (
        "the budget ladder never got tight enough to drop the summaries, so the "
        "ordering assertion below is vacuous — widen the ladder"
    )
    # The load-bearing half: at any step where a cross-check is gone, the
    # summaries must ALREADY be gone.
    for step in steps:
        if "d9" not in step or "d10" not in step:
            assert "summaries" not in step, (
                "a D-9/D-10 cross-check was shed while topic summaries were still "
                "in the message — that inverts the declared shed order"
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


def test_a_plain_rate_limit_is_not_mistaken_for_a_size_failure():
    """The distinction the outage turned on.

    Groq labels the 413 `rate_limit_exceeded`, so matching on the words "rate
    limit" would classify every ordinary 429 as unfixable and stop the chain
    from falling through — turning a recoverable blip into a dead page. The
    status code is what separates them.
    """
    ordinary = _FakeStatusError(429, "Rate limit reached for model, please retry")
    assert not providers._is_request_too_large(ordinary)


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
