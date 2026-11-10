#!/usr/bin/env python3
"""Wait for the agent-work run that woke agent-queue, then describe it.

WHY THIS EXISTS (#826)
----------------------
`agent-queue` drains the queue and chains the next cycle when an `agent-work`
run completes, via `workflow_run`. Measured 2026-11-08..10: it ran after 8 of
8 SCHEDULED cycles and after 0 of 26 DISPATCHED ones (chained cycles and QA
rounds). GitHub stops `workflow_run` chains after three levels: a cron cycle
(1) wakes agent-queue (2), which dispatches the next cycle (3), and that
cycle's completion would wake agent-queue at level 4 -- dropped, silently. So
each cron firing bought one cycle plus one chained cycle, and the lane then
sat until the next cron, which GitHub fires up to 8.5h apart. On 2026-11-10
the 11:12 chained cycle shipped #845 and nothing ran for 3h+ after it.

A dispatched `agent-work` run now ends by dispatching `agent-queue.yml` with
`after_run=<its own run id>` (`workflow_dispatch` has no such depth limit;
`agent-merge` re-dispatches itself in a chain every day). That dispatch happens
while the waking run is still in progress, and draining then would see the
waker as a busy lane -- exactly the trap agent-queue.yml's header records. So
this polls until the run is COMPLETED, then writes the same four facts the
`workflow_run` payload carries (`WAKE_NAME`, `WAKE_TITLE`, `WAKE_CONCLUSION`,
`WAKE_STARTED`) to $GITHUB_ENV for the drain and chain steps.

It refuses anything that is not a run of agent-work.yml: a dispatch input is a
string a person with write access typed, and chaining off an arbitrary run id
would let any workflow's completion count as a finished cycle.

EXIT CODES: 0 the run completed and was described   1 it did not complete in
time, or is not an agent-work run   2 bad input or environment
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

WORKFLOW_PATH = ".github/workflows/agent-work.yml"
POLL_SECONDS = 15
MAX_WAIT_SECONDS = 10 * 60


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def wait(gh: Runner, repo: str, run_id: str, sleep: Callable[[float], None] = time.sleep,
         max_wait: float = MAX_WAIT_SECONDS) -> tuple[int, dict | str]:
    waited = 0.0
    while True:
        try:
            run = json.loads(gh(["api", f"repos/{repo}/actions/runs/{run_id}"]))
        except (RuntimeError, ValueError) as exc:
            run, err = None, str(exc)[:120]
        if run is not None:
            path = (run.get("path") or "").split("@", 1)[0]
            if path != WORKFLOW_PATH:
                return 1, f"run {run_id} is {path or 'an unknown workflow'}, not {WORKFLOW_PATH}"
            if run.get("status") == "completed":
                return 0, {"WAKE_NAME": run.get("name") or "",
                           "WAKE_TITLE": run.get("display_title") or "",
                           "WAKE_CONCLUSION": run.get("conclusion") or "",
                           "WAKE_STARTED": run.get("run_started_at") or run.get("created_at") or ""}
        if waited >= max_wait:
            why = err if run is None else f"still {run.get('status')}"
            return 1, f"run {run_id} did not complete within {int(max_wait)}s ({why})"
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def main(argv: list[str], gh: Runner = run_gh, sleep: Callable[[float], None] = time.sleep) -> int:
    repo = os.environ.get("GH_REPO", "")
    run_id = os.environ.get("AFTER_RUN", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::wait_for_run.py needs GH_REPO=owner/name")
        return 2
    if not re.fullmatch(r"\d{1,20}", run_id):
        print(f"::error::AFTER_RUN must be a run id, got {run_id[:40]!r}")
        return 2
    code, result = wait(gh, repo, run_id, sleep)
    if code:
        print(f"::warning::{result}. Not draining or chaining off it; the steward's completion is the backstop.")
        return code
    print(f"run {run_id} completed: {result['WAKE_TITLE']!r} {result['WAKE_CONCLUSION']}")
    out = os.environ.get("GITHUB_ENV")
    if out:
        with open(out, "a") as fh:
            for k, v in result.items():
                fh.write(f"{k}={v.replace(chr(10), ' ')}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
