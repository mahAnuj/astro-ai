"""Does Groq charge cached tokens against the TPM limit? A measure-only probe (#475 Phase 1b).

THE QUESTION. `providers._pace_done` settles every reservation at
`prompt_tokens + completion_tokens`, i.e. it charges cached prompt tokens at
FULL weight. Groq's `cached_tokens` is a subset of `prompt_tokens`, and whether
Groq bills that subset against the 8,000 TPM limit is unknown. If it does not,
the bucket over-charges every warm call. The only authoritative answer is
Groq's own accounting, and the only place it is exposed is the
`x-ratelimit-remaining-tokens` response header.

WHAT THIS MODULE DOES, AND DELIBERATELY DOES NOT. It makes no call and changes
no reservation. `providers.chat()` hands it the headers of calls that traffic
was already making; it decides whether that call's header is a CLEAN sample and,
if so, how far Groq's figure sits from the one this app's own accounting
predicts. `settle()` is not touched: over-reserving is the safe side, and a
bucket corrected on a guess is worse than one calibrated late.

WHY A SAMPLE IS OFTEN NOT A SAMPLE. The header is a snapshot of REMAINING
tokens at response time, and every caller of the key shares that bucket (the
rashifal job runs two calls at once; other instances and other tools use the
key too). A snapshot is one call's charge only if nothing else touched that
model's bucket between the previous response and this one. Per `provider|model`
this module numbers every call start and finish; a sample is clean iff

  * the previous call's response left an ANCHOR (a clean snapshot of its own),
  * nothing started or finished between that response and this call's start, and
  * nothing started while this call ran.

Everything else is counted as a visible skip, not dropped silently and not
folded into a match.

THE CONTROL ARM. The same formula runs on isolated COLD calls (cached_tokens 0
or absent), which are excluded from the verdict count and kept as the noise
floor. Without them, "warm calls agree with the full-weight prediction" cannot
be told from "my refill model is wrong": a formula that is off by a constant
looks like agreement whenever the cached count is small.

CONFOUNDS STATED, NOT ELIMINATED. Another caller of the key only ever makes
Groq's figure LOWER than predicted (e positive), so it pushes toward a false
FULL WEIGHT and never toward a false DISCOUNTED: a FULL verdict is only as good
as a quiet cold control. The refill model (a bucket refilling at limit/60 per
second) is inferred from one 429 body. Cached tokens may be refunded "after
processing", which could land in the NEXT call's snapshot. An SDK retry after a
timeout could charge twice. The thresholds below are judgment, not measurement,
and live in one place so a reviewer can challenge them.

Stdlib only, never raises: it runs on the path of every Groq call.
"""
from __future__ import annotations

import threading
import time

# --- the verdict rule: judgment, named once so QA can challenge it ----------
MIN_WARM = 20                # isolated warm samples a model needs before any verdict
MIN_COLD = 5                 # isolated cold samples (the control arm) it needs
COLD_NOISE_FRACTION = 0.25   # cold mean |e| above this share of the mean cached count = NOISY
FULL_MAX_F = 0.25            # discounted fraction at or below this reads as FULL WEIGHT ...
DISCOUNT_MIN_F = 0.75        # ... at or above this as DISCOUNTED; between is PARTIAL
VOTE_MAX = 0.25              # FULL WEIGHT needs at most this share of samples voting "discounted"
VOTE_MIN = 0.75              # DISCOUNTED needs at least this share

VERDICTS = ("INSUFFICIENT", "NOISY", "FULL WEIGHT", "DISCOUNTED", "PARTIAL")

#: Counters summed across calls and days. `last_limit` is stored beside them but
#: is a latest value, not a sum. One definition shared by the writer
#: (llm_stats.record) and the reader (llm_stats.usage_summary).
SUM_FIELDS = ("warm_seen", "warm_n", "warm_rem", "warm_exp", "warm_cached", "warm_disc",
              "cold_seen", "cold_n", "cold_rem", "cold_exp", "cold_abs",
              "skip_noanchor", "skip_overlap", "skip_nohdr", "skip_clamp")
FIELDS = SUM_FIELDS + ("last_limit",)


def _clock() -> float:
    """Injectable so tests run on a fake clock."""
    return time.monotonic()


_lock = threading.Lock()
_seq: dict[str, int] = {}
# key -> (remaining, limit, t_recv, seq_at_finish)
_anchor: dict[str, tuple[int, int, float, int]] = {}


def reset() -> None:
    """Forget every key. Tests only."""
    with _lock:
        _seq.clear()
        _anchor.clear()


