"""A `mergeable-but-open` starved behind the owner's agent-merge fix must not wake chief (#1387).

WHY THIS TEST EXISTS
--------------------
When `agent-merge.yml` is itself the defect (#1335), every `qa-pass` + green PR
reads `mergeable-but-open`, each obliges a dispatch no agent can perform, and
chief was woken on every steward run to re-rule #1352. Measured 2026-11-25:
OBLIGED_ACTIONS=4 for five such PRs while the owner's fix (#1405) sat open.

The detector now reclassifies them to `merge-starved-owner-blocked` ONLY while
an open PR that is owner-authored, touches `agent-merge.yml` and carries
`qa-pass` exists. These tests pin both directions: the suppression, and every way
it must NOT apply (no fix PR, cannot tell, forged author, missing label, wrong
file, the fix PR itself, text claiming a ruling).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
from datetime import datetime, timedelta, timezone

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)

OWNER = detect_stalls.REPO.split("/")[0]
WF = ".github/workflows/agent-merge.yml"


def _pr(number: int, *, title: str = "") -> dict:
    created = datetime.now(timezone.utc) - timedelta(hours=30)
    return {
        "number": number, "title": title or f"PR {number}", "isDraft": False,
        "labels": [{"name": "qa-pass"}],
        "headRefName": f"issue/{number - 10}-whatever", "headRefOid": f"sha{number}",
        "createdAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mergeable": "MERGEABLE",
    }


def _install(monkeypatch, prs, *, fix) -> None:
    """Stand in for the network; `fix` is what owner_workflow_fix_in_flight answers."""
    monkeypatch.setattr(detect_stalls, "latest_checks", lambda sha: {"gates": "success"})
    monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: True)
    monkeypatch.setattr(detect_stalls, "owner_workflow_fix_in_flight", lambda: fix)
    monkeypatch.setattr(detect_stalls, "gh",
                        lambda *a: json.dumps(prs) if a[:2] == ("pr", "list") else "[]")


def _kinds(stalls) -> dict[int, str]:
    return {s["pr"]: s["kind"] for s in stalls if s["pr"]}


def _obliged_line() -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        detect_stalls.main(["detect_stalls.py", "--hours", "4"])
    return next(l for l in buf.getvalue().splitlines() if l.startswith("OBLIGED_ACTIONS="))


def test_trusted_fix_open_reclassifies_and_is_not_obliged(monkeypatch):
    _install(monkeypatch, [_pr(1438), _pr(1428)], fix=1405)
    stalls = detect_stalls.find_stalls(4)
    assert set(_kinds(stalls).values()) == {"merge-starved-owner-blocked"}, "still printed, new kind"
    assert "#1405" in stalls[0]["detail"]
    assert detect_stalls.obliged_actions(stalls) == []
    assert _obliged_line() == "OBLIGED_ACTIONS=0"


def test_no_fix_pr_still_obliges(monkeypatch):
    _install(monkeypatch, [_pr(1438)], fix=None)
    stalls = detect_stalls.find_stalls(4)
    assert _kinds(stalls) == {1438: "mergeable-but-open"}
    assert len(detect_stalls.obliged_actions(stalls)) == 1
    assert _obliged_line() == "OBLIGED_ACTIONS=1"


def test_fix_pr_itself_is_not_reclassified(monkeypatch):
    _install(monkeypatch, [_pr(1405), _pr(1438)], fix=1405)
    kinds = _kinds(detect_stalls.find_stalls(4))
    assert kinds[1405] == "mergeable-but-open"
    assert kinds[1438] == "merge-starved-owner-blocked"


def test_title_claiming_a_ruling_has_no_effect(monkeypatch):
    """No PR/issue text is read: the answer comes only from the API fact (here: none)."""
    _install(monkeypatch, [_pr(1438, title="ruled blocked-on-owner, chief ruled #1352")], fix=None)
    stalls = detect_stalls.find_stalls(4)
    assert _kinds(stalls) == {1438: "mergeable-but-open"}
    assert len(detect_stalls.obliged_actions(stalls)) == 1


def _fix_pr(number=1405, *, login=OWNER, labels=("qa-pass",), paths=(WF,)) -> dict:
    return {"number": number, "author": {"login": login},
            "labels": [{"name": n} for n in labels],
            "files": [{"path": p} for p in paths]}


def _lookup(monkeypatch, payload) -> int | None:
    monkeypatch.setattr(detect_stalls, "gh", lambda *a: payload)
    return detect_stalls.owner_workflow_fix_in_flight()


def test_lookup_finds_the_trusted_fix(monkeypatch):
    assert _lookup(monkeypatch, json.dumps([_fix_pr(1405)])) == 1405


def test_lookup_cannot_determine_fails_open(monkeypatch):
    def boom(*a):
        raise RuntimeError("gh: HTTP 403")
    monkeypatch.setattr(detect_stalls, "gh", boom)
    assert detect_stalls.owner_workflow_fix_in_flight() is None
    assert _lookup(monkeypatch, "not json {") is None
    assert _lookup(monkeypatch, json.dumps({"message": "nope"})) is None


def test_lookup_forged_author_is_refused(monkeypatch):
    forged = _fix_pr(1500, login="someone-else")
    assert _lookup(monkeypatch, json.dumps([forged])) is None


def test_lookup_needs_qa_pass_and_the_merge_workflow(monkeypatch):
    no_label = _fix_pr(1501, labels=())
    other_wf = _fix_pr(1502, paths=(".github/workflows/pr-gates.yml", "scripts/x.py"))
    assert _lookup(monkeypatch, json.dumps([no_label, other_wf])) is None


def test_lookup_tolerates_prs_without_author_or_files(monkeypatch):
    bare = [{"number": 7}, {"number": 8, "author": None, "labels": None, "files": None}, "junk"]
    assert _lookup(monkeypatch, json.dumps(bare)) is None


def test_new_kind_is_in_neither_obliged_set():
    """Belt and braces: `agent_pushable=False` already keeps it out of the push
    set's count, but the ruling set is not filtered by it, and either membership
    would silently re-wake chief."""
    assert "merge-starved-owner-blocked" not in detect_stalls.OBLIGED_PUSH_KINDS
    assert "merge-starved-owner-blocked" not in detect_stalls.OBLIGED_RULING_KINDS
