"""Vivah: the waning-half 11th-13th are excluded, the 12th is not credited (#1022).

Raman, Muhurtha (1948), marriage chapter, as knowledge/vedic_reference.md section 29.9
paraphrases it: rejects "the 11th of the dark half through New Moon", the Riktha tithis,
and the 8th, 12th and 6th, and calls the bright-half 2nd, 3rd, 5th, 7th, 10th, 11th and
13th best. Rao's Table 79 Wedding row (knowledge/grahas.md) lists 2, 3, 5, 7, 10, 11, 12,
13, 15 with no paksha, so the 12th is contested between the two books and gets no credit.

`find_candidates` used to key `good_tithis` on the tithi NAME alone, so Krishna Ekadashi,
Dwadashi and Trayodashi each earned +2 for a wedding like their bright-half namesakes.

The dates below were read out of `find_candidates` on 2026-11-15 (New Delhi). The other
four events have no event-specific tithi rule in the knowledge files, so their ratings
are pinned unchanged rather than "fixed".
"""
from __future__ import annotations

import html
from datetime import date
from types import SimpleNamespace

import pytest

from astro_ai import muhurat as m

OK_RATINGS = {"acceptable", "good", "excellent"}
DARK_TITHIS = ("Ekadashi", "Dwadashi", "Trayodashi")
OTHER_EVENTS = ("griha_pravesh", "business", "vidyarambh", "namkaran")
NO_COMBUST = {"jupiter": False, "venus": False, "mercury": False}


def _by_date(event, start, days):
    return {c.d: c for c in m.find_candidates(event, "New Delhi", start, days)}


def _score(event, tithi, paksha, weekday="Thursday", nakshatra="Rohini", boosters=()):
    panchang = SimpleNamespace(tithi_name=tithi, tithi_paksha=paksha)
    return m.score_event(event, panchang, weekday, nakshatra, False, False, "", "",
                         NO_COMBUST, boosters=boosters)


def test_the_issue_repro_dark_half_11th_to_13th_are_avoid_with_the_flag():
    cands = _by_date("vivah", date(2026, 12, 1), 120)
    # The tithi is the one at the finder's single judging instant (noon, #1020), not at
    # sunrise: 12-04 Ekadashi, 12-05 Dwadashi (was 'excellent'); 2027-03-04/05 Dwadashi,
    # Trayodashi (the same two dates read Ekadashi/Dwadashi on the old sunrise tithi).
    got = [(date(2026, 12, 4), "Ekadashi"), (date(2026, 12, 5), "Dwadashi")]
    cands.update(_by_date("vivah", date(2027, 3, 4), 2))
    got += [(date(2027, 3, 4), "Dwadashi"), (date(2027, 3, 5), "Trayodashi")]
    for d, tithi in got:
        c = cands[d]
        assert (c.tithi_paksha, c.tithi) == ("Krishna", tithi), (d, c.tithi_paksha, c.tithi)
        assert c.rating == "avoid", (d, c.rating, c.reason)
        assert c.flags == ("avoid_krishna_tithi",), (d, c.flags)
        assert "Raman" in c.reason and "dark half" in c.reason, c.reason


def test_no_dark_half_11th_to_13th_is_acceptable_or_better_for_vivah():
    seen = 0
    for c in m.find_candidates("vivah", "New Delhi", date(2026, 11, 14), 365):
        if c.tithi_paksha == "Krishna" and c.tithi in DARK_TITHIS:
            seen += 1
            assert c.rating == "avoid", (c.d, c.tithi, c.rating, c.reason)
    assert seen >= 30  # the sweep really covered them (36 on 2026-11-15)


@pytest.mark.parametrize("tithi", DARK_TITHIS)
@pytest.mark.parametrize("boosters", [
    (), ("Amrit Siddhi (Sun + Hasta)", "Sarvartha Siddhi Yoga (universally auspicious)", "Ravi Yoga"),
])
def test_a_booster_cannot_lift_a_dark_half_tithi(tithi, boosters):
    rating, reason, flags = _score("vivah", tithi, "Krishna", boosters=boosters)
    assert rating == "avoid", (tithi, reason)
    assert flags == ("avoid_krishna_tithi",)
    assert tithi in reason


@pytest.mark.parametrize("tithi", ["Ekadashi", "Trayodashi"])
def test_the_bright_half_namesakes_are_not_excluded_and_keep_the_credit(tithi):
    rating, reason, flags = _score("vivah", tithi, "Shukla")
    assert rating != "avoid", (tithi, reason)
    assert f"good tithi ({tithi})" in reason
    assert "avoid_krishna_tithi" not in flags
    # and on the real calendar: 2027-01-20 is a Shukla Trayodashi that rates excellent
    c = _by_date("vivah", date(2027, 1, 20), 1)[date(2027, 1, 20)]
    assert (c.tithi_paksha, c.tithi, c.rating) == ("Shukla", "Trayodashi", "excellent")
    assert "good tithi (Trayodashi)" in c.reason


