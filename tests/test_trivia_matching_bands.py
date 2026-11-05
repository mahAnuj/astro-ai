"""#177: the daily email's Ashtakoot trivia must quote the same band edges as /matching.

The fact said "18+ acceptable; 28+ excellent" while `matching._overall_verdict`
scores 30+ as Uttam — two "excellent" lines in one product, and the email one
reaches subscribers and cannot be retracted. The edges are derived from the
verdict function here, never retyped, so changing the bands without the trivia
turns this red.
"""
import re

from astro_ai.matching import _overall_verdict
from astro_ai.trivia import DID_YOU_KNOW


def _edge(label: str) -> int:
    return next(t for t in range(37) if _overall_verdict(t)[0] == label)


def _koota_facts():
    return [f for f in DID_YOU_KNOW if "Ashtakoot" in f["en"]]


def test_there_is_an_ashtakoot_fact():
    assert len(_koota_facts()) == 1


def test_trivia_quotes_the_band_edges_matching_uses():
    acceptable = _edge("Avara")
    excellent = _edge("Uttam")
    for fact in _koota_facts():
        for lang in ("en", "hi"):
            plus_edges = {int(n) for n in re.findall(r"(\d+)\+", fact[lang])}
            assert plus_edges == {acceptable, excellent}, (lang, plus_edges)


def test_trivia_does_not_present_the_cutoffs_as_classical():
    # /matching says the cut-offs are Bhagya's own reading (#635); the email
    # may not claim more than the page does.
    en = _koota_facts()[0]["en"]
    assert "own reading" in en and "not a rule from the classical texts" in en
