"""#838 (slice of #777): the Manglik copy stops stating three things the held sources do not say.

* "Mars combust" listed as a cancellation. knowledge/vedic_reference.md section 1.6.2: still
  UNSOURCED, absent from Raman's antidote list and from Rao, and Vasudev rejects the whole
  family. chart.py still applies it (that is #777's decision, not this test's).
* The six-house rule stated flatly. Both held lists are five houses (2/4/7/8/12) and the 1st is
  optional (section 1.6.1, 1.6.3); Shubh Bhagya counts it, and says so.
* "the classical house lists we work from", for a list whose author writes that the dosha
  "is not to be found in the standard astrological texts" (section 1.6.1).

#856 (residue of #838): the surfaces #838 missed. The flat six-house statements on the
FAQ mirrors, the manglik-dosh and Mars articles, the checker's result page and the
manglik-remedies summary, and the "many texts consider ... after age 28" sentence on
planets-in-7th-house-marriage, which vedic_reference.md row 21 records as a modern folk claim
that no classical text states.

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


# --- #856 -------------------------------------------------------------------------------

_CLAUSE = "the sources we work from list five and treat the 1st as an optional addition, which Shubh Bhagya counts"

# Born 1980-07-10 03:00 Mumbai: Mars is in none of the six houses from Lagna, Moon or Venus, so the
# "does not fall in any of the six ... houses" branch renders. A fixture that drifts to Manglik
# turns the first assertion below red rather than leaving the branch unpinned.
_NOT_MANGLIK = {"name": "Fixture", "birth_date": "1980-07-10", "birth_time": "03:00", "birth_place": "Mumbai"}


# Mars in the 8th and 12th (see test_manglik_checker_claims.py, same birth), so the "Basis" paragraph
# and the Manglik branch render.
_BIRTH = {"name": "Fixture", "birth_date": "1957-09-07", "birth_time": "01:05", "birth_place": "Mumbai"}


def test_manglik_dosh_article_states_the_six_houses_with_the_optional_1st_clause(client):
    t = _text(client, "/learn/manglik-dosh/")
    # lead paragraph (template:7), the registry FAQ (rendered + JSON-LD), and the "six houses" line
    assert t.count(_CLAUSE) >= 3
    assert "is documented in classical compilations" not in t
    assert "is how the rule is usually stated" in t
    assert "one of the six houses Shubh Bhagya counts" in t
    assert "Shubh Bhagya's six-house count, see the caution above" in t


def test_what_is_manglik_faq_no_longer_says_classically_indicate_friction(client):
    from astro_ai.learn_registry import ARTICLES

    faqs = [f["a"] for a in ARTICLES for f in a.faqs if f["a"].startswith("Manglik Dosh forms when Mars sits in")]
    assert len(faqs) == 1
    assert _CLAUSE in faqs[0]
    assert "classically indicate" not in faqs[0]


def test_mars_article_says_the_1st_is_optional_and_drops_classically_said(client):
    t = _text(client, "/learn/mangal-mars-in-vedic-astrology/")
    assert t.count(_CLAUSE) >= 2
    assert "is classically said to create friction" not in t
    assert "Six of the twelve houses trigger Manglik on Shubh Bhagya's count" in t


def test_manglik_remedies_summary_carries_the_clause(client):
    from astro_ai.learn_registry import get_article

    art = get_article("manglik-remedies")
    assert art is not None
    assert _CLAUSE in art.summary
    assert "classical tradition flags" not in art.summary
    # summary renders in the article header and the Article JSON-LD description
    assert _text(client, "/learn/manglik-remedies/").count(_CLAUSE) >= 2


def test_manglik_dosh_keypoints_carry_the_clause():
    from astro_ai.learn_registry import get_article

    art = get_article("manglik-dosh")
    assert art is not None
    assert _CLAUSE in art.llm_summary


def test_mars_keypoints_carry_the_clause():
    from astro_ai.learn_registry import get_article

    art = get_article("mangal-mars-in-vedic-astrology")
    assert art is not None
    assert "the sources we work from list 2/4/7/8/12 and treat the 1st as an optional addition" in art.llm_summary


def test_manglik_check_result_does_not_call_the_six_houses_classical(client):
    r = client.post("/manglik-check", data=_NOT_MANGLIK)
    assert r.status_code == 200
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    assert "doesn't fall in any of the six Manglik houses" in t or "doesn&#39;t fall in any of the six Manglik houses" in t
    assert "six classical Manglik houses" not in t
    assert _CLAUSE in t


def test_manglik_check_result_basis_names_the_optional_1st(client):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", client.post("/manglik-check", data=_BIRTH).text))
    assert "The 6 qualifying houses (1, 2, 4, 7, 8, 12; " + _CLAUSE in t


def test_planets_in_7th_house_does_not_attribute_the_age_28_claim_to_the_texts(client):
    t = _text(client, "/learn/planets-in-7th-house-marriage/")
    assert "many texts consider" not in t
    assert "after age 28; that is a modern folk claim with no classical text behind it" in t
