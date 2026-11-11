# infra-lead report — 2026-11-11 (run began 2026-11-10 ~23:58Z)

Focus: free-tier headroom, deploy truth, latency. Everything here was measured this run unless marked "read from" a file or "derived".
**Nothing in GCP, the repo or CLAUDE.md was changed.** I made two issue comments and filed one issue.

## 0. Summary

| # | Finding | Action |
|---|---|---|
| 1 | The `exact` deploy tier is live and holds. `/health` served `build_sha a433b7a`, which is the SHA of the 22:01Z verify-production run (success). | None. Not re-fixed. |
| 2 | One verify-production failure in the last 40 runs: a commit superseded by a merge 27 s later can never match the exact tier, so it times out after 12 min. | Commented on #341, which has the same root cause. |
| 3 | First request to each rashifal page after IST midnight takes 3.5–9.7 s (6 of 6 rashis). Repeats take 0.54–0.83 s. | Commented on #852 (the fix is already proposed there). |
| 4 | `llm-usage.json` reads 0 input tokens on every route, so the `token-ceiling` detector is blind. | Filed #868. |
| 5 | The brief's "standing work" list is stale: #266, #232 and #253 are CLOSED. Only #212 is open. | Noted below. |
| 6 | I still cannot read Cloud Build, Cloud Run or GCS. | Already tracked in #568. |

## 1. Deploy truth

