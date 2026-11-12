"""A red PR gets a re-run if the runner flaked and a fix cycle if the code failed (#912).

Measured 2026-11-12: #899, #900 and #901 sat ~10h on a runner DNS blip (apt
could not resolve security.ubuntu.com, no test ran); #892 and #884 sat 13h and
20h on real failures. Nothing acted, because `qa-on-green` exits on red and
`detect_stalls.py` has no red-gates kind.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("red_gates", ROOT / "scripts" / "red_gates.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)

SHA = "a" * 40
APT_FLAKE = ("2026-11-11T22:40:01.1Z E: Failed to fetch https://security.ubuntu.com/x.deb  "
             "Temporary failure resolving 'security.ubuntu.com'\n"
             "2026-11-11T22:40:01.2Z ##[error]Process completed with exit code 100.\n")
REAL = ("2026-11-11T10:20:00.0Z FAIL — 1 row(s) do not match their own command:\n"
        "2026-11-11T10:20:00.1Z ##[error]verify_architecture_counts FAIL (exit 1)\n")
FLAKY_BUT_JUDGED = APT_FLAKE + "2026-11-11T22:41:00.0Z FAILED tests/test_x.py::test_y - assert 1\n"


def env(branch="issue/889-matching-positions-line", attempt="1"):
    return {"GH_REPO": "o/r", "RUN_ID": "77", "HEAD_SHA": SHA, "HEAD_BRANCH": branch,
            "RUN_ATTEMPT": attempt, "AGENT_AUTHORS": "claude[bot],mahAnuj"}


class Gh:
    def __init__(self, *, branch="issue/889-matching-positions-line", login="claude[bot]",
                 head=SHA, logs=(REAL,), comments=(), files=("src/astro_ai/x.py",)):
        self.pr = {"number": 892, "user": {"login": login},
                   "head": {"ref": branch, "sha": head}}
        self.logs, self.comments, self.files = list(logs), list(comments), list(files)

    def __call__(self, args):
        url = args[1]
        if url.startswith("repos/o/r/pulls?state=open"):
            return json.dumps([self.pr])
        if url == "repos/o/r/actions/runs/77/jobs":
            return json.dumps({"jobs": [{"id": i, "name": f"job{i}", "conclusion": "failure"}
                                        for i in range(len(self.logs))]})
        if url.startswith("repos/o/r/actions/jobs/"):
            log = self.logs[int(url.split("/")[5])]
            if log is None:
                raise RuntimeError("HTTP 410")
            return log
        if url.startswith("repos/o/r/issues/892/comments"):
            return json.dumps([{"body": b} for b in self.comments])
        if url.startswith("repos/o/r/pulls/892/files"):
            return json.dumps([{"filename": f} for f in self.files])
        raise AssertionError(url)


# --- the classifier, on the logs that were actually red on 2026-11-12 ---------

def test_a_dns_failure_before_any_test_is_a_flake():
    assert rg.is_flake(APT_FLAKE)


def test_a_gate_verdict_is_never_a_flake():
    assert not rg.is_flake(REAL)
    assert not rg.is_flake(FLAKY_BUT_JUDGED), "a flaky line beside a real test failure is still real"


# --- decisions ---------------------------------------------------------------

def test_a_flake_on_the_first_attempt_is_re_run():
    d = rg.decide(Gh(logs=(APT_FLAKE, APT_FLAKE)), env())
    assert d["action"] == "rerun"


def test_a_flake_again_on_a_re_run_is_left_alone():
    assert rg.decide(Gh(logs=(APT_FLAKE,)), env(attempt="2"))["action"] == "none"


def test_an_unreadable_log_is_never_called_a_flake():
    assert rg.decide(Gh(logs=(None,)), env())["action"] == "fix"


def test_a_real_failure_on_an_issue_branch_dispatches_one_fix_cycle():
    d = rg.decide(Gh(), env())
    assert (d["action"], d["issue"], d["pr"]) == ("fix", 889, 892)


def test_partial_and_fix_branches_name_their_issue_too():
    for b, n in (("partial/773-numerology", 773), ("fix/700-x", 700)):
        assert rg.decide(Gh(branch=b), env(branch=b))["issue"] == n


def test_the_same_head_never_gets_a_second_fix():
    gh = Gh(comments=(f"{rg.FIX_MARK} {SHA}\n\nwhatever",))
    assert rg.decide(gh, env())["action"] == "none"


def test_a_workflows_diff_is_noted_not_dispatched():
    d = rg.decide(Gh(files=(".github/workflows/x.yml",)), env())
    assert d["action"] == "notify" and "workflows" in d["why"]


def test_an_owner_branch_with_no_issue_is_noted_once():
    b = "claude/peaceful-pascal-x"
    assert rg.decide(Gh(branch=b, login="mahAnuj"), env(branch=b))["action"] == "notify"
    gh = Gh(branch=b, login="mahAnuj", comments=(f"{rg.NOTE_MARK} {SHA}",))
    assert rg.decide(gh, env(branch=b))["action"] == "none"


def test_an_outsider_a_moved_head_and_a_measurement_pr_are_left_alone():
    assert rg.decide(Gh(login="stranger"), env())["action"] == "none"
    assert rg.decide(Gh(head="b" * 40), env())["action"] == "none"
    m = "measurements/1-1"
    assert rg.decide(Gh(branch=m), env(branch=m))["action"] == "none"


def test_bad_input_exits_2(monkeypatch):
    for k, v in env().items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("HEAD_SHA", "abc")
    assert rg.main(["x"], gh=Gh()) == 2


# --- the wiring --------------------------------------------------------------

def _wf():
    return yaml.safe_load((ROOT / ".github/workflows/qa-on-green.yml").read_text())


def _steps():
    return {s.get("name"): s for s in _wf()["jobs"]["consider"]["steps"]}


def test_red_runs_from_both_gate_workflows_and_green_stays_on_pr_gates():
    doc = _wf()
    on = doc[next(k for k in doc if str(k) in ("on", "True"))]
    assert on["workflow_run"]["workflows"] == ["PR gates", "verify-build"]
    # One job, not two: a new job inherits every workflow permission, which
    # verify_workflow_permissions reads as a widening. The green path exits
    # early on anything but PR gates; the red steps run only on a failed PR run.
    assert list(doc["jobs"]) == ["consider"]
    pick = _steps()["Is this a PR a cycle should finish?"]
    assert 'if [ "$GATES_WORKFLOW" != "PR gates" ]; then' in pick["run"]
    assert pick["env"]["GATES_WORKFLOW"] == "${{ github.event.workflow_run.name }}"
    assert "conclusion == 'failure'" in _steps()["What should happen to this red PR?"]["if"]


def test_the_marker_is_written_before_the_fix_is_dispatched():
    names = [s.get("name") for s in _wf()["jobs"]["consider"]["steps"]]
    assert names.index("Record the fix dispatch on the PR") < names.index("Dispatch the fix cycle")


def test_the_red_job_cannot_label_or_merge():
    for s in _wf()["jobs"]["consider"]["steps"]:
        run = s.get("run") or ""
        for banned in ("--add-label", "--remove-label", "gh pr edit", "gh pr merge"):
            assert banned not in run, banned
