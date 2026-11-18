# Every dispatch goes through the inbox; agent-queue's drain is the only worker, with an hourly backstop, liveness findings and timers

- **Date:** 2026-11-17
- **PR / issue:** #1185, #1186, #1187 (design #1184). Supersedes the "busy dispatches only" and
  "no `*/30` cron backstop" parts of the 2026-11-02 queue row in `ARCHITECTURE.md` §10.

## Why, measured

The owner, 2026-11-17: *"go ahead and build the workflow parts of 1185 and 1186"*, then *"and 1187
and 1188 as well"* (#1188, the outbox, is built separately).

- **Events lived inside the run that carried them.** `dispatch_cycle.sh` wrote a durable queue
  entry only when a lane was busy; on an idle lane it started `agent-work` straight from the
  handler's own run. GitHub keeps one pending run per concurrency group, and on 2026-11-17 it
  cancelled qa-on-green runs 44059296498 and 44059273106: #1165, then #1171, got no QA round.
- **The queue's drop logic discarded valid fixes twice** (#1092, #1165), and four PRs with a QA
  PASS on their head then sat about a day with red gates and no fix (#1121, #1127, #1136, #1138).
  The owner found every one of these by hand. Nothing in the loop asked whether an event finished.
- **Follow-ups were prose.** The analyst's "pending — scoreable from <date>" had nothing to fire it.

## What was decided

1. **Handlers only append.** `dispatch_cycle.sh` defaults to queue mode: validate, append an entry
   keyed (kind, target, head), wake `agent-queue.yml`, exit. Only `cycle_queue.py drain` sets
   `CYCLE_CARRIER=drain`, and only then does the script reach `gh workflow run agent-work.yml`.
   This converts every dispatch path at once (qa-on-green green and red, `red_gates.py`,
   `pr_fix_after_qa.py`, the steward, chief), because they all share the carrier.
   `tests/test_inbox_single_worker.py` greps scripts and workflows for any other dispatch.
   The chain step (`chain_cycle.py`, a ranked cycle with no target) stays in `agent-queue` beside
   the drain: it is the same worker, and it already runs only after the queue has had its turn.
2. **`workflow_dispatch` with `github.token` starts `agent-queue.yml`.** Measured, not assumed: 159
   `workflow_dispatch` runs of `agent-queue.yml`, every one with actor and triggering actor
   `github-actions[bot]`, the latest 44135868635 at 2026-11-17T17:20Z (from agent-work's #826
   wake step). It is GitHub's documented exception to the GITHUB_TOKEN recursion guard, which
   `agent-merge.yml` and `agent-work.yml` already rely on.
3. **Fold, with a fix outranking a QA request.** When the drain starts an entry, every other
   pending entry for the same target is marked `folded into run <id>`. Same target means the same
   PR (a `pr`/`fix_pr` entry, or an `issue` entry qa-on-green or red_gates wrote on that PR), or
   the same issue. A `fix_pr` or `issue` cycle pushes; the push is a new head; qa-on-green gives a
   new head its own round. A round on the pre-fix head would judge code that is about to change,
   so it is the round that folds into the fix, never the reverse. A target whose fix lane is busy
   waits whole. An `issue` entry written on the issue itself is not folded into a PR by guessing.
   The known cost: a fix that pushes nothing leaves the folded round's head un-reviewed; the head
   is red anyway, so agent-merge would not merge it, and `red-unhandled` raises it.
4. **A cancelled or duplicate drain is harmless.** Every drain re-reads the queue. A drain killed
   between claim and dispatch leaves a `claimed` entry; once it is older than `CLAIM_TTL` (20 min,
   above the job's 15-minute timeout) the next drain marks it `taken` if a matching run appeared
   within five minutes of the claim, else returns it to pending.
5. **Hourly backstop.** `agent-queue.yml` gains `schedule: "17 * * * *"`: fire timers, drain,
   chain, liveness. The old "no cron" reasoning was cost (~1,400 of 2,000 minutes a month); since
   the repo went public `measurements/cost.json` records Actions as unlimited (#338), and an
   hourly run that finds nothing is about a minute, at most 744 runs a month. No model runs in it.
6. **Liveness** (`scripts/liveness.py`, API reads only) raises `inbox-stale` (an entry with no end
   after 6h), `ready-unmerged` (green gates, a trusted `QA: PASS` naming the head, no `qa-fail`, no
   hold or `chief-cleared` at that head, open 6h after the PASS) and `red-unhandled` (the latest
   gate run on the head failed over 2h ago and no live queue entry is fixing it). A `fix
   dispatched at <head>` marker alone does not count as handled: the 2026-11-16/17 PRs had exactly
   that marker over a dropped entry. A `red gates noted at <head>` comment does count, because
   `red_gates.py` has routed that head to a session by design. Filed by `file_ops_findings.py
   --scope liveness`. The filer clears every open kind a run did not raise, so the steward's run
   and this one now own disjoint kinds.
7. **Timers** (`scripts/timers.py`): a hidden `<!-- agent-timer: key= due= kind=followup|schedule
   every= target=issue|pr:<n> action=<kind>:<n> -->` comment by `github-actions[bot]` (the queue's
   trust rule). `fire` runs hourly before the drain and appends an entry keyed
   `timer.<key>.<due>`; the queue dedupes a keyed entry in every state, so a double fire adds
   nothing. Timers are found through the search API (it indexes hidden markers in comments:
   `"agent-work-queue-taken" in:comments` found 5 issues and 30 PRs on 2026-11-17) plus the last
   week's comments, not by reading ~60 pages of comments an hour. `set` refuses a due time more
   than 55 days out, so every live timer stays inside the search window.
8. **The analyst's pending note becomes a timer** whose action is a new queue kind, `measure`. One
   analyst run scores every issue, so all `measure` entries fold into one run, and the drain starts
   none when an analyst run (the `measure` job, on a `schedule` or `workflow_dispatch` run) has
   already started since the due time. It waits 4h past due for the daily slot first. So in the
   usual case a timer costs no Claude at all, and it costs one analyst run when the slot was missed.
   This needed `allowed_bots: "github-actions"` on agent-measure's action, because a drain-
   dispatched run is a Bot actor (#421).

## Rejected

- **Removing the handlers' concurrency groups now.** The design says handlers hold none. Open PR
  #1171 edits qa-on-green's concurrency, and a cancelled handler run now costs nothing once its
  entry is written, so it is left for that PR.
- **A GCS inbox.** It needs a write-capable service account and `id-token: write` on every handler,
  which is owner act #3. Comments need no new permission. This stays the upgrade path if two
  consumers ever share a lane.
- **A per-PR run lookup in liveness.** One page each of the gate workflows' runs, matched by
  `head_sha`, replaces about 30 calls an hour against the 1,000-request GITHUB_TOKEN budget.
- **A post-deploy re-check timer.** `agent-merge` already dispatches `verify-production` on every
  merge, and `close-on-evidence` closes only on a `/health` `build_sha` equal to the commit. That
  field is null until the owner sets `BUILD_SHA` on the Cloud Build trigger, so a re-check would
  close nothing today. Left until `build_sha` is live; `timers.py` can carry it then without
  changes, as a new queue kind.

## Cost

0 Groq tokens: no app LLM path is touched. Claude: none in the queue, timers or liveness. A `measure`
timer costs one analyst run only when the daily slot did not run after its due time. Actions: at
most 744 hourly runs a month on a public repo.

## Amendment 2026-11-18: the hourly steps no longer wait on GitHub's cron

Measured on the first day: the `17 * * * *` schedule, merged 02:14 UTC, fired once
(10:15 UTC) and not again through 17:38, so timers and liveness ran once in fifteen
slots. GitHub documents scheduled runs as best-effort, delayed or dropped under load.
Every agent-queue run now asks `scripts/hourly_due.py`: a scheduled run is due, and
any other wake is due when no run in the last 55 minutes completed the timers step.
Event wakes are far more frequent than hourly, so they hold the cadence and the cron
is a fallback. Both steps are idempotent, so an unreadable API answers "due".
Rejected: a repository variable as the "last ran" clock (`GITHUB_TOKEN` cannot write
variables, and adding that scope is the owner's act #3).
