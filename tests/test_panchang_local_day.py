"""`/panchang` and the home strip must name the same day (#593).

Defect this guards: between 00:00 and 05:30 IST `/panchang` showed YESTERDAY's
date, weekday, day-lord and tithi while the home strip showed today's. Measured
live at 2026-10-29 23:45 UTC (Fri 30 Oct 05:15 IST): `/panchang` said
"29 October 2026 / Thursday / Krishna Chaturthi", the strip said "Friday in
Mumbai / Krishna Panchami". The route took "today" from `date.today()` -- the
server's UTC date on Cloud Run -- while the strip solved at the real moment in
the city. The strip's own day-cache was keyed on the same UTC date, so an entry
solved at 23:00 IST kept being served as "today" until 05:30 IST.

The clock is frozen at 2026-10-29T23:00Z = Fri 2026-10-30 04:30 IST, inside the
window. The convention under test is the CIVIL date in the city's own timezone
(chief's ruling on #593); a sunrise-to-sunrise day would make 04:30 IST still
"29 October", and these tests would then be wrong rather than the code.

The freeze patches `datetime`/`date` on the modules that read the clock, and it
does so for the server's UTC `date.today()` too, so the same test body is red
against the pre-fix code and green after it.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

import pytest

FROZEN = datetime(2026, 10, 29, 23, 0, tzinfo=timezone.utc)  # Fri 30 Oct, 04:30 IST
THURSDAY_AFTERNOON = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)  # 17:30 IST


class _Clock:
    """A settable instant behind frozen `datetime` and `date` classes."""

    def __init__(self, at: datetime):
        self.at = at

    def datetime_cls(self):
        clock = self

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.at.astimezone(tz) if tz else clock.at.replace(tzinfo=None)

        return _FrozenDatetime

    def date_cls(self):
        clock = self

        class _FrozenDate(date):
            @classmethod
            def today(cls):
                # The server's zone is UTC on Cloud Run.
                return date.fromisoformat(clock.at.astimezone(timezone.utc).date().isoformat())

        return _FrozenDate


@pytest.fixture
def clock(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import deps
    from astro_ai.routes import panchang as panchang_route

    c = _Clock(FROZEN)
    monkeypatch.setattr(chart, "datetime", c.datetime_cls())
    monkeypatch.setattr(deps, "date", c.date_cls())
    monkeypatch.setattr(panchang_route, "date", c.date_cls())
    # Fresh per-process caches, restored afterwards: an entry solved at another
    # instant by an earlier test would otherwise answer for this one.
    monkeypatch.setattr(chart, "_PANCHANG_CACHE", {})
    monkeypatch.setattr(deps, "_PANCHANG_STRIP_CACHE", {})
    monkeypatch.setattr(deps, "_fallback_cache", {})
    return c


def _page(client, path: str, **params) -> str:
    resp = client.get(path, params=params)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return resp.text


def _weekday_on_page(html: str) -> str:
    m = re.search(r"Day &amp; Lord</div>\s*<div[^>]*>([A-Za-z]+)</div>", html)
    assert m, "no 'Day & Lord' cell on the page"
    return m.group(1)


def _tithi_on_page(html: str) -> str:
    m = re.search(r"Tithi</div>\s*<div[^>]*>([^<]+)</div>", html)
    assert m, "no Tithi cell on the page"
    return m.group(1).strip()


def test_panchang_and_the_home_strip_name_the_same_day(client, clock):
    """The metric from the issue: 0 mismatches in date, weekday and tithi."""
    from astro_ai.routes.deps import panchang_strip_for_city

    strip, _, _ = panchang_strip_for_city("Mumbai, India")
    html = _page(client, "/panchang")

    assert strip.weekday == "Friday", "the strip is the reference: civil day in IST"
    assert "30 October 2026" in html, "the heading names the server's UTC date, not the city's"
    assert _weekday_on_page(html) == strip.weekday
    assert _tithi_on_page(html) == f"{strip.tithi_paksha} {strip.tithi_name}"


def test_the_today_badge_follows_the_citys_date_not_the_servers(client, clock):
    """`/panchang/2026-10-30` is today in Mumbai at 04:30 IST; the 29th is not."""
    today = _page(client, "/panchang/2026-10-30")
    yesterday = _page(client, "/panchang/2026-10-29")

    assert "Jump to today" not in today, "30 Oct was not recognised as today"
    assert "Jump to today" in yesterday, "29 Oct was still badged as today"


def test_the_strip_cache_rolls_over_at_the_citys_midnight(clock):
    """An entry solved on Thursday evening IST must not be served as Friday's.

    Both instants share one UTC date, so a cache keyed on the UTC date alone
    kept answering "Thursday" until 05:30 IST.
    """
    from astro_ai.routes.deps import panchang_strip_for_city

    clock.at = THURSDAY_AFTERNOON
    assert panchang_strip_for_city("Mumbai, India")[0].weekday == "Thursday"

    clock.at = FROZEN
    assert panchang_strip_for_city("Mumbai, India")[0].weekday == "Friday"


def test_the_page_states_which_day_it_means_in_both_languages(client, clock):
    en = _page(client, "/panchang")
    hi = _page(client, "/panchang", lang="hi")

    assert 'data-day-convention' in en and "civil day" in en
    assert 'data-day-convention' in hi and "नागरिक दिन" in hi
    assert "civil day" not in hi, "the Hindi page fell back to English"
