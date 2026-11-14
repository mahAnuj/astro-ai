#!/usr/bin/env python3
"""After a QA round on a PR fails, decide whether the loop fixes it (2026-11-13).

WHY THIS EXISTS
---------------
Owner, 2026-11-13: "let the loop fix session PRs too". A QA round on a PR whose
branch names no issue (`claude/...`, `feat/...`) is judge-only (agent-cycle.md
Step 0c): it writes `qa-fail` and stops. Nothing then pushed a fix, and nothing
ever would: `qa-on-green` fires when the GATES complete, and a judge-only round
pushes nothing, so the gates never run again. Measured on #951 that morning:
QA FAIL at 8fc8642 with one precise, fixable defect, and the PR waited for a
session to push.

So after a QA round, this reads the round's own verdict and, when it is a FAIL
the loop can fix, writes ONE `fix_pr=<n>` ruling for scripts/dispatch_cycle.sh.
That run (`/agent-cycle --fix-pr <n>`, Step 0d) fixes exactly the findings and
pushes to the PR's branch; the push re-runs the gates, and qa-on-green's
"a fix landed after the FAIL" path sends a fresh round. Nothing here is a
model, and nothing here writes or reads a label as a decision.

WHAT IT DECIDES (`action=<a>` on stdout and in $GITHUB_OUTPUT)

  fix   the latest `QA: FAIL — verified at <sha>` from claude[bot] names the
        PR's CURRENT head, the branch names no issue (an issue branch is the
        steward's, through `issue=<n>`), the diff touches no
        .github/workflows/ file (the cycle token cannot push one), and the PR
        has had fewer than MAX_PR_FIXES automatic fixes. The marker comment is
        written HERE, before the dispatch, as on every other dispatch path.
  none  anything else, with the reason.

EXIT CODES: 0 decided   2 bad environment
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Callable

Runner = Callable[[list[str]], str]

#: Shared with scripts/red_gates.py: both paths count the same markers, so a PR
#: gets MAX_PR_FIXES automatic fixes in total, whatever triggered them.
FIX_MARK = "qa-on-green: fix dispatched at"
MAX_PR_FIXES = 3
ISSUE_BRANCH = re.compile(r"^(?:issue|partial|fix)/(\d+)-")
FAIL_LINE = re.compile(r"^QA: FAIL\b.*?\b([0-9a-f]{40})\b")


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:200] or f"gh exited {p.returncode}")
    return p.stdout


#: The loop's own identities. The repo owner is added from the repo name, and
#: AGENT_AUTHORS (agent-merge.yml's list) overrides all of it when set.
LOOP_BOTS = ("claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]")


def authors_for(repo: str) -> set[str]:
    env = {a.strip() for a in os.environ.get("AGENT_AUTHORS", "").split(",") if a.strip()}
    return env or {*LOOP_BOTS, repo.split("/", 1)[0]}


def decide(gh: Runner, repo: str, num: int, authors: set[str] | None = None) -> dict:
    pr = json.loads(gh(["api", f"repos/{repo}/pulls/{num}"]))
    if pr.get("state") != "open":
        return {"action": "none", "why": f"#{num} is {pr.get('state')}"}
    if (pr.get("head") or {}).get("repo", {}).get("full_name") != repo:
        return {"action": "none", "why": f"#{num} is from a fork"}
    # QA on #999: the decision file and CLAUDE.md say the fix path is "never an
    # author outside AGENT_AUTHORS", enforced in code -- and this had no such
    # check, so a stranger's same-repo PR with a claude[bot] FAIL got a fix.
    login = (pr.get("user") or {}).get("login", "")
    if login not in (authors if authors is not None else authors_for(repo)):
        return {"action": "none", "why": f"#{num} is by {login or 'unknown'}, not in AGENT_AUTHORS"}
    branch, head = pr["head"]["ref"], pr["head"]["sha"]
    if ISSUE_BRANCH.match(branch):
        return {"action": "none", "why": f"{branch} names its issue; the steward routes that fix"}
    files = json.loads(gh(["api", f"repos/{repo}/pulls/{num}/files?per_page=100"]))
    if any((f.get("filename") or "").startswith(".github/workflows/") for f in files):
        return {"action": "none", "why": "the diff touches .github/workflows/, which a cycle cannot push"}
    comments = json.loads(gh(["api", f"repos/{repo}/issues/{num}/comments?per_page=100"]))
    verdicts = [c for c in comments
                if (c.get("user") or {}).get("login") == "claude[bot]"
                and (c.get("body") or "").startswith("QA: ")]
    if not verdicts:
        return {"action": "none", "why": "no QA verdict from claude[bot] on this PR"}
    first = (verdicts[-1].get("body") or "").split("\n", 1)[0]
    m = FAIL_LINE.match(first)
    if not m:
        return {"action": "none", "why": "the latest verdict is not a FAIL"}
    if m.group(1) != head:
        return {"action": "none", "why": f"the FAIL names {m.group(1)[:7]}, the head is {head[:7]}"}
    bodies = [c.get("body") or "" for c in comments]
    if any(b.startswith(f"{FIX_MARK} {head}") for b in bodies):
        return {"action": "none", "why": f"a fix was already dispatched at {head[:7]}"}
    tried = sum(1 for b in bodies if b.startswith(FIX_MARK))
    if tried >= MAX_PR_FIXES:
        return {"action": "none", "why": f"{tried} automatic fixes already tried; a person takes it from here"}
    return {"action": "fix", "pr": num, "head": head, "target": f"fix_pr={num}",
            "why": f"QA FAIL at {head[:7]} on {branch}; fix {tried + 1} of {MAX_PR_FIXES}"}


def main(argv: list[str], gh: Runner = run_gh) -> int:
    repo, num = os.environ.get("GH_REPO", ""), os.environ.get("PR", "")
    if not repo or not re.fullmatch(r"\d+", num):
        print("::error::pr_fix_after_qa.py needs GH_REPO and a numeric PR")
        return 2
    try:
        d = decide(gh, repo, int(num))
    except (RuntimeError, ValueError, KeyError) as exc:
        d = {"action": "none", "why": f"could not decide ({exc.__class__.__name__}: {str(exc)[:120]})"}
    if d["action"] == "fix" and "--dry-run" not in argv:
        # Marker FIRST: the next run reads it, so a dispatch that happened is
        # never repeated, and the cap counts it.
        gh(["pr", "comment", str(d["pr"]), "--repo", repo, "--body",
            f"{FIX_MARK} {d['head']}\n\nThe QA round failed on this head, and the branch names no issue, "
            f"so one fix run is being dispatched at this PR (`/agent-cycle --fix-pr {d['pr']}`, "
            f"Step 0d): it fixes exactly the findings above and pushes here, and the next QA round "
            f"judges the fix. At most {MAX_PR_FIXES} per PR. Mechanical: no model decided this."])
    print(f"action={d['action']}: {d.get('why', '')}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            for k in ("action", "pr", "target"):
                if k in d:
                    fh.write(f"{k}={d[k]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
