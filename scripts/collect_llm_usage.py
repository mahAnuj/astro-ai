#!/usr/bin/env python3
"""Snapshot the app's own LLM usage (cache hits, tokens per route) for the loop.

WHY THIS EXISTS
---------------
The owner, 2026-11-06: "to keep minimum token budget, we should direct the ops
monitoring agent to monitor the cache usage and see if it can increase the
caching to reduce the token usage".

The numbers already existed. `llm_stats.usage_summary()` aggregates per-day blobs
in GCS: calls, cache hits and misses, input and output tokens, the peak day, and
the same per route. `/admin/ops` renders them. But
`scripts/detect_ops_regressions.py` reads committed `measurements/*.json` only,
and its own header listed "cache hit ratio" and "daily token ceiling" under
NOT_COVERED: computed, displayed, never judged. This collector runs where GCS
credentials exist (agent-measure's analyst job) and writes the slice the
detector needs. The detector then raises `cache-low` and `token-ceiling`.

Writes /tmp/measure/llm-usage.json. The commit job copies /tmp/measure/*.json
into measurements/, the same path the GSC and GA4 files take. Needs
BHAGYA_STORAGE_BUCKET and GCS read access; on any failure it writes nothing and
exits 1, so the previous file stands and the detector reports it as stale rather
than as zero.

EXIT CODES: 0 written   1 could not read usage (nothing written)   2 bad args
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DAYS = 7


def slim(usage: dict, now: datetime) -> dict:
    """Only what a budget reader needs. Tokens-per-miss, because a cache hit spends
    no input tokens (ops_data's own note): dividing by calls would understate
    every prompt as the cache warms."""
    routes = []
    for r in usage.get("by_route") or []:
        calls, hits = int(r.get("calls") or 0), int(r.get("hits") or 0)
        misses = max(calls - hits, 0)
        routes.append({"route": r.get("route"), "calls": calls, "hits": hits,
                       "hit_rate_pct": int(r.get("hit_rate_pct") or 0),
                       "input_tokens": int(r.get("input_tokens") or 0),
                       "tokens_per_miss": int((r.get("input_tokens") or 0) / misses) if misses else 0})
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": int(usage.get("days") or DAYS),
        "total_calls": int(usage.get("total_calls") or 0),
        "cache_hits": int(usage.get("cache_hits") or 0),
        "cache_misses": int(usage.get("cache_misses") or 0),
        "hit_rate_pct": int(usage.get("hit_rate_pct") or 0),
        "total_input_tokens": int(usage.get("total_input_tokens") or 0),
        "total_output_tokens": int(usage.get("total_output_tokens") or 0),
        "peak_day_tokens": usage.get("peak_day_tokens"),
        "peak_day": usage.get("peak_day"),
        "by_route": sorted(routes, key=lambda r: -r["calls"]),
    }


def _summary(days: int) -> dict:
    from astro_ai import llm_stats  # noqa: PLC0415 -- needs src/ on the path
    return llm_stats.usage_summary(days)


def main(argv: list[str], summary: Callable[[int], dict] = _summary,
         now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=DAYS)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    try:
        usage = summary(a.days) or {}
    except Exception as exc:  # GCS auth, network, a missing bucket: say so, write nothing
        print(f"::warning::LLM usage not read ({exc.__class__.__name__}: {str(exc)[:160]}); "
              f"the previous llm-usage.json stands")
        return 1
    if not usage.get("total_calls"):
        print("::warning::LLM usage read as zero calls -- not written (zero is a reading "
              "error here, not a quiet week)")
        return 1
    doc = slim(usage, now or datetime.now(timezone.utc))
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"llm usage: {doc['total_calls']} calls, hit rate {doc['hit_rate_pct']}%, "
          f"peak day {doc['peak_day_tokens']} tokens ({doc['peak_day']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
