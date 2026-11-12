"""A run dropped from the queue is not a failed loop run (2026-11-11).

/admin/ops raised "At least 3 loop run(s) failed today" naming Agent merge and
verify-production. Both runs (42963999553, 42977495873) were `cancelled` 18s
and 28s after creation with zero jobs: GitHub keeps one pending run per
concurrency group and cancels the waiting one when a newer run arrives. A run
killed by `timeout-minutes` still counts, because it runs to its limit.
"""
from __future__ import annotations

import glob
from pathlib import Path

import yaml

from astro_ai import ops_today

ROOT = Path(__file__).resolve().parents[1]


def run(concl, created="2026-11-11T05:10:34Z", updated="2026-11-11T05:10:52Z"):
    return {"conclusion": concl, "created_at": created, "updated_at": updated}


def test_a_cancel_seconds_after_creation_is_superseded():
    assert ops_today.superseded(run("cancelled"))                                   # 18s, run 42963999553
    assert ops_today.superseded(run("cancelled", "2026-11-11T07:09:58Z", "2026-11-11T07:10:26Z"))


def test_a_cancel_at_a_timeout_still_counts_as_a_failure():
    assert not ops_today.superseded(run("cancelled", "2026-11-11T05:00:00Z", "2026-11-11T05:10:05Z"))


def test_only_cancelled_is_ever_read_as_superseded():
    for c in ("failure", "timed_out", "startup_failure", "action_required"):
        assert not ops_today.superseded(run(c))


def test_an_unreadable_time_keeps_the_failure():
    assert not ops_today.superseded({"conclusion": "cancelled", "created_at": "?"})


def test_no_loop_job_times_out_inside_the_superseded_window():
    # If a loop job's limit ever fell to the window, a real timeout would be
    # hidden as a queue drop. Pinned with a 2x margin.
    for f in glob.glob(str(ROOT / ".github/workflows/*.yml")):
        name = Path(f).name
        if name not in ops_today.LOOP_WORKFLOWS:
            continue
        for job, spec in (yaml.safe_load(open(f))["jobs"] or {}).items():
            limit = spec.get("timeout-minutes", 360)
            assert limit * 60 >= 2 * ops_today.SUPERSEDED_WITHIN_S, f"{name}:{job} timeout {limit} min"


def _fetch_failed(monkeypatch, runs):
    import json
    import urllib.error
    from datetime import datetime, timezone

    class _Resp:
        def __init__(self, p): self._p = p
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/pulls" in url:
            return _Resp([])
        if "/actions/runs" in url:
            return _Resp({"workflow_runs": runs})
        raise urllib.error.URLError(url)
    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    day = datetime(2026, 11, 10, 18, 30, tzinfo=timezone.utc)
    return ops_today.fetch_today("x/y", day, timeout=1)["failed"]


def _r(rid, path, concl, created, updated):
    return {"id": rid, "name": path[:-4], "path": f".github/workflows/{path}",
            "conclusion": concl, "created_at": created, "updated_at": updated,
            "html_url": f"https://github.com/x/y/{rid}"}


def test_the_failed_tile_skips_queue_drops_and_keeps_real_failures(monkeypatch):
    failed = _fetch_failed(monkeypatch, [
        _r(42963999553, "agent-merge.yml", "cancelled", "2026-11-11T05:10:34Z", "2026-11-11T05:10:52Z"),
        _r(42977495873, "verify-production.yml", "cancelled", "2026-11-11T07:09:58Z", "2026-11-11T07:10:26Z"),
        _r(42933391630, "agent-prioritise.yml", "failure", "2026-11-11T00:41:00Z", "2026-11-11T00:42:30Z"),
        _r(1, "agent-merge.yml", "cancelled", "2026-11-11T01:00:00Z", "2026-11-11T01:10:05Z"),   # a timeout
    ])
    assert sorted(f["run"] for f in failed) == [1, 42933391630]
