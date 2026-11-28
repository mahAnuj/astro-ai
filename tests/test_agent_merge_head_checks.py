"""agent-merge's HEAD_CHECKS_FN: one definition of "the head's checks are green" (2026-11-23).

Measured that day: #1335 (qa-pass, every gate green on b0d9aa7) was refused on every sweep
since 2026-11-21 by two check runs that could never be superseded -- `merge=failure` from an
EARLIER agent-merge run, and `mutants=cancelled` from a superseded pr-gates run whose job
#1262 had renamed to `mutants (0..3)`. These tests run the workflow's own function, lifted
from the YAML, against a `gh` that replays that commit's check runs.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FN = yaml.safe_load((ROOT / ".github/workflows/agent-merge.yml").read_text())["jobs"]["merge"]["env"]["HEAD_CHECKS_FN"]
GATES, MERGE = ".github/workflows/pr-gates.yml", ".github/workflows/agent-merge.yml"


def cr(name, conclusion, run, started, status="completed", cid=None):
    return {"name": name, "status": status, "conclusion": conclusion, "started_at": started,
            "id": cid or hash((name, run, started)) % 10**9,
            "details_url": f"https://github.com/o/r/actions/runs/{run}/job/1"}


def run_fn(checks, runs, fail_checks=False):
    """runs: run id -> (workflow path, created_at[, status])."""
    return run_fn_raw({"check_runs": checks}, runs, fail_checks)


def run_fn_raw(payload, runs, fail_checks=False):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "checks.json").write_text(json.dumps(payload))
        for rid, spec in runs.items():
            path, at, *st = spec
            (d / f"run-{rid}").write_text(f"{path} {at} {st[0] if st else 'completed'}")
        gh = d / "gh"
        gh.write_text(f"""#!/bin/bash
url=""; for a in "$@"; do case "$a" in repos/*) url="$a";; esac; done
case "$url" in
  */check-runs*) {'exit 1' if fail_checks else f'cat {d}/checks.json'} ;;
  */actions/runs/*) rid="${{url##*/}}"; cat "{d}/run-$rid" 2>/dev/null || exit 1 ;;
  *) exit 1 ;;
esac
""")
        gh.chmod(0o755)
        env = {"PATH": f"{d}:{os.environ['PATH']}", "GH_REPO": "o/r",
               "GITHUB_WORKFLOW_REF": f"o/r/{MERGE}@refs/heads/main"}
        r = subprocess.run(["bash", "-c", FN + '\nhead_checks deadbeef; echo "rc=$?"'],
                           capture_output=True, text=True, env=env)
    lines = [l for l in r.stdout.splitlines() if l and not l.startswith("rc=")]
    rc = int(r.stdout.strip().splitlines()[-1].split("=")[1])
    return lines, rc, r.stderr


RUNS_1335 = {"100": (MERGE, "2026-11-21T05:12:20Z"), "101": (MERGE, "2026-11-21T05:12:21Z"),
             "200": (GATES, "2026-11-21T05:13:50Z"), "201": (GATES, "2026-11-21T05:14:04Z"),
             "202": (GATES, "2026-11-21T05:14:10Z")}
CHECKS_1335 = [
    cr("merge", "success", "101", "2026-11-21T05:12:22Z"),
    cr("merge", "failure", "100", "2026-11-21T05:12:25Z"),
    cr("mutants", "cancelled", "201", "2026-11-21T05:14:06Z"),
    cr("suite", "cancelled", "201", "2026-11-21T05:14:06Z"),
    cr("gates", "failure", "201", "2026-11-21T05:14:20Z"),
    cr("suite", "success", "200", "2026-11-21T05:14:00Z"),
    cr("suite", "success", "202", "2026-11-21T05:14:12Z"),
    cr("mutants (0)", "success", "202", "2026-11-21T05:14:12Z"),
    cr("gates", "success", "202", "2026-11-21T05:20:00Z"),
]


def test_the_1335_shape_is_green():
    lines, rc, err = run_fn(CHECKS_1335, RUNS_1335)
    assert rc == 0, err
    assert sorted(lines) == ["gates=completed:success", "mutants (0)=completed:success",
                             "suite=completed:success"]


def test_this_workflows_own_runs_never_vote():
    lines, _, _ = run_fn(CHECKS_1335, RUNS_1335)
    assert not any(l.startswith("merge=") for l in lines)


def test_a_red_check_in_the_newest_run_still_blocks():
    checks = CHECKS_1335 + [cr("verify", "failure", "202", "2026-11-21T05:15:00Z")]
    lines, _, _ = run_fn(checks, RUNS_1335)
    assert "verify=completed:failure" in lines


def test_a_newest_run_still_running_is_pending_not_green():
    runs = {**RUNS_1335, "203": (GATES, "2026-11-21T06:00:00Z")}
    checks = CHECKS_1335 + [cr("gates", None, "203", "2026-11-21T06:00:05Z", status="in_progress")]
    lines, _, _ = run_fn(checks, runs)
    assert "gates=in_progress:pending" in lines


def test_a_check_from_another_app_still_counts():
    checks = CHECKS_1335 + [{"name": "external", "status": "completed", "conclusion": "failure",
                             "started_at": "2026-11-21T05:30:00Z", "id": 9, "details_url": "https://ci.example/9"}]
    lines, _, _ = run_fn(checks, RUNS_1335)
    assert "external=completed:failure" in lines


def test_unreadable_checks_or_runs_are_never_a_pass():
    _, rc, _ = run_fn(CHECKS_1335, RUNS_1335, fail_checks=True)
    assert rc == 2
    missing = {k: v for k, v in RUNS_1335.items() if k != "202"}
    _, rc, _ = run_fn(CHECKS_1335, missing)
    assert rc == 2


def test_a_newest_run_still_in_flight_reads_pending_not_green():
    """#1415: the newest pr-gates run on the head has green early jobs but no `gates` job yet
    (it needs the other four); the older run's red `gates` drops out, so the head must read
    pending until the newest run completes."""
    runs = {**RUNS_1335, "203": (GATES, "2026-11-21T06:00:00Z", "in_progress")}
    checks = CHECKS_1335 + [cr("suite", "success", "203", "2026-11-21T06:00:05Z")]
    lines, rc, _ = run_fn(checks, runs)
    assert rc == 0 and "run:pr-gates.yml=in_progress:pending" in lines


def test_more_than_one_page_of_check_runs_is_unreadable_not_truncated():
    """#1413 (minor): past 100 check runs the oldest would drop silently and could fail open."""
    big = {"check_runs": CHECKS_1335, "total_count": 101}
    lines, rc, _ = run_fn_raw(big, RUNS_1335)
    assert rc == 2
