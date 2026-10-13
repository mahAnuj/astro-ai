"""Per-day event log for admin observability.

Every notable user event (Kundli form submission, matching submission,
Ask question, error) is appended to a daily file in GCS at
`events/YYYY-MM-DD.jsonl` (one JSON object per line). Local /tmp fallback
for dev.

Retention: 30 days, same convention as llm_stats. Bucket lifecycle rule
can auto-delete older files.

Design: append-only via storage.update_json's CAS retry loop. Each record
call reads the current day's array, appends the new event, writes back.
Adds ~100-300ms per event; runs from FastAPI handlers so acceptable at
current traffic. Migrate to a proper events collection (Firestore, BQ)
when write throughput matters more than simplicity.

Schema (per-day file, JSON — not JSONL, easier to CAS):
    {
      "date": "2026-07-28",
      "events": [
        {
          "ts":    "2026-07-28T14:23:01+00:00",
          "type":  "form_kundli" | "form_matching" | "form_ask" | "error",
          "email": "u@x.com",          # signed-in user email, or ""
          "data":  { ... type-specific ... }
        },
        ...
      ]
    }

PII (#255): `form_kundli` and `form_matching` no longer store name, birth
date, time or place. They carry `identity.identity_key` hashes (HMAC: not
reversible, and not guessable from a date, without the server secret), the
rashi triple, and the coarse `profiling.coarse_profile` fields (age band, city) that keep
/admin/insights working.

Events STILL carry: the signed-in user's email on every event; `form_ask`
question text and the answer body; `error` message and traceback (a ChartError,
which embeds the birth place, is redacted in routes/llm_support). Rows written
before #255 still hold raw birth details until they age out at
EVENT_RETENTION_DAYS. templates/privacy.html discloses the remainder.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from astro_ai import hot_cache, storage

log = logging.getLogger(__name__)

EVENT_RETENTION_DAYS = 30
_MAX_EVENTS_PER_DAY = 5000  # safety cap so a bug can't blow up storage
_LOCAL_FALLBACK_DIR = Path(os.environ.get("BHAGYA_EVENTS_FALLBACK_DIR", "/tmp/bhagya_events"))

_TODAY_TTL_S = 60.0
"""Today's blob is still being appended to, so it can only be memoised briefly."""

_ABSENT_TTL_S = 300.0
"""How long we remember that an elapsed day has *no* blob. Not forever: a
backfill can create one after the fact."""

_READ_WORKERS = 8
"""Parallel GCS reads for the cold fill. Safe only because storage._client()
now shares a single google-cloud-storage client (and its connection pool)
across the process — 8 threads each building their own client would be worse."""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _key_for(day: date) -> str:
    return f"events/{day.isoformat()}.json"


def _local_path(day: date) -> Path:
    return _LOCAL_FALLBACK_DIR / f"{day.isoformat()}.json"


class _AbsentDay(Exception):
    """Internal signal: the day has no blob. Keeps `hot_cache.forever` from
    pinning a `None` for the lifetime of the process."""


_GEN_LOCK = threading.Lock()
_TODAY_GEN = 0


def _today_gen() -> int:
    with _GEN_LOCK:
        return _TODAY_GEN


def _bump_today_gen() -> None:
    """Invalidate the memoised copy of today's blob.

    `hot_cache` has no per-key delete, so today's cache key carries a
    generation counter and we simply move to the next one; the abandoned entry
    expires on its own within `_TODAY_TTL_S`.
    """
    global _TODAY_GEN
    with _GEN_LOCK:
        _TODAY_GEN += 1


def _fetch_day(day: date) -> dict[str, Any] | None:
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


def _read_day(day: date) -> dict[str, Any] | None:
    """Memoised `_fetch_day`. Same return value, far fewer round trips.

    An elapsed day's blob never changes again, so once seen it is pinned for
    the lifetime of the process. Today's is re-read every `_TODAY_TTL_S`
    (and immediately after a `record()`). A future day — which shouldn't
    happen — is never cached.
    """
    today = date.today()
    if day > today:
        return _fetch_day(day)

    key = f"events:day:{day.isoformat()}"
    if day == today:
        return hot_cache.get_or_compute(
            f"{key}#{_today_gen()}", _TODAY_TTL_S, lambda: _fetch_day(day)
        )

    def _pin() -> dict[str, Any]:
        # Only reached when the day is not already pinned. The inner probe
        # bounds how often a still-missing day is re-read from storage.
        blob = hot_cache.get_or_compute(
            f"{key}:probe", _ABSENT_TTL_S, lambda: _fetch_day(day)
        )
        if blob is None:
            raise _AbsentDay
        return blob

    try:
        return hot_cache.forever(key, _pin)
    except _AbsentDay:
        return None


def record(*, type: str, email: str = "", data: dict | None = None) -> None:
    """Append one event to today's file. Best-effort; never raises."""
    today = date.today()
    event = {
        "ts": _now_iso(),
        "type": type,
        "email": email,
        "data": data or {},
    }

    def _mut(current: dict | None) -> dict:
        blob = current or {"date": today.isoformat(), "events": []}
        events = blob.get("events", [])
        events.append(event)
        # Safety cap — drop from head (oldest) if we hit the limit.
        if len(events) > _MAX_EVENTS_PER_DAY:
            events = events[-_MAX_EVENTS_PER_DAY:]
        blob["events"] = events
        return blob

    result = storage.update_json(_key_for(today), _mut, default=None)
    if result is not None:
        # Drop the memoised copy of today so /admin/activity and the
        # audience-insights view see this event on the very next read.
        # Residual staleness: other Cloud Run instances keep their own copy
        # for up to _TODAY_TTL_S. Acceptable for an admin-only view.
        _bump_today_gen()
        return
    # Local fallback (non-atomic; fine for dev / preview).
    try:
        _LOCAL_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        path = _local_path(today)
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
        new_data = _mut(current)
        path.write_text(json.dumps(new_data, ensure_ascii=False), encoding="utf-8")
        _bump_today_gen()
    except Exception as err:  # noqa: BLE001 — events are best-effort
        log.debug("events.record local fallback failed: %s", err)


def recent(*, types: Iterable[str] | None = None, limit: int = 100,
           days: int = 7) -> list[dict[str, Any]]:
    """Return the most-recent events across the last `days` days.

    Filtered by `types` if provided; else all types. Sorted newest-first.
    Not paginated — cap at `limit`.
    """
    days = max(1, min(days, EVENT_RETENTION_DAYS))
    wanted = set(types) if types else None
    out: list[dict[str, Any]] = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        blob = _read_day(d)
        if blob is None:
            continue
        for evt in reversed(blob.get("events", [])):
            if wanted is not None and evt.get("type") not in wanted:
                continue
            out.append(evt)
            if len(out) >= limit:
                return out
    return out


def counts_by_type(*, days: int = 7) -> dict[str, int]:
    """Total event counts per type across the last `days` days."""
    days = max(1, min(days, EVENT_RETENTION_DAYS))
    today = date.today()
    wanted_days = [today - timedelta(days=i) for i in range(days)]

    # Cold fill is I/O-bound on cross-region GCS round trips, so fan out.
    # Aggregation stays on this thread — `totals` is never touched by a worker.
    with ThreadPoolExecutor(max_workers=_READ_WORKERS) as pool:
        blobs = list(pool.map(_read_day, wanted_days))

    totals: dict[str, int] = {}
    for blob in blobs:
        if blob is None:
            continue
        for evt in blob.get("events", []):
            t = evt.get("type", "unknown")
            totals[t] = totals.get(t, 0) + 1
    return totals
