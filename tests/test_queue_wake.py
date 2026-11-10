"""A dispatched cycle wakes agent-queue itself (#826, 2026-11-10).

Measured 2026-11-08..10: agent-queue ran after 8 of 8 scheduled agent-work
completions and 0 of 26 dispatched ones, because GitHub drops a fourth
`workflow_run` level. So the lane chained once per cron firing and then sat:
on 2026-11-10 the 11:12 chained cycle shipped #845 and nothing ran for 3h+.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
_spec = importlib.util.spec_from_file_location("wait_for_run", ROOT / "scripts" / "wait_for_run.py")
wfr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wfr)

REPO = "o/r"
DONE = {"path": ".github/workflows/agent-work.yml", "status": "completed", "conclusion": "success",
        "name": "Agent work", "display_title": "Agent work", "run_started_at": "2026-11-10T11:12:00Z"}


class Api:
    def __init__(self, *states):
        self.states = list(states)
        self.calls = 0

    def __call__(self, args):
        assert args == ["api", f"repos/{REPO}/actions/runs/42805592453"]
        self.calls += 1
        s = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        if isinstance(s, Exception):
            raise s
        return json.dumps(s)


def test_it_waits_for_the_waker_to_complete_then_describes_it():
    running = {**DONE, "status": "in_progress", "conclusion": None}
    gh, naps = Api(running, running, DONE), []
    code, facts = wfr.wait(gh, REPO, "42805592453", naps.append)
    assert code == 0 and gh.calls == 3 and len(naps) == 2
    assert facts == {"WAKE_NAME": "Agent work", "WAKE_TITLE": "Agent work",
                     "WAKE_CONCLUSION": "success", "WAKE_STARTED": "2026-11-10T11:12:00Z"}


def test_a_qa_round_is_described_by_its_title_so_chain_cycle_skips_it():
    code, facts = wfr.wait(Api({**DONE, "display_title": "QA round: PR #841"}), REPO, "42805592453", lambda s: None)
    assert code == 0 and facts["WAKE_TITLE"].startswith("QA round")


def test_a_run_of_any_other_workflow_is_refused():
    other = {**DONE, "path": ".github/workflows/pr-gates.yml"}
    code, why = wfr.wait(Api(other), REPO, "42805592453", lambda s: None)
    assert code == 1 and "pr-gates.yml" in why


def test_a_run_that_never_completes_times_out_rather_than_chaining():
    running = {**DONE, "status": "in_progress"}
    naps = []

    def nap(s):
        naps.append(s)
        if len(naps) > 50:               # a wait with no bound must fail here, not hang the suite
            raise AssertionError("wait_for_run never gave up")
    code, why = wfr.wait(Api(running), REPO, "42805592453", nap, max_wait=60)
    assert code == 1 and "did not complete" in why
    assert len(naps) == 60 // wfr.POLL_SECONDS


def test_a_transient_api_error_is_retried():
    code, _ = wfr.wait(Api(RuntimeError("HTTP 502"), DONE), REPO, "42805592453", lambda s: None)
    assert code == 0


def test_main_validates_its_input_and_writes_github_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_REPO", REPO)
    monkeypatch.setenv("AFTER_RUN", "1; rm -rf /")
    assert wfr.main(["x"], gh=Api(DONE), sleep=lambda s: None) == 2
    env = tmp_path / "env"
    monkeypatch.setenv("AFTER_RUN", "42805592453")
    monkeypatch.setenv("GITHUB_ENV", str(env))
    assert wfr.main(["x"], gh=Api(DONE), sleep=lambda s: None) == 0
    assert "WAKE_NAME=Agent work\n" in env.read_text()
    assert "WAKE_STARTED=2026-11-10T11:12:00Z\n" in env.read_text()


# --- the wiring --------------------------------------------------------------

def _doc(name):
    return yaml.safe_load((WF / name).read_text())


def test_a_dispatched_cycle_wakes_agent_queue_with_its_own_run_id():
    steps = _doc("agent-work.yml")["jobs"]["cycle"]["steps"]
    wake = steps[-2]
    assert wake["name"] == "Wake agent-queue when this run completes", (
        "it must run after the push and PR steps; only the receipt follows it")
    assert steps[-1]["name"] == "Record the loop receipt"
    assert wake["if"] == "always() && github.event_name == 'workflow_dispatch'", (
        "a scheduled run is already woken by workflow_run; waking it twice would chain twice")
    assert wake.get("continue-on-error") is True
    assert "gh workflow run agent-queue.yml" in wake["run"] and 'after_run="$RUN_ID"' in wake["run"]
    assert wake["env"]["RUN_ID"] == "${{ github.run_id }}"
    assert "agent-work.yml" not in wake["run"], "a cycle must never dispatch the next cycle itself"


def test_agent_queue_waits_before_draining_and_chains_off_the_woken_run():
    q = _doc("agent-queue.yml")
    on = q[next(k for k in q if str(k) in ("on", "True"))]
    assert "after_run" in on["workflow_dispatch"]["inputs"]
    steps = q["jobs"]["drain"]["steps"]
    names = [s.get("name") for s in steps]
    assert names.index("Wait for the waking cycle to finish") < names.index("Start the oldest queued cycle")
    wait = steps[names.index("Wait for the waking cycle to finish")]
    assert "scripts/wait_for_run.py" in wait["run"] and wait["env"]["AFTER_RUN"] == "${{ inputs.after_run }}"
    chain = steps[names.index("Chain the next ranked cycle")]
    assert "env.WAKE_NAME != ''" in chain["if"] and "github.event_name == 'workflow_run'" in chain["if"]
    for wr, wake in (("WR_NAME", "WAKE_NAME"), ("WR_TITLE", "WAKE_TITLE"),
                     ("WR_CONCLUSION", "WAKE_CONCLUSION"), ("WR_STARTED", "WAKE_STARTED")):
        assert f"env.{wake}" in chain["env"][wr], wr


def test_the_job_timeout_covers_the_wait():
    assert _doc("agent-queue.yml")["jobs"]["drain"]["timeout-minutes"] * 60 > wfr.MAX_WAIT_SECONDS
