"""One verdict, one moment: the finder reads every anga at the same instant (#1020), and a
row says when Abhijit lies inside Rahu Kaal or Bhadra (#1025).

Before #1020 `find_candidates` took tithi, karana and yoga from `compute_panchang` (local
sunrise) but the nakshatra, Panchak, Nitya Yoga and combustion at 12:00, so 2027-04-19 was rated
excellent on "Trayodashi + Hasta" although by noon, when the Hasta was read, the tithi is
Chaturdashi, an avoid tithi. Rao (knowledge/vedic_reference.md 29.7) judges the angas at the
time of the muhurta; nothing there reads different angas at different instants.

#1025 is display-only: no rating reads the overlap, because knowledge/ ranks neither window.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from astro_ai import chart, muhurat as m
from astro_ai.chart import _nitya_yoga_at, _tithi_at, julian_day_utc

IST = ZoneInfo("Asia/Kolkata")
NEW_DELHI = (28.6139, 77.2090, "Asia/Kolkata")
TROMSO = (69.6492, 18.9553, "Europe/Oslo")


@pytest.fixture(autouse=True)
def _delhi(monkeypatch):
    # conftest resolves every place to Mumbai; the minutes quoted in #1020/#1025 are New Delhi's.
    monkeypatch.setattr(chart, "geocode_place", lambda place: NEW_DELHI)


def _noon(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, m.MUHURTA_INSTANT_HOUR, tzinfo=IST)


def test_the_issue_repro_2027_04_19_is_avoid_on_the_tithi_that_holds_with_the_hasta():
    c = m.find_candidates("griha_pravesh", "New Delhi", date(2027, 4, 19), 1)[0]
    assert (c.nakshatra, c.tithi) == ("Hasta", "Chaturdashi")
    assert c.rating == "avoid" and "Chaturdashi" in c.reason, (c.rating, c.reason)


@pytest.mark.parametrize("event", ["griha_pravesh", "vivah"])
def test_every_column_of_a_row_is_read_at_one_instant(event):
    rows = m.find_candidates(event, "New Delhi", date(2026, 11, 14), 60)
    assert len(rows) == 60
    for c in rows:
        jd = julian_day_utc(_noon(c.d))
        _i, tithi, paksha, _s = _tithi_at(jd)
        assert (c.tithi, c.tithi_paksha) == (tithi, paksha), c.d
        assert c.nitya_yoga == _nitya_yoga_at(jd)[1], c.d


def test_the_judging_hour_is_the_same_one_nakshatra_and_combustion_always_used():
    assert m.MUHURTA_INSTANT_HOUR == 12


def test_the_abujha_row_shows_the_tithi_its_label_names():
    # 2026-11-20: Devuthani Ekadashi is a kshaya tithi (Dashami at sunrise, Ekadashi at noon).
    c = {x.d: x for x in m.find_candidates("griha_pravesh", "New Delhi", date(2026, 11, 20), 1)}[date(2026, 11, 20)]
    assert "Devuthani Ekadashi" in c.reason
    assert c.tithi == "Ekadashi"


def test_abhijit_rahu_kaal_overlap_is_named_on_every_wednesday_and_friday_and_never_on_a_monday():
    rows = m.find_candidates("griha_pravesh", "New Delhi", date(2026, 11, 14), 60)
    seen = {"Wednesday": 0, "Friday": 0}
    for c in rows:
        has = any("Rahu Kaal" in n for n in c.abhijit_overlaps)
        if c.weekday in seen:
            assert has, (c.d, c.weekday, c.abhijit_muhurta, c.rahu_kaal)
            seen[c.weekday] += 1
        if c.weekday == "Monday":
            assert not has, (c.d, c.abhijit_overlaps)
    assert all(seen.values())
    c = {x.d: x for x in rows}[date(2026, 11, 20)]
    assert c.abhijit_overlaps[0] == "Abhijit and Rahu Kaal overlap 11:45-12:06", c.abhijit_overlaps


def test_no_rating_can_read_the_overlap():
    # #1025 is display-only: score_event takes no overlap argument, so it cannot read one.
    import inspect
    assert "overlap" not in " ".join(inspect.signature(m.score_event).parameters)


def _t(h, mi=0, s=0):
    return datetime(2026, 11, 20, h, mi, s, tzinfo=IST)


def test_abhijit_overlaps_unit_cases():
    zone = IST
    abhijit = (_t(11, 45), _t(12, 27))
    # Rahu Kaal covering the first 21 minutes
    assert m._abhijit_overlaps(abhijit, (_t(10, 46), _t(12, 6)), [], zone) == (
        "Abhijit and Rahu Kaal overlap 11:45-12:06",)
    # a touch of less than a minute is not reported
    assert m._abhijit_overlaps(abhijit, (_t(10, 0), _t(11, 45, 30)), [], zone) == ()
    # disjoint
    assert m._abhijit_overlaps(abhijit, (_t(13, 0), _t(14, 30)), [], zone) == ()
    # Bhadra spans arrive as UTC instants and are reported in local time
    bh = [(_t(12, 10).astimezone(timezone.utc), _t(15, 0).astimezone(timezone.utc))]
    assert m._abhijit_overlaps(abhijit, (_t(13, 0), _t(14, 30)), bh, zone) == (
        "Abhijit and Bhadra (Vishti) overlap 12:10-12:27",)
    # both at once, Rahu Kaal first
    both = m._abhijit_overlaps(abhijit, (_t(10, 46), _t(12, 6)), bh, zone)
    assert [n.split(" overlap")[0] for n in both] == ["Abhijit and Rahu Kaal", "Abhijit and Bhadra (Vishti)"]


def test_a_date_with_no_daylight_span_carries_no_overlap_note(monkeypatch):
    # Reykjavik, June 2026: 15 dates hold no ordinary sunrise-to-sunset span, the windows are
    # blank (#228). The arithmetic is meaningless there (Abhijit '12:47-14:11' is 84 minutes), so
    # an overlap computed from it would be a confident wrong note: 7 of those 15 dates would get one.
    monkeypatch.setattr(chart, "geocode_place", lambda place: (64.1466, -21.9426, "Atlantic/Reykjavik"))
    blank = [c for c in m.find_candidates("business", "Reykjavik", date(2026, 6, 10), 30)
             if c.abhijit_muhurta == ""]
    assert len(blank) >= 10, "the fixture no longer reaches the polar dates"
    assert all(c.abhijit_overlaps == () for c in blank), [c.d for c in blank if c.abhijit_overlaps]


def test_the_page_says_when_each_verdict_is_read_and_names_the_overlap():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    page = TestClient(app).post("/muhurat", data={
        "event_type": "griha_pravesh", "city": "New Delhi",
        "start_date": "2026-11-14", "days": 14})
    assert page.status_code == 200
    body = html.unescape(page.text)
    assert "One verdict, one moment" in body and "are all read at 12:00 local time on the date, so" in body
    assert "Abhijit and Rahu Kaal overlap 11:45-12:06" in body
    assert 'read at 12:00 local time on the date">Tithi</th>' in body
