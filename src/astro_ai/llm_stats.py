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
          "measurable": 7,             # ...calls where a SILENCE from this model means "missed"
          "reported": 1,               # ...calls that returned a figure (ANY model, not a subset)
          "prompt_measurable": 16541,  # prompt tokens over measurable calls  -> effective denom
          "prompt_reported": 2363,     # prompt tokens over reported calls    -> hit denom
          "cached_measurable": 2304,   # cached tokens over measurable calls  -> effective numer
          "cached_tokens": 2304,       # cached tokens over reported calls    -> hit numer
          "reported_unmeasurable": 0}  # reported on a call the rule said could not
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
    does not.

    `reported` and `measurable` are INDEPENDENT, and neither contains the other.
    `reported` counts calls where the provider returned a figure, on any model,
    because `prompt_tokens_details.cached_tokens` is an OpenAI-compatible field
    and not every configured provider is Groq. `measurable` counts calls where a
    SILENCE would have meant "missed" -- a CACHE_REPORTING_MODELS model with a
    prompt at or over MIN_CACHEABLE_PREFIX. So `reported` can exceed
    `measurable` (a non-Groq provider reporting its own cache), and `measurable`
    can exceed `reported` (Groq missing). An earlier version of this docstring
    said `measurable` "sits between" calls and reported, and that a non-Groq call
    "adds to `calls` and nothing else"; QA round 3 disproved both.

    Each rate divides sums gathered under its own rule: effective_pct is
    cached_measurable/prompt_measurable, hit_pct is cached_tokens/prompt_reported.
    A measurable miss adds to prompt_measurable with zero cached, which is what
    makes effective_pct honest. Absent is still not zero -- but a measured miss
    IS zero, and conflating the two is what overstated the benefit ~7x.

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

# Keys already warned about, so a persistent old-schema row does not log once per
# row per day per request. A 30-day window with 30 such rows logged 900 lines on a
# single /admin load (QA round 3, BUG-18). Process-local and unbounded only by the
# number of distinct stat_keys, which is bounded by provider x model x route.
_warned_rows: set[str] = set()

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

# 128 is the BOTTOM of Groq's documented 128-1024 range.
#
# Lowering the floor was NOT the fix for the outcome-dependence bug -- that one is
# fixed by the two separate numerators in record(), and the history is recorded
# there rather than here, so there is one account of it and not two that can drift
# apart. An earlier revision of this comment argued the floor itself removed the
# asymmetry by making a sub-128 hit "impossible because Groq cannot cache that
# short". That was an assumption about a vendor dressed as a property of the code:
# CACHE_REPORTING_MODELS is matched on the model STRING, with no provider or
# base_url test, and `_legacy_provider` reads ASTRO_AI_MODEL from the environment.
#
# All the floor decides now is what a SILENCE means. Below it we cannot tell a miss
# from a prompt that was never eligible, so such a call is not measurable. 128 is
# chosen because it keeps the residual error in the understating direction for
# effective_pct: a model whose real floor is above 128 has its sub-floor misses
# scored as zeros, which lowers the published saving rather than inflating it, and
# under-promising is the correct direction to be wrong in for a quota metric.
# Whether that band is ever hit is answered by `reported_unmeasurable`, not by
# this comment.
#
# The threshold is compared against the provider's `prompt_tokens`, which is
# system + user, not the system prompt alone -- the smallest system prompt any
# route actually SENDS is 732 tokens (`monthly`; the 572-token ask_numerology.txt
# is an overlay on ask.txt and is never sent by itself, so ask+numerology is
# 1,822) and every route adds a chart or question payload on top.
MIN_CACHEABLE_PREFIX = 128


