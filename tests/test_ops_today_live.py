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


def _pr(number: int, merged_at: str | None,
        closed_at: str = "2026-10-17T20:00:00Z") -> dict:
    """A row from `/pulls?state=closed`.

    `closed_at` IS ALWAYS PRESENT, and defaults to a timestamp inside the day,
    because that is what the endpoint returns: every row from `state=closed`
    carries one, merged or not. Omitting it made
    `test_an_unmerged_closed_pr_is_not_shipped` unable to fail -- the obvious
    wrong implementation, `merged_at or closed_at`, counts every closed PR as
    shipped and passed against a fixture where `closed_at` did not exist.
    Proved by mutation, which reported MISSED. Same class as the tied-sort-key
    defect in #419: the fixture, not the assertion, was what could not fail.
    """
    return {"number": number, "title": f"PR {number}", "merged_at": merged_at,
            "closed_at": closed_at,
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
    on_disk = {p.name for p in (ROOT / ".github" / "workflows").glob("*.yml")}
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
    assert "today_truncated" in body.lower() or "≥" in body, body[:200]
    assert "≥" in body, (
        "the capped count renders as a flat number, so the page states a total "
        "it cannot stand behind"
    )
    assert "live, at least" in body, (
        "the live badge does not admit that the read was capped"
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
