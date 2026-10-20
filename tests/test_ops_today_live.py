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
import re
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


def _pr(number: int, merged_at: str | None,
        closed_at: str = "2026-10-17T20:00:00Z",
        updated_at: str | None = None) -> dict:
    """A row from `/pulls?state=closed`.

    `closed_at` IS ALWAYS PRESENT, and defaults to a timestamp inside the day,
    because that is what the endpoint returns: every row from `state=closed`
    carries one, merged or not. Omitting it made
    `test_an_unmerged_closed_pr_is_not_shipped` unable to fail -- the obvious
    wrong implementation, `merged_at or closed_at`, counts every closed PR as
    shipped and passed against a fixture where `closed_at` did not exist.
    Proved by mutation, which reported MISSED. Same class as the tied-sort-key
    defect in #419: the fixture, not the assertion, was what could not fail.

    `updated_at` IS ALSO ALWAYS PRESENT, for the same reason one level down.
    `_pages` stops on `oldest(batch[-1]) < since`, and its `oldest` for this
    endpoint is `r.get("updated_at") or ""` -- so a fixture without the field
    yields `""`, which is below EVERY `since`, and the pulls pager stopped on
    the day-boundary rule after one page no matter what was in the rows. The
    truncation test could therefore only ever truncate the RUNS read, and no
    test could observe the pulls pager paging at all. The endpoint sorts by
    this field (`sort=updated`), so it is the one field that cannot be absent.
    Defaults to `merged_at or closed_at`: GitHub guarantees
    `updated_at >= merged_at`, and equality is the tightest honest default.
    """
    return {"number": number, "title": f"PR {number}", "merged_at": merged_at,
            "closed_at": closed_at,
            "updated_at": updated_at or merged_at or closed_at,
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
    """Closed is not merged, and the row carries `closed_at` to prove it.

    The fixture is the whole test: `merged_at` is None while `closed_at` sits
    INSIDE the day, so an implementation reading `merged_at or closed_at` --
    the natural wrong one, since every row here is closed -- counts this PR and
    fails. See `_pr`.
    """
    _stub(monkeypatch, [_pr(1, None, closed_at="2026-10-17T20:00:00Z")], [])
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
    """The budget is 60/hour on a shared egress IP. Two, and only two.

    NON-EMPTY FIXTURES, deliberately. This passed EMPTY lists, and an empty
    list is a degenerate short page: `len(batch) < PER_PAGE` is true of zero
    rows whatever the pager does, so the assertion held for a reason that had
    nothing to do with the stop rules. One row each still exercises the
    short-page rule against a real row, and
    `test_a_pathological_day_is_capped_at_three_pages_per_endpoint` below
    covers the case that actually pages.
    """
    urls = _stub(monkeypatch,
                 [_pr(1, "2026-10-18T09:00:00Z")],
                 [_run(1, "agent-work.yml", "failure", "2026-10-18T09:00:00Z")])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert len(urls) == 2, urls
    assert len(got["shipped"]) == 1 and len(got["failed"]) == 1, \
        "the fixture was filtered out, so the count measured an empty read"


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
    Three is the ORDINARY-day figure `ops_today`'s COST paragraph commits to.

    It used to claim to be "what would notice it silently becoming four", and
    it could not: the fixtures were EMPTY, so both endpoints returned a
    degenerate short page and the pager could not have spent a second request
    whatever `MAX_PAGES` or the stop rules said. Served one real row each now,
    so three is three because the stop rules fired, not because there was
    nothing to read. The worst case -- 7 per render, which is OVER the 60/hour
    budget at 12 cache misses an hour -- is pinned by
    `test_a_pathological_day_is_capped_at_three_pages_per_endpoint` and
    `test_the_cost_paragraph_states_the_actual_worst_case`.
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
        if "/actions/runs" in url:
            return _Resp({"workflow_runs": [
                _run(1, "agent-work.yml", "failure", "2026-10-18T03:00:00Z")]})
        if "/pulls" in url:
            return _Resp([_pr(1, "2026-10-18T03:00:00Z")])
        return _Resp([])            # the backlog's /issues page

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", True)

    ops_data.snapshot(now=datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc))
    assert len(urls) == 3, urls
    ops_data.snapshot(now=datetime(2026, 10, 18, 6, 1, tzinfo=timezone.utc))
    assert len(urls) == 3, "the 300s caches are what keep this inside the budget"


# --------------------------------------------------------------------------- #
# Round 1 QA (2026-10-18) found eleven defects in the code above. These are the
# gates for the ones that were real, each named after the wrong behaviour it
# forbids rather than the right one it allows. Every one of them was MISSED by
# the suite as it stood -- a mutation proving each is in
# `mutate_behaviour_suite.py` beside it.
# --------------------------------------------------------------------------- #

def test_the_live_cache_does_not_survive_ist_midnight(monkeypatch):
    """Keyed on the clock alone, the entry outlives the day it describes.

    00:00 IST is 18:30 UTC, i.e. the middle of a UTC working afternoon, so the
    rollover is not an hour anyone would catch this in. For up to CACHE_TTL
    after midnight the tile reported YESTERDAY's merges and failures under the
    word "today", with the `live` badge beside them.
    """
    yday = DAY_START - timedelta(days=1)
    _stub(monkeypatch, [], [_run(1, "agent-work.yml", "failure",
                                 "2026-10-16T19:00:00Z")])
    before = ops_today.fetch_today("x/y", yday, timeout=1)
    ops_data._today_cache = (ops_data.time.monotonic(), yday.isoformat(), before)
    assert len(ops_data._live_today(yday)["failed"]) == 1, "same day: cached"
    # One second later in wall-clock terms, but a different IST day.
    fresh = ops_data._live_today(DAY_START)
    assert fresh is None or fresh["since"] == SINCE, \
        "the entry for the previous IST day was served for today"


def test_a_failure_outside_the_four_old_exception_types_does_not_500_the_page(
        monkeypatch):
    """`http.client.IncompleteRead` is not URLError, OSError, ValueError or KeyError.

    A truncated response is the ordinary failure of an HTTP read over a flaky
    link. Under the old tuple it escaped `_live_today`, escaped `snapshot()`,
    and took down the whole control room -- the one page you open to find out
    what is broken -- to protect a freshness nicety on one tile.
    """
    import http.client

    def boom(*a, **k):
        raise http.client.IncompleteRead(b"half")

    monkeypatch.setattr(ops_today, "fetch_today", boom)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    assert ops_data._live_today(DAY_START) is None


def test_a_failing_live_path_is_not_retried_on_every_render(monkeypatch):
    """None is cached too, or an outage costs one request per page view.

    The overwhelmingly likely failure is a 403 from the 60/hour unauthenticated
    budget on a shared egress IP. Re-asking every render is what keeps that
    budget spent -- the outage becomes self-sustaining.
    """
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise urllib.error.URLError("rate limited")

    monkeypatch.setattr(ops_today, "fetch_today", boom)
    assert ops_data._live_today(DAY_START) is None
    assert ops_data._live_today(DAY_START) is None
    assert len(calls) == 1, "the failure was re-asked instead of remembered"


def test_shipped_and_failed_are_newest_first(monkeypatch):
    """The drill-down lists them in order and nothing asserted it.

    Reversed, the page reads as though the oldest event of the day were the
    most recent thing that happened.
    """
    _stub(monkeypatch,
          [_pr(1, "2026-10-17T19:00:00Z"), _pr(2, "2026-10-18T09:00:00Z")],
          [_run(1, "agent-work.yml", "failure", "2026-10-17T19:00:00Z"),
           _run(2, "agent-merge.yml", "failure", "2026-10-18T09:00:00Z")])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert [s["pr"] for s in got["shipped"]] == [2, 1]
    assert [f["run"] for f in got["failed"]] == [2, 1]


def test_the_live_cache_expires(monkeypatch):
    """Without the TTL the tiles freeze at the first render of the process."""
    _stub(monkeypatch, [], [])
    first = ops_data._live_today(DAY_START)
    assert ops_data._live_today(DAY_START) is first
    stamp, day, doc = ops_data._today_cache
    ops_data._today_cache = (stamp - ops_data.CACHE_TTL - 1, day, doc)
    assert ops_data._live_today(DAY_START) is not first, "the TTL was ignored"


