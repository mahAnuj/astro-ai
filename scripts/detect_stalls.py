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


def agent_pushable(pr: int) -> bool:
    """Can an /agent-cycle actually update this PR's branch?

    No, if the diff touches `.github/workflows/**`. The Claude App's token lacks
    the `workflows` scope, so GitHub refuses the push outright:

        refusing to allow a GitHub App to create or update workflow
        .github/workflows/x.yml without `workflows` permission

    That refusal is not a bug to route around — the scope would let the App
    rewrite `pr-gates.yml` and `agent-merge.yml`, which ARE the enforcement, so
    `verify_no_relaxation.py` would be running inside a file the pushing agent
    could edit. chief declined to recommend granting it on 2026-10-11.

    This matters to the DETECTOR because `draft-never-readied` and
    `no-qa-verdict` both route to "dispatch a cycle". On a workflow-file PR that
    dispatch cannot succeed, so the stall persists, `steward-ineffective` fires
    at 18h, and chief is woken to rule the same un-dispatchable answer on every
    run. A stall nothing in the loop can clear is a HUMAN stall, and saying so
    is the difference between an escalation and a treadmill. (PR #315.)

    Fails OPEN — an API error returns True, because wrongly marking a clearable
    PR human-owned hides a real stall, while the reverse merely costs a ruling.
    """
    try:
        files = json.loads(gh("pr", "view", str(pr), "--repo", REPO, "--json", "files"))
    except RuntimeError:
        return True
    paths = [f.get("path", "") for f in files.get("files", [])]
    return not any(q.startswith(".github/workflows/") for q in paths)


#: The #354 trust boundary, as `agent-merge.yml`'s TRUST_BOUNDARY env sets it.
#: Duplicated here deliberately and said so: this script cannot read the
#: workflow's env block, and a detector that GUESSED the boundary would be the
#: thing that routed a `.github/workflows/` PR to chief. If TRUST_BOUNDARY
#: changes there, change this with it.
BOUNDARY = ("src/astro_ai/prompts/", "src/astro_ai/knowledge/",
            ".github/workflows/", "src/astro_ai/events.py",
            "src/astro_ai/notify.py", "src/astro_ai/email_sender.py",
            "src/astro_ai/storage.py")

#: The only two chief may rule on (chief.md Shape C). The other five are not
#: decidable by an agent for blast radius, not seniority: a workflow edit can
#: grant the loop powers, and email/notify reach real people.
CHIEF_DECIDABLE = ("src/astro_ai/prompts/", "src/astro_ai/knowledge/")


def boundary_paths(pr: int) -> set[str]:
    """Which trust-boundary paths this PR touches. Empty set on any failure.

    Fails CLOSED, unlike `agent_pushable` two functions up, and the asymmetry is
    the point. There, an API error returning "clearable" merely costs a ruling.
    Here it would decide that a PR touching nothing dangerous may be cleared by
    an agent — so a files read that 403s must land the PR in front of a human,
    never in front of chief. An empty set means "could not tell", and the caller
    reads it as human-only.
    """
    try:
        files = json.loads(gh("pr", "view", str(pr), "--repo", REPO, "--json", "files"))
    except RuntimeError:
        return set()
    return {q for f in files.get("files", [])
            if isinstance(q := f.get("path", ""), str) and q.startswith(BOUNDARY)}


def qa_fail_age(pr: int) -> float | None:
    """Hours since `qa-fail` was last applied, or None if it never was.

    Read from the timeline rather than the label list, because the label alone
    says a verdict exists and not WHEN — and when is the whole question: a head
    newer than the verdict means somebody fixed it and it needs re-reviewing,
    while a head older than the verdict means nobody has touched it.
    """
    try:
        events = json.loads(gh("api", f"repos/{REPO}/issues/{pr}/timeline",
                               "--paginate", "--jq",
                               '[.[] | select(.event=="labeled")'
                               ' | select(.label.name=="qa-fail") | .created_at]'))
    except RuntimeError:
        return None
    if not isinstance(events, list) or not events:
        return None
    return age_hours(sorted(events)[-1])


def head_pushed_hours_ago(pr: int) -> float | None:
    """Hours since this PR's head commit. None if it cannot be read."""
    try:
        out = json.loads(gh("pr", "view", str(pr), "--repo", REPO, "--json", "commits"))
    except RuntimeError:
        return None
    commits = out.get("commits") or []
    if not commits:
        return None
    return age_hours(commits[-1].get("committedDate") or "")


