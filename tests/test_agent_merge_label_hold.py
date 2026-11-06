"""`needs-human-review` must hold a PR on EVERY path, not only in the sweep (#604).

The sweep filter refuses the label. The edge-triggered path did not: the
`QA verdict` step's `case` read `qa-fail` and `qa-pass` and nothing else, so a
PR carrying `needs-human-review` + `qa-pass` + green gates passed it. The
comment above the `own` step asserted the opposite in prose -- "the sweep
filter and the labels step both refuse" -- which is the drift this repo keeps
paying for: a rule restated as prose, believed, and false.

WHY THE HOLE NEVER MERGED A BOUNDARY PR. The `Trust boundary` step is a PATH
check against $TRUST_BOUNDARY and runs on both paths, so a PR touching
`.github/workflows/` was held by its diff whatever the label said. The hole was
for the label's OTHER job -- holding a PR that touches no boundary path, the
only way a human or `chief` says "not this one". That worked in the `*/30`
sweep and not on the edge, so whether it held was a race on which fired first.

These tests DRIVE the real step. The `case` is a YAML string nothing
type-checks, and the failure is silent in the worst way: the PR merges.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MERGE = ROOT / ".github" / "workflows" / "agent-merge.yml"


def _qa_step() -> dict:
    doc = yaml.safe_load(MERGE.read_text())
    steps = doc["jobs"]["merge"]["steps"]
    return next(s for s in steps if s.get("id") == "qa")


HEAD = "c" * 40


def _drive(labels: str, tmp_path: Path, passed_at: str = HEAD) -> tuple[int, str, str]:
    """Run the step's own `run:` block with a fake `gh` returning `labels`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    # The step calls `gh pr view N --json labels --jq '...'` (the real --jq
    # joins names with a comma, so the fake prints that) and, on qa-pass, the
    # comments API -- answered by applying the step's OWN --jq with real jq
    # over a PASS bound to PR_SHA, so the SHA binding is exercised, not stubbed.
    comments = tmp_path / "comments.json"
    comments.write_text(json.dumps(
        [{"id": 1, "user": {"login": "claude[bot]"}, "body": f"QA: PASS — verified at `{passed_at}`\nok"}]))
    gh.write_text(f"""#!/usr/bin/env bash
filter=""; prev=""
for a in "$@"; do [ "$prev" = "--jq" ] && filter="$a"; prev="$a"; done
case "$*" in
  *"/comments"*) jq -r "$filter" {comments} ;;
  *"--json labels"*) printf '%s\\n' "$FAKE_LABELS" ;;
  *) exit 9 ;;
esac
""")
    gh.chmod(0o755)

    out_file = tmp_path / "gh_output"
    out_file.write_text("")
    script = _qa_step()["run"]
    p = subprocess.run(
        ["bash", "-e", "-c", script],
        capture_output=True, text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "FAKE_LABELS": labels,
            "GITHUB_OUTPUT": str(out_file),
            "GH_REPO": "mahAnuj/astro-ai",
            "PR_NUMBER": "550",
            "PR_SHA": HEAD,
            "REPO_OWNER": "mahAnuj",
        },
    )
    return p.returncode, p.stdout + p.stderr, out_file.read_text()


# ---------------------------------------------------------------- the defect

def test_needs_human_review_blocks_the_edge_triggered_path(tmp_path):
    """THE DEFECT. qa-pass + needs-human-review used to set ok=true."""
    rc, log, out = _drive("qa-pass,needs-human-review,qa:independent", tmp_path)
    assert rc == 0, log
    assert "ok=true" not in out, (
        "needs-human-review did not hold the PR on the edge-triggered path "
        "-- this is #604, and a held PR would have merged")
    assert "needs-human-review" in log


def test_needs_human_review_alone_also_blocks(tmp_path):
    rc, log, out = _drive("needs-human-review", tmp_path)
    assert rc == 0, log
    assert "ok=true" not in out


# ------------------------------------------------- nothing else regressed

def test_a_plain_qa_pass_still_merges(tmp_path):
    """The fix must not pay for itself by refusing everything."""
    rc, log, out = _drive("qa-pass,qa:independent", tmp_path)
    assert rc == 0, log
    assert "ok=true" in out, log


def test_qa_fail_still_wins_over_everything(tmp_path):
    rc, log, out = _drive("qa-pass,qa-fail,needs-human-review", tmp_path)
    assert rc == 0, log
    assert "ok=true" not in out
    assert "qa-fail" in log


def test_no_verdict_still_leaves_the_pr_open(tmp_path):
    rc, log, out = _drive("", tmp_path)
    assert rc == 0, log
    assert "ok=true" not in out


@pytest.mark.parametrize("labels,merges", [
    ("qa-pass", True),
    ("qa-pass,qa:independent", True),
    ("qa-pass,needs-human-review", False),
    ("qa-pass,qa-fail", False),
    ("needs-human-review", False),
    ("qa-fail", False),
    ("", False),
    ("qa:independent", False),
])
def test_the_label_matrix(labels, merges, tmp_path):
    """Every combination, so a future edit to the `case` cannot change one
    branch's meaning without a named row going red. Single-axis testing is
    what let #604 stand: `qa-fail` and `qa-pass` were each tested alone."""
    _, log, out = _drive(labels, tmp_path)
    assert ("ok=true" in out) is merges, f"{labels!r}: {log}"


# -------------------------------------------- the prose cannot drift again

def test_the_sweep_filter_and_this_step_refuse_the_same_label():
    """The two places that must agree, asserted rather than claimed in a
    comment. The comment claiming it was false for weeks."""
    text = MERGE.read_text()
    sweep = "needs-human-review" in text.split("jobs:")[0] or 'index("needs-human-review")' in text
    assert sweep, "the sweep filter no longer refuses needs-human-review"
    assert "*,needs-human-review,*)" in _qa_step()["run"], (
        "the QA verdict step no longer refuses needs-human-review")



def test_a_qa_pass_for_an_EARLIER_commit_does_not_merge(tmp_path):
    """2026-11-05. A label cannot say which commit it is about and survives a
    push (#609 merged on one). A `main` merged into a passed PR used to ship
    unreviewed; the step now requires a QA: PASS comment naming the head."""
    rc, log, out = _drive("qa-pass,qa:in-cycle", tmp_path, passed_at="d" * 40)
    assert rc == 0, log
    assert "ok=true" not in out
    assert "from an earlier commit" in log
