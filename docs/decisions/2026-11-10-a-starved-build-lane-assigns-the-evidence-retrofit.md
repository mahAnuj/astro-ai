# Issues locked out by the Evidence Block gate get a retrofit, assigned to project-manager

- **Date:** 2026-11-10
- **PR / issue:** #841

## Why, measured

**The problem.** On 2026-11-10, 112 issues were open and `verify_issue_evidence.py` failed 63
of them (34 more were exempt by date, 15 passed). Those 63 included every wrong-in-front-of-users
finding the auditors had filed (#581, #596, #714–#716, #777, #751).
- The cycle refuses those issues at Step 1, and it refuses to write its own eligibility, on
  purpose.
- `project-manager` named "retrofit the Evidence Blocks" as its second item on every ranking.
  It is read-only inside a cycle, so nothing happened.
- The build runs that day went: 01:53 moved #833, 02:06 nothing, 04:30 opened #839, 05:02
  nothing. The empty cycles alternated with the one item every cycle circled.

**What the first version got wrong.** It triggered on "two empty build cycles in a row" and
failed QA on #841 for three reasons:
- That pattern never occurred.
- `agent-queue` ran after 8 of 8 scheduled cycles and after 0 of 26 dispatched ones, so the
  chained cycles were never judged at all.
- `produced_something()` counted measurement PRs and PRs merged mid-window as cycle output. It
  also wrongly said `chain_cycle.py` had "declined to chain" those two runs; it never ran after
  them.

**The decision.** Trigger on the cause, not on cycle outcomes.
- On every `agent-queue` run that does not chain, `chain_cycle.py` counts the refused issues
  (`scripts/evidence_backlog.py`). The steward's completion reliably triggers that run.
- At 3 or more refused issues, it dispatches `agent-prioritise.yml` with `mode=evidence`. It
  does so at most once per 6h, never while a retrofit runs, and never on an unread or exhausted
  quota. The cooldown is checked before the count, so the ~100 issue reads happen once per
  window at most.
- In that mode, project-manager measures each refused issue, up to 15 per run, and does one of
  three things:
  - closes it under the existing four-kind grant;
  - posts an Evidence Block and confirms the checker exits 0;
  - labels it `needs-evidence`.
- Issues labelled `provenance:outsider` are skipped; they are triaged elsewhere first.
- `produced_something()` now counts only a PR opened in the window, or an older PR whose head
  commit landed in it, and never a `measurements/` PR.
- `detect_ops_regressions.py` raises `loop-starved` when 2 of the last 4 build cycles built
  nothing. That rule fires on the 11-10 pattern.

**Why project-manager, not the cycle.** The cycle writing the block it is then judged on would
be grading its own eligibility. Project-manager in `/prioritise` already holds `issues: write`
and the close grant. No permission is widened: `agent-queue.yml` already holds
`actions: write`.

**Rejected:**
- **Relaxing the gate for bugs.** The gate exists so an engineer never starts on a guess.
- **A new workflow.** It would need a new `permissions:` block, which
  `verify_workflow_permissions.py` reads as a widening.
- **Fixing the dispatched-cycle `workflow_run` gap (#826) here.** That gap is separate. This
  design no longer depends on it.
