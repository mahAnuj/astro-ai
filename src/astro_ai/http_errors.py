"""Per-route count of HTTP 5xx responses, so the weekly measurement can name a route (#1506).

WHY THIS EXISTS
---------------
The loop's analyst reported "HTTP 5xx per route: no data" every week. Nothing recorded a
5xx against the route that served it: `events.record(type="error")` is a per-event log
labelled by a hand-written `source`, and an inline `status_code=503` page (the
"every LLM provider is exhausted" pages) never reaches it at all. The count has to be
taken where every response passes, which is the ASGI `send`.

Persisted to GCS as `http_errors/YYYY-MM-DD.json`, one blob per UTC day, a SEPARATE blob
from `llm_stats/`: a 5xx storm must not contend on the compare-and-swap of the blob that
carries the token-ceiling numbers, and a bad write here cannot corrupt `range_summary`.
`scripts/collect_llm_usage.py` is the only reader.

    {"date": "2026-11-27", "boots": 3,
     "by_route": {"GET /learn/{slug}": {"500": 2, "503": 1}, "POST /kundli": {"500": 1}}}

Four rules worth knowing before reading a number off it:

  * The label is `"<METHOD> <route template>"` and nothing else. Never the raw path, query
    string, IP, header or cookie: a scanner hitting 10,000 distinct URLs must not grow the
    blob, and the label must carry no PII. A 5xx with no matched route (a static mount, a
    failure before routing) is `"<METHOD> unmatched"`. At most `MAX_ROUTES` labels per day;
    a new one past the cap folds into `"other"`.
  * Only status 500-599 is counted. 404s are scanner noise and would bury the signal.
  * Counts are COALESCED, never written per request. A 5xx storm is exactly when a write per
    failed request is a CAS storm and a burst of Class A operations (free tier: 5,000/month).
    The request path does one locked dict increment; a flush runs at most once per
    `FLUSH_MIN_INTERVAL_S` per process, and once more at shutdown. A process killed with
    SIGKILL or OOM loses its unflushed tail: an UNDERcount, never an invented one.
  * A day with no blob is NO EVIDENCE, not a zero: a quiet day writes nothing, and
    `storage.get` cannot tell "missing" from "unavailable". `boots` exists so that a day on
    which any instance started has a blob, and `range_summary()["days_recorded"]` tells the
    reader how many days of the window are evidence at all.

ORDERING (load-bearing): `main.py` adds this middleware BEFORE
`_RewriteHostFromForwardedMiddleware`, which makes it the innermost user middleware.
The router sets `scope["route"]` on the scope dict it was handed, and the host rewrite
replaces the scope with a COPY whenever `X-Forwarded-Host` is present (Firebase always sets
it). A middleware outside the rewrite reads `route=None` in production and labels every
5xx `unmatched`; a local request without that header cannot show it.

A handler-level hook would not do: an unhandled exception is rendered by
`ServerErrorMiddleware`, outside every user middleware, and an inline `status_code=503`
never passes an exception handler at all.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from astro_ai import storage

log = logging.getLogger(__name__)

# Distinct labels kept per day blob and per pending dict. The real keyspace is ~70 routes x
# ~2 methods x a few statuses, so this is a backstop for a bug, not an expected limit.
MAX_ROUTES = 100
_OTHER = "other"

# One flush per process per interval. 600 s caps a sustained all-day incident at 144 writes
# per instance per day (maxScale=5 -> 720), and a healthy week at about zero.
FLUSH_MIN_INTERVAL_S = 600
# Awaited, not fire-and-forget: Cloud Run is request-billed, so a background thread can be
# CPU-throttled the instant the response finishes and the write never happens. The cap
# bounds what a slow bucket can add to a request that has already failed.
_FLUSH_TIMEOUT_S = 3.0

_METHODS = frozenset({"GET", "POST", "HEAD", "PUT", "DELETE", "PATCH"})
_STATUS_KEYS = frozenset(str(s) for s in range(500, 600))
RETENTION_DAYS = 30

_PENDING: dict[str, dict[str, int]] = {}
_LOCK = threading.Lock()
# -inf so the FIRST 5xx of a process is written at once; later ones coalesce.
_LAST_FLUSH = float("-inf")


def _fallback_dir() -> Path:
    # Read per call, not at import, so a test can point it at tmp_path.
    return Path(os.environ.get("BHAGYA_HTTP_ERRORS_FALLBACK_DIR", "/tmp/bhagya_http_errors"))


def _key_for(day: date) -> str:
    return f"http_errors/{day.isoformat()}.json"


def _local_path(day: date) -> Path:
    return _fallback_dir() / f"{day.isoformat()}.json"


def _read_day(day: date) -> Any:
    """One day's blob from GCS, else the local fallback file. None if absent."""
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


