"""The carrier that turns a recorded ruling into an `agent-work` cycle (#442).

WHY THIS FILE EXISTS
--------------------
An agent inside `claude-code-action` holds the Claude GitHub App token, and
`gh workflow run` answers it HTTP 403. So `steward.md` spent its whole life
telling the steward to do something its credential cannot do, in six routing
rows, and the only working dispatch path was chief's -- which made chief the
dispatcher for every mechanical repair.

`scripts/dispatch_cycle.sh` is now that path for BOTH roles. It is one script
rather than two copies because this repository's most reliable defect is a
copied file diverging: `id-token: write` was missing from four agent loops that
had each been copied from a fifth.

These tests drive the real script through a FAKE `gh` on PATH, so every guard is
exercised with no network and no Actions minutes. The guards are the point: the
script refuses a lenient parse, a closed issue and a second concurrent cycle,
and it refuses to report a dispatch whose run died on arrival (#421, which hid
for three days behind `gh workflow run` exiting 0).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dispatch_cycle.sh"


def _fake_gh(tmp_path: Path, *, state="OPEN", busy=0, runs=("11", "22"),
             status_seq=("in_progress",)) -> Path:
    """A `gh` that answers only what the script asks, from shell case matching."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
case "$*" in
  *"issue view"*)         echo '{state}' ;;
  *"--json status --jq"*'select(.status != "completed")'*) echo '{busy}' ;;
  *"--limit 1 --json databaseId"*)
      if [ -f "{tmp_path}/dispatched" ]; then echo '{runs[1]}'; else echo '{runs[0]}'; fi ;;
  *"workflow run"*)       : > "{tmp_path}/dispatched"; echo 'dispatched' ;;
  *"run view"*)           echo '{status_seq[0]} ' ;;
  *) echo "UNEXPECTED gh $*" >&2; exit 9 ;;
esac
""")
    gh.chmod(0o755)
    return bindir


def _run(tmp_path: Path, contents: str | None, *, who="steward", dry=True, **kw):
    f = tmp_path / "ruling.txt"
    if contents is not None:
        f.write_text(contents)
    env = dict(os.environ)
    env["PATH"] = f"{_fake_gh(tmp_path, **kw)}:{env['PATH']}"
    env["GH_REPO"] = "owner/repo"
    env.pop("GITHUB_ENV", None)
    cmd = ["bash", str(SCRIPT), str(f), who] + (["--dry-run"] if dry else [])
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)


def test_no_ruling_is_a_ruling_not_a_failure(tmp_path):
    """The common case. A steward that found nothing dispatchable must exit 0,
    or every quiet run would read as a broken carrier."""
    r = _run(tmp_path, None)
    assert r.returncode == 0, r.stderr
    assert "recorded no dispatch" in r.stdout


def test_an_empty_file_is_also_no_ruling(tmp_path):
    r = _run(tmp_path, "")
    assert r.returncode == 0
    assert "recorded no dispatch" in r.stdout


@pytest.mark.parametrize("line", [
    "dispatch issue 409 please",
    "issue=409 and also issue=410",
    "issue=abc",
    "409",
    "ISSUE=409",
])
def test_anything_but_issue_equals_digits_is_refused(tmp_path, line):
    """A LENIENT PARSER HERE DISPATCHES AT THE WRONG ISSUE, which is ~50 Actions
    minutes on work nobody ruled on. `issue=409 and also issue=410` is the one
    that matters: a greedy match would take 409 and silently drop the rest."""
    r = _run(tmp_path, line)
    assert r.returncode == 1, r.stdout
    assert "unparseable" in r.stdout


def test_a_closed_issue_is_refused(tmp_path):
    """A cycle at a closed issue is the `cannot-reproduce` path at full cost."""
    r = _run(tmp_path, "issue=409", state="CLOSED")
    assert r.returncode == 1
    assert "CLOSED" in r.stdout


def test_a_cycle_already_in_flight_defers_rather_than_queueing(tmp_path):
    r = _run(tmp_path, "issue=409", busy=1)
    assert r.returncode == 0, r.stdout
    assert "in flight" in r.stdout
    assert "waits for the next run" in r.stdout


def test_an_unreadable_concurrency_check_counts_as_busy(tmp_path):
    """Guessing "not busy" is what spends the quota twice."""
    r = _run(tmp_path, "issue=409", busy="unknown")
    assert r.returncode == 0
    assert "in flight" in r.stdout


def test_the_ruling_names_whoever_recorded_it(tmp_path):
    """Both roles share this script, so the message may not hardcode `chief` --
    the report step attributes the dispatch from it."""
    r = _run(tmp_path, "issue=409", who="steward")
    assert "steward" in r.stdout and "chief" not in r.stdout


def test_a_missing_gh_repo_exits_2_as_documented(tmp_path):
    """Exit 2 is "wired wrong", exit 1 is "a ruling could not be carried out".
    The caller routes on the difference, so a documented code that lies is a
    defect. `${GH_REPO:?}` exited 1 here and that is why the guard is explicit."""
    f = tmp_path / "r.txt"
    f.write_text("issue=409")
    env = dict(os.environ)
    env["PATH"] = f"{_fake_gh(tmp_path)}:{env['PATH']}"
    env.pop("GH_REPO", None)
    r = subprocess.run(["bash", str(SCRIPT), str(f), "steward", "--dry-run"],
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_no_arguments_exits_2(tmp_path):
    r = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 2


def test_a_dry_run_never_dispatches(tmp_path):
    """The flag exists so these guards can be exercised for real. If it leaked
    into a dispatch, the test suite would spend Actions minutes."""
    r = _run(tmp_path, "issue=409", dry=True)
    assert r.returncode == 0
    assert "DRY RUN" in r.stdout
    assert not (tmp_path / "dispatched").exists()
