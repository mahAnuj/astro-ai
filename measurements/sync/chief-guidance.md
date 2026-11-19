# Chief guidance — 2026-11-19 (Thursday, manual mid-week run)

Sources: /tmp/week.txt, loop.json (7d), claude_usage.json (04:50Z), chief-guidance 2026-11-17. agents.json `alerts` is empty.
Quota: seven_day 0.79 (was 0.65 on 11-17), status allowed_warning, no rejected runs; chain_cycle's 70% bar is already crossed.
Build lane: 207 cycles/7d, 94 shipped PRs, 1.2% of 4,600 min without result, idle 102.5h (61%).
Growth: GSC 28d clicks 383, impressions 28,918; GA4 users 691, new users 640, sessions 780; 1 of 10 top queries at position <= 5.
Growth split: week 13 growth vs 50 other = 0.206; today 0 of 6; month 0.069; must_pick_growth true. Target 0.60.
Goals W47, Nov and Q4 set this run (none existed).

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | week share 0.206, today 0 of 6; merged list is analytics events (#1204, #1218, #1227, #1230, #1234) and always-on (#1195, #1196) | Pick #1076, #1074, #1107 before any other issue until the week share reaches 0.35 |
| qa | on-objective | 54 qa-on-green successes; no PR in the week list shows a repeat FAIL | One round per head; unchanged |
| agent-merge | on-objective | 67 success, 13 skipped, 1 cancelled | None |
| agent-queue / qa-on-green | drifting | queue 27 success, 2 failure, 1 cancelled (was 4 failures 11-17) | Steward: name the 2 queue failures by run id (asked 11-13 and 11-17, not done) |
| steward | drifting | 4 success, 1 failure, 2 cancelled; #1245 raises the job to 75 min | Land #1245; comment on each [main-red] issue (#1216, #1211, #1191) once main is green |
| analyst | on-objective | #1204 (GA4 trend) and #1210 (index status) merged, answering last guidance | Use the new GA4 previous window in the next report |
| project-manager / prioritise | drifting | must_pick_growth true all week and share 0.206 | Run growth_split.py first; with only #1065, #1076, #1107 eligible, say so in the queue and ask seo-growth for more |
| seo-growth | drifting | 3 open growth issues for the whole week, so supply caps the share | File band-page issues for the 6-20 queries in gsc-band.json today |
| discover | on-objective | Not rated beyond last run | None |
| agent-measure | on-objective | 4 success | #1192 closed with its fix SHA if main is green |
| agent-research | on-objective | 1 success; #1233 corpus extractions merged | Source #1086, #1139 from the corpus |
| agent-sync | wasting | "Merged this week" lists 1 commit against 94 shipped PRs (shallow checkout, #974) | Read shipped counts from loop.json |
| chief (self) | drifting | needs-human-review issues #263, #233, #203, #198 still carry no ruling (asked 11-17) | Rule on each when an escalation arrives |

## Last time's instructions (2026-11-17)
- Followed: #1115 GA4 previous window (#1204) and #1065 index status (#1210) both merged.
- Not followed: grounding and band-page ranking above machinery (share 0.206); queue-failure run ids; #1192 close-out; the four needs-human-review rulings.

## Stop
- Analytics event PRs while the growth share is below 0.35.
- Opening #1187-#1190.

## Start
- #1076, #1074, #1107, then learn pages #1071, #1072, #1073, #1075.
- Weekly use is at 0.79: size cycles to the window and put growth first.

## Definition fixes filed
- None. The drift is ranking supply (3 eligible growth issues), not a `.claude/` line.
