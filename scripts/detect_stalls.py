#!/usr/bin/env python3
"""Detect a stalled delivery pipeline. Deterministic: no judgment, no model.

WHY THIS EXISTS
---------------
Every loop in this repo takes work from the BACKLOG. Not one watches whether
the pipeline is flowing. So between 2026-10-08 and 10-10, each of these sat
unnoticed and none of them produced a red run:

  * PR #319 carried `qa-pass`, had green gates, and could never merge: a
    `cancelled` check run from `cancel-in-progress` voted forever. agent-merge
    declined correctly and exited 0 nine hours running.
  * PR #303 sat as a draft from 18:09 because /agent-cycle opened it before QA
    and nothing ever ran `gh pr ready`.
  * #268, #304 and #270 each had a merged PR and a green production
    verification and stayed open, because the close chain was broken in three
    different places.
  * agent-work's measurement fetch returned HTTP 403 on every run since it was
    wired. The step is `continue-on-error`, so every run went green.

`chief` is the role meant to resolve a deadlock, and `chief.md` says "You
cannot initiate. If no escalation arrives, you produce nothing." That was
deliberate — an agent that can decide it needs authority is the failure this
repo has twice. The consequence is that the one role able to act could not
notice.

THIS SCRIPT IS THE MISSING ESCALATION, AND IT IS NOT AN AGENT ON PURPOSE.
An agent that decides whether the system is stuck can decide that it is not.
Every condition below is computable from the GitHub API, and each one is here
because it actually happened.

EXIT CODES, matching the house convention
  0  no stalls
  1  stalls found (the caller escalates)
  2  could not determine — NOT a pass

USAGE
  uv run python scripts/detect_stalls.py [--hours N] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

REPO = "mahAnuj/astro-ai"

# A PR needs longer than a gate run to be judged stalled. pr-gates takes ~8-11
# min and the agent cycle can push again mid-flight, so anything under an hour
# is normal operation rather than a stall.
DEFAULT_HOURS = 4


def gh(*args: str) -> str:
    """`gh` with the repo pinned. Raises on failure so exit 2 is reachable."""
    out = subprocess.run(("gh", *args), capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} -> {out.returncode}: {out.stderr.strip()[:300]}")
    return out.stdout


def age_hours(iso: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 3600


def latest_checks(sha: str) -> dict[str, str]:
    """One conclusion per check NAME, the latest.

    A name recurs on a SHA and an older entry never disappears, so a
    `cancelled` run from `cancel-in-progress` votes forever unless reduced.
    That is exactly what blocked PR #319, and agent-merge now reduces the same
    way. Reading it differently here would make this detector disagree with the
    gate it is watching.
    """
    raw = json.loads(gh("api", f"repos/{REPO}/commits/{sha}/check-runs", "--paginate"))
    newest: dict[str, dict] = {}
    for c in sorted(raw.get("check_runs", []), key=lambda c: (c.get("started_at") or "", c.get("id") or 0)):
        newest[c["name"]] = c
    return {n: (c.get("conclusion") or "pending") for n, c in newest.items()}


def find_stalls(hours: float) -> list[dict]:
    stalls: list[dict] = []

    prs = json.loads(gh("pr", "list", "--repo", REPO, "--state", "open", "--limit", "50",
                        "--json", "number,title,isDraft,labels,headRefName,headRefOid,createdAt,updatedAt"))

    for pr in prs:
        n, age = pr["number"], age_hours(pr["createdAt"])
        if age < hours:
            continue
        # The owning issue, taken from the branch name rather than guessed. The
        # steward routes on this, so leaving it to be inferred downstream is how
        # a dispatch lands on the wrong issue. `grep`-equivalent, not GNU sed:
        # `\+` is a GNU extension and matched nothing on BSD twice this week.
        m = re.match(r"^issue/(\d+)", pr["headRefName"] or "")
        issue = int(m.group(1)) if m else None
        labels = {l["name"] for l in pr["labels"]}
        # `merge` is agent-merge's own check run; it is not a gate.
        checks = {k: v for k, v in latest_checks(pr["headRefOid"]).items() if k != "merge"}
        green = bool(checks) and all(v == "success" for v in checks.values())

        if pr["isDraft"]:
            # /agent-cycle opens the PR in draft BEFORE QA, deliberately, so the
            # work survives the runner. Nothing used to take it out. A draft
            # cannot merge and GitHub reports nothing about why. (PR #303, #321.)
            stalls.append(dict(kind="draft-never-readied", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"draft for {age:.0f}h; gh pr ready was never run",
                               checks=checks, labels=sorted(labels)))
        elif "qa-pass" in labels and "qa-fail" not in labels and green:
            # Every merge condition satisfied. If it is still open, the gate
            # read something it did not anticipate. (PR #319, nine hours.)
            stalls.append(dict(kind="mergeable-but-open", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"qa-pass, every latest check green, open {age:.0f}h",
                               checks=checks, labels=sorted(labels)))
        elif not checks:
            # Zero checks is not "not yet green", it is "nothing ever ran", and
            # agent-merge refuses on it forever. (PR #303's action_required.)
            stalls.append(dict(kind="no-checks-ever", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"open {age:.0f}h with no check runs at all",
                               checks={}, labels=sorted(labels)))
        elif "qa-pass" not in labels and "qa-fail" not in labels and green:
            # Gates green and no verdict either way: the cycle did not reach QA.
            # Distinct from the above because the fix is a QA dispatch, not a
            # pipeline repair. (PR #315, #318, #321.)
            stalls.append(dict(kind="no-qa-verdict", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"gates green, no qa-pass or qa-fail after {age:.0f}h",
                               checks=checks, labels=sorted(labels)))

    # THE WATCHER IS NOT WATCHED. This condition is the answer to "if the steward
    # did not act, why did nothing notice".
    #
    # The steward runs 09:00 and 15:00 UTC. A stall it is capable of clearing —
    # a draft needing a cycle, a missing QA verdict — that is still here after
    # three of its runs means the steward SAW it and achieved nothing. Measured
    # 2026-10-10/11: runs 38061473379 and 38078264987 both diagnosed PR #321,
    # #318 and #315 correctly, dispatched nothing, and concluded success. Green
    # twice, pipeline still stopped. That is the defect the steward exists to
    # catch, committed by the steward.
    #
    # `chief` cannot notice this itself: it is invoked only by escalation and
    # cannot initiate, deliberately. So the detector notices, because
    # deterministic code is the one part of this system that cannot report
    # success having done nothing. It escalates PAST the steward to `chief`,
    # which holds the precedence for deciding what to do about it.
    #
    # 18h, not a run count, and the reason matters more than I first wrote.
    #
    # The first version said "three scheduled runs fit in 18 hours". That is not
    # reliable: GitHub delays free-tier crons by hours. Measured — the steward's
    # `0 9,15 * * *` fired at 14:54 and 19:03, and agent-work's `0 23 * * *`
    # fired at 02:09 and 01:38, each roughly three hours late. A run count
    # inferred from wall-clock is therefore a guess.
    #
    # The condition stands on its own without that inference: a stall the
    # steward is able to clear, still present 18 hours later, is unresolved
    # regardless of how many runs saw it. That is the signal — persistence, not
    # attendance.
    #
    # Still a duration rather than a cross-reference of run history, because
    # reading that history needs the Actions API, and the agent's own token 403s
    # on it (#323). A detector that can fail on a permission is how the
    # measurement arm stayed silent for its entire life.
    STEWARD_CLEARABLE = {"draft-never-readied", "no-qa-verdict"}
    for st in list(stalls):
        if st["kind"] in STEWARD_CLEARABLE and (st["age_h"] or 0) > 18:
            stalls.append(dict(
                kind="steward-ineffective", pr=st["pr"], issue=st["issue"],
                age_h=st["age_h"],
                detail=(f"PR #{st['pr']} has been `{st['kind']}` for {st['age_h']:.0f}h. "
                        "The steward has had at least three scheduled runs in that window "
                        "and cleared nothing. ESCALATE TO CHIEF (Shape B) rather than "
                        "repeating the diagnosis."),
                checks=st["checks"], labels=st["labels"]))

    # A dead trigger leg. agent-merge's `workflow_run` leg failed 100% of the
    # time since it was written and nobody noticed, because its
    # `pull_request_target` leg worked and merges kept happening. A leg that
    # never succeeds is broken, not idle.
    for wf, leg in (("agent-merge.yml", "workflow_run"), ("agent-merge.yml", "pull_request_target")):
        try:
            runs = json.loads(gh("run", "list", "--repo", REPO, "--workflow", wf,
                                 "--limit", "40", "--json", "event,conclusion,createdAt"))
        except RuntimeError:
            continue
        leg_runs = [r for r in runs if r["event"] == leg]
        if leg_runs and not any(r["conclusion"] == "success" for r in leg_runs):
            stalls.append(dict(kind="dead-trigger-leg", pr=None, issue=None, age_h=None,
                               detail=f"{wf}: the `{leg}` leg has {len(leg_runs)} runs and zero successes",
                               checks={}, labels=[]))

    return stalls


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hours", type=float, default=DEFAULT_HOURS,
                    help=f"how old before a PR counts as stalled (default {DEFAULT_HOURS})")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv[1:])

    print("Pipeline stall detector — deterministic, no model")
    print(f"  repo {REPO}, threshold {args.hours}h\n")

    try:
        stalls = find_stalls(args.hours)
    except Exception as exc:  # noqa: BLE001 — any failure means "cannot determine"
        print(f"COULD NOT VERIFY (exit 2) — {type(exc).__name__}: {exc}")
        print("This is NOT a pass. The pipeline may be stalled and unobserved.")
        return 2

    if args.json:
        print(json.dumps(stalls, indent=2))

    if not stalls:
        # Say it explicitly. A detector that prints nothing when it finds
        # nothing is indistinguishable from one that did not run.
        print("PASS — no stall detected. Checked: drafts never readied, "
              "mergeable-but-open, PRs with no checks, missing QA verdicts, "
              "dead trigger legs.")
        return 0

    for s in stalls:
        where = f"PR #{s['pr']}" if s["pr"] else "workflow"
        owns = f"(issue #{s['issue']})" if s.get("issue") else ""
        print(f"STALL  {s['kind']:22} {where:10} {owns:14} {s['detail']}")
        if s["checks"]:
            print(f"       checks: {', '.join(f'{k}={v}' for k, v in sorted(s['checks'].items()))}")

    ineffective = [x for x in stalls if x["kind"] == "steward-ineffective"]
    print(f"\nFAIL - {len(stalls)} stall(s). The pipeline is not flowing.")
    if ineffective:
        print(f"       {len(ineffective)} of them have outlived three steward runs: "
              "ESCALATE TO CHIEF (Shape B). Diagnosing again is the loop that "
              "produced this finding.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