def _as_count(v: Any) -> int | None:
    """A stored counter as a non-negative int, or None for anything a hand-edited blob put there."""
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        return None
    return v


def _slot(by_route: dict, label: str) -> str:
    """The key `label` is booked under: itself, or "other" once the cap is reached.
    The last slot is reserved for "other", so the dict never exceeds MAX_ROUTES keys."""
    if label in by_route or len(by_route) < MAX_ROUTES - 1:
        return label
    return _OTHER


def label_for(scope: dict) -> str:
    """`"<METHOD> <route template>"`, or `"<METHOD> unmatched"`. See the module docstring."""
    method = scope.get("method")
    method = method if method in _METHODS else "OTHER"
    path = getattr(scope.get("route"), "path", None)
    return f"{method} {path if isinstance(path, str) and path else 'unmatched'}"


def count(label: str, status: int) -> None:
    """Book one 5xx in the in-process accumulator. O(1), no I/O, never raises."""
    key = str(status)
    if key not in _STATUS_KEYS:
        return
    with _LOCK:
        by_status = _PENDING.setdefault(_slot(_PENDING, label), {})
        by_status[key] = by_status.get(key, 0) + 1


def _merge(by_route: dict, batch: dict[str, dict[str, int]]) -> None:
    """Add `batch` onto `by_route` in place. Pure w.r.t. `batch`, so a CAS retry re-applies it."""
    for label, by_status in batch.items():
        slot = _slot(by_route, label)
        row = by_route.get(slot)
        if not isinstance(row, dict):
            row = by_route[slot] = {}
        for status, n in by_status.items():
            row[status] = (_as_count(row.get(status)) or 0) + n


