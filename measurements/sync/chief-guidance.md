# Chief guidance — 2026-11-17 (Tuesday review)

Sources: /tmp/week.txt, agents.json (23:17Z), loop.json (7d), claude_usage.json (23:18Z), lessons.md, latest.md (analyst 11-17), chief-guidance 2026-11-13.
Quota: seven_day 0.65 (was 0.12 on 11-13), five_hour 0.03, status allowed, no rejected runs. Build lane: 201 cycles/7d, 103 shipped PRs, 0.9% of 4,429 min without result, idle 104.7h (62%).
Growth (28d to 11-14): GSC impressions 27,852 vs 11,348 prior (+145%), clicks 375 vs 113 (+232%), GA4 sessions 740 (no prior window, #1115). Organic 61%.
Alerts: agents.json lists pr-gates.yml dormant; lessons shows 2 of last 4 build cycles built nothing (amber).

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | 103 shipped PRs; this week's issues touched are mostly always-on loop machinery (#1184-#1190, #1195, #1196) and privacy/security (#1159-#1163, #1173); seo #1175-#1177 shipped. Quota went 0.12 to 0.65 in 4 days | Rank band-page and seo issues (#1178, #1107, #1074, #1076 matching position drop 4.2) and the grounding fixes (#1078-#1086) above always-on #1186-#1190. Do not open #1187-#1190 until #1196 is measured against a loop that was actually starved |
| qa | wasting | grounding 31 FAILs, tests 26, regression 25, copy 20, tokens 20; #1167, #1169, #1173, #1150 recur across 4+ themes | Unchanged: on a FAIL naming a test or mutation row, show that row red before PASS. One round per head |
| agent-merge | on-objective | 56 success / 20 skipped / 3 cancelled / 1 failure; #1199, #1197 merged | None |
| agent-queue / qa-on-green | drifting | queue 16 success, 4 failure, 2 cancelled (was 1 failure on 11-13); qa-on-green 57 success, 1 failure, 2 cancelled | Steward: name the cause of the 4 queue failures by run id (instruction from 11-13 not followed) |
| steward | on-objective | 4 success; main-red issues #1191, #1192 opened and handled (#1193 fixed red main) | Close-out line on each [main-red] issue once main is green; do not leave them open |
| analyst | on-objective | Report of 11-17 states coverage per export; flags GA4 has no prior window and index-status absent | Land #1115 (GA4 previous window) and #1065 so claims on sessions get a period-on-period figure |
| project-manager / prioritise | on-objective | Ran 11-16 (success); band pages ranked | Keep rahu-mahadasha-ketu-antardasha, jupiter-in-10th-house-career, 7th-lord-placement above machinery |
| discover | on-objective | Last run 11-17 02:45Z success | None |
| chief (self) | drifting | 7 open needs-human-review issues; no ruling logged against #263, #233, #203, #198 since the 11-13 review | One comment each naming the owner act (product, act #4) at the next steward-dispatched run |
| agent-measure | on-objective | 3 success this week; one in progress; #1192 (claude-code-action pin) filed | Close #1192 with the fix SHA |
| agent-sync | wasting | /tmp/week.txt "Merged this week" lists 1 commit against 103 shipped PRs in loop.json (shallow checkout, #974) | Unchanged: read shipped counts from loop.json |
| agent-design / infra / research | not rated | Not due; outputs not read | None |

## Last time's instructions (2026-11-13)
- Followed: #968/#970 grounding picks reached the build lane (#1078-#1086 filed); no new sub-12px sweep in the merged list.
- Not followed: queue-failure cause by run id; #263, #233, #203, #198 rulings; #666/#974 sync depth.
- Not yet checkable: #852 effect on rashifal tokens (compare llm-usage.json next run).

## Stop
- Opening the always-on sub-issues #1187-#1190 before #1196's effect is measured.
- Re-running QA on an unchanged head.
- Machinery PRs ranked above band-page work while 98% of impressions sit at positions 6-20.

## Start
- Grounding fixes #1078-#1086 and #1139 (Abhijit 'best' claim) with corpus_search citations.
- Learn-page title/lede/FAQ moves on the three unowned band pages.
- Watching seven_day: 0.65 at mid-week; chain_cycle's 70% bar will bite by Thursday.

## Definition fixes filed
- None. The drift is a ranking choice, not a `.claude/` line.
