"""scripts/heartbeat.py -- one agent-queue run always on its way (2026-11-20).

Measured the day before: GitHub fired the hourly agent-queue cron 3 times in 27
slots, and once the events stopped the loop sat idle 3h+. The heartbeat must
never cancel a waiting wake (one pending run per concurrency group), so each
guard below is that failure mode."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("heartbeat", ROOT / "scripts" / "heartbeat.py")
hb = importlib.util.module_from_spec(_spec)
sys.modules["heartbeat"] = hb
_spec.loader.exec_module(hb)

REPO = "o/r"


class Gh:
    def __init__(self, runs_seq):
        self.runs_seq = list(runs_seq)   # one runs list per listing call; the last repeats
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "api":
            runs = self.runs_seq.pop(0) if len(self.runs_seq) > 1 else self.runs_seq[0]
            if runs == "boom":
                raise RuntimeError("HTTP 502")
            return json.dumps({"workflow_runs": runs})
        if args[:2] == ["workflow", "run"]:
            return ""
        raise AssertionError(args)

    @property
    def dispatched(self):
        return [a for a in self.calls if a[:2] == ["workflow", "run"]]


SELF = {"id": 1, "status": "in_progress"}


def test_rearm_dispatches_the_next_heartbeat_when_nothing_else_waits():
    gh = Gh([[SELF, {"id": 0, "status": "completed"}]])
    assert hb.rearm(gh, REPO, "1").startswith("rearmed")
    assert gh.dispatched == [["workflow", "run", "agent-queue.yml", "--repo", REPO, "-f", "heartbeat=true"]]


def test_rearm_never_dispatches_over_a_waiting_run():
    """Dispatching would cancel the pending run -- and with it a workflow_run chain payload."""
    for status in ("queued", "pending", "waiting", "requested", "in_progress"):
        gh = Gh([[SELF, {"id": 2, "status": status}]])
        assert "not rearmed" in hb.rearm(gh, REPO, "1")
        assert gh.dispatched == []


def test_rearm_on_an_unread_api_still_dispatches():
    """A duplicate heartbeat ends at its next rearm; a missing one is a dead loop."""
    gh = Gh(["boom"])
    assert "could not list" in hb.rearm(gh, REPO, "1")
    assert len(gh.dispatched) == 1


def test_doze_sleeps_the_full_doze_when_nothing_waits():
    slept = []
    out = hb.doze(Gh([[SELF]]), REPO, "1", sleep=slept.append, minutes=2)
    assert sum(slept) == 120 and "dozed 2m" in out


def test_doze_yields_as_soon_as_another_run_waits():
    slept = []
    gh = Gh([[SELF], [SELF], [SELF, {"id": 5, "status": "pending"}]])
    out = hb.doze(gh, REPO, "1", sleep=slept.append, minutes=20)
    assert "yielding after 60s" in out and sum(slept) == 60


def test_the_workflow_wires_doze_first_and_rearm_last_with_no_new_permission():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-queue.yml").read_text())
    on = doc.get("on") or doc.get(True)
    assert on["workflow_dispatch"]["inputs"]["heartbeat"]["default"] == "false"
    steps = doc["jobs"]["drain"]["steps"]
    names = [s.get("name") for s in steps]
    doze = steps[names.index("Doze until the next heartbeat")]
    assert doze["if"] == "inputs.heartbeat == 'true'" and doze["run"] == "python3 scripts/heartbeat.py doze"
    assert names.index("Doze until the next heartbeat") < names.index("Start the oldest queued cycle")
    last = steps[-1]
    assert last["name"] == "Keep the heartbeat alive" and last["if"] == "always()"
    assert last["run"] == "python3 scripts/heartbeat.py rearm"
    chain = steps[names.index("Chain the next ranked cycle")]
    assert "inputs.heartbeat == 'true'" in chain["if"]
    # The doze fits inside the job with room for the drain, chain and liveness after it.
    assert doc["jobs"]["drain"]["timeout-minutes"] >= hb.DOZE_MIN + 8
    assert doc["permissions"] == {"contents": "read", "actions": "write",
                                  "issues": "write", "pull-requests": "write"}
