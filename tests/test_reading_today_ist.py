"""Rashifal, /today, /outlook and the email path take "today" from the IST day (#794).

Defect this guards: those surfaces read `date.today()` -- the server's UTC date on
Cloud Run -- so between 00:00 and 05:30 IST they named, cached and looked up
YESTERDAY: the date in the page, the day-pinned sky behind the reading and the
cache key. The nightly job (#515) writes the new IST day's blob at ~04:15 IST, so
a UTC-keyed page could not even see it. Follow-up to #593, which fixed /panchang.

The clock is frozen at 2026-10-29T23:00Z = Fri 2026-10-30 04:30 IST, inside the
window. The UTC date there is the 29th, so every assertion below is red against
`date.today()` and green against `chart.reading_today()`.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

FROZEN = datetime(2026, 10, 29, 23, 0, tzinfo=timezone.utc)   # Fri 30 Oct, 04:30 IST
EVENING = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)  # Thu 29 Oct, 17:30 IST


class _Clock:
    def __init__(self, at: datetime):
        self.at = at

    def datetime_cls(self):
        clock = self

        class _Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.at.astimezone(tz) if tz else clock.at.replace(tzinfo=None)

        return _Frozen


@pytest.fixture
def clock(monkeypatch):
    from astro_ai import chart

    c = _Clock(FROZEN)
    monkeypatch.setattr(chart, "datetime", c.datetime_cls())
    return c


def test_reading_today_is_the_ist_date_not_the_utc_date(clock):
    from astro_ai.chart import reading_today

    assert reading_today() == date(2026, 10, 30)
    clock.at = EVENING
    assert reading_today() == date(2026, 10, 29)


def test_the_rashifal_grid_names_the_ist_day(client, clock):
    r = client.get("/rashifal")
    assert r.status_code == 200
    assert "30 October" in r.text and "29 October" not in r.text, \
        "the grid named the server's UTC date"


def test_a_single_rashifal_is_looked_up_and_dated_by_the_ist_day(
        client, stub_llm, rashi_body, clock, monkeypatch):
    """The key the page reads and writes is the IST day, the one the nightly job writes.

    Spied rather than seeded: `daily_cache.put` sweeps entries older than seven
    days by the REAL clock, which would delete a blob dated at the frozen day.
    """
    from astro_ai import daily_cache

    keys: list[tuple[str, str]] = []
    real_get, real_put = daily_cache.get, daily_cache.put
    monkeypatch.setattr(daily_cache, "get", lambda ns, k, d=None: (
        keys.append(("get", d)), real_get(ns, k, d))[1])
    monkeypatch.setattr(daily_cache, "put", lambda ns, k, p, d=None: (
        keys.append(("put", d)), real_put(ns, k, p, d))[1])
    stub_llm(lambda _n: rashi_body(heading="Aries / Mesha"))

    r = client.get("/rashifal/aries")

    assert r.status_code == 200
    assert "30 October" in r.text and "29 October" not in r.text
    assert keys and {d for _, d in keys} == {"2026-10-30"}, keys


def test_the_reading_is_pinned_to_the_ist_day(client, stub_llm, rashi_body, clock, monkeypatch):
    from astro_ai.chart import rashifal_day_moment
    from astro_ai.routes import rashifal

    seen: list = []
    real = rashifal.compute_transit_snapshot

    def spy(chart, when=None):
        seen.append(when)
        return real(chart, when=when)

    monkeypatch.setattr(rashifal, "compute_transit_snapshot", spy)
    stub_llm(lambda _n: rashi_body(heading="Aries / Mesha"))
    assert client.get("/rashifal/aries").status_code == 200
    assert seen and all(w == rashifal_day_moment(date(2026, 10, 30)) for w in seen), seen


@pytest.mark.parametrize("path", ["/today", "/monthly"])
def test_today_and_outlook_name_the_ist_day(client, saved_chart, stub_llm, clock, path):
    saved_chart()
    stub_llm("## Reading\n\nA steady day for measured work. " * 30)
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    assert "30 October" in r.text and "29 October" not in r.text, path


def test_the_email_context_dates_the_message_by_the_ist_day(clock):
    from astro_ai.routes import subscribe

    ctx = subscribe._email_context(lang="en", city=None)
    assert ctx["today_iso"] == "2026-10-30"