def _write(mutator) -> bool:
    """Apply `mutator` to today's blob: GCS first, local file when GCS is unavailable
    (as llm_stats does, so dev and tests need no bucket). True when it landed."""
    today = date.today()
    if storage.update_json(_key_for(today), lambda cur: mutator(cur, today), default=None) is not None:
        return True
    try:
        _fallback_dir().mkdir(parents=True, exist_ok=True)
        path = _local_path(today)
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
        path.write_text(json.dumps(mutator(current, today), ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as err:  # noqa: BLE001 -- the recorder is best-effort
        log.debug("http_errors local fallback failed: %s", err)
        return False


def _fresh(current: Any, today: date) -> dict:
    data = current if isinstance(current, dict) else {}
    data.setdefault("date", today.isoformat())
    if not isinstance(data.get("by_route"), dict):
        data["by_route"] = {}
    return data


def flush() -> None:
    """Write the pending counts. Sync (run it in the threadpool); never raises.

    The accumulator is drained under the lock BEFORE the write, so a count is written once;
    a write that fails puts the batch back, so it is neither lost nor doubled."""
    try:
        with _LOCK:
            batch = {label: dict(s) for label, s in _PENDING.items()}
            _PENDING.clear()
        if not batch:
            return

        def _mut(current: Any, today: date) -> dict:
            data = _fresh(current, today)
            _merge(data["by_route"], batch)
            return data

        try:
            landed = _write(_mut)
        except Exception as err:  # noqa: BLE001 -- storage raising must not lose the batch
            log.debug("http_errors.flush write raised: %s", err)
            landed = False
        if not landed:
            with _LOCK:
                for label, by_status in batch.items():
                    row = _PENDING.setdefault(_slot(_PENDING, label), {})
                    for status, n in by_status.items():
                        row[status] = row.get(status, 0) + n
    except Exception as err:  # noqa: BLE001
        log.debug("http_errors.flush failed: %s", err)


def mark_boot() -> None:
    """Count one process start on today's blob, so a day an instance started has a blob and
    "no 5xx" can be told from "the recorder was not running". Best-effort; never raises."""
    try:
        def _mut(current: Any, today: date) -> dict:
            data = _fresh(current, today)
            data["boots"] = (_as_count(data.get("boots")) or 0) + 1
            return data

        _write(_mut)
    except Exception as err:  # noqa: BLE001
        log.debug("http_errors.mark_boot failed: %s", err)


def flush_on_shutdown() -> None:
    """Flush the tail of the interval at SIGTERM (Cloud Run gives ~10 s), so a scale-down or
    a deploy does not drop it. SIGKILL and OOM still can; that is an undercount."""
    flush()


async def _flush_if_due() -> None:
    """Flush if the interval has elapsed. Called after the response has gone out (or just
    before re-raising), never raises. `_LAST_FLUSH` is set BEFORE the write so that 80
    concurrent failures flush once."""
    global _LAST_FLUSH
    try:
        now = time.monotonic()
        if now - _LAST_FLUSH < FLUSH_MIN_INTERVAL_S:
            return
        _LAST_FLUSH = now
        await asyncio.wait_for(run_in_threadpool(flush), timeout=_FLUSH_TIMEOUT_S)
    except Exception as err:  # noqa: BLE001 -- a timeout lets the thread finish on its own
        log.debug("http_errors flush skipped: %s", err)


def _record(scope: dict, status: int) -> None:
    try:
        count(label_for(scope), status)
    except Exception as err:  # noqa: BLE001 -- counting must never touch a response
        log.debug("http_errors.count failed: %s", err)


class HttpErrorMiddleware:
    """Pure ASGI. Forwards every message unchanged, never buffers or delays a response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        seen = {"status": 0}

        async def _send(message):
            if message["type"] == "http.response.start":
                status = message.get("status")
                seen["status"] = status if isinstance(status, int) else 0
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except ClientDisconnect:
            raise                        # the client left; not a server fault
        except Exception:
            # An unhandled exception reaches us as an exception, never as a response:
            # ServerErrorMiddleware, outside us, renders the 500. Count once.
            _record(scope, seen["status"] if seen["status"] >= 500 else 500)
            await _flush_if_due()
            raise
        if seen["status"] >= 500:
            _record(scope, seen["status"])
            await _flush_if_due()


def range_summary(days: int, today: date | None = None) -> dict[str, Any]:
    """The last `days` day blobs (inclusive of `today`, UTC), summed. Collector only.

    `days_recorded` is how many of those days HAVE a blob; a missing day is no evidence, not
    a zero. A hand-edited blob (a non-dict `by_route`, bool/negative/string counts, a bad
    status key) is skipped row by row and never raises."""
    days = max(1, min(int(days), RETENTION_DAYS))
    end = today or date.today()
    total = 0
    recorded = 0
    acc: dict[str, dict[str, int]] = {}
    for i in range(days):
        blob = _read_day(end - timedelta(days=i))
        if not isinstance(blob, dict):
            continue
        recorded += 1
        by_route = blob.get("by_route")
        for label, by_status in (by_route.items() if isinstance(by_route, dict) else ()):
            if not isinstance(by_status, dict):
                continue
            for status, n in by_status.items():
                n = _as_count(n)
                if n is None or status not in _STATUS_KEYS:
                    continue
                row = acc.setdefault(str(label), {})
                row[status] = row.get(status, 0) + n
                total += n
    return {
        "from": (end - timedelta(days=days - 1)).isoformat(),
        "to": end.isoformat(),
        "days": days,
        "days_recorded": recorded,
        "total": total,
        "by_route": {label: {"total": sum(s.values()), "by_status": dict(s)}
                     for label, s in acc.items()},
    }
