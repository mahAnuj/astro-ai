"""Eclipse days in the muhurat finder are computed, not typed (#1018).

The hand-typed `_ECLIPSE_DATES` listed two 2028 lunar eclipses that do not exist (Feb 12,
Aug 6), omitted four real ones and was empty from 2029. The expected set below is NASA GSFC,
Lunar Eclipses 2021-2030 (eclipse.gsfc.nasa.gov/LEdecade/LEdecade2021.html) and the matching
Solar Eclipses 2021-2030 table, read 2026-11-14. NASA lists UT; the app uses the IST calendar
date of the maximum, so the one row that differs is 2027 penumbral lunar of Feb 20 UT
(23:12 UT, 04:42 IST), which is 2027-02-21 here. Every other 2026-2028 row is the same date
in both zones.
"""
from __future__ import annotations

from datetime import date

import pytest

from astro_ai import muhurat as m

EXPECTED = {
    2026: [
        (date(2026, 2, 17), "Annular Solar Eclipse"),
        (date(2026, 3, 3),  "Total Lunar Eclipse"),
        (date(2026, 8, 12), "Total Solar Eclipse"),
        (date(2026, 8, 28), "Partial Lunar Eclipse"),
    ],
    2027: [
        (date(2027, 2, 6),  "Annular Solar Eclipse"),
        (date(2027, 2, 21), "Penumbral Lunar Eclipse"),   # NASA: Feb 20 UT
        (date(2027, 7, 18), "Penumbral Lunar Eclipse"),
        (date(2027, 8, 2),  "Total Solar Eclipse"),
        (date(2027, 8, 17), "Penumbral Lunar Eclipse"),
    ],
    2028: [
        (date(2028, 1, 12), "Partial Lunar Eclipse"),
        (date(2028, 1, 26), "Annular Solar Eclipse"),
        (date(2028, 7, 6),  "Partial Lunar Eclipse"),
        (date(2028, 7, 22), "Total Solar Eclipse"),
        (date(2028, 12, 31), "Total Lunar Eclipse"),
    ],
}


@pytest.mark.parametrize("year", sorted(EXPECTED))
def test_computed_eclipses_match_the_nasa_tables(year):
    assert list(m._eclipses_in_year(year)) == EXPECTED[year]


def test_the_issue_repro_blocks_real_eclipses_and_not_invented_ones():
    f = lambda d: m._eclipse_flag(d)[0]  # noqa: E731
    got = [f(date(2028, 2, 12)), f(date(2028, 8, 6)), f(date(2028, 1, 12)),
           f(date(2028, 7, 6)), f(date(2027, 8, 17)), f(date(2028, 12, 31))]
    assert got == [False, False, True, True, True, True]


def test_years_past_the_old_table_still_have_eclipses():
    # The typed table ended at 2028; from 2029 every eclipse silently vanished.
    for year in (2029, 2030, 2035):
        assert 4 <= len(m._eclipses_in_year(year)) <= 7, year
    assert (date(2030, 6, 1), "Annular Solar Eclipse") in m._eclipses_in_year(2030)
    assert m._eclipse_flag(date(2030, 11, 25)) == (
        True, "Total Solar Eclipse on this date — universal muhurat blocker")


def test_a_hybrid_eclipse_is_named_hybrid():
    # 2031-11-14 UT 21:41 is 2031-11-15 IST: the only hybrid in 2023-2031 apart from 2023-04-20.
    assert (date(2031, 11, 15), "Hybrid Solar Eclipse") in m._eclipses_in_year(2031)


def test_a_maximum_near_new_year_lands_on_its_ist_date():
    # 2029-12-20 22:42 UT lunar maximum is 2029-12-21 04:12 IST.
    assert (date(2029, 12, 21), "Total Lunar Eclipse") in m._eclipses_in_year(2029)
    assert all(d.year == 2029 for d, _ in m._eclipses_in_year(2029))


def test_blocking_window_and_reason_text_are_unchanged():
    assert m._eclipse_flag(date(2028, 7, 5)) == (
        True, "Partial Lunar Eclipse (day before, Jul 06) — traditionally inauspicious")
    assert m._eclipse_flag(date(2028, 7, 7)) == (
        True, "Partial Lunar Eclipse (day after, Jul 06) — traditionally inauspicious")
    assert m._eclipse_flag(date(2028, 7, 4)) == (False, "")
    assert m._eclipse_flag(date(2028, 7, 8)) == (False, "")
    # Year boundary: 2028-12-31 blocks 2029-01-01 through d.year-1.
    assert m._eclipse_flag(date(2029, 1, 1))[0] is True


def test_the_hand_typed_table_is_gone():
    assert not hasattr(m, "_ECLIPSE_DATES")