- `curl /health` (00:00Z): `{"ok":true,"revision":"bhagya-00652-hc9","build_sha":"a433b7a07c0bd9fd9b38df41e73996ae027fd131"}`.
- Run 42910633224 (workflow_dispatch, head a433b7a, 22:01Z) concluded success. Its log has the exact-tier branch.
- `origin/main` is ff1dd2e (#861, merged 23:57:12Z). Run 42927508055 for it was still in "Wait for the deploy" when I last read it. **I did not see ff1dd2e serving.** A build_sha two commits behind HEAD within minutes of a merge is the normal deploy lag, not a fault. I did not re-read `/health` after the deploy window.
- I could not compare a433b7a to the tree: the checkout is shallow (`git rev-parse --is-shallow-repository` is true) and the object is absent. The proof comes from the matching workflow run, not from git.
- `gh run list --workflow=verify-production.yml -L 40`: 38 success, 1 failure, 1 in progress. Of the 40, only one was a `push` event; nearly all were `workflow_dispatch` from `agent-merge`.

### The one failure, run 42868967144 (head b500fd9, the #854 merge)

- Dispatched 17:50:03Z. Another commit, 6d615d6, landed at 17:50:24Z.
- The log shows tries 1–21 serving `b05de53` on revision bhagya-00643-hsk, then tries 22–48 serving `6d615d6` on bhagya-00645-2rx. Revision 00644 was never observed.
- "Wait for the deploy" ran 17:50:08 to 18:02:28 and exited 1 with `DEPLOY_GATE=timeout`.
- Production was verified anyway: the next run (6d615d6) was green.
- The cost is that close-on-evidence has no green run for b500fd9 itself.
- Frequency: 1 in 40 runs. It needs two merges inside roughly one build time, and `agent-merge` now chains merges (CLAUDE.md, 2026-11-07), so it will recur.
- The fix is a `superseded` result when the serving SHA is a descendant of `GITHUB_SHA`. That needs `fetch-depth > 1` and a workflow edit, which is `chief`'s or a human's. Written up on #341 (comment 6782739919), not filed separately.

## 2. Latency (from this runner; each ~0.35 s of it is the network floor)

| Route | Measured |
|---|---|
| `/`, `/kundli`, `/matching`, `/numerology` (probe file) | 0.62–0.66 s, all 200 |
| `/panchang`, `/learn/`, `/static/css/app.css`, `/static/sw.js`, `/health` | 0.59 s, 0.77 s, 0.42 s, 0.36 s, 0.36–0.45 s |
| `/learn` (probe file) | 307, 0.46 s (redirect to `/learn/`) |
| `/rashifal/<rashi>`, first request after IST midnight | aries 5.66, taurus 3.53, leo 3.60, gemini 7.96, pisces 9.69, virgo 4.76 s (TTFB) |
| the same pages, second request | 0.54–0.83 s |

- **The rashifal first-hit cost is real and has a known cause.** At 00:00Z the IST day was 2026-11-11 (the pages carried that date). The 01:00Z `/admin/warm-rashifal` had not run yet, so each rashi pays its generation on the first read. The 3.5–9.7 s is consistent with an LLM call, but I read no server logs, so I cannot prove it was Groq rather than a GCS miss.
- The affected window is IST 00:00–06:30, low-traffic but crawler-visible. #852's fix (generate tomorrow's day the afternoon before) removes it. Evidence added on #852 (comment 6782740297).
- **Free-tier cost of my probe, disclosed:** six distinct rashis, derived at ~3,330 input tokens each (CLAUDE.md's figure, not measured by me), is ~20k of the ~200k TPD if those were Groq misses. I did not POST `/kundli` or any natal route.
- `sw.js` is served with `cache-control: public, max-age=300` and an ETag. That is not the no-revalidate shape that caused #253. #253 is closed.
- `/` is `no-store` with `x-cache: MISS`, so every page view reaches Cloud Run. The 0.6 s figure is Cloud Run's own, with no CDN in front. Derived: the home page scales with Cloud Run's request ceiling.

## 3. Free-tier headroom

| Resource | Ceiling | Measured now | Breaks at | Move |
|---|---|---|---|---|
| Groq TPM (per model) | 8,000 | not measured this run; last measured natal worst case 6,751 (2026-11-03 report) | one uncached natal per minute per model | unchanged: cache, then #852 |
| Groq daily (rashifal path) | ~200,000 TPD | 778,261 input tokens / 7 days from /admin/ops (read from #852, not measured by me), ~111k/day average | the 7-day average is already ~56% of TPD, derived | #852 moves it to ~0. It stays inside the free tier and uses the Claude Max quota. |
| Claude Max weekly window | 100% | `seven_day` 0.49, `five_hour` 0.15, status allowed (`claude_usage.json`, 21:04Z) | at 2x the current weekly burn | #852 adds one scheduled job. 0.49 leaves room, but size it against this file. |
| Cloud Run / GCS | free-tier quotas | **not readable** (PERMISSION_DENIED, below) | unknown | #568 |

- The 778k/7 days figure is a **7-day total**, so the per-day average is derived and the peak day could be higher.
- `llm-usage.json` (generated 2026-11-10T03:07Z) shows 119 calls, 66% hit rate (natal 86%, rashifal 50%, ask 0 of 16) and input tokens 0 throughout. That is the collector defect in #868. **I did not use its token figures.** Its hit-rate figures I take as plausible but unverified here.
- `ask` has 0 of 16 cache hits. Chief said note it and take no action. Noted.

## 4. GCP access (re-tested this run)

- `gcloud builds triggers list --region asia-south1 --project bhagya-500701` → `PERMISSION_DENIED`, as `agent-analytics@bhagya-500701.iam.gserviceaccount.com`.
- `gcloud run services list` → `Permission 'run.services.list' denied`.
- So **no trigger export was possible and no GCP change was made.** I could not confirm `ignoredFiles: measurements/**` is still on the trigger. I verified the exact tier from `/health` and the verify-production logs only, as the brief says to. #568 tracks the missing roles. I did not try to widen the account.

## 5. GitHub Actions

`gh run list -L 150` covers 2026-11-10 19:40Z to 23:57Z (about 4 h) and shows 6 non-success runs, all PR-side:

| Run | Workflow | Result | Cause |
|---|---|---|---|
| 42893872894 / 42893872911 (20:17Z) | PR gates, verify-build | failure | branch `issue/584-numerology-score-disclosure` |
| 42895618099 / 42895618077 (20:28Z) | PR gates, verify-build | failure | same branch; the work merged as #861 at 23:57Z, so the loop fixed it |
| 42904850808 (21:25Z) | PR gates | cancelled | `issue/759-chief-clear-dispatches-merge`, superseded by a newer push (I did not read the log) |
| 42905722609 (21:30Z) | PR gates | cancelled | on `push` to main, I did not read the log |

- I did not open the logs of the #584 failures or the two cancellations. The 4-hour window is too short to rate any workflow's failure rate. No red `main`, no failed `Agent queue`, `Agent merge` or `agent-work` runs appear in it.

## 6. Standing work, state read this run

| # | State | Note |
|---|---|---|
| #266 /kundli 503 | CLOSED 2026-10-21 | I did not POST `/kundli` this run to avoid spending ~6.8k tokens, so I make no claim it is gone. `/kundli` GET is 200 in 0.60 s. |
| #212 prompt growth | OPEN, last update 2026-08-26 | `scripts/verify_token_budget.py` exists. I did not run it this run. |
| #232 rashifal GCS fan-out | CLOSED 2026-10-31 | Repeat reads of one page were 0.54–0.83 s. |
| #253 stale stylesheet | CLOSED 2026-10-20 | See `sw.js` headers above. |

The brief's standing-work list should drop #266, #232 and #253, and `.claude/agents/infra-lead.md` still says the exact tier "**has never run**" (line 39) and names an `architecture-scaler` skill that is not in this session's skill list. The same stale claim was flagged in the 2026-10-13 and 2026-11-03 reports. Editing that file is permitted by the 2026-11-06 grant, but I am read-only on code this run and did not change it. A one-line fix is for a later cycle.

## 7. Filed and commented

- **#868 (new):** `collect_llm_usage.py` reads the `input_tokens` field that #473 zeroed on purpose, so `token-ceiling` and `cache-low` read blind. Needs an Engineering fix. I read the cause from the tree and did not run the collector.
- **#341 comment:** the superseded-commit timeout, with the log evidence.
- **#852 comment:** the first-hit latency measurements.

## 8. What I did not do

- No `/kundli`, natal, ask, or `/admin/*` call.
- No Cloud Run, GCS or Cloud Build reads. No Actions-minute figures (the repo is public and `cost.json` says unlimited).
- I did not re-check whether ff1dd2e deployed.
