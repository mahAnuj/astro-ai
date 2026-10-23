"""The "blocked on bucket" column and the store behind it (#475, Phase 1, S1).

WHY THIS EXISTS
---------------
Phase 1 puts a per-process token bucket in front of each Groq model. Before it
does anything, the ops page needs somewhere to show what it did -- otherwise the
first evidence that pacing helps (or hurts) is a 429 count, which is the thing
it is meant to remove. This file holds the read/write side only; nothing here
produces a pacing dict, so every test hands `record()` one directly.

What is easy to get quietly wrong, and so is pinned:

  * `record()` must still make exactly ONE storage write per call -- the new
    key rides the existing mutator. A second `update_json` per call would double
    the cross-continent GCS round-trips on the LLM path (#144).
  * a dash and a zero must not look alike: `reserved` is written whenever pacing
    was on, so a model the bucket never blocked prints `0`, and a model nobody
    recorded pacing for prints `—`;
  * a day with no `paced_by_model` contributes NOTHING and is not counted in
    `paced_days`;
  * a hand-edited blob must not take the window down;
  * the new key changes nothing `range_summary` reports (a ninth `_PREFIX_ZERO`
    key is how the prefix-cache panel once emptied itself).

Every assertion drives the real function (`record`, `usage_summary`,
`_model_rows`, the rendered page).
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from astro_ai import events, llm_stats, ops_data

G120 = ("groq120", "openai/gpt-oss-120b")
K120, K20, KOAI = "groq120|openai/gpt-oss-120b", "groq20|openai/gpt-oss-20b", "openai|gpt-4o-mini"


def _pace(reserved=1, waits=0, wait_ms=0, skips=0, forced=0):
    return {"reserved": reserved, "waits": waits, "wait_ms": wait_ms,
            "skips": skips, "forced": forced}


@pytest.fixture
def day(monkeypatch, tmp_path):
    """An isolated per-day stats dir, so record() writes somewhere we can read."""
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path)
    monkeypatch.setattr(llm_stats.storage, "update_json", lambda *a, **k: None)
    monkeypatch.setattr(llm_stats.storage, "get_json", lambda *a, **k: None)
    return tmp_path


def _blob(day_dir: Path) -> dict:
    files = list(day_dir.glob("*.json"))
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


def _write_day(day_dir: Path, d: date, blob: dict) -> None:
    (day_dir / f"{d.isoformat()}.json").write_text(json.dumps(
        {"date": d.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0, **blob}))


# --------------------------------------------------------------------------- #
# the write side
# --------------------------------------------------------------------------- #

def test_record_writes_paced_by_model_and_sums_across_calls(day):
    llm_stats.record(provider=G120[0], model=G120[1], route="rashifal_single",
                     prompt_tokens=3000, completion_tokens=500,
                     pacing={K120: _pace(reserved=1, waits=1, wait_ms=4470, skips=1)})
    llm_stats.record(provider=G120[0], model=G120[1], route="rashifal_single",
                     prompt_tokens=3000, completion_tokens=500,
                     pacing={K120: _pace(reserved=1, forced=1)})
    p = _blob(day)["paced_by_model"][K120]
    assert p == {"reserved": 2, "waits": 1, "wait_ms": 4470, "skips": 1, "forced": 1}


def test_a_call_with_no_pacing_writes_no_key_at_all(day):
    """Absent, not zero: that is how the panel tells 'not paced' from 'never blocked'."""
    llm_stats.record(provider=G120[0], model=G120[1], route="natal",
                     prompt_tokens=100, completion_tokens=50)
    assert "paced_by_model" not in _blob(day)
    llm_stats.record(provider=G120[0], model=G120[1], route="natal",
                     prompt_tokens=100, completion_tokens=50, pacing=None)
    assert "paced_by_model" not in _blob(day)


def test_pacing_on_but_nothing_waited_is_written_as_a_zero_not_omitted(day):
    llm_stats.record(provider=G120[0], model=G120[1], route="natal",
                     prompt_tokens=100, completion_tokens=50, pacing={K120: _pace(reserved=1)})
    assert _blob(day)["paced_by_model"][K120]["wait_ms"] == 0
    assert _blob(day)["paced_by_model"][K120]["reserved"] == 1


def test_record_is_still_exactly_one_storage_write_per_call(monkeypatch):
    calls = []

    def fake_update(key, mut, default=None):
        calls.append(key)
        return mut(None)                     # non-None: no local-fallback second write

    monkeypatch.setattr(llm_stats.storage, "update_json", fake_update)
    llm_stats.record(provider=G120[0], model=G120[1], route="rashifal_single",
                     prompt_tokens=3000, completion_tokens=500,
                     pacing={K120: _pace(reserved=1, waits=1, wait_ms=900)})
    assert len(calls) == 1, f"pacing must ride the existing mutator, got {len(calls)} writes"


def test_one_record_call_books_every_model_in_the_mapping_under_its_own_key(day):
    """The serving model is K20; K120 only waited and 429'd. Both must land."""
    llm_stats.record(provider=G120[0], model="x", route="natal",
                     pacing={K120: _pace(reserved=1, waits=1, wait_ms=3000),
                             K20: _pace(reserved=1, skips=2)})
    p = _blob(day)["paced_by_model"]
    assert p[K120] == {"reserved": 1, "waits": 1, "wait_ms": 3000, "skips": 0, "forced": 0}
    assert p[K20] == {"reserved": 1, "waits": 0, "wait_ms": 0, "skips": 2, "forced": 0}
    assert f"{G120[0]}|x" not in p, "the serving model was credited with a pacing it did not do"


