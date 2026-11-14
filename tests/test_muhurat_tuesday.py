"""Tuesday is a HARD exclusion in the muhurat finder, for every event (#1021).

Raman, Muhurtha (1948), knowledge/vedic_reference.md section 29.9: line 790 "Tuesday and
Saturday should be invariably avoided for all good and auspicious work"; the marriage
chapter has Tuesday "invariably rejected"; Rao Table 79 lists Mon, Wed, Thu, Fri for a
wedding. `score_event` used to take one point off, so a Tuesday with a good tithi and
nakshatra rated 'acceptable' and a booster lifted it to 'excellent'.

The dates below were read out of `find_candidates` on 2026-11-14 (New Delhi); the
weekday of each is asserted by the calendar, not by the code under test. Saturday is
contested inside Raman and stays a one-point penalty, so it is pinned the other way.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from astro_ai import muhurat as m

EVENTS = ("vivah", "griha_pravesh", "namkaran", "vidyarambh", "business")
OK_RATINGS = {"acceptable", "good", "excellent"}


def _by_date(event, start, days):
    return {c.d: c for c in m.find_candidates(event, "New Delhi", start, days)}


def test_the_issue_repro_tuesdays_are_avoid_with_the_flag():
    cands = _by_date("vivah", date(2027, 1, 1), 200)
    # 2027-06-29 is the Amrit Siddhi (Tuesday + Ashwini) case the reason must disclose.
    for d in (date(2027, 1, 19), date(2027, 2, 16), date(2027, 6, 29)):
        assert d.strftime("%A") == "Tuesday"
        c = cands[d]
        assert c.rating == "avoid", (d, c.rating, c.reason)
        assert "avoid_weekday" in c.flags, (d, c.flags)
        assert "Raman" in c.reason


def test_no_tuesday_is_acceptable_or_better_for_any_event():
    start = date(2026, 11, 14)
    seen_tuesdays = 0
    for event in EVENTS:
        for c in m.find_candidates(event, "New Delhi", start, 365):
            assert c.d.strftime("%A") == c.weekday
            if c.weekday == "Tuesday":
                seen_tuesdays += 1
                assert c.rating not in OK_RATINGS, (event, c.d, c.rating, c.reason)
    assert seen_tuesdays >= 5 * 50  # the sweep really covered the Tuesdays


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize("boosters", [
    (), ("Amrit Siddhi (Mars + Ashwini)",), ("Sarvartha Siddhi Yoga (universally auspicious)",),
    ("Amrit Siddhi (Mars + Ashwini)", "Sarvartha Siddhi Yoga (universally auspicious)", "Ravi Yoga"),
])
def test_a_booster_cannot_lift_a_tuesday(event, boosters):
    # A day with nothing else against it: favourable tithi, no Panchak, no combustion.
    rules = m.EVENT_RULES[event]
    panchang = SimpleNamespace(tithi_name=sorted(rules["good_tithis"])[0])
    nakshatra = sorted(rules["good_nakshatras"])[0]
    rating, reason, flags = m.score_event(
        event, panchang, "Tuesday", nakshatra, False, False, "", "",
        {"jupiter": False, "venus": False, "mercury": False}, boosters=boosters)
    assert rating == "avoid", (event, boosters, reason)
    assert flags == ("avoid_weekday",)
    assert "Amrit Siddhi" in reason and "does not override" in reason


def test_saturday_is_still_only_a_one_point_penalty():
    # Contested inside Raman (Ch. II avoids it, the marriage chapter calls it middling).
    c = _by_date("vivah", date(2026, 12, 12), 1)[date(2026, 12, 12)]
    assert c.weekday == "Saturday"
    # good tithi (+2) + good nakshatra (+2) - Saturday (1) = 3
    assert c.rating == "acceptable", (c.rating, c.reason)
    assert "avoid weekday (Saturday)" in c.reason
    assert c.flags == ("avoid_weekday",)


def test_sunday_is_not_a_good_weekday_for_vivah():
    c = _by_date("vivah", date(2027, 1, 24), 1)[date(2027, 1, 24)]
    assert c.weekday == "Sunday"
    assert c.rating == "good", (c.rating, c.reason)   # tithi + nakshatra alone make 4
    assert "good weekday" not in c.reason, c.reason
    assert "Sunday" not in m.EVENT_RULES["vivah"]["good_days"]


def test_no_event_lists_tuesday_as_a_good_weekday():
    for event, rules in m.EVENT_RULES.items():
        assert "Tuesday" not in rules["good_days"], event


def _namkaran_tuesday(event):
    cands = m.find_candidates(event, "New Delhi", date(2027, 1, 1), 60)
    return next(c for c in cands if c.weekday == "Tuesday" and c.flags == ("avoid_weekday",))


def test_namkaran_discloses_ramans_child_day_exception():
    reason = _namkaran_tuesday("namkaran").reason
    assert "10th, 12th or 16th day" in reason
    assert "no birth date" in reason


def test_other_events_do_not_carry_the_namkaran_exception():
    assert "10th, 12th or 16th" not in _namkaran_tuesday("vivah").reason
