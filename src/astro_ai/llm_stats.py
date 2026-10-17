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
      "fallbacks": 2,  # number of calls that succeeded after an upstream 429/error
      "fallback_reasons": {          # #355 — WHY each fallback happened
        "groq120|429_tpm": 1,        # "<provider that failed>|<reason class>"
        "groq20|quality":  1,
      },
      "prefix_cache": {              # #396 — Groq's PROVIDER-side prefix cache
        "groq120|openai/gpt-oss-120b|rashifal_single": {
          "calls": 7,                  # every provider call on this provider|model|route
          "measurable": 7,             # ...of those, calls where a SILENCE is informative
          "reported": 1,               # ...of those, calls that returned a cache figure
          "prompt_measurable": 16541,  # prompt tokens over measurable calls
          "prompt_reported": 2363,     # prompt tokens over reported calls only
          "cached_tokens": 2304}
      },
      "calls": {"total": .., "hits": .., "misses": .., "miss_latency_sum_ms": ..},
      "call_by_route": {
        "rashifal": {"calls": .., "hits": .., "input_tokens": .., "output_tokens": ..,
                     "miss_latency_sum_ms": 41200, "miss_latency_n": 3}   # #355
      }
    }

Two invariants worth knowing before reading a number off this file:

  * prefix_cache is NOT the response cache (`calls.hits`). That one is this
    app's own cache and dies with the Cloud Run instance; this one is Groq's and
    does not. `calls` counts every served call; `reported` moves only when the
    provider actually returned a figure; `measurable` sits between them -- a
    call on a CACHE_REPORTING_MODELS model with a prompt at or over
    MIN_CACHEABLE_PREFIX, where Groq's silence means "missed", not "cannot say".
    A miss therefore adds to `prompt_measurable` with zero cached tokens, which
    is what makes effective_pct honest; a call on a non-reporting model adds to
    `calls` and nothing else. Absent is still not zero -- but a measured miss IS
    zero, and conflating the two is what overstated the benefit ~7x.

  * sum(fallback_reasons.values()) == fallbacks for any day recorded after #355,
    because both are incremented in the same mutator. A day recorded BEFORE it
    has `fallbacks` and no `fallback_reasons` at all, so over a mixed window the
    reasons add up to LESS than the fallbacks. That is a gap in the record, not
    a bug, and the page says so.
  * Per-route latency is two keys, not one. `miss_latency_n` counts only the
    misses whose latency was recorded. Day-files written before #355 have
    misses and no latency; dividing by `calls - hits` would drag a route's
    average toward zero across the whole 30-day window, and a zero reads as
    "fast". Divide by `miss_latency_n`, and report None when it is 0.
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

# --- #396: what makes a missing cache figure INFORMATIVE ---------------------
#
# Groq returns no `prompt_tokens_details` object at all on a cache miss, so an
# absent figure is ambiguous: it could mean "this model never reports" or
# "this model reports and this call simply missed". Measured live on
# openai/gpt-oss-120b, 2026-10-17: 1 hit (cached 2304 of 2363 prompt tokens)
# and 6 misses across 7 identical-prefix calls, every miss arriving as
# `prompt_tokens_details: null`. Both states look the same on the wire.
#
# The model resolves it. Groq documents prefix caching for exactly these three
# models, with a minimum cacheable prefix "ranging from 128 to 1024 tokens"
# depending on the model (console.groq.com/docs/prompt-caching, read 2026-10-17).
# Both spellings are listed because the chain configures the `openai/` prefix
# while the docs name the bare model.
#
# This is an EXACT match, and that is a sharp edge worth knowing: `ProviderConfig
# .model()` returns `os.environ.get(f"{NAME}_MODEL", default)`, so pointing
# GROQ120_MODEL at a pinned or versioned id -- `openai/gpt-oss-120b-0924` -- makes
# the route unrecognised and every row for it reads "--" with nothing saying why.
# Exact matching is still preferred over a prefix test, which would quietly
# classify some future non-caching `gpt-oss-*` variant as reporting; the fix for a
# pinned id is to add it here.
CACHE_REPORTING_MODELS = frozenset({
    "openai/gpt-oss-120b", "openai/gpt-oss-20b", "openai/gpt-oss-safeguard-20b",
    "gpt-oss-120b", "gpt-oss-20b", "gpt-oss-safeguard-20b",
})

