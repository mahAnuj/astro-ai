"""A new prefix-cache counter must not empty the panel, and an old row must not be
resurrected (#431).

`_PREFIX_ZERO` was both the shape `record()` writes and the set `range_summary`
required of every stored row, so adding ANY counter made every row already stored
fail the gate and be skipped whole. That is why #475 booked a new kind of report in
an existing field instead. `_PREFIX_REQUIRED` splits the two: a key added to
`_PREFIX_ZERO` alone reads as 0 on old rows; a key added to both says "absent is not
zero" and skips them.

The tests monkeypatch a HYPOTHETICAL ninth key rather than add one -- no counter is
added by this change. Hermetic: storage is a tmp dir.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from astro_ai import llm_stats
# The fixtures, not copies of them: `stats_dir` points storage at a tmp dir and
# `_forget_warned_rows` clears the per-process skip-warning dedupe.
from test_prefix_cache_usage import _forget_warned_rows, stats_dir  # noqa: F401

KEY = "groq120|openai/gpt-oss-120b|ask"
MODEL = "openai/gpt-oss-120b"
# The eight v2 keys, spelled out so this file does not read the very constant it
# is checking.
V2_KEYS = {"calls", "measurable", "reported", "prompt_measurable", "prompt_reported",
           "cached_tokens", "cached_measurable", "reported_unmeasurable"}
V2_ROW = {"calls": 10, "measurable": 10, "reported": 10, "prompt_measurable": 20_000,
          "prompt_reported": 20_000, "cached_tokens": 4_000, "cached_measurable": 4_000,
          "reported_unmeasurable": 0}
NINTH = "reported_impossible"


def _write_day(stats_dir, day, row, key=KEY):
    stats_dir.mkdir(parents=True, exist_ok=True)
    (stats_dir / f"{day.isoformat()}.json").write_text(json.dumps({
        "date": day.isoformat(), "counts": {key: row.get("calls", 0)},
        "totals": {"ask": row.get("calls", 0)}, "fallbacks": 0,
        "prefix_cache": {key: row}}))


def _nine_keys(monkeypatch, *, required: bool):
    """Declare a hypothetical ninth counter, as a future change would."""
    monkeypatch.setattr(llm_stats, "_PREFIX_ZERO", {**llm_stats._PREFIX_ZERO, NINTH: 0})
    if required:
        monkeypatch.setattr(llm_stats, "_PREFIX_REQUIRED",
                            llm_stats._PREFIX_REQUIRED | {NINTH})


def test_a_v2_row_stays_readable_when_a_defaultable_key_is_added(stats_dir, monkeypatch):
    """The issue's metric: `prefix_cache_skipped_rows` stays 0 across a schema bump."""
    _write_day(stats_dir, date.today(), dict(V2_ROW))
    _nine_keys(monkeypatch, required=False)
    agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 0
    e = agg["prefix_cache"]["ask"]
    assert e["calls"] == 10 and e["cached_tokens"] == 4_000
    assert e["models"] == [f"groq120:{MODEL}"]


def test_a_window_spanning_the_bump_adds_the_old_and_the_new_row(stats_dir, monkeypatch):
    """Yesterday's v2 row plus today's row written by `record()` under nine keys."""
    _write_day(stats_dir, date.today() - timedelta(days=1), dict(V2_ROW))
    _nine_keys(monkeypatch, required=False)
    llm_stats.record(provider="groq120", model=MODEL, route="ask",
                     prompt_tokens=2363, cached_tokens=2304)
    agg = llm_stats.range_summary(3)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 0
    e = agg["prefix_cache"]["ask"]
    assert e["calls"] == 11, "the old day and the new day must both count"
    assert e["cached_tokens"] == 4_000 + 2304


def test_a_key_declared_required_skips_the_old_row(stats_dir, monkeypatch):
    """The other branch: "absent is not zero" must still skip, or a meaning change
    would be summed into the new definition."""
    _write_day(stats_dir, date.today(), dict(V2_ROW))
    _nine_keys(monkeypatch, required=True)
    agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 1
    assert "ask" not in agg["prefix_cache"]


def test_the_required_set_sits_between_the_v2_keys_and_what_record_writes():
    assert V2_KEYS <= llm_stats._PREFIX_REQUIRED, (
        "a v2 key left out of the required set lets a partial old row read as current")
    assert llm_stats._PREFIX_REQUIRED <= llm_stats._PREFIX_ZERO.keys(), (
        "a required key record() never writes would skip every NEW row")


def test_a_v1_row_is_replaced_not_upgraded_by_the_next_calls(stats_dir, monkeypatch):
    """The write side. A v1 row (`prompt_tokens`, 76,000 cached) used to be topped up
    in place by `.get(k, 0)` until it carried all eight keys, at which point it
    passed the read gate with its old sums: `impossible: True`, cached ~76k."""
    _write_day(stats_dir, date.today(), {"calls": 40, "reported": 40,
                                         "prompt_tokens": 80_000, "cached_tokens": 76_000})
    llm_stats.record(provider="groq120", model=MODEL, route="ask",
                     prompt_tokens=2363, cached_tokens=2304)
    # below the 128-token floor: books `reported_unmeasurable`, the last key an
    # in-place upgrade would still be missing
    llm_stats.record(provider="groq120", model=MODEL, route="ask",
                     prompt_tokens=100, cached_tokens=96)
    row = json.loads((stats_dir / f"{date.today().isoformat()}.json").read_text()
                     )["prefix_cache"][KEY]
    assert "prompt_tokens" not in row, "the v1 shape survived into the stored row"
    assert row["calls"] == 2
    e = llm_stats.range_summary(1)["aggregate"]["prefix_cache"]["ask"]
    assert e["cached_tokens"] == 2304 + 96, "the v1 row's 76,000 leaked into the sum"
    assert e["impossible"] is False