def find_stalls(hours: float) -> list[dict]:
    stalls: list[dict] = []

    prs = json.loads(gh("pr", "list", "--repo", REPO, "--state", "open", "--limit", "50",
                        "--json", "number,title,isDraft,labels,headRefName,headRefOid,"
                        "createdAt,updatedAt,mergeable"))

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
        pushable = agent_pushable(n)

        if pr["isDraft"] and "qa-fail" in labels:
            # A DRAFT HELD OPEN BY A VERDICT IS NOT A DRAFT NOBODY READIED, and
            # conflating them would have had the loop open a gate somebody shut
            # on purpose. `draft-never-readied` routes to "dispatch a cycle,
            # which runs QA, READIES THE PR and labels it" -- correct for a
            # cycle that died before readying, and catastrophic here.
            #
            # Measured 2026-10-20 on #425: a draft carrying `qa-fail` whose
            # independent round found a live exploitable XSS and said in as many
            # words that it should stay a draft until the sink is escaped. The
            # draft IS the gate. Readying it makes it eligible for pr-gates and
            # then for agent-merge.
            #
            # Checked BEFORE the draft branch, not inside it, because the
            # ordering is the whole defect: `isDraft` was first in the chain, so
            # the label could never be reached.
            stalls.append(dict(
                kind="draft-held-by-qa-fail", pr=n, issue=issue, age_h=round(age, 1),
                detail=(f"draft for {age:.0f}h carrying qa-fail — the draft is the gate, not an "
                        f"oversight. Fix the findings; do NOT ready it."),
                checks=checks, labels=sorted(labels), agent_pushable=pushable))
        elif pr["isDraft"]:
            # /agent-cycle opens the PR in draft BEFORE QA, deliberately, so the
            # work survives the runner. Nothing used to take it out. A draft
            # cannot merge and GitHub reports nothing about why. (PR #303, #321.)
            stalls.append(dict(kind="draft-never-readied", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"draft for {age:.0f}h; gh pr ready was never run",
                               checks=checks, labels=sorted(labels), agent_pushable=pushable))
        elif ("needs-human-review" in labels and "qa-pass" in labels
              and "qa-fail" not in labels and "chief-cleared" not in labels and green):
            # A TRUST-BOUNDARY HOLD, AND WHETHER CHIEF MAY CLEAR IT (Shape C,
            # owner 2026-10-20). `agent-merge` excludes `needs-human-review`
            # from its sweep and nothing else ever removed it, so every such PR
            # waited on one person: #412 sat 59h this way carrying an
            # independent qa-pass and green gates.
            #
            # The detector CLASSIFIES rather than just reporting, because chief
            # may rule on prompts/ and knowledge/ only. Handing it a workflow or
            # email_sender PR would mean the first thing chief does on waking is
            # decline — every 30 minutes, forever — which is the treadmill
            # `agent_pushable` above was written to end.
            bpaths = boundary_paths(n)
            decidable = bool(bpaths) and all(q.startswith(CHIEF_DECIDABLE) for q in bpaths)
            stalls.append(dict(
                kind="boundary-hold-clearable" if decidable else "boundary-hold-human-only",
                pr=n, issue=issue, age_h=round(age, 1),
                detail=((f"needs-human-review for {age:.0f}h with qa-pass and green gates; "
                         f"every boundary path is prompts/ or knowledge/ "
                         f"({', '.join(sorted(bpaths))}) — chief may rule Shape C")
                        if decidable else
                        (f"needs-human-review for {age:.0f}h with qa-pass and green gates, but "
                         f"it touches {', '.join(sorted(bpaths)) or 'paths that could not be read'} "
                         f"— outside chief's Shape C scope. A HUMAN decides this one.")),
                boundary_paths=sorted(bpaths),
                checks=checks, labels=sorted(labels),
                agent_pushable=pushable if decidable else False))
        elif "qa-pass" in labels and "qa-fail" not in labels and green:
            # Every merge condition satisfied. If it is still open, the gate
            # read something it did not anticipate. (PR #319, nine hours.)
            stalls.append(dict(kind="mergeable-but-open", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"qa-pass, every latest check green, open {age:.0f}h",
                               checks=checks, labels=sorted(labels), agent_pushable=pushable))
        elif not checks:
            # Zero checks is not "not yet green", it is "nothing ever ran", and
            # agent-merge refuses on it forever. (PR #303's action_required.)
            #
            # TWO CAUSES, OPPOSITE FIXES, and the detail line now says which.
            #
            # 1. CONFLICTING. `pull_request` workflows run against the MERGE REF
            #    (`refs/pull/N/merge`), which GitHub cannot compute while the PR
            #    has conflicts — so `synchronize` fires and NO run is created.
            #    Not a skipped run, not a failed one: nothing, with no event
            #    anywhere saying why. Reopening does not help; only resolving the
            #    conflict does. Measured on PR #325 on 2026-10-11: `opened` ran
            #    both gates, then two pushes after `main` moved underneath it
            #    produced zero runs, and the only check suite on the head was an
            #    unrelated app's. chief had already inferred this for PR #318
            #    ("a reopen alone will not give checks while the PR is
            #    conflicting") and was right.
            #
            # 2. CREATED BY GITHUB_TOKEN. The PR object exists but GitHub
            #    suppresses its events to stop a workflow triggering itself, so
            #    no push will ever give it checks. Only a human reopening it
            #    fires `reopened`. (PR #303, #318, #322.)
            #
            # Telling them apart is the difference between "resolve the
            # conflict" and "a human must reopen it", and the steward was
            # guessing.
            conflicting = pr.get("mergeable") == "CONFLICTING"
            why = ("the PR is CONFLICTING, so GitHub cannot build the merge ref "
                   "that `pull_request` workflows run against — pushes fire no "
                   "run at all. RESOLVE THE CONFLICT; reopening will not help."
                   if conflicting else
                   "mergeable, so the PR object itself is the problem: it was "
                   "most likely created by GITHUB_TOKEN, whose events GitHub "
                   "suppresses. A HUMAN must close and reopen it.")
            stalls.append(dict(kind="no-checks-ever", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"open {age:.0f}h with no check runs at all — {why}",
                               checks={}, labels=sorted(labels), agent_pushable=pushable,
                               conflicting=conflicting))
        elif "qa-fail" in labels:
            # A VERDICT FOUND DEFECTS AND THE LOOP COULD NOT SEE IT. Until
            # 2026-10-20 every use of `qa-fail` in this file was a NEGATION
            # (`"qa-fail" not in labels`), so a PR carrying it matched no
            # detector at all and was invisible to the loop permanently --
            # which is the most common state a PR is ever in. Measured the
            # moment it was noticed: #410 fired `no-qa-verdict` and
            # `steward-ineffective` while unlabelled, and fired NOTHING once its
            # FAIL was recorded. Recording the verdict correctly hid the PR.
            #
            # Two states, two different actions, and the deciding fact is
            # whether the head moved AFTER the verdict:
            #
            #   head older than the label -> nobody fixed it. Dispatch a cycle
            #                                at the findings.
            #   head newer than the label -> somebody fixed it and no verdict
            #                                has seen the fix. Dispatch QA.
            #
            # Both are obliged actions an agent can perform, which is what keeps
            # this out of chief's lap: it is work, not a decision.
            fail_age = qa_fail_age(n)
            head_age = head_pushed_hours_ago(n)
            if fail_age is None or head_age is None:
                # Could not read one of the two. Report it rather than guessing
                # a direction -- a wrong guess here dispatches the wrong agent
                # and burns a full cycle on it.
                stalls.append(dict(
                    kind="qa-fail-unreadable", pr=n, issue=issue, age_h=round(age, 1),
                    detail=(f"carries qa-fail but the verdict time or the head commit time "
                            f"could not be read, so whether a fix has landed is unknown"),
                    checks=checks, labels=sorted(labels), agent_pushable=False))
            elif head_age < fail_age:
                stalls.append(dict(
                    kind="qa-fail-refixed", pr=n, issue=issue, age_h=round(fail_age, 1),
                    detail=(f"qa-fail {fail_age:.0f}h ago, head pushed {head_age:.0f}h ago — a fix "
                            f"landed after the verdict and no round has seen it. Dispatch QA."),
                    checks=checks, labels=sorted(labels), agent_pushable=pushable))
            else:
                stalls.append(dict(
                    kind="qa-fail-unaddressed", pr=n, issue=issue, age_h=round(fail_age, 1),
                    detail=(f"qa-fail {fail_age:.0f}h ago and nothing pushed since (head is "
                            f"{head_age:.0f}h old) — the findings are unaddressed. Dispatch a "
                            f"cycle at them."),
                    checks=checks, labels=sorted(labels), agent_pushable=pushable))
        elif "qa-pass" not in labels and "qa-fail" not in labels and green:
            # Gates green and no verdict either way: the cycle did not reach QA.
            # Distinct from the above because the fix is a QA dispatch, not a
            # pipeline repair. (PR #315, #318, #321.)
            stalls.append(dict(kind="no-qa-verdict", pr=n, issue=issue, age_h=round(age, 1),
                               detail=f"gates green, no qa-pass or qa-fail after {age:.0f}h",
                               checks=checks, labels=sorted(labels), agent_pushable=pushable))

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
    STEWARD_CLEARABLE = {"draft-never-readied", "no-qa-verdict",
                         "qa-fail-unaddressed", "qa-fail-refixed",
                         "draft-held-by-qa-fail"}
    for st in list(stalls):
        if st["kind"] in STEWARD_CLEARABLE and (st["age_h"] or 0) > 18 \
                and st.get("agent_pushable", True):
            stalls.append(dict(
                kind="steward-ineffective", pr=st["pr"], issue=st["issue"],
                age_h=st["age_h"],
                detail=(f"PR #{st['pr']} has been `{st['kind']}` for {st['age_h']:.0f}h. "
                        "The steward has had at least three scheduled runs in that window "
                        "and cleared nothing. ESCALATE TO CHIEF (Shape B) rather than "
                        "repeating the diagnosis."),
                checks=st["checks"], labels=st["labels"]))

    # A stall no agent can clear. Reported, but NOT as `steward-ineffective`:
    # the steward is not ineffective for declining work it is structurally
    # refused. Distinguishing these is chief's recommendation 2 from the
    # 2026-10-11 ruling, and it is what stops the same un-dispatchable PR
    # waking chief twice a day forever.
    for st in list(stalls):
        if st["kind"] in STEWARD_CLEARABLE and (st["age_h"] or 0) > 18 \
                and not st.get("agent_pushable", True):
            stalls.append(dict(
                kind="human-owned-stall", pr=st["pr"], issue=st["issue"],
                age_h=st["age_h"],
                detail=(f"PR #{st['pr']} has been `{st['kind']}` for {st['age_h']:.0f}h and "
                        "NO agent can clear it: its diff touches `.github/workflows/**`, "
                        "which the App's token is refused on. Do not dispatch a cycle. "
                        "A human updates the branch and records the verdict."),
                checks=st["checks"], labels=st["labels"], agent_pushable=False))

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

    # THE OBLIGED COUNT, emitted from here on purpose.
    #
    # `agent-steward.yml` used to re-derive this with its own grep over the JSON,
    # which meant the routing table existed in three places — steward.md, this
    # script, and a regex in YAML — and the YAML copy silently disagreed the
    # moment `human-owned-stall` was added: it went on counting #315's
    # `no-qa-verdict` as demanding an action no agent can take, which wakes chief
    # twice a day to rule the same thing. One source, read by the step.
    #
    # A stall is obliged only if its kind routes to an action AND an agent can
    # actually perform it. `no-checks-ever` and `dead-trigger-leg` are absent:
    # they route to an escalation or an issue, not a dispatch.
    obliged = [x for x in stalls
               if x["kind"] in {"draft-never-readied", "no-qa-verdict",
                                "mergeable-but-open", "steward-ineffective",
                                "qa-fail-unaddressed", "qa-fail-refixed",
                                "draft-held-by-qa-fail"}
               and x.get("agent_pushable", True)]
    print(f"OBLIGED_ACTIONS={len(obliged)}")

    if not stalls:
        # Say it explicitly. A detector that prints nothing when it finds
        # nothing is indistinguishable from one that did not run.
        print("PASS — no stall detected. Checked: drafts never readied, "
              "mergeable-but-open, PRs with no checks, missing QA verdicts, "
              "dead trigger legs, and stalls no agent can clear.")
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