def test_a_truncated_runs_page_is_admitted_rather_than_undercounted(monkeypatch):
    """Overflow must not read as a quiet zero.

    Measured 2026-10-18: page 1 spanned 31 hours against `total_count` 139,
    with 51 rows inside the IST day two-thirds through it. Under 2x headroom,
    and the failure mode is a SILENT UNDERCOUNT -- which is this module's own
    bug class, one layer up.
    """
    # Every page full, and every row inside the day: the pager can never reach
    # back past `since`, so it must stop at MAX_PAGES and say so.
    full = [_run(i, "agent-work.yml", "success", "2026-10-18T09:00:00Z")
            for i in range(ops_today.PER_PAGE)]
    urls = _stub(monkeypatch, [], full)
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert got["truncated"] is True
    runs_urls = [u for u in urls if "/actions/runs" in u]
    assert len(runs_urls) == ops_today.MAX_PAGES, runs_urls
    assert "page=2" in runs_urls[1]


def test_an_ordinary_day_still_costs_one_request_per_endpoint(monkeypatch):
    """The pager must not turn the common case into MAX_PAGES requests.

    A short page means the endpoint ran out; there is nothing unfetched.
    """
    urls = _stub(monkeypatch, [_pr(1, "2026-10-18T09:00:00Z")],
                 [_run(1, "agent-work.yml", "failure", _inside_today_utc())])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert got["truncated"] is False
    assert len(urls) == 2, urls


def _workflow_files(wdir: Path | None = None) -> set[str]:
    """Every workflow file on disk, BOTH extensions.

    GitHub honours `.yaml` exactly as it honours `.yml`, and
    `scripts/verify_workflows.py:708` already globs both
    (`sorted(list(wdir.glob("*.yml")) + list(wdir.glob("*.yaml")))`). The
    exhaustiveness assertion below globbed `*.yml` alone, so the two checks
    disagreed about what a workflow is -- and the disagreement was silent in
    the direction that matters.

    DEMONSTRATED BOTH WAYS, 2026-10-20. Drop a scheduled `zz.yaml` into
    `.github/workflows/` and it is neither in `LOOP_WORKFLOWS` nor in
    `NOT_LOOP_WORKFLOWS`; the `on_disk - declared` assertion cannot see it, so
    a dead scheduled leg leaves the Failed-today tile reading 0 with no test
    red anywhere -- the 2026-10-18 screen, reached through a file extension.
    The converse also passed: declare `zz.yaml` in `LOOP_WORKFLOWS` with no
    such file on disk and `declared - on_disk` stays empty, so the guard
    against a stale declaration is blind to the same half of the namespace.

    All 15 workflows are `.yml` today, which is why this cost nothing yet. A
    helper rather than a wider glob inline, so the rule itself is testable:
    `test_the_workflow_scan_sees_a_yaml_as_well_as_a_yml` drives it over a
    temporary directory, because the real one cannot be made to hold a
    counter-example without committing a workflow.
    """
    wdir = wdir if wdir is not None else ROOT / ".github" / "workflows"
    return {p.name for p in wdir.iterdir()
            if p.is_file() and p.suffix in (".yml", ".yaml")}


def test_the_workflow_scan_sees_a_yaml_as_well_as_a_yml(tmp_path):
    """The glob, over a directory built to contain the counter-example.

    `*.yml` alone is a one-character edit away and the exhaustiveness test
    above cannot notice it, because the repository has no `.yaml` workflow to
    be missed. So the rule is asserted here, against a directory that does.
    """
    (tmp_path / "agent-work.yml").write_text("on: {schedule: []}")
    (tmp_path / "zz.yaml").write_text("on: {schedule: []}")
    (tmp_path / "README.md").write_text("not a workflow")
    (tmp_path / "nested").mkdir()
    assert _workflow_files(tmp_path) == {"agent-work.yml", "zz.yaml"}


def test_every_workflow_is_either_a_loop_leg_or_declared_not_one():
    """The two sets must be exhaustive over `.github/workflows/`.

    `LOOP_WORKFLOWS` used to mirror `report_loop_outcomes.WORKFLOW`, which is
    itself a partial list -- so the mirror inherited six blind spots. The worst
    was `agent-steward.yml`, whose stated job is to notice that the pipeline
    has stopped: its own failure was invisible on the tile built to show the
    pipeline stopping.

    This is the sync guard. A new workflow fails here instead of silently never
    being counted. It lives in the tests because the app image ships `src/` and
    three files, not `.github/`.
    """
    on_disk = _workflow_files()
    declared = set(ops_today.LOOP_WORKFLOWS) | set(ops_today.NOT_LOOP_WORKFLOWS)
    assert on_disk - declared == set(), \
        "a workflow is neither a loop leg nor declared not one"
    assert declared - on_disk == set(), "a declared workflow no longer exists"
    assert not set(ops_today.LOOP_WORKFLOWS) & set(ops_today.NOT_LOOP_WORKFLOWS)


def test_the_steward_counts_as_a_loop_leg(monkeypatch):
    """Named on its own, because it is the one that makes the rule matter."""
    _stub(monkeypatch, [],
          [_run(1, "agent-steward.yml", "failure", "2026-10-18T09:00:00Z")])
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert [f["run"] for f in got["failed"]] == [1]


def test_the_fallback_alert_does_not_render_a_literal_question_mark():
    """Snapshot rows are CYCLES and carry no `workflow` key.

    The live wording joined `f.get("workflow") or "?"` over them, so the
    fallback -- the path taken whenever the API is unreachable, i.e. exactly
    when someone is reading this page to find out what broke -- printed "?" to
    the reader.
    """
    loop = {"ok": True, "today_live": False, "today_failed": [{"outcome": "failed"}],
            "rows": [], "outcomes": {}, "attribution": {}, "days": [],
            "latest": None, "today": [], "today_shipped": []}
    alerts = ops_data._alerts(loop=loop, issues={"rows": []},
                              agents={}, app={}, ages={})
    failed = [a for a in alerts if "failed today" in a["title"]]
    assert failed, "the fallback alert did not fire"
    assert "?" not in failed[0]["detail"]
    assert "cycle" in failed[0]["title"]


def test_the_ops_page_does_not_block_the_event_loop(monkeypatch):
    """`snapshot()` makes up to three blocking urllib calls at 4s each.

    Awaited inline in a coroutine that is up to 12s of the whole single-process
    app serving nobody, not 12s of one request.
    """
    import asyncio
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    # NOT the thread NAME. Under TestClient the loop does not necessarily run
    # on MainThread, so a name comparison passes whether or not the call was
    # offloaded -- the first version of this test asserted exactly that and the
    # mutation harness reported MISSED. The question is not which thread ran
    # it, it is whether that thread had a live event loop to block.
    loop_thread = {}
    real = ops_data.snapshot

    def spy(*a, **k):
        try:
            asyncio.get_running_loop()
            loop_thread["on_the_loop"] = True
        except RuntimeError:
            loop_thread["on_the_loop"] = False
        return real(*a, **k)

    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(ops_data, "snapshot", spy)
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200
    assert loop_thread["on_the_loop"] is False, \
        "snapshot() made its blocking calls on a thread with a running loop"


def test_the_page_tells_the_drill_down_which_shape_the_rows_are(monkeypatch):
    """`today_live` picks the row renderer; nothing noticed if it was wrong.

    Live rows are PRs and workflow runs; fallback rows are attributed cycles.
    Hardcode the flag and the drill-down renders PR dicts through the cycle
    template -- a panel of blanks, with no error anywhere.
    """
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    _stub(monkeypatch, [_pr(1, "2026-10-18T09:00:00Z")], [])
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    body = TestClient(app).get("/admin/ops", auth=("admin", pw)).text
    assert '"today_live": true' in body.lower().replace(" :", ":"), \
        "the live flag did not reach the page"


