"""#1331: Kalabhairav Jayanti stops asserting an Ashtami window the corpus does not source.

#1326 shipped the row saying the date is the day Ashtami runs "from pradosh through nishita" / "from dusk to
midnight". Measured (pyswisseph, Lahiri, Delhi): Ashtami of 2026-12-01 ends 23:13, so it is NOT running at
midnight on the date the registry prints, and 2027-11-20 / 2028-11-09 end at 19:16 / 15:39 (next day 17:19 /
14:02). The date is Drik Panchang's and is unchanged; only the window claim was wrong. Which Ashtami a temple
counts (pradosh, nishita or midnight) has no source in knowledge/*.md, so the copy now says what the date is
(Ashtami running after sunset, as Drik prints it) and that a temple keeping the midnight tithi may differ.

The window string also lives in tests/festival_dates_expected.json, so the registry and the table must keep
saying the same thing (the last test).

A phrase test: it catches the wording it names (and one regex for the same claim), not every possible
rewording of an unsourced window.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from astro_ai.festival_registry import FESTIVALS

SLUG = "kalabhairav-jayanti"

# Phrases that put the tithi at midnight or at nishita/pradosh as the thing the date means. Lowercase.
# 'to midnight' must not match the honest 'ends before midnight' or 'the midnight tithi'.
_WINDOW_CLAIMS = ("dusk to midnight", "to midnight", "nishita", "pradosh to", "through nishita")

# 'from pradosh through nishita', 'dusk until midnight', 'evening to nishita' -- any "<dusk word> <to word>
# <midnight word>" shape.
_WINDOW_SHAPE = re.compile(
    r"\b(dusk|pradosh|evening|sunset)\b\W+(?:\w+\W+){0,2}?(to|through|until|till)\b\W+(midnight|nishita)\b"
)

_EXPECTED = pathlib.Path(__file__).parent / "festival_dates_expected.json"


def _festival():
    return next(f for f in FESTIVALS if f.slug == SLUG)


def _copy() -> str:
    f = _festival()
    return " ".join([f.significance, f.observance_window, f.observance]).lower()


def test_the_copy_names_no_dusk_to_midnight_or_nishita_window():
    t = _copy()
    for needle in _WINDOW_CLAIMS:
        assert needle not in t, needle


def test_no_window_shaped_phrase_ties_the_date_to_midnight_or_nishita():
    m = _WINDOW_SHAPE.search(_copy())
    assert m is None, m and m.group(0)


def test_the_copy_says_ashtami_runs_after_sunset_and_a_midnight_temple_may_differ():
    f = _festival()
    assert f.observance_window == "evening, Ashtami running after sunset"
    assert "after sunset" in f.significance
    assert "midnight tithi may observe a day either side" in f.significance


@pytest.mark.parametrize("f", FESTIVALS, ids=lambda f: f.slug)
def test_each_observance_window_matches_the_expected_table(f):
    expected = json.loads(_EXPECTED.read_text())["festivals"][f.slug]["observance_window"]
    assert f.observance_window == expected
