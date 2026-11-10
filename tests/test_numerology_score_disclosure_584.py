"""#584: the numerology 0-100 is disclosed as editorial, and compounds carry no score term.

WHAT WAS WRONG
--------------
`compute_numerology_bhagya_score` added +2 / -2 for name compounds in two hand-written
lists that no held source supports (knowledge/numerology.md §13: Johari's compounds are
birth-day 10-31 only; §13.2: no numeric scoring formula in either book), and the driver
text called the +2 list "one of the most-fortunate ... in this tradition" while the code's
own comment recorded Cheiro contradicting it for 28 and 49. Neither page said the 0-100 is
Bhagya's own weighting. chief ruled Option B: disclose it, and drop the compound term.
"""

from __future__ import annotations

import dataclasses

import pytest

from astro_ai import numerology as n
from astro_ai.i18n import translate

# The two lists as they stood before #584. Pinned here, not read from the code, so a
# re-introduced tier is caught whichever values it picks.
OLD_GOOD = (10, 19, 23, 27, 28, 37, 46, 49)
OLD_CHALLENGED = (13, 14, 16, 26, 43)


def _score(compound: int) -> int:
    base = n.compute("Asha Rao", "1990-01-01", target_year=2026)
    return n.compute_numerology_bhagya_score(dataclasses.replace(base, name_compound=compound)).value


@pytest.mark.parametrize("compound", range(10, 53))
def test_name_compound_does_not_move_the_score(compound):
    """Every compound 10-52 scores the same as every other, other terms equal."""
    assert _score(compound) == _score(25)


def test_no_driver_names_a_compound():
    base = n.compute("Asha Rao", "1990-01-01", target_year=2026)
    for compound in OLD_GOOD + OLD_CHALLENGED:
        s = n.compute_numerology_bhagya_score(dataclasses.replace(base, name_compound=compound))
        assert not [d for d in s.drivers if "Compound" in d.note], compound


def test_compound_score_keys_are_gone_from_both_languages():
    for lang in ("en", "hi"):
        for key in ("nbs_compound_good", "nbs_compound_challenge"):
            assert translate(lang, key) == key, (lang, key)


def test_disclosure_text_is_editorial_in_english():
    assert "editorial weighting" in translate("en", "num_score_disclosure")


def _post_reading(client, path="/numerology"):
    r = client.post(path, data={"name": "Asha Rao", "birth_date": "1990-01-01"})
    assert r.status_code == 200, r.status_code
    assert "Numerology Bhagya Score" in r.text or "भाग्य" in r.text, "reading did not render"
    return r


def _post_compat(client, path="/numerology/compatibility"):
    r = client.post(path, data={
        "name_a": "Asha Rao", "birth_date_a": "1990-01-01",
        "name_b": "Ravi Kumar", "birth_date_b": "1988-05-12", "context": "general",
    })
    assert r.status_code == 200, r.status_code
    assert "/100" in r.text, "the score did not render; the test proves nothing"
    return r


def test_reading_page_discloses_the_score_is_editorial(client):
    assert "editorial weighting" in _post_reading(client).text


def test_compat_page_discloses_the_score_is_editorial(client):
    assert "editorial weighting" in _post_compat(client).text


def test_hindi_pages_carry_the_hindi_disclosure(client):
    hi = translate("hi", "num_score_disclosure")
    assert hi != translate("en", "num_score_disclosure")
    assert hi in _post_reading(client, "/numerology?lang=hi").text
    assert hi in _post_compat(client, "/numerology/compatibility?lang=hi").text


def test_the_page_no_longer_calls_any_compound_most_fortunate(client):
    for compound_name in ("Amit", "Lloyd George", "Anuj"):  # compounds 10, 43, 13
        r = client.post("/numerology", data={"name": compound_name, "birth_date": "1990-01-01"})
        assert r.status_code == 200
        assert "most-fortunate name compounds" not in r.text
        assert "a challenging compound" not in r.text