# --------------------------------------------------------------------------- #
# Round 2 QA (2026-10-20). Three ship-blocking findings, and the first is the
# one this block exists for: `truncated` was computed in `ops_today` and read
# NOWHERE -- not in `ops_data`, not in `routes/admin.py`, not in the template --
# while THREE places said the page showed it, one of them the ARCHITECTURE
# decision row. The flag's existing test asserted only the dict key, so forcing
# it True left all 706 tests green.
#
# Every test below reads the RENDERED PAGE, because every one of these findings
# is about what a reader is told.
# --------------------------------------------------------------------------- #

def _ops_body(monkeypatch, prs, runs, *, pages=1):
    """The real /admin/ops page over a stubbed GitHub."""
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" not in url:
            raise urllib.error.URLError("no raw fetches in this test")
        if "/pulls" in url:
            return _Resp(prs)
        return _Resp({"workflow_runs": runs})

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    ops_data._today_cache = None
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def _inside_today_utc() -> str:
    """A UTC stamp inside the CURRENT IST day.

    The route calls `snapshot()` with no `now`, so a hardcoded date falls
    outside the window and the rows are filtered out before the pager is ever
    reached -- which is how my first version of this test passed while
    asserting nothing. Derived, not written down.
    """
    now = datetime.now(timezone.utc)
    ist = now + timedelta(hours=5, minutes=30)
    day_start = (ist.replace(hour=0, minute=0, second=0, microsecond=0)
                 - timedelta(hours=5, minutes=30))
    return (day_start + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_with(*, prs, runs):
    """The real `fetch_today` over a stubbed `_get`, no monkeypatch needed."""
    def _get(url, *, timeout, token=None):
        return prs if "/pulls" in url else {"workflow_runs": runs}
    orig = ops_today._get
    ops_today._get = _get
    try:
        return ops_today.fetch_today("x/y", DAY_START, timeout=1)
    finally:
        ops_today._get = orig

def test_a_truncated_read_renders_an_at_least_on_the_tiles(monkeypatch):
    """S-1, through the page. `≥` on the number and "at least" on the badge."""
    stamp = _inside_today_utc()
    full = [_run(1000 + i, "agent-work.yml", "failure", stamp)
            for i in range(ops_today.PER_PAGE)]
    body = _ops_body(monkeypatch, [], full)

    # SCOPED TO THE TILE, and that is the finding. These assertions used to be
    # `"≥" in body` and `"live, at least" in body` -- whole-PAGE substrings, so
    # they could be satisfied by a `≥` on any other tile or anywhere in the
    # markup. The PR comment that claimed to have fixed this quoted the scoped
    # form, but the scoped form lived on `feat/ops-token-window` (#419) and was
    # never an ancestor of this branch; checked with `git merge-base
    # --is-ancestor`, 2026-10-20.
    #
    # Measured consequence: `"shipped_truncated": pr_more` -> `pr_more or
    # runs_more` left 772 tests GREEN while the page rendered
    # `<span class="num c-shipped">≥0</span>` off a complete, empty pulls read
    # and printed "live, at least" twice. The marker appeared on the wrong tile
    # and nothing noticed.
    assert 'class="num c-failed">≥' in body, (
        "the capped FAILED count renders as a flat number, so the page states "
        "a total it cannot stand behind"
    )
    assert 'class="num c-shipped">≥' not in body, (
        "the floor marker reached the SHIPPED tile, whose read was complete -- "
        "a truncation flag is leaking across tiles"
    )
    assert body.count("live, at least") == 1, (
        f'the "at least" badge appears {body.count("live, at least")} times; '
        "exactly one tile was truncated, so exactly one badge may say so"
    )


def test_an_uncapped_read_claims_no_floor(monkeypatch):
    """The marker must mean something, so it must be absent when exact."""
    body = _ops_body(
        monkeypatch, [],
        [_run(1, "agent-work.yml", "failure", _inside_today_utc())])
    assert "live, at least" not in body
    assert "≥" not in body.split('data-drill="backlog"')[0], (
        "a complete read is marked as a floor"
    )


@pytest.mark.parametrize("conclusion", [
    "startup_failure",      # invalid YAML, missing secret, runner never started
    "action_required",
    "stale",
    "some_value_github_adds_in_2027",
])
def test_any_conclusion_that_is_not_a_success_counts_as_a_failure(conclusion):
    """S-2. The allow-list of FAILURES was the wrong way round.

    `FAILED_CONCLUSIONS = ("failure", "timed_out", "cancelled")` omitted
    `startup_failure` -- a leg that produced nothing at all. A bad `on:` block
    landing in `agent-steward.yml` would kill the loop for days while this tile
    read `0 Failed today, live` and raised no alert: the 2026-10-18 screen,
    through the one conclusion value nobody wrote down.

    This module already had the right reasoning one screen up -- `LOOP_WORKFLOWS`
    is "every workflow except the PR gates ... so the list grows by default
    rather than by remembering" -- and it was not carried across.
    """
    runs = [_run(1, "agent-work.yml", conclusion, "2026-10-18T09:00:00Z")]
    doc = _fetch_with(prs=[], runs=runs)
    assert len(doc["failed"]) == 1, (
        f"a run concluding {conclusion!r} produced nothing at all and is not "
        f"counted as a failure: {doc['failed']}"
    )
    assert doc["failed"][0]["conclusion"] == conclusion


@pytest.mark.parametrize("conclusion", ["success", "skipped", "neutral"])
def test_a_successful_conclusion_is_not_a_failure(conclusion):
    """The converse, so the set cannot be widened into meaninglessness."""
    assert conclusion in ops_today.SUCCEEDED_CONCLUSIONS


def test_a_run_still_in_flight_is_not_counted_as_failed():
    """`conclusion is None` means not finished, which is not the same as badly."""
    assert None not in ops_today.SUCCEEDED_CONCLUSIONS, (
        "None must be excluded by the caller explicitly, not by sitting in the "
        "success set where it would read as 'this run succeeded'"
    )


def test_the_measurements_fetch_does_not_500_the_page_on_a_truncated_read(monkeypatch):
    """S-3. `_fetch` kept the four-type tuple after the live callers were widened.

    `http.client.IncompleteRead` inherits from HTTPException and is none of
    `URLError`/`OSError`/`ValueError`, and in the container there is no
    `measurements/` directory, so EVERY file on a cold render comes through this
    HTTPS path -- far more traffic than the two API calls the fix hardened.
    Reproduced by QA round 2 as `GET /admin/ops -> 500`, where `_fetch`'s own
    docstring promises "None on any failure, with a log line".
    """
    import http.client

    def boom(*a, **k):
        raise http.client.IncompleteRead(b"27 bytes")

    monkeypatch.setattr(ops_data.urllib.request, "urlopen", boom)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "measurements_dir", lambda: None)
    ops_data._cache.clear()
    snap = ops_data.snapshot()
    assert snap["loop"]["ok"] is False, "a blanked panel, not an exception"


def test_a_programming_error_in_the_live_path_raises_an_alert(monkeypatch):
    """G-13. The bare `except Exception` is right; the silence was not.

    QA round 2 drove `fetch_today` into a plain `TypeError` and the page
    degraded to three tiles reading `0 ... as of 4d ago`, forever, with a
    WARNING in Cloud Run as the only signal -- within an "as of" footer of the
    2026-10-18 screen this panel exists to prevent. "The page survives" and
    "somebody is told" are different properties and only the first was built.
    The backlog panel's identical alert already existed one screen over.
    """
    def boom(*a, **k):
        raise TypeError("a programming error, not a network one")

    monkeypatch.setattr(ops_today, "fetch_today", boom)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    ops_data._today_cache = None
    snap = ops_data.snapshot()
    assert snap["loop"]["fell_back"] is True
    titles = [a["title"] for a in snap["alerts"]]
    assert any("delivery tiles fell back" in t for t in titles), (
        f"the tiles fell back to a stale snapshot and no alert said so: {titles}"
    )


