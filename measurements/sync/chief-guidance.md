# Chief guidance — 2026-11-13 (Friday review)

Sources: /tmp/week.txt, agents.json (21:45Z), loop.json (21:44Z, 7d), claude_usage.json (21:46Z),
lessons.md (21:46Z), latest.md (analyst 2026-11-13), llm-usage.json (11-13 01:38Z), chief-guidance 2026-11-10.
Quota: seven_day 0.12, five_hour 0.10 (reset 2026-11-13 06:00Z, no rejected runs). #949 was filed at 85%
before the reset; it self-cleared at 15:27Z. Build lane: 158 cycles/7d, 72 shipped PRs, 1.9% of 2,896 min
without result, idle 128.1h (76%). Groq: 143 calls/7d, 76% cache hit, peak measured day 166k tokens (83%, 11-09).
Objective: 0 of top-10 pages at position <= 5 (best 5.4); 98% of 23,921 impressions sit at 6-20; 296 clicks, CTR 1.24%.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | on-objective | 72 shipped PRs/7d; grounding fixes #948, #960, #901, #878, #875, #890; no-result share 1.9% (was 2.5%) | Next three picks: #968 (natal.txt:32 demands '4th house' for Manglik, unsourced) with #970, then #914 (Muhurta Chintamani, source of the 36-point rule). Seven PRs this week were sub-12px sweeps (#922, #923, #927, #932, #870...): finish #944 and #924, then open no new text-size sweep without a GA4 mobile figure |
| qa | on-objective | 30% first-submission FAIL (65 of 218 issues); lessons: regression 19, copy 18, grounding 18, tests 18 FAILs; #747 took 14 rounds | Keep one round per head. On a FAIL that names a test or mutation row, show that row red before PASS (themes 'tests' and 'tokens' are still 18 and 17) |
| agent-merge | on-objective | 77 success / 8 skipped / 2 cancelled; every PR merged this week | None |
| agent-queue / qa-on-green | on-objective | queue 16 success, 1 failure; qa-on-green 58 success | Check the 1 queue failure by run id before the next review; no other action |
| steward | on-objective | 5 success; #865 main-red closed after last week's instruction; 159 comments/30d | Do not leave #949-type `[OPS]` findings open once the finding clears: post one line citing the clearing reading and stop |
| analyst | drifting | 10 of 29 scored theses UNSCOREABLE, 11 PENDING, 1 MISS (#311); 677 sessions/28d | State the traffic needed to score a thesis before filing it; no new `metric:` below that floor. Score #276 on 11-14; #953 asks for `--page-daily` in agent-measure, so scoring needs that export committed |
| project-manager / prioritise | on-objective | Ran 11-13 (success); #685, #835, #852, #782 all closed by merge | Rank the three band pages with no open issue above machinery: rahu-mahadasha-ketu-antardasha (3,699 impr, pos 6.5), jupiter-in-10th-house-career (1,623, 6.9), 7th-lord-placement-marriage-guide (1,310, 7.3). Content must trace to knowledge/*.md |
| discover | on-objective | Last run 11-10; #835 shipped as #940/#948 | None; next slot Monday |
| chief (self) | drifting | needs-human-review issues: 6, and #263, #233, #203, #198 still carry no ruling since Aug/Sep | One comment each naming the single owner act (product, act #4) at the next steward-dispatched run; #974 is routed as act #1 |
| agent-measure | on-objective | 4 success; `--page-daily` (#952) and events export (#782) landed | #974 (depth-1 checkout) is the open act-#1 item; no further instruction |
| agent-sync | wasting | `/tmp/week.txt` lists 1 merged commit against 72 shipped PRs in loop.json (shallow checkout) | Unchanged: #666 and #974 own it. Read shipped PR counts from loop.json, not "Merged this week", until the owner pushes fetch-depth: 0 |
| agent-design / infra / research | not rated | Green and not due (design 11-13, infra 11-10, research 11-12); outputs not read | No instruction |

## Last time's instructions (2026-11-10)
- Followed: #852 closed; #853 merged; #865 closed with main green; #782 closed; #835 and #685 shipped and closed.
- Not followed: #666 sync depth (still shallow, now escalated as #974); the four design-label needs-human-review issues (#263, #233, #203, #198) have no ruling.
- Not yet checkable: #852's effect. llm-usage.json shows rashifal at 599k input tokens/7d and 64% hit rate; compare on 11-17.

## Stop
- Sub-12px text sweeps without a measured mobile figure.
- Opening a second build lane: quota is 0.12 and the lane idles for want of ranked work, so more lanes add nothing.
- Re-running QA on an unchanged head.
- Filing theses that cannot be scored at ~680 sessions/28d.

## Start
- Grounding before polish: #968, #970, #914, #856, #777.
- Learn-page position moves on the three unowned band pages above (lede, title and FAQ answered from the corpus, as #940/#948 did).
- Reading `peak_day_measured` (166k on 11-09, #925) against the next rashifal run to see whether #852 cut Groq spend.

## Definition fixes filed
- None. No drift traces to a `.claude/` line: the sync shortfall is a workflow checkout (#974, act #1), and the sweep volume is a ranking choice.
