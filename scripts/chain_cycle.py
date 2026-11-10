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

WHEN ISSUES ARE LOCKED OUT, IT ASSIGNS THE EVIDENCE RETROFIT (2026-11-10)
-------------------------------------------------------------------------
Measured 2026-11-10: 112 issues open and 63 failing `verify_issue_evidence.py`,
including every wrong-in-front-of-users finding the auditors had filed. The
cycle refuses those at Step 1 and may not write its own eligibility, and
nobody else owned writing the missing blocks, so half the cycles that day
built nothing while the ranker circled the few eligible items.

So on every run that does not chain, `retrofit_reason` counts the refused
issues (scripts/evidence_backlog.py) and, at `RETROFIT_MIN_REFUSED` or more,
dispatches `agent-prioritise.yml` with `mode=evidence`: project-manager, which
already holds `issues: write` and the four-kind close grant there, measures
each one and closes it with evidence or posts the block. At most one retrofit
per `RETROFIT_COOLDOWN`, none while one runs, never on an unread or exhausted
quota. Same scope as the chain: `actions: write`.

`produced_something` also stopped counting measurement PRs and PRs merged
mid-window as cycle output (QA on #841): both bumped `updated_at`, so an
empty cycle read as productive and chained.

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
#: Refused issues worth a retrofit run. One is #444-shaped noise (a standing
#: report issue with no defect); three is a ranker with real work locked out.
RETROFIT_MIN_REFUSED = 3
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


def _head_pushed_since(gh: Runner, repo: str, number: int, since: datetime) -> bool:
    out = gh(["api", f"repos/{repo}/pulls/{number}/commits?per_page=100"])
    commits = json.loads(out)
    if not commits:
        return False
    date = ((commits[-1].get("commit") or {}).get("committer") or {}).get("date")
    return bool(date) and _ts(date) >= since


def produced_something(gh: Runner, repo: str, since: datetime) -> bool:
    """Did a cycle open a PR, or push to one, at or after `since`?

    `updated_at` alone over-counts (QA on #841, replaying 2026-11-10): a
    `measurements/<run>-<attempt>` PR is the publisher landing a report, and a
    PR `agent-merge` merged inside the window was built earlier. Both bumped
    `updated_at`, so the two empty cycles that day both read "produced
    something". So: skip measurement PRs; count a PR opened in the window; for
    an older PR, count it only if its head commit landed in the window (a cycle
    pushing a fix). A fixture with no `created_at` keeps the old reading.
    """
    out = gh(["api", f"repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=30"])
    for p in json.loads(out):
        if (p.get("user") or {}).get("login") not in LOOP_AUTHORS:
            continue
        if ((p.get("head") or {}).get("ref") or "").startswith("measurements/"):
            continue
        if _ts(p["updated_at"]) < since:
            continue
        created = p.get("created_at")
        if not created or _ts(created) >= since:
            return True
        if p.get("number") and _head_pushed_since(gh, repo, p["number"], since):
            return True
    return False


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


def refused_count(gh: Runner, repo: str) -> int:
    """Open issues `verify_issue_evidence.py` fails -- the ones a cycle refuses."""
    from evidence_backlog import failing  # noqa: PLC0415 -- only on the retrofit path
    return len(failing(gh, repo))


def retrofit_reason(gh: Runner, repo: str, usage: dict | None, now: datetime) -> str | None:
    """None to dispatch the evidence retrofit, else why not.

    Judged on the CAUSE, not on cycle outcomes. Replayed 2026-11-10 (QA on
    #841): the empty cycles alternated with productive ones -- 01:53 moved
    #833, 02:06 nothing, 04:30 opened #839, 05:02 nothing -- because every
    ranked cycle circled the one or two evidence-complete items while 63 issues
    sat refused. "Two empty cycles in a row" never happened, and a trigger on
    the finished cycle could not see the chained ones anyway (agent-queue ran
    after 8 of 8 scheduled cycles and 0 of 26 dispatched ones). So: on every
    agent-queue run that does not chain (the steward's completion reliably gets
    here), count the refused issues and dispatch when there are enough.
    The cooldown is checked first so the ~100 issue reads happen at most once
    per `RETROFIT_COOLDOWN`.
    """
    reason = quota_reason(usage, now)
    if reason:
        return reason
    out = gh(["api", f"repos/{repo}/actions/workflows/agent-prioritise.yml/runs?per_page=20"])
    for r in json.loads(out).get("workflow_runs") or []:
        if not (r.get("display_title") or "").startswith(RETROFIT_TITLE):
            continue
        if r.get("status") != "completed":
            return "an evidence retrofit is already running"
        age = now - _ts(r["created_at"])
        if age < RETROFIT_COOLDOWN:
            return f"an evidence retrofit ran {age.total_seconds() / 3600:.1f}h ago"
    n = refused_count(gh, repo)
    if n < RETROFIT_MIN_REFUSED:
        return f"{n} open issue(s) fail the Evidence Block gate, under {RETROFIT_MIN_REFUSED}"
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
        try:
            why = retrofit_reason(gh, repo, usage, now)
        except (RuntimeError, ValueError, KeyError) as exc:
            why = f"could not decide ({exc.__class__.__name__}: {str(exc)[:120]})"
        if why:
            print(f"no evidence retrofit: {why}.")
        else:
            gh(["workflow", "run", "agent-prioritise.yml", "--repo", repo, "-f", "mode=evidence"])
            print("refused backlog: dispatched agent-prioritise mode=evidence to "
                  "retrofit or close the issues the build loop refuses.")
        return 0
    gh(["workflow", "run", "agent-work.yml", "--repo", repo])
    print("chained: dispatched one ranked agent-work cycle (project-manager picks).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