# --------------------------------------------------------------------------- #
# QA round 3 on #418 (2026-10-20). Twelve guard gaps, each demonstrated by a
# hand-built mutant that survived the whole suite AND the 179-row sweep. The
# shape they share is worth stating once, because it is the thing to look for
# in the next round too:
#
#   EVERY ONE OF THEM PINNED A TRANSPORT AND NOT A USE.
#
# `fetch_today` was tested against a day start handed to it already correct, so
# nothing tested the line that COMPUTES the day start. `truncated` was tested
# as a dict key, so nothing tested the badge a human reads. `today_live` was
# tested as a serialised JSON field, so nothing tested the branch that picks a
# row renderer from it. In each case the value was proved to travel and never
# proved to arrive anywhere that matters.
#
# So each test below names the WRONG OUTPUT it forbids, and reads the thing the
# reader or the next function actually consumes.
# --------------------------------------------------------------------------- #

def _stub_paged(monkeypatch, *, pulls_pages=((),), runs_pages=((),)):
    """Serve a DIFFERENT payload per `page=` on each endpoint.

    `_stub` above answers every page with the same rows, which is enough to
    make the pager spend requests but cannot express anything that changes
    between two fetches -- and a page boundary is precisely where two fetches
    see different data. Pages past the end come back empty, which is what the
    endpoint does.
    """
    urls: list[str] = []

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        urls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        pages = pulls_pages if "/pulls" in url else runs_pages
        rows = list(pages[page - 1]) if page <= len(pages) else []
        return _Resp(rows if "/pulls" in url else {"workflow_runs": rows})

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    return urls


def _page(monkeypatch, *, live_today=False, live_backlog=False,
          prs=(), runs=(), backlog_rows=()):
    """The real /admin/ops page with BOTH live switches set explicitly.

    `_ops_body` above renders only the live-delivery case. The tile badges have
    to be read on both sides of both switches -- "says live when live" is half
    a guard, and the half that cannot catch a hardcoded flag.
    """
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/pulls" in url:
            return _Resp(list(prs))
        if "/actions/runs" in url:
            return _Resp({"workflow_runs": list(runs)})
        # The committed measurements come off disk in a checkout, so nothing
        # else should be reaching the network at all.
        raise urllib.error.URLError(f"not stubbed: {url}")

    monkeypatch.setattr(ops_today.urllib.request, "urlopen", fake)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", live_today)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", live_backlog)
    if live_backlog:
        # The backlog's own live path, shaped like issues.json. Stubbed at the
        # loader rather than at the socket because this file is about the
        # delivery tiles; `test_ops_backlog_live.py` owns that transport.
        monkeypatch.setattr(
            ops_data, "_live_issues",
            lambda objective: {"generated_at": None, "objective": objective,
                               "rows": list(backlog_rows)})
    ops_data._today_cache = None
    ops_data._live_cache = None
    ops_data._cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def _tile(body: str, drill: str) -> str:
    """The markup of ONE tile button.

    Scoped, because every assertion here is about a word that also appears in
    a neighbouring tile: "live" is on the backlog tile too, and "as of" is on
    four of them. An unscoped `in body` assertion passes while the tile under
    test says the opposite.
    """
    start = body.index(f'data-drill="{drill}"')
    return body[start:body.index("</button>", start)]


# --------------------------------------------------------------------------- #
# G1. The IST day boundary, guarded where it is COMPUTED rather than where it
# is consumed. THE HIGHEST-VALUE GAP OF THE ROUND, because the mutant is the
# original defect verbatim: the ARCHITECTURE row calls it "the boundary bug
# found while building it" and records its cost as "2 failures where the
# correct bound returned 5".
#
# Two tests existed and neither could catch it. Both hand `fetch_today` the
# already-correct `DAY_START`, so both pin the callee -- `fetch_today` really
# does normalise and really does bound the query by the right UTC date -- and
# nothing pinned the one line in `snapshot()` that decides WHICH day start the
# callee is handed. Change `now_ist` to `now` there and `fetch_today` is given
# 00:00 UTC, dutifully converts it to 00:00 UTC, and reports the wrong day
# correctly.
# --------------------------------------------------------------------------- #

def test_the_page_computes_the_day_start_in_ist_not_in_utc(monkeypatch):
    """`snapshot()` must bound the live read at IST midnight, not UTC midnight.

    00:00 IST is 18:30 UTC on the PREVIOUS day. Computing it from `now` rather
    than `now_ist` shifts the window by 5h30m and drops every run between
    00:00 and 05:30 IST -- which is when the loop is scheduled ("04:30 IST,
    after the rolling cap resets"). Three clocks, chosen so that no single
    off-by-one passes all three:

      06:00 UTC  mid-IST-day, UTC and IST dates AGREE
      19:00 UTC  the IST day has rolled over and the UTC day has not
      18:29 UTC  one minute before the IST rollover, the hardest case
    """
    seen: list[datetime] = []

    def spy(repo, day_start, *, timeout, token=None):
        seen.append(day_start.astimezone(timezone.utc))
        return {"since": "", "shipped": [], "failed": [], "truncated": False,
                "shipped_truncated": False, "failed_truncated": False}

    monkeypatch.setattr(ops_today, "fetch_today", spy)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    for now, expected in (
        (datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc),
         datetime(2026, 10, 17, 18, 30, tzinfo=timezone.utc)),
        (datetime(2026, 10, 17, 19, 0, tzinfo=timezone.utc),
         datetime(2026, 10, 17, 18, 30, tzinfo=timezone.utc)),
        (datetime(2026, 10, 17, 18, 29, tzinfo=timezone.utc),
         datetime(2026, 10, 16, 18, 30, tzinfo=timezone.utc)),
    ):
        seen.clear()
        # The two clocks above describe the SAME IST day, so the 300s cache
        # would serve the second from the first and `seen` would stay empty.
        ops_data._today_cache = None
        ops_data.snapshot(now=now)
        assert seen == [expected], (
            f"at {now.isoformat()} the live read was bounded at "
            f"{seen[0].isoformat() if seen else 'nothing'}, not at IST midnight "
            f"({expected.isoformat()})"
        )


def test_the_day_start_handed_to_the_api_is_the_one_the_page_prints(monkeypatch):
    """The tile says "today, {{ ops.today_ist }}" -- same day or it is lying.

    The bound and the label are computed from the same `now_ist` two lines
    apart, so they can be made to disagree by editing either. A reader cannot
    see the bound; they can only see the date beside the count, which is what
    makes a mismatch invisible without this.
    """
    seen: list[str] = []

    def spy(repo, day_start, *, timeout, token=None):
        seen.append(day_start.astimezone(IST).strftime("%Y-%m-%d"))
        return {"since": "", "shipped": [], "failed": [], "truncated": False,
                "shipped_truncated": False, "failed_truncated": False}

    monkeypatch.setattr(ops_today, "fetch_today", spy)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    ops_data._today_cache = None
    snap = ops_data.snapshot(now=datetime(2026, 10, 17, 19, 0, tzinfo=timezone.utc))
    assert seen == [snap["today_ist"]] == ["2026-10-18"]


# --------------------------------------------------------------------------- #
# G2. The kill switch. `LIVE_TODAY` is the thing an operator reaches for when
# the budget is spent or the environment has no egress, and dropping the
# `if LIVE_TODAY` guard left every test green -- including the ones that set
# the switch, because they set it to False and then only asserted that the
# page still returned 200, which it does either way while spending the budget.
# --------------------------------------------------------------------------- #

def test_pinning_the_tiles_to_the_snapshot_makes_no_api_call_and_is_not_a_fallback(
        monkeypatch):
    """`OPS_LIVE_TODAY=0` must mean no request, and must not raise the alert.

    Named to match its backlog twin in `test_ops_backlog_live.py`, because the
    two switches have the same shape and only one of them had this test.

    The second half is the half that is easy to get wrong: an environment
    deliberately configured without egress is NOT a failed live call, so the
    "fell back to the committed snapshot" alert must stay silent. Firing it
    would put an amber row on every render forever, which is how a reader
    learns to skip the alert strip.
    """
    calls: list[tuple] = []

    def spy(*a, **k):
        calls.append((a, k))
        return {"since": "", "shipped": [{"pr": 1}], "failed": [{"run": 1}],
                "truncated": False, "shipped_truncated": False,
                "failed_truncated": False}

    monkeypatch.setattr(ops_today, "fetch_today", spy)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    ops_data._today_cache = None
    snap = ops_data.snapshot(now=datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc))
    assert calls == [], "the switch is off and the live read happened anyway"
    assert snap["loop"]["today_live"] is False
    assert snap["loop"]["fell_back"] is False, \
        "a switched-off panel was reported as a failed one"
    titles = [a["title"] for a in snap["alerts"]]
    assert not [t for t in titles if "delivery tiles fell back" in t], titles


