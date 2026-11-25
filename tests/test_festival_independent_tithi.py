"""#1330: Gate E of scripts/verify_lunar_observances.py checks the five #1326 rows
against the ephemeris, at each row's own window, by exact equality.

Before it, a one-day shift of any of those rows in the registry and the expected
table together shipped green in 19 of 30 cases. These tests hold the gate in both
directions (a shifted date goes red; the shipped dates stay green) and pin the
Kalabhairav "evening" bound at the three knife-edge cases that justify it. They
load the script, they do not reimplement it."""

from __future__ import annotations

import dataclasses
import importlib.util
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SLUG = "verify_lunar_observances"


def _load():
    spec = importlib.util.spec_from_file_location(SLUG, ROOT / "scripts" / f"{SLUG}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[SLUG] = mod
    spec.loader.exec_module(mod)
    return mod


vlo = _load()
festival_registry = vlo.festival_registry

ROW_SLUGS = [r.slug for r in vlo.INDEPENDENT_ROWS]
YEARS = list(festival_registry.DATA_YEARS)


def test_gate_e_is_green_on_the_shipped_registry(capfd):
    assert vlo.gate_e_independent_window_check() == []


def test_gate_e_checks_every_row_in_every_data_year(capfd):
    assert len(vlo.INDEPENDENT_ROWS) == 5
    vlo.gate_e_independent_window_check()
    out = capfd.readouterr().out
    assert "15 row-year(s) checked (5 rows x 3 year(s))" in out
    assert len(vlo.INDEPENDENT_ROWS) * len(YEARS) == 15


@pytest.mark.parametrize("shift", (-1, +1))
@pytest.mark.parametrize("year", YEARS)
@pytest.mark.parametrize("slug", ROW_SLUGS)
def test_a_one_day_shift_in_any_row_year_fails_gate_e(monkeypatch, slug, year, shift):
    fest = festival_registry.BY_SLUG[slug]
    shifted = (date.fromisoformat(fest.dates[year]) + timedelta(days=shift)).isoformat()
    monkeypatch.setitem(fest.dates, year, shifted)
    failures = vlo.gate_e_independent_window_check()
    assert any(f.startswith(f"{slug} {year}") for f in failures), failures


def test_kalabhairav_has_exactly_one_candidate_evening_each_year():
    fest = festival_registry.BY_SLUG["kalabhairav-jayanti"]
    for year in YEARS:
        days = vlo._evening_ashtami_days(year, "Kartika")
        assert days == [date.fromisoformat(fest.dates[year])], (year, days)


def test_kalabhairav_evening_ends_at_midnight_not_sunrise():
    # Knife-edge facts (pyswisseph, Lahiri, New Delhi), 1-minute scan.
    ashtami = vlo._KRISHNA_ASHTAMI
    # 2026: Ashtami starts 12-01 00:13, 13 minutes AFTER the evening of 11-30
    # closes at midnight. A sunset-to-next-sunrise night would include it.
    assert ashtami not in vlo._evening_samples(date(2026, 11, 30))
    # ...and it is running at the sunset of 12-01 (ends 23:15 that night).
    assert vlo._evening_samples(date(2026, 12, 1))[0] == ashtami
    assert vlo._krishna_ashtami_in_evening(date(2026, 12, 1))
    # 2027: Ashtami 11-20 19:18 -> 11-21 17:21; sunset 11-21 is 17:25, so it ends
    # 4 minutes BEFORE the evening of 11-21 opens.
    assert ashtami not in vlo._evening_samples(date(2027, 11, 21))
    assert vlo._krishna_ashtami_in_evening(date(2027, 11, 20))
    # 2028: Ashtami 11-09 15:41 -> 11-10 14:04, long over by the evening of 11-10.
    assert ashtami not in vlo._evening_samples(date(2028, 11, 10))
    assert vlo._krishna_ashtami_in_evening(date(2028, 11, 9))


def test_kalabhairav_end_sample_is_civil_midnight():
    # The second sample is a late-evening clock time, not the next sunrise: on the
    # 2026-11-30 night Ashtami is running at the next sunrise (12-01) but not
    # at 23:59 of 11-30.
    _sunrise, _sunset = vlo._sunrise_sunset(
        date(2026, 12, 1), vlo.ld._DELHI_LAT, vlo.ld._DELHI_LON, vlo.ld._DELHI_TZ)
    assert vlo._tithi_idx_at(_sunrise) == vlo._KRISHNA_ASHTAMI
    midnight = datetime.combine(date(2026, 11, 30), time(23, 59), tzinfo=vlo.ld._DELHI_TZ)
    assert vlo._tithi_idx_at(midnight) != vlo._KRISHNA_ASHTAMI


def test_a_missing_slug_a_missing_year_and_an_edited_window_each_fail(monkeypatch):
    slug = "gita-jayanti"
    fest = festival_registry.BY_SLUG[slug]
    others = tuple(f for f in festival_registry.FESTIVALS if f.slug != slug)

    # a renamed or removed slug
    monkeypatch.setattr(festival_registry, "FESTIVALS", others)
    failures = vlo.gate_e_independent_window_check()
    assert any(f.startswith(f"{slug}: no such row") for f in failures), failures

    # an edited window: the row no longer reads as it did when the gate was written
    edited = dataclasses.replace(fest, observance_window="moonrise")
    monkeypatch.setattr(festival_registry, "FESTIVALS", others + (edited,))
    failures = vlo.gate_e_independent_window_check()
    assert any(f.startswith(f"{slug}: observance_window") for f in failures), failures
    monkeypatch.undo()

    # a year with no date
    monkeypatch.delitem(fest.dates, 2027)
    failures = vlo.gate_e_independent_window_check()
    assert f"{slug} 2027: no date in the registry" in failures, failures


def test_an_unresolvable_computation_is_a_failure_not_a_skip(monkeypatch):
    monkeypatch.setattr(vlo.ld, "shukla_tithi_date", lambda *a, **k: None)
    failures = vlo.gate_e_independent_window_check()
    # the four shukla rows x 3 years each; Kalabhairav does not use this engine
    assert sum("found no day" in f for f in failures) == 12, failures


def test_two_candidate_evenings_fail_loudly_without_a_tie_break(monkeypatch):
    fest = festival_registry.BY_SLUG["kalabhairav-jayanti"]
    shipped = date.fromisoformat(fest.dates[2026])
    monkeypatch.setattr(
        vlo, "_evening_ashtami_days",
        lambda year, month: [shipped - timedelta(days=1), shipped])
    failures = vlo.gate_e_independent_window_check()
    assert any("candidate days" in f and f.startswith("kalabhairav-jayanti 2026")
               for f in failures), failures
