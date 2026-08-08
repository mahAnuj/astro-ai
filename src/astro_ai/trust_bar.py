"""Homepage trust-bar counts, cached off the request path (issue #144).

The four numbers (`users`, `subscribers`, `kundlis`, `asks`) cost **32 GCS
reads** to compute: `users.count()` (1) + `subscribers.count()` (1) +
`events.counts_by_type(days=30)` (one blob per day, 30). The bucket is US
multi-region while Cloud Run runs in `asia-south1`, so every one of those is
an intercontinental round trip — measured median for `GET /` in production was
19.9s, warm or cold. Computing them inline on every homepage request is the
single largest cost of rendering `/`.

**Zeros are the safe default, not a data-integrity risk.** Every pill is
threshold-gated in `templates/index.html`:

    {% if trust_users and trust_users >= trust_users_min %}

with defaults of `users=500, subscribers=100, kundlis=500, asks=500`
(env-overridable via `TRUST_MIN_*`). Real counts are far below all four
thresholds today, so *not one pill currently renders*. A cold cache, a failed
refresh, or a dead storage backend therefore produces exactly the HTML the
site already serves — no pills — rather than a wrong number or a 500. That is
why `get_or_refresh(..., initial=<zeros>)` is correct here: the worst case is
the status quo.

`counts()` uses stale-while-revalidate, so it **never blocks the caller**.
The first request after process start returns zeros immediately and kicks off
a background refresh; subsequent requests inside the 10-minute TTL are served
from process memory with zero GCS calls.
"""

from __future__ import annotations

import os

from astro_ai import events, hot_cache, subscribers, users

CACHE_KEY = "trust_bar"
TTL_S = 600.0

_ZEROS: dict[str, int] = {"users": 0, "subscribers": 0, "kundlis": 0, "asks": 0}


def _compute() -> dict[str, int]:
    """The original inline homepage block, verbatim — same swallow, same zeros.

    Each backend is guarded separately so one dead collection cannot zero the
    other three.
    """
    try:
        _users_ct = users.count()
    except Exception:
        _users_ct = 0
    try:
        _subs_ct = subscribers.count()
    except Exception:
        _subs_ct = 0
    # Kundli + Ask lifetime-ish counts from the GCS events log. We
    # aggregate across the full retention window (30 days) which is
    # a reasonable proxy for "till now" while numbers are early. When
    # traffic warrants a true lifetime counter, add a persistent
    # counters.py module — for now retention-window totals suffice.
    try:
        _totals = events.counts_by_type(days=events.EVENT_RETENTION_DAYS)
        _kundlis_ct = _totals.get("form_kundli", 0)
        _asks_ct = _totals.get("form_ask", 0)
    except Exception:
        _kundlis_ct = 0
        _asks_ct = 0
    return {
        "users": _users_ct,
        "subscribers": _subs_ct,
        "kundlis": _kundlis_ct,
        "asks": _asks_ct,
    }


def counts() -> dict[str, int]:
    """Current trust-bar counts. Never blocks; may be up to `TTL_S` stale."""
    return hot_cache.get_or_refresh(
        CACHE_KEY, ttl_s=TTL_S, fn=_compute, initial=dict(_ZEROS)
    )


def minimums() -> dict[str, int]:
    """Per-pill display thresholds.

    Trust bar counts (SEO audit #134) — real numbers only. Never fake,
    never round up. Each pill has a MIN THRESHOLD (env-overrideable);
    below the threshold the pill is hidden — "1 registered reader"
    looks weaker than no pill at all. Turn a pill on by lowering its
    env threshold once real traffic accumulates.

    Defaults picked so the site DOES NOT show any pill until numbers
    are meaningfully impressive (2026-08-06 user request).
    """
    return {
        "users":       int(os.environ.get("TRUST_MIN_USERS",       "500")),
        "subscribers": int(os.environ.get("TRUST_MIN_SUBSCRIBERS", "100")),
        "kundlis":     int(os.environ.get("TRUST_MIN_KUNDLIS",     "500")),
        "asks":        int(os.environ.get("TRUST_MIN_ASKS",        "500")),
    }
