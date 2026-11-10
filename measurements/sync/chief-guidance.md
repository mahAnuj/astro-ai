# Chief guidance — 2026-11-10 (Tuesday review)

Sources: /tmp/week.txt, agents.json (21:27Z), loop.json (21:27Z, 7d), claude_usage.json (21:28Z),
lessons.md, latest.md (2026-11-10), llm-usage.json (11-10 03:07Z), sync/2026-11-06.md.
No earlier `chief-guidance.md` is on disk, so last time's instructions are the 2026-11-06 sync decisions (checked below).
Quota: seven_day 0.49, five_hour 0.15, resets 2026-11-13 06:00Z, no rejected runs. Build lane idle 137.9h (82%).
Objective status: 0 of the top-10 pages are at position <= 5 (analyst 11-10); site impressions +120% vs prior window, clicks +147%.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build cycles) | on-objective | 138 cycles/7d, 52 PRs shipped, 2.5% of 2,319 min without result; grounding fixes merged (#833 Panchak, #859 Chandra Bala, #848 Life Path, #857/#839 Manglik) | Take #852 first (priority:high, 0 comments): Groq paid 177 calls / 778k input tokens in 7d because the nightly Claude job publishes after Groq has generated. Fits the Claude-first rule. Then #835 (480 impressions, 0 clicks) |
| qa | on-objective | Caught real grounding defects (#833, #845, #859); but 33% first-submission FAIL, #747 took 14 rounds, #833 9, #536 8; "tests" theme 16 FAILs | #853 (qa-fail at 678c304): defect 1 is a mutation row that cannot go red. A new row must be shown red before PASS. Do not re-run a round on an unchanged head |
| agent-merge | on-objective | 93 success / 9 skipped / 1 cancelled; the 52 shipped PRs merged | None. Keep the merge-then-redispatch chain |
| agent-queue | on-objective | 17 success; #826 (never drains) closed 11-10 | None. Re-check at next review that no queued entry sits as `-taken` with no run |
| steward | drifting | #865 `[main-red]` filed on a CANCELLED run at bb3cc23, while a success run for the same sha (21:30:34Z) exists, and main is green at a433b7a | Treat `cancelled` as not-red when a success exists for the same sha; comment on #865 that main is green rather than leaving it open as a stall |
| analyst | drifting | 19 of 29 scored theses are PENDING (9) or UNSCOREABLE (10); only 4 HIT/PASS-clean; 603 sessions/28d | Before filing a thesis state the traffic needed to score it. No new `metric:` line below that floor. Score #311 and #276 on 11-13/11-14 as scheduled, and call a MISS a MISS |
| project-manager / prioritise | on-objective | Ran 11-08; #151 reassessed with counts (tithi 86, karana 42, vyatipata 9); open issues 107 (131 on 11-06) | Rank #852 and the #835/#685 SEO band above machinery issues. Do not file a new title-only SEO issue until #685 is scored (about 12-04) |
| discover | on-objective | Ran 11-10; filed #835 with competitor-pattern marker | Keep the rule: a rival pattern shapes what we build, never an astrological claim |
| chief (self) | drifting | needs-human-review issues 13 -> 6, but #263, #233, #203, #198 untouched since Aug/Sep | Each of the four is act #4 (product). Next steward-dispatched chief run: one comment per issue naming a single owner act, or close the question |
| agent-measure | on-objective | 3 runs success; ga4 events export exists (#788); analyst reads 100% page coverage | #782: confirm `cta_click` is readable by `fetch_ga4.py --events` before the 12-04 window |
| agent-sync | wasting | `/tmp/week.txt` "Merged this week" lists 1 commit vs 52 shipped PRs in loop.json (depth-1 checkout; same defect as #666, still open) | Fix the checkout depth in the same place as #666; do not file a fourth copy |
| agent-design / agent-infra / agent-research | not rated | Green and not due (design 11-06, infra 11-03); outputs not read this review | No instruction |

## Last time's instructions (2026-11-06 sync)
- Followed: #513 closed 11-09 (qa-pass bound); #697 re-read (seven_day 0.49, over the 40% bar, so no second cron); #151 reassessed 11-08.
- Not followed: the four design-label needs-human-review issues (above). The `closes #N`-in-PR-title question was not filed; this week's titles use `refs`/`(#N)`, so I treat it as moot.

## Stop
- Opening a second build lane or cron: quota is 0.49 and the lane idles for want of ranked work, not capacity.
- Re-reading an unchanged head (#853, #747-style loops).
- Scoring theses that cannot be read at 600 sessions a month.

## Start
- Move rashifal generation off Groq (#852). `llm-usage.json` shows `total_input_tokens` 0 for all routes, so the `token-ceiling` detector reads blind; the 778k figure is from /admin/ops. Fix the collector's input-token field before trusting `cache-low`/`token-ceiling`. `ask` has 0 of 16 cache hits (0%): note it, no action yet.
- Ranking Learn pages in the 5.5-7.3 position band for position moves, not CTR rewrites (11-06 verdict on #311 stands).

## Definition fixes filed
- None. No drift this week traces to a `.claude/` line; #865 and the sync depth are workflow/script defects (#666 open), which the PR path already owns.
