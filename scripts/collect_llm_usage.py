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

FALLBACKS (#1208). `fallbacks` and `fallback_reasons` are SITE-WIDE over the window:
how many calls succeeded only after an upstream 429/error, and why
("groq120|429_tpm": 3). They let the analyst name which provider failed and why
instead of reporting an errors gap each night. Per-route fallbacks are NOT in the
day blob, so they are not exported; that is a separate follow-up. `null` means
UNKNOWN, never 0 (same rule as total_input_tokens). Invariant:
sum(fallback_reasons.values()) <= fallbacks. A shortfall is a gap in the record,
not a defect: days before #355 carry a count and no reasons, so fallbacks > 0 with
{} is a real state, and fallbacks 0 with {} is a legitimate quiet window (not None).

HTTP 5XX (#1506). `http_5xx_by_route` is the per-route count of responses with status
500-599 over the window, labelled "<METHOD> <route template>" (never a raw path), top 20,
from the `http_errors/` day blobs written by `astro_ai.http_errors`. Four keys, all `null`
when unknown, never 0 (same rule as FALLBACKS): `http_5xx_total`, `http_5xx_by_route`,
`http_5xx_window` (stated UTC from/to, inclusive), `http_5xx_days_recorded`. A day with no
blob is no evidence, not a zero, so read `http_5xx_days_recorded` BESIDE the total: a total
of 0 with 5 of 7 days recorded means "none seen on those 5 days". `days_recorded == 0` makes
total and by_route null; `days_recorded >= 1` with no errors is a real 0 and `[]`. The read
is its own failure domain: if it fails the four keys are null and the LLM snapshot still lands.

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
# fallback_reasons keys are "<provider>|<reason>"; bounded so a pathological blob
# cannot bloat a file the commit job copies into measurements/.
_REASON_KEY_MAX = 80
_REASON_MAX_ENTRIES = 20
_HTTP_5XX_MAX_ROUTES = 20     # top-N 5xx routes kept (#1506); labels reuse _REASON_KEY_MAX


def _measured_by_feature(usage: dict) -> dict[str, dict[str, int]]:
    """Provider-reported sums (`measured_by_route`) folded onto the feature each
    serves, the way /admin/ops does (ops_data._token_rows). `by_route[*].input_tokens`
    is 0 on every day recorded since #473 -- input is not knowable at the cache
    layer -- so reading it alone reported a flawless zero input spend (#868)."""
    from astro_ai.ops_data import PROVIDER_ROUTE_FEATURE  # noqa: PLC0415 -- needs src/ on the path
    out: dict[str, dict[str, int]] = {}
    for m in usage.get("measured_by_route") or []:
        key = PROVIDER_ROUTE_FEATURE.get(m.get("route") or "", m.get("route") or "")
        acc = out.setdefault(key, {"measured": 0, "input_tokens": 0, "output_tokens": 0})
        for k in acc:
            acc[k] += int(m.get(k) or 0)
    return out


def _is_count(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _fallbacks(usage: dict) -> tuple[int | None, dict[str, int] | None]:
    """(fallbacks, fallback_reasons) from `usage["aggregate"]`, or (None, None).

    They live under range_summary()["aggregate"], NOT at the top of usage_summary():
    reading usage.get("fallbacks") would export a permanent, silent 0 (#1208).
    Absent or malformed is unknown (None), never 0."""
    agg = usage.get("aggregate")
    if not isinstance(agg, dict) or not _is_count(agg.get("fallbacks")):
        return None, None
    reasons: dict[str, int] = {}
    raw = agg.get("fallback_reasons")
    for k, n in (raw.items() if isinstance(raw, dict) else ()):
        if not isinstance(n, (int, float)) or isinstance(n, bool):
            continue
        key = str(k)[:_REASON_KEY_MAX]
        reasons[key] = reasons.get(key, 0) + max(int(n), 0)
    top = sorted(reasons.items(), key=lambda kv: -kv[1])[:_REASON_MAX_ENTRIES]
    return max(agg["fallbacks"], 0), dict(top)


def _http_5xx(usage: dict) -> dict:
    """The four `http_5xx_*` keys from `usage["http_errors"]` (http_errors.range_summary), all
    None when it is absent or malformed. See HTTP 5XX in the module docstring."""
    unknown = {"http_5xx_total": None, "http_5xx_by_route": None,
               "http_5xx_window": None, "http_5xx_days_recorded": None}
    he = usage.get("http_errors")
    if not isinstance(he, dict):
        return unknown
    recorded, days = he.get("days_recorded"), he.get("days")
    if (not _is_count(recorded) or recorded < 0 or not _is_count(days) or days < 1
            or not isinstance(he.get("from"), str) or not isinstance(he.get("to"), str)):
        return unknown
    window = {"from": he["from"], "to": he["to"], "days": days}
    if recorded == 0:                         # the recorder wrote nothing: unknown, not zero
        return {**unknown, "http_5xx_window": window, "http_5xx_days_recorded": 0}
    rows = []
    raw = he.get("by_route")
    for label, v in (raw.items() if isinstance(raw, dict) else ()):
        if not isinstance(v, dict) or not _is_count(v.get("total")) or v["total"] < 0:
            continue
        by_status = {str(s): n for s, n in (v.get("by_status") or {}).items()
                     if _is_count(n) and n >= 0} if isinstance(v.get("by_status"), dict) else {}
        rows.append({"route": str(label)[:_REASON_KEY_MAX], "count": v["total"],
                     "by_status": by_status})
    rows.sort(key=lambda r: (-r["count"], r["route"]))
    total = he.get("total")
    return {"http_5xx_total": max(total, 0) if _is_count(total) else sum(r["count"] for r in rows),
            "http_5xx_by_route": rows[:_HTTP_5XX_MAX_ROUTES],
            "http_5xx_window": window, "http_5xx_days_recorded": recorded}


def slim(usage: dict, now: datetime) -> dict:
    """Only what a budget reader needs.

    Input tokens are MEASURED (provider-reported) or UNKNOWN (None), never a
    silent 0: a zero would read as "spent nothing" to a ceiling detector. Per
    provider CALL, not per miss -- one rashifal miss is twelve provider calls."""
    measured = _measured_by_feature(usage)
    routes = []
    for r in usage.get("by_route") or []:
        calls, hits = int(r.get("calls") or 0), int(r.get("hits") or 0)
        m = measured.get(r.get("route") or "") or {}
        n = int(m.get("measured") or 0)
        row = {"route": r.get("route"), "calls": calls, "hits": hits,
               "hit_rate_pct": int(r.get("hit_rate_pct") or 0),
               "input_tokens": int(m["input_tokens"]) if n else None,
               "output_tokens": int(m["output_tokens"]) if n else None,
               "measured_calls": n,
               "tokens_per_call": int(m["input_tokens"] / n) if n else None}
        routes.append(row)
    any_measured = any(r["measured_calls"] for r in routes)
    peak_meas = usage.get("peak_day_measured_tokens")
    fallbacks, fallback_reasons = _fallbacks(usage)
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": int(usage.get("days") or DAYS),
        "total_calls": int(usage.get("total_calls") or 0),
        "cache_hits": int(usage.get("cache_hits") or 0),
        "cache_misses": int(usage.get("cache_misses") or 0),
        "hit_rate_pct": int(usage.get("hit_rate_pct") or 0),
        "total_input_tokens": sum(r["input_tokens"] or 0 for r in routes) if any_measured else None,
        "total_output_tokens": int(usage.get("total_output_tokens") or 0),
        # The cache layer's OUTPUT-only peak (its input side is 0 by design);
        # kept for the files already on disk. The detector prefers the measured one.
        "peak_day_tokens": usage.get("peak_day_tokens"),
        "peak_day": usage.get("peak_day"),
        "peak_day_measured_tokens": peak_meas,
        "peak_day_measured": usage.get("peak_day_measured") if peak_meas else None,
        "fallbacks": fallbacks,
        "fallback_reasons": fallback_reasons,
        **_http_5xx(usage),
        "by_route": sorted(routes, key=lambda r: -r["calls"]),
    }


def _summary(days: int) -> dict:
    from astro_ai import llm_stats  # noqa: PLC0415 -- needs src/ on the path
    usage = llm_stats.usage_summary(days)
    # usage_summary() has no fallbacks; range_summary()'s aggregate does (#1208).
    # Raising here fails the whole collect, as a usage_summary failure does.
    usage["aggregate"] = llm_stats.range_summary(days)["aggregate"]
    usage["http_errors"] = _http_errors(days)
    return usage


def _http_errors(days: int) -> dict | None:
    """http_errors.range_summary(days), or None when it cannot be read (#1506). Unlike the
    fallbacks line above this must NOT raise: an unreadable 5xx record yields unknown (None)
    and the LLM snapshot still lands."""
    try:
        from astro_ai import http_errors  # noqa: PLC0415 -- needs src/ on the path
        return http_errors.range_summary(days)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::HTTP 5xx record not read ({exc.__class__.__name__}: {str(exc)[:160]}); "
              f"http_5xx_* are null")
        return None


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
    peak = doc["peak_day_measured_tokens"] or doc["peak_day_tokens"]
    print(f"llm usage: {doc['total_calls']} calls, hit rate {doc['hit_rate_pct']}%, "
          f"input tokens {doc['total_input_tokens'] if doc['total_input_tokens'] is not None else 'unknown'}, "
          f"peak day {peak} tokens ({doc['peak_day_measured'] or doc['peak_day']}), "
          f"fallbacks {doc['fallbacks'] if doc['fallbacks'] is not None else 'unknown'}, "
          f"5xx {doc['http_5xx_total'] if doc['http_5xx_total'] is not None else 'unknown'} "
          f"({doc['http_5xx_days_recorded'] if doc['http_5xx_days_recorded'] is not None else '?'}"
          f"/{doc['days']} days)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
