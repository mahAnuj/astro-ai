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

#: WIDENED TO THE WHOLE BOUNDARY -- granted by the user 2026-11-01 (#610).
#:
#: The user's words, verbatim: "do not hold chief for TRUST_BOUNDARY as well.
#: I want the loop to not hold on me".
#:
#: It was `("src/astro_ai/prompts/", "src/astro_ai/knowledge/")` -- chief.md's
#: Shape C -- with this reasoning: "The other five are not decidable by an
#: agent for blast radius, not seniority: a workflow edit can grant the loop
#: powers, and email/notify reach real people." That reasoning is recorded
#: rather than deleted, because it is the argument against this grant and the
#: user has overridden it knowingly.
#:
#: WHY THIS CONSTANT AND NOT JUST `agent-merge`. Honouring `chief-cleared` at
#: the merge gate is necessary and NOT sufficient: nothing would ever ASK chief
#: to rule. This tuple is what decides whether a boundary hold is reported
#: `boundary-hold-clearable` (the steward dispatches chief) or
#: a `human-only` kind that said "A HUMAN decides this one", so leaving it
#: narrow would route every workflow, notify and email PR to the owner and the
#: loop would still hold on them -- which is the thing being fixed. That arm is
#: gone entirely since the 2026-11-01 grant; see the `needs-human-review`
#: branch below.
#:
#: One real limit survives and no grant can move it: the App token has no
#: `workflows` permission (#421), so chief can MERGE a `.github/workflows/` PR
#: a human or a session pushed and still cannot author one.
CHIEF_DECIDABLE = BOUNDARY


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


