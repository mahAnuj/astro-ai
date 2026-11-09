#!/usr/bin/env python3
"""Decide whether a cycle-triggered measurement refresh is due.

WHY THIS EXISTS
---------------
`agent-measure` used to refresh its collectors on a clock: 21:00 for the
analyst plus seven collector slots (02:00 and every 3h from 05:00). Measured
2026-11-05..09, GitHub's cron throttling delivered about FOUR runs a day at
irregular times, and the analyst's 21:00 slot started 00:09-01:20Z. Meanwhile
what these files describe -- loop outcomes, agent health, the Claude quota
`chain_cycle.py` gates on -- changes when a CYCLE finishes, not on the hour.

So the collectors now also run when `agent-work` completes (`workflow_run`).
Cycles finish up to ~20 times a day once chaining and QA rounds are counted,
and every refresh opens a measurement PR, so this debounces:

  * NOT due if a measurement commit landed on `main` less than `MIN_GAP` ago:
    the panel is already that fresh, and another PR is noise.
  * NOT due while an earlier measurement PR is still open and younger than
    `STUCK_AFTER`: a second PR on the same six files conflicts with the first
    -- that is exactly how #800 and #805 stacked on 2026-11-08. One older than
    `STUCK_AFTER` is stuck rather than in flight, and a fresh refresh is the
    right response to a stuck one, so it no longer blocks.

Scheduled and dispatched runs are always due: the analyst slot must run, and
a human asking for a measurement means it.

Prints `due=true|false` and the reason. Fails OPEN (`due=true`): a refresh
that could not check is one extra PR, while a refresh wrongly skipped is a
stale quota reading under the chaining gate.

EXIT CODES: 0 always (the decision is the output)   2 bad env
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

MIN_GAP = timedelta(minutes=60)
STUCK_AFTER = timedelta(hours=3)
PUBLISHER = "shubhagya-publisher[bot]"
#: One file every measurement commit rewrites (collect_loop_measurements.py).
MARKER = "measurements/loop.json"


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def decide(gh: Runner, repo: str, event: str, now: datetime) -> tuple[bool, str]:
    if event != "workflow_run":
        return True, f"a {event} run is always due"
    commits = json.loads(gh(["api", f"repos/{repo}/commits?sha=main&path={MARKER}&per_page=1"]))
    if commits:
        age = now - _ts(commits[0]["commit"]["committer"]["date"])
        if age < MIN_GAP:
            return False, f"a measurement landed on main {age.total_seconds() / 60:.0f} min ago"
    prs = json.loads(gh(["api", f"repos/{repo}/pulls?state=open&per_page=100"]))
    for pr in prs:
        if (pr.get("user") or {}).get("login") == PUBLISHER \
                and pr["head"]["ref"].startswith("measurements/"):
            age = now - _ts(pr["created_at"])
            if age < STUCK_AFTER:
                return False, (f"measurement PR #{pr['number']} is still open "
                               f"({age.total_seconds() / 60:.0f} min old)")
    return True, "no recent measurement and none in flight"


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::measure_due.py needs GH_REPO=owner/name")
        return 2
    event = os.environ.get("EVENT_NAME", "")
    try:
        due, reason = decide(gh, repo, event, now or datetime.now(timezone.utc))
    except (RuntimeError, ValueError, KeyError) as exc:
        due, reason = True, f"could not check ({exc.__class__.__name__}); failing open"
    print(f"due={'true' if due else 'false'}: {reason}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"due={'true' if due else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
