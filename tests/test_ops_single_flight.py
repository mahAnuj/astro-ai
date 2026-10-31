"""Two cold /admin/ops renders must spend ONE render's GitHub budget (#450).

WHY THIS FILE EXISTS
--------------------
`routes/admin.py` runs `ops_data.snapshot` under `asyncio.to_thread`, which is a
REAL thread. The `await` yields while one render is inside it, so a second
request finds `_live_cache` / `_today_cache` still empty and starts its own full
set of reads. The cost is not hypothetical: the API ceiling is 60/hour per
egress IP, shared, and the documented per-render worst case is already 10.

REPRODUCED BEFORE THE FIX (2026-10-30, these very tests, unfixed ops_data.py):
4 threads, each fake request taking 0.15 s, caches cold -->

    _live_issues   4 requests  (one render's worth is 1)
    _live_today    8 requests  (one render's worth is 2)

i.e. N concurrent cold renders cost N renders. After the fix: 1 and 2.

Every wait here is bounded. A single-flight that deadlocks must FAIL the suite,
not hang it -- a hang is the one outcome a CI run cannot report.

Hermetic: `urlopen` is stubbed in every test. No network, per conftest.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai import ops_data  # noqa: E402

DAY_START = datetime(2026, 10, 17, 18, 30, tzinfo=timezone.utc)
THREADS = 4
#: Long enough that every thread has reached the cache check while the first is
#: still "in flight"; the Barrier below is what makes the overlap deterministic,
#: this only has to outlast thread start-up skew after it.
LATENCY = 0.15
#: A hang must fail, not block. Generous against LATENCY * THREADS.
JOIN_TIMEOUT = 10


@pytest.fixture(autouse=True)
def _no_cache():
    ops_data._today_cache = None
    ops_data._live_cache = None
    yield
    ops_data._today_cache = None
    ops_data._live_cache = None


class _Resp:
    def __init__(self, payload): self._p = payload
    def read(self): return json.dumps(self._p).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Spy:
    """A slow fake GitHub that counts every request, per endpoint family."""

    def __init__(self, fail_first: set[str] = frozenset()):
        self.lock = threading.Lock()
        self.urls: list[str] = []
        self._fail_first = set(fail_first)

    def count(self, needle: str) -> int:
        return sum(1 for u in self.urls if needle in u)

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        family = "/issues" if "/issues" in url else (
            "/pulls" if "/pulls" in url else "/actions/runs")
        with self.lock:
            self.urls.append(url)
            boom = family in self._fail_first
            self._fail_first.discard(family)
        time.sleep(LATENCY)
        if boom:
            raise urllib.error.URLError("rate limited")
        if family == "/actions/runs":
            return _Resp({"workflow_runs": []})
        return _Resp([])


def _install(monkeypatch, spy: _Spy) -> None:
    # `ops_data.urllib.request` IS the `urllib.request` module that
    # `issue_backlog` and `ops_today` import, so this one patch is the seam
    # for all three readers.
    monkeypatch.setattr(ops_data.urllib.request, "urlopen", spy)


def _race(fns: list, n: int = THREADS) -> list:
    """Run `fns[i % len(fns)]` on n threads released together; return results.

    Raises AssertionError if any thread is still alive after JOIN_TIMEOUT.
    """
    barrier = threading.Barrier(n)
    results: list = [None] * n
    errors: list = []

    def work(i):
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            results[i] = fns[i % len(fns)]()
        except BaseException as exc:  # noqa: BLE001 -- surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,), daemon=True)
               for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(JOIN_TIMEOUT)
    hung = [t for t in threads if t.is_alive()]
    assert not hung, f"{len(hung)} thread(s) still blocked after {JOIN_TIMEOUT}s"
    assert not errors, errors
    return results


# --------------------------------------------------------------------------- #
# (a) N concurrent cold calls spend one render's worth
# --------------------------------------------------------------------------- #

def test_concurrent_cold_backlog_reads_spend_one_request(monkeypatch):
    spy = _Spy()
    _install(monkeypatch, spy)
    got = _race([lambda: ops_data._live_issues("obj")])
    assert spy.count("/issues") == 1, (
        f"{THREADS} concurrent cold renders spent {spy.count('/issues')} "
        "backlog requests; one render's worth is 1")
    assert all(g is not None for g in got)
    assert all(g is got[0] for g in got), "waiters must be served the cached doc"


def test_concurrent_cold_today_reads_spend_one_renders_worth(monkeypatch):
    spy = _Spy()
    _install(monkeypatch, spy)
    got = _race([lambda: ops_data._live_today(DAY_START)])
    spent = spy.count("/pulls") + spy.count("/actions/runs")
    assert spent == 2, (
        f"{THREADS} concurrent cold renders spent {spent} today-tile requests; "
        "one render's worth is 2")
    assert all(g is got[0] and g is not None for g in got)


def test_concurrent_cold_snapshots_spend_one_renders_worth(monkeypatch):
    """The whole page, as the route calls it: snapshot() on N threads."""
    spy = _Spy()
    _install(monkeypatch, spy)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", True)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    # The committed-file readers are not the subject and would otherwise make
    # their own requests in an image without `measurements/`.
    monkeypatch.setattr(ops_data, "_fetch", lambda name: None)
    now = datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc)
    _race([lambda: ops_data.snapshot(now=now)])
    api = [u for u in spy.urls if "api.github.com" in u]
    assert len(api) == 3, (
        f"{THREADS} concurrent cold snapshots spent {len(api)} requests; "
        f"one render is 3: {api}")


# --------------------------------------------------------------------------- #
# (b) a failing first read releases the lock and hangs nobody
# --------------------------------------------------------------------------- #

def test_a_failing_first_backlog_read_releases_the_lock(monkeypatch):
    """The first read raises. The waiters must not hang on a held lock.

    `_live_issues` has never cached a failure (it returns before the store), so
    the next waiter legitimately makes its own read -- that is the existing
    semantics and the test pins it: exactly two requests, one failed and one
    that succeeded, and every thread comes back.
    """
    spy = _Spy(fail_first={"/issues"})
    _install(monkeypatch, spy)
    got = _race([lambda: ops_data._live_issues("obj")])
    assert spy.count("/issues") == 2, spy.urls
    assert sum(g is None for g in got) == 1, "exactly the failed caller sees None"
    assert sum(g is not None for g in got) == THREADS - 1
    # And the lock really is free afterwards, not merely free in this schedule.
    assert ops_data._live_issues("obj") is not None


def test_a_failing_first_today_read_is_cached_and_the_lock_released(monkeypatch):
    """None is cached for the day tiles, so the waiters are served it unread."""
    spy = _Spy(fail_first={"/pulls"})
    _install(monkeypatch, spy)
    got = _race([lambda: ops_data._live_today(DAY_START)])
    assert all(g is None for g in got), got
    assert ops_data._today_cache is not None and ops_data._today_cache[2] is None, \
        "the failure was not remembered"
    spent = spy.count("/pulls") + spy.count("/actions/runs")
    assert spent == 1, (
        f"the waiters re-asked after a cached failure ({spent} requests)")
    # Free afterwards: an expired entry must be able to refetch.
    stamp, day, doc = ops_data._today_cache
    ops_data._today_cache = (stamp - ops_data.CACHE_TTL - 1, day, doc)
    assert ops_data._live_today(DAY_START) is not None


# --------------------------------------------------------------------------- #
# (c) the two caches stay independent
# --------------------------------------------------------------------------- #

def test_a_failure_in_one_cache_neither_blanks_nor_blocks_the_other(monkeypatch):
    # Backlog read fails; today read succeeds, on interleaved threads.
    spy = _Spy(fail_first={"/issues"})
    _install(monkeypatch, spy)
    issues_fn = lambda: ("issues", ops_data._live_issues("obj"))      # noqa: E731
    today_fn = lambda: ("today", ops_data._live_today(DAY_START))     # noqa: E731
    got = _race([issues_fn, today_fn], n=2)
    by = dict(got)
    assert by["today"] is not None, "a backlog failure blanked the today tiles"
    assert by["issues"] is None
    assert ops_data._today_cache[2] is not None


def test_one_cache_being_filled_does_not_block_the_other(monkeypatch):
    """The backlog read cannot finish until the today read has.

    Deterministic, not timed: the fake holds the backlog request open until the
    today tiles have been served. Behind ONE shared lock the today caller waits
    for the backlog lock and the backlog request waits for the today caller --
    a cycle that the bounded Event wait turns into a failure, not a hang.
    """
    today_served = threading.Event()
    issues_in_flight = threading.Event()
    saw_today_first = []
    spy = _Spy()

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/issues" in url:
            issues_in_flight.set()
            saw_today_first.append(today_served.wait(timeout=3))
        return spy(req, timeout)

    monkeypatch.setattr(ops_data.urllib.request, "urlopen", urlopen)

    def today_fn():
        # Start only once the backlog request is in flight, so the schedule is
        # "backlog holds its lock, then today asks" every time. Without this,
        # today can win a shared lock first and the test passes by luck.
        assert issues_in_flight.wait(timeout=3)
        out = ops_data._live_today(DAY_START)
        today_served.set()
        return out

    _race([lambda: ops_data._live_issues("obj"), today_fn], n=2)
    assert saw_today_first == [True], (
        "the today tiles could not be served while the backlog read was in "
        "flight -- the two caches are sharing a lock")
