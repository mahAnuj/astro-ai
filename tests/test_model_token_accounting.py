"""Per-MODEL token accounting and the busiest-minute figure (#475, Phase 0).

WHY THIS EXISTS
---------------
`measured_by_route` answers "what does one <feature> request cost". It cannot
answer "how close is groq120 to its 8,000 TPM bucket", because the bucket is
enforced per MODEL and a chain that falls back mid-feature spreads one feature
across several of them. On 2026-10-21 every feature row sat under its line
while `groq20 429_tpm x2 / groq120 429_tpm x1` were being returned.

So there is a SECOND store beside the first: `measured_by_model` (four counters,
keyed `provider|model`) and `peak_tpm_by_model` (ONE overwritten entry per model,
never a list of minutes). These tests hold what is easy to get quietly wrong:

  * the silence rule -- an unsized call is a call, not a zero-token minute;
  * the minute arithmetic -- reset, max-not-last, and the late arrival that must
    neither reset nor inflate;
  * that the second store RECONCILES with the first, so the two panels cannot
    disagree about the same calls;
  * that a day recorded before this existed contributes nothing and does not
    dilute (a silence is not a zero);
  * what the panel prints, including that it never prints a literal "None".

Every assertion drives the real function (`record`, `usage_summary`,
`_model_rows`, the rendered page). None reimplements the arithmetic.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from astro_ai import events, llm_stats, ops_data

G120 = ("groq120", "openai/gpt-oss-120b")
G20 = ("groq20", "openai/gpt-oss-20b")


@pytest.fixture
def day(monkeypatch, tmp_path):
    """An isolated per-day stats dir, so record() writes somewhere we can read."""
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path)
    monkeypatch.setattr(llm_stats.storage, "update_json", lambda *a, **k: None)
    monkeypatch.setattr(llm_stats.storage, "get_json", lambda *a, **k: None)
    return tmp_path


@pytest.fixture
def clock(monkeypatch):
    """Pin the UTC epoch minute. `clock.at(n)` moves it."""
    state = {"m": 29_000_000}

    class _C:
        @staticmethod
        def at(m: int) -> None:
            state["m"] = m

        @property
        def m(self) -> int:
            return state["m"]

    monkeypatch.setattr(llm_stats, "_now_minute", lambda: state["m"])
    return _C()


def _blob(day_dir: Path) -> dict:
    files = [f for f in day_dir.glob("*.json")]
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


def _rec(who, route="rashifal_single", p=1000, c=500):
    llm_stats.record(provider=who[0], model=who[1], route=route,
                     prompt_tokens=p, completion_tokens=c)


def _peak(day_dir, who):
    return _blob(day_dir)["peak_tpm_by_model"][f"{who[0]}|{who[1]}"]


# --------------------------------------------------------------------------- #
# the store: counters
# --------------------------------------------------------------------------- #

def test_two_models_on_one_route_make_two_model_rows_and_one_route_row(day, clock):
    _rec(G120)
    _rec(G20)
    b = _blob(day)
    assert set(b["measured_by_model"]) == {"groq120|openai/gpt-oss-120b",
                                           "groq20|openai/gpt-oss-20b"}
    assert list(b["measured_by_route"]) == ["rashifal_single"], (
        "measured_by_route must stay keyed by route alone")
    assert b["measured_by_route"]["rashifal_single"]["calls"] == 2


def test_the_model_store_reconciles_with_the_route_store(day, clock):
    """Same calls, two groupings: every counter must sum to the same total."""
    _rec(G120, "rashifal_single", 3210, 1923)
    _rec(G20, "rashifal_single", 3000, 1000)
    _rec(G120, "natal", 4000, 800)
    llm_stats.record(provider=G120[0], model=G120[1], route="natal")           # silent
    llm_stats.record(provider=G20[0], model=G20[1], route="ask",
                     prompt_tokens=500)                                         # half
    b = _blob(day)
    for field in ("calls", "measured", "input_tokens", "output_tokens"):
        by_model = sum(v[field] for v in b["measured_by_model"].values())
        by_route = sum(v[field] for v in b["measured_by_route"].values())
        assert by_model == by_route, f"{field}: {by_model} != {by_route}"
    assert sum(v["calls"] for v in b["measured_by_model"].values()) == 5


def test_a_silent_call_counts_as_a_call_and_touches_no_accumulator(day, clock):
    _rec(G120, p=1000, c=500)
    before = dict(_peak(day, G120))
    llm_stats.record(provider=G120[0], model=G120[1], route="natal")                   # silent
    llm_stats.record(provider=G120[0], model=G120[1], route="natal",
                     prompt_tokens=9000)                                                # half
    b = _blob(day)
    mm = b["measured_by_model"]["groq120|openai/gpt-oss-120b"]
    assert mm["calls"] == 3 and mm["measured"] == 1
    assert (mm["input_tokens"], mm["output_tokens"]) == (1000, 500)
    assert _peak(day, G120) == before, "an unsized call must not move the minute"


def test_a_model_that_never_reported_gets_no_peak_entry(day, clock):
    llm_stats.record(provider="x", model="m", route="natal")
    b = _blob(day)
    assert b["measured_by_model"]["x|m"]["calls"] == 1
    assert "x|m" not in (b.get("peak_tpm_by_model") or {}), (
        "a call nobody could size is not a zero-token minute")


# --------------------------------------------------------------------------- #
# the store: the minute
# --------------------------------------------------------------------------- #

def test_the_same_minute_accumulates_and_a_later_minute_resets(day, clock):
    clock.at(100)
    _rec(G120, p=1000, c=500)
    _rec(G120, p=2000, c=500)
    e = _peak(day, G120)
    assert (e["minute"], e["tokens"], e["peak"], e["peak_minute"]) == (100, 4000, 4000, 100)
    clock.at(101)
    _rec(G120, p=300, c=100)
    e = _peak(day, G120)
    assert e["minute"] == 101
    assert e["tokens"] == 400, "a new minute starts from zero, not from the last total"
    assert e["peak"] == 4000, "the peak is the MAX, not the latest minute"
    assert e["peak_minute"] == 100, "and it remembers WHICH minute"


def test_a_quieter_minute_after_a_busy_one_does_not_lower_the_peak(day, clock):
    clock.at(5)
    _rec(G120, p=5000, c=1000)
    clock.at(6)
    _rec(G120, p=10, c=10)
    clock.at(7)
    _rec(G120, p=20, c=20)
    assert _peak(day, G120)["peak"] == 6000


def test_a_late_arrival_neither_resets_nor_inflates_the_open_minute(day, clock):
    clock.at(200)
    _rec(G120, p=1000, c=0)
    clock.at(201)
    _rec(G120, p=500, c=0)
    clock.at(200)                      # finished late, belongs to a closed minute
    _rec(G120, p=7000, c=0)
    e = _peak(day, G120)
    assert e["minute"] == 201 and e["tokens"] == 500, "the open minute is untouched"
    assert e["peak"] == 1000, "and the late 7,000 is not folded into any peak"
    # but the call is still a call, with its tokens, in the counters
    mm = _blob(day)["measured_by_model"]["groq120|openai/gpt-oss-120b"]
    assert mm["calls"] == 3 and mm["input_tokens"] == 8500


def test_the_blob_grows_with_models_not_with_minutes(day, clock):
    for i in range(500):
        clock.at(1000 + i // 167)                     # 3 minutes
        _rec(G120 if i % 2 else G20)
    b = _blob(day)
    assert len(b["peak_tpm_by_model"]) == 2
    assert len(b["measured_by_model"]) == 2
    assert sum(v["calls"] for v in b["measured_by_model"].values()) == 500


# --------------------------------------------------------------------------- #
# the read side
# --------------------------------------------------------------------------- #

def _write_day(day_dir: Path, d: date, blob: dict) -> None:
    (day_dir / f"{d.isoformat()}.json").write_text(json.dumps(
        {"date": d.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0, **blob}))


def _mm(calls, measured, i, o):
    return {"calls": calls, "measured": measured, "input_tokens": i, "output_tokens": o}


def test_across_days_the_peak_is_the_max_and_the_tokens_are_the_sum(day, clock):
    today = date.today()
    key = "groq120|openai/gpt-oss-120b"
    _write_day(day, today, {
        "measured_by_model": {key: _mm(4, 4, 4000, 2000)},
        "peak_tpm_by_model": {key: {"peak": 5000, "peak_minute": 29_000_010,
                                    "minute": 29_000_010, "tokens": 5000}}})
    _write_day(day, today - timedelta(days=1), {
        "measured_by_model": {key: _mm(6, 5, 6000, 3000)},
        "peak_tpm_by_model": {key: {"peak": 7400, "peak_minute": 28_999_000,
                                    "minute": 28_999_000, "tokens": 100}}})
    # a pre-change day: contributes NOTHING and must not dilute
    _write_day(day, today - timedelta(days=2), {})
    s = llm_stats.usage_summary(3)
    assert s["model_days_recorded"] == 2, "only days that carried the key"
    (row,) = s["measured_by_model"]
    assert row["key"] == key
    assert (row["provider"], row["model"]) == ("groq120", "openai/gpt-oss-120b")
    assert (row["calls"], row["measured"]) == (10, 9)
    assert (row["input_tokens"], row["output_tokens"]) == (10000, 5000)
    assert row["peak_tpm"] == 7400, "MAX across days, not 5,000 + 7,400"
    # epoch minute 28,999,000 * 60 s = 1739940000 = 2025-02-19 04:40 UTC, and it
    # must be the minute of the 7,400 peak, not of the other day's 5,000
    assert row["peak_minute"] == "2025-02-19T04:40+00:00"


def test_a_window_of_only_legacy_days_is_not_recorded_rather_than_zero(day, clock):
    _write_day(day, date.today(), {})
    s = llm_stats.usage_summary(1)
    assert s["measured_by_model"] == []
    assert s["model_days_recorded"] == 0


def test_malformed_rows_do_not_raise_and_the_range_summary_is_unchanged(day, clock):
    today = date.today()
    base = {"counts": {"groq120|openai/gpt-oss-120b|natal": 3}, "totals": {"natal": 3},
            "fallbacks": 1, "fallback_reasons": {"groq120|429_tpm": 1}}
    _write_day(day, today, base)
    plain = llm_stats.range_summary(1)["aggregate"]
    _write_day(day, today, {**base,
        "measured_by_model": {"a|b": "garbage", "c|d": _mm("x", None, True, [1]),
                              "e|f": _mm(2, 2, 10, 5)},
        "peak_tpm_by_model": {"a|b": 7, "e|f": {"peak": "NaN", "peak_minute": "x"},
                              "g|h": {"peak": 90, "peak_minute": 5}}})
    s = llm_stats.usage_summary(1)           # must not raise
    keys = {r["key"] for r in s["measured_by_model"]}
    assert "e|f" in keys
    assert llm_stats.range_summary(1)["aggregate"] == plain, (
        "the new keys must not change anything range_summary reports -- a ninth "
        "key in _PREFIX_ZERO is how the prefix-cache panel emptied itself")


# --------------------------------------------------------------------------- #
# the panel rows
# --------------------------------------------------------------------------- #

K120, K20, KOAI = "groq120|openai/gpt-oss-120b", "groq20|openai/gpt-oss-20b", "openai|gpt-4o-mini"


def _usage(rows, days_rec=3, days=7):
    return {"days": days, "model_days_recorded": days_rec, "measured_by_model": rows}


def _urow(key, calls=10, measured=9, i=9000, o=4000, peak=6000,
          minute="2026-10-22T14:03+00:00"):
    prov, _, model = key.partition("|")
    return {"key": key, "provider": prov, "model": model, "calls": calls,
            "measured": measured, "input_tokens": i, "output_tokens": o,
            "peak_tpm": peak, "peak_minute": minute}


def test_model_rows_follow_chain_order_then_unlisted_models_by_calls():
    usage = _usage([_urow(K20, calls=2), _urow("zz|old", calls=50), _urow("aa|older", calls=9)])
    rows = ops_data._model_rows(usage, [K120, K20], {})
    assert [r["key"] for r in rows] == [K120, K20, "zz|old", "aa|older"]
    assert [r["in_chain"] for r in rows] == [True, True, False, False]


def test_a_chain_model_that_served_nothing_shows_zero_calls_and_dashes():
    rows = {r["key"]: r for r in ops_data._model_rows(
        _usage([_urow(K20)], days_rec=3), [K120, K20], {})}
    r = rows[K120]
    assert r["calls"] == 0
    assert r["input_tokens"] is None and r["peak"] is None and r["pct"] is None
    assert r["title"] == "served no calls in the 3 recorded days"


def test_a_legacy_window_is_not_recorded_in_every_cell():
    rows = ops_data._model_rows(_usage([], days_rec=0), [K120, K20],
                                {"fallback_reasons": {"groq120|429_tpm": 4}})
    for r in rows:
        assert r["title"] == "not recorded"
        assert all(r[k] is None for k in
                   ("calls", "unsized", "input_tokens", "output_tokens",
                    "peak", "pct", "fb429")), r


def test_the_percentage_is_the_peak_over_the_module_constant():
    (r,) = ops_data._model_rows(_usage([_urow(K120, peak=6000)]), [K120], {})
    assert r["pct"] == round(6000 / ops_data.TPM_PER_MODEL * 100) == 75
    (r,) = ops_data._model_rows(_usage([_urow(K120, peak=9400)]), [K120], {})
    assert r["pct"] == 118, "above 100% is shown, not clamped: it is an approximation"


def test_only_groq_models_get_a_percentage_of_the_groq_bucket():
    rows = {r["key"]: r for r in ops_data._model_rows(
        _usage([_urow(K120), _urow(KOAI, peak=3000)]), [K120, KOAI], {})}
    assert rows[K120]["pct"] is not None
    assert rows[KOAI]["peak"] == 3000 and rows[KOAI]["pct"] is None


def test_unsized_calls_are_calls_minus_measured_and_silence_is_not_zero_tokens():
    (r,) = ops_data._model_rows(_usage([_urow(K120, calls=10, measured=9)]), [K120], {})
    assert r["calls"] == 10 and r["unsized"] == 1
    (r,) = ops_data._model_rows(
        _usage([_urow(K120, calls=4, measured=0, i=0, o=0, peak=None, minute=None)]),
        [K120], {})
    assert r["input_tokens"] is None and r["output_tokens"] is None
    assert r["peak"] is None and r["pct"] is None


def test_the_429_column_counts_only_bucket_429s_joined_on_the_provider():
    agg = {"fallback_reasons": {"groq120|429_tpm": 1, "groq20|429_tpm": 2,
                                "groq20|429_tpd": 1, "groq20|timeout": 9,
                                "groq20|413": 3, "groq20|429": 5}}
    rows = {r["key"]: r for r in ops_data._model_rows(
        _usage([_urow(K120), _urow(K20)]), [K120, K20], agg)}
    assert rows[K120]["fb429"] == 1
    assert rows[K20]["fb429"] == 3, "429_tpm + 429_tpd only; timeout/413/bare 429 excluded"


# --------------------------------------------------------------------------- #
# _app_view and the page
# --------------------------------------------------------------------------- #

@pytest.fixture
def _ops(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(events, "error_breakdown", lambda **k: {})
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _stub_usage(monkeypatch, extra: dict):
    base = {"days": 7, "total_calls": 40, "cache_hits": 0, "cache_misses": 40,
            "hit_rate_pct": 0, "total_input_tokens": 0, "total_output_tokens": 0,
            "by_route": []}
    monkeypatch.setattr(llm_stats, "usage_summary", lambda d: {**base, "days": d, **extra})
    monkeypatch.setattr(llm_stats, "range_summary", lambda d: {
        "days": [], "aggregate": {"fallback_reasons": {"groq20|429_tpm": 2}}})


def test_app_view_survives_a_usage_summary_without_the_new_keys(_ops, monkeypatch):
    """Existing stubs (and any rolled-back writer) omit the per-model keys."""
    _stub_usage(monkeypatch, {})
    monkeypatch.setattr(ops_data, "_chain_keys", lambda: [K120, K20])
    app = ops_data._app_view(7)
    assert app["ok"] is True
    assert app["models_days_recorded"] == 0
    assert [m["key"] for m in app["models"]] == [K120, K20]


def _page_html(monkeypatch, extra, chain=(K120, K20)):
    from fastapi.testclient import TestClient

    from astro_ai.main import app
    from astro_ai.routes import deps
    _stub_usage(monkeypatch, extra)
    monkeypatch.setattr(ops_data, "_chain_keys", lambda: list(chain))
    ops_data._app_cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def _panel(html: str) -> str:
    start = html.index("Tokens per minute, by model")
    return html[start:html.index("</section>", start)]


def test_the_page_renders_the_model_panel_with_its_caveats(_ops, monkeypatch):
    html = _page_html(monkeypatch, {
        "model_days_recorded": 2,
        "measured_by_model": [_urow(K120, peak=6000), _urow("zz|old", calls=3, measured=3)]})
    panel = _panel(html)
    flat = " ".join(panel.split())
    assert "Tokens per minute, by model" in flat
    assert "a 429 is in no figure here" in flat
    assert "A high figure proves pressure. A low one proves nothing about headroom." in flat
    assert "shared by every instance" in flat
    assert "for 2 of 7 days" in flat
    assert "not in current chain" in flat
    assert f"% of {ops_data.TPM_PER_MODEL:,} TPM" in flat
    assert "75%" in flat
    assert "10-22 14:03 UTC" in flat
    assert "each instance observes only" not in flat.lower(), (
        "the per-instance claim is true only of the local fallback file")


def test_the_panel_never_prints_the_word_none(_ops, monkeypatch):
    for extra, label in (
        ({}, "legacy window, nothing recorded"),
        ({"model_days_recorded": 1, "measured_by_model": [
            _urow(K120, calls=4, measured=0, i=0, o=0, peak=None, minute=None)]},
         "all-silent model"),
        ({"model_days_recorded": 1, "measured_by_model": [_urow(KOAI)]},
         "non-groq model with a peak"),
    ):
        ops_data._app_cache.clear()
        panel = _panel(_page_html(monkeypatch, extra, chain=(K120, K20, KOAI)))
        assert "None" not in panel, f"literal None in the panel ({label})"
        assert "—" in panel


def test_a_legacy_window_says_not_recorded_on_the_page(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, {}))
    assert 'title="not recorded"' in panel
    assert "for 0 of 7 days" in " ".join(panel.split())
