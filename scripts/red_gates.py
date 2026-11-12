#!/usr/bin/env python3
"""Decide what to do about a PR whose gates just went red (#912).

WHY THIS EXISTS
---------------
Measured 2026-11-12: five open PRs sat 9-20 hours with red gates and nothing
acted. Three (#899, #900, #901) were a runner network blip -- `apt-get install
poppler-utils` could not resolve `security.ubuntu.com` -- so their code was
never tested at all. Two (#892, #884) were real failures a cycle could fix.
`qa-on-green` exits on any non-green gate, `detect_stalls.py` has no stall
kind for red gates, and repo rules forbid an empty commit to re-trigger CI, so
a red PR waited for a human every time.

WHAT IT DECIDES (printed as `action=<a>` plus details, and written to
$GITHUB_OUTPUT):

  rerun   the failed job log shows an infrastructure flake and NO test or
          gate result -- the code was never judged. Only on run_attempt 1, so
          a real outage is re-run once, not forever.
  fix     a real failure on a loop branch that names its issue (issue/, partial/
          or fix/ + <n>-), whose diff does not touch .github/workflows/ (the
          cycle's token cannot push there). Dispatched once per head: the
          workflow writes a marker comment first, the same guard as the green
          path's `qa-on-green: dispatched at <sha>`.
  notify  a real failure nothing here can fix (an owner branch, a workflows
          diff): one comment naming the failing gates, once per head.
  none    not this loop's PR, a moved head, or already handled for this head.

EXIT CODES: 0 decided (action may be none)   2 bad environment
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Callable

Runner = Callable[[list[str]], str]

#: Strings a runner prints when the MACHINE failed, not the code. Matched only
#: when no test or gate verdict appears in the same log (see `is_flake`).
FLAKE = re.compile(
    r"Temporary failure resolving|Could not resolve host|Unable to fetch some archives"
    r"|Failed to fetch https?://|The runner has received a shutdown signal"
    r"|lost communication with the server|Connection timed out|Read timed out"
    r"|Installation process exited with code: 100|ECONNRESET|503 Service Unavailable")

#: Any of these means the job got far enough to judge the code, so a failure
#: is real even if a flaky line also appears.
JUDGED = re.compile(
    r"FAILED tests/|##\[error\]verify_\w+ (FAIL|SKIPPED)|gates passed|tests did not run"
    r"|FAIL — |\d+ passed")         # unanchored: raw job logs prefix every line with a timestamp

ISSUE_BRANCH = re.compile(r"^(?:issue|partial|fix)/(\d+)-")
FIX_MARK = "qa-on-green: fix dispatched at"
NOTE_MARK = "qa-on-green: red gates noted at"


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def is_flake(log: str) -> bool:
    return bool(FLAKE.search(log)) and not JUDGED.search(log)


def failed_jobs(gh: Runner, repo: str, run_id: str) -> list[dict]:
    jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{run_id}/jobs"])).get("jobs") or []
    return [j for j in jobs if j.get("conclusion") == "failure"]


def decide(gh: Runner, env: dict) -> dict:
    repo, run_id, sha = env["GH_REPO"], env["RUN_ID"], env["HEAD_SHA"]
    branch, attempt = env["HEAD_BRANCH"], int(env.get("RUN_ATTEMPT") or "1")
    authors = {a.strip() for a in env.get("AGENT_AUTHORS", "").split(",") if a.strip()}
    if branch.startswith("measurements/"):
        return {"action": "none", "why": "a measurement PR self-merges"}
    prs = json.loads(gh(["api", f"repos/{repo}/pulls?state=open&per_page=100"]))
    pr = next((p for p in prs if (p.get("head") or {}).get("ref") == branch), None)
    if not pr:
        return {"action": "none", "why": f"no open PR on {branch}"}
    num, login = pr["number"], (pr.get("user") or {}).get("login", "")
    if login not in authors:
        return {"action": "none", "why": f"#{num} by {login}, not in AGENT_AUTHORS"}
    if pr["head"]["sha"] != sha:
        return {"action": "none", "why": f"#{num} moved past {sha[:7]}"}

    jobs = failed_jobs(gh, repo, run_id)
    logs = []
    for j in jobs:
        try:
            logs.append(gh(["api", f"repos/{repo}/actions/jobs/{j['id']}/logs"]))
        except RuntimeError:
            logs.append("")          # unreadable log: never call it a flake
    if jobs and all(is_flake(lg) for lg in logs):
        if attempt > 1:
            return {"action": "none", "pr": num,
                    "why": "a flake again on a re-run: an outage, not a blip; left for a human"}
        return {"action": "rerun", "pr": num, "why": "runner flake before any test ran"}

    comments = json.loads(gh(["api", f"repos/{repo}/issues/{num}/comments?per_page=100"]))
    seen = "\n".join(c.get("body") or "" for c in comments)
    names = ", ".join(j.get("name", "?") for j in jobs) or env.get("WORKFLOW_NAME", "gates")
    m = ISSUE_BRANCH.match(branch)
    files = json.loads(gh(["api", f"repos/{repo}/pulls/{num}/files?per_page=100"]))
    touches_wf = any((f.get("filename") or "").startswith(".github/workflows/") for f in files)
    if m and not touches_wf:
        if f"{FIX_MARK} {sha}" in seen:
            return {"action": "none", "pr": num, "why": f"a fix was already dispatched at {sha[:7]}"}
        return {"action": "fix", "pr": num, "issue": int(m.group(1)), "jobs": names,
                "why": f"real failure in {names}; a cycle can push to {branch}"}
    if f"{NOTE_MARK} {sha}" in seen:
        return {"action": "none", "pr": num, "why": f"already noted at {sha[:7]}"}
    return {"action": "notify", "pr": num, "jobs": names,
            "why": ("the diff touches .github/workflows/, which a cycle cannot push" if touches_wf
                    else f"{branch} names no issue for a cycle to adopt")}


def main(argv: list[str], gh: Runner = run_gh) -> int:
    need = ("GH_REPO", "RUN_ID", "HEAD_SHA", "HEAD_BRANCH")
    env = {k: os.environ.get(k, "") for k in (*need, "RUN_ATTEMPT", "AGENT_AUTHORS", "WORKFLOW_NAME")}
    if any(not env[k] for k in need) or not re.fullmatch(r"[0-9a-f]{40}", env["HEAD_SHA"]) \
            or not re.fullmatch(r"\d+", env["RUN_ID"]):
        print("::error::red_gates.py needs GH_REPO, RUN_ID, HEAD_SHA (40-hex) and HEAD_BRANCH")
        return 2
    try:
        d = decide(gh, env)
    except (RuntimeError, ValueError, KeyError) as exc:
        d = {"action": "none", "why": f"could not decide ({exc.__class__.__name__}: {str(exc)[:120]})"}
    print(f"action={d['action']}: {d.get('why', '')}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            for k in ("action", "pr", "issue", "jobs"):
                if k in d:
                    fh.write(f"{k}={str(d[k]).replace(chr(10), ' ')}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
