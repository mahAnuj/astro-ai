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
  4. the LATEST `gates` check run on that sha is completed and `success`
     (precondition 2). Latest by (started_at, id): a superseded red run does
     not veto a head whose re-run is green (#1442, PR #1428), and a later red
     run still refuses an earlier green one
  5. a `claude[bot]` comment contains `chief-cleared at <sha>`  (precondition 4:
     the ruling comes first, and agent-merge re-checks this same string)
  6. a `QA: PASS` verdict from `claude[bot]` or the repo owner, as agent-merge
     accepts, whose first line names that sha  (the labels cannot say which
     commit they are about -- #706 carried an independent PASS from b9077f6
     onto da2f7d3 after a merge of main)

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

AFTER A CLEARANCE (#759)
------------------------
When at least one PR was cleared, the script dispatches `agent-merge.yml` once
(`workflow_dispatch`, which `github.token` may do under the job's existing
`actions: write`). It writes no label and adds no scope. Never on a refusal.
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


def qa_authors(repo: str) -> tuple[str, ...]:
    """Who may author a `QA: PASS` verdict: the same set agent-merge accepts.

    A top-level session records its verdict as the repo owner, so a PASS the
    merge gate takes must not be refused here (#1287). The RULING stays
    `claude[bot]` only. `main` rejects any repo that is not word characters,
    dots and dashes either side of one slash before this runs, so the owner
    is safe to interpolate into a jq filter.
    """
    return (RULER, repo.split("/")[0])


def _count_matches(gh: Runner, repo: str, pr: int, who: str, body_filters: str) -> int:
    """How many comments on PR #pr match `who` and `body_filters`.

    `--paginate` runs `--jq` once PER PAGE, so a filter ending in `length`
    prints one number per page and a match on page 2 reads as garbage or as
    zero: on a PR with over 100 comments the ruling or verdict went missing
    (#1287). Emit one id per match and count the lines, as agent-merge does.
    Anything but a digit-only line is not counted, so odd output fails closed;
    an API error still raises.
    """
    out = gh(["api", "--paginate", f"repos/{repo}/issues/{pr}/comments?per_page=100", "--jq",
              f".[] | select({who}) | {body_filters} | .id"])
    return sum(1 for line in out.splitlines() if line.strip().isdigit())


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


def _latest_gates(raw: str) -> dict | None:
    """The `gates` run with the greatest (started_at, id), or None.

    None on empty output, malformed JSON or a line with no `id`: the caller
    refuses, so anything odd fails closed. A null `started_at` (a queued run)
    sorts last via "~", which is above every ISO timestamp, so a pending
    re-run over an older green refuses rather than being skipped.
    """
    runs = []
    try:
        for line in raw.splitlines():
            if line.strip():
                r = json.loads(line)
                r["id"]                     # a line with no id is not a run we can order
                runs.append(r)
        return max(runs, key=lambda r: (r.get("started_at") or "~", r["id"])) if runs else None
    except (ValueError, KeyError, TypeError):
        return None


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
        # JSON lines, not a joined string: the joined conclusions of EVERY run
        # let a superseded failure veto a green re-run (#1442, PR #1428 head
        # c2621f7: failure 04:25:30Z, success 04:33:27Z). `filter=all` so a
        # re-run is listed beside the run it replaced rather than left to
        # GitHub's own idea of "latest"; we pick the latest ourselves.
        gates = gh(["api", "--paginate",
                    f"repos/{repo}/commits/{sha}/check-runs?check_name=gates&per_page=100&filter=all",
                    "--jq", ".check_runs[] | {id, started_at, status, conclusion}"])
    except RuntimeError as exc:
        return f"could not read the gates check ({exc})"
    latest = _latest_gates(gates)
    # Green only when the LATEST run is completed AND success. Never "any
    # success" and never "ignore failures": a red run that came after the
    # green one still refuses.
    if not latest or not (latest.get("status") == "completed"
                          and latest.get("conclusion") == "success"):
        seen = (f"latest run {latest['id']}: {latest.get('status')}/{latest.get('conclusion')}"
                if latest else "no run")
        return f"`gates` on {sha[:7]} is not green ({seen})"
    try:
        ruled = _count_matches(gh, repo, pr, f'.user.login == "{RULER}"',
                               f'select(.body | contains("chief-cleared at {sha}"))')
    except RuntimeError as exc:
        return f"could not read the comments ({exc})"
    if ruled == 0:
        return f"no `{RULER}` comment contains `chief-cleared at {sha}`; the ruling comes first"
    # The QA labels cannot say which commit they are about. On #706 `main` was
    # merged in after an independent PASS at b9077f6, and the labels stayed on
    # the new head da2f7d3. The verdict COMMENT names its sha, so require one
    # for this head -- the same binding agent-merge applies to the ruling.
    # Authors are the set agent-merge accepts (claude[bot] or the owner, #1287).
    authors = qa_authors(repo)
    try:
        passed = _count_matches(gh, repo, pr,
                                " or ".join(f'.user.login == "{a}"' for a in authors),
                                'select(.body | startswith("QA: PASS"))'
                                ' | select(.body | split("\\n")[0] | contains("' + sha + '"))')
    except RuntimeError as exc:
        return f"could not read the QA verdicts ({exc})"
    if passed == 0:
        return (f"no `{authors[0]}` or `{authors[1]}` `QA: PASS` verdict names {sha[:7]}; "
                f"the QA labels may be left over from an earlier commit")
    return None


def apply(gh: Runner, repo: str, pr: int) -> None:
    gh(["api", "-X", "POST", f"repos/{repo}/issues/{pr}/labels", "-f", f"labels[]={CLEARED}"])
    gh(["api", "-X", "DELETE", f"repos/{repo}/issues/{pr}/labels/{HOLD}"])


def dispatch_sweep(gh: Runner, repo: str) -> None:
    """Start one `agent-merge` sweep after a clearance (#759).

    A label applied with `github.token` starts no workflow run (GitHub's own
    rule for events a workflow creates), so a cleared PR waited for an
    unrelated edge or the throttled `*/30` cron: #749 and #750 sat cleared for
    13-14 hours, #810 for 13 minutes. `workflow_dispatch` is the documented
    exception, and the merge job already uses it to chain sweeps. The sweep
    re-reads every merge condition from the API, so this cannot merge anything
    the cron would have refused; it only removes the wait. Warning-only: a
    failed dispatch leaves the clearance in place and the cron still reaches it.
    """
    try:
        gh(["workflow", "run", "agent-merge.yml", "--repo", repo, "--ref", "main"])
    except RuntimeError as exc:
        print(f"::warning::cleared, but could not dispatch agent-merge ({exc}); "
              f"the */30 sweep will reach it")
    else:
        print("dispatched one agent-merge sweep for the cleared PR(s)")


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
    cleared = 0
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
        cleared += 1
        print(f"PR #{pr}: cleared at {sha[:7]} -- `{CLEARED}` added, `{HOLD}` removed; "
              f"agent-merge merges it on its own checks")
    if cleared:
        dispatch_sweep(gh, repo)       # once per run, however many PRs were cleared
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