# --------------------------------------------------------------------------- #
# G4. The three tile disclosure badges. The only page-level assertion the suite
# had was `'"today_live": true' in body` -- the serialised JSON, i.e. the
# transport again. Nothing read the markup, so all three of these survived:
# forcing `live` onto Shipped today, deleting "agent-work only," from the
# Failed-today fallback, and deleting the Filed-today badge outright.
#
# The badge IS the fix. On 2026-10-18 the page read 0/0/0 and no reader could
# tell a quiet day from an unreachable API, so a count without its provenance
# is the defect, not a decoration on the fix for it.
# --------------------------------------------------------------------------- #

def test_the_shipped_tile_says_live_only_when_it_is_live(monkeypatch):
    """Both directions, because one direction cannot catch a hardcoded badge."""
    live = _tile(_page(monkeypatch, live_today=True,
                       prs=[_pr(1, _inside_today_utc())]), "today-shipped")
    assert "live" in live, "a live read is not labelled live"
    assert "as of" not in live, "a live read is labelled with an age"

    snap = _tile(_page(monkeypatch, live_today=False), "today-shipped")
    assert "as of" in snap, "the fallback does not say how old it is"
    assert "live" not in snap, (
        "the Shipped tile is badged `live` while reading the committed "
        "snapshot -- the exact claim the 2026-10-18 screen made"
    )


def test_the_failed_tile_fallback_says_it_counts_agent_work_only(monkeypatch):
    """The scope caveat, which is the half freshness cannot fix.

    `collect_loop_measurements.py:109` is `WORKFLOW_NAME = "agent-work"`, so
    the snapshot holds agent-work cycles and nothing else. Every failure of
    2026-10-18 was `agent-measure` and could not have appeared on this tile at
    ANY freshness. "as of 4h ago" tells the reader the number is old; it does
    not tell them the number is also answering a narrower question. Both or
    the tile still misleads.
    """
    snap = _tile(_page(monkeypatch, live_today=False), "today-failed")
    assert "agent-work only, as of" in snap, (
        "the fallback tile states a loop-wide failure count from an "
        "agent-work-only source without saying so"
    )
    live = _tile(_page(monkeypatch, live_today=True,
                       runs=[_run(1, "agent-measure.yml", "failure",
                                  _inside_today_utc())]), "today-failed")
    assert "agent-work only" not in live, \
        "a live read spans every loop leg and must not carry the caveat"


def test_the_filed_tile_carries_its_own_source_badge(monkeypatch):
    """"Filed today" reads the BACKLOG, which has its own live flag and its own
    failure mode -- so it needs its own badge, and the badge needs a test.

    Deleting it entirely left the suite green. The tile then renders a count
    with no provenance at all, which is strictly worse than the other two
    getting it wrong: at least a wrong badge is a claim a reader can check.
    """
    snap = _tile(_page(monkeypatch, live_backlog=False), "today-filed")
    assert "as of" in snap, "the Filed-today tile has no source badge"
    assert "live" not in snap

    live = _tile(_page(monkeypatch, live_backlog=True,
                       backlog_rows=[]), "today-filed")
    assert "live" in live, "a live backlog is not labelled live"
    assert "as of" not in live


# --------------------------------------------------------------------------- #
# G5. The drill-down's USE of `today_live`, and of a PR's own number.
#
# WHY THESE ARE SOURCE ASSERTIONS. The decision lives in the page's JavaScript
# and there is no JS runtime in this suite (`playwright` drives two
# `scripts/verify_*.py` gates and exits 2 when absent, which is not a pass).
# The alternative was to keep asserting on the serialised flag, and that is the
# assertion the reviewer's mutant walked straight past: `today_live` arrived in
# the page correctly and was then thrown away one line later.
#
# The existing test's own docstring describes the failure it cannot catch --
# "Hardcode the flag and the drill-down renders PR dicts through the cycle
# template -- a panel of blanks, with no error anywhere." A blank panel with no
# console error is not something a status-code assertion can ever see.
# --------------------------------------------------------------------------- #

def test_the_drill_down_picks_its_row_renderer_from_the_live_flag(monkeypatch):
    """`"pr"`/`"run"` when live, `"cycle"` when not -- chosen, not hardcoded.

    Live rows are PRs (`pr`, `title`, `merged_at`) and workflow runs (`run`,
    `workflow`, `conclusion`); fallback rows are attributed cycles (`issue`,
    `outcome`, `minutes`, `trigger`). The field sets do not overlap, so the
    wrong renderer produces a sheet of empty chips and blank links rather than
    an error.
    """
    body = _page(monkeypatch, live_today=True, prs=[_pr(1, _inside_today_utc())])
    tiles = body[body.index("var TILES = {"):body.index('"backlog":')]
    assert 'D.today_live ? "pr" : "cycle"' in tiles, (
        "the shipped drill-down does not choose its renderer from today_live"
    )
    assert 'D.today_live ? "run" : "cycle"' in tiles, (
        "the failed drill-down does not choose its renderer from today_live"
    )
    assert 'D.filed_live ?' in tiles, (
        "the filed drill-down borrows the delivery flag instead of the "
        "backlog's own"
    )


def test_the_drill_down_links_a_merged_pr_by_its_own_number(monkeypatch):
    """One hardcoded number sends every row of the sheet to the same PR.

    The sheet exists so a reader can go from "3 shipped" to the three diffs.
    A constant in the href keeps the count right, keeps the titles right, and
    quietly points all three links at one pull request -- a wrong destination
    reads as the page working.
    """
    body = _page(monkeypatch, live_today=True, prs=[_pr(1, _inside_today_utc())])
    branch = body[body.index('if (kind === "pr") {'):
                  body.index('if (kind === "run") {')]
    assert '"/pull/" + r.pr' in branch, \
        "the PR diff link is not built from the row's own number"
    assert not re.search(r'/pull/\d', branch), \
        "a PR number is hardcoded into the drill-down link"
    assert "r.pr" in branch and "r.title" in branch


# --------------------------------------------------------------------------- #
# G6. `_loop_view(None, ..., None)` -- no snapshot AND no API. Uncovered: one
# existing test covers no-snapshot-with-API and another covers
# snapshot-with-no-API, and the corner where both are missing is the one that
# runs during a GitHub outage, i.e. the worst moment available.
# --------------------------------------------------------------------------- #

def test_no_snapshot_and_no_api_is_an_absence_not_three_live_zeroes():
    """`"today_live": live_today is not None` -> `True` is one character.

    Its output is three tiles reading `0 ... live` during a total outage: a
    confident claim that nothing shipped, nothing was filed and nothing failed,
    sourced from nothing at all. That is the 2026-10-18 screen with a worse
    badge on it.
    """
    v = ops_data._loop_view(None, "2026-10-18", None)
    assert v["ok"] is False
    assert v["today_live"] is False, (
        "with no snapshot and no API the tiles claim to be live"
    )
    assert v["today_shipped"] == [] and v["today_failed"] == []
    assert v["today_truncated"] is False
    assert v["shipped_truncated"] is False and v["failed_truncated"] is False
    # Every key the ok path returns, or the template raises UndefinedError and
    # 500s the page -- reproduced 2026-10-18 at admin_ops.html:1161.
    full = ops_data._loop_view({"rows": []}, "2026-10-18", None)
    assert set(v) == set(full), sorted(set(full) ^ set(v))


# --------------------------------------------------------------------------- #
# G7. The fallback alert's substance. The existing guard asserts only that the
# detail holds no "?" and that the title says "cycle", so the whole explanatory
# sentence can be deleted and both assertions still hold.
# --------------------------------------------------------------------------- #

