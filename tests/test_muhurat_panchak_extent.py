"""Panchak starts at the THIRD QUARTER of Dhanishta, not at Dhanishta (#713).

Raman, Muhurtha (1948) ch. III, "Nakshatra Panchaka": from the third quarter of
Dhanishta to the end of Revati. `muhurat._PANCHAK_NAKSHATRAS` flagged the whole
of Dhanishta while its own comment said "latter half", so a day whose noon Moon
sat in Dhanishta pada 1-2 was marked `panchak` and demoted to "avoid". The quote
is the #713 filer's transcription; data/ was absent when this was written.

The expected sets below are written out from the source sentence, not derived
from the helper under test, and the integration test reads the Moon through
find_candidates, so a rule that regresses in either place goes red.
"""
from __future__ import annotations

from datetime import date

import pytest

from astro_ai.chart import NAKSHATRAS
from astro_ai.muhurat import _is_panchak, find_candidates

# Whole nakshatras Raman lists after Dhanishta's third quarter.
_WHOLE = ("Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati")


@pytest.mark.parametrize("pada", [1, 2, 3, 4])
@pytest.mark.parametrize("nakshatra", NAKSHATRAS)
def test_every_nakshatra_and_pada_against_the_source_span(nakshatra, pada):
    expected = nakshatra in _WHOLE or (nakshatra == "Dhanishta" and pada in (3, 4))
    assert _is_panchak(nakshatra, pada) is expected, (nakshatra, pada)


def test_dhanishta_first_half_is_not_panchak_and_second_half_is():
    assert [_is_panchak("Dhanishta", p) for p in (1, 2, 3, 4)] == [False, False, True, True]


def test_neighbours_of_the_span_are_not_panchak():
    assert not _is_panchak("Shravana", 4)   # the nakshatra just before Dhanishta
    assert not _is_panchak("Ashwini", 1)    # the one just after Revati


def test_a_missing_moon_is_not_panchak():
    # find_candidates passes ("", 0) when the snapshot has no Moon; that must
    # keep today's behaviour (not Panchak), never mark a day avoid.
    assert _is_panchak("", 0) is False


def test_the_finder_flags_panchak_only_from_dhanishta_pada_3():
    """Delhi, noon Moon, measured 2026-11-09: 11-17 Dhanishta pada 2 (the day
    the old rule over-flagged), 11-18 Shatabhisha, 11-19 Purva Bhadrapada,
    11-20 Uttara Bhadrapada, 11-21 Revati, 11-22 Ashwini.

    11-20 is Devuthani Ekadashi, an abujha day, and score_event returns on the
    abujha rating before it reaches the Panchak check, so its flags carry
    "abujha_muhurat" and not "panchak" even though the Moon is in Panchak. 11-17
    is still "avoid" -- for Chaturmas, which is checked after Panchak and so was
    hidden behind the over-flag -- but no longer for Panchak."""
    got = {c.d: c for c in find_candidates("griha_pravesh", "Delhi", date(2026, 11, 15), 8)}
    assert got[date(2026, 11, 17)].nakshatra == "Dhanishta"
    assert "panchak" not in got[date(2026, 11, 17)].flags
    for day in (18, 19, 21):
        assert "panchak" in got[date(2026, 11, day)].flags, got[date(2026, 11, day)].nakshatra
    assert "panchak" not in got[date(2026, 11, 22)].flags


def test_the_moon_pada_reaches_the_rule_from_the_chart_field():
    """The pada is read off PlanetPosition.pada, not recomputed (see
    matching._moon_pada). Noon IST 2026-11-17 is Dhanishta pada 2."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from astro_ai.chart import compute_chart
    from astro_ai.muhurat import _moon_nakshatra_for

    chart = compute_chart("2026-11-15", "12:00", "Delhi")
    when = datetime(2026, 11, 17, 12, 0, tzinfo=ZoneInfo(chart.birth_tz))
    assert _moon_nakshatra_for(chart, when) == ("Dhanishta", 2)
