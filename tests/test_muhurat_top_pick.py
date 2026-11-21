"""#1341 (R1 of #1017, closes #1339): the finder ranks within a tier by score and names a top pick.

`MuhuratCandidate.score` carries the soft-scoring points behind the rating, the sort key is
`(tier, -score, date)`, and `top_pick` names the first valid row: an excellent/good/acceptable
day that, in couple mode, is not a verdict of "avoid". A booster- or Abujha-lifted day carries its
tier's floor as its score; no weight, cut-off or exclusion changed (the sweep below pins that
the rating is still a pure function of the points for every day nothing lifted).

The Range select must show the days that were searched (#1339): `prefill_days` is the clamped
value on a result and the raw value on an error re-render. The template is the frontend's half;
this file reads the route's context.

No network (geocoding is stubbed) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1341_muhurat_top_pick.py.
"""
from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from astro_ai import muhurat
from astro_ai.muhurat import MuhuratCandidate, _RATING_MIN_SCORE, rank_key, top_pick

CITY = "Delhi, India"
DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 21)
START = date(2026, 11, 22)
EVENTS = ["vivah", "griha_pravesh", "vidyarambh", "namkaran", "business"]


@pytest.fixture(autouse=True)
def _pinned(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


def _row(d: date, rating: str, score: int, verdict: str | None = None) -> MuhuratCandidate:
    """A candidate with only what ranking reads. `couple` is a stand-in: `top_pick` reads
    `combined_verdict` and nothing else of it."""
    return MuhuratCandidate(
        d=d, weekday=d.strftime("%A"), tithi="Panchami", tithi_paksha="Shukla",
        nakshatra="Rohini", rating=rating, reason="fixture", flags=(), score=score,
        couple=SimpleNamespace(combined_verdict=verdict) if verdict else None)


def _ranked(rows):
    return sorted(rows, key=rank_key)


@pytest.fixture
def ctx(monkeypatch):
    """The template context of every finder render, in order. The route's TemplateResponse is
    wrapped, not replaced, so the page still renders; the frontend's half of #1339 (the select
    itself) is not asserted here."""
    from astro_ai.routes.deps import templates

    seen: list[dict] = []
    real = templates.TemplateResponse

    def recording(request, name, context=None, *a, **k):
        if name == "muhurat_finder.html":
            seen.append(context)
        return real(request, name, context, *a, **k)

    monkeypatch.setattr(templates, "TemplateResponse", recording)
    return seen


# --- (a) the higher score wins inside a tier, even when it is later ----------------------


def test_the_higher_scoring_excellent_day_is_the_pick_even_when_later():
    early, late = _row(date(2026, 12, 1), "excellent", 5), _row(date(2026, 12, 9), "excellent", 6)
    pick, ties = top_pick(_ranked([early, late]))
    assert pick is late and ties == 0
    assert _ranked([early, late])[0] is late


def test_tier_still_outranks_score():
    # A "good" 4 never outranks an "excellent" 5: the tier is the first key element.
    good, excellent = _row(date(2026, 12, 1), "good", 4), _row(date(2026, 12, 9), "excellent", 5)
    assert top_pick(_ranked([good, excellent]))[0] is excellent


def test_the_pick_is_the_first_valid_row_of_the_ranked_list():
    rows = _ranked([_row(date(2026, 12, 1), "caution", 2), _row(date(2026, 12, 2), "good", 4),
                    _row(date(2026, 12, 3), "excellent", 6), _row(date(2026, 12, 4), "avoid", 0)])
    assert top_pick(rows)[0] is rows[0]


def test_a_real_window_has_a_later_higher_scoring_excellent_day_and_the_pick_is_it():
    # Vidyarambh from 2026-11-22: 11-25 is the first excellent by date and only reaches the
    # excellent floor through a booster (score 5); 11-26 scores 6 from the soft factors alone.
    rows = muhurat.find_candidates("vidyarambh", CITY, START, 90)
    excellent = sorted((c for c in rows if c.rating == "excellent"), key=lambda c: c.d)
    first_by_date = excellent[0]
    best = max(excellent, key=lambda c: c.score)
    assert best.d > first_by_date.d and best.score > first_by_date.score, \
        "premise: a later excellent day outscores the first one by date"
    pick, _ties = top_pick(rows)
    assert pick.d != first_by_date.d
    assert pick.score == best.score
    assert pick.d == min(c.d for c in excellent if c.score == best.score)
    assert rows[0] is pick  # no caution/avoid-only reordering: the ranked head is the pick


@pytest.mark.parametrize("event", EVENTS)
def test_the_pick_equals_the_first_valid_row_of_the_real_ranked_list(event):
    rows = muhurat.find_candidates(event, CITY, START, 90)
    first_valid = next(c for c in rows if c.rating in muhurat.AUSPICIOUS_RATINGS)
    assert top_pick(rows)[0] is first_valid


# --- (b) eligibility and ties -----------------------------------------------------------


def test_a_couple_avoid_day_is_never_the_pick_but_stays_in_the_list():
    avoid_pair = _row(date(2026, 12, 1), "excellent", 7, verdict="avoid")
    ok_pair = _row(date(2026, 12, 9), "good", 4, verdict="good-for-both")
    rows = _ranked([avoid_pair, ok_pair])
    assert avoid_pair in rows and rows[0] is avoid_pair  # still listed, still ranked first
    assert top_pick(rows)[0] is ok_pair


def test_a_mixed_couple_verdict_is_still_eligible():
    mixed = _row(date(2026, 12, 1), "excellent", 5, verdict="mixed")
    assert top_pick([mixed])[0] is mixed


def test_all_couple_avoid_gives_no_pick():
    rows = [_row(date(2026, 12, 1), "excellent", 6, verdict="avoid"),
            _row(date(2026, 12, 2), "good", 4, verdict="avoid")]
    assert top_pick(rows) == (None, 0)


def test_caution_only_avoid_only_and_empty_give_no_pick():
    assert top_pick([]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "caution", 2)]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "avoid", 0)]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "caution", 2),
                     _row(date(2026, 12, 2), "avoid", 0)]) == (None, 0)