# 128 is the BOTTOM of Groq's documented 128-1024 range, and the choice matters.
#
# An earlier version used 1024, the top, reasoning that below it a miss cannot be
# told from a prompt that was never eligible. That was wrong in a way worth
# recording, because it reintroduced the exact bias this module exists to remove:
# `measurable` is also true whenever a call REPORTED (it has to be, or a reported
# call's cached tokens would count in the numerator while its prompt tokens were
# missing from the denominator). So with the floor at 1024, a HIT at 714 tokens
# was measurable and a MISS at 714 on the identical request was not -- the
# denominator selected for hits, which is selection bias at the length level
# after we had just removed it at the model level. Measured: 1 hit + 6 misses at
# 714 tok read 97.5% instead of the true 13.9%.
#
# At 128 the asymmetry is unreachable rather than merely smaller: Groq cannot
# cache a prefix shorter than 128 tokens on any model, so a hit below the floor
# cannot occur and the "reported" disjunct never has to rescue one.
#
# The cost is the opposite error, and it is the safe one: if a particular model's
# real floor is higher than 128, its misses between 128 and that floor are scored
# as zeros when they were never eligible, which UNDERSTATES the saving. For a
# quota metric, under-promising is the correct direction to be wrong in.
#
# In practice the band is nearly empty anyway. The threshold is compared against
# the provider's `prompt_tokens`, which is system + user, not the system prompt
# alone -- the smallest system prompt in the repo is 572 tokens and every route
# adds a chart or question payload on top.
MIN_CACHEABLE_PREFIX = 128


def _rate(cached: int, prompt: int, n: int) -> float | None:
    """cached/prompt as a percentage, or None when nothing measurable happened.

    None, never 0: a route served only by a non-reporting model was not observed,
    and a zero there would read as "no caching". Clamped to 0-100 because the
    figures come from the provider and nothing upstream guarantees they are sane
    -- a misreporting provider should not put 250% on the dashboard.
    """
    if not n or prompt <= 0:
        return None
    return round(max(0.0, min(100.0, cached / prompt * 100)), 1)

# One definition of the counter row, shared by record() and range_summary(). They
# drifting apart is how a field gets summed in one place and ignored in the other.
_PREFIX_ZERO = {"calls": 0, "measurable": 0, "reported": 0,
                "prompt_measurable": 0, "prompt_reported": 0, "cached_tokens": 0}


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


def record(*, provider: str, model: str, route: str = "", fallback: bool = False,
           fallback_reason: str = "", failed_provider: str = "",
           prompt_tokens: int | None = None,
           cached_tokens: int | None = None) -> None:
    """Increment counters for today's LLM call. Best-effort; never raises.

    Called from providers.chat() after a successful response. `route` labels
    the calling feature ("natal", "ask", "matching", ...). `fallback=True`
    indicates this provider only succeeded after an upstream one failed.

    `fallback_reason` / `failed_provider` say why (#355). They are counted in
    the SAME mutator as `fallbacks`, so sum(fallback_reasons.values()) ==
    fallbacks for every day recorded after this change. A caller passing
    `fallback=True` with no reason lands under "unknown|unknown" rather than
    being dropped, to keep that invariant.

    `prompt_tokens` / `cached_tokens` (#396) are what the provider reported for
    its own prefix cache, or None when it reported nothing. They are counted in
    the same mutator -- no extra storage write -- and only when BOTH are given.
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
            reasons = data.setdefault("fallback_reasons", {})
            rkey = f"{failed_provider or 'unknown'}|{fallback_reason or 'unknown'}"
            reasons[rkey] = reasons.get(rkey, 0) + 1
        pc = data.setdefault("prefix_cache", {}).setdefault(stat_key, dict(_PREFIX_ZERO))
        pc["calls"] = pc.get("calls", 0) + 1
        if prompt_tokens is not None:
            # A call that REPORTED is measurable by definition, whatever its size:
            # the model's own minimum may be 128, and excluding a reported call
            # from the denominator while counting its cached tokens in the
            # numerator would let the effective rate exceed 100%.
            measurable = cached_tokens is not None or (
                model in CACHE_REPORTING_MODELS and prompt_tokens >= MIN_CACHEABLE_PREFIX)
            if measurable:
                pc["measurable"] = pc.get("measurable", 0) + 1
                pc["prompt_measurable"] = pc.get("prompt_measurable", 0) + prompt_tokens
            if cached_tokens is not None:
                pc["reported"] = pc.get("reported", 0) + 1
                pc["prompt_reported"] = pc.get("prompt_reported", 0) + prompt_tokens
                pc["cached_tokens"] = pc.get("cached_tokens", 0) + cached_tokens
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


def record_call(*, route: str, cache_hit: bool, latency_ms: int = 0,
                input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Bump per-day hit/miss/latency counters. Called from cache.log_call().

    Persisted alongside the per-model counters (same GCS file, extra keys)
    so a single admin-panel read gets everything. Adds a small write cost
    per LLM call but survives Cloud Run cold starts / deploys, unlike the
    SQLite-backed usage_log which lives in /tmp.
    """
    today = date.today()

    def _mut(current: dict | None) -> dict:
        data = current or {
            "date": today.isoformat(),
            "counts": {}, "totals": {}, "fallbacks": 0,
            "calls": {"total": 0, "hits": 0, "misses": 0,
                       "input_tokens": 0, "output_tokens": 0,
                       "miss_latency_sum_ms": 0},
            "call_by_route": {},
        }
        data.setdefault("calls", {"total": 0, "hits": 0, "misses": 0,
                                    "input_tokens": 0, "output_tokens": 0,
                                    "miss_latency_sum_ms": 0})
        data.setdefault("call_by_route", {})

        c = data["calls"]
        c["total"] = c.get("total", 0) + 1
        if cache_hit:
            c["hits"] = c.get("hits", 0) + 1
        else:
            c["misses"] = c.get("misses", 0) + 1
            c["miss_latency_sum_ms"] = c.get("miss_latency_sum_ms", 0) + latency_ms
            c["input_tokens"] = c.get("input_tokens", 0) + input_tokens
            c["output_tokens"] = c.get("output_tokens", 0) + output_tokens

        rk = route or "unknown"
        r = data["call_by_route"].setdefault(rk, {"calls": 0, "hits": 0,
                                                     "input_tokens": 0, "output_tokens": 0})
        r["calls"] = r.get("calls", 0) + 1
        if cache_hit:
            r["hits"] = r.get("hits", 0) + 1
        else:
            r["input_tokens"] = r.get("input_tokens", 0) + input_tokens
            r["output_tokens"] = r.get("output_tokens", 0) + output_tokens
            # Per-route latency (#355). Two keys, because `n` is not derivable
            # from `calls - hits` on a route that has pre-#355 misses.
            r["miss_latency_sum_ms"] = r.get("miss_latency_sum_ms", 0) + latency_ms
            r["miss_latency_n"] = r.get("miss_latency_n", 0) + 1
        return data

    result = storage.update_json(_key_for(today), _mut, default=None)
    if result is not None:
        return
    # Local fallback (dev / preview).
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
        log.debug("llm_stats.record_call local fallback failed: %s", err)


