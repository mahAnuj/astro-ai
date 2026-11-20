"""The build lane chains its next ranked cycle (owner, 2026-11-06: "I have been
seeing a long queue of backlog issues for very long"; measured: the lane idle
89% of the week). Every guard is a measured failure mode, so each has a test."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("chain_cycle", ROOT / "scripts" / "chain_cycle.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules["chain_cycle"] = cc
_spec.loader.exec_module(cc)

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
REPO = "o/r"
RUN = {"name": "Agent work", "title": "Agent work", "conclusion": "success",
       "started": "2026-11-06T11:30:00Z"}
USAGE = {"generated_at": "2026-11-06T09:00:00Z",
         "latest": {"seven_day": 0.30, "status": "allowed"}}


class FakeGh:
    def __init__(self, running=(), today=(), prs=None):
        self.running = list(running)          # displayTitles of non-completed runs
        self.today = list(today)              # display_titles of today's runs
        self.prs = prs if prs is not None else [
            {"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T11:50:00Z"}]
        self.calls: list[list[str]] = []

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["run", "list"]:
            # Evaluate the real lane jq's intent: count non-QA running titles.
            jq = args[args.index("--jq") + 1]
            qa = '| not)' not in jq
            n = sum(t.startswith(cc.QA_TITLE) == qa for t in self.running)
            return f"{n}\n"
        if args[0] == "api" and "/actions/workflows/agent-work.yml/runs" in args[1]:
            return json.dumps({"workflow_runs": [{"display_title": t} for t in self.today]})
        if args[0] == "api" and "/pulls?" in args[1]:
            return json.dumps(self.prs)
        if args[:2] == ["workflow", "run"]:
            return ""
        raise AssertionError(args)

    @property
    def dispatched(self):
        return any(a[:2] == ["workflow", "run"] for a in self.calls)


def decide(gh, run=RUN, usage=USAGE):
    return cc.decide(gh, REPO, dict(run), usage, NOW)


def test_a_productive_build_cycle_with_headroom_chains():
    assert decide(FakeGh()) is None


def test_the_weekly_window_at_the_ceiling_stops_it():
    u = {**USAGE, "latest": {"seven_day": 0.70, "status": "allowed"}}
    assert "70%" in decide(FakeGh(), usage=u)


def test_an_unread_stale_or_refused_quota_stops_it():
    assert "unreadable" in decide(FakeGh(), usage=None)
    assert "old" in decide(FakeGh(), usage={**USAGE, "generated_at": "2026-11-04T00:00:00Z"})
    rej = {**USAGE, "latest": {"seven_day": 0.1, "status": "rejected"}}
    assert "rejected" in decide(FakeGh(), usage=rej)


def test_only_a_successful_build_cycle_chains():
    assert "QA round" in decide(FakeGh(), run={**RUN, "title": "QA round: PR #5"})
    assert "failure" in decide(FakeGh(), run={**RUN, "conclusion": "failure"})
    assert "Agent steward" in decide(FakeGh(), run={**RUN, "name": "Agent steward"})


def test_a_busy_build_lane_stops_it_but_a_running_qa_round_does_not():
    assert "busy" in decide(FakeGh(running=["Agent work"]))
    assert decide(FakeGh(running=["QA round: PR #9"])) is None


def test_the_daily_cap_counts_build_runs_only():
    full = ["Agent work"] * cc.MAX_BUILD_RUNS_PER_DAY
    assert "cap" in decide(FakeGh(today=full))
    assert decide(FakeGh(today=["QA round: PR #1"] * 40)) is None


def test_a_cycle_that_moved_no_pr_does_not_chain():
    stale = [{"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T10:00:00Z"}]
    assert "no PR" in decide(FakeGh(prs=stale))
    owners = [{"user": {"login": "mahAnuj"}, "updated_at": "2026-11-06T11:59:00Z"}]
    assert "no PR" in decide(FakeGh(prs=owners))


def test_main_dispatches_one_ranked_cycle_with_no_inputs(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(USAGE))
    monkeypatch.setenv("GH_REPO", REPO)
    for k, v in RUN.items():
        monkeypatch.setenv(f"WR_{k.upper()}", v)
    gh = FakeGh()
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=p) == 0
    sent = [a for a in gh.calls if a[:2] == ["workflow", "run"]]
    assert sent == [["workflow", "run", "agent-work.yml", "--repo", REPO]]


def test_main_does_not_dispatch_when_a_guard_says_no(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_REPO", REPO)
    for k, v in RUN.items():
        monkeypatch.setenv(f"WR_{k.upper()}", v)
    gh = FakeGh()
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=tmp_path / "missing.json") == 0
    assert not gh.dispatched


def test_the_queue_runs_the_chain_after_the_drain_and_only_on_workflow_run():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-queue.yml").read_text())
    steps = doc["jobs"]["drain"]["steps"]
    names = [s.get("name") for s in steps]
    assert names.index("Chain the next ranked cycle") > names.index("Start the oldest queued cycle")
    step = steps[names.index("Chain the next ranked cycle")]
    assert "workflow_run" in step["if"] and step["run"] == "python3 scripts/chain_cycle.py"
    # Since #826 a woken run (agent-queue dispatched with after_run) supplies
    # WAKE_STARTED instead; the workflow_run payload still comes first.
    assert step["env"]["WR_STARTED"].startswith("${{ github.event.workflow_run.run_started_at ||")


# --- the freshest quota reading (2026-11-20) ------------------------------------------------

def _rate_block(seven, status):
    body = json.dumps({"rate_limit_info": {"status": status, "unifiedWindows": {
        "five_hour": {"utilization": 0.3, "status": status},
        "seven_day": {"utilization": seven, "status": status}}}}, indent=2)
    inner = body.split("\n", 1)[1].rsplit("\n", 1)[0]
    return "\n".join(f"2026-11-06T11:40:00.0000000Z {l}" for l in inner.splitlines()) + "\n"


class FreshGh(FakeGh):
    """FakeGh plus the newest finished agent-work run and its job log."""

    def __init__(self, log, **kw):
        super().__init__(**kw)
        self.log = log

    def __call__(self, args):
        url = next((a for a in args if a.startswith("repos/")), "")
        if args[0] == "api" and "agent-work.yml/runs?status=completed&per_page=1" in url:
            return json.dumps({"workflow_runs": [{"id": 91, "run_started_at": "2026-11-06T11:30:00Z"}]})
        if args[0] == "api" and url.endswith("/actions/runs/91/jobs"):
            return json.dumps({"jobs": [{"id": 7}]})
        if args[0] == "api" and url.endswith("/actions/jobs/7/logs"):
            return self.log
        return super().__call__(args)


def test_a_stale_warning_does_not_block_a_chain_the_fresh_reading_allows(tmp_path, monkeypatch):
    """2026-11-20 11:43Z: claude_usage.json still said 'allowed_warning' (88%, from 03:53Z)
    while the 11:05Z cycle had logged 4% -- the weekly window reset at ~06:00Z -- and the loop
    stood down with 96% of the week unused."""
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"generated_at": "2026-11-06T11:00:00Z",
                             "latest": {"seven_day": 0.88, "status": "allowed_warning",
                                        "at": "2026-11-06T04:00:00Z"}}))
    monkeypatch.setenv("GH_REPO", REPO)
    for k, v in RUN.items():
        monkeypatch.setenv(f"WR_{k.upper()}", v)
    gh = FreshGh(_rate_block(0.04, "allowed"))
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=p) == 0
    assert [a for a in gh.calls if a[:2] == ["workflow", "run"]] == [["workflow", "run", "agent-work.yml", "--repo", REPO]]


def test_a_fresh_warning_still_blocks_even_when_the_file_says_allowed(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    p.write_text(json.dumps({**USAGE, "latest": {**USAGE["latest"], "at": "2026-11-06T04:00:00Z"}}))
    monkeypatch.setenv("GH_REPO", REPO)
    for k, v in RUN.items():
        monkeypatch.setenv(f"WR_{k.upper()}", v)
    gh = FreshGh(_rate_block(0.91, "allowed_warning"))
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=p) == 0
    assert not [a for a in gh.calls if a[:3] == ["workflow", "run", "agent-work.yml"]]


def test_an_older_fresh_reading_never_replaces_a_newer_file():
    usage = {"generated_at": "2026-11-06T11:50:00Z", "latest": {"seven_day": 0.5, "status": "allowed",
                                                                 "at": "2026-11-06T11:45:00Z"}}
    older = {"seven_day": 0.01, "status": "allowed", "at": "2026-11-06T09:00:00Z"}
    assert cc.freshest(usage, older, NOW) is usage


# --- an expired reading, and an idle lane (2026-11-20) --------------------------------------

def _epoch(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def test_a_reading_whose_windows_have_both_reset_no_longer_refuses():
    """The 2026-11-20 reading: 88%, allowed_warning, seven-day reset 06:00Z, five-hour 04:40Z;
    judged at 11:43Z."""
    latest = {"seven_day": 0.88, "status": "allowed_warning",
              "resets": {"five_hour": _epoch("2026-11-06T04:40:00Z"),
                         "seven_day": _epoch("2026-11-06T06:00:00Z")}}
    assert cc.quota_reason({**USAGE, "latest": latest}, NOW) is None


def test_a_reading_with_one_window_still_open_still_refuses():
    latest = {"seven_day": 0.88, "status": "allowed_warning",
              "resets": {"five_hour": _epoch("2026-11-06T04:40:00Z"),
                         "seven_day": _epoch("2026-11-06T18:00:00Z")}}
    assert "allowed_warning" in cc.quota_reason({**USAGE, "latest": latest}, NOW)
    nores = {"seven_day": 0.88, "status": "allowed_warning"}
    assert "allowed_warning" in cc.quota_reason({**USAGE, "latest": nores}, NOW)


class IdleGh(FakeGh):
    """FakeGh plus the finished agent-work runs `last_build_run` reads."""

    def __init__(self, finished, **kw):
        super().__init__(**kw)
        self.finished = finished

    def __call__(self, args):
        url = next((a for a in args if a.startswith("repos/")), "")
        if args[0] == "api" and "agent-work.yml/runs?status=completed&per_page=20" in url:
            return json.dumps({"workflow_runs": self.finished})
        if args[0] == "api" and "agent-work.yml/runs?status=completed&per_page=1" in url:
            return json.dumps({"workflow_runs": []})
        return super().__call__(args)


def _build(started, ended, title="Agent work"):
    return {"display_title": title, "run_started_at": started, "updated_at": ended}


def test_an_idle_lane_restarts_after_an_hour():
    gh = IdleGh([_build("2026-11-06T10:20:00Z", "2026-11-06T10:50:00Z")],
                prs=[{"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T10:45:00Z"}])
    assert cc.idle_reason(gh, REPO, USAGE, NOW) is None


def test_an_idle_lane_waits_out_the_hour_and_a_qa_round_is_not_a_build_run():
    gh = IdleGh([_build("2026-11-06T11:40:00Z", "2026-11-06T11:55:00Z", "QA round: PR #9"),
                 _build("2026-11-06T11:00:00Z", "2026-11-06T11:30:00Z")],
                prs=[{"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T11:20:00Z"}])
    assert "30m ago" in cc.idle_reason(gh, REPO, USAGE, NOW)


def test_after_an_empty_cycle_an_idle_lane_waits_four_hours():
    gh = IdleGh([_build("2026-11-06T09:00:00Z", "2026-11-06T09:30:00Z")],
                prs=[{"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T08:00:00Z"}])
    assert "restarts after 240m" in cc.idle_reason(gh, REPO, USAGE, NOW)


def test_an_idle_restart_keeps_the_quota_busy_and_cap_guards():
    old = [_build("2026-11-06T08:00:00Z", "2026-11-06T08:30:00Z")]
    hot = {**USAGE, "latest": {"seven_day": 0.75, "status": "allowed"}}
    assert "70%" in cc.idle_reason(IdleGh(old), REPO, hot, NOW)
    assert "busy" in cc.idle_reason(IdleGh(old, running=["Agent work"]), REPO, USAGE, NOW)
    full = ["Agent work"] * cc.MAX_BUILD_RUNS_PER_DAY
    assert "cap" in cc.idle_reason(IdleGh(old, today=full), REPO, USAGE, NOW)


def test_a_run_with_no_finished_cycle_restarts_an_idle_lane_through_main(tmp_path, monkeypatch, capsys):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(USAGE))
    monkeypatch.setenv("GH_REPO", REPO)
    for k in RUN:
        monkeypatch.setenv(f"WR_{k.upper()}", "")
    gh = IdleGh([_build("2026-11-06T08:00:00Z", "2026-11-06T08:30:00Z")],
                prs=[{"user": {"login": "claude[bot]"}, "updated_at": "2026-11-06T08:20:00Z"}])
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=p) == 0
    assert [a for a in gh.calls if a[:2] == ["workflow", "run"]] == [["workflow", "run", "agent-work.yml", "--repo", REPO]]
    assert "restarted:" in capsys.readouterr().out
