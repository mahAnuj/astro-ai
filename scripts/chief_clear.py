#!/usr/bin/env python3
"""Carry out chief's ruling to clear a trust-boundary hold (#719).

WHY THIS EXISTS
---------------
The owner granted `chief` the authority to clear `needs-human-review`
(CLAUDE.md, 2026-11-01): remove that label and add `chief-cleared`, after a
ruling comment bound to the head SHA. Nobody gave it the means. Both steps in
`agent-steward.yml` that run chief deny `gh pr edit`, so chief could post the
ruling and never apply the label. Measured on PR #706: chief ruled
`chief-cleared at b9077f6...` at 2026-11-05T00:51Z, and the PR was still held
seven hours later, until the owner applied the labels by hand.

The fix keeps the agent unable to label anything. It follows the dispatch
carrier's pattern ("CHIEF DECIDES, CODE EXECUTES"): chief writes its ruling to
`/tmp/chief-clear.txt`, and this script, in a plain `run:` step holding the
job's own `pull-requests: write`, checks that ruling and applies it. No scope
is added.

WHAT IS CHECKED, AND WHY THE SCRIPT DOES NOT TRUST THE FILE
-----------------------------------------------------------
A line in a file is a claim. Each line is `pr=<number> sha=<40-hex head sha>`.
The labels change only when ALL of these read true from the API now:

  1. the PR is open and its head IS that sha  (a clearance never survives a push)
  2. it carries `needs-human-review`          (otherwise there is no hold to clear)
  3. `qa-pass` AND `qa:independent`, no `qa-fail`   (chief.md precondition 1)
  4. the `gates` check run on that sha concluded `success`   (precondition 2)
  5. a `claude[bot]` comment contains `chief-cleared at <sha>`  (precondition 4:
     the ruling comes first, and agent-merge re-checks this same string)
  6. a `claude[bot]` `QA: PASS` verdict whose first line names that sha  (the
     labels cannot say which commit they are about -- #706 carried an
     independent PASS from b9077f6 onto da2f7d3 after a merge of main)

Precondition 3, that chief read the diff, cannot be checked by code; the
ruling comment is chief's record of it. Any refusal leaves every label as it
was. Any API failure counts as a refusal, so a hiccup keeps the hold.

At most MAX_LINES lines are read, so a runaway ruling file cannot relabel the
repository.

EXIT CODES
----------
  0  every line was applied, or there was no file (no ruling this run)
  1  at least one line was refused or failed -- the reasons are printed
  2  bad arguments
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

RULER = "claude[bot]"
HOLD = "needs-human-review"
CLEARED = "chief-cleared"
MAX_LINES = 3
_LINE = re.compile(r"^pr=(\d+)\s+sha=([0-9a-f]{40})$")

Runner = Callable[[list[str]], str]


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {p.stderr.strip()[:200]}")
    return p.stdout


def parse(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    """(rulings, problems). Blank lines and `#` comments are ignored."""
    rulings, problems = [], []
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    for l in lines[:MAX_LINES]:
        m = _LINE.match(l)
        if m:
            rulings.append((int(m.group(1)), m.group(2)))
        else:
            problems.append(f"not `pr=<n> sha=<40-hex>`: {l[:80]!r}")
    if len(lines) > MAX_LINES:
        problems.append(f"{len(lines) - MAX_LINES} line(s) past the first {MAX_LINES} ignored")
    return rulings, problems


def refusal(gh: Runner, repo: str, pr: int, sha: str) -> str | None:
    """Why NOT to clear PR #pr at sha, or None when every check holds."""
    try:
        state, head, labels = gh(["api", f"repos/{repo}/pulls/{pr}", "--jq",
                                  '[.state, .head.sha, ([.labels[].name] | join(","))] | @tsv'
                                  ]).rstrip("\n").split("\t")
    except (RuntimeError, ValueError) as exc:
        return f"could not read the PR ({exc})"
    have = set(labels.split(",")) - {""}
    if state != "open":
        return f"PR is {state}"
    if head != sha:
        return f"head is {head[:7]}, the ruling names {sha[:7]}; a clearance does not survive a push"
    if HOLD not in have:
        return f"no `{HOLD}` label, so there is no hold to clear"
    if "qa-fail" in have:
        return "`qa-fail` is on the PR; a hold can be cleared, a verdict cannot"
    if not {"qa-pass", "qa:independent"} <= have:
        return "needs `qa-pass` AND `qa:independent` (chief.md precondition 1)"
    try:
        gates = gh(["api", f"repos/{repo}/commits/{sha}/check-runs?check_name=gates&per_page=20",
                    "--jq", "[.check_runs[].conclusion] | join(\",\")"]).strip()
    except RuntimeError as exc:
        return f"could not read the gates check ({exc})"
    if not gates or any(c != "success" for c in gates.split(",")):
        return f"`gates` on {sha[:7]} is not green ({gates or 'no run'})"
    try:
        ruled = gh(["api", f"repos/{repo}/issues/{pr}/comments?per_page=100", "--jq",
                    f'[.[] | select(.user.login == "{RULER}")'
                    f' | select(.body | contains("chief-cleared at {sha}"))] | length']).strip()
    except RuntimeError as exc:
        return f"could not read the comments ({exc})"
    if not ruled.isdigit() or int(ruled) == 0:
        return f"no `{RULER}` comment contains `chief-cleared at {sha}`; the ruling comes first"
    # The QA labels cannot say which commit they are about. On #706 `main` was
    # merged in after an independent PASS at b9077f6, and the labels stayed on
    # the new head da2f7d3. The verdict COMMENT names its sha, so require one
    # for this head -- the same binding agent-merge applies to the ruling.
    try:
        passed = gh(["api", f"repos/{repo}/issues/{pr}/comments?per_page=100", "--jq",
                     f'[.[] | select(.user.login == "{RULER}")'
                     f' | select(.body | startswith("QA: PASS"))'
                     f' | select(.body | split("\\n")[0] | contains("{sha}"))] | length']).strip()
    except RuntimeError as exc:
        return f"could not read the QA verdicts ({exc})"
    if not passed.isdigit() or int(passed) == 0:
        return (f"no `{RULER}` `QA: PASS` verdict names {sha[:7]}; the QA labels may be left "
                f"over from an earlier commit")
    return None


def apply(gh: Runner, repo: str, pr: int) -> None:
    gh(["api", "-X", "POST", f"repos/{repo}/issues/{pr}/labels", "-f", f"labels[]={CLEARED}"])
    gh(["api", "-X", "DELETE", f"repos/{repo}/issues/{pr}/labels/{HOLD}"])


def main(argv: list[str], gh: Runner = run_gh) -> int:
    if len(argv) != 2:
        print("usage: chief_clear.py <ruling-file>", file=sys.stderr)
        return 2
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        print("::error::GH_REPO must be owner/repo", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print("no clearance ruling this run")
        return 0
    rulings, problems = parse(path.read_text())
    failed = bool(problems)
    for p in problems:
        print(f"::warning::{p}")
    for pr, sha in rulings:
        why = refusal(gh, repo, pr, sha)
        if why:
            print(f"::warning::PR #{pr}: NOT cleared -- {why}")
            failed = True
            continue
        try:
            apply(gh, repo, pr)
        except RuntimeError as exc:
            print(f"::error::PR #{pr}: labelling failed ({exc}); the hold may be half-cleared -- "
                  f"agent-merge still refuses it while `{HOLD}` is present")
            failed = True
            continue
        print(f"PR #{pr}: cleared at {sha[:7]} -- `{CLEARED}` added, `{HOLD}` removed; "
              f"agent-merge merges it on its own checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
