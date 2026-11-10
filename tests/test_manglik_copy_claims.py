"""#838 (slice of #777): the Manglik copy stops stating three things the held sources do not say.

* "Mars combust" listed as a cancellation. knowledge/vedic_reference.md section 1.6.2: still
  UNSOURCED, absent from Raman's antidote list and from Rao, and Vasudev rejects the whole
  family. chart.py still applies it (that is #777's decision, not this test's).
* The six-house rule stated flatly. Both held lists are five houses (2/4/7/8/12) and the 1st is
  optional (section 1.6.1, 1.6.3); Shubh Bhagya counts it, and says so.
* "the classical house lists we work from", for a list whose author writes that the dosha
  "is not to be found in the standard astrological texts" (section 1.6.1).

Pinned through the real routes. It is a phrase test: it catches the wording it names, not every
possible rewording.
"""
from __future__ import annotations

import re

import pytest

_COMBUST_PAGES = [
    "manglik-dosh",
    "mars-remedies",
    "marriage-delayed",
    "mangal-mars-in-vedic-astrology",
]

# How many times "optional addition" must appear in each page's rendered HTML. The count is the
# number of SURFACES carrying the clause, so deleting it from any one of them turns the test red:
# marriage-delayed and planets-in-7th-house-marriage carry it in the template body (1) and in
# the registry FAQ, which renders both visibly and in the FAQPage JSON-LD (2); manglik-remedies
# carries it in the template only (its registry keypoints are not rendered; tested below).
_OPTIONAL_FIRST = {
    "marriage-delayed": 3,
    "planets-in-7th-house-marriage": 3,
    "manglik-remedies": 1,
}


def _text(client, path: str) -> str:
    r = client.get(path)
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


@pytest.mark.parametrize("slug", _COMBUST_PAGES)
def test_no_manglik_page_lists_combust_mars_as_a_cancellation(client, slug):
    t = _text(client, f"/learn/{slug}/")
    assert "Mars combust" not in t, slug
    assert "combust the Sun" not in t, slug
    assert "Combustion cancels Manglik" not in t, slug


@pytest.mark.parametrize("slug,surfaces", sorted(_OPTIONAL_FIRST.items()))
def test_pages_that_state_the_six_houses_say_the_1st_is_an_optional_addition(client, slug, surfaces):
    t = _text(client, f"/learn/{slug}/")
    assert t.count("optional addition") >= surfaces, slug
    assert "which Shubh Bhagya counts" in t, slug


def test_manglik_remedies_keypoints_say_the_1st_is_an_optional_addition():
    from astro_ai.learn_registry import get_article

    art = get_article("manglik-remedies")
    assert art is not None
    assert "optional addition" in art.llm_summary


def test_matching_page_says_the_sources_list_five_houses_and_the_1st_is_optional(client):
    t = _text(client, "/matching")
    assert "2nd/4th/7th/8th/12th" in t
    assert "optional addition, which Bhagya counts" in t


def test_manglik_dosh_no_longer_calls_its_house_lists_classical(client):
    t = _text(client, "/learn/manglik-dosh/")
    assert "classical house lists" not in t
    assert "the two house lists we work from" in t
    assert "is not to be found in the standard astrological texts" in t
