"""#1089: a name that mixes scripts is refused, not scored on its Latin words alone.

WHAT WAS WRONG
--------------
`POST /numerology` refused a name with fewer than two Latin letters (#168) but let
`Anuj महाजन` through. `_clean_name` dropped every non-Latin word, the numbers for `ANUJ`
were computed, and the page showed them under the full name as typed. The surname
contributed nothing and nothing said so. knowledge/numerology.md §3.2 gives Chaldean
values for the 26 Latin letters only, so a dropped word cannot be "scored as zero".
"""
from __future__ import annotations

import re

import pytest

from astro_ai import numerology as n


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    return TestClient(app)


# The meta description a rendered reading carries (the form's own copy also says "Soul Urge").
_READING = re.compile(r"Soul Urge (\d+), Personality (\d+)")


def _post(client, name):
    return client.post("/numerology", data={"name": name, "birth_date": "1990-08-15"})


@pytest.mark.parametrize("name", ["Anuj महाजन", "名字 Li", "Straße Rao", "Łukasz Kumar"])
def test_a_name_with_a_letter_that_cannot_be_scored_is_refused(client, name):
    r = _post(client, name)
    assert r.status_code == 400, name
    assert "English letters" in r.text
    assert not _READING.search(r.text), "the refusal must not render a reading"


def test_the_refusal_names_the_characters_it_would_have_ignored(client):
    r = _post(client, "Anuj महाजन")
    assert "These characters can&#39;t be scored:" in r.text or "These characters can't be scored:" in r.text
    assert "म" in r.text and "ज" in r.text


@pytest.mark.parametrize("name", ["Anuj Mahajan", "José Núñez", "Śrī Rama", "Mary-Ann O'Neil", "A. K. Rao"])
def test_names_that_are_wholly_latin_are_still_scored(client, name):
    r = _post(client, name)
    assert r.status_code == 200, (name, r.status_code)
    assert _READING.search(r.text), "a Latin name must still get its reading"


def test_all_devanagari_is_still_refused_as_before_168(client):
    r = _post(client, "अनुज महाजन")
    assert r.status_code == 400
    assert "English letters" in r.text


def test_compatibility_refuses_a_mixed_script_name_on_either_side(client):
    r = client.post("/numerology/compatibility", data={
        "name_a": "Anuj महाजन", "birth_date_a": "1990-08-15",
        "name_b": "Asha Rao", "birth_date_b": "1992-03-04"})
    assert r.status_code == 400
    assert "English letters" in r.text
    r2 = client.post("/numerology/compatibility", data={
        "name_a": "Anuj Mahajan", "birth_date_a": "1990-08-15",
        "name_b": "Asha राव", "birth_date_b": "1992-03-04"})
    assert r2.status_code == 400


def test_unscored_letters_ignores_spaces_hyphens_and_accents():
    assert n.unscored_letters("José Núñez-Smith O'Neil") == []
    assert n.unscored_letters("Anuj महाजन") == ["म", "ह", "ा", "ज", "न"]
