# A dispatched agent-work run wakes agent-queue itself

- **Date:** 2026-11-10
- **PR / issue:** #826

## Why, measured

`agent-queue` drains the queue and chains the next build cycle when an `agent-work` run
completes, using `workflow_run`. Measured 2026-11-08..10, it ran after **8 of 8 scheduled
cycles** and **0 of 26 dispatched ones** (chained cycles and QA rounds).

GitHub stops `workflow_run` chains after three levels. Each link of the chain:
- a cron cycle (level 1) wakes `agent-queue` (level 2);
- `agent-queue` dispatches the next cycle (level 3);
- that cycle's completion would wake `agent-queue` at level 4, which is dropped silently.

So each cron firing bought one cycle plus one chained cycle. The lane then waited for the next
cron, and GitHub fires those irregularly, up to 8.5h apart. On 2026-11-10 the 11:12 chained cycle
shipped #845 and nothing ran for 3h+ afterwards, with about 74 eligible issues open. The same gap
stranded queued QA rulings for #804 and #810 (#826).

**Decision:**
- A dispatched `agent-work` run ends with one best-effort step that dispatches `agent-queue.yml`
  with `after_run=<its run id>`. `workflow_dispatch` has no depth limit; `agent-merge`
  re-dispatches itself in a chain daily.
- A scheduled run does not do this, because it is still woken by `workflow_run`.
- `agent-queue`, when started this way, runs `scripts/wait_for_run.py` first. The script:
  - waits up to 10 minutes for that run to complete, because draining while it still runs would
    see it as a busy lane, which is the trap `agent-queue.yml`'s header records;
  - refuses a run of any other workflow;
  - passes the same four facts as the `workflow_run` payload to the existing drain and chain
    steps.
- Every chain guard is unchanged: the 70% weekly-quota ceiling, 16 build runs a day, no chain
  after a cycle that produced nothing, and drain-before-chain.
- No permission changes. `agent-work` already holds `actions: write` for its `pr-gates`
  dispatch.

**Known limit.** `agent-queue`'s concurrency group keeps one pending run. If two wakes and a
steward completion land while a drain is running, the third cancels the pending one. That drops
the chain off that one run, and the next completion or the steward re-reads the state.

**Rejected:**
- **A `*/30` cron on `agent-queue`.** Roughly 1,400 Actions minutes a month, already rejected in
  its header.
- **Dispatching with the publisher App token to reset the depth.** It is unverified that the App
  holds `actions: write`, and it would add a secret to two more workflows.
- **Draining from inside the running cycle.** It dispatches into the cancellable pending slot.
