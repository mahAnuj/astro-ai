"""After a QA round FAILS on a session PR, the loop dispatches one fix
(scripts/pr_fix_after_qa.py, 2026-11-13: "let the loop fix session PRs too")."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pfq", ROOT / "scripts" / "pr_fix_after_qa.py")
pfq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pfq)

HEAD = "a" * 40
OLD = "b" * 40
REPO = "o/r"


class Gh:
    def __init__(self, *, branch="claude/session-x", head=HEAD, state="open", fork=False,
                 files=("src/astro_ai/x.py",), comments=()):
        self.pr = {"state": state, "head": {"ref": branch, "sha": head,
                                            "repo": {"full_name": "other/r" if fork else REPO}}}
        self.files, self.comments, self.posted = list(files), list(comments), []

    def __call__(self, args):
        if args[:2] == ["pr", "comment"]:
            self.posted.append(args)
            return ""
        url = args[-1]
        if url == f"repos/{REPO}/pulls/951":
            return json.dumps(self.pr)
        if url.startswith(f"repos/{REPO}/pulls/951/files"):
            return json.dumps([{"filename": f} for f in self.files])
        if url.startswith(f"repos/{REPO}/issues/951/comments"):
            return json.dumps(self.comments)
        raise AssertionError(args)


def fail(sha=HEAD, who="claude[bot]"):
    return {"user": {"login": who}, "body": f"QA: FAIL — verified at `{sha}`\nOne defect."}


def mark(sha):
    return {"user": {"login": "github-actions[bot]"}, "body": f"{pfq.FIX_MARK} {sha}\n\nx"}


def test_a_fail_on_the_current_head_of_a_session_pr_gets_one_fix():
    d = pfq.decide(Gh(comments=[fail()]), REPO, 951)
    assert d["action"] == "fix" and d["target"] == "fix_pr=951"


def test_the_same_head_never_gets_a_second_fix():
    d = pfq.decide(Gh(comments=[fail(), mark(HEAD)]), REPO, 951)
    assert d["action"] == "none" and "already dispatched" in d["why"]


def test_three_fixes_is_the_cap_then_a_person_takes_it():
    tried = [mark(f"{i:040x}") for i in range(pfq.MAX_PR_FIXES)]
    d = pfq.decide(Gh(comments=[*tried, fail()]), REPO, 951)
    assert d["action"] == "none" and "person" in d["why"]


def test_only_claude_bots_fail_naming_this_head_counts():
    assert pfq.decide(Gh(comments=[fail(OLD)]), REPO, 951)["action"] == "none"
    assert pfq.decide(Gh(comments=[fail(who="stranger")]), REPO, 951)["action"] == "none"
    passed = {"user": {"login": "claude[bot]"}, "body": f"QA: PASS — verified at `{HEAD}`"}
    assert pfq.decide(Gh(comments=[fail(), passed]), REPO, 951)["action"] == "none"


def test_issue_branches_workflow_diffs_forks_and_closed_prs_are_left_alone():
    assert pfq.decide(Gh(branch="issue/9-x", comments=[fail()]), REPO, 951)["action"] == "none"
    assert pfq.decide(Gh(files=(".github/workflows/a.yml",), comments=[fail()]), REPO, 951)["action"] == "none"
    assert pfq.decide(Gh(fork=True, comments=[fail()]), REPO, 951)["action"] == "none"
    assert pfq.decide(Gh(state="closed", comments=[fail()]), REPO, 951)["action"] == "none"


def test_the_marker_is_written_before_anything_is_dispatched(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.write_text("")
    monkeypatch.setenv("GH_REPO", REPO)
    monkeypatch.setenv("PR", "951")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    gh = Gh(comments=[fail()])
    assert pfq.main(["x"], gh) == 0
    assert gh.posted and f"{pfq.FIX_MARK} {HEAD}" in gh.posted[0][-1]
    assert "target=fix_pr=951" in out.read_text()


def test_it_shares_the_fix_marker_and_cap_with_red_gates():
    spec2 = importlib.util.spec_from_file_location("rg", ROOT / "scripts" / "red_gates.py")
    rg = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(rg)
    assert (pfq.FIX_MARK, pfq.MAX_PR_FIXES) == (rg.FIX_MARK, rg.MAX_PR_FIXES)


def test_the_cycle_doc_says_a_fix_run_never_judges_or_labels_itself():
    """Step 0d is prose the agent obeys; these lines are its independence rule."""
    doc = (ROOT / ".claude" / "commands" / "agent-cycle.md").read_text()
    assert "## Step 0d" in doc and "--fix-pr <n>" in doc
    assert "**no verdict is\nwritten**" in doc
    assert "run a QA round, write or remove a label, open a PR, or touch `.github/workflows/`" in doc
