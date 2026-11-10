#!/usr/bin/env python3
"""Start the next ranked build cycle as soon as one finishes, within the quota.

WHY THIS EXISTS
---------------
The owner, 2026-11-06, on a backlog of 131 open issues: "I have been seeing a
long queue of backlog issues for very long." Measured the same day in
`measurements/loop.json`: the build lane sat idle **148.8 of the last 168
hours (89%)** while the Claude weekly window stood at 3%. `agent-work` fires on
six cron slots a day and a cycle takes ~20 minutes, so after each one the lane
waited up to four hours for the next slot. The capacity existed and went unused.

So when a build cycle completes, `agent-queue.yml` drains the queue first (a
ruling someone made outranks the ranker), then runs this. If the build lane is
still free, this dispatches one ranked cycle (`gh workflow run agent-work.yml`,
no inputs: project-manager picks), so the next issue starts in minutes, not hours.

WHAT STOPS IT, each one a measured failure mode rather than caution
------------------------------------------------------------------
- **The weekly Claude window.** Every agent shares one Claude Max subscription,
  and the weekly window reached ~89% the week before this was written. No chain
  at or above `QUOTA_CEILING` of `seven_day`, and none when the reading is
  missing, stale or not `allowed`: an unread quota is not a free one.
- **A cycle that produced nothing.** Chaining off a cycle that opened or moved
  no PR would spin on an empty or unworkable backlog. A chain needs a PR by a
  loop author updated after the finished run started.
- **A daily cap.** At most `MAX_BUILD_RUNS_PER_DAY` build runs per UTC day,
  counting cron and dispatched runs alike, whatever the other guards say.
- **Only a successful BUILD run chains.** A QA round, a failed run, or the
  steward completing (agent-queue's backstop trigger) never does.

WHEN THE LANE STARVES, IT ASSIGNS THE EVIDENCE RETROFIT (2026-11-10)
-------------------------------------------------------------------
Measured 2026-11-10: 112 issues open, 63 failing `verify_issue_evidence.py`,
and the two build cycles that day ended "nothing" -- every ranked item was
refused at Step 1, the cycle may not write its own eligibility, and nobody
else owned writing the missing Evidence Blocks. Not chaining was correct; it
was also the end of the line, because nothing then fixed the reason.

So when the finished cycle produced nothing AND the build run before it did
too (no loop PR moved since that earlier run started), this dispatches
`agent-prioritise.yml` with `mode=evidence`: project-manager, which already
holds `issues: write` and the four-kind close grant there, measures each
failing issue and either closes it with evidence or posts the block. One
retrofit per `RETROFIT_COOLDOWN`, none while one is running, and never on an
unread or exhausted quota. Same scope as the chain: `actions: write`.

It writes no label and no comment, and needs no scope `agent-queue.yml` lacks:
dispatching `agent-work` is what `dispatch_cycle.sh` already does there.

EXIT CODES: 0 decided (chained or not -- the reason is printed)   2 bad env
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle_queue import QA_TITLE, busy, run_gh  # noqa: E402

Runner = Callable[[list[str]], str]

QUOTA_CEILING = 0.70
QUOTA_MAX_AGE = timedelta(hours=36)
MAX_BUILD_RUNS_PER_DAY = 16
RETROFIT_COOLDOWN = timedelta(hours=6)
#: agent-prioritise.yml's run-name in mode=evidence. `gh run list` cannot show
#: inputs, so the title is how a retrofit run is recognised -- the same reason
#: the QA lane is told apart by QA_TITLE. tests/test_evidence_retrofit.py pins both copies.
RETROFIT_TITLE = "Evidence retrofit"
NOTHING = "the finished cycle opened or moved no PR -- nothing workable to chain on"
#: Who opens and pushes loop PRs -- agent-merge.yml's AGENT_AUTHORS, minus the
#: repo owner, whose own pushes say nothing about what a cycle did.
LOOP_AUTHORS = {"claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]"}
USAGE = Path(__file__).resolve().parent.parent / "measurements" / "claude_usage.json"


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def quota_reason(usage: dict | None, now: datetime) -> str | None:
    """None when the quota allows a chain, else why not."""
    if not usage:
        return "claude_usage.json unreadable -- an unread quota is not a free one"
    latest = usage.get("latest") or {}
    try:
        age = now - _ts(usage["generated_at"])
        used = float(latest["seven_day"])
    except (KeyError, TypeError, ValueError):
        return "claude_usage.json has no usable seven_day reading"
    if age > QUOTA_MAX_AGE:
        return f"claude_usage.json is {age.total_seconds() / 3600:.0f}h old"
    if latest.get("status") != "allowed":
        return f"the latest Claude reading says {latest.get('status')!r}"
    if used >= QUOTA_CEILING:
        return f"weekly Claude window at {used:.0%}, ceiling {QUOTA_CEILING:.0%}"
    return None


def build_runs_today(gh: Runner, repo: str, now: datetime) -> int:
    out = gh(["api", f"repos/{repo}/actions/workflows/agent-work.yml/runs"
              f"?per_page=100&created=>={now:%Y-%m-%d}"])
    runs = json.loads(out).get("workflow_runs") or []
    return sum(1 for r in runs if not (r.get("display_title") or "").startswith(QA_TITLE))


def produced_something(gh: Runner, repo: str, since: datetime) -> bool:
    out = gh(["api", f"repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=30"])
    return any((p.get("user") or {}).get("login") in LOOP_AUTHORS
               and _ts(p["updated_at"]) >= since for p in json.loads(out))


def decide(gh: Runner, repo: str, run: dict, usage: dict | None, now: datetime) -> str | None:
    """None to chain, else the reason not to."""
    if run.get("name") != "Agent work":
        return f"triggered by {run.get('name')!r}, not a finished cycle"
    if (run.get("title") or "").startswith(QA_TITLE):
        return "a QA round finished; only a build cycle chains"
    if run.get("conclusion") != "success":
        return f"the cycle concluded {run.get('conclusion')!r}"
    reason = quota_reason(usage, now)
    if reason:
        return reason
    if busy(gh, repo, "build"):
        return "the build lane is busy (the queue started a cycle, or one is running)"
    n = build_runs_today(gh, repo, now)
    if n >= MAX_BUILD_RUNS_PER_DAY:
        return f"{n} build runs today, cap {MAX_BUILD_RUNS_PER_DAY}"
    if not produced_something(gh, repo, _ts(run["started"])):
        return NOTHING
    return None


def previous_build_start(gh: Runner, repo: str, started: datetime) -> datetime | None:
    """When the successful build run before the finished one started."""
    out = gh(["api", f"repos/{repo}/actions/workflows/agent-work.yml/runs"
              f"?status=completed&per_page=30"])
    for r in json.loads(out).get("workflow_runs") or []:
        if (r.get("display_title") or "").startswith(QA_TITLE) or r.get("conclusion") != "success":
            continue
        st = _ts(r.get("run_started_at") or r["created_at"])
        if st < started - timedelta(minutes=1):
            return st
    return None


def retrofit_reason(gh: Runner, repo: str, run: dict, now: datetime) -> str | None:
    """None to dispatch the evidence retrofit, else why not. Called only after NOTHING."""
    prev = previous_build_start(gh, repo, _ts(run["started"]))
    if prev is None:
        return "no earlier build run to compare with"
    if produced_something(gh, repo, prev):
        return "the build run before this one moved a PR -- one empty cycle is not starvation"
    out = gh(["api", f"repos/{repo}/actions/workflows/agent-prioritise.yml/runs?per_page=20"])
    for r in json.loads(out).get("workflow_runs") or []:
        if not (r.get("display_title") or "").startswith(RETROFIT_TITLE):
            continue
        if r.get("status") != "completed":
            return "an evidence retrofit is already running"
        age = now - _ts(r["created_at"])
        if age < RETROFIT_COOLDOWN:
            return f"an evidence retrofit ran {age.total_seconds() / 3600:.1f}h ago"
    return None


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None,
         usage_path: Path = USAGE) -> int:
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::chain_cycle.py needs GH_REPO=owner/name")
        return 2
    run = {k: os.environ.get(f"WR_{k.upper()}", "") for k in
           ("name", "title", "conclusion", "started")}
    try:
        usage = json.loads(usage_path.read_text())
    except (OSError, ValueError):
        usage = None
    now = now or datetime.now(timezone.utc)
    try:
        reason = decide(gh, repo, run, usage, now)
    except (RuntimeError, ValueError, KeyError) as exc:
        reason = f"could not decide ({exc.__class__.__name__}: {str(exc)[:120]})"
    if reason:
        print(f"no chain: {reason}.")
        if reason == NOTHING:
            try:
                why = retrofit_reason(gh, repo, run, now)
            except (RuntimeError, ValueError, KeyError) as exc:
                why = f"could not decide ({exc.__class__.__name__}: {str(exc)[:120]})"
            if why:
                print(f"no evidence retrofit: {why}.")
            else:
                gh(["workflow", "run", "agent-prioritise.yml", "--repo", repo, "-f", "mode=evidence"])
                print("starved: two build cycles in a row produced nothing -- dispatched "
                      "agent-prioritise mode=evidence to retrofit or close the refused issues.")
        return 0
    gh(["workflow", "run", "agent-work.yml", "--repo", repo])
    print("chained: dispatched one ranked agent-work cycle (project-manager picks).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
