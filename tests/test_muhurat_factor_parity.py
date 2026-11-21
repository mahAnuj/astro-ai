"""#1017 R3: the soft factors `muhurat_factors.explain` shows are the ones `score_event` counted.

`score_event` emits no structured key for tithi, star, weekday or peak day (they exist only in
its `reason` prose), so `explain` recomputes them from `EVENT_RULES` and the candidate's own
fields. Nothing stops the two drifting except this file. The TEST may parse the scorer's prose;
the runtime may not. The weights and tier cut-offs below are written out literally on purpose:
they pin the site's own point count (a convention, knowledge/vedic_reference.md 29.9) without
importing the scorer's table.

Two comparisons, because each catches what the other cannot:
  grid       every (event, tithi, paksha, star, weekday) the scorer can see, no hard trigger
  real scan  `find_candidates` output for all five events (a candidate field that differs from
             the scorer's input shows up here, not in the grid)

No network (geocoding is stubbed) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1017_r3_factor_registry.py.
"""
from __future__ import annotations

import re
from datetime import date

import pytest

from astro_ai import chart, muhurat as m
from astro_ai import muhurat_factors as mf

EVENTS = ["vivah", "griha_pravesh", "vidyarambh", "namkaran", "business"]
DELHI = (28.61, 77.21, "Asia/Kolkata")
SCAN_START = date(2026, 11, 21)
SCAN_DAYS = 200
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# (name, paksha) for the 30 tithis: chart._TITHI_NAMES runs Pratipada..Purnima then
# Pratipada..Amavasya, so index < 15 is Shukla.
TITHIS = [(n, "Shukla" if i < 15 else "Krishna") for i, n in enumerate(chart._TITHI_NAMES)]
# The site's own point count, literal (see module docstring).
WEIGHT = {"good_tithi": 2, "good_nakshatra": 2, "good_weekday": 1, "peak_day": 1,
          "avoid_weekday_soft": -1}
SOFT_KEYS = set(WEIGHT)

_SEGMENT = [
    ("good_tithi", re.compile(r"^good tithi \((.+)\)$")),
    ("good_nakshatra", re.compile(r"^good nakshatra \((.+)\)$")),
    ("good_weekday", re.compile(r"^good weekday \((.+)\)$")),
    ("peak_day", re.compile(r"^(peak-day for this event)$")),
    ("avoid_weekday_soft", re.compile(r"^avoid weekday \((.+)\)$")),
]


def _tier(points: int) -> str:
    return "excellent" if points >= 5 else "good" if points == 4 else \
        "acceptable" if points == 3 else "caution"


def _parsed(reason: str) -> list[tuple[str, str]]:
    """The scorer's soft segments as (key, value); a booster name or 'neutral factors' is not one."""
    out = []
    for seg in reason.split("; "):
        for key, rx in _SEGMENT:
            hit = rx.match(seg)
            if hit:
                out.append((key, hit.group(1) if key != "peak_day" else ""))
    return out


def _explained_soft(event: str, tithi: str, paksha: str, nakshatra: str, weekday: str):
    """explain()'s soft items for a row, via the public function (rating forced auspicious so the
    gate does not hide them); boosters empty so only soft items come back."""
    cand = m.MuhuratCandidate(d=date(2026, 12, 1), weekday=weekday, tithi=tithi,
                              tithi_paksha=paksha, nakshatra=nakshatra, rating="excellent",
                              reason="", flags=())
    return [i for i in mf.explain(cand, event).scored if i.key in SOFT_KEYS]


def _compare(event, tithi, paksha, nakshatra, weekday, rating, reason, boosted):
    items = _explained_soft(event, tithi, paksha, nakshatra, weekday)
    got = [(i.key, i.text.split(": ", 1)[1] if ": " in i.text else "") for i in items]
    assert got == _parsed(reason), (event, tithi, paksha, nakshatra, weekday, reason, got)
    if not boosted:
        assert rating == _tier(sum(WEIGHT[i.key] for i in items)), \
            (event, tithi, nakshatra, weekday, rating, reason)
    assert all(i.against == (i.key == "avoid_weekday_soft") for i in items)
    return {i.key for i in items}