def test_a_caution_row_is_never_the_pick_when_a_valid_row_exists():
    rows = _ranked([_row(date(2026, 12, 1), "caution", 2), _row(date(2026, 12, 20), "acceptable", 3)])
    assert top_pick(rows)[0].rating == "acceptable"


def test_ties_pick_the_earliest_and_count_the_others():
    rows = _ranked([_row(date(2026, 12, 9), "excellent", 5), _row(date(2026, 12, 1), "excellent", 5),
                    _row(date(2026, 12, 5), "excellent", 5), _row(date(2026, 12, 2), "excellent", 6),
                    _row(date(2026, 12, 3), "excellent", 6), _row(date(2026, 12, 4), "good", 4)])
    pick, ties = top_pick(rows)
    assert pick.d == date(2026, 12, 2) and ties == 1  # the other score-6 day only


def test_a_couple_avoid_day_does_not_count_as_a_tie():
    rows = _ranked([_row(date(2026, 12, 1), "excellent", 5),
                    _row(date(2026, 12, 2), "excellent", 5, verdict="avoid"),
                    _row(date(2026, 12, 3), "excellent", 5)])
    pick, ties = top_pick(rows)
    assert pick.d == date(2026, 12, 1) and ties == 1


# --- (c) the 3-tuple, the default, and the rating-from-points invariant ------------------


def test_score_event_still_returns_the_three_tuple():
    out = muhurat.score_event(
        "vidyarambh", SimpleNamespace(tithi_name="Panchami", tithi_paksha="Shukla"),
        "Thursday", "Pushya", False, False, "", "", {})
    assert isinstance(out, tuple) and len(out) == 3
    assert out[0] in ("excellent", "good", "acceptable", "caution")


def test_a_candidate_built_without_a_score_defaults_to_zero():
    c = MuhuratCandidate(d=TODAY, weekday="Saturday", tithi="Panchami", tithi_paksha="Shukla",
                         nakshatra="Rohini", rating="good", reason="r", flags=())
    assert c.score == 0
    assert dataclasses.fields(MuhuratCandidate)[-1].name == "score"


