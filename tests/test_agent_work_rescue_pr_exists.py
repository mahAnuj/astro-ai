"""The rescue net must not open a second PR for work that already has one.

WHY THIS IS A TEST, given the charter in conftest.py.

Same footing as test_agent_work_push_net.py: shell inside a YAML string, which
nothing type-checks, and a failure mode that reports success.

Measured, and this is the whole reason the file exists. PR #660 merged at
2026-11-01T22:51:06Z. The rescue step of the cycle that had just finished its
round ran ten seconds later, asked `gh pr list --head <branch>` -- with no
`--state`, so `gh` answered for OPEN pull requests only -- got an empty list,
and opened PR #663 for the same head. Its diff against the merge base was
empty: a pull request for work already on main.

The wasted PR is the cheap half. A PR this step opens is authored by
`github-actions[bot]`, because the step has only `github.token`; `AGENT_AUTHORS`
in `qa-on-green.yml` and `agent-merge.yml` is `claude[bot],<owner>`. So neither
workflow will ever label it or merge it (#669), while `detect_stalls`, `steward`
and `chief` all read it, none of them filtering on author. One mis-timed query
therefore manufactures an immortal PR that consumes agent invocations and can
never be resolved by the loop -- the exact waste this repo is trying to remove.

The receipt step forty lines below has always used `--state all`. Only this
guard did not. These tests drive the real guard against a fake `gh` and pin
that MERGED, CLOSED and OPEN all suppress creation, and that a failed lookup
declines rather than creating.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WF = (Path(__file__).resolve().parent.parent
      / ".github" / "workflows" / "agent-work.yml")
JOB = yaml.safe_load(WF.read_text(encoding="utf-8"))["jobs"]


def _guard() -> str:
    """The `existing=` guard out of the net step, verbatim.

    Lifted, not reimplemented: a reimplementation passes forever while the
    workflow ships something else.
    """
    steps = next(iter(JOB.values()))["steps"]
    step = next(s for s in steps
                if s.get("name") == "Push the branch and open the PR")
    m = re.search(r"(existing=\$\(gh pr list.*?\n\s*fi)\n", step["run"], re.S)
    assert m, "the net's `existing=$(gh pr list ...)` guard is no longer recognisable"
    return m.group(1)


GUARD = _guard()


def _run(tmp_path: Path, listing: str, *, list_rc: int = 0) -> subprocess.CompletedProcess:
    """Drive the real guard with a fake `gh` that answers `pr list` with `listing`.

    The fake pipes `--jq` through the real `jq`, as `gh` does. An earlier fake
    in this repo swallowed `--jq` and handed bash a JSON string, which made a
    sound workflow look broken; see the note in test_steward_accountability.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(
        "#!/bin/bash\n"
        'if [ "$1" = "pr" ] && [ "$2" = "list" ]; then\n'
        f"  [ {list_rc} -ne 0 ] && exit {list_rc}\n"
        '  jqf=""\n'
        '  while [ $# -gt 0 ]; do\n'
        '    [ "$1" = "--jq" ] && jqf="$2"\n'
        '    shift\n'
        '  done\n'
        f"  printf '%s' {listing!r} | jq -r \"$jqf\"\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "create" ]; then\n'
        '  echo CREATED_A_PR\n'
        "  exit 0\n"
        "fi\n"
        'echo "unexpected: $*" >&2\n'
        "exit 9\n",
        encoding="utf-8",
    )
    (bin_dir / "gh").chmod(0o755)
    script = 'branch="rescue/me"\nGH_REPO="o/r"\n' + GUARD + "\n"
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
    )


# The measured incident: the PR for this head had MERGED ten seconds earlier.
# Under the old `--state open` query this is the case that opened #663.
def test_a_merged_pr_on_the_head_stops_a_second_one(tmp_path):
    p = _run(tmp_path, '[{"number":660,"state":"MERGED"}]')
    assert p.returncode == 0, p.stderr
    assert "CREATED_A_PR" not in p.stdout, (
        "the rescue opened a second PR for a head whose PR had already MERGED "
        "-- this is PR #663, and the PR it opens is an orphan (#669)"
    )
    assert "660" in p.stdout and "MERGED" in p.stdout, (
        "the step must name the PR it found and its state, so a reader of the "
        f"log can tell 'already landed' from 'declined'; got {p.stdout!r}"
    )


# A human closed it on purpose. Re-opening overrides that decision.
def test_a_closed_pr_on_the_head_stops_a_second_one(tmp_path):
    p = _run(tmp_path, '[{"number":642,"state":"CLOSED"}]')
    assert p.returncode == 0, p.stderr
    assert "CREATED_A_PR" not in p.stdout, (
        "a CLOSED PR means someone decided this work should not land; the "
        "rescue re-opened it anyway"
    )


# The case that always worked. Pinned so the fix cannot trade it away.
def test_an_open_pr_on_the_head_still_stops_a_second_one(tmp_path):
    p = _run(tmp_path, '[{"number":649,"state":"OPEN"}]')
    assert p.returncode == 0, p.stderr
    assert "CREATED_A_PR" not in p.stdout, p.stdout


# The whole point of the net: a finished branch with no PR gets one.
def test_a_head_with_no_pr_at_all_does_get_one(tmp_path):
    p = _run(tmp_path, "[]")
    assert p.returncode == 0, p.stderr
    assert "CREATED_A_PR" in p.stdout, (
        "no PR exists for this head and the rescue declined to open one -- "
        "that is the work loss the net exists to prevent"
    )


# A failed read is not "no PR". Creating on a failed read manufactures the
# orphan, so the only safe answer is to decline and say so.
def test_a_failed_lookup_declines_rather_than_creating(tmp_path):
    p = _run(tmp_path, "[]", list_rc=1)
    assert "CREATED_A_PR" not in p.stdout, (
        "the lookup FAILED and the rescue created a PR anyway; a failed read "
        "cannot distinguish 'no PR' from 'a PR this would duplicate'"
    )
    assert "could not list" in (p.stdout + p.stderr), (
        f"a declined rescue must say why; got {p.stdout!r} {p.stderr!r}"
    )


def test_the_guard_asks_for_every_state(tmp_path):
    """Static, and it is the defect itself.

    `gh pr list` defaults to `--state open`. The guard must say `--state all`
    out loud; the behavioural tests above cannot tell a correct query from a
    fake that answers generously.
    """
    assert "--state all" in GUARD, (
        "the rescue's PR lookup does not pass `--state all`, so it reads OPEN "
        "pull requests only and will open a duplicate for a head whose PR "
        "merged moments earlier (PR #663, measured)"
    )
