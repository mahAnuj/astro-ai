# A dispatched `main` gates run reports through a dispatched reporter, and a run that never started is not a red main

- **Date:** 2026-11-26
- **PR / issue:** #1480 (the route), #1221; the rule for never-started runs and the server clock: #1284, #1486, #1487, #1488

## Why, measured

**The route (#1480, #1221):**
- `agent-merge` merges with `GITHUB_TOKEN`, whose push starts nothing, so after a merge it dispatches `pr-gates` on `main`.
- GitHub delivered that run's `workflow_run` to `main-red-report` for 1 of 20 such runs (steward, 2026-11-18). The chain sits past the three-level limit #826 hit.
- So `agent-merge` also dispatches `main-red-report` with `after=<time>`, which has no depth limit. `scripts/await_main_gates.py` finds the oldest dispatched `main` run created at or after `after`, waits for it, and hands the existing reporter step the four facts the `workflow_run` payload carries.
- **Rejected:**
  - **Reporting from inside `pr-gates`:** a cancelled or timed-out job cannot report itself (#461 finding 1).
  - **Widening `pr-gates`' permissions:** `verify_workflow_permissions.py` refuses it.

**Which cancelled runs count (#1284, #1486):**
- GitHub keeps one pending run per concurrency group and cancels the older one when a newer one queues. That run concludes `cancelled` with no step executed, and four false `[main-red]` issues (#1146, #1191, #1249, #1274) were filed on runs of that shape.
- The rule, in both the reporter and `await_main_gates.py`: **a `cancelled` run whose job list was read and has no step at all is not reported.**
- The first version (#1480) said "a newer run exists". That also swallowed a run that timed out with the next merge's run queued behind it, which is the case #461 exists for (#1486). A timed-out run has steps.
- An unreadable job list reports, never swallows.

**Whose clock (#1487):** `after` is GitHub's clock (the `Date` header of a `rate_limit` call), compared with the run's server-side `created_at`. With the runner's clock, a few seconds of skew either missed the run (5 minutes later, exit 1) or adopted the previous merge's run. The runner clock is used only when the header cannot be read.
