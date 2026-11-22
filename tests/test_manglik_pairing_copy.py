"""#1377: the Manglik pairing copy stops asserting a rule the held sources do not state as ours.

The daily-email trivia said Mangal Dosh "only matters in marriage if both partners have it —
they cancel each other out" (Hindi: "रद्द कर देते हैं"), and /learn/marriage-delayed called
matching with another Manglik "the classical remedy". Both-Manglik cancellation is one entry in
one modern antidote list (knowledge/vedic_reference.md section 1.6), not a classical rule, and
the trivia's "only matters" inverted the list's claim. The email reaches subscribers and cannot
be retracted, so the wording is pinned here.

A phrase test: it catches the wording it names and requires the attributed replacement.
"""
from pathlib import Path

from astro_ai.trivia import DID_YOU_KNOW

_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "src" / "astro_ai" / "templates" / "learn" / "marriage-delayed.html"
)


def _mangal_facts():
    return [f for f in DID_YOU_KNOW if "Mangal Dosh" in f["en"]]


def test_there_is_exactly_one_mangal_fact():
    assert len(_mangal_facts()) == 1


def test_trivia_drops_the_inverted_cancellation_claim():
    fact = _mangal_facts()[0]
    assert "cancel each other out" not in fact["en"]
    assert "only matters" not in fact["en"]
    assert "रद्द" not in fact["hi"]


def test_trivia_states_the_attributed_antidote():
    fact = _mangal_facts()[0]
    assert "both partners are Manglik" in fact["en"]
    assert "दोनों साथी मांगलिक" in fact["hi"]


def test_marriage_delayed_does_not_call_manglik_pairing_the_classical_remedy():
    html = _TEMPLATE.read_text(encoding="utf-8")
    assert "preference for matching with another Manglik" not in html
    assert "this is the classical remedy" not in html
    assert (
        "one held antidote list says the dosha is cancelled when both partners are Manglik"
        in html
    )
