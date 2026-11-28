#!/usr/bin/env python3
"""Wait for the pr-gates run agent-merge dispatched on main, then describe it (#1221).

WHY THIS EXISTS
---------------
`main-red-report.yml` listens for `workflow_run` of "PR gates". agent-merge merges
with GITHUB_TOKEN, whose push starts nothing, so after each merge it DISPATCHES
pr-gates on main (#797). GitHub then delivers that run's completion to the
reporter almost never: measured by steward on 2026-11-18, 1 of 20 dispatched
`main` runs produced a report, against 20 of 21 push and schedule runs. A
`workflow_run` chain stops after three levels (the same limit #826 hit), and a
dispatch from a run that was itself started by `workflow_run` sits past it. So a
red merge result went unreported, and a green one left an open sentinel standing
until the next push or the daily schedule.

So agent-merge now ALSO dispatches the reporter, with `after=<the time it
dispatched pr-gates>`. `workflow_dispatch` has no depth limit. This script finds
that pr-gates run (the oldest dispatched `main` run created at or after `after`),
waits for it to complete, and writes the four facts the `workflow_run` payload
would have carried to $GITHUB_ENV: GATES_SHA, GATES_URL, GATES_RUN_ID,
GATES_CONCLUSION. The reporter's own step is unchanged.

A RUN THAT WAS REPLACED IS NOT A RED MAIN. GitHub keeps one pending run per
concurrency group; a second merge's dispatch replaces a pending first one, which
concludes `cancelled` having run nothing (#1284 measured four false `[main-red]`
issues of that shape). A `cancelled` run in which NO STEP EVER RAN is reported
as replaced and nothing is written. Until 2026-11-26 the test was "a newer run
exists", which also swallowed a run that TIMED OUT with the next merge's run
queued behind it -- the case #461 exists for (#1486). A timed-out run has steps.

EXIT CODES: 0 described (or superseded / skipped, said why)   1 no run found, or
it did not complete in time   2 bad input or environment
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Callable

Runner = Callable[[list[str]], str]

WORKFLOW = "pr-gates.yml"
#: pr-gates' parallel jobs take ~17 min; its own timeout bounds a hung one.
MAX_WAIT_S = 55 * 60
#: How long a just-dispatched run may take to appear in the list at all.
FIND_WAIT_S = 5 * 60
POLL_S = 30
ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main_runs(gh: Runner, repo: str, after: datetime) -> list[dict]:
    """Dispatched pr-gates runs on main created at or after `after`, oldest first."""
    out = gh(["api", f"repos/{repo}/actions/workflows/{WORKFLOW}/runs"
                     f"?branch=main&event=workflow_dispatch&per_page=30"])
    runs = [r for r in json.loads(out).get("workflow_runs") or []
            if r.get("head_branch") == "main" and _ts(r["created_at"]) >= after]
    return sorted(runs, key=lambda r: (r["created_at"], r["id"]))


def never_started(gh: Runner, repo: str, run_id: int) -> bool:
    """True only when the run's job list was read and no step in it ever ran.
    An unreadable list answers False, so the run is reported, never swallowed."""
    try:
        jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"]))
    except (RuntimeError, ValueError):
        return False
    return not any(j.get("steps") for j in jobs.get("jobs") or [])


def await_run(gh: Runner, repo: str, after: datetime, sleep: Callable[[float], None] = time.sleep,
              max_wait: float = MAX_WAIT_S, find_wait: float = FIND_WAIT_S) -> tuple[int, dict | None, str]:
    waited = 0.0
    mine = None
    while True:
        try:
            runs = main_runs(gh, repo, after)
        except (RuntimeError, ValueError, KeyError) as exc:
            runs, note = [], f" (list failed: {str(exc)[:80]})"
        else:
            note = ""
        if mine is None and runs:
            mine = runs[0]["id"]
        cur = next((r for r in runs if r["id"] == mine), None)
        if cur and cur.get("status") == "completed":
            if cur.get("conclusion") == "cancelled" and never_started(gh, repo, mine):
                return 0, None, (f"run {mine} was cancelled before any step ran -- a pending run "
                                 "a newer one replaced; not a red main")
            if cur.get("conclusion") == "skipped":
                return 0, None, f"run {mine} concluded skipped -- nothing was asserted"
            return 0, cur, f"run {mine} completed: {cur.get('conclusion')}"
        if mine is None and waited >= find_wait:
            return 1, None, f"no dispatched pr-gates run on main appeared after {after:%H:%M:%SZ}{note}"
        if waited >= max_wait:
            return 1, None, f"run {mine} did not complete within {max_wait / 60:.0f} min{note}"
        sleep(POLL_S)
        waited += POLL_S


def main(argv: list[str], gh: Runner = run_gh, sleep: Callable[[float], None] = time.sleep) -> int:
    repo = os.environ.get("GH_REPO", "")
    after = os.environ.get("AFTER", "")
    out = os.environ.get("GITHUB_ENV", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not ISO.fullmatch(after) or not out:
        print("::error::await_main_gates.py needs GH_REPO=owner/name, AFTER=YYYY-MM-DDTHH:MM:SSZ and GITHUB_ENV")
        return 2
    rc, run, why = await_run(gh, repo, _ts(after), sleep)
    print(("" if rc == 0 else "::error::") + why)
    if run:
        sha, url = str(run.get("head_sha", "")), str(run.get("html_url", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or not url.startswith("https://github.com/"):
            print("::error::the run's head_sha or html_url is not in the expected shape")
            return 1
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"GATES_SHA={sha}\nGATES_URL={url}\nGATES_RUN_ID={int(run['id'])}\n"
                    f"GATES_CONCLUSION={re.sub(r'[^a-z_]', '', str(run.get('conclusion') or 'unknown'))}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
