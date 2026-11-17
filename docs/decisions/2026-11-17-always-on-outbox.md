# The outbox: one deduped, capped, retried posting path, its ledger in hidden markers, its evals on /admin/ops

- **Date:** 2026-11-17
- **PR / issue:** #1188 (slice 4 of #1184)

## Why, measured

Every script posted comments and issues on its own, each with an anti-noise rule written
after its own incident (#311, #276 and #329 each collected 20+ near-identical comments).
Nothing retried, nothing recorded a delivery, and nothing measured how noisy the loop is.

First reading of the evals (`scripts/collect_outbox.py`, run read-only against the repo,
2026-11-17 18:25Z):

| window | loop comments | per PR | per issue | duplicate rate | owner commented on |
| --- | --- | --- | --- | --- | --- |
| 11-10 → 11-17 | 1,268 (732 on 138 PRs, 536 on 152 issues) | 5.3 | 3.53 | 4.3% (55) | 6 of 138 PRs (4%) |
| 11-03 → 11-10 | 776 (453 on 77 PRs, 323 on 75 issues) | 5.88 | 4.31 | 4.0% (31) | 9 of 79 PRs (11%) |

Busiest threads this week: PR #1058 (22), #1132 (21), #1000, #1002, #1169 (15 each). That
is the baseline #1188's metric asks for. `outbox-noise` does not fire on it (4.0% → 4.3%,
5.88 → 5.3 per PR).

## What was chosen

- **`scripts/outbox.py`** (library and CLI). Dedupe key = (target, kind, sha256 of the body
  with SHAs, timestamps and run ids normalised), checked against this run's ledger and the
  target's comments by this identity within a per-kind window. A rolling-24h cap per
  (target, kind). A kind not in `KINDS` starts at `QUIET_CAP` = 1. Retry with backoff
  (10s, 60s) on 5xx, 429 and the secondary rate limit, never on another 4xx; the target is
  re-read before a resend, because a 502 can still have created the comment.
- **`KINDS`** at landing: `ops-finding` cap 2/day, `dedupe: last` (a state carrier: A,
  cleared, A must all be said); `ops-finding-issue` cap 5/day on the repository;
  `triage-stage1` cap 2, 30-day window; `provenance-unresolved` cap 1.
- **Migrated:** `file_ops_findings.py`, `triage_outsider_issues.py`,
  `resolve_provenance.py`. Each keeps its own "only on change" rule; the outbox is the
  second line, and each keeps the wire it used: REST `gh api` for `file_ops_findings.py`
  (the default), `gh issue comment` / `gh issue view` porcelain for triage (whose write
  surface #367 pins) and `resolve_provenance.py`. Porcelain is GraphQL, which a Claude Code
  web session's proxy refuses (HTTP 403, measured while building this); Actions is not
  behind it. `tests/test_outbox.py` fails if any other script under `scripts/` posts a
  comment or files an issue without it, with an explicit allow-list.
- **Not migrated, on purpose:** `qa_verdict.sh`. Its comment is SHA-bound and is
  `agent-merge`'s merge trigger; the outbox normalises SHAs and would dedupe a PASS at a new
  head against the PASS at the old one. `cycle_queue.py`, `pr_fix_after_qa.py` and the other
  #1185-#1187 files are being changed in parallel and are allow-listed until that lands.
  `ask_audit_post.py` (#1167) landed on `main` while this was built; it posts only a
  leak-guarded body file and is allow-listed until a follow-up migrates it.
  Agents posting with `gh` directly from `.claude/` prose are a later step.

## Where the ledger lands, and the alternatives

Posters run in many jobs under several tokens; only agent-measure's commit job writes
`measurements/`. Options weighed:

1. **Hidden markers on the posted text, collected from comments — chosen.** Each message
   ends `<!-- outbox: kind=… key=… -->`. A refused or failed attempt is tallied onto the
   newest same-kind comment this identity already has on the target (an edit: it notifies
   nobody and needs only the scope the poster holds). `collect_outbox.py` reads the repo's
   recent comments and writes `measurements/outbox.json`. No new permission, job or secret.
2. A GCS blob with `storage.update_json` CAS: the upgrade path #1184 names; it needs a
   write-capable service account and `id-token: write` on every poster (owner act #3).
3. Per-run ledger artifacts collected from job logs: needs a step in every poster workflow
   and a log download per run (agent-work's logs are large); rejected for cost.

**The collector runs from `collect_lessons.py`**, not as a new step: that step already holds
`issues: read` in agent-measure's commit job, and running there needs no workflow edit,
so the PR is not held at the trust boundary and the loop can maintain it. It runs before the
lessons step's detector call, so `outbox-noise` judges the fresh file. The cost is a hidden
coupling, stated in both scripts' headers.

**The evals read every loop comment, not just the outbox's**, so a quiet number means the
loop is quiet rather than "the three migrated scripts are quiet".

## What it cannot see, stated rather than reported as zero

- A failed post with no earlier same-kind comment to tally onto: only that run's log line.
- A refused issue CREATE: issue bodies are not edited, so those are in the run log only.
- Tallies are cumulative per comment, read from comments updated in the window: an upper
  bound for the window, and not split for the previous window.
- Two concurrent tallies on one comment can lose an increment (read-modify-write).
- "Owner commented" counts PR conversation comments only; review comments are not read,
  and commits and merges are already in the Delivery panel's "you helped".
- A tally edit moves the comment's `updated_at`, so collectors that window comments by
  `since=` without a `created_at` filter (`collect_agent_performance.py`) can count an old
  outbox comment again in the week it was tallied. Small while suppressions are rare; worth
  a `created_at` filter there if the tallies grow.

## The finding

`detect_ops_regressions.py` raises `outbox-noise` (amber) when the duplicate rate or
comments per PR rises more than 50% over the previous 7 days, with at least 30 loop
comments in each window and 5 PRs for the per-PR figure; a duplicate rate rising from 0
fires only at 3% or more. A collection truncated by its page cap is `unreadable`, never a
rise. The lever it names is routing the poster through the outbox, never raising a cap.

**Tokens:** 0. No LLM call anywhere on this path.
