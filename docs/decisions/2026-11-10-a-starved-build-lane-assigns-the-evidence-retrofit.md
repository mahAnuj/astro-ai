# A starved build lane assigns the Evidence Block retrofit to project-manager

- **Date:** 2026-11-10
- **PR / issue:** this PR

## Why, measured

On 2026-11-10, 112 issues were open and `verify_issue_evidence.py` failed 63 of them (34 more
were exempt by date, 15 passed). The two build cycles that day (runs 42740481767 and
42759567954) both built nothing. The ranker's own report said every ranked item that was wrong
in front of users (#581, #596, #714–#716, #777, #751) failed the gate, and it listed "retrofit
the Evidence Blocks" as its second item. Nobody acted on that. The cycle refuses to write its
own eligibility, on purpose. `project-manager` is read-only inside a cycle. `chain_cycle.py`
correctly declined to chain, and that left the lane idle until the next cron.

Decision:
- `chain_cycle.py` dispatches `agent-prioritise.yml` with `mode=evidence` when a build cycle
  produces nothing and the build run before it did too, at most once per 6h, never while a
  retrofit runs, and never on an unread or exhausted quota.
- In that mode, `scripts/evidence_backlog.py` lists the refused issues in harm order, and
  project-manager measures each one. It closes the issue under the existing four-kind grant, or
  posts an Evidence Block and confirms the checker exits 0, or labels it `needs-evidence`. It
  takes at most 15 per run.
- `detect_ops_regressions.py` raises `loop-starved` so /admin/ops shows the state.

Why project-manager, and not the cycle: the cycle writing the block it is then judged on is
grading its own eligibility. Project-manager in `/prioritise` already holds `issues: write`
and the close grant. No permission is widened: `agent-queue.yml` already holds `actions: write`
for the chain.

Rejected:
- **Relaxing the gate for bugs.** The gate exists so an engineer never starts on a guess.
- **A new workflow.** It would need a new `permissions:` block, which
  `verify_workflow_permissions.py` reads as a widening.
