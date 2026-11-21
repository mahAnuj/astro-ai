"""#1338: `compute_panchang` must not depend on which caller reached its cache first.

`_PANCHANG_CACHE` used to be keyed on a 0.5 degree cell (~55 km), so the FIRST caller in a
cell decided the sunrise, Rahu Kaal, Abhijit and choghadiya for everyone after it. The muhurat
landing page asks for "New Delhi, India" and the finder takes "Delhi": same cell, ~5 s apart
at sunset, which the truncated `%H:%M` display turns into one printed minute. So the finder's
output depended on whether the landing page had rendered earlier in the process.

No network: `geocode_place` is patched with fixed coordinates (as tests/test_sidereal_threads.py
does), so every place below is a point this file chose.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
import swisseph as swe

from astro_ai import chart, muhurat
from astro_ai.routes.muhurat import _landing_upcoming

KOLKATA = "Asia/Kolkata"
# Both round to (28.5, 77.0) under round(x*2)/2, so a cell-keyed cache merges them.
NEW_DELHI = (28.6138954, 77.2090057, KOLKATA)   # the landing page's LANDING_CITY
DELHI = (28.6328027, 77.2197713, KOLKATA)       # what the finder's free-text "Delhi" resolves to
PLACES = {"New Delhi, India": NEW_DELHI, "Delhi": DELHI}
DAY = date(2026, 12, 1)


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    saved = dict(chart._PANCHANG_CACHE)
    chart._PANCHANG_CACHE.clear()
    monkeypatch.setattr(chart, "geocode_place", lambda place: PLACES[place])
    yield
    chart._PANCHANG_CACHE.clear()
    chart._PANCHANG_CACHE.update(saved)


def _finder_hash(event: str) -> str:
    rows = sorted(muhurat.find_candidates(event, "Delhi", DAY, 30), key=lambda c: c.d)
    seen = [(c.d, c.rahu_kaal, c.abhijit_muhurta, c.choghadiya, c.sunrise) for c in rows]
    return hashlib.md5(repr(seen).encode()).hexdigest()


def test_the_finder_does_not_depend_on_the_landing_page_having_run_first():
    events = ("namkaran", "griha_pravesh", "vidyarambh")
    cold = {e: _finder_hash(e) for e in events}

    chart._PANCHANG_CACHE.clear()
    _landing_upcoming("griha_pravesh", date(2026, 11, 21))
    warm = {e: _finder_hash(e) for e in events}

    assert cold == warm


def _panchang(place: str, day: date = DAY) -> chart.DailyPanchang:
    natal = chart.compute_chart(day.isoformat(), "12:00", place)
    return chart.compute_panchang(natal, datetime.combine(day, time(12), tzinfo=ZoneInfo(KOLKATA)))


def _windows(p: chart.DailyPanchang) -> tuple:
    return (p.sunrise, p.sunset, p.rahu_kaal_start, p.rahu_kaal_end, p.abhijit_start, p.abhijit_end)


def test_two_cities_in_one_half_degree_cell_each_keep_their_own_times_in_either_order():
    a_first = (_panchang("New Delhi, India"), _panchang("Delhi"))
    chart._PANCHANG_CACHE.clear()
    b_first = (_panchang("Delhi"), _panchang("New Delhi, India"))
    # Reversed on purpose: a swap-order test that compared A-then-B with itself would pass forever.
    b_first = (b_first[1], b_first[0])

    assert _windows(a_first[0]) == _windows(b_first[0])
    assert _windows(a_first[1]) == _windows(b_first[1])
    # The two points are ~5 s apart at sunset: if they were still one entry these would be equal.
    assert a_first[0].sunset != a_first[1].sunset


def test_the_cache_still_hits_for_the_same_place_and_day():
    first = _panchang("Delhi")
    size = len(chart._PANCHANG_CACHE)
    second = _panchang("Delhi")
    assert second is first
    assert len(chart._PANCHANG_CACHE) == size


# Tuesday's Rahu Kaal is the 7th of 8 equal parts of the day (sunrise to sunset).
_RAHU_PART = {0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3, 6: 8}


def _independent(lat: float, lon: float, day: date) -> tuple[datetime, datetime, datetime, datetime]:
    """Sunrise, sunset and Rahu Kaal from `swisseph.rise_trans` alone: no project code."""
    tz = ZoneInfo(KOLKATA)
    mid = datetime.combine(day, time(0), tzinfo=tz).astimezone(ZoneInfo("UTC"))
    jd0 = swe.julday(mid.year, mid.month, mid.day, mid.hour + mid.minute / 60.0)

    def at(flag):
        _, tret = swe.rise_trans(jd0, swe.SUN, flag, (lon, lat, 0.0))
        return datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")) + timedelta(days=tret[0] - 2451544.5)

    rise, sets = at(swe.CALC_RISE).astimezone(tz), at(swe.CALC_SET).astimezone(tz)
    part = (sets - rise) / 8
    n = _RAHU_PART[day.weekday()]
    return rise, sets, rise + part * (n - 1), rise + part * n


@pytest.mark.parametrize("place", ["Delhi", "New Delhi, India"])
def test_each_places_windows_match_an_independent_swisseph_computation(place):
    lat, lon, _ = PLACES[place]
    rise, sets, rk0, rk1 = _independent(lat, lon, DAY)
    # Warm the shared cell from the OTHER point first, so a cell-keyed cache hands back its value.
    _panchang(next(k for k in PLACES if k != place))
    p = _panchang(place)
    for got, want in ((p.sunrise, rise), (p.sunset, sets), (p.rahu_kaal_start, rk0), (p.rahu_kaal_end, rk1)):
        assert abs((got - want).total_seconds()) < 1.5, (place, got, want)


def test_rahu_kaal_for_the_two_delhi_points_is_pinned_as_a_literal():
    # Drik Panchang, New Delhi, 2026-12-01 (fetched 2026-11-21 by astro-auditor): sunrise 06:56,
    # sunset 17:24, Rahu Kalam 14:47-16:05. The two points differ by one minute at the start of
    # the window; each is the exact-coordinate answer (swisseph rise_trans), not a shared cell's.
    def hm(dt):
        return dt.strftime("%H:%M")

    nd, dl = _panchang("New Delhi, India"), _panchang("Delhi")
    assert (hm(nd.rahu_kaal_start), hm(nd.rahu_kaal_end), hm(nd.sunset)) == ("14:47", "16:05", "17:24")
    assert (hm(dl.rahu_kaal_start), hm(dl.rahu_kaal_end), hm(dl.sunset)) == ("14:46", "16:05", "17:23")


def test_the_cache_is_bounded_because_free_text_cities_mint_keys(monkeypatch):
    monkeypatch.setattr(chart, "_PANCHANG_CACHE_MAX", 2)
    for i in range(5):
        PLACES[f"p{i}"] = (20.0 + i, 75.0, KOLKATA)
        _panchang(f"p{i}")
    try:
        assert 1 <= len(chart._PANCHANG_CACHE) <= 2
    finally:
        for i in range(5):
            PLACES.pop(f"p{i}", None)
