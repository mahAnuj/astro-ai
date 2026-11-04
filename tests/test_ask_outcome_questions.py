"""#402 AC5 — what `/ask` is TOLD to do with "will I clear this exam?".

SCOPE, STATED PLAINLY: this file reads the rendered system prompt and the
rendered user message. It does NOT call a model, so it cannot show that an
answer to an exam question contains no yes/no; it shows that nothing in what the
model is sent still instructs one. Whether the new wording is obeyed is
unmeasured until a probe runs against a live provider.

The defect it guards: ask.txt used to say "For yes/no questions: commit to
'likely yes', 'probably not'..." and "For 'when?' questions: give a window
(specific months/years)", which is the opposite of the honesty rules ten lines
below it (:28 no exact dates, :30 astrology cannot guarantee outcomes) and of
the issue's own requirement that grounding make answers more honest, not more
confident. A "challenging" transit verdict added under that instruction would
have read as a confident "probably not".
"""
from __future__ import annotations

import re

from astro_ai import chart, llm
from astro_ai.routes import deps

PROMPT = llm._system_prompt(deps.ASK_PROMPT_PATH, "en", None)
OVERLAYS = {name: llm._system_prompt(deps.ASK_PROMPT_PATH, "en", path)
            for name, path in deps.ASK_OVERLAY_PATHS.items()}


def _line(pattern: str, text: str = PROMPT) -> str:
    hits = [ln for ln in text.splitlines() if re.search(pattern, ln)]
    assert len(hits) == 1, (pattern, hits)
    return hits[0]


def test_nothing_sent_to_the_model_still_says_to_commit_to_a_yes_or_no():
    for text in (PROMPT, *OVERLAYS.values()):
        low = text.lower()
        assert "commit to" not in low
        assert "likely yes" not in low
        assert "strongly suggests yes" not in low
        assert "specific months" not in low and "months/years" not in low


def test_an_outcome_question_is_told_to_describe_the_chart_not_to_answer_yes_or_no():
    rule = _line(r"specific outcome")
    assert re.search(r"never a yes/no verdict", rule, re.I)
    # It must not forbid "likely" itself: HONESTY says to USE "likely", and a
    # prompt that bans and requires the same word hands the model a coin flip.
    assert '"likely"' not in rule
    assert 'Use "likely", "the chart suggests", "tends toward".' in PROMPT
    # still ANSWER FIRST: the rule opens the answer with what the chart supports,
    # so it cannot be satisfied by an evasion.
    assert re.search(r"open with what the chart does and does not support", rule, re.I)
    assert "FIRST sentence MUST directly answer" in PROMPT


def test_a_when_question_gets_a_broad_stretch_and_no_dates():
    rule = _line(r'For "when\?" questions')
    assert "never specific dates" in rule
    # and it no longer contradicts :28's "exact dates" prohibition
    assert "DO NOT predict death, terminal illness, specific accidents, or exact dates." in PROMPT


def test_the_honesty_and_plain_words_rules_are_still_in_effect():
    """Strengthening is allowed, weakening is not: every prohibition the issue
    names (:4, :7, :18-19, :22, :26-30) is still present."""
    for must in (
        "FIRST sentence MUST directly answer what they asked",
        "NOT specific countries",
        "DO NOT name specific planets",
        "DO NOT name specific signs",
        "DO NOT reference natal house numbers",
        "DO NOT cite classical texts by name",
        "Astrology shows tendencies, not certainties.",
        "DO NOT predict death, terminal illness, specific accidents, or exact dates.",
        "DO NOT promise outcomes.",
        "Astrology CANNOT pinpoint specific countries, exact future events, "
        "names of future partners, or guarantee outcomes.",
    ):
        assert must in PROMPT, must


def test_the_category_hints_that_carry_a_concept_or_a_limit_survive_the_prune():
    assert "- marriage: Manglik status if relevant" in PROMPT
    assert "- health: Sade Sati phase if relevant" in PROMPT
    assert "- travel / foreign: broad region/direction (not country)" in PROMPT


def test_the_user_message_for_an_exam_question_carries_the_never_an_event_framing(monkeypatch):
    cap: dict = {}
    monkeypatch.setattr(llm.providers, "chat",
                        lambda messages, route=None, **k: cap.update(m=messages) or "x")
    natal = chart.compute_chart("1990-04-15", "07:30", "New Delhi")
    llm.generate_ask_answer(natal, chart.compute_dasha_state(natal),
                            chart.compute_vedic_flags(natal),
                            "Will I clear my UPSC exam this year?", "career",
                            deps.ASK_PROMPT_PATH)
    user = cap["m"][1]["content"]
    assert "never whether a specific event will happen" in user
    assert "Will I clear my UPSC exam this year?" in user
    # the system side of the same request: the matching instruction is present
    assert "Never a yes/no verdict" in cap["m"][0]["content"]
