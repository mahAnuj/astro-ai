"""The Token budget panel must separate "large" from "breaking" (#355).

WHY THIS IS HERE, given the charter in conftest.py.

Four of these pin defects that shipped; the rest pin the arithmetic that
decides what the page says is red, because getting it wrong is silent in the
direction that matters.

  1. The panel reported `in / request` only. Groq's 8,000 TPM and 200,000 TPD
     both count input + output, so an input-only figure reads as headroom the
     budget does not have.
  2. There was no daily figure at all. 2026-10-08 read `TPD: Limit 200000,
     Used 198888` and took every rashifal page down; averaged across its
     window that day is invisible.
  3. `BUDGET_FAIL_REASONS` was first written `("413", "429_tpm", "429_tpd")`
     and `providers.py:_failure_reason` also returns a BARE `429` when the
     error text names neither window -- so a real rate limit counted as "not a
     budget failure" and the red metric under-reported. Caught by writing the
     test the constant's own comment promised. That is what
     `test_every_reason_providers_can_emit_is_classified` exists for.
  4. The breaks count was a total with no feature attached, so "something broke
     97 times" could not be turned into an instruction.
"""
from __future__ import annotations

import inspect

import pytest

from astro_ai import events, llm_stats, ops_data, providers


# --- 1. total, not input ----------------------------------------------------

def _route(**kw):
    base = {"route": "r", "calls": 10, "hits": 8, "hit_rate_pct": 80,
            "input_tokens": 0, "output_tokens": 0, "avg_miss_latency_ms": None}
    base.update(kw)
    return base


def _reset_app_cache():
    """`_app_view` memoises for APP_CACHE_TTL (60 s), so a second call in the
    same second returns the first test's data. Isolation, not a workaround:
    every test here builds its own store."""
    ops_data._app_cache = None


def _routes_from(rows, monkeypatch):
    _reset_app_cache()
    monkeypatch.setattr(llm_stats, "usage_summary",
                        lambda days: {"days": days, "total_calls": sum(r["calls"] for r in rows),
                                      "cache_hits": 0, "cache_misses": 0, "hit_rate_pct": 0,
                                      "total_input_tokens": 0, "total_output_tokens": 0,
                                      "by_route": rows})
    monkeypatch.setattr(llm_stats, "range_summary", lambda days: {"days": []})
    monkeypatch.setattr(events, "recent", lambda **kw: [])
    return {r["route"]: r for r in ops_data._app_view(7)["routes"]}


def test_per_request_total_is_input_plus_output_over_misses(monkeypatch):
    # 10 calls, 8 hits -> 2 misses. 1,000 in + 500 out = 1,500 / 2 = 750.
    r = _routes_from([_route(input_tokens=1000, output_tokens=500)], monkeypatch)["r"]
    assert r["per_request"] == 500          # input alone, kept as the regression signal
    assert r["per_request_out"] == 250
    assert r["per_request_total"] == 750    # what the limit actually counts


def test_the_headline_figure_is_never_the_input_alone(monkeypatch):
    # The defect: output was recorded and never shown, so a route at 60% of the
    # bucket read as 40%.
    r = _routes_from([_route(input_tokens=4000, output_tokens=2000)], monkeypatch)["r"]
    assert r["per_request_total"] > r["per_request"]


def test_tpm_pct_is_the_total_against_one_models_bucket(monkeypatch):
    # 2 misses, 7,800 total -> 3,900/request -> 49% of 8,000.
    r = _routes_from([_route(input_tokens=5200, output_tokens=2600)], monkeypatch)["r"]
    assert r["tpm_pct"] == round(3900 / ops_data.TPM_PER_MODEL * 100)


def test_a_route_with_no_misses_reports_none_not_zero(monkeypatch):
    # Zero would read as "free". It means "never generated".
    r = _routes_from([_route(calls=5, hits=5, input_tokens=0, output_tokens=0)],
                     monkeypatch)["r"]
    assert r["per_request_total"] is None and r["tpm_pct"] is None


# --- 2. the peak day, not the mean -----------------------------------------

def test_peak_day_reports_the_worst_day_and_names_it():
    from datetime import date, timedelta
    from astro_ai import llm_stats
    today = date.today()
    quiet = {"calls": {"total": 1, "hits": 0, "misses": 1,
                       "input_tokens": 100, "output_tokens": 50}}
    spike = {"calls": {"total": 1, "hits": 0, "misses": 1,
                       "input_tokens": 150000, "output_tokens": 48888}}
    peak_on = (today - timedelta(days=2)).isoformat()

    def fake_read(d):
        return spike if d.isoformat() == peak_on else quiet

    orig = llm_stats._read_day
    llm_stats._read_day = fake_read
    try:
        out = llm_stats.usage_summary(7)
    finally:
        llm_stats._read_day = orig
    # The mean over 7 days would be ~28k and hide it entirely.
    assert out["peak_day_tokens"] == 198888
    assert out["peak_day"] == peak_on


