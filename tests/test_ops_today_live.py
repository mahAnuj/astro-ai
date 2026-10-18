"""The three "today" tiles are read live, and the fallback says so.

WHY THIS FILE EXISTS, MEASURED
------------------------------
On 2026-10-18 /admin/ops read `0 shipped today`, `0 filed today`,
`0 failed today`. Five loop runs had failed that IST day. Two separate defects
produced one indistinguishable screen:

  1. STALENESS. `measurements/loop.json` is committed by `agent-measure`, which
     had failed on every run since 2026-10-15 ("GH006: Protected branch update
     failed"). `_loop_view` buckets by `date_ist == today_ist`, so with no row
     dated today each tile renders 0 -- a claim, not an absence.
  2. SCOPE. `collect_loop_measurements.py:109` is `WORKFLOW_NAME = "agent-work"`,
     so the file holds agent-work cycles alone. Every failure that day was
     `agent-measure`, which that source cannot represent at ANY freshness. The
     file being three days old hid a tile that would have read 0 regardless.

The circularity is the point and is what these tests pin: the failure the
dashboard could not show was the failure keeping the dashboard's data stale.

Hermetic: `urlopen` is stubbed in every test. No network, per conftest.
"""
from __future__ import annotations

import json
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import ops_data, ops_today  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))

#: 00:00 IST on 2026-10-18 == 18:30 UTC on the 17th. Every boundary assertion
#: here hangs off that offset, which is the one the naive filter got wrong.
DAY_START = datetime(2026, 10, 17, 18, 30, tzinfo=timezone.utc)
SINCE = "2026-10-17T18:30:00Z"


@pytest.fixture(autouse=True)
def _no_cache():
    """The live caches are module globals; a hit would serve another test."""
    ops_data._today_cache = None
    ops_data._live_cache = None
    yield
    ops_data._today_cache = None
    ops_data._live_cache = None


def _pr(number: int, merged_at: str | None) -> dict:
    return {"number": number, "title": f"PR {number}", "merged_at": merged_at,
            "html_url": f"https://github.com/x/y/pull/{number}"}


def _run(rid: int, path: str, conclusion: str, created_at: str) -> dict:
    return {"id": rid, "name": path.removesuffix(".yml"),
            "path": f".github/workflows/{path}", "conclusion": conclusion,
            "created_at": created_at, "html_url": f"https://github.com/x/y/{rid}"}


def _stub(monkeypatch, prs: list[dict], runs: list[dict]) -> list[str]:
    """Serve pulls then actions/runs. Returns the list of URLs requested."""
    urls: list[str] = []

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        urls.append(url)
        if "/pulls" in url:
            return _Resp(prs)
        if "/actions/runs" in url:
            return _Resp({"workflow_runs": runs})
        raise urllib.error.URLError(f"not stubbed: {url}")

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    return urls


# --------------------------------------------------------------------------- #
# fetch_today: what counts
# --------------------------------------------------------------------------- #

def test_a_pr_merged_before_the_ist_day_started_is_not_shipped_today(monkeypatch):
    _stub(monkeypatch,
          [_pr(1, "2026-10-17T18:29:59Z"), _pr(2, "2026-10-17T18:30:00Z")],
          [])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert [s["pr"] for s in got["shipped"]] == [2]


def test_an_unmerged_closed_pr_is_not_shipped(monkeypatch):
    _stub(monkeypatch, [_pr(1, None)], [])
    assert ops_today.fetch_today("x/y", DAY_START, timeout=1)["shipped"] == []


def test_a_pr_is_counted_once_even_if_the_endpoint_repeats_it(monkeypatch):
    """The unit is the PR, not the row.

    `collect_loop_measurements.py`'s own header says to count distinct `pr`
    values because two agent-work runs can share one PR. The live path counts
    PRs directly, and enforces the distinctness rather than assuming the
    endpoint never repeats.
    """
    _stub(monkeypatch, [_pr(7, "2026-10-18T02:00:00Z"),
                        _pr(7, "2026-10-18T02:00:00Z")], [])
    assert len(ops_today.fetch_today("x/y", DAY_START, timeout=1)["shipped"]) == 1


def test_every_loop_leg_counts_as_a_failure_not_just_agent_work(monkeypatch):
    """THE 2026-10-18 DEFECT. All five failures that day were agent-measure.

    A source scoped to agent-work reports 0 while the loop is visibly broken,
    and no amount of freshness fixes that -- which is why this assertion names
    the workflow rather than just counting.
    """
    _stub(monkeypatch, [], [
        _run(1, "agent-measure.yml", "failure", "2026-10-18T03:00:00Z"),
        _run(2, "agent-work.yml", "failure", "2026-10-18T04:00:00Z"),
    ])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert {f["workflow"] for f in got["failed"]} == {"agent-measure", "agent-work"}


