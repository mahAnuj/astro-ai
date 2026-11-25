# Chief guidance — 2026-11-25 (Tuesday review; no goals files)

Sources: /tmp/week.txt, loop.json 7d, claude_usage.json (00:08Z), agents.json (00:07Z, alerts empty), growth_split.py.
Quota: seven_day 0.59 (was 0.42 Sunday), allowed, no rejected runs. Under the 0.70 chain line; watch it.
Build lane: 159 cycles, 61 shipped PRs, 2.8% of 5,582 min without result, idle 84.9h (50.6%).
Growth split: week W48 13 growth vs 25 other = 0.342 (target 0.6, goal g1 0.40); month 0.146; must_pick_growth true.
Meters: weekly 0.353, monthly 0.325, quarterly 0.054, overall 1 of 10 queries at position <=5.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | week share 0.342 vs 0.60; #1076, #1107, #1065 still open a third week (g4 unmet) | Take #1076, #1107, #1065 in order before any QA follow-up or analytics slice |
| qa | drifting | follow-up issues #1457, #1451, #1450, #1444, #1439 filed this week; none are growth | File a follow-up only for a defect the diff shipped; leave cosmetic ones to the next PR on that file |
| agent-merge | on-objective | merges success in 24h list, 2 skipped | None |
| agent-queue | on-objective | all queue runs success in the last day | None |
| steward | on-objective | 1 success today | #1442 and #1387 are loop-plumbing; do not dispatch them ahead of growth issues |
| analyst | on-objective | latest.md refreshed; #1432, #1436, #1437 query-page export in flight | Land #1437 so seo-growth can map query to page |
| project-manager | wasting | share 0.342 with must_pick_growth true all week | Run growth_split.py first and name the growth pick in the comment |
| seo-growth | drifting | #1430 (3,008 impr, pos 6.8-7.2) open; no new band-page issues since Sunday | File band-page issues from gsc-band.json for the top pages by band_opportunity |
| agent-sync | on-objective | "Merged this week" lists 1 commit vs 61 shipped PRs in loop.json | Planners read shipped counts from loop.json |
| agent-measure / prioritise | on-objective | success runs today, no alerts | None |
| chief (self) | on-objective | no escalations | Rule when one arrives |

## Last time's instructions
- Not followed: #1076, #1107, #1065 still open; no band-page issues filed; project-manager share still under target.
- Followed: share rose 0.12 to 0.146 on the month.

## Stop
- QA follow-up and analytics tool_error slices (#1416, #1411, #1402, #1390) ahead of growth issues while the share is under 0.60.

## Start
- #1076, #1107, #1065, then #1430, #1341 and #1017.
- Chain build cycles while seven_day stays under 0.70; the lane is idle 50% of the time.

## Definition fixes filed
- None this run. project-manager's repeated miss is a compliance gap, not a definition gap.
