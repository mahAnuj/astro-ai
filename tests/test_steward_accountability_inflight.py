"""A cycle already in flight is the system working, not the watcher failing.

WHY THIS IS A TEST, given the charter in conftest.py.

`agent-steward.yml`'s accountability step decides whether to wake `chief`, and
it is shell inside a YAML string that nothing type-checks. Getting it wrong is
not an exception: it is a Claude invocation spent on a ruling with no possible
act, repeated on every run.

THE DEFECT, MEASURED 2026-11-01. The step counted only `agent-work` runs
CREATED since `$SINCE`. But the steward's own guard 1 says:

    "Is a cycle already running or queued? If anything is in_progress or
     queued, dispatch nothing and say so."

So a steward that correctly stood down produced `cycles=0`, which this step
could not tell from a steward that simply failed -- and it logged "NOTHING
happened - Waking chief." chief then also had nothing to do. Across four PRs
that day, 26 comments were written; the steward's six and chief's five produced
no act, and chief ruled three times on one unchanged SHA.

This is the THIRD link in that chain, and the one in a workflow file. The other
two are the verdict-age floor in `detect_stalls.py` and the per-head guards in
both prompts, all in this PR.

WHAT IT MUST NOT DO is excuse a real failure. `inflight=0` with nothing
dispatched and nothing filed is still the case chief exists for, and
`test_a_steward_that_did_nothing_with_nothing_running_still_wakes_chief` is the
guard on that.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-steward.yml"
DOC = yaml.safe_load(WF.read_text(encoding="utf-8"))
STEPS = DOC["jobs"]["steward"]["steps"]
ACTED = next(s for s in STEPS if s.get("id") == "acted")
RUN = ACTED["run"]

SINCE = "2026-11-01T10:00:00Z"


_FAKE_GH_TEMPLATE = "#!/usr/bin/env python3\nimport json, subprocess, sys\nargv = sys.argv[1:]\njoined = ' '.join(argv)\nif 'run' in argv and 'list' in argv:\n    payload = __RUNS__\nelif 'issue' in argv and 'list' in argv:\n    payload = __ISSUES__\nelse:\n    sys.stderr.write('unexpected gh call: ' + joined)\n    raise SystemExit(9)\nif '--jq' in argv:\n    expr = argv[argv.index('--jq') + 1]\n    r = subprocess.run(['jq', '-r', expr], input=payload,\n                       capture_output=True, text=True)\n    sys.stdout.write(r.stdout)\n    raise SystemExit(r.returncode)\nsys.stdout.write(payload)\n"


def _fake_gh(tmp_path: Path, runs: list, issues: list) -> Path:
    """A `gh` that answers the two calls this step makes, and nothing else.

    IT HONOURS `--jq`, which the first draft of this harness did not -- and the
    omission produced a failure that looked like a defect in the workflow. The
    real `gh issue list --json createdAt --jq '... | length'` returns a NUMBER,
    because gh applies the filter itself; a fake returning the raw array fed
    `[ "$issues" -gt 0 ]` a JSON string and bash said "integer expression
    expected". A fake that answers differently from the real tool tests the
    fake.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    body = (_FAKE_GH_TEMPLATE
            .replace("__RUNS__", repr(json.dumps(runs)))
            .replace("__ISSUES__", repr(json.dumps(issues))))
    gh.write_text(body, encoding="utf-8")
    gh.chmod(0o755)
    return bin_dir


def _run(tmp_path: Path, *, runs: list, issues: list, stalls: str = "OBLIGED_ACTIONS=2"):
    out = tmp_path / "out"
    out.write_text("")
    Path("/tmp/stalls.txt").write_text(stalls + "\n", encoding="utf-8")
    env = dict(os.environ)
    env.update({
        "PATH": f"{_fake_gh(tmp_path, runs, issues)}:{env['PATH']}",
        "GH_TOKEN": "x", "GH_REPO": "owner/repo", "SINCE": SINCE,
        "GITHUB_OUTPUT": str(out),
    })
    p = subprocess.run(["bash", "-c", RUN], capture_output=True, text=True,
                       env=env, timeout=120)
    ok = None
    for line in out.read_text().splitlines():
        if line.startswith("ok="):
            ok = line[3:]
    return ok, p.stdout + p.stderr, p.returncode


def _run_obj(created: str, status: str = "completed") -> dict:
    return {"createdAt": created, "status": status}


