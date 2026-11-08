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
         "by_route": [{"route": "ask", "calls": 100, "hits": 20, "hit_rate_pct": 20, "input_tokens": 152_000},
                      {"route": "natal", "calls": 300, "hits": 280, "hit_rate_pct": 93, "input_tokens": 38_000}]}


def test_tokens_per_miss_divides_by_misses_not_calls():
    """A hit spends no input tokens; per-call would understate every prompt as
    the cache warms (ops_data's own note)."""
    doc = cu.slim(USAGE, NOW)
    ask = next(r for r in doc["by_route"] if r["route"] == "ask")
    assert ask["tokens_per_miss"] == 152_000 // 80


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
