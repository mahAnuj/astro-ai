"""Workflow halves of four QA follow-ups the loop cannot author (session PR, 2026-11-26):
#1283 rename detection, #1290 qa-on-green's group, #1299 a failed compare, #1286 an unread
chief ruling. Each pins the shape a revert would undo."""
from __future__ import annotations

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _doc(name):
    return yaml.safe_load((WF / name).read_text())


def _runs(name):
    doc = _doc(name)
    return "\n".join(s.get("run", "") for j in doc["jobs"].values() for s in j.get("steps", []))


def test_the_scope_diff_lists_both_sides_of_a_rename():
    """#1283: rename detection prints only the new path, so src/ -> measurements/ read as
    measurements-only and the gates skipped while the merge deleted a shipped file."""
    for wf in ("pr-gates.yml", "verify-build.yml"):
        line = next(l for l in _runs(wf).splitlines() if "changed=$(" in l and "git diff --name-only" in l)
        assert "--no-renames" in line, f"{wf}: {line.strip()}"


def test_qa_on_green_serialises_per_branch_not_per_workflow():
    group = _doc("qa-on-green.yml")["concurrency"]["group"]
    assert group == "qa-on-green-${{ github.event.workflow_run.head_branch }}"


def test_a_failed_compare_is_red_not_a_silent_skip():
    run = _runs("close-on-evidence.yml")
    i = run.index('if [ "$rel" = "error" ]; then')
    assert run.index("exit 1", i) < run.index('if [ "$rel" != "ahead" ]; then')


def test_an_unread_chief_ruling_keeps_the_label():
    """#1286: non-numeric counted as zero, and the step then removed `chief-cleared` as stale."""
    run = next(s["run"] for s in _doc("agent-merge.yml")["jobs"]["merge"]["steps"] if s.get("id") == "boundary")
    assert '| length" 2>/dev/null || echo unreadable)' in run
    keep = run.index("keeping the hold and the label")
    assert run.index("exit 0", keep) < run.index('--remove-label "chief-cleared"')