def test_the_blob_grows_with_models_not_with_calls(day):
    for i in range(200):
        who = ("groq120", "a") if i % 2 else ("groq20", "b")
        llm_stats.record(provider=who[0], model=who[1], route="natal", pacing={f"{who[0]}|{who[1]}": _pace(waits=1, wait_ms=10)})
    p = _blob(day)["paced_by_model"]
    assert set(p) == {"groq120|a", "groq20|b"}
    assert sum(v["reserved"] for v in p.values()) == 200


def test_a_garbage_or_negative_pacing_value_cannot_poison_the_counters(day):
    llm_stats.record(provider="g", model="m", route="natal",
                     pacing={"g|m": {"reserved": 2, "waits": "x", "wait_ms": -500, "skips": None,
                                     "forced": True}})
    assert _blob(day)["paced_by_model"]["g|m"] == {
        "reserved": 2, "waits": 0, "wait_ms": 0, "skips": 0, "forced": 0}


# --------------------------------------------------------------------------- #
# the read side
# --------------------------------------------------------------------------- #

def _mm(calls, measured, i, o):
    return {"calls": calls, "measured": measured, "input_tokens": i, "output_tokens": o}


def test_usage_summary_sums_pacing_and_counts_only_days_that_carried_it(day):
    today = date.today()
    _write_day(day, today, {
        "measured_by_model": {K120: _mm(4, 4, 4000, 2000)},
        "paced_by_model": {K120: _pace(4, 2, 5000, 1, 0)}})
    _write_day(day, today - timedelta(days=1), {
        "measured_by_model": {K120: _mm(6, 6, 6000, 3000)},
        "paced_by_model": {K120: _pace(6, 3, 7000, 0, 1)}})
    # per-model figures but NO pacing (switch off that day): not a paced day
    _write_day(day, today - timedelta(days=2), {"measured_by_model": {K120: _mm(1, 1, 10, 5)}})
    # a legacy day with neither
    _write_day(day, today - timedelta(days=3), {})
    s = llm_stats.usage_summary(4)
    assert s["paced_days"] == 2, "only days that carried paced_by_model"
    assert s["model_days_recorded"] == 3
    (row,) = s["measured_by_model"]
    assert (row["reserved"], row["waits"], row["wait_ms"], row["skips"], row["forced"]) == (
        10, 5, 12000, 1, 1)
    assert row["calls"] == 11, "the pacing fields must not disturb the call counters"