def usage_summary(days: int = 1) -> dict[str, Any]:
    """Return the same shape cache.usage_summary used to, from GCS.

    Aggregates the last `days` days of per-day blobs. Survives Cloud Run
    cold starts and deploys, so the /admin/usage top panel no longer
    resets to zero after each push.
    """
    days = max(1, min(days, STATS_RETENTION_DAYS))
    today = date.today()
    total = 0
    hits = 0
    miss_latency_sum = 0
    misses = 0
    in_tok = 0
    out_tok = 0
    peak_tok = 0
    peak_date: str | None = None
    by_route_acc: dict[str, dict[str, int]] = {}
    for i in range(days):
        d = today - timedelta(days=i)
        blob = _read_day(d)
        if blob is None:
            continue
        c = blob.get("calls", {})
        total += c.get("total", 0)
        hits += c.get("hits", 0)
        misses += c.get("misses", 0)
        miss_latency_sum += c.get("miss_latency_sum_ms", 0)
        in_tok += c.get("input_tokens", 0)
        out_tok += c.get("output_tokens", 0)
        # THE PEAK DAY, not the average. The daily limit is a CEILING, and an
        # average cannot tell you how close a ceiling came -- 30 quiet days
        # around one 198,888-token day (2026-10-08) average to nothing while
        # the day itself exhausted the quota and took every rashifal page down.
        # So: the worst day in the window, and which day it was, because "when"
        # is what makes it diagnosable.
        day_tok = c.get("input_tokens", 0) + c.get("output_tokens", 0)
        if day_tok > peak_tok:
            peak_tok, peak_date = day_tok, d.isoformat()
        for route, r in blob.get("call_by_route", {}).items():
            acc = by_route_acc.setdefault(route, {"calls": 0, "hits": 0,
                                                    "input_tokens": 0, "output_tokens": 0,
                                                    "lat_sum": 0, "lat_n": 0})
            acc["lat_sum"] += r.get("miss_latency_sum_ms", 0)
            acc["lat_n"] += r.get("miss_latency_n", 0)
            acc["calls"] += r.get("calls", 0)
            acc["hits"] += r.get("hits", 0)
            acc["input_tokens"] += r.get("input_tokens", 0)
            acc["output_tokens"] += r.get("output_tokens", 0)
    by_route = sorted(
        [
            {"route": k, "calls": v["calls"], "hits": v["hits"],
             "hit_rate_pct": int(v["hits"] / v["calls"] * 100) if v["calls"] else 0,
             "input_tokens": v["input_tokens"], "output_tokens": v["output_tokens"],
             # None, never 0: a route with no recorded latency is UNKNOWN, and
             # a zero would read as "fast". Covers only days recorded since #355.
             "avg_miss_latency_ms": int(v["lat_sum"] / v["lat_n"]) if v["lat_n"] else None,
             "miss_latency_n": v["lat_n"]}
            for k, v in by_route_acc.items()
        ],
        key=lambda r: -r["calls"],
    )
    return {
        "days": days,
        "total_calls": total,
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate_pct": int(hits / total * 100) if total else 0,
        "total_input_tokens": in_tok,
        "total_output_tokens": out_tok,
        # None, not 0, when nothing was recorded: a zero peak would read as
        # "a quiet day", which is the opposite of "we have no idea".
        "peak_day_tokens": peak_tok or None,
        "peak_day": peak_date,
        "avg_miss_latency_ms": int(miss_latency_sum / misses) if misses else 0,
        "by_route": by_route,
        "cache_entries": 0,   # SQLite-only concept; filled by admin_usage from cache.py
    }


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
            "fallback_reasons": {"groq120|429_tpm": 2, ...},   # sorted desc; #355
            "prefix_cache": {"rashifal_single": {"calls", "measurable", "reported",
                             "prompt_measurable", "prompt_reported", "cached_tokens",
                             "hit_pct", "effective_pct"}, ...},   # #396
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
    fallback_reasons: dict[str, int] = defaultdict(int)
    prefix_acc: dict[str, dict[str, int]] = {}
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
        for rkey, n in (blob.get("fallback_reasons") or {}).items():
            fallback_reasons[rkey] += n
        # Days recorded before #396 have no key and contribute nothing -- they
        # must not count as calls with a missing figure, or they would dilute.
        for compound_key, pc in (blob.get("prefix_cache") or {}).items():
            parts = compound_key.split("|")
            if len(parts) != 3:
                continue
            # A row written by an OLDER schema must be skipped whole, not summed
            # field-by-field. The first #396 shape stored `prompt_tokens`; this
            # one stores `prompt_measurable` / `prompt_reported`. Summing by the
            # CURRENT field list silently takes such a row's `cached_tokens` into
            # the numerator while contributing nothing to either denominator, and
            # a mixed window then publishes a rate over 100% (measured: 571% and
            # 3998%). Requiring every field makes a schema change show up as a
            # missing row rather than an inflated percentage.
            if not _PREFIX_ZERO.keys() <= pc.keys():
                continue
            acc = prefix_acc.setdefault(parts[2], dict(_PREFIX_ZERO))
            for field in acc:
                acc[field] += pc.get(field, 0)
    daily.reverse()  # oldest first for display
    return {
        "days": daily,
        "aggregate": {
            "by_model": dict(sorted(by_model.items(), key=lambda kv: -kv[1])),
            "by_route": dict(sorted(by_route.items(), key=lambda kv: -kv[1])),
            "by_provider": dict(sorted(by_provider.items(), key=lambda kv: -kv[1])),
            "total_calls": total,
            "fallbacks": fallbacks,
            "fallback_reasons": dict(sorted(fallback_reasons.items(), key=lambda kv: -kv[1])),
            # TWO rates, because they answer two different questions and the
            # difference is large. Measured live 2026-10-17: 1 hit in 7 identical
            # calls on gpt-oss-120b, cached 2304 of 2363 prompt tokens. hit_pct
            # reads 97.5% -- true, and it is how hard a hit lands. effective_pct
            # reads 13.9% -- also true, and it is the only one that describes the
            # quota actually saved. Publishing hit_pct alone overstates the
            # benefit by ~7x, because its denominator excludes every miss.
            #
            # Both are None rather than 0 when nothing measurable happened: a
            # route served only by a non-reporting model, or only by prompts under
            # MIN_CACHEABLE_PREFIX, was never observed and must not read as 0%.
            "prefix_cache": {
                route: {**v,
                        "hit_pct": _rate(v["cached_tokens"], v["prompt_reported"], v["reported"]),
                        "effective_pct": _rate(v["cached_tokens"], v["prompt_measurable"],
                                               v["measurable"])}
                for route, v in sorted(prefix_acc.items(), key=lambda kv: -kv[1]["calls"])
            },
        },
    }