def _rate(cached: int, prompt: int, n: int) -> float | None:
    """cached/prompt as a percentage, or None when nothing measurable happened.

    None, never 0: a route served only by a non-reporting model was not observed,
    and a zero there would read as "no caching".

    Clamped to 0-100 because the figures are the provider's and nothing upstream
    guarantees they are sane. But the clamp is reported separately by
    `_is_impossible`, because SMOOTHING an impossible figure into a plausible one
    is its own defect: a rate over 100% is the only evidence the accounting is
    broken, and it is exactly how the old-schema aggregation bug was caught (it
    published 571% and 3998%). Under a silent clamp that same bug would have read
    a tidy 100.0% and nobody would have looked.
    """
    if not n or prompt <= 0:
        return None
    return round(max(0.0, min(100.0, cached / prompt * 100)), 1)


def _is_impossible(v: dict) -> bool:
    """True when the stored sums cannot describe a real cache.

    Cached tokens are a SUBSET of prompt tokens (Groq: "cached_tokens: Number of
    input tokens that were served from cache"), so cached > prompt means the
    accounting is wrong -- a misreporting provider, or a bug in this module. The
    dashboard flags it instead of letting the clamp hide it.
    """
    return (v["cached_tokens"] < 0 or v["cached_measurable"] < 0
            # the two published ratios
            or v["cached_tokens"] > v["prompt_reported"]
            or v["cached_measurable"] > v["prompt_measurable"]
            # pairs record() cannot produce: cached_measurable only ever
            # increments alongside cached_tokens, and neither counter can
            # outrun the call count it is a subset of (QA round 3, BUG-15)
            or v["cached_measurable"] > v["cached_tokens"]
            or v["measurable"] > v["calls"] or v["reported"] > v["calls"])

