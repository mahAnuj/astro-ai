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


def test_an_unreadable_or_empty_reading_writes_nothing(tmp_path):
    """Zero calls is a reading error here, not a quiet week."""
    out = tmp_path / "llm-usage.json"

    def boom(days):
        raise PermissionError("403 storage.objects.get")
    assert cu.main(["x", "--out", str(out)], summary=boom, now=NOW) == 1
    assert cu.main(["x", "--out", str(out)], summary=lambda d: {"total_calls": 0}, now=NOW) == 1
    assert not out.exists()
