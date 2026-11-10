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