def test_the_fallback_alert_says_the_count_is_stale_and_agent_work_only():
    """Three facts, each load-bearing, none of them implied by the other two.

    This alert fires on the path taken when the API is unreachable, which is
    exactly when someone is reading the page to find out what broke. It has to
    say (a) where the number came from, (b) that it is not live, and (c) that
    it counts a narrower thing than the live tile would -- because a reader who
    knows only that it is old will assume a fresh collection would have shown
    the `agent-measure` failures, and it would not have.
    """
    live_free = {"ok": True, "today_live": False,
                 "today_failed": [{"outcome": "failed"}],
                 "rows": [], "outcomes": {}, "attribution": {}, "days": [],
                 "latest": None, "today": [], "today_shipped": []}
    alerts = ops_data._alerts(loop=live_free, issues={"rows": []},
                              agents={}, app={}, ages={})
    hit = next(a for a in alerts if "failed today" in a["title"])
    detail = hit["detail"]
    assert "committed snapshot" in detail, detail
    assert "not live" in detail, detail
    assert "agent-work only" in detail, detail
    assert "out of date" in detail, detail


# --------------------------------------------------------------------------- #
# G8. `filed_live`. Added in the same commit as `today_live` with the comment
# "the backlog has its own live flag (#353) and its own failure mode, so
# 'Filed today' cannot borrow the delivery one" -- and then not tested, so
# hardcoding it True left the suite green and badged a stale snapshot `live`.
# --------------------------------------------------------------------------- #

def test_the_filed_drill_down_flag_follows_the_backlog_not_the_delivery_read(
        monkeypatch):
    """The two live sources fail independently, so one flag cannot serve both.

    `_live_issues` and `_live_today` keep separate caches for exactly this
    reason -- a 403 on one must not blank the other -- so a shared flag would
    put the label of whichever panel happened to succeed onto both.
    """
    both_off = _page(monkeypatch, live_today=False, live_backlog=False)
    assert '"filed_live": false' in both_off, \
        "the Filed-today drill-down claims live off a committed snapshot"
    assert '"today_live": false' in both_off

    # The discriminating case: delivery live, backlog NOT. A borrowed flag
    # reads True here.
    delivery_only = _page(monkeypatch, live_today=True, live_backlog=False,
                          prs=[_pr(1, _inside_today_utc())])
    assert '"today_live": true' in delivery_only
    assert '"filed_live": false' in delivery_only, \
        "Filed today borrowed the delivery panel's live flag"

    backlog_only = _page(monkeypatch, live_today=False, live_backlog=True)
    assert '"filed_live": true' in backlog_only
    assert '"today_live": false' in backlog_only


# --------------------------------------------------------------------------- #
# G9. The budget and robustness constants. Both of `MAX_PAGES` and `PER_PAGE`
# could be changed to anything without a test failing, because every existing
# assertion was written in terms of the constant it was meant to be checking.
# `len(runs_urls) == ops_today.MAX_PAGES` is true of MAX_PAGES = 99.
# --------------------------------------------------------------------------- #

def test_a_pathological_day_is_capped_at_three_pages_per_endpoint(monkeypatch):
    """The worst case, in LITERAL requests, against the 60/hour ceiling.

    Three per endpoint and six per cache miss. With `ops_data`'s one backlog
    request that is 7 per render, and at the 300 s cache TTL a reader holding
    refresh costs 84/hour against a budget of 60 shared with every other
    tenant on this egress IP -- see the COST paragraph in `ops_today`, which
    this number is deliberately duplicated from so that raising the cap breaks
    something.

    Every page full and every row inside the day, so neither stop rule can
    fire and only the cap can end it.
    """
    stamp = "2026-10-18T09:00:00Z"
    full_prs = [_pr(1000 + i, stamp) for i in range(ops_today.PER_PAGE)]
    full_runs = [_run(2000 + i, "agent-work.yml", "failure", stamp)
                 for i in range(ops_today.PER_PAGE)]
    urls = _stub(monkeypatch, full_prs, full_runs)
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    pulls_urls = [u for u in urls if "/pulls" in u]
    runs_urls = [u for u in urls if "/actions/runs" in u]
    assert len(pulls_urls) == 3, f"the pulls read spent {len(pulls_urls)}"
    assert len(runs_urls) == 3, f"the runs read spent {len(runs_urls)}"
    assert len(urls) == 6, urls
    assert got["shipped_truncated"] is True and got["failed_truncated"] is True


def test_each_page_asks_for_a_hundred_rows(monkeypatch):
    """`per_page` is half of what the cap is worth.

    At 30 the same three pages cover 90 rows instead of 300, so a day the
    pager would have read completely becomes `truncated` -- and the tiles drop
    to "at least N" on an ordinary busy day. 100 is the endpoint's maximum, so
    this is not a tunable: anything lower buys nothing and costs coverage.
    """
    urls = _stub(monkeypatch, [], [])
    ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert urls, "no request was made"
    assert all("per_page=100" in u for u in urls), urls


def test_the_pager_stops_at_the_day_boundary_not_only_on_a_short_page(monkeypatch):
    """The `since` rule, which no test had ever been the reason a pager stopped.

    `test_an_ordinary_day_still_costs_one_request_per_endpoint` stops on the
    short-page rule with one row, and the truncated test fills every page with
    rows inside the day so it never reaches back past `since` at all. So the
    boundary rule -- the one the pager's docstring is mostly about -- could be
    deleted and the suite would notice nothing but a larger bill.

    A FULL page whose oldest row is older than the day start is the only shape
    that isolates it: the short-page rule cannot fire, so stopping proves the
    boundary rule did.
    """
    inside = "2026-10-18T09:00:00Z"
    before = "2026-10-17T18:00:00Z"          # 30 min before 00:00 IST
    page = [_run(3000 + i, "agent-work.yml", "failure", inside)
            for i in range(ops_today.PER_PAGE - 1)]
    page.append(_run(3999, "agent-work.yml", "failure", before))
    assert len(page) == ops_today.PER_PAGE, "the page must be FULL to isolate the rule"
    urls = _stub(monkeypatch, [], page)
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    runs_urls = [u for u in urls if "/actions/runs" in u]
    assert len(runs_urls) == 1, (
        "a full page reaching back past the day start did not stop the pager, "
        f"which spent {len(runs_urls)} requests"
    )
    assert got["failed_truncated"] is False, \
        "the read was complete and was reported as a floor"
    assert len(got["failed"]) == ops_today.PER_PAGE - 1


@pytest.mark.parametrize("payload, where", [
    ({"message": "API rate limit exceeded"}, "/pulls"),
    ({"workflow_runs": {"message": "API rate limit exceeded"}}, "/actions/runs"),
])
def test_a_page_that_is_not_a_list_raises_rather_than_counting_as_empty(
        payload, where):
    """GitHub answers an error with an OBJECT, and `{}` has length 0.

    Accepting it silently is the failure mode of this whole module one level
    down: a 403 body treated as "no rows" renders `0 shipped, 0 failed` with a
    `live` badge, which is the 2026-10-18 screen with the worst possible label
    on it. Raising hands the caller its documented fallback -- the snapshot,
    labelled as the snapshot.
    """
    def _get(url, *, timeout, token=None):
        if where in url:
            return payload
        return [] if "/pulls" in url else {"workflow_runs": []}

    orig = ops_today._get
    ops_today._get = _get
    try:
        with pytest.raises(ValueError, match="did not return a list"):
            ops_today.fetch_today("x/y", DAY_START, timeout=1)
    finally:
        ops_today._get = orig


# --------------------------------------------------------------------------- #
# G11. Cross-page distinctness for `failed`. `shipped` dedupes by PR number
# with a comment explaining that the unit of the count is the PR; the runs list
# appended with no such enforcement, so the reasoning was written down for one
# list and not carried to its sibling.
# --------------------------------------------------------------------------- #

