"""#1504: Shashti and Dwadashi in the avoid_tithis sets of Vivah and Griha Pravesh.

Source: knowledge/vedic_reference.md 29.9 and the 29.13 Griha Pravesh row. B.V. Raman, *Muhurtha*
(1948): the general avoid list is the 4th, 6th, 8th, 12th, 14th, Full Moon and New Moon, and the
marriage chapter rejects the 8th, 12th and 6th. Rao's Table 79 Wedding row lists 12 but not 6; its
Griha Pravesh row lists neither 6 nor 12. Ruling (astro-auditor, #1504): Griha Pravesh adds Shashti
and Dwadashi; Vivah adds Shashti; the Vivah bright-half Dwadashi is CONTESTED (#1022) and stays
neutral, so it is deliberately NOT in vivah's avoid_tithis.

Contested and neighbouring rows are pinned UNCHANGED on purpose (business, vidyarambh and namkaran
sets, Navami, Purnima). `data/` is absent on the runner, so these tests pin the code to that
section, not to the books.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from astro_ai import muhurat as m

NO_COMBUST = {"jupiter": False, "venus": False, "mercury": False}
EVENTS = tuple(m.EVENT_RULES)
SARVARTHA = "Sarvartha Siddhi Yoga (universally auspicious)"
BOOSTERS = [(SARVARTHA,), ("Amrit Siddhi (Sun + Hasta)",), ("Ravi Yoga",),
            ("Amrit Siddhi (Sun + Hasta)", SARVARTHA, "Ravi Yoga")]


# Monday, not Thursday: Thursday + Shashti is a Dagdha pair, which would return "avoid" with the
# "dagdha" flag before the tithi rule is reached and hide whether the new entry fires.
def _score(event, tithi, paksha, weekday="Monday", nakshatra="Rohini", boosters=()):
    panchang = SimpleNamespace(tithi_name=tithi, tithi_paksha=paksha)
    return m.score_event(event, panchang, weekday, nakshatra, False, False, "", "",
                         NO_COMBUST, boosters=boosters)


def _by_date(event, d):
    return {c.d: c for c in m.find_candidates(event, "New Delhi", d, 1)}[d]


def test_griha_pravesh_avoid_set_is_ramans_general_list_plus_navami():
    assert m.EVENT_RULES["griha_pravesh"]["avoid_tithis"] == {
        "Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi", "Chaturdashi", "Amavasya",
        "Purnima"}


def test_vivah_avoid_set_adds_shashti_and_not_dwadashi():
    avoid = m.EVENT_RULES["vivah"]["avoid_tithis"]
    assert avoid == {"Chaturthi", "Shashti", "Ashtami", "Navami", "Chaturdashi", "Amavasya",
                     "Purnima"}
    # The 12th is contested (#1022): neither credited nor excluded in the bright half.
    assert "Dwadashi" not in avoid
    assert "Dwadashi" not in m.EVENT_RULES["vivah"]["good_tithis"]


@pytest.mark.parametrize("event", EVENTS)
def test_good_and_avoid_tithis_are_disjoint_for_every_event(event):
    rules = m.EVENT_RULES[event]
    assert not (rules["good_tithis"] & rules["avoid_tithis"]), event


def test_other_events_avoid_sets_are_unchanged():
    assert m.EVENT_RULES["business"]["avoid_tithis"] == {
        "Chaturthi", "Ashtami", "Navami", "Chaturdashi", "Amavasya", "Purnima"}
    assert m.EVENT_RULES["vidyarambh"]["avoid_tithis"] == {
        "Chaturthi", "Ashtami", "Navami", "Chaturdashi", "Amavasya", "Purnima"}
    assert m.EVENT_RULES["namkaran"]["avoid_tithis"] == {
        "Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi", "Chaturdashi", "Amavasya",
        "Purnima"}


@pytest.mark.parametrize("paksha", ["Shukla", "Krishna"])
@pytest.mark.parametrize("tithi", ["Shashti", "Dwadashi"])
def test_griha_pravesh_is_avoid_with_the_flag_in_both_pakshas(tithi, paksha):
    rating, reason, flags = _score("griha_pravesh", tithi, paksha)
    assert (rating, flags) == ("avoid", ("avoid_tithi",)), (tithi, paksha, rating, reason)
    assert f"Avoid tithi ({tithi})" == reason


@pytest.mark.parametrize("paksha", ["Shukla", "Krishna"])
def test_vivah_shashti_is_avoid_with_the_flag_in_both_pakshas(paksha):
    rating, reason, flags = _score("vivah", "Shashti", paksha)
    assert (rating, flags) == ("avoid", ("avoid_tithi",)), (paksha, rating, reason)


@pytest.mark.parametrize("boosters", BOOSTERS)
@pytest.mark.parametrize("event,tithi", [("griha_pravesh", "Shashti"), ("griha_pravesh", "Dwadashi"),
                                         ("vivah", "Shashti")])
def test_a_booster_cannot_lift_the_new_avoid_tithis(event, tithi, boosters):
    # 2027-02-12 and 2027-01-27 were "good"/"excellent" only because Sarvartha Siddhi lifted a Shashti.
    for paksha in ("Shukla", "Krishna"):
        assert _score(event, tithi, paksha, boosters=boosters)[0] == "avoid", (event, tithi, paksha)


def test_vivah_shukla_dwadashi_is_not_excluded():
    rating, reason, flags = _score("vivah", "Dwadashi", "Shukla")
    assert rating != "avoid" and "avoid_tithi" not in flags, (rating, reason, flags)
    assert "good tithi (Dwadashi)" not in reason


def test_vivah_krishna_dwadashi_is_still_the_dark_half_exclusion():
    rating, _reason, flags = _score("vivah", "Dwadashi", "Krishna")
    assert (rating, flags) == ("avoid", ("avoid_krishna_tithi",))


# Real dates, New Delhi, read out of find_candidates on 2026-11-27. Each was good or excellent on
# a booster or a missing set entry before #1504.
def test_real_dates_flip_to_avoid():
    cases = [
        ("vivah", date(2027, 2, 12), "Shashti", "Shukla"),
        ("vivah", date(2027, 1, 27), "Shashti", "Krishna"),
        ("griha_pravesh", date(2026, 12, 5), "Dwadashi", "Krishna"),
        ("griha_pravesh", date(2027, 2, 18), "Dwadashi", "Shukla"),
    ]
    for event, d, tithi, paksha in cases:
        c = _by_date(event, d)
        assert (c.tithi, c.tithi_paksha) == (tithi, paksha), (event, d, c.tithi, c.tithi_paksha)
        assert (c.rating, c.flags) == ("avoid", ("avoid_tithi",)), (event, d, c.rating, c.flags)


def test_vivah_on_a_bright_dwadashi_is_not_avoided_by_a_tithi_rule():
    c = _by_date("vivah", date(2027, 2, 18))
    assert (c.tithi, c.tithi_paksha) == ("Dwadashi", "Shukla")
    assert c.rating != "avoid" and "avoid_tithi" not in c.flags


def test_vivah_rules_summary_line_lists_the_avoided_tithis_it_applies():
    line = next(s for s in m.EVENT_LANDING["vivah"]["rules_summary"]
                if s.startswith("Favourable tithi"))
    assert line.startswith("Favourable tithi: 2, 3, 5, 7, 10, 11, 13 (avoid 4, 6, 8, 9, 14, "
                           "Amavasya, Purnima)")
    # 4, 6, 8, 9, 14 are the numbered entries of the set, so the line cannot drift from it again.
    numbered = {"Chaturthi": 4, "Shashti": 6, "Ashtami": 8, "Navami": 9, "Chaturdashi": 14}
    listed = {n for t, n in numbered.items() if t in m.EVENT_RULES["vivah"]["avoid_tithis"]}
    assert listed == {4, 6, 8, 9, 14}