def test_peak_day_is_none_when_nothing_was_recorded():
    from astro_ai import llm_stats
    orig = llm_stats._read_day
    llm_stats._read_day = lambda d: None
    try:
        out = llm_stats.usage_summary(7)
    finally:
        llm_stats._read_day = orig
    # None, never 0: a zero peak reads as a quiet day, not as no data.
    assert out["peak_day_tokens"] is None and out["peak_day"] is None


# --- 3. which failures are the budget's fault -------------------------------

def test_every_reason_providers_can_emit_is_classified():
    """The test the constant's comment promised -- and it found the defect.

    `_failure_reason` returns a BARE `429` when the error text names neither
    "per day" nor "per minute". The first version of BUDGET_FAIL_REASONS listed
    only 413/429_tpm/429_tpd, so that case counted as "not a budget failure"
    and the red metric under-reported a real rate limit.
    """
    src = inspect.getsource(providers._failure_reason)
    emitted = set(__import__("re").findall(r'return "([^"]+)"', src))
    assert emitted, "could not read the reasons out of _failure_reason"
    # Every emitted reason is either a budget failure or explicitly not one.
    not_budget = {"timeout", "empty", "error"}
    unclassified = emitted - set(ops_data.BUDGET_FAIL_REASONS) - not_budget
    assert not unclassified, (
        f"{sorted(unclassified)} is emitted by providers.py but classified neither as a "
        "budget failure nor as provider instability, so it silently counts as 'not the "
        "budget' and the red metric under-reports")


@pytest.mark.parametrize("reason", ["413", "429", "429_tpm", "429_tpd"])
def test_a_budget_reason_counts_as_a_budget_failure(reason):
    assert reason in ops_data.BUDGET_FAIL_REASONS


@pytest.mark.parametrize("reason", ["timeout", "empty", "error"])
def test_provider_instability_does_not_count_as_a_budget_failure(reason):
    # Counting these would point at the prompt, which no change to the prompt
    # would fix.
    assert reason not in ops_data.BUDGET_FAIL_REASONS


# --- 4. which FEATURE broke -------------------------------------------------

def _app_with_errors(errs, monkeypatch):
    _reset_app_cache()
    monkeypatch.setattr(llm_stats, "usage_summary",
                        lambda days: {"days": days, "total_calls": 10, "cache_hits": 0,
                                      "cache_misses": 10, "hit_rate_pct": 0,
                                      "total_input_tokens": 0, "total_output_tokens": 0,
                                      "by_route": []})
    monkeypatch.setattr(llm_stats, "range_summary", lambda days: {"days": []})
    monkeypatch.setattr(events, "recent", lambda **kw: errs)
    return ops_data._app_view(7)


def _err(kind, source):
    return {"data": {"error_type": kind, "source": source}}


def test_breaks_are_counted_per_feature(monkeypatch):
    app = _app_with_errors([
        _err("AllProvidersExhausted", "rashifal_single:aries"),
        _err("AllProvidersExhausted", "rashifal_single:aries"),
        _err("RequestTooLarge", "chart:natal"),
    ], monkeypatch)
    assert app["budget_breaks_total"] == 3
    assert dict(app["budget_breaks"]) == {"rashifal_single:aries": 2, "chart:natal": 1}


def test_a_fallback_is_not_a_break(monkeypatch):
    # Recovering on a second provider means the visitor got their reading.
    # Only the two exception types are user-visible failures.
    app = _app_with_errors([_err("APITimeoutError", "chart:natal")], monkeypatch)
    assert app["budget_breaks_total"] == 0


def test_request_too_large_is_a_break_although_it_subclasses_exhausted(monkeypatch):
    # providers.py: RequestTooLarge(AllProvidersExhausted). `error_type` stores
    # the CONCRETE class, so the subclass name must be listed in its own right
    # or every 413 would be missed here.
    app = _app_with_errors([_err("RequestTooLarge", "chart:natal")], monkeypatch)
    assert app["budget_breaks_total"] == 1
    assert "RequestTooLarge" in ops_data.BUDGET_ERROR_TYPES


# --- the alert thresholds ---------------------------------------------------

def test_the_daily_cap_alert_is_red_over_the_whole_bucket_and_amber_below():
    def alerts_for(pct):
        app = {"ok": True, "measured": True, "calls": 1, "errors": 0, "error_rate": 0,
               "exhausted": 0, "too_large": 0, "fallback_rate": 0, "budget_failures": 0,
               "peak_day_pct": pct, "peak_day_tokens": 1, "peak_day": "2026-10-08"}
        return ops_data._alerts({}, {}, {}, app, {})

    assert any(a["level"] == "red" for a in alerts_for(ops_data.PEAK_DAY_RED))
    assert any(a["level"] == "amber" for a in alerts_for(ops_data.PEAK_DAY_AMBER))
    assert not alerts_for(ops_data.PEAK_DAY_AMBER - 1)
