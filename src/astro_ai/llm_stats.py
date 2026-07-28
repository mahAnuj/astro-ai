"""Per-day counter of LLM calls, keyed by (provider, model, route).

Persisted to GCS as `llm_stats/YYYY-MM-DD.json` — one file per day. Files
older than STATS_RETENTION_DAYS are considered stale and skipped on read
(GCS bucket lifecycle rule can auto-delete them). Falls back silently to
local /tmp when GCS isn't configured, so dev doesn't need a bucket.

Read path: /admin/usage aggregates today's + last 7 days for the dashboard.

Design: uses storage.update_json's CAS retry loop so concurrent LLM calls
never lose count. Adds ~100-300ms per record() call under normal traffic.
For MVP scale this is negligible against the 1-2s LLM latency it decorates.
Migrate to Firestore or an in-memory buffer + periodic flush when write
throughput matters more than simplicity.

Schema (per-day file):
    {
      "date": "2026-07-28",
      "counts": {
        "groq120|openai/gpt-oss-120b|natal": 15,
        "groq120|openai/gpt-oss-120b|ask":   30,
        "groq20|openai/gpt-oss-20b|natal":    3,
        ...
      },
      "totals": {
        "natal":    18,
        "ask":      30,
        ...
      },
      "fallbacks": 2   # number of calls that succeeded after an upstream 429/error
    }
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from astro_ai import storage

log = logging.getLogger(__name__)

# Number of days of stats to keep readable on the dashboard. Older files
# are just skipped on aggregation; a GCS lifecycle rule (documented in
# README) actually deletes them.
STATS_RETENTION_DAYS = 30

_LOCAL_FALLBACK_DIR = Path(os.environ.get("BHAGYA_LLM_STATS_FALLBACK_DIR", "/tmp/bhagya_llm_stats"))


def _key_for(day: date) -> str:
    return f"llm_stats/{day.isoformat()}.json"


def _local_path(day: date) -> Path:
    return _LOCAL_FALLBACK_DIR / f"{day.isoformat()}.json"


def _read_day(day: date) -> dict[str, Any] | None:
    """Read one day's stats blob from GCS or local fallback. None if absent."""
    data = storage.get_json(_key_for(day))
    if data is not None:
        return data
    path = _local_path(day)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def record(*, provider: str, model: str, route: str = "", fallback: bool = False) -> None:
    """Increment counters for today's LLM call. Best-effort; never raises.

    Called from providers.chat() after a successful response. `route` labels
    the calling feature ("natal", "ask", "matching", ...). `fallback=True`
    indicates this provider only succeeded after an upstream one failed.
    """
    today = date.today()
    stat_key = f"{provider}|{model}|{route or 'unknown'}"

    def _mut(current: dict | None) -> dict:
        data = current or {"date": today.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0}
        data.setdefault("counts", {})
        data.setdefault("totals", {})
        data["counts"][stat_key] = data["counts"].get(stat_key, 0) + 1
        route_key = route or "unknown"
        data["totals"][route_key] = data["totals"].get(route_key, 0) + 1
        if fallback:
            data["fallbacks"] = data.get("fallbacks", 0) + 1
        return data

    result = storage.update_json(_key_for(today), _mut, default=None)
    if result is not None:
        return
    # GCS unavailable → local fallback (best-effort, non-atomic).
    try:
        _LOCAL_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        path = _local_path(today)
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
        new_data = _mut(current)
        path.write_text(json.dumps(new_data, ensure_ascii=False), encoding="utf-8")
    except Exception as err:  # noqa: BLE001 — stats are best-effort
        log.debug("llm_stats.record local fallback failed: %s", err)


def _empty_day(day: date) -> dict[str, Any]:
    return {"date": day.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0}


def today_summary() -> dict[str, Any]:
    """Return today's raw stats blob (or an empty template)."""
    today = date.today()
    return _read_day(today) or _empty_day(today)


def range_summary(days: int) -> dict[str, Any]:
    """Aggregate the last `days` days into a single summary.

    Returns:
        {
          "days": [{"date": "2026-07-28", "totals": {...}, "fallbacks": N}, ...],
          "aggregate": {
            "by_model":  {"groq120:openai/gpt-oss-120b": 45, ...},
            "by_route":  {"natal": 20, "ask": 42, ...},
            "by_provider": {"groq120": 45, "groq20": 20, ...},
            "total_calls": 87,
            "fallbacks": 3,
          }
        }
    """
    days = max(1, min(days, STATS_RETENTION_DAYS))
    today = date.today()
    by_model: dict[str, int] = defaultdict(int)
    by_route: dict[str, int] = defaultdict(int)
    by_provider: dict[str, int] = defaultdict(int)
    total = 0
    fallbacks = 0
    daily: list[dict[str, Any]] = []
    for i in range(days):
        d = today - timedelta(days=i)
        blob = _read_day(d) or _empty_day(d)
        daily.append({
            "date": blob["date"],
            "totals": dict(blob.get("totals", {})),
            "fallbacks": blob.get("fallbacks", 0),
            "total": sum(blob.get("totals", {}).values()),
        })
        for compound_key, count in blob.get("counts", {}).items():
            parts = compound_key.split("|")
            if len(parts) == 3:
                prov, mod, route = parts
                by_model[f"{prov}:{mod}"] += count
                by_provider[prov] += count
                by_route[route] += count
                total += count
        fallbacks += blob.get("fallbacks", 0)
    daily.reverse()  # oldest first for display
    return {
        "days": daily,
        "aggregate": {
            "by_model": dict(sorted(by_model.items(), key=lambda kv: -kv[1])),
            "by_route": dict(sorted(by_route.items(), key=lambda kv: -kv[1])),
            "by_provider": dict(sorted(by_provider.items(), key=lambda kv: -kv[1])),
            "total_calls": total,
            "fallbacks": fallbacks,
        },
    }
