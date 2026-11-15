"""The finder's Bhadra (Vishti) window is the true karana span, not a 3-hour sample (#1019).

`_bhadra_window_for_day` sampled Vishti at 00, 03, ... 21 o'clock and reported the first
sampled hour as the start. Vishti that began at 09:18 was shown from 12:00 (2026-12-20,
New Delhi), so the minutes before the stated start read as clear; Vishti that began after
21:00 produced no window at all. Source for the rule itself: knowledge/vedic_reference.md
section 29.9 (Raman, Muhurtha: Vishti is "invariably" discarded for a marriage).

The oracle here is independent of the code under test: a 5-minute scan of
`chart._karana_at`, the function /panchang uses, over the civil day.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from astro_ai import muhurat as m
from astro_ai.chart import _karana_at, compute_chart, julian_day_utc

STEP = timedelta(minutes=5)
_WINDOW = re.compile(
    r"Bhadra active (?:(?P<a>\d\d:\d\d)-(?P<b>\d\d:\d\d)|until (?P<until>\d\d:\d\d)"
    r"|from (?P<from>\d\d:\d\d)|(?P<all>all day))"
)


def _chart(city="New Delhi"):
    return compute_chart("2026-12-20", "12:00", city)


def _noon(d, zone):
    return datetime.combine(d, time(12), tzinfo=zone)


def _truth(d, zone):
    """Minutes-of-day (local) at which Vishti is active, scanned every 5 minutes."""
    start = datetime.combine(d, time.min, tzinfo=zone)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=zone)
    out, t = [], start
    while t < end:
        if _karana_at(julian_day_utc(t))[1] == "Vishti":
            out.append(t)
        t += STEP
    return start, end, out


def _stated(window, d, zone):
    """[(start, end)] local datetimes the sentence claims, or [] for no window."""
    if not window:
        return []
    day0 = datetime.combine(d, time.min, tzinfo=zone)
    day1 = datetime.combine(d + timedelta(days=1), time.min, tzinfo=zone)

    def at(hhmm):
        return datetime.combine(d, time.fromisoformat(hhmm), tzinfo=zone)

    spans = []
    for g in _WINDOW.finditer(window):
        if g["all"]:
            spans.append((day0, day1))
        elif g["until"]:
            spans.append((day0, at(g["until"])))
        elif g["from"]:
            spans.append((at(g["from"]), day1))
        else:
            spans.append((at(g["a"]), at(g["b"])))
    assert spans, window
    return spans


def _check_day(chart, d, zone):
    window = m._bhadra_window_for_day(chart, _noon(d, zone))
    day0, day1, active = _truth(d, zone)
    stated = _stated(window, d, zone)
    # 1. NO Vishti minute is outside the stated window -- the defect itself.
    for t in active:
        assert any(s <= t < e for s, e in stated), (d, t.isoformat(), window)
    # 2. The window is not wider than the truth by more than the scan step either:
    #    every stated edge that is a real boundary sits within one step of Vishti.
    for s, e in stated:
        if s > day0:
            assert any(abs(t - s) <= STEP for t in active), (d, "start", window)
        if e < day1:
            assert any(abs(t + STEP - e) <= STEP for t in active), (d, "end", window)
    # 3. A window exists exactly when Vishti is active at some point of the day.
    assert bool(window) == bool(active), (d, window, len(active))
    return window, active


def test_the_issue_repro_window_starts_when_vishti_does_not_at_noon():
    zone = ZoneInfo("Asia/Kolkata")
    chart = _chart()
    window = m._bhadra_window_for_day(chart, _noon(date(2026, 12, 20), zone))
    # Was "Bhadra active ~12:00-21:00 (afternoon)": 09:30 read as clear, and it is Vishti.
    assert m._bhadra_active_at(chart, datetime(2026, 12, 20, 9, 30, tzinfo=zone))
    (start, end), = _stated(window, date(2026, 12, 20), zone)
    assert start <= datetime(2026, 12, 20, 9, 30, tzinfo=zone) < end, window
    assert start < datetime(2026, 12, 20, 9, 30, tzinfo=zone), window
    assert "12:00" not in window, window


def test_every_vishti_minute_of_sixty_days_is_inside_the_stated_window():
    zone = ZoneInfo("Asia/Kolkata")
    chart = _chart()
    with_window = 0
    for i in range(60):
        window, _active = _check_day(chart, date(2026, 11, 14) + timedelta(days=i), zone)
        with_window += bool(window)
    assert with_window >= 10, with_window  # Vishti is ~11 h about every 3.5 days


def test_a_vishti_that_starts_after_21_00_still_gets_a_window():
    zone = ZoneInfo("Asia/Kolkata")
    chart = _chart()
    late = []
    for i in range(120):
        d = date(2026, 11, 14) + timedelta(days=i)
        _s, _e, active = _truth(d, zone)
        if active and active[0].hour >= 21 and active[-1] == active[-1].replace(hour=23, minute=55):
            late.append(d)
    assert late, "no late-evening Vishti in the sampled 120 days; widen the range"
    for d in late[:3]:
        window = m._bhadra_window_for_day(chart, _noon(d, zone))
        assert window.startswith("Bhadra active from 2"), (d, window)
        assert "continues into the next day" in window, window


def test_a_vishti_running_in_from_the_day_before_reads_until():
    zone = ZoneInfo("Asia/Kolkata")
    chart = _chart()
    carried = None
    for i in range(120):
        d = date(2026, 11, 14) + timedelta(days=i)
        _s, _e, active = _truth(d, zone)
        if active and active[0].hour == 0 and active[0].minute == 0 and len(active) < 280:
            carried = d
            break
    assert carried, "no Vishti crossing midnight in the sampled range"
    window = m._bhadra_window_for_day(chart, _noon(carried, zone))
    assert window.startswith("Bhadra active until "), window


@pytest.mark.parametrize("day", [date(2027, 3, 28), date(2029, 10, 28)])
def test_a_dst_day_is_measured_in_real_hours(day):
    # Paris springs forward on 2027-03-28 (a 23-hour civil day) and falls back on
    # 2029-10-28 (25 hours). Both days were chosen by scanning for a Vishti edge
    # inside the hour a fixed 24-hour day would get wrong. The finder resolves
    # only Indian cities today, but the function takes any zone, and Vishti does
    # not depend on place.
    zone = ZoneInfo("Europe/Paris")
    chart = _chart()
    for i in range(-2, 3):
        _check_day(chart, day + timedelta(days=i), zone)


def test_the_window_says_when_it_covers_all_of_the_daylight():
    zone = ZoneInfo("Asia/Kolkata")
    chart = _chart()
    d = date(2026, 12, 20)
    rise, sset = _noon(d, zone).replace(hour=10), _noon(d, zone).replace(hour=17)
    assert "(covers sunrise to sunset)" in m._bhadra_window_for_day(
        chart, _noon(d, zone), (rise, sset))
    rise, sset = _noon(d, zone).replace(hour=6), _noon(d, zone).replace(hour=17)
    assert "covers" not in m._bhadra_window_for_day(chart, _noon(d, zone), (rise, sset))
    assert "covers" not in m._bhadra_window_for_day(chart, _noon(d, zone))


def test_the_finder_hands_the_exact_window_to_every_row():
    zone = ZoneInfo("Asia/Kolkata")
    rows = {c.d: c for c in m.find_candidates("vivah", "New Delhi", date(2026, 12, 19), 3)}
    assert rows[date(2026, 12, 19)].bhadra_window == ""
    got = rows[date(2026, 12, 20)].bhadra_window
    (start, _end), = _stated(got, date(2026, 12, 20), zone)
    assert start.time() < time(9, 30), got


def test_the_finder_passes_sunrise_and_sunset_so_a_fully_covered_day_says_so():
    # The suite's geocoder is stubbed to Mumbai, so the days are found by the
    # oracle (a 5-minute scan between that day's own sunrise and sunset), not
    # hard-coded. The rating is NOT changed by this: knowledge/ states no weight
    # for it (see the PR on #1019).
    zone = ZoneInfo("Asia/Kolkata")
    base = compute_chart("2026-11-14", "12:00", "New Delhi")
    rows = m.find_candidates("vivah", "New Delhi", date(2026, 11, 14), 365)
    covered = []
    for c in rows:
        if not c.bhadra_window:
            continue
        p = m.compute_panchang(base, _noon(c.d, zone))
        t, all_vishti = p.sunrise, True
        while t <= p.sunset:
            all_vishti &= _karana_at(julian_day_utc(t))[1] == "Vishti"
            t += STEP
        said = "(covers sunrise to sunset)" in c.bhadra_window
        assert said == all_vishti, (c.d, c.bhadra_window)
        covered.append(said)
    assert any(covered), "no day in the year has Vishti across all daylight; widen the range"
