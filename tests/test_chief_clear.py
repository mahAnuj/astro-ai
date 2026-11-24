"""chief's clearance carrier (#719).

chief could post `chief-cleared at <sha>` and never apply the label, because
both steps that run it deny `gh pr edit` -- PR #706 sat held seven hours after
the ruling. scripts/chief_clear.py carries the ruling out from a `run:` step,
and re-reads every precondition from the API rather than trusting the file."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("chief_clear", ROOT / "scripts" / "chief_clear.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules["chief_clear"] = cc
_spec.loader.exec_module(cc)

REPO = "o/r"
SHA = "b9077f6b65a881a5b4108cc4df1f33210c0affc9"
OTHER = "a" * 40
T1, T2 = "2026-11-24T04:25:30Z", "2026-11-24T04:33:27Z"


class FakeGh:
    def __init__(self, *, state="open", head=SHA,
                 labels="needs-human-review,qa-pass,qa:independent",
                 gates=((1, "2026-11-24T04:00:00Z", "completed", "success"),),
                 comments=None, fail=None):
        self.state, self.head, self.labels = state, head, labels
        # (id, started_at, status, conclusion) per `gates` run, or the raw
        # text itself when a test wants unreadable output
        self.gates = gates
        self.gate_calls: list[list[str]] = []
        # (login, body)
        self.comments = comments if comments is not None else [
            (cc.RULER, f"QA: PASS — independent round, verified at {SHA}\nbody"),
            (cc.RULER, f"**chief ruling**\n\nchief-cleared at {SHA}")]
        self.fail = fail or set()
        self.writes: list[list[str]] = []
        self.dispatches: list[list[str]] = []

    def __call__(self, args):
        if args[0] == "workflow":
            if "workflow" in self.fail:
                raise RuntimeError("boom")
            self.dispatches.append(args)
            return ""
        url = next(a for a in args[1:] if a.startswith("repos/"))
        for f in self.fail:
            if f in url:
                raise RuntimeError("boom")
        if args[1] == "-X":
            self.writes.append(args)
            return "{}"
        if re.search(r"/pulls/\d+$", url):
            return f"{self.state}\t{self.head}\t{self.labels}\n"
        if "/check-runs" in url:
            self.gate_calls.append(args)
            if isinstance(self.gates, str):
                return self.gates
            return "".join(json.dumps({"id": i, "started_at": at, "status": st, "conclusion": c})
                           + "\n" for i, at, st, c in self.gates)
        if "/comments" in url and 'startswith("QA: PASS")' in args[-1]:
            want = re.search(r'contains\("([0-9a-f]{40})"\)', args[-1]).group(1)
            m = re.search(r'login (==|!=) "([^"]+)"', args[-1])   # read the script's OWN filter
            ok = (lambda l: l == m.group(2)) if m.group(1) == "==" else (lambda l: l != m.group(2))
            return str(sum(1 for l, b in self.comments if ok(l) and b.startswith("QA: PASS")
                           and want in b.split("\n")[0])) + "\n"
        if "/comments" in url:
            want = re.search(r'contains\("chief-cleared at ([0-9a-f]+)"\)', args[-1]).group(1)
            m = re.search(r'login (==|!=) "([^"]+)"', args[-1])
            ok = (lambda l: l == m.group(2)) if m.group(1) == "==" else (lambda l: l != m.group(2))
            return str(sum(1 for l, b in self.comments if ok(l) and f"chief-cleared at {want}" in b)) + "\n"
        raise AssertionError(args)


def run(tmp_path, monkeypatch, gh, text=f"pr=706 sha={SHA}\n"):
    monkeypatch.setenv("GH_REPO", REPO)
    f = tmp_path / "chief-clear.txt"
    f.write_text(text)
    return cc.main(["chief_clear.py", str(f)], gh=gh)


def test_a_bound_ruling_on_a_ready_PR_is_applied(tmp_path, monkeypatch):
    gh = FakeGh()
    assert run(tmp_path, monkeypatch, gh) == 0
    assert gh.writes == [
        ["api", "-X", "POST", f"repos/{REPO}/issues/706/labels", "-f", "labels[]=chief-cleared"],
        ["api", "-X", "DELETE", f"repos/{REPO}/issues/706/labels/needs-human-review"]]


def test_a_ruling_for_an_OLD_head_is_refused(tmp_path, monkeypatch):
    """A clearance does not survive a push (#609, #564)."""
    gh = FakeGh(head=OTHER)
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_no_ruling_comment_means_no_label(tmp_path, monkeypatch, capsys):
    """The comment comes first: a label with no ruling above it is the
    fabrication shape this repo has been burned by twice."""
    gh = FakeGh(comments=[(cc.RULER, f"QA: PASS — verified at {SHA}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []
    assert "the ruling comes first" in capsys.readouterr().out


def test_a_ruling_comment_by_anyone_but_claude_bot_does_not_count(tmp_path, monkeypatch):
    gh = FakeGh(comments=[(cc.RULER, f"QA: PASS — verified at {SHA}"),
                          ("someone", f"chief-cleared at {SHA}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_a_ruling_bound_to_another_sha_does_not_count(tmp_path, monkeypatch):
    gh = FakeGh(comments=[(cc.RULER, f"QA: PASS — verified at {SHA}"),
                          (cc.RULER, f"chief-cleared at {OTHER}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_an_in_cycle_qa_pass_is_not_enough(tmp_path, monkeypatch):
    """chief.md precondition 1 -- the #712 case: qa:in-cycle only."""
    gh = FakeGh(labels="needs-human-review,qa-pass,qa:in-cycle")
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_qa_fail_is_a_verdict_not_a_hold(tmp_path, monkeypatch):
    gh = FakeGh(labels="needs-human-review,qa-pass,qa:independent,qa-fail")
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_red_or_missing_gates_are_refused(tmp_path, monkeypatch):
    for gates in (((1, T1, "completed", "failure"),), (),
                  ((1, T1, "completed", "success"), (2, T2, "completed", "failure"))):
        gh = FakeGh(gates=gates)
        assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == [], gates


def test_a_superseded_red_run_does_not_veto_a_green_rerun(tmp_path, monkeypatch):
    """#1442: PR #1428 head c2621f7 had `gates` failure (id 138216580157,
    04:25:30Z) then success (id 138219560717, 04:33:27Z); joining every
    conclusion refused a head whose latest run was green."""
    gh = FakeGh(gates=((138216580157, "2026-11-24T04:25:30Z", "completed", "failure"),
                       (138219560717, "2026-11-24T04:33:27Z", "completed", "success")))
    assert run(tmp_path, monkeypatch, gh) == 0 and len(gh.writes) == 2


def test_a_green_run_followed_by_a_red_one_is_refused(tmp_path, monkeypatch):
    """Not "any success": the LATEST run decides, and here it is red."""
    gh = FakeGh(gates=((1, T1, "completed", "success"), (2, T2, "completed", "failure")))
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


@pytest.mark.parametrize("status,conclusion", [
    ("in_progress", None), ("queued", None), ("completed", "cancelled"),
    ("completed", "skipped"), ("completed", "failure"), ("completed", "timed_out"),
    ("completed", None)])
def test_a_latest_run_that_is_not_completed_success_is_refused(tmp_path, monkeypatch,
                                                              status, conclusion):
    gh = FakeGh(gates=((1, T1, "completed", "success"), (2, T2, status, conclusion)))
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


@pytest.mark.parametrize("flip", [False, True])
def test_equal_started_at_is_decided_by_the_higher_id(tmp_path, monkeypatch, flip):
    """Same start second, either listing order: id 2 (green) is the latest."""
    runs = [(1, T1, "completed", "failure"), (2, T1, "completed", "success")]
    gh = FakeGh(gates=tuple(reversed(runs)) if flip else tuple(runs))
    assert run(tmp_path, monkeypatch, gh) == 0
    runs = [(1, T1, "completed", "success"), (2, T1, "completed", "failure")]
    gh = FakeGh(gates=tuple(reversed(runs)) if flip else tuple(runs))
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_a_queued_rerun_with_no_start_time_is_the_latest(tmp_path, monkeypatch):
    """A queued run has a null started_at; it must not be skipped in favour
    of an older green one."""
    gh = FakeGh(gates=((1, T1, "completed", "success"), (2, None, "queued", None)))
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


@pytest.mark.parametrize("raw", ["not json\n", '{"started_at": "2026-11-24T04:00:00Z", '
                                 '"status": "completed", "conclusion": "success"}\n',
                                 "[1, 2]\n", "\n"])
def test_unreadable_gates_output_is_refused(tmp_path, monkeypatch, raw):
    gh = FakeGh(gates=raw)
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_the_gates_request_is_paginated_and_filtered_to_gates(tmp_path, monkeypatch):
    """Without --paginate a head with more than one page of runs is read
    from the first page only."""
    gh = FakeGh()
    run(tmp_path, monkeypatch, gh)
    (args,) = gh.gate_calls
    assert "--paginate" in args
    url = next(a for a in args if a.startswith("repos/"))
    assert "check_name=gates" in url and "filter=all" in url and "per_page=100" in url


def test_the_refusal_names_the_latest_run(tmp_path, monkeypatch, capsys):
    gh = FakeGh(gates=((1, T1, "completed", "success"), (7, T2, "completed", "cancelled")))
    run(tmp_path, monkeypatch, gh)
    assert "latest run 7: completed/cancelled" in capsys.readouterr().out


def test_a_PR_with_no_hold_or_closed_is_left_alone(tmp_path, monkeypatch):
    for kw in ({"labels": "qa-pass,qa:independent"}, {"state": "closed"}):
        gh = FakeGh(**kw)
        assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == [], kw


def test_an_API_failure_keeps_the_hold(tmp_path, monkeypatch):
    for where in ("/pulls/706", "/check-runs", "/comments"):
        gh = FakeGh(fail={where})
        assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == [], where


def test_no_file_is_no_ruling_and_green(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_REPO", REPO)
    assert cc.main(["chief_clear.py", str(tmp_path / "absent.txt")], gh=FakeGh()) == 0


def test_malformed_and_excess_lines_are_not_applied(tmp_path, monkeypatch):
    gh = FakeGh()
    text = "pr=706 sha=b9077f6\n" + "".join(f"pr={n} sha={SHA}\n" for n in (1, 2, 3, 4))
    rulings, problems = cc.parse(text)
    assert len(rulings) == 2 and len(problems) == 2      # 1 malformed + "past the first 3"
    assert run(tmp_path, monkeypatch, gh, text) == 1


def test_the_workflow_runs_the_carrier_after_chief_with_no_new_scope():
    """The carrier is a `run:` step on the job's own token; the agent steps
    keep denying `gh pr edit`, so chief still cannot label anything itself."""
    wf = yaml.safe_load((ROOT / ".github/workflows/agent-steward.yml").read_text())
    job = wf["jobs"]["steward"]
    steps = job["steps"]
    i = next(n for n, s in enumerate(steps) if "chief_clear.py" in (s.get("run") or ""))
    assert "/tmp/chief-clear.txt" in steps[i]["run"]
    assert "${{ github.token }}" in steps[i]["env"]["GH_TOKEN"]
    assert steps[i].get("if", "").startswith("always()")
    agent_steps = [n for n, s in enumerate(steps) if "claude-code-action" in (s.get("uses") or "")]
    assert agent_steps and max(agent_steps) < i, "the carrier must run after every agent step"
    for n in agent_steps:
        assert "Bash(gh pr edit:*)" in steps[n]["with"]["claude_args"]
    assert job["permissions"]["pull-requests"] == "write"



def test_QA_labels_left_over_from_an_earlier_commit_are_not_enough(tmp_path, monkeypatch, capsys):
    """#706, 2026-11-05: `main` was merged in after an independent PASS at
    b9077f6, and the labels stayed on the new head. The verdict comment names
    its sha; the labels cannot."""
    gh = FakeGh(comments=[(cc.RULER, f"QA: PASS — verified at {OTHER}"),
                          (cc.RULER, f"chief-cleared at {SHA}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []
    assert "may be left over from an earlier commit" in capsys.readouterr().out


def test_a_PASS_verdict_by_anyone_but_claude_bot_does_not_count(tmp_path, monkeypatch):
    gh = FakeGh(comments=[("someone", f"QA: PASS — verified at {SHA}"),
                          (cc.RULER, f"chief-cleared at {SHA}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_a_clearance_dispatches_one_agent_merge_sweep(tmp_path, monkeypatch):
    """#759: a label applied with github.token starts no run, so #749, #750,
    #758, #767 and #810 each waited for an unrelated edge or the throttled cron."""
    gh = FakeGh()
    assert run(tmp_path, monkeypatch, gh) == 0
    assert gh.dispatches == [["workflow", "run", "agent-merge.yml", "--repo", REPO, "--ref", "main"]]


def test_two_clearances_dispatch_only_one_sweep(tmp_path, monkeypatch):
    gh = FakeGh()
    text = f"pr=706 sha={SHA}\npr=707 sha={SHA}\n"
    assert run(tmp_path, monkeypatch, gh, text) == 0
    assert len(gh.dispatches) == 1 and len(gh.writes) == 4


def test_a_refused_clearance_dispatches_nothing(tmp_path, monkeypatch):
    for kw in ({"head": OTHER}, {"gates": ((1, T1, "completed", "failure"),)}, {"labels": "qa-pass,qa:independent"}):
        gh = FakeGh(**kw)
        assert run(tmp_path, monkeypatch, gh) == 1 and gh.dispatches == [], kw


def test_a_failed_dispatch_keeps_the_clearance_and_only_warns(tmp_path, monkeypatch, capsys):
    gh = FakeGh(fail={"workflow"})
    assert run(tmp_path, monkeypatch, gh) == 0 and len(gh.writes) == 2
    assert "could not dispatch agent-merge" in capsys.readouterr().out


def test_the_carrier_job_holds_actions_write_and_the_script_labels_nothing_new():
    wf = yaml.safe_load((ROOT / ".github/workflows/agent-steward.yml").read_text())
    assert wf["jobs"]["steward"]["permissions"]["actions"] == "write"
    src = (ROOT / "scripts" / "chief_clear.py").read_text()
    assert "qa-pass" not in src.split("def apply")[1].split("def dispatch_sweep")[0], \
        "the carrier must never write a QA label"
