"""What `/panchang` renders for moonrise and moonset (#150).

`compute_moon_rise_set` sat in `chart.py` with two comments about it and ZERO
callers — the shape #140's intent classifier had, where the code exists and
nothing reaches it. Wiring it is the easy half; the reason these tests exist is
the other half, because the Moon breaks three of the assumptions the
sunrise/sunset card is built on:

  * **It is not a span.** The moonset inside a calendar date usually ends the
    PREVIOUS night's Moon, so it precedes that date's moonrise — 187 of the 365
    days of 2026 at New Delhi. Rendering "15:14 — 04:54" the way the sunrise
    card does would be a backwards window, which is the defect #227 had just
    finished removing from Rahu Kaal.
  * **The event can fall on the next day.** Successive moonrises are ~24h50m
    apart, so a date can hold none of its own: 13 of 365 Delhi days in 2026.
    A bare "00:42" on the 10 Jan page is then a time on the 11th.
  * **The event can be absent**, and far more often than the Sun equivalent —
    the Moon's path is inclined ~5.1° to the ecliptic, so it goes circumpolar
    at lower latitudes than the Sun does. Measured over 2026: both instants
    absent on 166 of 365 days at Tromso and 88 at Reykjavik, against 5
    sun-flagged days at Tromso. At New Delhi and Mumbai: zero.

The last one is deliberately NOT `DailyPanchang.daylight_ordinary`, which is
about the Sun and says so in its own comment. Tromso 2026-05-16 is the case
that proves they must stay separate: no ordinary daylight span, and a real
moonrise at 00:36.

Values here come from Swiss Ephemeris via `compute_moon_rise_set` itself, not
from an independent almanac — these tests assert what the PAGE does with the
computation, not that the computation matches drikpanchang. Ephemeris accuracy
is not what shipped broken here; the absent call was.
"""
from __future__ import annotations

import re

import pytest

# Coordinates pinned rather than geocoded — the suite is hermetic (conftest's
# `_offline_geocode`). Tromso and Reykjavik are the two polar references
# `scripts/verify_panchang_angas.py` already uses.
CITIES = {
    "New Delhi, India": (28.6139, 77.2090, "Asia/Kolkata"),
    "Tromso": (69.6492, 18.9553, "Europe/Oslo"),
    "Reykjavik": (64.1466, -21.9426, "Atlantic/Reykjavik"),
}

DISCLOSURE = "No moonrise or moonset on this date"


@pytest.fixture
def at_city(monkeypatch):
    """Resolve every place to one chosen city, overriding conftest's Mumbai.

    Applied per test rather than autouse: conftest's `_offline_geocode` sends
    everything to Mumbai, and a polar case needs polar coordinates to be the
    case it claims to be.
    """

    def _install(city: str):
        from astro_ai import chart

        monkeypatch.setattr(chart, "geocode_place", lambda place: CITIES[city])
        return city

    return _install