def _as_count(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v >= 0 else None
    if isinstance(v, str):
        s = v.strip()
        return int(s) if s.isascii() and s.isdigit() else None
    return None


def parse_headers(headers) -> tuple[int, int] | None:
    """(limit_tokens, remaining_tokens) from response headers, or None.

    Both must be non-negative integers with remaining <= limit and limit > 0;
    names are matched case-insensitively. Anything else is "no usable header",
    never an exception -- a header is the provider's to get wrong.
    """
    try:
        found: dict[str, object] = {}
        for k, v in headers.items():
            found[str(k).lower()] = v
        limit = _as_count(found.get("x-ratelimit-limit-tokens"))
        remaining = _as_count(found.get("x-ratelimit-remaining-tokens"))
    except Exception:  # noqa: BLE001 — observability never breaks a reading
        return None
    if limit is None or remaining is None or limit <= 0 or remaining > limit:
        return None
    return limit, remaining


def begin(key: str) -> tuple | None:
    """Number the start of a call on `key`. Returns a ticket for finish()/abort()."""
    try:
        with _lock:
            s = _seq.get(key, 0) + 1
            _seq[key] = s
            anchor = _anchor.get(key)
            adjacent = anchor if anchor is not None and anchor[3] + 1 == s else None
            return key, s, _clock(), adjacent
    except Exception:  # noqa: BLE001
        return None


def abort(ticket) -> None:
    """A failed attempt. It may still have been charged upstream (a timeout, a
    5xx), so it must leave a hole in the sequence and no anchor behind: the next
    call re-anchors. begin() already numbered the attempt, which alone makes the
    next call non-adjacent; this keeps that true if the attempt never reaches a
    finish() and drops the stale anchor."""
    if ticket is None:
        return
    try:
        with _lock:
            _seq[ticket[0]] = _seq.get(ticket[0], 0) + 1
            _anchor.pop(ticket[0], None)
    except Exception:  # noqa: BLE001
        pass


def finish(ticket, rl, prefix, completion) -> dict | None:
    """Close a call and return the counter increments to book, or None.

    `rl` is parse_headers()' result or None; `prefix` is providers._last_prefix
    (prompt, cached-or-None, rejected); `completion` is completion_tokens or
    None. None is returned when the call cannot be classified warm or cold (no
    usage, or an impossible cached figure) -- it then claims nothing at all.
    Every other call comes back as an increment dict, so
    warm_seen + cold_seen == samples + skips for whatever has been booked.
    """
    if ticket is None:
        return None
    key, s_begin, t_start, adjacent = ticket
    try:
        t_recv = _clock()
        with _lock:
            s_end = _seq.get(key, 0) + 1
            _seq[key] = s_end
            clean = s_end == s_begin + 1
            # Only a clean call with a header leaves an anchor. An overlapped one
            # may have been answered before or after a neighbour's charge, so its
            # snapshot cannot be placed in the sequence.
            if clean and rl is not None:
                _anchor[key] = (rl[1], rl[0], t_recv, s_end)
            else:
                _anchor.pop(key, None)
        if (prefix is None or prefix[2] or completion is None
                or not isinstance(prefix[0], int)):
            return None
        prompt, cached = prefix[0], prefix[1]
        warm = bool(cached)                       # None (absent) and 0 are both cold
        side = "warm" if warm else "cold"
        out: dict[str, int] = {f"{side}_seen": 1}
        if rl is not None:
            out["last_limit"] = rl[0]
        if rl is None:
            out["skip_nohdr"] = 1
            return out
        if not clean:
            out["skip_overlap"] = 1
            return out
        if adjacent is None or adjacent[1] != rl[0]:
            out["skip_noanchor"] = 1
            return out
        limit, remaining = rl
        rate = limit / 60.0
        pred = prompt + completion               # exactly what settle() charges
        pre = min(limit, adjacent[0] + rate * (t_start - adjacent[2]))
        exp_full = pre + rate * (t_recv - t_start) - pred
        # A clamp at either end destroys the arithmetic the formula rests on.
        if exp_full > limit or exp_full <= 0 or remaining == 0:
            out["skip_clamp"] = 1
            return out
        exp_i = int(round(exp_full))
        e = exp_i - remaining                     # > 0: Groq charged MORE than predicted
        out[f"{side}_n"] = 1
        out[f"{side}_rem"] = remaining
        out[f"{side}_exp"] = exp_i
        if warm:
            out["warm_cached"] = cached
            out["warm_disc"] = 1 if e < -cached / 2 else 0
        else:
            out["cold_abs"] = abs(e)
        return out
    except Exception:  # noqa: BLE001 — observability never breaks a reading
        return None


def verdict(c: dict) -> dict:
    """One of five outcomes from a model's summed counters. A pure function.

    f = sum(remaining - predicted_remaining) over warm samples / sum(cached):
    0 means Groq charged cached tokens in full, 1 means it did not charge them
    at all. The vote is the share of warm samples that individually sat more
    than half their cached count above the prediction.
    """
    def n(k: str) -> int:
        v = c.get(k)
        return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0

    n_w, n_c = n("warm_n"), n("cold_n")
    out: dict = {"verdict": "INSUFFICIENT", "n_warm": n_w, "n_cold": n_c,
                 "f": None, "vote": None, "mean_cached": None, "cold_mean_abs": None}
    if n_w:
        out["mean_cached"] = n("warm_cached") / n_w
    if n_c:
        out["cold_mean_abs"] = n("cold_abs") / n_c
    if n_w and n("warm_cached"):
        out["f"] = (n("warm_rem") - n("warm_exp")) / n("warm_cached")
        out["vote"] = n("warm_disc") / n_w
    if n_w < MIN_WARM or n_c < MIN_COLD or out["f"] is None:
        return out
    if out["cold_mean_abs"] > COLD_NOISE_FRACTION * out["mean_cached"]:
        out["verdict"] = "NOISY"
    elif out["f"] <= FULL_MAX_F and out["vote"] <= VOTE_MAX:
        out["verdict"] = "FULL WEIGHT"
    elif out["f"] >= DISCOUNT_MIN_F and out["vote"] >= VOTE_MIN:
        out["verdict"] = "DISCOUNTED"
    else:
        out["verdict"] = "PARTIAL"
    return out
