# Chief guidance — 2026-11-19 (Thursday, manual mid-week run, second this day)

Sources: /tmp/week.txt, loop.json (7d), claude_usage.json (04:50Z), agents.json (04:50Z, alerts empty).
Quota: seven_day 0.79, allowed_warning, no rejected runs.
Build lane: 207 cycles, 94 shipped PRs, 1.2% of 4,600 min without result, idle 102.5h (61%).
Growth split: week 13 growth vs 50 other = 0.206; today 0 of 6; month 0.069; must_pick_growth true.
Goals: monthly and quarterly exist (3 each). W47 weekly goals were missing (meter null); set this run.
Progress since morning: #1071, #1072, #1073, #1074, #1075 are now CLOSED; open growth issues are only #1065, #1076, #1107.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | week share 0.206, today 0 of 6 | Take #1076, then #1107, then #1065 before anything else this week |
| qa | on-objective | 54 qa-on-green successes, no repeat FAIL theme | None |
| agent-merge | on-objective | 67 success, 13 skipped, 1 cancelled | None |
| agent-queue | on-objective | queue failures fell from 4 (11-17) to 2 | Steward names the 2 failing run ids (asked twice) |
| steward | drifting | 4 success, 1 failure, 2 cancelled | Comment on open [main-red] #1249 once main is green |
| analyst | on-objective | GA4 trend (#1204) and index status (#1210) merged | Use the GA4 previous window in the next report |
| project-manager | drifting | share 0.206 with must_pick_growth true all week | Run growth_split.py first; say in the queue that only 3 growth issues are eligible |
| seo-growth | drifting | 3 open growth issues, supply caps the share | File band-page issues for the 6-20 queries in gsc-band.json today |
| agent-sync | wasting | "Merged this week" shows 1 commit against 94 shipped PRs | Read shipped counts from loop.json |
| agent-measure / research / discover | on-objective | no alerts in agents.json | None |
| chief (self) | drifting | needs-human-review #263, #233, #203, #198 unruled | Rule when an escalation arrives |

## Last time's instructions
- Followed: #1071-#1075 learn issues closed (5 growth issues shipped); #1074 closed.
- Not followed: queue-failure run ids; supply of new growth issues (still 3 open).

## Stop
- Analytics-event PRs while the week share is below 0.35.
- Opening #1187-#1190.

## Start
- #1076, #1107, #1065 in that order; new band-page issues from seo-growth.
- Size cycles to the 0.79 weekly window.

## Definition fixes filed
- None. The drift is growth-issue supply, not a `.claude/` line.
