"""`/festivals` and `/muhurat` must take "today" from the IST day (#798).

Defect this guards: both routes read `date.today()` -- the server's UTC date on
Cloud Run -- so from 00:00 to 05:30 IST they were a day behind the home strip
and `/panchang`, which #593/#793 had already moved onto `chart.local_today`.
`/festivals` cut its whole six-month window, its "in N days" copy and its
`today_iso` from that date; `/muhurat` and `/muhurat/<event>` pre-filled the
start-date input with it, so a visitor at 04:30 IST was offered yesterday as the
earliest muhurat date.

The clock is frozen at 2026-10-29T23:00Z = Fri 2026-10-30 04:30 IST, the same
instant as tests/test_panchang_local_day.py. The server's UTC `date.today()` is
frozen to the 29th as well, so a route still reading it is a day behind the
strip rather than merely different from it by accident of the wall clock.
"""
from __future__ import annotations

import datetime as _dt
import re
from datetime import date, datetime, timezone

import pytest

FROZEN = datetime(2026, 10, 29, 23, 0, tzinfo=timezone.utc)  # Fri 30 Oct, 04:30 IST


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN.astimezone(tz) if tz else FROZEN.replace(tzinfo=None)


class _FrozenDate(date):
    @classmethod
    def today(cls):
        # The server's zone is UTC on Cloud Run: the 29th, not the IST 30th.
        return date(2026, 10, 29)


@pytest.fixture
def clock(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import festivals as festivals_route

    monkeypatch.setattr(chart, "datetime", _FrozenDatetime)
    # muhurat.py reads `datetime.date` through a function-local import, so the
    # stdlib module attribute is what a pre-fix route would see.
    monkeypatch.setattr(_dt, "date", _FrozenDate)
    monkeypatch.setattr(festivals_route, "date", _FrozenDate, raising=False)


def _prefill_start(html: str) -> str:
    m = re.search(r'name="start_date"[^>]*value="([^"]*)"|value="([^"]*)"[^>]*name="start_date"', html)
    assert m, "no start_date input on the page"
    return m.group(1) or m.group(2)


def test_festivals_window_starts_on_the_ist_day(client, clock, monkeypatch):
    """The registry is asked for the 30th, and the page says so."""
    from astro_ai import festival_registry

    asked: list[date] = []
    real_upcoming = festival_registry.upcoming

    def _spy(today, *a, **kw):
        asked.append(today)
        return real_upcoming(today, *a, **kw)

    monkeypatch.setattr(festival_registry, "upcoming", _spy)
    resp = client.get("/festivals")

    assert resp.status_code == 200
    assert asked == [date(2026, 10, 30)], f"upcoming() was given {asked}, not the IST day"
    assert "30 October 2026" in resp.text, "the window does not start on the IST day"
    assert "29 October 2026" not in resp.text


@pytest.mark.parametrize("path", ["/muhurat", "/muhurat/vivah"])
def test_muhurat_prefills_the_ist_day(client, clock, path):
    resp = client.get(path)

    assert resp.status_code == 200
    assert _prefill_start(resp.text) == "2026-10-30"
