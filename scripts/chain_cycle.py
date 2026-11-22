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

IT RESTARTS AN IDLE LANE, AND READS THE FRESHEST QUOTA (2026-11-20)
-------------------------------------------------------------------
At 11:43Z it refused on `claude_usage.json`'s 03:53Z reading (88% weekly,
`allowed_warning`) while the 11:05Z cycle had logged 4%: the weekly window had
reset at 06:00Z, which the reading itself said (`resets.seven_day`). QA had
flagged staleness-by-`generated_at` on #749 as non-blocking; it was never
filed. Now: `fresh_reading` takes the newest finished cycle's own reading when
it is newer than the file, and `windows_reset` sets aside a reading whose
windows have both reset. And a run with no finished cycle behind it (the
hourly cron, or scripts/heartbeat.py's heartbeat) asks `idle_reason`: with
the lane free for `IDLE_RESTART` (`IDLE_AFTER_NOTHING` after an empty cycle)
and the same quota and cap guards, it starts one ranked cycle. Before, only
`agent-work`'s own cron restarted an idle lane, and GitHub drops those.

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

A MALFORMED READING STOPS THE CHAIN (2026-11-22, #1282)
-------------------------------------------------------
`NaN >= 0.70` is False and a future `generated_at` makes a negative age that
passes `age > 36h`, so a `claude_usage.json` carrying `seven_day: NaN` (Python's
`json.loads` accepts the bare token) or a clock-ahead timestamp let the chain
spend the shared subscription on no reading at all. `quota_reason` now refuses
a non-finite or out-of-range `seven_day` and a `generated_at` or `latest.at`
more than `QUOTA_FUTURE_SKEW` ahead, BEFORE `windows_reset`: `resets` is part
of the same file, and a reading that cannot be bounded must not be able to
claim it has expired.

EXIT CODES: 0 decided (chained or not -- the reason is printed)   2 bad env
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle_queue import QA_TITLE, busy, run_gh  # noqa: E402
import collect_claude_usage as ccu  # noqa: E402

Runner = Callable[[list[str]], str]

QUOTA_CEILING = 0.70
QUOTA_MAX_AGE = timedelta(hours=36)
#: How far ahead of `now` a reading's timestamp may sit before it is a clock error,
#: not a reading (#1282). generated_at is stamped on one runner and judged on another,
#: and latest.at is GitHub's created_at judged on the runner's clock: seconds of NTP
#: skew, so 5 minutes absorbs that and is ~0.2% of QUOTA_MAX_AGE. Not measured.
QUOTA_FUTURE_SKEW = timedelta(minutes=5)
MAX_BUILD_RUNS_PER_DAY = 16
#: An IDLE lane restarts (2026-11-20). A run with no finished cycle behind it --
#: the hourly cron, or the heartbeat -- starts one ranked cycle once the last
#: build run has been finished this long. After a cycle that produced nothing
#: it waits IDLE_AFTER_NOTHING instead: roughly the old six-crons-a-day cadence,
#: so an unworkable backlog is retried, not spun on.
IDLE_RESTART = timedelta(minutes=60)
IDLE_AFTER_NOTHING = timedelta(hours=4)
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


def windows_reset(latest: dict, now: datetime) -> bool:
    """True when BOTH windows the reading measured have reset since it was taken.

    2026-11-20: the reading said 88% weekly, `allowed_warning`, and carried
    `resets.seven_day` = 06:00Z; at 11:43Z the chain still refused on it. A
    reading describes its windows, and once both have ended it describes
    nothing: a new window starts empty, and any cycle since would have left a
    newer reading (fresh_reading). Unparseable or missing resets answer False,
    so the reading is judged as before.
    """
    resets = latest.get("resets") or {}
    try:
        return all(datetime.fromtimestamp(float(resets[k]), timezone.utc) <= now
                   for k in ("five_hour", "seven_day"))
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False


def quota_reason(usage: dict | None, now: datetime) -> str | None:
    """None when the quota allows a chain, else why not."""
    if not usage:
        return "claude_usage.json unreadable -- an unread quota is not a free one"
    latest = usage.get("latest") or {}
    try:
        generated = _ts(usage["generated_at"])
        age = now - generated
        used = float(latest["seven_day"])
        at = latest.get("at")
        at_ts = _ts(at) if at is not None else None
        at_ahead = at_ts - now if at_ts is not None else None
    except (KeyError, TypeError, ValueError):
        return "claude_usage.json has no usable seven_day reading"
    # Validate BEFORE windows_reset: that returns None (chain allowed) ahead of every other
    # check, and `resets` is in the same file, so a NaN reading with past resets would open.
    if not math.isfinite(used) or not 0 <= used <= 1:
        return (f"claude_usage.json seven_day reading {used!r} is not a number from 0 to 1"
                " -- an unreadable quota is not a free one")
    for what, ahead in (("generated_at", -age), ("latest.at", at_ahead)):
        if ahead is not None and ahead > QUOTA_FUTURE_SKEW:
            return (f"claude_usage.json {what} is {ahead.total_seconds() / 60:.0f}m in the future"
                    " -- a clock error, not a reading")
    if age > QUOTA_MAX_AGE:
        return f"claude_usage.json is {age.total_seconds() / 3600:.0f}h old"
    if windows_reset(latest, now):
        return None
    if latest.get("status") != "allowed":
        return f"the latest Claude reading says {latest.get('status')!r}"
    if used >= QUOTA_CEILING:
        return f"weekly Claude window at {used:.0%}, ceiling {QUOTA_CEILING:.0%}"
    return None


def fresh_reading(gh: Runner, repo: str) -> dict | None:
    """The quota as the newest COMPLETED agent-work run logged it, or None.

    WHY (2026-11-20): measurements/claude_usage.json is refreshed by agent-measure, which
    runs AFTER the cycle that wakes this. Measured that day: at 11:43Z the chain declined on
    "the latest Claude reading says 'allowed_warning'" -- the 03:53Z reading at 88% weekly --
    while the 11:05Z cycle had already logged 4%: the weekly window had reset at ~06:00Z. The
    committed file caught up at 11:45Z, two minutes too late, and the loop then sat idle for
    3h+ with 96% of the week unused. The finished cycle's own log is the freshest reading
    there is, and parsing it is the collector's own code (collect_claude_usage)."""
    try:
        runs = json.loads(gh(["api", f"repos/{repo}/actions/workflows/agent-work.yml/runs"
                              "?status=completed&per_page=1"])).get("workflow_runs") or []
        if not runs:
            return None
        run = runs[0]
        jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{run['id']}/jobs"])).get("jobs") or []
        blocks: list[dict] = []
        for j in jobs:
            blocks += ccu.parse_blocks(ccu.fetch_log(gh, repo, j["id"]))
        got = ccu.summarise(blocks)
    except (RuntimeError, ValueError, KeyError, TypeError):
        return None
    if not got or got.get("seven_day") is None:
        return None
    return {**got, "at": run.get("run_started_at") or run.get("created_at"), "run": run.get("id")}


def freshest(usage: dict | None, fresh: dict | None, now: datetime) -> dict | None:
    """The committed usage, with its `latest` replaced by `fresh` when `fresh` is newer."""
    if not fresh or not fresh.get("at"):
        return usage
    latest_at = ((usage or {}).get("latest") or {}).get("at")
    try:
        # A file reading dated past the skew must not pin itself above a real one (#1282):
        # quota_reason refuses it, so without this no genuine reading could ever replace it.
        newer = (latest_at is None or _ts(latest_at) > now + QUOTA_FUTURE_SKEW
                 or _ts(fresh["at"]) > _ts(latest_at))
    except (TypeError, ValueError):
        newer = True
    if not newer:
        return usage
    # The age is the READING's, never now's: stamping now made a 45h-old log reading (an
    # hourly tick after missed cron slots) pass the QUOTA_MAX_AGE guard as if it were fresh.
    return {**(usage or {}), "generated_at": fresh["at"], "latest": fresh}


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
    return gave_a_verdict(gh, repo, since)


#: The first line `scripts/qa_verdict.sh` writes on every verdict comment.
VERDICT_PREFIXES = ("QA: PASS", "QA: FAIL")


def gave_a_verdict(gh: Runner, repo: str, since: datetime) -> bool:
    """Did the loop post a QA verdict at or after `since`?

    A cycle that ADOPTS an earlier cycle's PR and passes or fails it pushes
    nothing and opens nothing, yet it moved a PR toward merge. Measured
    2026-11-22: run 45023409764 adopted PR #1378 and recorded its QA PASS, was
    scored "produced nothing", and the idle restart then waited 240 min; the
    04:03-08:34Z gap the same morning had the same shape. One repo-wide read.
    """
    out = gh(["api", f"repos/{repo}/issues/comments?since={since:%Y-%m-%dT%H:%M:%SZ}&per_page=100"])
    for c in json.loads(out):
        if (c.get("user") or {}).get("login") not in LOOP_AUTHORS:
            continue
        if _ts(c.get("created_at") or "1970-01-01T00:00:00Z") < since:
            continue
        if (c.get("body") or "").lstrip().startswith(VERDICT_PREFIXES):
            return True
    return False


def last_build_run(gh: Runner, repo: str) -> dict | None:
    """The newest finished non-QA agent-work run, or None."""
    out = gh(["api", f"repos/{repo}/actions/workflows/agent-work.yml/runs?status=completed&per_page=20"])
    for r in json.loads(out).get("workflow_runs") or []:
        if not (r.get("display_title") or "").startswith(QA_TITLE):
            return r
    return None


def idle_reason(gh: Runner, repo: str, usage: dict | None, now: datetime) -> str | None:
    """None to RESTART an idle build lane, else why not (2026-11-20).

    Until then a run with no finished cycle behind it never started one, so the
    lane restarted only on `agent-work`'s own cron, which GitHub drops: on
    2026-11-20 the 07:00 and 15:00 slots never fired and the lane sat idle from
    11:52Z with 96% of the weekly window unused. Same quota and cap guards as
    a chain."""
    reason = quota_reason(usage, now)
    if reason:
        return reason
    if busy(gh, repo, "build"):
        return "the build lane is busy"
    n = build_runs_today(gh, repo, now)
    if n >= MAX_BUILD_RUNS_PER_DAY:
        return f"{n} build runs today, cap {MAX_BUILD_RUNS_PER_DAY}"
    last = last_build_run(gh, repo)
    if last is None:
        return None
    ended = _ts(last.get("updated_at") or last["run_started_at"])
    wait = IDLE_RESTART
    if not produced_something(gh, repo, _ts(last["run_started_at"])):
        wait = IDLE_AFTER_NOTHING
    idle = now - ended
    if idle < wait:
        return (f"the last build run ended {idle.total_seconds() / 60:.0f}m ago; "
                f"an idle lane restarts after {wait.total_seconds() / 60:.0f}m")
    return None


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
    fresh = fresh_reading(gh, repo)
    usage = freshest(usage, fresh, now)
    if fresh and usage and usage.get("latest") is fresh:
        print(f"quota: the newest finished cycle's own reading (run {fresh.get('run')}, "
              f"{fresh['seven_day']:.0%} weekly, {fresh['status']}) -- newer than claude_usage.json.")
    idle = not run["name"]       # the hourly cron or the heartbeat: no finished cycle
    try:
        reason = idle_reason(gh, repo, usage, now) if idle else decide(gh, repo, run, usage, now)
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
    if idle:
        print("restarted: the build lane was idle; dispatched one ranked agent-work cycle.")
    else:
        print("chained: dispatched one ranked agent-work cycle (project-manager picks).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