def test_a_model_with_no_pacing_row_reports_none_not_zero(day):
    _write_day(day, date.today(), {
        "measured_by_model": {K120: _mm(1, 1, 10, 5), KOAI: _mm(2, 2, 10, 5)},
        "paced_by_model": {K120: _pace(1)}})
    rows = {r["key"]: r for r in llm_stats.usage_summary(1)["measured_by_model"]}
    assert rows[K120]["reserved"] == 1
    for f in ("reserved", "waits", "wait_ms", "skips", "forced"):
        assert rows[KOAI][f] is None, f


def test_a_window_with_no_pacing_has_zero_paced_days(day):
    _write_day(day, date.today(), {"measured_by_model": {K120: _mm(1, 1, 10, 5)}})
    s = llm_stats.usage_summary(1)
    assert s["paced_days"] == 0
    assert s["measured_by_model"][0]["reserved"] is None


def test_malformed_pacing_does_not_raise_and_range_summary_is_unchanged(day):
    today = date.today()
    base = {"counts": {"groq120|openai/gpt-oss-120b|natal": 3}, "totals": {"natal": 3},
            "fallbacks": 1, "fallback_reasons": {"groq120|429_tpm": 1}}
    _write_day(day, today, base)
    plain = llm_stats.range_summary(1)["aggregate"]
    _write_day(day, today, {**base,
        "measured_by_model": {"e|f": _mm(2, 2, 10, 5)},
        "paced_by_model": {"a|b": "garbage", "c|d": {"reserved": "x", "waits": [1], "wait_ms": True},
                           "e|f": _pace(2, 1, 300)}})
    s = llm_stats.usage_summary(1)                      # must not raise
    rows = {r["key"]: r for r in s["measured_by_model"]}
    assert rows["e|f"]["wait_ms"] == 300
    assert "a|b" not in rows
    assert rows["c|d"]["reserved"] == 0, "a malformed value counts as 0, it does not raise"
    assert llm_stats.range_summary(1)["aggregate"] == plain, (
        "the new key must not change anything range_summary reports")


# --------------------------------------------------------------------------- #
# the panel rows
# --------------------------------------------------------------------------- #

def _urow(key, calls=10, **pace):
    prov, _, model = key.partition("|")
    row = {"key": key, "provider": prov, "model": model, "calls": calls, "measured": calls,
           "input_tokens": 9000, "output_tokens": 4000, "peak_tpm": 6000,
           "peak_minute": "2026-10-22T14:03+00:00",
           "reserved": None, "waits": None, "wait_ms": None, "skips": None, "forced": None}
    row.update(pace)
    return row


def _usage(rows, days_rec=3, paced_days=2, days=7):
    return {"days": days, "model_days_recorded": days_rec, "paced_days": paced_days,
            "measured_by_model": rows}


def test_model_rows_turn_milliseconds_into_seconds_and_keep_the_counts():
    (r,) = ops_data._model_rows(_usage([_urow(
        K120, reserved=17, waits=5, wait_ms=42000, skips=2, forced=1)]), [K120], {})
    assert (r["reserved"], r["waits"], r["wait_s"], r["skips"], r["forced"]) == (17, 5, 42.0, 2, 1)


def test_model_rows_measured_zero_is_zero_and_silence_is_none():
    rows = {r["key"]: r for r in ops_data._model_rows(_usage([
        _urow(K120, reserved=5, waits=0, wait_ms=0, skips=0, forced=0),
        _urow(K20)]), [K120, K20, KOAI], {})}
    assert rows[K120]["reserved"] == 5 and rows[K120]["wait_s"] == 0
    for key in (K20, KOAI):                        # recorded-but-unpaced, and never seen
        assert rows[key]["reserved"] is None and rows[key]["wait_s"] is None, key


def test_a_legacy_window_has_no_pacing_figures_either():
    for r in ops_data._model_rows({"days": 7, "model_days_recorded": 0}, [K120], {}):
        assert r["reserved"] is None and r["wait_s"] is None


# --------------------------------------------------------------------------- #
# the page
# --------------------------------------------------------------------------- #

