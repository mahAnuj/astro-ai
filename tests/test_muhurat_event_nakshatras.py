"""Griha Pravesh and Vidyarambh nakshatra / tithi sets follow the two held muhurta books (#1061, #1059).

Source: knowledge/vedic_reference.md 29.13. Raman, *Muhurtha* (1948), "Entering a New House" names
Rohini, Mrigasira, Uttara (Phalguni), Uttarashadha, Chitta and Uttarabhadra as the best and Anuradha and
Revati as permissible ("the other constellations should be rejected"); Rao Table 79 row "Entering a new
house" omits Hasta. For commencing education Raman lists Ardra, Dhanishta and Satabhisha among the "most
beneficial" and says "New and Full Moon days should be avoided"; Rao's "Teaching alphabet" row brackets
Ardra, Dhanishta and Satabhisha.

`data/` is absent on the runner, so these tests pin the code to that section, not to the books.
"""
from __future__ import annotations

from types import SimpleNamespace

from astro_ai import muhurat as m

NO_COMBUST = {"jupiter": False, "venus": False, "mercury": False}


def _score(event, nakshatra, tithi="Panchami", weekday="Monday"):
    panchang = SimpleNamespace(tithi_name=tithi, tithi_paksha="Shukla")
    return m.score_event(event, panchang, weekday, nakshatra, False, False, "", "", NO_COMBUST)


def test_griha_pravesh_hasta_is_not_credited_and_uttara_bhadrapada_is():
    r = m.EVENT_RULES["griha_pravesh"]
    assert "Hasta" not in r["good_nakshatras"]
    assert "Uttara Bhadrapada" in r["good_nakshatras"]
    # Neither book names Hasta as a BAD star for a house entry; it is just not on their lists.
    assert "Hasta" not in r["avoid_nakshatras"]


def test_griha_pravesh_good_set_is_exactly_what_both_books_list():
    # Raman's six best + Anuradha and Revati; Rao's row lists the same eight (plus Dhanishta and
    # Satabhisha, which Raman does not, so they stay uncredited as contested).
    assert m.EVENT_RULES["griha_pravesh"]["good_nakshatras"] == {
        "Rohini", "Mrigashira", "Uttara Phalguni", "Uttara Ashadha", "Chitra",
        "Uttara Bhadrapada", "Anuradha", "Revati"}


def test_griha_pravesh_scoring_changes_with_the_sets():
    _, hasta_reason, _ = _score("griha_pravesh", "Hasta")
    _, ub_reason, _ = _score("griha_pravesh", "Uttara Bhadrapada")
    assert "good nakshatra (Hasta)" not in hasta_reason
    assert "good nakshatra (Uttara Bhadrapada)" in ub_reason


def test_vidyarambh_ardra_is_good_not_avoided():
    r = m.EVENT_RULES["vidyarambh"]
    assert "Ardra" not in r["avoid_nakshatras"]
    assert {"Ardra", "Dhanishta", "Shatabhisha"} <= r["good_nakshatras"]
    _, reason, _ = _score("vidyarambh", "Ardra")
    assert "good nakshatra (Ardra)" in reason


def test_vidyarambh_purnima_is_avoided_like_amavasya():
    r = m.EVENT_RULES["vidyarambh"]
    assert {"Purnima", "Amavasya"} <= r["avoid_tithis"]
    # And no nakshatra sits in both lists for any of the four events this finder carries.
    for ev, rules in m.EVENT_RULES.items():
        assert not (rules["good_nakshatras"] & rules["avoid_nakshatras"]), ev


def test_vidyarambh_thursday_peak_is_labelled_as_this_finders_convention():
    # Raman's one explicit best day for education is Wednesday morning. The code keeps Thursday
    # (Jupiter, karaka of learning) and says so next to the key, so the next reader does not take
    # it for a sourced rule (#1059 item 4).
    assert m.EVENT_RULES["vidyarambh"]["peak_day"] == "Thursday"
    src = open(m.__file__, encoding="utf-8").read()
    i = src.index('"peak_day":   "Thursday"')
    assert "FINDER'S CONVENTION" in src[max(0, i - 700):i]
