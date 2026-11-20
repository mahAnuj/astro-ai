#!/usr/bin/env python3
"""Keep one agent-queue run always on its way, so the loop cannot sit dead.

WHY THIS EXISTS (2026-11-20)
----------------------------
Every wake the loop has is either an event (a cycle completing, a handler
queueing a ruling) or a GitHub cron. When the events stop, only cron is left,
and GitHub documents scheduled runs as best-effort. Measured 2026-11-19 12:00Z
to 2026-11-20 15:17Z: the hourly `17 * * * *` agent-queue schedule fired 3
times in 27 slots (18:16Z, 00:41Z, 08:32Z), and the last scheduled `agent-work`
run started at 11:05Z, missing the 15:00Z slot.
On 2026-11-20 the chain declined at 11:43Z (a stale quota reading, fixed in
chain_cycle.py), no event followed, and nothing ran from 11:52Z for 3h+.

So agent-queue keeps a heartbeat: a `workflow_dispatch` run with
`heartbeat=true`. `workflow_dispatch` from `github.token` is one of the two
events GitHub still starts (agent-merge.yml's header has the measurement), and
unlike `workflow_run` it has no three-level limit. Each run ends with `rearm`;
a heartbeat run begins with `doze`.

  doze   sleep up to DOZE_MIN minutes, polling every POLL_S seconds, and stop
         early the moment another agent-queue run is waiting. A heartbeat run
         holds the `agent-queue` concurrency group while it sleeps, and GitHub
         keeps ONE pending run per group, cancelling the older: a second wake
         arriving during a long sleep would cancel the first, and a cancelled
         `workflow_run` wake loses the chain payload it carried. Yielding
         within POLL_S keeps that to one pending run at most.

  rearm  dispatch the next heartbeat ONLY when no other agent-queue run is
         queued, pending or in progress. Dispatching while one is pending would
         cancel it -- the exact loss above. A run that is waiting will rearm
         when it ends. Two heartbeats cannot both survive: the drain job is
         serialised, so the later one always sees the earlier.

The heartbeat is not the clock for anything: hourly_due.py still decides
timers and liveness, and chain_cycle.py decides whether an idle lane restarts.
It only guarantees that SOMETHING asks, every DOZE_MIN minutes or sooner.

COST: the repo is public, so Actions minutes are unlimited
(measurements/cost.json, #338). About 3 runs an hour while idle, each mostly
asleep. No model runs, no new permission: `actions: write` is already granted
for dispatch_cycle.sh.

EXIT CODES: 0 decided (the reason is printed)   2 bad environment
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import Callable

Runner = Callable[[list[str]], str]

WORKFLOW = "agent-queue.yml"
#: Under the drain job's timeout-minutes (agent-queue.yml) with room for the
#: drain, chain and liveness steps after it. tests/test_heartbeat.py pins that.
DOZE_MIN = 20
POLL_S = 30
#: GitHub run states that are not `completed`.
WAITING = {"queued", "pending", "waiting", "requested", "in_progress"}


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def others(gh: Runner, repo: str, this_run: str) -> list[dict]:
    """agent-queue runs other than this one that have not completed."""
    out = gh(["api", f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=20"])
    return [r for r in json.loads(out).get("workflow_runs") or []
            if r.get("status") in WAITING and str(r.get("id")) != this_run]


def doze(gh: Runner, repo: str, this_run: str, sleep: Callable[[float], None] = time.sleep,
         minutes: int = DOZE_MIN) -> str:
    polls = minutes * 60 // POLL_S
    for i in range(polls):
        try:
            waiting = others(gh, repo, this_run)
        except (RuntimeError, ValueError):
            waiting = []                 # an unread API never ends the doze early
        if waiting:
            return f"another agent-queue run is waiting (run {waiting[0].get('id')}); yielding after {i * POLL_S}s"
        sleep(POLL_S)
    return f"dozed {minutes}m; nothing else woke the queue"


def rearm(gh: Runner, repo: str, this_run: str) -> str:
    try:
        waiting = others(gh, repo, this_run)
    except (RuntimeError, ValueError) as exc:
        # Unread: dispatch anyway. A duplicate heartbeat ends at the next rearm
        # (it sees this one); a missing one is a dead loop, which is the defect.
        waiting, note = [], f" (could not list runs: {str(exc)[:80]})"
    else:
        note = ""
    if waiting:
        return (f"not rearmed: run {waiting[0].get('id')} is {waiting[0].get('status')} "
                "and rearms when it ends")
    gh(["workflow", "run", WORKFLOW, "--repo", repo, "-f", "heartbeat=true"])
    return "rearmed: dispatched the next heartbeat" + note


def main(argv: list[str], gh: Runner = run_gh, sleep: Callable[[float], None] = time.sleep) -> int:
    repo = os.environ.get("GH_REPO", "")
    this_run = os.environ.get("THIS_RUN", "")
    if len(argv) != 2 or argv[1] not in ("doze", "rearm") or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::usage: GH_REPO=owner/name THIS_RUN=<id> heartbeat.py doze|rearm")
        return 2
    print("heartbeat: " + (doze(gh, repo, this_run, sleep) if argv[1] == "doze"
                           else rearm(gh, repo, this_run)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