def _score(event, tithi, paksha, nakshatra, weekday):
    panchang = m._MuhurtaInstant(tithi, paksha)
    return m.score_event(event, panchang, weekday, nakshatra, False, False, "", "", {})


def test_grid_the_soft_factors_equal_what_score_event_counted():
    fired: dict[str, set[str]] = {e: set() for e in EVENTS}
    compared = 0
    for event in EVENTS:
        for tithi, paksha in TITHIS:
            for nak in chart.NAKSHATRAS:
                for wd in WEEKDAYS:
                    rating, reason, _flags = _score(event, tithi, paksha, nak, wd)
                    if rating == "avoid":
                        continue
                    compared += 1
                    fired[event] |= _compare(event, tithi, paksha, nak, wd, rating, reason, False)
    assert compared > 10_000, "the grid stopped scoring rows"
    # every soft key fires somewhere it is registered for, and nowhere it is not
    for event in EVENTS:
        want = {"good_tithi", "good_nakshatra", "good_weekday", "avoid_weekday_soft"}
        if m.EVENT_RULES[event].get("peak_day"):
            want.add("peak_day")
        assert fired[event] == want, (event, fired[event])
    assert {e for e in EVENTS if "peak_day" in fired[e]} == {"business", "vidyarambh"}


def test_grid_the_deducted_weekdays_are_saturday_and_for_vidyarambh_sunday():
    got: dict[str, set[str]] = {e: set() for e in EVENTS}
    for event in EVENTS:
        for tithi, paksha in TITHIS:
            for wd in WEEKDAYS:
                rating, _r, _f = _score(event, tithi, paksha, "Hasta", wd)
                if rating == "avoid":
                    continue
                for i in _explained_soft(event, tithi, paksha, "Hasta", wd):
                    if i.key == "avoid_weekday_soft":
                        got[event].add(wd)
    assert got == {"vivah": {"Saturday"}, "griha_pravesh": {"Saturday"},
                   "namkaran": {"Saturday"}, "business": {"Saturday"},
                   "vidyarambh": {"Saturday", "Sunday"}}


@pytest.fixture(scope="module")
def scans():
    mp = pytest.MonkeyPatch()
    mp.setattr(chart, "geocode_place", lambda place: DELHI)
    try:
        yield {e: m.find_candidates(e, "Delhi, India", SCAN_START, SCAN_DAYS) for e in EVENTS}
    finally:
        mp.undo()


def test_real_scan_the_soft_factors_equal_what_score_event_counted(scans):
    seen = 0
    for event, rows in scans.items():
        assert len(rows) >= 150, (event, len(rows))  # a few days may be skipped on an exception
        for c in rows:
            if c.rating == "avoid":
                continue
            seen += 1
            # An Abujha lift is a booster since #1346: it raises the rating the way Sarvartha does.
            boosted = bool(c.boosters) or "abujha_muhurat" in c.flags
            _compare(event, c.tithi, c.tithi_paksha, c.nakshatra, c.weekday, c.rating,
                     c.reason, boosted)
    assert seen > 100, "the real scan stopped producing scored rows"


def test_real_scan_explain_agrees_with_the_reason_on_every_auspicious_row(scans):
    """The public path end to end: the scored list explain returns for a real row, boosters
    aside, is the reason's soft segments."""
    rows = 0
    for event, cands in scans.items():
        for c in cands:
            if c.rating not in m.AUSPICIOUS_RATINGS:
                continue
            rows += 1
            soft = [(i.key, i.text.split(": ", 1)[1] if ": " in i.text else "")
                    for i in mf.explain(c, event).scored if i.key in SOFT_KEYS]
            assert soft == _parsed(c.reason), (event, c.d, c.reason, soft)
    assert rows > 100


def test_a_peak_day_is_always_a_good_day_so_the_branch_nesting_is_the_scorers():
    """`score_event` credits peak_day only inside the good-weekday branch; `explain` mirrors that.
    If an event ever named a peak day outside its good_days the two nestings would diverge, and
    the grid above could not tell which was right."""
    for event, rules in m.EVENT_RULES.items():
        peak = rules.get("peak_day")
        assert peak is None or peak in rules["good_days"], event