def post_verdict_commits(pr: int, fail_age: float) -> tuple[int, int] | None:
    """`(non_merge, merge)` counts for commits newer than the verdict.

    WHY THIS EXISTS: "the head is newer than the verdict" is NOT "the findings
    were fixed", and `qa-fail-refixed` used to assert the second from the first.
    Measured 2026-10-20 on PRs #418 and #419: the only commits after their
    verdicts were `Merge origin/main` clearing a conflict, so both were routed as
    refixed, and the routed comment would have told a QA round that the fix had
    landed. A round on unaddressed findings returns the same FAIL at full cost.

    Merge-ness comes from the PARENT COUNT via the commits API, not from a
    headline starting with "Merge" -- a commit can say anything. Returns None
    when the parents cannot be read, so the caller hedges instead of guessing.
    """
    try:
        out = json.loads(gh("pr", "view", str(pr), "--repo", REPO, "--json", "commits"))
    except RuntimeError:
        return None
    newer = [c for c in (out.get("commits") or [])
             if (age_hours(c.get("committedDate") or "") or 0) < fail_age]
    if not newer:
        return (0, 0)
    merge = non_merge = 0
    for c in newer:
        sha = c.get("oid")
        if not sha:
            return None
        try:
            meta = json.loads(gh("api", f"repos/{REPO}/commits/{sha}",
                                 "--jq", "{parents: (.parents | length)}"))
        except RuntimeError:
            return None
        if int(meta.get("parents", 1)) > 1:
            merge += 1
        else:
            non_merge += 1
    return (non_merge, merge)


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
        #
        # ALL THREE CYCLE NAMESPACES, not just `issue/` -- fixed 2026-10-25.
        # Every routed action in steward.md's table is "dispatch a cycle at the
        # owning issue", so a `None` here is not a missing field, it is a stall
        # the steward can SEE and cannot ACT on. Measured the day this changed:
        # #521 and #524 sat `no-qa-verdict` for 21h with green gates and no
        # verdict either way, the steward ran at least three times against
        # both, cleared neither, and `steward-ineffective` escalated both to
        # chief -- which would have ruled the same un-dispatchable answer on
        # every run. The PRs were not held by any judgment; their branches were
        # called `partial/` and this regex returned nothing.
        #
        # NOT `^[a-z]+/(\d+)`: that matches `measurements/40140256532-1` and
        # yields issue 40140256532, so a measurement PR open long enough to be
        # judged stalled would route a dispatch at an issue that does not
        # exist. The namespaces are enumerated because only these three carry
        # an issue number by construction (agent-cycle.md Step 4).
        m = re.match(r"^(?:issue|partial|fix)/(\d+)", pr["headRefName"] or "")
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
            # `needs-human-review` MEANS "CHIEF DECIDES" -- user, 2026-11-01.
            #
            # Their words, verbatim: "anything that is labeled as
            # needs-human-review, should be decided by chief".
            #
            # So the label's MEANING changed, not its mechanism. It still holds
            # the merge -- there has to be something to decide -- but the
            # decision is routed to chief instead of to the owner. The label
            # keeps its name deliberately: it is spelled in `agent-merge.yml`'s
            # sweep filter, its `QA verdict` step, `agent-work.yml`,
            # `steward.md`, `chief.md`, `README.md` and here, and this repo has
            # already paid for one rule living in six places (the `issue/*`
            # branch-name coupling, 2026-10-25). Renaming it is a separate
            # change from granting the authority.
            #
            # THERE IS NO LONGER A `human-only` ARM. It was reached when a
            # boundary path fell outside chief's Shape C, and before that when
            # `CHIEF_DECIDABLE` was prompts/ and knowledge/ only. Both of those
            # routed work to one person, which is what #610 and this grant
            # exist to stop. `kind` keeps the name `boundary-hold-clearable`
            # for the same reason the label does -- `steward.md` and
            # `agent-steward.yml` both match on it.
            #
            # WHAT WAS GIVEN UP, recorded rather than deleted, because it is
            # the argument against this grant: "The other five are not
            # decidable by an agent for blast radius, not seniority: a workflow
            # edit can grant the loop powers, and email/notify reach real
            # people." The owner has overridden that knowingly.
            #
            # An UNREADABLE diff still routes to chief rather than to the
            # owner. `boundary_paths` returns an empty set on any failure, and
            # chief's documented `insufficient-evidence` return is the right
            # answer to a diff it cannot read -- recorded as a ruling comment,
            # which is what keeps it auditable and stops it being re-decided
            # silently every sweep.
            bpaths = boundary_paths(n)
            stalls.append(dict(
                kind="boundary-hold-clearable",
                pr=n, issue=issue, age_h=round(age, 1),
                detail=(f"needs-human-review for {age:.0f}h with qa-pass and green gates; "
                        f"CHIEF decides this one (user grant 2026-11-01) — it touches "
                        f"{', '.join(sorted(bpaths)) or 'paths that could not be read'}. "
                        f"A ruling comment naming the head SHA plus `chief-cleared` "
                        f"releases it; the clearance does not survive a push."),
                boundary_paths=sorted(bpaths),
                checks=checks, labels=sorted(labels),
                agent_pushable=pushable))
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
            if conflicting:
                # A CONFLICT IS WORK, NOT A DECISION, and routing it through
                # `no-checks-ever` made it an escalation. That kind is
                # deliberately absent from `obliged` -- it covers the
                # GITHUB_TOKEN case, which no agent can rescue -- so a
                # conflicting PR woke chief to rule on `git merge origin/main`.
                #
                # Measured 2026-10-20: #418 and #419 both sat CONFLICTING with
                # independent verdicts on them, and both were cleared by hand in
                # minutes. `scripts/merge_main_into_branch.py` does the three
                # resolutions this repo produces mechanically and REFUSES
                # anything else, so the split is safe: a source-file conflict
                # still lands in front of a person.
                stalls.append(dict(
                    kind="pr-conflicting", pr=n, issue=issue, age_h=round(age, 1),
                    detail=(f"CONFLICTING for {age:.0f}h, so GitHub cannot build the merge ref "
                            f"and no check will ever run. Resolvable by "
                            f"scripts/merge_main_into_branch.py unless the conflict is in a "
                            f"source file, which it refuses."),
                    conflicting=True,
                    checks=checks, labels=sorted(labels), agent_pushable=pushable))
                continue
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
                # NEWER IS NOT FIXED. Ask what the new commits actually are.
                split = post_verdict_commits(n, fail_age)
                if split is None:
                    stalls.append(dict(
                        kind="qa-fail-refixed", pr=n, issue=issue, age_h=round(fail_age, 1),
                        detail=(f"qa-fail {fail_age:.0f}h ago, head pushed {head_age:.0f}h ago — "
                                f"something landed after the verdict but its commits could not be "
                                f"classified, so whether it is a FIX or a merge is unknown. Read "
                                f"them before saying either. Dispatch QA only if a fix is there."),
                        checks=checks, labels=sorted(labels), agent_pushable=pushable))
                elif split[0] == 0 and split[1] > 0:
                    stalls.append(dict(
                        kind="qa-fail-unaddressed", pr=n, issue=issue, age_h=round(fail_age, 1),
                        detail=(f"qa-fail {fail_age:.0f}h ago; the only {split[1]} commit(s) since "
                                f"are MERGES, so the findings are unaddressed — a merge forward is "
                                f"not a fix. Dispatch a cycle to fix them, NOT a QA round, which "
                                f"would return the same FAIL at full cost."),
                        checks=checks, labels=sorted(labels), agent_pushable=pushable))
                else:
                    stalls.append(dict(
                        kind="qa-fail-refixed", pr=n, issue=issue, age_h=round(fail_age, 1),
                        detail=(f"qa-fail {fail_age:.0f}h ago, head pushed {head_age:.0f}h ago — "
                                f"{split[0]} non-merge commit(s) landed after the verdict and no "
                                f"round has seen them. Dispatch QA."),
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
                         "draft-held-by-qa-fail", "pr-conflicting"}
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

    # A stall whose BRANCH no agent can update. Reported, but NOT as
    # `steward-ineffective`: the steward is not ineffective for declining work
    # it is structurally refused. Distinguishing these is chief's
    # recommendation 2 from the 2026-10-11 ruling, and it is what stops the
    # same un-pushable PR waking chief twice a day forever.
    #
    # WHAT IS AND IS NOT IRREDUCIBLE HERE -- narrowed 2026-11-01 (#610).
    # The App token is refused the `workflows` permission, so AUTHORING a
    # commit on such a branch is genuinely impossible for any agent. Nothing
    # else about these PRs is:
    #
    #   judging the diff   a QA round reads and labels; it pushes nothing, so
    #                      the refused permission never comes into it. The old
    #                      detail said "a human records the verdict", which was
    #                      never true -- `qa_verdict.sh` writes the label with
    #                      `github.token`.
    #   clearing the hold  chief's, since the user widened Shape C to the whole
    #                      boundary on 2026-11-01.
    #   merging            `agent-merge` merges with `github.token`, NOT the
    #                      App token, and that token carries `contents: write`.
    #
    # So this kind means one thing only: if the diff needs CHANGING, a human or
    # a Claude session has to push it. Saying more than that is what kept three
    # green PRs waiting on a person for a permission that was never in the way.
    for st in list(stalls):
        if st["kind"] in STEWARD_CLEARABLE and (st["age_h"] or 0) > 18 \
                and not st.get("agent_pushable", True):
            stalls.append(dict(
                kind="human-owned-stall", pr=st["pr"], issue=st["issue"],
                age_h=st["age_h"],
                detail=(f"PR #{st['pr']} has been `{st['kind']}` for {st['age_h']:.0f}h and "
                        "its diff touches `.github/workflows/**`, which the App's token is "
                        "refused on, so no agent can PUSH to this branch. That is the only "
                        "irreducible part. ROUTE TO CHIEF: a QA round can still judge the "
                        "diff and `qa_verdict.sh` can still label it, and chief clears the "
                        "boundary hold and lets `agent-merge` take it. Escalate to a human "
                        "only if the diff itself has to change."),
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
                                "draft-held-by-qa-fail", "pr-conflicting"}
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
