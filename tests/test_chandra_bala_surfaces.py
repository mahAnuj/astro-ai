"""#715: Chandra Bala is graded on two surfaces that answer two questions.

The daily Rashifal asks "how is today's Moon for me?" and follows the Gochara Moon row held in
`knowledge/vedic_reference.md` 2A: strong {1,3,6,7,10,11}, weak {2,4,5,8,9,12}. The Muhurat
Finder asks "may I choose this day?" and marks a house weak when EITHER 2A or Raman, *Muhurtha
or Electional Astrology* (2A-bis: the 6th, 8th or 12th from the Janma Rasi in an election
chart) names it: strong {1,3,7,10,11}, weak {2,4,5,6,8,9,12}. House 6 is the one that differs.

Expected sets are typed from those two sources, not read back from `muhurat.py`, and every
check below calls the real function the route calls.
"""
from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import date, datetime

import pytest

from astro_ai import chart, muhurat
from astro_ai.chart import RASHIS
from astro_ai.muhurat import (PartnerFactors, _chandra_bala, _couple_verdict,
                              _partner_factors_for, _personal_match_for,
                              chandra_bala_by_rashi)

GOCHARA_STRONG = {1, 3, 6, 7, 10, 11}   # vedic_reference.md 2A, Moon row
GOCHARA_WEAK = {2, 4, 5, 8, 9, 12}
RAMAN_MUHURTHA = {6, 8, 12}             # vedic_reference.md 2A-bis
MUHURTA_WEAK = GOCHARA_WEAK | RAMAN_MUHURTHA
MUHURTA_STRONG = set(range(1, 13)) - MUHURTA_WEAK


def _in_house(house: int, natal: str) -> str:
    return RASHIS[(RASHIS.index(natal) + house - 1) % 12]


def test_the_typed_muhurta_sets_are_what_the_two_sources_say():
    assert MUHURTA_WEAK == {2, 4, 5, 6, 8, 9, 12}
    assert MUHURTA_STRONG == {1, 3, 7, 10, 11}


def test_the_real_constants_hold_both_surfaces():
    assert muhurat._CB_GOCHARA_STRONG == GOCHARA_STRONG
    assert muhurat._CB_GOCHARA_WEAK == GOCHARA_WEAK
    assert muhurat._CB_MUHURTA_STRONG == MUHURTA_STRONG
    assert muhurat._CB_MUHURTA_WEAK == MUHURTA_WEAK


@pytest.mark.parametrize("natal", RASHIS)
@pytest.mark.parametrize("house", range(1, 13))
def test_the_rashifal_path_keeps_the_gochara_grade_for_every_house(natal, house):
    # The function routes/rashifal.py and routes/subscribe.py call, not _chandra_bala.
    transit = _in_house(house, natal)
    got_house, verdict = chandra_bala_by_rashi(transit)[natal.split(" (")[0].lower()]
    assert got_house == house
    assert verdict == ("strong" if house in GOCHARA_STRONG else "weak")


def test_house_6_is_strong_on_the_rashifal_path_and_weak_on_the_muhurta_path():
    natal = RASHIS[0]
    transit = _in_house(6, natal)
    assert chandra_bala_by_rashi(transit)["aries"] == (6, "strong")
    assert _chandra_bala(natal, transit, surface="muhurta") == (6, "weak")


@pytest.mark.parametrize("house", range(1, 13))
def test_the_muhurta_surface_grades_each_house_from_the_two_held_sources(house):
    got_house, verdict = _chandra_bala(RASHIS[3], _in_house(house, RASHIS[3]), surface="muhurta")
    assert got_house == house
    assert verdict == ("strong" if house in MUHURTA_STRONG else "weak")


def test_the_two_surfaces_differ_on_house_6_and_nowhere_else():
    differing = {h for h in range(1, 13)
                 if _chandra_bala(RASHIS[0], _in_house(h, RASHIS[0]), surface="gochara")[1]
                 != _chandra_bala(RASHIS[0], _in_house(h, RASHIS[0]), surface="muhurta")[1]}
    assert differing == {6}


def test_the_surface_has_no_default_and_an_unknown_one_fails():
    # A caller that forgets which question it is asking must not silently get an answer.
    with pytest.raises(TypeError):
        _chandra_bala(RASHIS[0], RASHIS[5])  # type: ignore[call-arg]
    with pytest.raises(KeyError):
        _chandra_bala(RASHIS[0], RASHIS[5], surface="rashifal")
    assert inspect.signature(_chandra_bala).parameters["surface"].default is inspect.Parameter.empty


def _moon_chart(natal_rashi: str):
    """A real Chart whose Moon is in `natal_rashi`, derived from a computed chart."""
    base = chart.compute_chart("1995-03-14", "12:00", "Delhi")
    planets = tuple(replace(p, rashi=natal_rashi) if p.name == "Moon" else p
                    for p in base.planets)
    return replace(base, planets=planets)


@pytest.fixture
def geo(monkeypatch):
    monkeypatch.setattr(chart, "geocode_place", lambda place: (28.61, 77.21, "Asia/Kolkata"))


def test_the_finder_personal_match_grades_house_6_weak(geo, monkeypatch):
    natal = RASHIS[0]
    user = _moon_chart(natal)
    transit = type("T", (), {"rashi": _in_house(6, natal)})()
    monkeypatch.setattr(muhurat, "_transit_moon", lambda c, when: transit)
    pm = _personal_match_for(user, datetime(2026, 12, 1, 12), "Ashwini", ())
    assert (pm.chandra_house, pm.chandra_bala) == (6, "weak")


def test_the_couple_partner_factors_grade_house_6_weak(geo):
    natal = RASHIS[0]
    ch = _moon_chart(natal)
    transit = type("T", (), {"rashi": _in_house(6, natal)})()
    pf = _partner_factors_for(ch, datetime(2026, 12, 1, 12), "Ashwini", transit, "none", ())
    assert pf.chandra_bala == "weak"


def _partner(chandra: str) -> PartnerFactors:
    return PartnerFactors("excellent", "Parama Mitra", chandra, "none", "", "")


def test_a_partner_with_the_moon_in_the_6th_downgrades_the_couple_day():
    natal = RASHIS[0]
    _, verdict = _chandra_bala(natal, _in_house(6, natal), surface="muhurta")
    assert _couple_verdict(_partner("strong"), _partner("strong")) == "excellent-for-both"
    assert _couple_verdict(_partner("strong"), _partner(verdict)) == "mixed"
    assert _couple_verdict(_partner(verdict), _partner("strong")) == "mixed"


def test_a_find_candidates_couple_day_with_a_partner_moon_in_6th_is_not_good_for_both(geo):
    # End to end through the real search: no day may be good-for-both if either partner's
    # grade that day is weak, and at least one day in the window has a house-6 Moon.
    bride = chart.compute_chart("1995-03-14", "12:00", "Delhi")   # natal Moon in Cancer
    groom = chart.compute_chart("1992-08-02", "06:30", "Delhi")   # natal Moon in Virgo
    cands = muhurat.find_candidates("vivah", "Delhi", date(2026, 12, 1), days=30,
                                    personal_chart=bride, bride_chart=bride, groom_chart=groom)
    assert cands
    assert {p.rashi for p in bride.planets if p.name == "Moon"} == {"Cancer (Karka)"}, "fixture"
    six = [c for c in cands if c.personal.chandra_house == 6]
    assert six, "fixture: no house-6 day in the window"
    for c in six:
        assert c.personal.chandra_bala == "weak"
        assert c.couple.bride.chandra_bala == "weak"
        assert c.couple.combined_verdict not in ("good-for-both", "excellent-for-both")
