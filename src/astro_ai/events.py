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

PII: birth details, emails, question text ARE stored. Same PII the site
already stores in users.json + sends to Telegram alerts. Update privacy
policy accordingly.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from astro_ai import storage

log = logging.getLogger(__name__)

EVENT_RETENTION_DAYS = 30
_MAX_EVENTS_PER_DAY = 5000  # safety cap so a bug can't blow up storage
_LOCAL_FALLBACK_DIR = Path(os.environ.get("BHAGYA_EVENTS_FALLBACK_DIR", "/tmp/bhagya_events"))


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _key_for(day: date) -> str:
    return f"events/{day.isoformat()}.json"


def _local_path(day: date) -> Path:
    return _LOCAL_FALLBACK_DIR / f"{day.isoformat()}.json"


def _read_day(day: date) -> dict[str, Any] | None:
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
    totals: dict[str, int] = {}
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        blob = _read_day(d)
        if blob is None:
            continue
        for evt in blob.get("events", []):
            t = evt.get("type", "unknown")
            totals[t] = totals.get(t, 0) + 1
    return totals