@pytest.fixture
def _ops(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(events, "error_breakdown", lambda **k: {})
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _page_html(monkeypatch, extra, chain=(K120, K20)):
    from fastapi.testclient import TestClient

    from astro_ai.main import app
    from astro_ai.routes import deps
    base = {"days": 7, "total_calls": 40, "cache_hits": 0, "cache_misses": 40,
            "hit_rate_pct": 0, "total_input_tokens": 0, "total_output_tokens": 0,
            "by_route": []}
    monkeypatch.setattr(llm_stats, "usage_summary", lambda d: {**base, "days": d, **extra})
    monkeypatch.setattr(llm_stats, "range_summary", lambda d: {
        "days": [], "aggregate": {"fallback_reasons": {}}})
    monkeypatch.setattr(ops_data, "_chain_keys", lambda: list(chain))
    ops_data._app_cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def _panel(html: str) -> str:
    start = html.index("Tokens per minute, by model")
    return html[start:html.index("</section>", start)]


def _cells(panel: str, key_model: str) -> list[str]:
    """The <td> contents of the row whose first cell names `key_model`, whitespace-flattened."""
    for tr in re.findall(r"<tr>.*?</tr>", panel, flags=re.S):
        if key_model in tr:
            return [" ".join(re.sub(r"<[^>]+>", " ", td).split())
                    for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
    raise AssertionError(f"no row for {key_model}")


def test_the_page_prints_a_dash_for_silence(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, _usage([_urow(K120)], paced_days=0)))
    assert "blocked on bucket" in panel
    assert _cells(panel, "gpt-oss-120b")[-1] == "—"
    assert "None" not in panel


def test_the_page_prints_zero_for_a_measured_zero(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, _usage([_urow(
        K120, reserved=5, waits=0, wait_ms=0, skips=0, forced=0)])))
    cell = _cells(panel, "gpt-oss-120b")[-1]
    assert cell.startswith("0 "), cell
    assert "0 of 5 waited · 0 skipped · 0 forced" in cell
    assert not cell.startswith("—")
    assert "None" not in panel


def test_the_page_prints_seconds_and_the_sub_line_when_populated(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, _usage([_urow(
        K120, reserved=17, waits=5, wait_ms=42000, skips=2, forced=1)])))
    cell = _cells(panel, "gpt-oss-120b")[-1]
    assert cell == "42 s 5 of 17 waited · 2 skipped · 1 forced", cell
    assert "None" not in panel


def test_a_model_that_was_only_skipped_does_not_read_0_of_0_waited(_ops, monkeypatch):
    """QA round 2: skips with no reservations printed "0 of 0 waited · 2 skipped"."""
    panel = _panel(_page_html(monkeypatch, _usage([_urow(
        K120, reserved=0, waits=0, wait_ms=0, skips=2, forced=1)])))
    cell = _cells(panel, "gpt-oss-120b")[-1]
    assert cell == "0 none admitted · 2 skipped · 1 forced", cell


def test_a_sub_second_wait_is_not_rounded_into_a_false_zero(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, _usage([_urow(
        K120, reserved=3, waits=1, wait_ms=400)])))
    assert _cells(panel, "gpt-oss-120b")[-1].startswith("0.4 s ")


def test_the_panel_has_eight_columns_and_says_per_process(_ops, monkeypatch):
    html = _page_html(monkeypatch, _usage([_urow(K120)]))
    panel = _panel(html)
    flat = " ".join(panel.split())
    assert len(re.findall(r"<th[ >]", panel)) == 8
    assert 'class="rt cols8"' in panel
    assert "per process, not account" in flat
    assert ".rt.cols8{" in html, "the min-width rule for the new table must exist"
    assert "for 2 of 7 days" in flat, "the paced-days sentence"
    assert len(_cells(panel, "gpt-oss-120b")) == 8


def test_the_empty_state_colspan_matches_the_column_count(_ops, monkeypatch):
    panel = _panel(_page_html(monkeypatch, {}, chain=()))
    assert 'colspan="8"' in panel
