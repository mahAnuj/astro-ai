#!/usr/bin/env python3
"""Are agent-queue's hourly steps (timers, liveness) due on THIS run?

WHY THIS EXISTS (2026-11-18)
----------------------------
The hourly backstop (#1186) ran timers and liveness only when
`github.event_name == 'schedule'`, so it depended entirely on GitHub's cron.
Measured on its first day: the `17 * * * *` schedule merged at 02:14 UTC,
fired ONCE, at 10:15, and not again through 17:38 -- one run in fifteen slots.
GitHub documents scheduled runs as best-effort, delayed or dropped under load;
this repo's `*/30` merge sweep already ran about every six hours. So timers did
not fire and liveness filed nothing, while the queue itself kept draining on
every event wake.

So every agent-queue run now asks this script. A scheduled run is always due.
Any other run (a handler's wake, an agent-work or steward completion) is due
when no agent-queue run in the last WINDOW_MIN minutes completed the timers
step successfully. The cron becomes a fallback, not the clock.

Both steps are safe to run twice: a timer's queue entry is keyed and the queue
dedupes it (#1187), and file_ops_findings.py files each finding once. That is
why an unreadable API answers "due" -- a duplicate run costs a minute, a missed
one costs an hour of silence, which is the defect this fixes.

OUTPUT: `due=true` or `due=false` appended to $GITHUB_OUTPUT, and the reason on
stdout. Always exits 0 on a decision; 2 on a bad environment.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Callable

Runner = Callable[[list[str]], str]

WORKFLOW = "agent-queue.yml"
#: The step whose success counts as "the hourly steps ran". Renaming it in
#: agent-queue.yml without changing this makes every run due (harmless, noisy);
#: tests/test_hourly_due.py pins that the two agree.
TIMER_STEP = "Fire due timers into the queue"
#: Under an hour, so a run at :55 past the last one still counts as due and the
#: cadence never slips past hourly.
WINDOW_MIN = 55
#: At most this many recent runs are opened (one jobs call each).
MAX_RUNS = 10


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def _ts(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def decide(gh: Runner, repo: str, event: str, this_run: str, now: datetime) -> tuple[bool, str]:
    if event == "schedule":
        return True, "a scheduled run is always due"
    since = now - timedelta(minutes=WINDOW_MIN)
    try:
        runs = json.loads(gh(["api", f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=30"]))
        recent = []
        for r in runs.get("workflow_runs") or []:
            at = _ts(r.get("run_started_at") or r.get("created_at") or "")
            if at is None or at < since or str(r.get("id")) == this_run:
                continue
            if r.get("status") != "completed":
                continue
            recent.append(r)
        for r in recent[:MAX_RUNS]:
            jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{r['id']}/jobs"]))
            for job in jobs.get("jobs") or []:
                for step in job.get("steps") or []:
                    if step.get("name") == TIMER_STEP and step.get("conclusion") == "success":
                        return False, f"run {r['id']} ran the hourly steps at {r.get('run_started_at')}"
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        return True, f"could not read recent runs ({str(exc)[:100]}); running them, both steps are idempotent"
    return True, f"no run in the last {WINDOW_MIN} min ran the hourly steps"


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::hourly_due.py needs GH_REPO=owner/name")
        return 2
    due, why = decide(gh, repo, os.environ.get("EVENT_NAME", ""), os.environ.get("THIS_RUN", ""),
                      now or datetime.now(timezone.utc))
    print(f"due={'true' if due else 'false'}: {why}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"due={'true' if due else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