# One definition of the counter row, shared by record() and range_summary(). They
# drifting apart is how a field gets summed in one place and ignored in the other.
_PREFIX_ZERO = {"calls": 0, "measurable": 0, "reported": 0,
                "prompt_measurable": 0, "prompt_reported": 0, "cached_tokens": 0,
                "cached_measurable": 0, "reported_unmeasurable": 0}


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
           cached_tokens: int | None = None,
           reported_impossible: bool = False,
           completion_tokens: int | None = None) -> None:
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

    `prompt_tokens` / `completion_tokens` are ALSO the measured size of this
    call, and #473 is where they started being kept as such in
    `measured_by_route`. Until then the only token figures the ops page had came
    from `cache.estimate_tokens(text) * 2` at the cache layer: input DEFINED as
    twice an estimate of the output, a fixed 2:1 ratio for every route forever.

    Two reasons this is the right layer and the cache layer is not:

      * it is the only one that sees a usage block at all, and
      * a cache-layer "call" is a DOCUMENT. `generate_rashifal` fans one out to
        twelve provider calls, so tokens attributed per cached request there
        understate the job by 12x before any estimate is involved.

    `route` here is the PROVIDER route (`rashifal_single`, `dasha`), which is
    not always the cached feature (`rashifal`, `dasha_deep_dive`). ops_data owns
    that mapping; this module stores what it was told, unaggregated.

    A SILENCE IS NOT A ZERO -- the same rule the prefix-cache block below keeps,
    for the same reason. A call whose provider reported no usage adds to
    `calls` and to nothing else, so `measured` is always the honest denominator
    and `input_tokens / measured` is a real mean rather than one diluted by
    calls nobody could size.
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
        # #473. Keyed by ROUTE alone, not provider|model|route: the question
        # it answers is "what does one <feature> request cost", and splitting it
        # per model would make every row a fraction of an answer on a chain that
        # falls back between models mid-feature.
        mb = data.setdefault("measured_by_route", {}).setdefault(
            route_key, {"calls": 0, "measured": 0, "input_tokens": 0, "output_tokens": 0})
        mb["calls"] = mb.get("calls", 0) + 1
        if prompt_tokens is not None and completion_tokens is not None:
            mb["measured"] = mb.get("measured", 0) + 1
            mb["input_tokens"] = mb.get("input_tokens", 0) + int(prompt_tokens)
            mb["output_tokens"] = mb.get("output_tokens", 0) + int(completion_tokens)

        pc = data.setdefault("prefix_cache", {}).setdefault(stat_key, dict(_PREFIX_ZERO))
        pc["calls"] = pc.get("calls", 0) + 1
        if prompt_tokens is not None:
            # MEASURABILITY READS (model, size) AND NOTHING ELSE. In particular it
            # must not read the OUTCOME, which is the bug this whole key exists to
            # remove and which survived two attempts:
            #
            #   v1  `cached is not None` alone      -> every miss dropped; 97.5%
            #                                          published where 13.9% was true
            #   v2  `cached is not None or (model, size>=1024)` -> a HIT at 714 tok was
            #                                          measurable and a MISS at 714 was
            #                                          not; the denominator selected
            #                                          for hits, same defect, narrower
            #   v3  lowering the floor to 128       -> band shrunk to [0,128), NOT
            #                                          removed. The claim that a
            #                                          sub-128 hit "cannot occur" was
            #                                          an assumption about Groq, not a
            #                                          property of this code:
            #                                          CACHE_REPORTING_MODELS matches
            #                                          the MODEL STRING only, with no
            #                                          provider or base_url check, and
            #                                          `_legacy_provider` takes both
            #                                          ASTRO_AI_API_BASE and
            #                                          ASTRO_AI_MODEL from the
            #                                          environment.
            #
            # So the disjunct is gone, replaced by TWO SEPARATE NUMERATORS. This is what lets measurability read
            # (model, size) and nothing else without either losing data or
            # letting a rate exceed 100%:
            #
            #   reported  -- the provider TOLD us. Always trustworthy, whatever
            #                the model: `prompt_tokens_details.cached_tokens` is
            #                an OpenAI-compatible field and the chain has four
            #                non-Groq providers, one of them OpenAI itself. These
            #                sums feed hit_pct.
            #   measurable -- a SILENCE from this call would have meant "missed".
            #                That is a property of (model, size) alone. These sums
            #                feed effective_pct.
            #
            # Sharing one `cached_tokens` across both is what forced the earlier
            # `cached is not None or ...` disjunct, and the disjunct is what made
            # measurability outcome-dependent: a hit at 714 tok counted and a miss
            # at 714 did not, so the denominator selected for hits. With separate
            # numerators each rate divides sums gathered under its own rule.
            #
            # Neither rate can then exceed 100%, and the reason is ENFORCED rather
            # than assumed: `providers._prefix_usage` rejects a call whose cached
            # count exceeds its own prompt tokens, so every term summed here
            # satisfies cached <= prompt and so does every sum of them. QA round 3
            # caught the earlier version of this comment claiming "by construction"
            # while nothing in the code established it -- (prompt=100, cached=5000)
            # was stored intact and the 5000% was saved only by the display clamp.
            # `_is_impossible` stays as the detector for a violation that reaches
            # the store some other way. NOT "an older blob": QA round 4 found
            # that justification circular, because an older-shaped row is
            # skipped whole by the schema gate in `range_summary` BEFORE this
            # detector ever sees it. The reachable causes are a hand-edited
            # blob, a row that `record()` upgraded in place until it carried all
            # eight keys while its sums were accumulated under the old meaning,
            # and a future bug in this module. Writing down a justification and
            # then treating the writing as the fact is the pattern CLAUDE.md
            # names; this comment was an instance of it.
            measurable = (model in CACHE_REPORTING_MODELS
                          and prompt_tokens >= MIN_CACHEABLE_PREFIX)
            if reported_impossible:
                # THE PROVIDER SPOKE AND WE THREW IT AWAY. That is not a
                # measurement, so it enters NEITHER denominator -- and the
                # reason it must not is the defect QA round 4 found here.
                #
                # `_prefix_usage` rejects `cached > prompt` by returning a
                # SILENCE, and on an eligible call a silence is booked as a
                # measured zero: `_prefix_usage(prompt=1000, cached=5000)` gave
                # `{"reported": 0, "cached_tokens": 0, "effective_pct": 0.0,
                #   "reported_unmeasurable": 0, "impossible": false}`. No warning,
                # no dash -- a misreporting provider became indistinguishable
                # from one that genuinely missed, it dragged the published saving
                # down with nothing to explain it, and the counter that exists to
                # make this rule falsifiable stayed 0 because it is gated on
                # `cached_tokens is not None`. The fix for an earlier bug did the
                # exact thing the docstring shipped beside it forbids:
                # "SMOOTHING an impossible figure into a plausible one is its own
                # defect".
                #
                # Counted in `reported_unmeasurable`, NOT a new field. A ninth
                # key in `_PREFIX_ZERO` would fail `_PREFIX_ZERO.keys() <=
                # pc.keys()` for every row already stored, so every historical
                # row would be skipped whole and the panel would empty itself --
                # trading a wrong number for no number. The counter already means
                # "the provider reported on a call this rule cannot use"; an
                # impossible report is exactly that, and the panel copy names
                # both causes.
                pc["reported_unmeasurable"] = pc.get("reported_unmeasurable", 0) + 1
            else:
                if measurable:
                    pc["measurable"] = pc.get("measurable", 0) + 1
                    pc["prompt_measurable"] = pc.get("prompt_measurable", 0) + prompt_tokens
                if cached_tokens is not None:
                    pc["reported"] = pc.get("reported", 0) + 1
                    pc["prompt_reported"] = pc.get("prompt_reported", 0) + prompt_tokens
                    pc["cached_tokens"] = pc.get("cached_tokens", 0) + cached_tokens
                    if measurable:
                        pc["cached_measurable"] = (
                            pc.get("cached_measurable", 0) + cached_tokens)
                    else:
                        # The provider reported on a call our rule says it could
                        # not. Kept as a counter rather than discarded, because it
                        # is evidence the rule is wrong -- too high a floor, or a
                        # model missing from the set -- and it makes that
                        # falsifiable by production instead of by live calls
                        # nobody may spend. An IMPOSSIBLE report lands here too,
                        # from the branch above; the panel copy names both.
                        pc["reported_unmeasurable"] = (
                            pc.get("reported_unmeasurable", 0) + 1)
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
    measured_acc: dict[str, dict[str, int]] = {}
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
        # #473: the MEASURED sums, keyed by the PROVIDER route. Accumulated
        # beside call_by_route rather than merged into it, because the two count
        # different things and merging them is how the old figures came to look
        # authoritative: call_by_route counts cached DOCUMENTS and carries the
        # `estimate_tokens(text) * 2` numbers, this one counts PROVIDER CALLS
        # and carries what the provider said. ops_data joins them and says which
        # it used.
        for route, r in (blob.get("measured_by_route") or {}).items():
            acc = measured_acc.setdefault(route, {"calls": 0, "measured": 0,
                                                  "input_tokens": 0, "output_tokens": 0})
            for k in acc:
                acc[k] += int(r.get(k) or 0)
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
        # #473. PROVIDER-route keyed and deliberately NOT folded into by_route:
        # one `rashifal` document is twelve `rashifal_single` provider calls, so
        # the two lists have different row counts and different units. Empty for
        # every day recorded before #473, which is what lets ops_data fall back
        # to the old estimate and SAY that it did rather than render a zero.
        "measured_by_route": sorted(
            [{"route": k, **v} for k, v in measured_acc.items()],
            key=lambda r: -r["input_tokens"],
        ),
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
    skipped_rows = 0          # prefix_cache rows from an older schema (#410 NEW-5)
    daily: list[dict[str, Any]] = []
    for i in range(days):
        d = today - timedelta(days=i)
        blob = _read_day(d) or _empty_day(d)
        # `route_tokens` is ADDITIVE to this entry's documented shape, not a
        # change to it. The blob already carries per-day per-route tokens in
        # `call_by_route` (#355) and this loop already reads every blob in the
        # window, so a per-feature trend costs no extra read and needs no new
        # instrumentation -- it was being written and never displayed.
        #
        # Only the two token fields are carried. The rest of `call_by_route`
        # (hits, latency sums) belongs to the aggregate table, and copying it
        # per day would put a second, differently-windowed copy of those
        # figures on the page for a reader to mistake for the first.
        route_tokens = {
            route: {"input_tokens": int(r.get("input_tokens") or 0),
                    "output_tokens": int(r.get("output_tokens") or 0)}
            for route, r in (blob.get("call_by_route") or {}).items()
            if isinstance(r, dict)
        }
        daily.append({
            "date": blob["date"],
            "totals": dict(blob.get("totals", {})),
            "fallbacks": blob.get("fallbacks", 0),
            "total": sum(blob.get("totals", {}).values()),
            "route_tokens": route_tokens,
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
                # Counted and logged for the same reason as the field-shape skip
                # below: `stat_key` is "provider|model|route", and if a segment is
                # ever added this is the branch every stored row falls into. Silent
                # here meant a whole window could vanish with nothing to show for it.
                if compound_key not in _warned_rows:
                    _warned_rows.add(compound_key)
                    log.warning("llm_stats: skipping a prefix_cache row whose key is "
                                "not provider|model|route (key=%s, %d segments) -- its "
                                "counts are excluded from the aggregate",
                                compound_key, len(parts))
                skipped_rows += 1
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
                # Say so. The comment here used to claim the skip "makes a schema
                # change show up as a missing row", which is only true when the
                # route has no current-schema days: otherwise the row is present
                # and the sole symptom is a silent gap between "By route" and this
                # table's Fresh calls. A log line is the difference between a
                # discrepancy someone can explain and one they cannot.
                if compound_key not in _warned_rows:
                    _warned_rows.add(compound_key)
                    log.warning("llm_stats: skipping a prefix_cache row with an "
                                "unrecognised shape (key=%s, fields=%s) -- its counts "
                                "are excluded from the aggregate", compound_key,
                                sorted(pc.keys()))
                skipped_rows += 1
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
                        "effective_pct": _rate(v["cached_measurable"], v["prompt_measurable"],
                                               v["measurable"]),
                        "impossible": _is_impossible(v)}
                for route, v in sorted(prefix_acc.items(), key=lambda kv: -kv[1]["calls"])
            },
            # Non-zero means some stored rows were written by an older schema and
            # excluded, so this table's Fresh calls will be short of "By route".
            "prefix_cache_skipped_rows": skipped_rows,
            # THE GAP, MEASURED, per route -- calls that `by_route` counts and
            # this table does not.
            #
            # It exists for an ordinary reason with no notice attached to it:
            # every day recorded BEFORE #396 contributes to `counts` (and so to
            # `by_route` and `total_calls`) and contributes no `prefix_cache` key
            # at all, so `skipped_rows` stays 0 and neither existing notice
            # renders. Measured on the real store: `by_route` rashifal_single 407
            # / natal 2 against Fresh calls rashifal_single 7 / natal 2 -- 400
            # calls absent from one card with nothing saying so.
            #
            # QA round 4 found the panel's response to this was a footnote
            # asserting the two lists "never match anyway" because one is keyed
            # by web route and the other by chat route. That is false -- both are
            # the third segment of `provider|model|route` -- and it instructed
            # the operator that a real 400-call discrepancy was meaningless. A
            # number is the only honest answer to "why do these disagree".
            "prefix_cache_unaccounted": {
                route: n - prefix_acc.get(route, {}).get("calls", 0)
                for route, n in by_route.items()
                if n > prefix_acc.get(route, {}).get("calls", 0)
            },
        },
    }