def _moon_times(city: str, iso: str):
    """(moonrise, moonset) straight from the production function.

    The tests compare the PAGE against this rather than against a transcribed
    clock time, so an ephemeris update moves both together instead of turning
    a rendering test red for an astronomy reason.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from astro_ai.chart import compute_chart, compute_moon_rise_set

    chart = compute_chart("2000-01-01", "12:00", city)
    tz = ZoneInfo(chart.birth_tz)
    y, m, d = (int(part) for part in iso.split("-"))
    return compute_moon_rise_set(chart, when=datetime(y, m, d, 12, 0, tzinfo=tz))


def _page(client, city: str, iso: str) -> str:
    resp = client.get(f"/panchang/{iso}", params={"city": city})
    assert resp.status_code == 200, f"{city} {iso} returned {resp.status_code}"
    return resp.text


def test_an_ordinary_day_shows_both_instants_and_no_disclosure(client, at_city):
    """Defect this guards: the function had no caller at all, so the page
    showed neither instant. 2026-01-01 at Delhi also has the moonset (04:54)
    BEFORE the moonrise (15:14), which is the ordinary case, not an error.
    """
    city = at_city("New Delhi, India")
    rise, set_ = _moon_times(city, "2026-01-01")
    assert rise is not None and set_ is not None, "Delhi always has both"

    html = _page(client, city, "2026-01-01")

    assert f"Moonrise {rise:%H:%M}" in html
    assert f"Moonset {set_:%H:%M}" in html
    assert DISCLOSURE not in html
    # The two instants must never be joined into one window the way
    # sunrise/sunset are: on this date that window would run backwards.
    #
    # Assert on the SPAN, not on one spelling of it. QA of 9710313 mutated the
    # template to emit `Moonrise 15:14 &mdash; Moonset 04:54` — a LABELLED join,
    # still a backwards window — and the bare-string form below passed it. The
    # mutation was caught, but by the `Moonrise 15:14` assertion above rather
    # than by the check written for this purpose, which is luck, not a guard.
    # This strips the labels and the tags first, so any rendering that puts the
    # two clocks either side of a dash fails regardless of what sits between.
    stripped = re.sub(r"<[^>]+>", " ", html)
    stripped = stripped.replace("&mdash;", "—").replace("&ndash;", "–")
    # Labels FIRST, whitespace SECOND. Doing both in one alternation leaves a
    # double space where a label was removed, so the single-spaced pattern below
    # never matches — the first version of this guard did exactly that and
    # missed every labelled join it was written to catch.
    stripped = re.sub(r"Moonrise|Moonset", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped)
    for dash in ("—", "–", "-"):
        joined = f"{rise:%H:%M} {dash} {set_:%H:%M}"
        assert joined not in stripped, (
            f"the two instants were joined into {joined!r} — that is a backwards "
            "window on this date, the #227 defect through a new field"
        )
    assert f"{rise:%H:%M} — {set_:%H:%M}" not in html


def test_a_next_day_moonrise_carries_its_date(client, at_city):
    """Defect this guards: a bare "00:42" on the 10 Jan page is a time on the
    11th. `compute_moon_rise_set`'s docstring tells callers to render the date;
    nothing enforced it, because nothing called it.
    """
    city = at_city("New Delhi, India")
    rise, _ = _moon_times(city, "2026-01-10")
    assert rise is not None and rise.day == 11, (
        "2026-01-10 at Delhi is in the census as a day whose first moonrise "
        f"falls on the 11th; got {rise}"
    )

    html = _page(client, city, "2026-01-10")

    # The clock time and its date must appear together, in that order, with
    # nothing but markup between them.
    pattern = re.compile(
        rf"Moonrise {rise:%H:%M}\s*<[^>]*>on {rise:%d %b}", re.UNICODE
    )
    assert pattern.search(html), (
        f"a moonrise on {rise:%d %b} rendered without its date on the "
        "2026-01-10 page"
    )


def test_a_moonless_day_discloses_instead_of_printing_a_clock(client, at_city):
    """Defect this guards: the Moon's own polar case. Reykjavik 2026-01-01 has
    no moonrise and no moonset — 88 of its 365 days in 2026 do not. Printing
    "Moonrise 00:04 — Moonset 00:01" for one of them would be #227 reintroduced
    through a different field.
    """
    city = at_city("Reykjavik")
    rise, set_ = _moon_times(city, "2026-01-01")
    assert (rise, set_) == (None, None), (
        f"2026-01-01 at Reykjavik is in the census as moonless; got {rise} / {set_}"
    )

    html = _page(client, city, "2026-01-01")

    assert DISCLOSURE in html
    # No clock time for an event that did not happen — not "00:00", not "—".
    assert "Moonrise" not in html.replace(DISCLOSURE, "")
    assert "Moonset" not in html.replace(DISCLOSURE, "")


def test_a_missing_moonset_is_named_not_faked(client, at_city):
    """One instant present, one absent — 10 of 365 days at Tromso in 2026.

    2026-05-16 is also one of the FIVE dates `daylight_ordinary` flags there
    (#227), and it still has a real moonrise at 00:36. So this is the test that
    holds the two flags apart: keying the moon card off the Sun's flag would
    withhold an instant that exists.
    """
    city = at_city("Tromso")
    rise, set_ = _moon_times(city, "2026-05-16")
    assert rise is not None and set_ is None, (
        f"2026-05-16 at Tromso is in the census as rise-only; got {rise} / {set_}"
    )

    html = _page(client, city, "2026-05-16")

    assert f"Moonrise {rise:%H:%M}" in html
    assert "No moonset on this date" in html
    assert DISCLOSURE not in html
    # The Sun's disclosure is showing on this very page — the Moon's card must
    # not have been suppressed along with the daylight windows.
    assert "No ordinary sunrise-to-sunset day" in html
