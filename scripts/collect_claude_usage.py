#!/usr/bin/env python3
"""How close the loop runs to its Claude Max subscription limits.

WHY THIS EXISTS
---------------
Every agent in this repo -- `agent-work`, the steward, `chief`, the weekly
loops -- runs on ONE Claude Max 5x subscription (measurements/cost.json). The
question "can we run more cycles in parallel?" (owner, 2026-11-03) turns on how
much of that subscription is left, and nothing measured it. The rate-limit
state was there all along: `claude-code-action` logs a `rate_limit_info` block
on every rate-limit event, with BOTH windows the subscription enforces:

    "unifiedWindows": {
      "five_hour": {"utilization": 0.01, "resetsAt": ..., "status": "allowed"},
      "seven_day": {"utilization": 0.68, "resetsAt": ..., "status": "allowed"}
    }

Measured on run 41574673500 (2026-11-03): five-hour ~1%, SEVEN-DAY 68%. So the
binding window is the weekly one, not the five-hour one this repo's comments
had assumed -- which is exactly why it has to be measured rather than argued.

The utilization is ACCOUNT-WIDE, so any run's reading describes the whole
subscription at that moment; reading recent runs of every Claude-backed
workflow gives a time series.

OUTPUT: measurements/claude_usage.json
--------------------------------------
    latest            the newest reading: both windows, their reset times, status
    peak_seven_day    the highest weekly utilization in the sampled window
    rejected_runs     runs where any window reported `rejected` (the cap HIT)
    readings          one row per run: workflow, run, time, both windows

Nothing is written when no reading could be parsed: a file that says "0%"
because the logs were unreadable is worse than yesterday's file.

EXIT CODES
----------
  0  written   1  nothing readable (previous file left standing)   2  bad args
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

#: Every workflow that runs `anthropics/claude-code-action`, i.e. every
#: consumer of the one subscription. tests/test_claude_usage.py fails if a
#: workflow gains the action and is not listed here.
CLAUDE_WORKFLOWS = (
    "agent-work.yml", "agent-steward.yml", "agent-measure.yml", "agent-discover.yml",
    "agent-design.yml", "agent-infra.yml", "agent-prioritise.yml", "agent-research.yml",
    "agent-sync.yml", "rashifal-generate.yml",
)
WINDOW_HOURS = 48          # how far back to sample
PER_WORKFLOW = 4           # newest N completed runs per workflow (logs are ~2 MB each)
STATUS_RANK = {"allowed": 0, "allowed_warning": 1, "rejected": 2}
_TS = re.compile(r"^\S+Z\s?")          # the per-line timestamp Actions prefixes

Runner = Callable[[list[str]], str]


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {p.stderr.strip()[:200]}")
    return p.stdout


def fetch_log(gh: Runner, repo: str, job: int) -> str:
    """One job's log. Job logs contain terminal escape sequences and `gh api`
    REFUSES to print them without `--allow-escape-sequences` -- measured by QA on
    PR #691 with gh 2.103.2 on a GitHub-hosted runner, where every call failed
    and the file was never written (the session that built this had gh 2.89,
    which did not need it). Same flag, same fallback as
    collect_loop_measurements.LogSource: an older gh that does not know the
    flag is retried without it."""
    path = f"repos/{repo}/actions/jobs/{job}/logs"
    try:
        return gh(["api", "--allow-escape-sequences", path])
    except RuntimeError as exc:
        if "unknown flag" in str(exc):
            return gh(["api", path])
        raise


def parse_blocks(log: str) -> list[dict]:
    """Every `rate_limit_info` object in a job log, parsed as JSON.

    The block is pretty-printed across lines, each prefixed with a timestamp,
    so the prefix is stripped and braces are balanced before json.loads. A
    block that does not parse is skipped, never guessed at.
    """
    lines = [_TS.sub("", l, count=1) for l in log.splitlines()]
    out: list[dict] = []
    i = 0
    while i < len(lines):
        if '"rate_limit_info"' in lines[i] and "{" in lines[i]:
            buf, depth = [], 0
            first = lines[i][lines[i].index("{"):]
            for l in [first] + lines[i + 1:]:
                buf.append(l)
                depth += l.count("{") - l.count("}")
                if depth <= 0:
                    break
            try:
                out.append(json.loads("\n".join(buf).rstrip().rstrip(",")))
            except json.JSONDecodeError:
                pass
            i += len(buf)
        else:
            i += 1
    return out


def summarise(blocks: list[dict]) -> dict | None:
    """The worst state a run saw: max utilization per window, worst status."""
    five, seven, status, resets = None, None, "allowed", {}
    for b in blocks:
        w = b.get("unifiedWindows") or {}
        for name in ("five_hour", "seven_day"):
            u = (w.get(name) or {}).get("utilization")
            if isinstance(u, (int, float)):
                if name == "five_hour":
                    five = u if five is None else max(five, u)
                else:
                    seven = u if seven is None else max(seven, u)
                if (w.get(name) or {}).get("resetsAt"):
                    resets[name] = w[name]["resetsAt"]
            s = (w.get(name) or {}).get("status")
            if s in STATUS_RANK and STATUS_RANK[s] > STATUS_RANK[status]:
                status = s
        s = b.get("status")
        if s in STATUS_RANK and STATUS_RANK[s] > STATUS_RANK[status]:
            status = s
    if five is None and seven is None:
        return None
    return {"five_hour": five, "seven_day": seven, "status": status, "resets": resets}


def collect(gh: Runner, repo: str, now: datetime, tally: dict | None = None) -> dict | None:
    """The document, or None when nothing parsed. `tally` (if given) is filled
    with how many logs were fetched, failed to fetch, and parsed to nothing --
    so the caller can say WHICH failed instead of blaming the logs."""
    since = (now - timedelta(hours=WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    readings: list[dict] = []
    t = tally if tally is not None else {}
    t.update({"logs_fetched": 0, "fetch_failed": 0, "no_blocks": 0, "last_error": ""})
    for wf in CLAUDE_WORKFLOWS:
        try:
            runs = json.loads(gh(["api", f"repos/{repo}/actions/workflows/{wf}/runs"
                                  f"?status=completed&per_page={PER_WORKFLOW}&created=>={since}",
                                  "--jq", "[.workflow_runs[] | {id, created_at}]"]) or "[]")
        except (RuntimeError, json.JSONDecodeError):
            continue
        for r in runs[:PER_WORKFLOW]:
            try:
                jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{r['id']}/jobs",
                                      "--jq", "[.jobs[].id]"]) or "[]")
            except (RuntimeError, json.JSONDecodeError):
                continue
            blocks: list[dict] = []
            for j in jobs:
                try:
                    log = fetch_log(gh, repo, j)
                except RuntimeError as exc:
                    t["fetch_failed"] += 1
                    t["last_error"] = str(exc)[:200]
                    continue
                t["logs_fetched"] += 1
                got = parse_blocks(log)
                if not got:
                    t["no_blocks"] += 1
                blocks += got
            s = summarise(blocks)
            if s:
                readings.append({"workflow": wf.removesuffix(".yml"), "run": r["id"],
                                 "at": r["created_at"], **s})
    if not readings:
        return None
    readings.sort(key=lambda x: x["at"])
    sevens = [x["seven_day"] for x in readings if x["seven_day"] is not None]
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": WINDOW_HOURS,
        "latest": readings[-1],
        "peak_seven_day": max(sevens) if sevens else None,
        "rejected_runs": [x["run"] for x in readings if x["status"] == "rejected"],
        "readings": readings,
    }


def validate(doc: dict) -> list[str]:
    errs = []
    for k in ("generated_at", "latest", "readings", "rejected_runs"):
        if k not in doc:
            errs.append(f"missing {k}")
    for x in doc.get("readings", []):
        for w in ("five_hour", "seven_day"):
            u = x.get(w)
            if u is not None and not (0 <= u <= 1.5):
                errs.append(f"run {x.get('run')}: {w} utilization {u} out of range")
    return errs


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    tally: dict = {}
    doc = collect(gh, a.repo, now or datetime.now(timezone.utc), tally)
    if doc is None:
        # Say WHICH failed: a fetch refused by gh and a log with no rate-limit
        # block are different repairs, and QA round 1 on #691 found the old
        # single message blaming the logs when the fetch was the problem.
        if tally.get("fetch_failed") and not tally.get("logs_fetched"):
            print(f"::warning::every job-log FETCH failed ({tally['fetch_failed']}); last error: "
                  f"{tally['last_error']}. The previous claude_usage.json is left standing.")
        else:
            print(f"::warning::{tally.get('logs_fetched', 0)} log(s) fetched, none carried a "
                  f"rate_limit_info block ({tally.get('fetch_failed', 0)} fetch failure(s)). "
                  f"The previous claude_usage.json is left standing.")
        return 1
    errs = validate(doc)
    if errs:
        print("::error::claude_usage.json would not validate: " + "; ".join(errs))
        return 1
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    L = doc["latest"]
    print(f"claude usage: seven-day {L['seven_day']}, five-hour {L['five_hour']}, "
          f"status {L['status']}; peak seven-day {doc['peak_seven_day']}; "
          f"{len(doc['rejected_runs'])} run(s) hit a limit; {len(doc['readings'])} readings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
