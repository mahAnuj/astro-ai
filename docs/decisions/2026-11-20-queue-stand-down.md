# The queue does not drain a PR that is only waiting for its gates, and does not retry a green run that wrote nothing

- **Date:** 2026-11-20
- **PR / issue:** #1207

## Why, measured

`agent-queue` failed on four runs on 2026-11-17 (steward's count in #1207), each
at "Start the oldest queued cycle". The queue drained an entry for a target whose work was
already done, the new `agent-work` cycle stood down in about a minute and wrote no comment, and
`scripts/dispatch_cycle.sh` read a quick `success` with no `claude[bot]` comment as #421's
died-on-arrival (exit 1). `cycle_queue.drain()` then requeued it, up to three cycles.

| agent-queue run | agent-work run it dispatched | target | what the target was doing |
| --- | --- | --- | --- |
| 44168143200 | 44168205976 | issue #1176 | PR #1197 merged 20:29Z |
| 44197966449, 44198225538, 44198512363 | 44198047810, 44198312083, 44198606840 | issue #1163 | PR #1199 `qa-pass`, merged 14 minutes after the drain |
| not read | 44395548615 (2026-11-18, `workflow_dispatch`) | issue #1226 | PR #1227 `qa-pass`, `blocked` while a second `gates` run was in progress; run `success`, 20:52:23Z to 20:54:04Z |

`_mergeable_passed_pr` treated only `mergeable_state` `clean` / `has_hooks` as "waiting to
merge". GitHub reports `blocked` both for a PR whose required check is red and for one whose
required check is still running, so the second kind started a cycle with nothing to do.

## Decided

1. **Waiting = a `QA: PASS` bound to the current head, `mergeable_state` `blocked`, and the
   latest run of EACH required gates workflow on that head not red** (running, queued, or
   `success`). The required workflows are `PR gates` (check `gates`) and `verify-build` (check
   `build-gates`), the same pair `scripts/collect_gate_failures.py` counts. `_gates_red` reads
   them through `repos/{repo}/actions/runs?head_sha=<sha>&event=pull_request`, takes each
   workflow's newest run by `[created_at, id]` (a same-second tie otherwise picks the older), and
   answers True if either is red, False only when both are present and not red. Anything else
   starts the cycle: a red or cancelled run in either workflow, a MISSING run of either (neither
   workflow is path-filtered, so absence is a run not yet created, not "not needed"; a test pins
   that `verify-build` has no `paths:`), a skipped run, an unreadable answer, `dirty`, `behind`,
   `unknown` and `unstable`, because a wasted stand-down costs a minute and a wrongly dropped
   entry is permanent. `GATES_WORKFLOW` and `BUILD_WORKFLOW` are pinned to their files' `name:`.
   QA on PR #1271 found the first version read `PR gates` only, which would drop a PR whose
   `verify-build` is red, the #1165 shape.
2. **A carrier failure that says the run `concluded 'success'` is dropped, not retried.**
   A green run that wrote nothing repeats itself on the same state. It still turns the drain
   red once, so the stand-down is seen. A `concluded 'failure'` run keeps its two retries.

## Rejected

- **Option 2 as worded in the issue: skip a target that already carries a `claude[bot]` comment
  newer than the entry's marker.** `claude[bot]` is also the steward, chief and the analyst, and
  a comment can describe an older head, so it is not proof the work for this head is done.
- **Drop any `qa-pass` + `blocked` entry without reading the gates run.** That is #1165
  again: PRs #1121, #1127, #1136 and #1138 went red on a head that held a PASS, and their
  red-gates fixes were dropped as "waiting to merge".
- **`commits/<sha>/check-runs` for the gates state.** It needs a `checks` scope that
  `agent-queue` does not hold; the Actions API is what `scripts/collect_gate_failures.py` already
  uses.
- **Make `dispatch_cycle.sh` accept a quick `success` without a trace.** That reverses the
  2026-11-08 rule that a quick success counts only when it left a trace, which exists to keep
  #421's shape caught. A policy call for `chief` or the owner, not a side effect of this fix.
- **Make the stand-down exit green so the queue stays quiet.** It loses the #421 visibility the
  red run provides.
- **Post the trace comment from a workflow step.** It needs an edit under
  `.github/workflows/`, which the App token cannot author (#421).

## Not done here

The other repair the issue names, a one-line trace comment on every stand-down in
`.claude/commands/agent-cycle.md`, is a separate step: the permission system refused the write
to that file while this was built, so it remains open. With the queue-side repair a stand-down
for a target that is only waiting is no longer drained; a cycle that does stand down still leaves
no trace until that bullet lands.
