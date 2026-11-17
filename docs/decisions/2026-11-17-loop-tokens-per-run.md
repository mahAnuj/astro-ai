# loop.json records Claude tokens per run, read from the result object the action already logs

- **Date:** 2026-11-17
- **PR / issue:** owner request, 2026-11-17 ("Measure tokens per cycle. The usage numbers are
  already in every run's log but aren't collected.")

## Why, measured

claude-code-action ends every run's log with a pretty-printed `"type": "result"` object. On
agent-work run 44020807802 (job 133837665489) its `model_usage_since_last_result` reads 305
input, 103,720 output, 13,174,859 cache-read and 542,749 cache-write tokens, costUSD $3.8793
(list price) over 26 turns. That costUSD equals the object's `total_cost_usd`, so this key is
the session total including subagents. The same object's top-level `usage` (2,293,717
cache-read) covers the main agent only. Every `assistant` message carries its own per-call
`usage`, and every subagent `task_progress` carries a running `usage.total_tokens`. Summing
any of those would double-count. Across the 40 most recent runs, `modelUsage` equalled
`model_usage_since_last_result` 40 times out of 40, and each object parsed. An older object
(run 41574673500, 2026-11-03) carries only `modelUsage`. Its costUSD, $3.7298, equals its
`total_cost_usd`.

Decision: `collect_loop_measurements.parse_usage` reads only top-level result objects. It sums
`model_usage_since_last_result` across them, counting one `uuid` once, so a resumed session's
segments add up. It falls back to `modelUsage` only when the run has a single result object.
It returns None, never 0, if any object is unreadable. When the runner has damaged the JSON
(a masked `***` or an `##[endgroup]` inside a tool result, which broke 12 non-result objects
in those 40 runs), the usage sub-object is cut out by indentation. The fields come from the
log fetch the receipt already uses, so a run costs no extra request. A snapshot without the
new `tokens` block is backfilled once. Measured locally against the live repo, that read 308
listed runs in 6m57s, and later collections read nothing extra.

`tokens.per_merged_pr` is every measured run's tokens in the 7-day window, including QA
rounds and empty cycles, divided by the distinct PRs that merged in it. The cost of a shipped
fix includes the cycles that produced nothing. First reading (collected 2026-11-17T07:12Z):
9.59M tokens per merged PR (101 PRs, 179/179 runs measured), against 11.75M the week before
(49 PRs, 127/130 measured). Median 6.48M per build cycle and 1.34M per QA round. 969M tokens
and $309.35 list price in the window. Runs older than the 14-day listing window are not
re-listed, so they stay unmeasured. `/admin/ops` shows these under "Claude tokens per shipped fix". The detector
raises `cycle-tokens` when per-merged-PR rises more than 50% over the previous window, with
at least 3 merged PRs and 80% of runs measured in both windows.

Rejected: summing per-message `usage` (main agent only, misses subagents); reading
`total_cost_usd` alone (a dollar figure at list price, while the Max subscription is a flat
fee, so it says nothing about the weekly quota); re-reading every unmeasured row on every
collection (a run that died before Claude finished would be fetched forever).

Not verified: no real log in the 40 sampled had more than one result object. The summing
rule follows the key's name ("since last result"), and `num_turns` is summed on the same
assumption. Tokens: 0 Groq. This is a deterministic parser with no LLM path.
