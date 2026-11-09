#!/usr/bin/env python3
"""Which tests fail on the open PRs' gates, and which fail on more than one.

WHY THIS EXISTS
---------------
On 2026-11-08 #797 moved the shared `today_iso` test fixture to the IST day.
One test keyed a cache by the server's UTC date, so from 18:30Z to 24:00Z it
failed -- on `main`, and therefore on every open PR gated in that window. By
the next morning seven PRs were red on the SAME test
(`test_panchang_strip_cache.py::test_eviction_is_bounded_and_keeps_what_matters`)
and nothing in the loop connected them:

  * each PR's red gate reads as that PR's own problem, so a cycle aimed at it
    would hunt its own diff for a defect it did not contain;
  * `qa-on-green` fires only on green, so a red PR gets no round at all;
  * `collect_lessons.py` reads QA FAILs, reverts and failed production checks,
    none of which a broken `main` produces.

One test failing on two PRs with unrelated diffs is the cheapest available
evidence that the defect is on `main`, not in either PR. This collector writes
the per-test tally; `detect_ops_regressions.py` raises `main-red-suspected`
from it, `file_ops_findings.py` files that as one issue, and the lessons ledger
carries it because it reads the detector's findings.

WHAT IT READS
-------------
For each open PR, the failed runs of `GATE_WORKFLOWS` on its head SHA, their
jobs named in `GATE_CHECKS` that concluded `failure`, and from each job's log the pytest short-summary lines
(`FAILED tests/...::name - message`). Everything is read through the Actions
API (`actions: read`, which `agent-measure`'s commit job already holds through
`actions: write`) plus the open-PR list (`pull-requests`, also held).

A log it cannot fetch is COUNTED, never silently dropped: an all-fetches-failed
run writes `fetch_failed` > 0 with an empty tally, and the detector reports
that as unreadable rather than as "no shared failure".

EXIT CODES: 0 wrote the file   1 could not list PRs (previous file kept)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str]], str]

#: The check runs that execute the behaviour suite: `pr-gates`' `gates` job and
#: `verify-build`'s `build-gates` job.
GATE_CHECKS = {"gates", "build-gates"}
GATE_WORKFLOWS = {"PR gates", "verify-build"}
MAX_PRS = 40
#: GitHub prefixes every log line with an ISO timestamp.
_TS = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
_ESC = re.compile(r"\x1b\[[0-9;]*m")
#: pytest's short summary. The node id runs to the first " - " (the message).
_FAILED = re.compile(r"^(?:FAILED|ERROR) (tests/\S+?)(?: - .*)?$")


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def failed_tests(log: str) -> list[str]:
    """Distinct pytest node ids named in a log's short summary, in order."""
    seen: list[str] = []
    for raw in log.splitlines():
        line = _ESC.sub("", _TS.sub("", raw, count=1)).strip()
        m = _FAILED.match(line)
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def collect(gh: Runner, repo: str, now: datetime) -> dict:
    prs = json.loads(gh(["api", f"repos/{repo}/pulls?state=open&per_page={MAX_PRS}"]))
    by_test: dict[str, set[int]] = {}
    red_prs: list[int] = []
    logs_fetched = fetch_failed = 0
    for pr in prs:
        num, sha = pr["number"], pr["head"]["sha"]
        # The Actions API, not `commits/<sha>/check-runs`: that one needs a
        # `checks` scope agent-measure does not hold, and every job here is an
        # Actions job anyway. A job id is the check-run id, so the log URL is
        # the same either way.
        runs = json.loads(gh(["api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50"]))
        failed = []
        for wr in runs.get("workflow_runs") or []:
            if wr.get("name") not in GATE_WORKFLOWS or wr.get("conclusion") != "failure":
                continue
            jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{wr['id']}/jobs"]))
            failed += [j for j in jobs.get("jobs") or []
                       if j.get("name") in GATE_CHECKS and j.get("conclusion") == "failure"]
        if not failed:
            continue
        red_prs.append(num)
        for run in failed:
            try:
                log = gh(["api", f"repos/{repo}/actions/jobs/{run['id']}/logs"])
            except RuntimeError:
                fetch_failed += 1
                continue
            logs_fetched += 1
            for test in failed_tests(log):
                by_test.setdefault(test, set()).add(num)
    tally = sorted(({"test": t, "prs": sorted(p)} for t, p in by_test.items()),
                   key=lambda r: (-len(r["prs"]), r["test"]))
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "open_prs": len(prs),
        "red_prs": sorted(red_prs),
        "logs_fetched": logs_fetched,
        "fetch_failed": fetch_failed,
        "by_test": tally,
    }


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv[1:])
    try:
        doc = collect(gh, a.repo, now or datetime.now(timezone.utc))
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::warning::gate failures not collected ({exc.__class__.__name__}: {exc}); "
              f"{a.out} is the previous one")
        return 1
    a.out.write_text(json.dumps(doc, indent=2) + "\n")
    shared = [r for r in doc["by_test"] if len(r["prs"]) >= 2]
    print(f"wrote {a.out}: {len(doc['red_prs'])} of {doc['open_prs']} open PRs red, "
          f"{len(shared)} test(s) failing on 2+ PRs, {doc['fetch_failed']} log fetch(es) failed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