def test_a_run_repeated_across_a_page_boundary_is_counted_once(monkeypatch):
    """A run created BETWEEN two page fetches shifts every row one place later.

    `/actions/runs` is newest-first and the pager reads page 1 then page 2, so
    a run starting in that window pushes the last row of page 1 onto page 2 as
    well. Reproduced here deterministically: 150 failed runs, one created in
    the window, page 2 therefore served from index 99.

    151 rows, 150 distinct ids, run 3099 counted twice on the tile and listed
    twice in the drill-down. Low probability per render -- and the window is
    at its widest during the run storm that makes the pager page at all, which
    is the one time the tile is being read.
    """
    stamp = "2026-10-18T09:00:00Z"
    runs = [_run(3000 + i, "agent-work.yml", "failure", stamp) for i in range(150)]
    urls = _stub_paged(monkeypatch,
                       pulls_pages=([],),
                       runs_pages=(runs[:100], runs[99:]))
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert len([u for u in urls if "/actions/runs" in u]) == 2, "it did not page"
    ids = [f["run"] for f in got["failed"]]
    assert len(ids) == len(set(ids)), "a run appears twice in the drill-down"
    assert ids.count(3099) == 1, "the boundary run was double-counted"
    assert len(ids) == 150, f"the tile reads {len(ids)} for 150 failed runs"


def test_a_run_with_no_id_is_kept_rather_than_collapsed(monkeypatch):
    """Dedupe must not become a drop.

    `id` is always present in practice, so the obvious implementation keys on
    `r.get("id")` and silently collapses every id-less row into one. That
    trades a rare double-count for a systematic undercount, which is the wrong
    way round for this module: the whole file exists because an undercount read
    as a quiet zero.
    """
    runs = [{"path": ".github/workflows/agent-work.yml", "name": "agent-work",
             "conclusion": "failure", "created_at": "2026-10-18T09:00:00Z"}
            for _ in range(3)]
    _stub(monkeypatch, [], runs)
    got = ops_today.fetch_today("x/y", DAY_START, timeout=1)
    assert len(got["failed"]) == 3, got["failed"]


# --------------------------------------------------------------------------- #
# G12. The COST paragraph went stale the moment the pager landed: it still said
# "Two requests" and "36/hour worst case" while `MAX_PAGES = 3` on two
# endpoints makes the worst case 7 per render and 84/hour -- against the
# 60/hour ceiling the same paragraph reasons about. A docstring that argues
# from a number is a claim, and this one would have justified a self-inflicted
# 403 straight back into the 0/0/0 fallback the module exists to fix.
# --------------------------------------------------------------------------- #

def test_the_cost_paragraph_states_the_actual_worst_case():
    """Recomputed from `MAX_PAGES`, so raising the cap cannot leave prose behind.

    This is the only gate in the round whose subject is a comment, and it is
    here because the comment is load-bearing: it is where the next person
    decides whether another endpoint or another page is affordable. It was
    wrong by a factor of 2.3 and on the wrong side of the budget.
    """
    doc = ops_today.__doc__
    # DERIVED FROM BOTH CONSTANTS. This was `+ 1`, which pinned the paragraph at
    # 7/84 while the real worst case is 10/120 -- so the gate built to stop the
    # arithmetic drifting was HOLDING THE WRONG NUMBER IN PLACE, and correcting
    # the docstring turned this test red. `issue_backlog.fetch_live` pages to
    # `issue_backlog.MAX_PAGES`, so that is the term, not a literal.
    from astro_ai import issue_backlog
    per_render = ops_today.MAX_PAGES * 2 + issue_backlog.MAX_PAGES
    per_hour = per_render * 12                      # CACHE_TTL defaults to 300 s
    assert f"MAX_PAGES ({ops_today.MAX_PAGES})" in doc
    assert f"= {per_render} per render" in doc, (
        f"the COST paragraph does not state {per_render} requests per render"
    )
    assert f"= {per_hour}/hour" in doc, (
        f"the COST paragraph does not state the {per_hour}/hour worst case"
    )
    assert "60/hour" in doc, "the worst case is stated with nothing to compare it to"
    assert "Two requests" not in doc, "the pre-pager figure is still claimed"


# --------------------------------------------------------------------------- #
# G15. Symmetric key access in `_loop_view`. The ok path indexed
# `live_today["shipped"]` while the no-snapshot branch used `.get(..., [])` on
# the same dict, so the branch that runs on every ordinary render was the one
# that trusted -- and `_loop_view` is called from `snapshot()`, whose docstring
# is "Never raises", outside any try.
# --------------------------------------------------------------------------- #

def test_a_live_dict_missing_a_key_blanks_a_tile_rather_than_500ing_the_page():
    """A KeyError here is not a blank tile, it is a dead control room.

    `fetch_today` always returns both keys today, so this is a guard against a
    future shape change rather than a live defect -- which is exactly the
    reasoning the no-snapshot branch three screens up already applied, and did
    not carry here. The two branches disagreeing about how much they trust the
    same dict is the finding; which way they agree matters less than that they
    agree, and blanking a panel is what this module chooses everywhere else.
    """
    v = ops_data._loop_view(_SNAP, "2026-10-18", {"since": SINCE})
    assert v["today_live"] is True
    assert v["today_shipped"] == []
    assert v["today_failed"] == []


# --------------------------------------------------------------------------- #
# G2, second half. THE SUITE WAS NOT HERMETIC, and the docstring at the top of
# this file has said it was since the file was written.
#
# MEASURED 2026-10-20 with a `urlopen` spy: 16 real HTTPS requests to
# raw.githubusercontent.com per run, eight each from
# `test_llm_attribution.py::test_ops_says_it_is_reading_a_local_dev_store` and
# `::test_ops_names_the_bucket_when_one_is_configured`. Round 1 removed 2 of 18
# and recorded that the suite "no longer depends on a network it is documented
# not to use"; the claim was false and is now made true in `conftest.py`
# instead of restated. A GitHub outage could turn `pr-gates` red for reasons
# having nothing to do with the diff.
# --------------------------------------------------------------------------- #

def test_the_behaviour_suite_cannot_reach_the_network():
    """The guard, asserted rather than assumed -- the point of the whole gap.

    `.invalid` is a reserved TLD that never resolves, so `urlopen` raises
    `URLError` here whether or not the guard is installed. The assertion is
    therefore on the MESSAGE: it proves the request was refused by
    `conftest._no_outbound_http` and not by DNS, without emitting a packet in
    either case. Asserting on the exception type alone would pass on a laptop
    with no Wi-Fi and fail nowhere.
    """
    import urllib.request

    with pytest.raises(urllib.error.URLError) as exc:
        urllib.request.urlopen("https://raw.githubusercontent.invalid/x", timeout=1)
    assert "the behaviour suite is hermetic" in str(exc.value), (
        f"outbound HTTP is not blocked; this failed by itself: {exc.value}"
    )


def test_the_ops_page_survives_every_source_being_unreadable(monkeypatch):
    """A total GitHub outage must blank panels, never 500 the control room.

    FOUND BY MAKING THE SUITE HERMETIC, which is the argument for having done
    it: this branch had never once run under test, because the two tests that
    rendered this page with no `measurements/` directory were silently
    fetching the real files over the network and getting the ok path.

    Reachable in production. The container ships no `measurements/`, so every
    committed file arrives from raw.githubusercontent.com and the live backlog
    from api.github.com -- BOTH GitHub, so one outage takes the live read and
    its fallback together. Two separate 500s were sitting there:

      * `routes/admin.py:197` is `I["filed_today"]`, and `_issues_view`'s
        zero-state returned four keys -> `KeyError: 'filed_today'`.
      * the cost panel's `.arith` block reads `C.known_usd` unguarded, and
        `_cost_view`'s zero-state returned two keys ->
        `UndefinedError: 'dict object' has no attribute 'known_usd'`.

    `_loop_view` already carried a ten-line comment stating the rule -- "EVERY
    KEY THE OK PATH RETURNS IS PRESENT HERE, with an empty value" -- written
    after this exact failure, on 2026-10-18, two screens above both of them.
    The rule was recorded and not carried to the siblings, which is the same
    finding as `failed` not inheriting `shipped`'s distinctness.
    """
    import os
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    # No disk, and `conftest._no_outbound_http` is what denies the network.
    monkeypatch.setattr(ops_data, "measurements_dir", lambda: None)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", True)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", True)
    monkeypatch.setattr(ops_data, "_app_cache", None)
    ops_data._cache.clear()
    ops_data._today_cache = None
    ops_data._live_cache = None
    try:
        pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
        r = TestClient(app).get("/admin/ops", auth=("admin", pw))
        assert r.status_code == 200, (
            f"the control room returned {r.status_code} because its data "
            f"sources were unreachable"
        )
        snap = ops_data.snapshot(now=datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc))
    finally:
        ops_data._cache.clear()
        ops_data._today_cache = None
        ops_data._live_cache = None
    # Blank, and SAYING it is blank. A zero-state that renders as a confident
    # zero is the 2026-10-18 screen; the footer naming the missing files is
    # what makes it an absence instead.
    assert snap["loop"]["ok"] is False
    assert snap["issues"]["ok"] is False and snap["issues"]["filed_today"] == []
    assert snap["cost"]["ok"] is False and snap["cost"]["known_usd"] == 0
    assert "issues.json" in snap["missing"] and "cost.json" in snap["missing"]
    # And both live reads are reported as fallbacks, so the strip is not silent.
    assert snap["loop"]["fell_back"] is True
    assert snap["issues"]["fell_back"] is True


