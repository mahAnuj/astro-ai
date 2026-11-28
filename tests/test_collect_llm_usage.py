"""The app's own LLM usage, snapshotted for the ops detector (owner,
2026-11-06: monitor the cache and raise it to cut Groq tokens)."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("collect_llm_usage", ROOT / "scripts" / "collect_llm_usage.py")
cu = importlib.util.module_from_spec(_spec)
sys.modules["collect_llm_usage"] = cu
_spec.loader.exec_module(cu)

NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)
USAGE = {"days": 7, "total_calls": 400, "cache_hits": 300, "cache_misses": 100, "hit_rate_pct": 75,
         "total_input_tokens": 190_000, "total_output_tokens": 40_000, "peak_day_tokens": 61_000,
         "peak_day": "2026-11-04",
         "peak_day_measured_tokens": 120_000, "peak_day_measured": "2026-11-03",
         # What /admin/ops reads. The by_route input_tokens below are 0 on every day
         # recorded since #473 -- the shape that made this collector read blind (#868).
         "measured_by_route": [
             {"route": "ask", "calls": 100, "measured": 80, "input_tokens": 152_000, "output_tokens": 20_000},
             {"route": "rashifal_single", "calls": 288, "measured": 288, "input_tokens": 960_000,
              "output_tokens": 120_000}],
         # Site-wide, from range_summary()["aggregate"] -- usage_summary() has none (#1208).
         "aggregate": {"fallbacks": 5, "fallback_reasons": {"groq120|429_tpm": 3, "groq20|quality": 1}},
         "by_route": [{"route": "ask", "calls": 100, "hits": 20, "hit_rate_pct": 20, "input_tokens": 0},
                      {"route": "rashifal", "calls": 24, "hits": 12, "hit_rate_pct": 50, "input_tokens": 0},
                      {"route": "natal", "calls": 300, "hits": 280, "hit_rate_pct": 93, "input_tokens": 0}]}


def test_input_tokens_come_from_the_measured_store_not_the_zeroed_field():
    """#868: `by_route[*].input_tokens` is 0 by design since #473; the provider-
    reported sums live in `measured_by_route`, keyed by PROVIDER route."""
    doc = cu.slim(USAGE, NOW)
    ask = next(r for r in doc["by_route"] if r["route"] == "ask")
    assert ask["input_tokens"] == 152_000 and ask["tokens_per_call"] == 152_000 // 80
    assert doc["total_input_tokens"] == 152_000 + 960_000


def test_a_provider_route_is_folded_onto_the_feature_it_serves():
    """rashifal_single -> rashifal, as ops_data does: otherwise rashifal, the
    biggest spender (#852), shows as unknown."""
    rash = next(r for r in cu.slim(USAGE, NOW)["by_route"] if r["route"] == "rashifal")
    assert rash["input_tokens"] == 960_000 and rash["measured_calls"] == 288
    assert rash["tokens_per_call"] == 960_000 // 288


def test_an_unmeasured_route_is_unknown_not_zero():
    """None, never 0: a zero reads to a ceiling detector as 'spent nothing'."""
    natal = next(r for r in cu.slim(USAGE, NOW)["by_route"] if r["route"] == "natal")
    assert natal["input_tokens"] is None and natal["tokens_per_call"] is None
    nothing = {**USAGE, "measured_by_route": []}
    doc = cu.slim(nothing, NOW)
    assert doc["total_input_tokens"] is None
    assert all(r["input_tokens"] is None for r in doc["by_route"])


def test_the_measured_peak_day_is_carried_and_absent_is_none():
    assert cu.slim(USAGE, NOW)["peak_day_measured_tokens"] == 120_000
    bare = {k: v for k, v in USAGE.items() if not k.startswith("peak_day_measured")}
    doc = cu.slim(bare, NOW)
    assert doc["peak_day_measured_tokens"] is None and doc["peak_day_measured"] is None


def test_it_writes_the_slice_the_detector_reads(tmp_path):
    out = tmp_path / "llm-usage.json"
    assert cu.main(["x", "--out", str(out)], summary=lambda d: USAGE, now=NOW) == 0
    doc = json.loads(out.read_text())
    assert {"total_calls", "hit_rate_pct", "peak_day_tokens", "by_route"} <= set(doc)
    assert doc["fallbacks"] == 5 and doc["fallback_reasons"]["groq120|429_tpm"] == 3


def test_an_unreadable_or_empty_reading_writes_nothing(tmp_path):
    """Zero calls is a reading error here, not a quiet week."""
    out = tmp_path / "llm-usage.json"

    def boom(days):
        raise PermissionError("403 storage.objects.get")
    assert cu.main(["x", "--out", str(out)], summary=boom, now=NOW) == 1
    assert cu.main(["x", "--out", str(out)], summary=lambda d: {"total_calls": 0}, now=NOW) == 1
    assert not out.exists()


def test_fallbacks_and_reasons_are_carried_from_the_aggregate():
    """#1208: site-wide, read from `aggregate` (range_summary), and sum(reasons) <= fallbacks."""
    doc = cu.slim(USAGE, NOW)
    assert doc["fallbacks"] == 5
    assert doc["fallback_reasons"] == {"groq120|429_tpm": 3, "groq20|quality": 1}
    assert sum(doc["fallback_reasons"].values()) <= doc["fallbacks"]


def test_absent_fallbacks_are_unknown_not_zero():
    """None, never 0: a zero would read as 'no provider ever failed'. Top-level
    `fallbacks` is not where they live, so it must not be read either."""
    bare = {k: v for k, v in USAGE.items() if k != "aggregate"}
    doc = cu.slim({**bare, "fallbacks": 9}, NOW)
    assert doc["fallbacks"] is None and doc["fallback_reasons"] is None
    doc = cu.slim({**USAGE, "aggregate": {"fallback_reasons": {"a|b": 1}}}, NOW)
    assert doc["fallbacks"] is None and doc["fallback_reasons"] is None


def test_zero_fallbacks_with_no_reasons_is_a_real_reading():
    doc = cu.slim({**USAGE, "aggregate": {"fallbacks": 0, "fallback_reasons": {}}}, NOW)
    assert doc["fallbacks"] == 0 and doc["fallback_reasons"] == {}


def test_fallback_reasons_are_bounded_and_clean():
    many = {f"groq{i}|r": i + 1 for i in range(30)}
    many["x" * 200 + "|long"] = 100
    many["groq|bad"] = "n/a"
    many["groq|bool"] = True
    doc = cu.slim({**USAGE, "aggregate": {"fallbacks": 999, "fallback_reasons": many}}, NOW)
    reasons = doc["fallback_reasons"]
    assert len(reasons) == 20
    assert "groq|bad" not in reasons and "groq|bool" not in reasons
    assert all(len(k) <= 80 for k in reasons)
    assert list(reasons.values())[0] == 100 and list(reasons) == sorted(reasons, key=lambda k: -reasons[k])


def test_the_default_summary_attaches_the_range_aggregate(monkeypatch):
    """#1208: the wiring. usage_summary() has no fallbacks; without this the export is a silent 0/None."""
    from astro_ai import llm_stats
    monkeypatch.setattr(llm_stats, "usage_summary", lambda days: {"total_calls": 3})
    monkeypatch.setattr(llm_stats, "range_summary",
                        lambda days: {"aggregate": {"fallbacks": 2, "fallback_reasons": {"g|429_tpm": 2}}})
    got = cu._summary(7)
    assert got["total_calls"] == 3 and got["aggregate"]["fallbacks"] == 2


# --- #1506: per-route HTTP 5xx -------------------------------------------------------------
_HE = {"from": "2026-10-31", "to": "2026-11-06", "days": 7, "days_recorded": 5, "total": 4,
       "by_route": {"GET /learn/{slug}": {"total": 3, "by_status": {"500": 2, "503": 1}},
                    "POST /kundli": {"total": 1, "by_status": {"500": 1}}}}
_HTTP_KEYS = ("http_5xx_total", "http_5xx_by_route", "http_5xx_window", "http_5xx_days_recorded")


def test_http_5xx_is_carried_with_its_window_and_coverage():
    doc = cu.slim({**USAGE, "http_errors": _HE}, NOW)
    assert doc["http_5xx_total"] == 4
    assert doc["http_5xx_by_route"] == [
        {"route": "GET /learn/{slug}", "count": 3, "by_status": {"500": 2, "503": 1}},
        {"route": "POST /kundli", "count": 1, "by_status": {"500": 1}}]
    assert doc["http_5xx_window"] == {"from": "2026-10-31", "to": "2026-11-06", "days": 7}
    assert doc["http_5xx_days_recorded"] == 5


def test_absent_or_malformed_http_errors_is_unknown_not_zero():
    for bad in (None, "x", [], {}, {**_HE, "days_recorded": True}, {**_HE, "from": None}):
        doc = cu.slim({**USAGE, "http_errors": bad}, NOW)
        assert all(doc[k] is None for k in _HTTP_KEYS), bad
    assert all(cu.slim(USAGE, NOW)[k] is None for k in _HTTP_KEYS)


def test_no_recorded_day_means_total_and_routes_are_unknown_not_zero():
    """The recorder wrote nothing in the window: that is no evidence, and a 0 would read as 'no 5xx'."""
    doc = cu.slim({**USAGE, "http_errors": {**_HE, "days_recorded": 0, "total": 0, "by_route": {}}}, NOW)
    assert doc["http_5xx_total"] is None and doc["http_5xx_by_route"] is None
    assert doc["http_5xx_days_recorded"] == 0 and doc["http_5xx_window"]["days"] == 7


def test_recorded_days_with_no_errors_is_a_real_zero():
    doc = cu.slim({**USAGE, "http_errors": {**_HE, "days_recorded": 3, "total": 0, "by_route": {}}}, NOW)
    assert doc["http_5xx_total"] == 0 and doc["http_5xx_by_route"] == []
    assert doc["http_5xx_days_recorded"] == 3


def test_http_5xx_routes_are_sorted_capped_and_clean():
    many = {f"GET /r{i}": {"total": i + 1, "by_status": {"500": i + 1}} for i in range(30)}
    many["GET /" + "x" * 200] = {"total": 100, "by_status": {"500": 100}}
    many["GET /bad"] = {"total": "n/a"}
    many["GET /neg"] = {"total": -4}
    doc = cu.slim({**USAGE, "http_errors": {**_HE, "by_route": many}}, NOW)
    rows = doc["http_5xx_by_route"]
    assert len(rows) == 20 and rows[0]["count"] == 100
    assert [r["count"] for r in rows] == sorted((r["count"] for r in rows), reverse=True)
    assert all(len(r["route"]) <= 80 for r in rows)
    assert not {"GET /bad", "GET /neg"} & {r["route"] for r in rows}


def test_the_window_spans_exactly_the_days_asked(tmp_path, monkeypatch):
    from datetime import date
    from astro_ai import http_errors
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setenv("BHAGYA_HTTP_ERRORS_FALLBACK_DIR", str(tmp_path))
    s = http_errors.range_summary(7, date(2026, 11, 6))
    assert (s["from"], s["to"], s["days"], s["days_recorded"]) == ("2026-10-31", "2026-11-06", 7, 0)
    assert (cu.slim({**USAGE, "http_errors": s}, NOW)["http_5xx_window"]
            == {"from": "2026-10-31", "to": "2026-11-06", "days": 7})


def test_the_default_summary_attaches_http_errors_and_a_failed_read_is_none(monkeypatch):
    """The 5xx read is its own failure domain: it must not fail the collect, unlike the fallbacks line."""
    from astro_ai import http_errors, llm_stats
    monkeypatch.setattr(llm_stats, "usage_summary", lambda days: {"total_calls": 3})
    monkeypatch.setattr(llm_stats, "range_summary", lambda days: {"aggregate": {"fallbacks": 0}})
    monkeypatch.setattr(http_errors, "range_summary", lambda days: _HE)
    assert cu._summary(7)["http_errors"] == _HE

    def boom(days):
        raise PermissionError("403")
    monkeypatch.setattr(http_errors, "range_summary", boom)
    got = cu._summary(7)
    assert got["http_errors"] is None and got["total_calls"] == 3
    doc = cu.slim({**USAGE, **got}, NOW)
    assert doc["total_calls"] == 3 and all(doc[k] is None for k in _HTTP_KEYS)


def test_it_writes_the_http_5xx_keys(tmp_path):
    out = tmp_path / "llm-usage.json"
    assert cu.main(["x", "--out", str(out)], summary=lambda d: {**USAGE, "http_errors": _HE}, now=NOW) == 0
    doc = json.loads(out.read_text())
    assert doc["http_5xx_total"] == 4 and doc["http_5xx_days_recorded"] == 5
