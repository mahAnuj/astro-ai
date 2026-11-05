"""chief's clearance carrier (#719).

chief could post `chief-cleared at <sha>` and never apply the label, because
both steps that run it deny `gh pr edit` -- PR #706 sat held seven hours after
the ruling. scripts/chief_clear.py carries the ruling out from a `run:` step,
and re-reads every precondition from the API rather than trusting the file."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("chief_clear", ROOT / "scripts" / "chief_clear.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules["chief_clear"] = cc
_spec.loader.exec_module(cc)

REPO = "o/r"
SHA = "b9077f6b65a881a5b4108cc4df1f33210c0affc9"
OTHER = "a" * 40


class FakeGh:
    def __init__(self, *, state="open", head=SHA,
                 labels="needs-human-review,qa-pass,qa:independent",
                 gates="success", comments=None, fail=None):
        self.state, self.head, self.labels, self.gates = state, head, labels, gates
        # (login, body)
        self.comments = comments if comments is not None else [
            (cc.RULER, f"**chief ruling**\n\nchief-cleared at {SHA}")]
        self.fail = fail or set()
        self.writes: list[list[str]] = []

    def __call__(self, args):
        url = args[1] if args[1] != "-X" else args[3]
        for f in self.fail:
            if f in url:
                raise RuntimeError("boom")
        if args[1] == "-X":
            self.writes.append(args)
            return "{}"
        if re.search(r"/pulls/\d+$", url):
            return f"{self.state}\t{self.head}\t{self.labels}\n"
        if "/check-runs" in url:
            return self.gates + "\n"
        if "/comments" in url:
            want = re.search(r'contains\("chief-cleared at ([0-9a-f]+)"\)', args[-1]).group(1)
            who = re.search(r'login == "([^"]+)"', args[-1]).group(1)
            return str(sum(1 for l, b in self.comments if l == who and f"chief-cleared at {want}" in b)) + "\n"
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
    gh = FakeGh(comments=[])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []
    assert "the ruling comes first" in capsys.readouterr().out


def test_a_ruling_comment_by_anyone_but_claude_bot_does_not_count(tmp_path, monkeypatch):
    gh = FakeGh(comments=[("someone", f"chief-cleared at {SHA}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_a_ruling_bound_to_another_sha_does_not_count(tmp_path, monkeypatch):
    gh = FakeGh(comments=[(cc.RULER, f"chief-cleared at {OTHER}")])
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_an_in_cycle_qa_pass_is_not_enough(tmp_path, monkeypatch):
    """chief.md precondition 1 -- the #712 case: qa:in-cycle only."""
    gh = FakeGh(labels="needs-human-review,qa-pass,qa:in-cycle")
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_qa_fail_is_a_verdict_not_a_hold(tmp_path, monkeypatch):
    gh = FakeGh(labels="needs-human-review,qa-pass,qa:independent,qa-fail")
    assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == []


def test_red_or_missing_gates_are_refused(tmp_path, monkeypatch):
    for gates in ("failure", "", "success,failure"):
        gh = FakeGh(gates=gates)
        assert run(tmp_path, monkeypatch, gh) == 1 and gh.writes == [], gates


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
