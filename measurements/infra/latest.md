# infra-lead report — 2026-11-18
Focus: free-tier headroom, deploy truth, latency.
Chief's row for infra: "not rated, not due, outputs not read", with no instruction. Nothing to follow or refuse.
No GCP change made, so no trigger export was needed. No issue filed: every finding below maps to #266, #212, #232 or #253, or is not actionable.

## Deploy truth: the `exact` tier still holds (measured this run)
- `/health` returned `{"ok":true,"revision":"bhagya-00783-xnq","build_sha":"c207ca3c46206a30709d1fa7970dcc0a8d40f338"}`.
- `gh api commits/c207ca3` is "subscribe: send the welcome email after the response ... (#1199)", committed 2026-11-17T23:30:15Z.
- `gh api compare c207ca3...main` shows main is 1 commit ahead. That commit is the sync report (#1201), which touches only `measurements/`, so it builds nothing. Production is therefore serving the newest deployable commit.
- `build_sha` is non-null, so the tier is live. I did not re-fix it.
- The checkout is shallow, so `git` could not resolve `c207ca3`. I used the API instead.
- The last 3 `verify-production` runs (workflow_dispatch, 19:25, 20:29, 23:30 on 11-17) were green.
- I could not read the Cloud Build trigger (#568). The tier is verified from `/health` and the runs only.

## GitHub Actions
- Failed run 44145312520 (push, 2026-11-17T18:12:27Z): the "Wait for the deploy" step ended with `DEPLOY_GATE: timeout`, and the summary says "No new revision appeared ... inconclusive, not green".
  - Three sibling push runs from the same minute (18:12:14, :18, :23) were cancelled after 5–6s, apparently by concurrency.
  - That is consistent with a burst of merges collapsing into one deploy, though I did not read the logs of the cancelled runs to confirm.
  - Production did later reach `c207ca3`, and the dispatch runs went green. I read this as an inconclusive run, not a deploy fault.
  - The run's displayTitle is a merge-commit subject, so the failed run is easy to misread as a failure of that commit.
- The sample of the 30 most recent runs across workflows was mostly success. It had 1 PR-gates failure, 2 "Agent work" runs with an empty conclusion (still running or unfinished), and some skips. I did not investigate the PR-gates failure.
- No trigger that never fires was found in this sample. I did not audit every workflow's `on:` block.

## Latency (probe in /tmp/probe.txt, taken from a GitHub runner)
- `/` 0.68s, `/kundli` 0.77s, `/matching` 0.67s, `/numerology` 0.70s, `/learn` 308 redirect in 0.44s. All pages are served from the page cache or are static in this probe.
- This does NOT measure the 26-second natal path, which only runs on an LLM cache miss. I did not trigger a natal generation, because that would spend Groq TPM on a production budget.
- The ~0.7s floor is dominated by the network round trip from the runner. I have no Cloud Run cold-start measurement.

## Free-tier headroom (Groq)
Source: `measurements/llm-usage.json`, generated 2026-11-17T03:22Z, 7 days. I read it this run; I did not produce it.

| Route | Calls | Cache hit rate | Tokens per call (measured) | Note |
|---|---|---|---|---|
| natal | 107 | 91% | 6,631 | measured on only 9 calls |
| rashifal | 28 | 92% | 4,429 | |
| ask | 13 | 0% | 2,270 | |

- Weekly total was 218,160 input and 32,187 output tokens. Peak measured day was 139,799 tokens (2026-11-11).
- The peak-day figure is 70% of the 200,000 TPD ceiling that CLAUDE.md says has been observed. This is the closest ceiling to being hit.
- That peak is a single day, not a trend, and the "measured" and unmeasured peak-day figures differ (12,796 vs 139,799), so the instrumentation is incomplete.

**Ceiling: 8,000 TPM per model (#266).**
- Current usage: one natal cache miss is about 6,631 input tokens plus output. That is 83% of one model's per-minute bucket, so one miss nearly fills it.
- Breaks at: 2 natal misses within the same minute on one model. Across the two-model chain (groq120, groq20) the combined budget is 16,000 TPM, so roughly 3 near-simultaneous misses in a minute exhaust it.
- Traffic multiple: average misses are low, so the multiple is set by burstiness rather than by volume. The failure is already intermittent at current traffic, which is why #266 is live. A natal miss rate that rises tenfold makes same-minute collisions common.
- Proposed move (existing issues, not new): shrink the natal prompt, or split it so no single call is near the ceiling. Serve shared content from a scheduled Claude Code job (CLAUDE.md's first move). Only `/kundli` is personal.
- Stays in the free tier: yes. No new model and no paid quota.
- Caveat: the 6,631 figure rests on 9 measured calls, so treat it as indicative. #212 is the gap: nothing gates per-request growth yet.
- #852's effect on rashifal tokens (flagged "not yet checkable" last time): the only figure here is 4,429 tokens per call across 27 measured calls. I have no pre-#852 baseline in hand, so I cannot say whether it helped.

## Standing issues
- #232: not re-measured this run. The mechanism is unchanged as far as I know. The fix is in-process memoisation (`hot_cache`) with a single in-flight fetch.
- #253: not re-measured this run. I did not check the service worker's current cache-versioning.

## Not done / could not verify
- No GCS read or egress numbers, and no Cloud Run request or CPU-second figures. The service account's permissions and the available tooling here did not give me those, so I give no headroom figure for them.
- No cold-start measurement.