def test_the_cutoffs_table_is_best_first_and_matches_the_documented_cutoffs():
    assert list(_RATING_MIN_SCORE.items()) == [("excellent", 5), ("good", 4), ("acceptable", 3)]


@pytest.fixture(scope="module")
def sweep():
    from astro_ai import chart

    # chart.geocode_place is patched per test by _pinned; the module fixture needs the same stub
    # without function-scoped monkeypatch, so it patches by hand and restores.
    real = chart.geocode_place
    chart.geocode_place = lambda place: DELHI
    try:
        return {ev: muhurat.find_candidates(ev, CITY, date(2026, 11, 22), 365) for ev in EVENTS}
    finally:
        chart.geocode_place = real


@pytest.mark.parametrize("event", EVENTS)
def test_sweep_the_rating_is_still_a_pure_function_of_the_points_unless_lifted(sweep, event):
    rows = sweep[event]
    assert len(rows) == 365
    plain = lifted = avoided = 0
    for c in rows:
        if c.rating == "avoid":
            assert c.score == 0, c
            avoided += 1
        elif c.boosters or "abujha_muhurat" in c.flags:
            floor = _RATING_MIN_SCORE.get(c.rating, 0)
            assert c.score >= floor, c
            lifted += 1
        else:
            derived = next((r for r, f in _RATING_MIN_SCORE.items() if c.score >= f), "caution")
            assert c.rating == derived, c
            plain += 1
    assert plain and avoided, "premise: the sweep reached both plain and avoided days"
    assert [rank_key(c) for c in rows] == sorted(rank_key(c) for c in rows)


def test_sweep_reaches_a_lifted_day_somewhere(sweep):
    # Guards the sweep's lifted branch from being vacuous across all five events.
    assert any(c.boosters or "abujha_muhurat" in c.flags for rows in sweep.values() for c in rows)


def test_an_abujha_day_carries_the_excellent_floor():
    rows = muhurat.find_candidates("vivah", CITY, date(2027, 2, 10), 3)
    abujha = [c for c in rows if "abujha_muhurat" in c.flags]
    assert abujha, "premise: 2027-02-11 is an Abujha date for vivah"
    assert all(c.rating == "excellent" and c.score == _RATING_MIN_SCORE["excellent"] for c in abujha)


# --- the Range select shows the searched days (#1339) -------------------------------------


def test_a_get_with_days_14_puts_14_in_the_context(client, ctx):
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 14})
    assert r.status_code == 200
    assert ctx[-1]["prefill_days"] == 14


def test_prefill_days_is_the_clamped_value(client, ctx):
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 400})
    assert ctx[-1]["prefill_days"] == 365


def test_a_post_reports_the_days_it_searched(client, ctx):
    r = client.post("/muhurat", data={"event_type": "vivah", "city": CITY,
                                      "start_date": START.isoformat(), "days": "30"})
    assert ctx[-1]["prefill_days"] == 30


def test_error_re_renders_keep_the_requested_days(client, ctx):
    base = {"event": "vivah", "city": CITY, "start": START.isoformat(), "days": 14}
    for override in ({"event": "nope"}, {"start": "not-a-date"}, {"city": "x" * 101}):
        r = client.get("/muhurat", params={**base, **override})
        assert r.status_code == 400
        assert ctx[-1]["prefill_days"] == 14, override


def test_a_failed_search_keeps_the_requested_days(client, ctx, monkeypatch):
    from astro_ai.routes import muhurat as route

    def boom(*a, **k):
        raise ValueError("no such city")

    monkeypatch.setattr(route, "_search", boom)
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 14})
    assert r.status_code == 500
    assert ctx[-1]["prefill_days"] == 14


def test_the_route_hands_the_template_the_pick(client, ctx):
    r = client.get("/muhurat", params={"event": "vidyarambh", "city": CITY,
                                       "start": START.isoformat(), "days": 90})
    pick = ctx[-1]["top_pick"]
    assert pick is not None and pick.d == date(2026, 11, 26)
    assert isinstance(ctx[-1]["top_pick_ties"], int)


def test_a_bare_form_has_no_pick(client, ctx):
    r = client.get("/muhurat")
    assert r.status_code == 200
    assert "top_pick" not in ctx[-1]
