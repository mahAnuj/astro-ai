# Chief guidance — 2026-11-28 (Friday review; no goals files)

Sources: /tmp/week.txt, loop.json 7d, claude_usage.json (00:21Z), agents.json (00:21Z, alerts empty), growth_split.py.
Quota: seven_day 0.07 (window just reset), allowed, no rejected runs. Capacity is not the constraint.
Build lane: 151 cycles, 78 shipped PRs, 1.8% of 6,728 min without result, idle 63.6h (37.8%).
Growth split W48: 15 growth vs 66 other = 0.185 (target 0.6, goal g1 0.40); today 0 of 4; month 0.134; must_pick_growth true.
Meters: weekly 0.546, monthly 0.503, quarterly 0.136, overall 1 of 10 queries at position <=5.
Last guidance (Tue): growth share was 0.342, now 0.185. Not followed: growth picks before QA follow-ups and analytics slices.

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | wasting | share 0.185 vs 0.60 while seven_day is 0.07; merges this week are mostly /admin/ops slices (#1133: #1552, #1556, #1558, #1561) | Stop /admin/ops and ops_data hardening; take #1076, #1107, #1065 (g4) next |
| qa | drifting | follow-up issues keep adding non-growth supply (#1553, #1554 class) | Follow-up issues only for defects the diff shipped to users |
| agent-merge | on-objective | merges success in the last 2 days, skips only on held PRs | None |
| agent-queue | on-objective | queue runs success; 1 cancelled today | None |
| steward | on-objective | success today, no stall alerts | Do not dispatch loop-plumbing ahead of growth issues |
| analyst | on-objective | measurement runs daily, latest.md refreshed | Keep the query-page export (#1436) feeding seo-growth |
| project-manager | wasting | must_pick_growth true all week, 0 of 4 build cycles today on growth | Run growth_split.py first and name the growth pick in the comment |
| seo-growth | drifting | no new band-page issues since Tuesday; only #1017 labelled growth is open | File band-page issues from gsc-band.json for the top pages by band_opportunity |
| agent-sync | on-objective | week.txt now lists shipped PRs and growth split | None |
| agent-measure / prioritise | on-objective | measure run in progress, no missed slots | None |
| design / discover / infra | on-objective | last runs success, not due | None |

## Stop
- /admin/ops slices and ops_data malformed-row hardening until g4 issues ship.
- Dispatching QA follow-ups ahead of a growth issue.

## Start
- #1076, #1107, #1065 in that order, then #1017/#1341 muhurat work (g5).
- Build idle is 37.8% at 7% quota: chain more cycles, all on growth.

## Definition fixes filed
- None this review.
