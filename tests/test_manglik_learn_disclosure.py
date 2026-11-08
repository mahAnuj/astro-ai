"""#429 (last slice): the /learn Manglik pages stop presenting Bhagya's own choices as classical.

Three statements were still on /learn after /kundli, /matching and the checker page
had been corrected:

* "Some traditions exclude the 2nd" -- both held house lists (Vasudev, Raman) INCLUDE
  the 2nd; neither excludes it. The only optional house in the sources is the 1st.
* "the cancellation reads strongest when both Mars positions sit in similar houses" --
  stated nowhere in the corpus.
* "comparable severity" given as the classical rule with no word on where the band
  comes from. The corpus (vedic_reference.md section 1.3, rule 20) says "comparable"
  and stops; the low/moderate/high band is Bhagya's own.

Pinned through the real /learn routes. It is a phrase test: it catches the wording it
names, not every possible rewording.
"""
from __future__ import annotations

import re

import pytest

# Pages that state the mutual-cancellation rule and so must say the band is ours.
_BAND_PAGES = [
    "manglik-dosh",
    "mars-remedies",
    "marriage-delayed",
    "mangal-mars-in-vedic-astrology",
]


def _text(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


def test_no_page_says_some_traditions_exclude_the_second_house(client):
    for slug in _BAND_PAGES:
        assert "traditions exclude the 2nd" not in _text(client, slug), slug


def test_manglik_dosh_says_both_held_lists_include_the_2nd_and_the_1st_is_optional(client):
    t = _text(client, "manglik-dosh")
    assert "Both of the classical house lists we work from include the 2nd" in t
    assert "some include the 1st" in t
    assert "optional addition" in t


def test_manglik_dosh_no_longer_claims_similar_houses_strengthen_the_cancellation(client):
    assert "sit in similar houses" not in _text(client, "manglik-dosh")


@pytest.mark.parametrize("slug", _BAND_PAGES)
def test_every_page_that_states_comparable_severity_says_the_band_is_bhagyas_own(client, slug):
    t = _text(client, slug)
    assert "comparable" in t  # the rule is still stated
    assert re.search(r"(Shubh )?Bhagya'?s? own (convention|weighting)|the band is ours", t), slug
    assert "not scripture" in t, slug


def test_manglik_dosh_calls_the_grades_our_own_weighting(client):
    assert "our own weighting, not a classical ladder" in _text(client, "manglik-dosh")
