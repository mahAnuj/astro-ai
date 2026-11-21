"""#1332: an Ekadashi seen at a single sunrise, with Dwadashi skipped, is printed by Drik Panchang
on the day BEFORE; and `lunar_dates.shukla_tithi_date` resolves a lunar month that straddles the
year boundary to a date IN the requested year.

The day-earlier rule is an UNSOURCED-IN-CORPUS Drik almanac convention: 3 of 3 Drik readings
(2027-01-19 -> 01-18 Putrada, 2028-02-07 -> 02-06 Jaya, 2028-11-13 -> 11-12 Utpanna), the other
71 Ekadashis of 2026-2028 unchanged, two of them kept as negative controls below. See
docs/decisions/2026-11-21-1332-ekadashi-drik-day-and-nija-month.md.

Fast on purpose: 2026-2028 only, no network, no LLM. The full 2024-2032 gate is
scripts/verify_lunar_observances.py. Mutation rows: scripts/mutations/
2026_11_21_1332_ekadashi_gauna.py.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from astro_ai import lunar_dates as ld
from astro_ai import lunar_observances as lo


def _ekadashis(y0: int = 2026, y1: int = 2028) -> list[date]:
    return [
        d
        for d, o in lo.observances_between(date(y0, 1, 1), date(y1, 12, 31))
        if o.slug.startswith("ekadashi")
    ]


# --- the engine: the three Drik dates and the two controls -------------------------------

@pytest.mark.parametrize(
    "engine_day, drik_day",
    [("2027-01-19", "2027-01-18"), ("2028-02-07", "2028-02-06"), ("2028-11-13", "2028-11-12")],
)
def test_the_three_drik_dates_are_emitted_a_day_earlier(engine_day, drik_day):
    days = _ekadashis()
    assert date.fromisoformat(drik_day) in days
    assert date.fromisoformat(engine_day) not in days


@pytest.mark.parametrize("day", ["2027-10-25", "2028-08-16"])
def test_the_negative_controls_stay_on_the_sunrise_day(day):
    # Strict arunodaya would move both; Drik prints both on the sunrise day.
    d = date.fromisoformat(day)
    assert d in _ekadashis()
    assert d - timedelta(days=1) not in _ekadashis()


def test_the_issue_repro_slug_is_the_18th():
    rows = lo.observances_between(date(2027, 1, 15), date(2027, 1, 21))
    assert [o.slug for _d, o in rows if o.slug.startswith("ekadashi")] == ["ekadashi-2027-01-18"]


def test_the_rule_moves_exactly_three_of_74_and_keeps_the_total():
    days = _ekadashis()
    assert len(days) == 74
    total = sum(len(lo.observances_between(date(y, 1, 1), date(y, 12, 31))) for y in (2026, 2027, 2028))
    assert total == 149  # 149 = 2026-2028, unchanged by the shift


# --- the rule itself, on synthetic sunrise indices --------------------------------------

def _emit_with(monkeypatch, pattern: list[int], t: int, year: int = 2030, lead: int = 40):
    """(the sunrise day carrying tithi `t`, every row `_observances_for_year` emits) when
    the daily sunrise tithi index follows `pattern`, placed `lead` days after sampling
    starts, in `year`, counting +1 a day before and after it."""
    start = date(year - 1, 12, 20)
    n = (date(year + 1, 1, 10) - start).days + 1
    seq = [(pattern[0] - lead + k) % 30 for k in range(lead)] + pattern
    while len(seq) < n:
        seq.append((seq[-1] + 1) % 30)
    by_day = {start + timedelta(days=k): seq[k] for k in range(n)}
    monkeypatch.setattr(lo, "_tithi_index_at_sunrise", lambda d: by_day[d])
    rows = lo._observances_for_year.__wrapped__(year)
    return start + timedelta(days=lead + pattern.index(t)), rows


def _days(rows, kind: str) -> list[date]:
    return [d for d, o in rows if o.slug.startswith(kind)]


@pytest.mark.parametrize("t", [10, 25])
def test_t_minus_1_then_t_then_t_plus_2_takes_the_day_before(monkeypatch, t):
    pivot, rows = _emit_with(monkeypatch, [t - 2, t - 1, t, t + 2, t + 3], t)
    got = _days(rows, "ekadashi")
    assert pivot - timedelta(days=1) in got and pivot not in got


@pytest.mark.parametrize("t", [10, 25])
def test_t_plus_1_at_the_next_sunrise_stays_on_the_sunrise_day(monkeypatch, t):
    # Dwadashi has a sunrise: the >= t+2 test is what keeps this case still.
    pivot, rows = _emit_with(monkeypatch, [t - 2, t - 1, t, t + 1, t + 2], t)
    got = _days(rows, "ekadashi")
    assert pivot in got and pivot - timedelta(days=1) not in got


@pytest.mark.parametrize("t", [10, 25])
def test_without_t_minus_1_at_the_previous_sunrise_it_stays(monkeypatch, t):
    # Dashami skipped as well as Dwadashi: the t-1 test is what keeps this case still.
    pivot, rows = _emit_with(monkeypatch, [t - 3, t - 2, t, t + 2, t + 3], t)
    got = _days(rows, "ekadashi")
    assert pivot in got and pivot - timedelta(days=1) not in got


@pytest.mark.parametrize("t, kind", [(14, "purnima"), (29, "amavasya")])
def test_the_day_earlier_rule_does_not_touch_purnima_or_amavasya(monkeypatch, t, kind):
    # Same index shape at tithi 14 / 29: the rule is Ekadashi's alone.
    pivot, rows = _emit_with(monkeypatch, [t - 2, t - 1, t, (t + 2) % 30, (t + 3) % 30], t)
    assert pivot in _days(rows, kind)
    assert pivot - timedelta(days=1) not in _days(rows, kind)


# --- lunar_dates: the copy of the pick, and the year-straddling month --------------------

def _samples(pattern: list[int], lead: int = 5):
    d0 = date(2030, 3, 1)
    seq = [(pattern[0] - lead + k) % 30 for k in range(lead)] + pattern
    seq += [(seq[-1] + 1 + k) % 30 for k in range(10)]
    return [(d0 + timedelta(days=k), i) for k, i in enumerate(seq)], d0 + timedelta(days=lead)


@pytest.mark.parametrize("t", [10, 25])
def test_pick_day_takes_the_day_before_like_the_engine(t):
    samples, pivot = _samples([t - 2, t - 1, t, t + 2, t + 3])
    assert ld._pick_day(samples, t) == (pivot + timedelta(days=1), "run")  # pivot = pattern[0]


@pytest.mark.parametrize("pattern", [[8, 9, 10, 11, 12], [7, 8, 10, 12, 13]])
def test_pick_day_keeps_the_sunrise_day_when_either_condition_fails(pattern):
    samples, pivot = _samples(pattern)
    assert ld._pick_day(samples, 10) == (pivot + timedelta(days=pattern.index(10)), "run")


def test_pick_day_at_a_sample_edge_does_not_index_out_of_range():
    # Ekadashi as the very first / last sample: no neighbour to test, so no shift.
    d0 = date(2030, 3, 1)
    assert ld._pick_day([(d0, 10), (d0 + timedelta(days=1), 12)], 10) == (d0, "run")
    assert ld._pick_day([(d0, 9), (d0 + timedelta(days=1), 10)], 10) == (d0 + timedelta(days=1), "run")


def test_lunar_dates_agrees_with_lunar_observances_on_devuthani_2025():
    # 2025-11-02 is a single-sunrise Ekadashi with Dwadashi skipped; both modules must move
    # it to 2025-11-01 together, or `muhurat` Chaturmas ends on a different day from the hub.
    got = ld.shukla_tithi_date(2025, "Kartika", 11)
    assert got == date(2025, 11, 1)
    slugs = [o.slug for d, o in lo.observances_between(got, got) if o.slug.startswith("ekadashi")]
    assert slugs == ["ekadashi-2025-11-01"]


def test_margashirsha_2027_is_the_2027_month_not_the_december_2026_one():
    assert ld.shukla_tithi_date(2027, "Margashirsha", 11) == date(2027, 12, 9)


def test_pausha_2027_is_putrada_on_the_18th():
    assert ld.shukla_tithi_date(2027, "Pausha", 11) == date(2027, 1, 18)


def test_a_month_with_no_occurrence_in_the_year_is_none_not_the_neighbouring_year():
    # Pausha 2026 opens 2025-12-21; its shukla Ekadashi is in 2025.
    assert ld.shukla_tithi_date(2026, "Pausha", 11) is None


def test_two_in_year_candidates_return_the_earlier():
    assert [m.start for m in ld._nija_months(2028, "Pausha")] == [date(2027, 12, 28), date(2028, 12, 17)]
    assert ld.shukla_tithi_date(2028, "Pausha", 11) == date(2028, 1, 8)


def test_nija_month_is_still_the_first_overlapping_month():
    # Gate 3(c) and Gate 1's Bhadli Navami read it as a kshaya detector; it is not a resolver.
    assert ld.nija_month(2027, "Margashirsha").start == date(2026, 12, 9)
    assert ld.nija_month(2027, "Nonexistent") is None


def test_an_ordinary_month_is_unchanged():
    assert ld.shukla_tithi_date(2027, "Ashadha", 11) == date(2027, 7, 14)
