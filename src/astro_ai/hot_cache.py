"""Tiny thread-safe memo: TTL, stale-while-revalidate, and compute-once.

Why this exists (issue #144): the homepage handler is `async def` but calls
blocking I/O (GCS reads) directly on the asyncio event loop. The Dockerfile
runs a single uvicorn worker — one event loop — while Cloud Run allows
`containerConcurrency: 80`. So one slow request stalls *every* request on
that instance; we measured `GET /sw.js` taking 55s purely from queueing.
That is why `get_or_refresh` (stale-while-revalidate) exists and why it is
the preferred entry point for anything on a hot path: it never blocks the
caller, so a slow backend costs staleness, not availability.

Scope of the cache: **per-process / per-instance**. It lives in module
globals, it dies with the container, and it is not shared between Cloud Run
instances. That is acceptable here — `maxScale` is 5, so at most 5 instances
may briefly disagree about a value that is already TTL-bounded. This mirrors
the precedent already in the repo: `chart.py::_PANCHANG_CACHE` and
`main.py::_HOMEPAGE_PANCHANG_CACHE`, both plain per-process dicts.

Locking discipline: `_LOCK` is a bookkeeping lock only — it is never held
across a call to `fn`. Deduplication of concurrent work is done with a
*per-key* lock, which is held across `fn` on purpose (that is what turns 80
concurrent misses into one computation), but it never blocks a different key.

Failure policy for `get_or_compute` (deliberate): if `fn` raises, the
exception is **cached for `ERROR_TTL_S` seconds and re-raised** to every
caller in that window. Re-raising (rather than returning a fallback) keeps
the caller in control of degradation; caching the failure stops a broken
backend from turning 80 concurrent requests into a retry storm.

Stdlib only. No new dependencies.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable, NamedTuple, TypeVar

T = TypeVar("T")

MAX_ENTRIES = 500
"""Hard cap on cached keys; oldest inserted are evicted first. Mirrors the
bounded-growth guard on `_HOMEPAGE_PANCHANG_CACHE` in main.py."""

ERROR_TTL_S = 5.0
"""How long a failure is remembered, for both the raise-through path and the
background-refresh backoff."""


class _Entry(NamedTuple):
    value: object
    error: BaseException | None
    expires_at: float


_LOCK = threading.Lock()
_CACHE: dict[str, _Entry] = {}
_KEY_LOCKS: dict[str, threading.Lock] = {}
_INFLIGHT: set[str] = set()
_RETRY_AFTER: dict[str, float] = {}


def _store(key: str, value: object, error: BaseException | None, ttl_s: float) -> None:
    expires_at = math.inf if ttl_s == math.inf else time.monotonic() + ttl_s
    with _LOCK:
        _CACHE[key] = _Entry(value, error, expires_at)
        while len(_CACHE) > MAX_ENTRIES:
            oldest = next(iter(_CACHE))
            _CACHE.pop(oldest, None)
            _KEY_LOCKS.pop(oldest, None)


def _fresh(key: str) -> _Entry | None:
    with _LOCK:
        entry = _CACHE.get(key)
    if entry is not None and entry.expires_at > time.monotonic():
        return entry
    return None


def get_or_compute(key: str, ttl_s: float, fn: Callable[[], T]) -> T:
    """Return `fn()`'s result, cached for `ttl_s`. Blocks on a miss.

    Concurrent misses on the same key collapse into one call to `fn`; misses
    on different keys never wait on each other. If `fn` raises, the exception
    is cached for `ERROR_TTL_S` and re-raised (see module docstring).
    """
    entry = _fresh(key)
    if entry is not None:
        if entry.error is not None:
            raise entry.error
        return entry.value  # type: ignore[return-value]

    with _LOCK:
        key_lock = _KEY_LOCKS.setdefault(key, threading.Lock())

    with key_lock:
        entry = _fresh(key)  # another thread may have filled it while we waited
        if entry is not None:
            if entry.error is not None:
                raise entry.error
            return entry.value  # type: ignore[return-value]
        try:
            value = fn()
        except Exception as exc:
            _store(key, None, exc, ERROR_TTL_S)
            raise
        _store(key, value, None, ttl_s)
        return value


def get_or_refresh(key: str, ttl_s: float, fn: Callable[[], T], *, initial: T) -> T:
    """Stale-while-revalidate. **Never blocks the caller.**

    Fresh value -> return it. Stale value -> return the stale value now and
    recompute in a daemon thread. No value yet -> return `initial` now and
    fill in the background. At most one refresh per key is in flight; a
    failed refresh backs off for `ERROR_TTL_S` before another is attempted.
    """
    now = time.monotonic()
    with _LOCK:
        entry = _CACHE.get(key)
        stale = entry is not None and entry.expires_at <= now
        needs_refresh = entry is None or stale
        may_start = (
            needs_refresh
            and key not in _INFLIGHT
            and _RETRY_AFTER.get(key, 0.0) <= now
        )
        if may_start:
            _INFLIGHT.add(key)

    if may_start:
        threading.Thread(
            target=_refresh_worker, args=(key, ttl_s, fn), daemon=True
        ).start()

    if entry is not None and entry.error is None:
        return entry.value  # type: ignore[return-value]
    return initial


def _refresh_worker(key: str, ttl_s: float, fn: Callable[[], object]) -> None:
    try:
        _store(key, fn(), None, ttl_s)
    except Exception:
        with _LOCK:
            _RETRY_AFTER[key] = time.monotonic() + ERROR_TTL_S
    finally:
        with _LOCK:
            _INFLIGHT.discard(key)


def forever(key: str, fn: Callable[[], T]) -> T:
    """Compute once, cache for the lifetime of the process.

    Failures are still only cached for `ERROR_TTL_S`, so a bad start-up
    moment does not poison the key permanently.
    """
    return get_or_compute(key, math.inf, fn)


def clear() -> None:
    """Drop everything. For probes and tests."""
    with _LOCK:
        _CACHE.clear()
        _KEY_LOCKS.clear()
        _RETRY_AFTER.clear()