def test_a_red_pr_gate_is_not_a_loop_failure(monkeypatch):
    """A gate going red is the gate working.

    Counting it here would make every caught defect look like an outage and
    bury the failures that are real.
    """
    _stub(monkeypatch, [], [_run(1, "pr-gates.yml", "failure", "2026-10-18T03:00:00Z")])
    assert ops_today.fetch_today("x/y", DAY_START, timeout=1)["failed"] == []


def test_a_run_killed_by_the_clock_counts_as_failed(monkeypatch):
    """`cancelled` is what `timeout-minutes` reports.

    PR #410's gates were killed at 20m10s and the check read `cancelled`. A
    gate killed by the clock did not fail -- it never ran, which is worse, and
    was invisible for exactly as long as this tile ignored the conclusion.
    """
    _stub(monkeypatch, [], [_run(1, "agent-work.yml", "cancelled", "2026-10-18T03:00:00Z")])
    assert len(ops_today.fetch_today("x/y", DAY_START, timeout=1)["failed"]) == 1


def test_a_successful_run_is_not_a_failure(monkeypatch):
    _stub(monkeypatch, [], [_run(1, "agent-work.yml", "success", "2026-10-18T03:00:00Z")])
    assert ops_today.fetch_today("x/y", DAY_START, timeout=1)["failed"] == []


def test_a_renamed_workflow_display_name_does_not_empty_the_tile(monkeypatch):
    """Matched on `path`, never on `name`.

    `name:` is free text in the workflow file. Keying on it means renaming a
    workflow silently zeroes this tile, which is the failure mode this whole
    file exists to prevent.
    """
    r = _run(1, "agent-measure.yml", "failure", "2026-10-18T03:00:00Z")
    r["name"] = "Nightly measurement (renamed)"
    _stub(monkeypatch, [], [r])
    assert len(ops_today.fetch_today("x/y", DAY_START, timeout=1)["failed"]) == 1


# --------------------------------------------------------------------------- #
# The IST boundary — the regression that produced a wrong number in testing
# --------------------------------------------------------------------------- #

def test_the_actions_query_is_bounded_by_the_ist_day_start_not_todays_utc_date(monkeypatch):
    """`created>=` must carry 10-17, not 10-18.

    The IST day opens at 18:30 UTC on the PREVIOUS day. Bounding the query by
    today's UTC date drops every run between 00:00 and 05:30 IST -- which is
    exactly when the loop is scheduled ("04:30 IST, after the rolling cap
    resets"). Measured while building this: the naive bound returned 2
    failures for 2026-10-18 where the correct one returned 5.
    """
    urls = _stub(monkeypatch, [], [])
    ops_today.fetch_today("x/y", DAY_START, timeout=1)
    runs_url = next(u for u in urls if "/actions/runs" in u)
    assert "2026-10-17" in runs_url, runs_url
    assert "2026-10-18" not in runs_url, runs_url


def test_a_run_started_in_the_evening_utc_belongs_to_the_next_ist_day(monkeypatch):
    _stub(monkeypatch, [], [
        _run(1, "agent-measure.yml", "failure", "2026-10-17T18:29:00Z"),   # before
        _run(2, "agent-measure.yml", "failure", "2026-10-17T22:50:00Z"),   # IST 18th
    ])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert [f["run"] for f in got["failed"]] == [2]


def test_an_ist_aware_day_start_is_normalised_rather_than_trusted(monkeypatch):
    """Passing 00:00 IST directly must give the same answer as 18:30 UTC.

    The caller converts today, but a function that silently returns a day of
    wrong rows when it does not is the same bug class in a new place.
    """
    urls = _stub(monkeypatch, [], [])
    ops_today.fetch_today("x/y", datetime(2026, 10, 18, tzinfo=IST), timeout=1)
    assert "2026-10-17" in next(u for u in urls if "/actions/runs" in u)


def test_fetch_today_costs_exactly_two_requests(monkeypatch):
    """The budget is 60/hour on a shared egress IP. Two, and only two."""
    urls = _stub(monkeypatch, [], [])
    ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert len(urls) == 2, urls


# --------------------------------------------------------------------------- #
# _loop_view: live wins, the fallback is labelled
# --------------------------------------------------------------------------- #

