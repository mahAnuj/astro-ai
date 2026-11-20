# Chief guidance — 2026-11-20 (Friday review; no goals files)

Sources: /tmp/week.txt, loop.json (7d), claude_usage.json (22:45Z), agents.json (22:44Z, alerts empty).
Quota: seven_day 0.10, allowed, no rejected runs (was 0.79 yesterday; the window reset, so capacity is not the constraint).
Build lane: 213 cycles, 89 shipped PRs, 2.7% of 4,810 min without result, idle 99.9h (59.5%).
Growth split: week 17 growth vs 58 other = 0.227; today 2 of 5 = 0.40; month 0.082; must_pick_growth true.
Meters: daily 0.667, weekly 0.214, monthly 0.073, quarterly 0.017, overall 1 of 10 top queries at position <=5.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | week share 0.227 vs 0.35 weekly goal; 58 other cycles, many are QA follow-ups (#1282-#1303) | Take #1076, #1107, #1065 (all still open) before any further QA follow-up or analytics issue |
| qa | on-objective | qa-on-green runs green; follow-up issues are specific defects | None |
| agent-merge | on-objective | many successes, few skipped | None |
| agent-queue | on-objective | 1 cancelled among ~12 runs today | None |
| steward | on-objective | success this cycle | Comment on open [main-red] #1307 only once main is green |
| analyst | on-objective | trend and index-status work merged | Use the GA4 previous window in the next report |
| project-manager | drifting | share 0.227 with must_pick_growth true all week | Run growth_split.py first; pick a growth issue when it says so, and name the 3 eligible ones |
| seo-growth | drifting | open growth supply is 3 issues; weekly goal g1 cannot be met without supply | File band-page issues for the 6-20 position queries in gsc-band.json |
| agent-sync | on-objective | week.txt "Merged this week" still lists 1 commit vs 89 shipped PRs (loop.json) | Planners read shipped counts from loop.json, not that list |
| agent-measure / research / discover | on-objective | no alerts in agents.json | None |
| chief (self) | on-objective | no escalations this week | Rule when one arrives |

## Last time's instructions
- Followed: #1071-#1075 closed; queue failures are down.
- Not followed: growth share 0.206 to 0.227 only; #1076, #1107, #1065 still open; no new band-page issues filed.

## Stop
- Taking QA follow-up and analytics issues ahead of growth issues while share < 0.35.

## Start
- #1076, then #1107, then #1065.
- With the window at 0.10 weekly use, chain build cycles on growth issues; idle 59.5% shows capacity exists, supply of growth issues is the limit.

## Definition fixes filed
- None. The drift is growth-issue supply, not a `.claude/` line.