# --- the defect, executed ---------------------------------------------------

def test_a_cycle_already_in_flight_does_not_wake_chief(tmp_path):
    """THE CASE. The cycle started BEFORE this steward run, so it is not
    counted by `createdAt > $SINCE` -- and guard 1 forbade dispatching another.
    Standing down was correct."""
    ok, log, rc = _run(tmp_path,
                       runs=[_run_obj("2026-11-01T09:00:00Z", "in_progress")],
                       issues=[])
    assert rc == 0, log
    assert ok == "true", f"chief would be woken; log:\n{log}"
    assert "in flight" in log


def test_a_queued_cycle_counts_the_same_as_a_running_one(tmp_path):
    """`queued` is the state GitHub puts a second dispatch in, and it is exactly
    what guard 1 tells the steward to stand down for."""
    ok, log, rc = _run(tmp_path,
                       runs=[_run_obj("2026-11-01T08:00:00Z", "queued")],
                       issues=[])
    assert ok == "true", log


def test_it_says_standing_down_rather_than_claiming_the_steward_acted(tmp_path):
    """Two different facts. "There was nothing to do" and "it did something"
    must not print the same sentence, or the next reader cannot tell a working
    loop from a busy one."""
    ok, log, _ = _run(tmp_path,
                      runs=[_run_obj("2026-11-01T09:00:00Z", "in_progress")],
                      issues=[])
    assert ok == "true"
    assert "standing down was correct" in log
    assert "the steward acted" not in log


# --- and it must not excuse a real failure ----------------------------------

def test_a_steward_that_did_nothing_with_nothing_running_still_wakes_chief(tmp_path):
    """THE GUARD ON THE GUARD. This is the case the accountability step exists
    for: actionable findings, no cycle, no issue, nothing in flight."""
    ok, log, _ = _run(tmp_path, runs=[_run_obj("2026-10-31T09:00:00Z")], issues=[])
    assert ok == "false", f"a real inaction was excused; log:\n{log}"
    assert "NOTHING happened" in log


def test_a_fresh_dispatch_still_counts_as_acting(tmp_path):
    ok, log, _ = _run(tmp_path,
                      runs=[_run_obj("2026-11-01T10:30:00Z", "completed")],
                      issues=[])
    assert ok == "true", log
    assert "the steward acted" in log


def test_a_filed_issue_still_counts_as_acting(tmp_path):
    ok, log, _ = _run(tmp_path, runs=[],
                      issues=[{"createdAt": "2026-11-01T10:30:00Z"}])
    assert ok == "true", log


def test_no_obliged_action_short_circuits_before_any_api_call(tmp_path):
    """Nothing demanded an action, so nothing is owed and no run history is
    read. The cheap path stays cheap."""
    ok, log, rc = _run(tmp_path, runs=[], issues=[], stalls="OBLIGED_ACTIONS=0")
    assert rc == 0, log
    assert ok == "true"
    assert "nothing in the findings obliged an action" in log


@pytest.mark.parametrize("runs", [[], "not-json"])
def test_an_unreadable_run_list_does_not_crash_the_step(tmp_path, runs):
    """`gh` failing must not take the step down: a crashed accountability check
    reports nothing at all, which is worse than either verdict."""
    payload = runs if isinstance(runs, list) else []
    ok, log, rc = _run(tmp_path, runs=payload, issues=[])
    assert rc == 0, log
    assert ok in ("true", "false"), log


# --- static: the two counts are distinct and both are read ------------------

def test_both_counts_are_computed_from_one_api_call():
    """One `gh run list` with `createdAt,status`, not two calls. The second call
    could answer differently from the first and the step would compare two
    moments as though they were one."""
    assert "--json createdAt,status" in RUN
    assert RUN.count("gh run list") == 1, "the run history is read twice"


def test_the_inflight_branch_is_tested_before_the_acted_branch():
    """Order matters: an in-flight cycle with nothing new dispatched must report
    "standing down", not fall through to the failure branch."""
    assert RUN.index('"$inflight" -gt 0') < RUN.index('"$cycles" -gt 0')


def test_every_value_reaches_the_shell_as_an_env_var():
    """A privileged trigger makes a `${{ }}` in a run block an injection sink,
    and `verify_workflows.py` fails the build on one."""
    assert "${{" not in RUN
