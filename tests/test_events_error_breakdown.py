"""`events.error_breakdown` — the uncapped error aggregation /admin/ops reads.

WHY THIS FILE EXISTS. The function replaced a capped `recent(types=["error"],
limit=500)` after three QA rounds failed to make a capped read honest:

  1. the error RATE divided a capped numerator by an uncapped denominator, so a
     steady 10% true rate rendered 10.0% at 1 day, 1.79% at 7, and nothing at
     all at 30 — widening the window made the app look healthier;
  2. fixing only the rate left `exhausted`, `too_large`, the per-type counts and
     the per-source counts on the sample, so a RED alert read "93 requests had
     every provider fail" against a true 180, identical at 7d and 30d;
  3. marking those "at least" did not save it, BECAUSE A CAP CANNOT MARK A ZERO:
     1,020 errors whose newest 500 were all 429s hid 300 AllProvidersExhausted
     and 120 RequestTooLarge, so the panel printed `0` and `0` and the alert
     strip was silent while 300 visitors saw the "high demand" page.

Every ops-side test stubs this function, which is correct — they are testing the
panel, not the walk. But it meant three mutants of the walk itself survived the
whole suite. This file drives the real thing against a real local store.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from astro_ai import events


@pytest.fixture(autouse=True)
def _store(tmp_path, monkeypatch):
    """A private local event store, and no bucket."""
    monkeypatch.setattr(events, "_LOCAL_FALLBACK_DIR", tmp_path / "events")
    monkeypatch.setattr(events.storage, "get_json", lambda *a, **k: None)
    # `_read_day` PINS AN ELAPSED DAY FOR THE PROCESS LIFETIME through
    # `hot_cache.forever`. That is the memoisation this function's cost argument
    # depends on, and it means one test's blobs leak into the next one's walk
    # unless the cache is cleared — my first version of this fixture guessed at
    # a `clear` that did not exist, and two tests then read a sibling's store
    # and failed with a marginal that could not arise from their own data.
    events.hot_cache.clear()
    monkeypatch.setattr(events, "_TODAY_TTL_S", 0)
    yield tmp_path / "events"
    events.hot_cache.clear()


def _write(store, day_offset: int, evts: list[dict]) -> None:
    store.mkdir(parents=True, exist_ok=True)
    day = date.today() - timedelta(days=day_offset)
    (store / f"{day.isoformat()}.json").write_text(
        json.dumps({"date": day.isoformat(), "events": evts}))


def _err(kind="APITimeoutError", source="chart:natal") -> dict:
    return {"type": "error", "data": {"error_type": kind, "source": source}}


def test_only_error_events_are_counted(_store):
    """A page view is not an error, and counting it inflates the rate."""
    _write(_store, 0, [_err(), {"type": "page_view", "data": {}},
                       {"type": "signup", "data": {"source": "x"}}, _err()])
    d = events.error_breakdown(days=1)
    assert d["total"] == 2, f"a non-error event was counted: {d}"
    assert d["by_error_type"] == {"APITimeoutError": 2}


def test_the_window_bounds_the_walk(_store):
    """A one-day window must not inherit older days' errors."""
    _write(_store, 0, [_err()])
    _write(_store, 1, [_err(), _err()])
    _write(_store, 5, [_err()] * 10)
    assert events.error_breakdown(days=1)["total"] == 1
    assert events.error_breakdown(days=2)["total"] == 3
    assert events.error_breakdown(days=7)["total"] == 13


def test_the_window_is_clamped_to_the_retention_ceiling(_store):
    """Beyond retention there is nothing to read, so a larger window must not
    claim to cover more than it can — and must still cover everything it can.

    ASSERTS A VALUE, NOT AN EQUALITY. My first version compared
    `error_breakdown(days=beyond)` with `error_breakdown(days=RETENTION)`, which
    a mutant replacing the clamp with `days = 1` satisfies trivially: it changes
    both sides the same way, so they stay equal and the test stays green. An
    equality between two calls can only see a difference BETWEEN them.
    """
    last = events.EVENT_RETENTION_DAYS - 1
    _write(_store, 0, [_err()])
    _write(_store, last, [_err()] * 4)

    # The far edge of retention is inside the window and must be counted.
    assert events.error_breakdown(days=events.EVENT_RETENTION_DAYS)["total"] == 5
    # And asking for more does not reach past it, nor lose it.
    assert events.error_breakdown(days=events.EVENT_RETENTION_DAYS + 90)["total"] == 5
    # A day beyond retention is unreachable at any window.
    _write(_store, events.EVENT_RETENTION_DAYS + 5, [_err()] * 99)
    assert events.error_breakdown(days=events.EVENT_RETENTION_DAYS + 90)["total"] == 5


def test_the_cross_tab_and_both_marginals_agree_with_the_total(_store):
    """The panel reads all four. Two of them disagreeing is a wrong number
    somewhere, and the marginals are derived from `pairs` so they cannot."""
    _write(_store, 0, [
        _err("AllProvidersExhausted", "rashifal_single:aries"),
        _err("AllProvidersExhausted", "rashifal_single:aries"),
        _err("AllProvidersExhausted", "chart:natal"),
        _err("RequestTooLarge", "chart:natal"),
    ])
    d = events.error_breakdown(days=1)
    assert d["total"] == 4
    assert sum(d["pairs"].values()) == 4
    assert sum(d["by_error_type"].values()) == 4
    assert sum(d["by_source"].values()) == 4
    assert d["by_error_type"] == {"AllProvidersExhausted": 3, "RequestTooLarge": 1}
    assert d["by_source"] == {"rashifal_single:aries": 2, "chart:natal": 2}
    assert d["pairs"][("AllProvidersExhausted", "rashifal_single:aries")] == 2


def test_a_rare_kind_behind_many_newer_errors_is_still_counted(_store):
    """The ship-blocking scenario, at the level of the walk.

    A cap would have returned only the 429s. There is no cap, so the ordering
    of the store cannot hide anything.
    """
    _write(_store, 0, [_err("RateLimitError", "rashifal_single:aries")] * 600
                      + [_err("AllProvidersExhausted", "chart:natal")] * 300
                      + [_err("RequestTooLarge", "chart:natal")] * 120)
    d = events.error_breakdown(days=1)
    assert d["total"] == 1020
    assert d["by_error_type"]["AllProvidersExhausted"] == 300
    assert d["by_error_type"]["RequestTooLarge"] == 120


def test_an_error_with_no_shape_is_counted_rather_than_dropped(_store):
    """An error we cannot classify still happened. Dropping it is the
    undercount this function exists to remove."""
    _write(_store, 0, [{"type": "error"}, {"type": "error", "data": {}},
                       {"type": "error", "data": {"error_type": "X"}}])
    d = events.error_breakdown(days=1)
    assert d["total"] == 3
    assert d["by_error_type"] == {"?": 2, "X": 1}
    assert d["by_source"] == {"?": 3}


def test_a_missing_or_unreadable_day_does_not_abort_the_walk(_store):
    """A gap in the store is a gap, not an exception: /admin/ops must render."""
    _write(_store, 0, [_err()])
    # day 1 absent entirely; day 2 present but corrupt
    _store.mkdir(parents=True, exist_ok=True)
    bad = _store / f"{(date.today() - timedelta(days=2)).isoformat()}.json"
    bad.write_text("{not json")
    assert events.error_breakdown(days=7)["total"] == 1


def test_an_empty_store_is_zero_and_not_an_error(_store):
    d = events.error_breakdown(days=7)
    assert d == {"total": 0, "pairs": {}, "by_error_type": {}, "by_source": {}}