# --------------------------------------------------------------------------- #
# QA round 4, findings F4-F10. Every one of these is a mechanism that WORKS and
# that nothing pins, so each test below was written by first building the mutant
# that survives the suite, then asserting on what a reader is actually told.
# --------------------------------------------------------------------------- #

def test_the_alert_admits_the_floor_when_the_tile_does(monkeypatch):
    """F4. The tile says `≥100`; the alert must not say `100` as a total.

    Two separate single-line mutants survived the whole suite: `_loop_view`'s
    `"today_truncated": bool(...)` forced to `False`, and `_alerts`' `at_least`
    forced to `""`. Either leaves the tile marked as a floor and the alert
    stating the same number as a fact, on the one occasion it happens -- a run
    storm, which is when the page matters most.

    `_loop_view`'s own comment says the flag must travel with the numbers "so
    the alert cannot disagree with the tile". Nothing checked that it does.
    """
    stamp = _inside_today_utc()
    full = [_run(2000 + i, "agent-work.yml", "failure", stamp)
            for i in range(ops_today.PER_PAGE)]
    body = _ops_body(monkeypatch, [], full)

    assert 'class="num c-failed">≥' in body, "precondition: the tile is a floor"
    assert "At least" in body, (
        "the tile admits a capped read and the alert states the count as a "
        "total -- the two disagree about the same number on the same screen"
    )
    assert "this is a floor, not a total" in body, (
        "the alert drops the sentence that explains why the number is a floor"
    )


def test_an_uncapped_read_claims_no_floor_in_the_alert_either(monkeypatch):
    """F4's other side, so the disclosure means something when it appears."""
    body = _ops_body(
        monkeypatch, [],
        [_run(1, "agent-work.yml", "failure", _inside_today_utc())])
    assert "At least" not in body, "a complete read is announced as a floor"
    assert "this is a floor, not a total" not in body


def test_every_failing_workflow_is_named_once(monkeypatch):
    """F10. The alert dedupes with `sorted({...})` and nothing pinned it.

    Dropping the set turns today's real data into the same workflow name
    printed once per failed run -- 11 times on 2026-10-20 -- in a sentence
    meant to tell an operator which legs are broken.
    """
    stamp = _inside_today_utc()
    runs = [_run(3000 + i, "agent-steward.yml", "failure", stamp) for i in range(6)]
    runs += [_run(3100 + i, "agent-measure.yml", "failure", stamp) for i in range(4)]
    body = _ops_body(monkeypatch, [], runs)

    # The names come from the run payloads; each must appear once in the alert.
    alert = body.split("loop run(s) failed today")[1][:400]
    assert alert.count("agent-steward") == 1, (
        f"the alert names the same workflow repeatedly: {alert[:160]!r}")
    assert alert.count("agent-measure") == 1


def test_a_run_with_no_name_is_still_named_something(monkeypatch):
    """F9. `r.get("name") or path` -- the fallback was never exercised.

    Measured on the real API 2026-10-20: GitHub returned the literal
    `.github/workflows/agent-steward.yml` as a run's `name` for 11 runs, which
    is why the fallback looks unreachable. It is reachable the moment a run
    payload omits `name`, and then the alert must not print `None`.
    """
    stamp = _inside_today_utc()
    run = _run(4000, "agent-work.yml", "failure", stamp)
    run.pop("name", None)
    body = _ops_body(monkeypatch, [], [run])

    # THE REACHABLE FALLBACK IS `ops_today`'s, not `_alerts`'. My first version
    # of this test mutated `_alerts`' `or "an unnamed workflow"` and the test
    # passed -- because `ops_today`'s `r.get("name") or path` had already
    # substituted the workflow PATH, so the downstream fallback never runs.
    # That is F9's actual finding: one fallback makes the other dead code.
    # So this asserts on the path appearing, which is what a reader is told.
    alert = body.split("loop run(s) failed today")[1][:400]
    assert "agent-work" in alert, (
        f"a run with no `name` is not identified at all: {alert[:160]!r}")
    assert "None" not in alert, "the missing name renders as the string None"


def test_the_ops_json_blob_cannot_be_escaped_by_a_pr_title(monkeypatch):
    """F6. Pre-existing line, newly load-bearing.

    `json.dumps(client).replace("</", "<\\\\/")` has no test; deleting it leaves
    the suite green. It predates this PR, but THIS PR is what first puts GitHub
    PR titles -- outsider-authored text in a public repo -- into that blob.
    """
    stamp = _inside_today_utc()
    hostile = '</script><img src=x onerror=alert(1)>'
    # `_pr` TAKES NO `title`, which is why the first version of this test was
    # vacuous: it never put the hostile string on the page at all, and deleting
    # the escape left it green. The title has to be injected onto the row.
    pr = {**_pr(7, stamp), "title": hostile}
    body = _ops_body(monkeypatch, [pr], [])

    assert "onerror=alert(1)" in body, (
        "precondition failed: the hostile title never reached the page, so "
        "this test would assert nothing")
    # The escape rewrites `</` inside the JSON string. Without it the raw
    # `</script>` terminates the block early and the <img> becomes live markup.
    assert "</script><img src=x" not in body, (
        "a PR title closed the ops-data <script> block early -- everything "
        "after it is live markup in the admin page")
    assert "<\\/script><img src=x" in body, (
        "the `</` escape did not reach the rendered blob")


def test_the_request_carries_a_user_agent_and_the_token_when_set():
    """F5. `OPS_GH_TOKEN` is the stated mitigation for the request budget, and
    nothing asserted it reaches the wire.

    Both `headers["Authorization"] = f"Bearer {token}"` and
    `"User-Agent": _UA` could be deleted with the whole suite green. The wire
    was verified correct by execution during QA round 4 -- an UNGUARDED working
    wire, not a broken one -- which is the state that silently becomes a broken
    one. GitHub rejects a request with no User-Agent, and without the token the
    60/hour ceiling stays in force while the docstring says it does not.
    """
    import urllib.request

    seen = {}

    class _R:
        def read(self): return b"[]"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def spy(req, *a, **kw):
        seen["headers"] = dict(req.headers)
        return _R()

    orig = urllib.request.urlopen
    urllib.request.urlopen = spy
    try:
        ops_today._get("https://api.github.com/x", timeout=1, token="t0ken")
    finally:
        urllib.request.urlopen = orig

    # urllib title-cases header names.
    h = {k.lower(): v for k, v in seen["headers"].items()}
    assert h.get("authorization") == "Bearer t0ken", (
        f"the token does not reach the wire, so the rate-limit mitigation this "
        f"module documents does not exist: {sorted(h)}")
    assert h.get("user-agent") == ops_today._UA, (
        f"no User-Agent: GitHub rejects the request outright. got {sorted(h)}")


def test_no_token_sends_no_authorization_header():
    """The other side: an unauthenticated read must not send an empty Bearer."""
    import urllib.request

    seen = {}

    class _R:
        def read(self): return b"[]"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, *a, **kw: (
        seen.update(headers=dict(req.headers)) or _R())
    try:
        ops_today._get("https://api.github.com/x", timeout=1, token=None)
    finally:
        urllib.request.urlopen = orig

    h = {k.lower(): v for k, v in seen["headers"].items()}
    assert "authorization" not in h, f"sent an Authorization header with no token: {sorted(h)}"
    assert h.get("user-agent") == ops_today._UA
