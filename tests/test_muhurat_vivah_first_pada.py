"""Vivah: the first quarter of Magha and Mula is rejected, the rest of each stays good (#1232).

Raman, Muhurtha (1948), "Electing a Time for Marriage", as knowledge/vedic_reference.md
section 29.14 records it: "The best asterisms are Rohini, Mrigasira, Makha, Uttara, Hasta,
Swathi, Anuradha, Moola, Uttarashadha, Uttarabhadra and Revati. The first quarter of Makha
and Moola and the last quarter of Revati are inauspicious and they should be rejected."

`score_event` judged the nakshatra alone, so a Moon in pada 1 of Magha or Mula earned the +2
nakshatra credit. The Revati clause needs no new rule: Revati is whole-nakshatra Panchak
(`_is_panchak`), and the last test pins that so the third clause of the sentence is covered.

The two calendar dates were read out of `find_candidates("vivah", "New Delhi", ...)` on
2026-11-19: both were 'excellent' before the change.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from astro_ai import muhurat as m

NO_COMBUST = {"jupiter": False, "venus": False, "mercury": False}
FIRST_PADA_NAKSHATRAS = ("Magha", "Mula")
OTHER_EVENTS = ("griha_pravesh", "business", "vidyarambh", "namkaran")


def _score(event, nakshatra, pada=None, is_panchak=False, tithi="Dwitiya", paksha="Shukla",
           weekday="Thursday"):
    panchang = SimpleNamespace(tithi_name=tithi, tithi_paksha=paksha)
    kw = {} if pada is None else {"moon_pada": pada}
    return m.score_event(event, panchang, weekday, nakshatra, is_panchak, False, "", "",
                         NO_COMBUST, **kw)


@pytest.mark.parametrize("nakshatra", FIRST_PADA_NAKSHATRAS)
def test_pada_1_of_magha_and_mula_is_avoid_with_the_flag(nakshatra):
    rating, reason, flags = _score("vivah", nakshatra, 1)
    assert rating == "avoid", reason
    assert flags == ("avoid_nakshatra_pada",)
    assert nakshatra in reason and "first quarter" in reason and "Raman" in reason
    assert f"The rest of {nakshatra} stays good" in reason


@pytest.mark.parametrize("nakshatra", FIRST_PADA_NAKSHATRAS)
@pytest.mark.parametrize("pada", [2, 3, 4])
def test_the_other_three_quarters_keep_the_credit_and_the_same_rating(nakshatra, pada):
    got = _score("vivah", nakshatra, pada)
    assert got[0] != "avoid", got
    assert f"good nakshatra ({nakshatra})" in got[1]
    assert "avoid_nakshatra_pada" not in got[2]
    assert got == _score("vivah", nakshatra)  # same as the pada not being passed at all


@pytest.mark.parametrize("nakshatra", FIRST_PADA_NAKSHATRAS)
def test_an_unknown_pada_never_rejects(nakshatra):
    # find_candidates gets pada 0 when the snapshot has no Moon (_moon_nakshatra_for).
    assert _score("vivah", nakshatra, 0) == _score("vivah", nakshatra)
    assert _score("vivah", nakshatra, 0)[0] != "avoid"


@pytest.mark.parametrize("booster", [(), ("Amrit Siddhi (Sun + Hasta)", "Ravi Yoga")])
def test_a_booster_cannot_lift_a_first_pada(booster):
    panchang = SimpleNamespace(tithi_name="Dwitiya", tithi_paksha="Shukla")
    rating, _reason, flags = m.score_event("vivah", panchang, "Thursday", "Mula", False, False,
                                           "", "", NO_COMBUST, boosters=booster, moon_pada=1)
    assert rating == "avoid" and flags == ("avoid_nakshatra_pada",)


def test_the_first_pada_of_another_vivah_good_nakshatra_is_not_rejected():
    for nakshatra in m.EVENT_RULES["vivah"]["good_nakshatras"] - set(FIRST_PADA_NAKSHATRAS):
        if nakshatra == "Revati":
            continue  # Panchak, covered below
        assert _score("vivah", nakshatra, 1) == _score("vivah", nakshatra), nakshatra


def test_only_vivah_carries_the_pada_aware_key_and_magha_mula_stay_good():
    for event, rules in m.EVENT_RULES.items():
        assert ("avoid_nakshatra_padas" in rules) == (event == "vivah"), event
    vivah = m.EVENT_RULES["vivah"]
    assert vivah["avoid_nakshatra_padas"] == {"Magha": {1}, "Mula": {1}}
    assert set(FIRST_PADA_NAKSHATRAS) <= vivah["good_nakshatras"]
    assert not set(FIRST_PADA_NAKSHATRAS) & vivah["avoid_nakshatras"]


@pytest.mark.parametrize("event", OTHER_EVENTS)
@pytest.mark.parametrize("nakshatra", FIRST_PADA_NAKSHATRAS)
def test_other_events_are_unchanged_by_the_pada(event, nakshatra):
    got = _score(event, nakshatra, 1)
    assert "avoid_nakshatra_pada" not in got[2], (event, nakshatra)
    assert got == _score(event, nakshatra), (event, nakshatra)


def test_the_rest_of_the_vivah_rule_set_is_untouched_by_the_pada_argument():
    # Passing a pada changes nothing outside the two first-quarter cases, for every nakshatra.
    for nakshatra in m.NAKSHATRAS:
        for pada in (1, 2, 3, 4):
            if nakshatra in FIRST_PADA_NAKSHATRAS and pada == 1:
                continue
            assert _score("vivah", nakshatra, pada) == _score("vivah", nakshatra), (nakshatra, pada)


def test_revati_last_quarter_is_rejected_by_the_panchak_path():
    # Raman's third clause. Not a pada rule: _is_panchak rejects every pada of Revati.
    assert m._is_panchak("Revati", 4) is True
    rating, reason, flags = _score("vivah", "Revati", 4, is_panchak=m._is_panchak("Revati", 4))
    assert rating == "avoid", reason
    assert flags == ("panchak",)
    assert "avoid_nakshatra_padas" in m.EVENT_RULES["vivah"]
    assert "Revati" not in m.EVENT_RULES["vivah"]["avoid_nakshatra_padas"]


@pytest.mark.parametrize("d, nakshatra", [
    (date(2026, 11, 30), "Magha"),   # pada 1 at the 12:00 IST judging instant; was 'excellent'
    (date(2027, 4, 25), "Mula"),     # pada 1 at the 12:00 IST judging instant; was 'excellent'
])
def test_the_real_finder_rejects_the_two_dates_that_were_excellent(d, nakshatra):
    (c,) = m.find_candidates("vivah", "New Delhi", d, 1)
    assert c.nakshatra == nakshatra
    assert c.rating == "avoid", (c.d, c.reason)
    assert c.flags == ("avoid_nakshatra_pada",), c.flags


# ─── what the page says ─────────────────────────────────────────────────────────

def test_the_rules_summary_discloses_the_first_quarter_exclusion():
    (fav,) = [x for x in m.EVENT_LANDING["vivah"]["rules_summary"]
              if x.startswith("Favourable nakshatra")]
    assert "first quarter (pada) of Magha and of Mula is excluded" in fav
    assert "Raman" in fav and "classical" not in fav.lower()


def test_the_real_pages_render_the_disclosure():
    import html

    from fastapi.testclient import TestClient

    from astro_ai.main import app

    client = TestClient(app)
    page = client.get("/muhurat/vivah")
    assert page.status_code == 200
    assert "first quarter (pada) of Magha and of Mula is excluded" in html.unescape(page.text)

    learn = client.get("/learn/vivah-muhurat-2027")
    assert learn.status_code == 200
    assert "first quarter (pada) of Magha and of Mula" in html.unescape(learn.text)