_SNAP = {"rows": [
    {"run": 1, "outcome": "failed", "date": "2026-10-18", "issue": 9, "pr": None,
     "started": "2026-10-18T03:00:00Z"},
]}


def test_live_rows_replace_the_snapshot_rather_than_joining_them():
    """Two sources counting different units into one tile means nothing."""
    live = {"since": SINCE, "shipped": [{"pr": 5}], "failed": [{"run": 2}]}
    v = ops_data._loop_view(_SNAP, "2026-10-18", live)
    assert v["today_live"] is True
    assert v["today_failed"] == [{"run": 2}]
    assert v["today_shipped"] == [{"pr": 5}]


def test_the_snapshot_is_used_and_flagged_when_the_api_call_fails():
    v = ops_data._loop_view(_SNAP, "2026-10-18", None)
    assert v["today_live"] is False
    assert len(v["today_failed"]) == 1
    assert v["today_failed"][0]["run"] == 1


def test_live_tiles_survive_a_missing_snapshot_file():
    """The ribbon needs loop.json. The tiles do not.

    `agent-measure` being unable to commit is precisely when the tiles matter
    most, so a missing file must not blank them.
    """
    live = {"since": SINCE, "shipped": [], "failed": [{"run": 2}]}
    v = ops_data._loop_view(None, "2026-10-18", live)
    assert v["ok"] is False
    assert v["today_live"] is True
    assert v["today_failed"] == [{"run": 2}]


def test_a_live_fetch_failure_returns_none_and_never_raises(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("rate limited")
    monkeypatch.setattr(ops_today.urllib.request, "urlopen", boom)
    assert ops_data._live_today(DAY_START) is None


# --------------------------------------------------------------------------- #
# The alert
# --------------------------------------------------------------------------- #

def test_the_failure_alert_fires_even_with_no_loop_json():
    """The old gate was `loop["ok"] and ...`.

    The snapshot that would have unlocked the alert was itself unwritable
    because `agent-measure` was failing -- the very thing the alert announces.
    A monitoring page must not require the broken subsystem's own output in
    order to report that it is broken.
    """
    live = {"since": SINCE, "shipped": [],
            "failed": [{"run": 2, "workflow": "agent-measure"}]}
    loop = ops_data._loop_view(None, "2026-10-18", live)
    issues = ops_data._issues_view(None, "2026-10-18")
    alerts = ops_data._alerts(loop, issues, {}, {}, {})
    assert any("failed today" in a["title"] for a in alerts), alerts


def test_the_failure_alert_names_which_legs_failed():
    live = {"since": SINCE, "shipped": [],
            "failed": [{"run": 2, "workflow": "agent-measure"},
                       {"run": 3, "workflow": "agent-measure"}]}
    loop = ops_data._loop_view(None, "2026-10-18", live)
    alerts = ops_data._alerts(loop, ops_data._issues_view(None, "2026-10-18"), {}, {}, {})
    hit = next(a for a in alerts if "failed today" in a["title"])
    assert "agent-measure" in hit["detail"]
    assert "2 loop run(s)" in hit["title"]


def test_the_page_renders_at_all_with_no_loop_json(monkeypatch):
    """A missing snapshot must blank a panel, never 500 the page.

    Measured 2026-10-18: the short zero-state raised
    `UndefinedError: 'dict object' has no attribute 'attribution'` at
    admin_ops.html:1161. The trigger is `loop.json` being unreadable, which is
    where `agent-measure` failing to commit eventually leads -- so the control
    room was one missing file away from dying of the outage it reports.
    """
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    real = ops_data._fetch
    monkeypatch.setattr(ops_data, "_fetch",
                        lambda n: None if n == "loop.json" else real(n))
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200


def test_one_render_costs_three_api_calls_and_a_second_render_costs_none(monkeypatch):
    """The whole-page budget, asserted in one place.

    One backlog request (#353) plus two for the today tiles. The ceiling is
    60/hour shared across every tenant on Cloud Run's egress IP, so the number
    that matters is per RENDER, and the caches are what keep a reload free.
    Three is the figure `ops_today`'s docstring commits to; this is what would
    notice it silently becoming four.
    """
    urls: list[str] = []

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" not in url:
            raise urllib.error.URLError("no raw fetches in this test")
        urls.append(url)
        return _Resp({"workflow_runs": []} if "/actions/runs" in url else [])

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", True)

    ops_data.snapshot(now=datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc))
    assert len(urls) == 3, urls
    ops_data.snapshot(now=datetime(2026, 10, 18, 6, 1, tzinfo=timezone.utc))
    assert len(urls) == 3, "the 300s caches are what keep this inside the budget"