def test_bright_half_dwadashi_is_neutral_not_credited_and_not_excluded():
    rating, reason, flags = _score("vivah", "Dwadashi", "Shukla")
    assert rating != "avoid", reason
    assert "good tithi" not in reason, reason
    assert flags == ()
    assert "Dwadashi" not in m.EVENT_RULES["vivah"]["good_tithis"]
    assert "Dwadashi" not in m.EVENT_RULES["vivah"]["avoid_tithis"]
    for c in m.find_candidates("vivah", "New Delhi", date(2026, 11, 14), 365):
        assert "good tithi (Dwadashi)" not in c.reason, (c.d, c.reason)
    # Shukla Dwadashi 2027-05-17 (Monday): was 'acceptable' on the Dwadashi credit, now 'caution'
    c = _by_date("vivah", date(2027, 5, 17), 1)[date(2027, 5, 17)]
    assert (c.tithi_paksha, c.tithi, c.rating) == ("Shukla", "Dwadashi", "caution")


def test_shashti_and_purnima_are_unchanged():
    assert "Shashti" not in m.EVENT_RULES["vivah"]["good_tithis"]
    assert "Shashti" not in m.EVENT_RULES["vivah"]["avoid_tithis"]
    assert "Purnima" in m.EVENT_RULES["vivah"]["avoid_tithis"]


def test_only_vivah_carries_the_paksha_aware_key():
    for event, rules in m.EVENT_RULES.items():
        assert ("avoid_krishna_tithis" in rules) == (event == "vivah"), event


@pytest.mark.parametrize("event", OTHER_EVENTS)
@pytest.mark.parametrize("tithi", DARK_TITHIS)
def test_other_events_are_not_excluded_on_a_dark_half_tithi(event, tithi):
    rating, reason, flags = _score(event, tithi, "Krishna")
    assert "avoid_krishna_tithi" not in flags, (event, tithi)
    # Same score a Shukla day of the same tithi gets: the paksha changes nothing here.
    assert (rating, reason, flags) == _score(event, tithi, "Shukla"), (event, tithi)


def test_other_events_ratings_on_a_krishna_ekadashi_and_dwadashi_are_pinned():
    # Measured identical before and after the change over 365 days for all four events (#1022);
    # namkaran's 12th changed afterwards, see the row below.
    pinned = {
        ("griha_pravesh", date(2026, 12, 4)): "excellent",
        ("business", date(2026, 12, 4)): "excellent",
        ("vidyarambh", date(2026, 12, 4)): "excellent",
        ("namkaran", date(2026, 12, 4)): "excellent",
        ("griha_pravesh", date(2026, 12, 5)): "good",
        ("vidyarambh", date(2026, 12, 5)): "excellent",
        # #1060: Raman's Namakarana avoid list carries the 12th, so this was "excellent" only on the
        # Dwadashi credit the books do not support.
        ("namkaran", date(2026, 12, 5)): "avoid",
        ("business", date(2027, 3, 5)): "excellent",
    }
    for (event, d), want in pinned.items():
        c = _by_date(event, d, 1)[d]
        assert c.tithi_paksha == "Krishna" and c.tithi in DARK_TITHIS, (event, d, c.tithi)
        assert c.rating == want, (event, d, c.rating, c.reason)


# ─── what the page says ─────────────────────────────────────────────────────────

RAMAN_SENTENCE = ("Wedding dates on the 11th, 12th or 13th tithi of the waning (Krishna paksha) "
                  "half are excluded, following B.V. Raman's Muhurtha, which rejects the "
                  "dark-half 11th through New Moon for marriage")
TWELFTH_SENTENCE = ("The bright-half 12th is not credited: Rao's wedding guideline table lists "
                    "it, Raman's rejects it, so the finder gives it no credit either way")


def _vivah_summary():
    return m.EVENT_LANDING["vivah"]["rules_summary"]


def test_the_rules_summary_carries_both_disclosures_and_never_says_classical_there():
    lines = _vivah_summary()
    assert RAMAN_SENTENCE in lines
    assert TWELFTH_SENTENCE in lines
    for line in (RAMAN_SENTENCE, TWELFTH_SENTENCE):
        assert "classical" not in line.lower()


def test_the_favourable_tithi_line_no_longer_claims_the_12th():
    (fav,) = [x for x in _vivah_summary() if x.startswith("Favourable tithi")]
    listed = fav.split(":", 1)[1].split("(", 1)[0]
    assert "12" not in listed, fav
    assert "2, 3, 5, 7, 10, 11, 13" in listed
    assert "waning half" in fav


def test_the_real_route_renders_the_disclosure_and_the_learn_page_agrees():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    client = TestClient(app)
    page = client.get("/muhurat/vivah")
    assert page.status_code == 200
    body = html.unescape(page.text)
    assert RAMAN_SENTENCE in body and TWELFTH_SENTENCE in body

    learn = client.get("/learn/vivah-muhurat-2027")
    assert learn.status_code == 200
    text = html.unescape(learn.text)
    assert "rejects the dark-half 11th through New Moon for marriage" in text
    assert "2, 3, 5, 7, 10, 11, 12, 13 (both bright and dark halves)" not in text
