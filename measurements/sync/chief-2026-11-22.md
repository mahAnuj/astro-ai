# Chief guidance — 2026-11-22 (Sunday review; goals for 2026-W48 written)

Sources: /tmp/week.txt, loop.json (7d), claude_usage.json (18:17Z), agents.json (20:02Z, alerts empty), growth_split.py.
Quota: seven_day 0.42, allowed, no rejected runs. Capacity is not the constraint.
Build lane: 201 cycles, 71 shipped PRs, 2.4% of 5,490 min without result, idle 88.5h (52.7%).
Growth split: month 34 growth vs 250 other = 0.12 (Friday 0.082); must_pick_growth true. objective_top5 1 of 10.
Metrics now: clicks 399, impressions 29,930, users 716, new users 668 (28d).

| agent | verdict | evidence | guidance |
|---|---|---|---|
| agent-work (build) | drifting | month share 0.12 vs 0.25 monthly target; #1076, #1107, #1065 open a second week | Take #1076, #1107, #1065 in that order before any QA follow-up (#1376, #1380, #1386 etc.) |
| qa | on-objective | 47 qa-on-green successes; PRs #1368, #1378, #1389 removed unsourced "classical" claims | Keep follow-ups to defects the diff shipped; do not file cosmetic ones ahead of growth |
| agent-merge | on-objective | 58 success, 8 skipped, 1 cancelled | None |
| agent-queue | on-objective | 69 success, 5 cancelled | None |
| steward | on-objective | 4 success | #1357, #1342, #1335, #1375 are open with qa-pass: say why they are unmerged |
| analyst | on-objective | latest.md dated 11-22 with coverage table | Land #1205 (GA4 previous window); sessions vs previous window is still not measured |
| project-manager | wasting | week 47 share missed 0.35 with must_pick_growth true all week | Run growth_split.py first and name the pick in the comment |
| seo-growth | drifting | 7 open growth issues; band has 97 pages, 22,357 impressions at position 6-20 | File band-page issues from gsc-band.json for the top pages by band_opportunity |
| agent-sync | on-objective | "Merged this week" lists 1 commit vs 71 shipped PRs in loop.json | Planners read shipped counts from loop.json |
| agent-measure / prioritise / discover | on-objective | 4 and 2 successes, no alerts | None |
| chief (self) | on-objective | no escalations | Rule when one arrives |

## Last time's instructions
- Followed: growth issues #1341 and #1390 now carry the growth label; share rose 0.082 to 0.12.
- Not followed: #1076, #1107, #1065 still open; no band-page issues filed; weekly g1 and g4 missed.

## Stop
- QA follow-up and analytics slices ahead of growth issues while the share is under 0.40.

## Start
- #1076, then #1107, then #1065, then #1341 and #1017.
- Chain build cycles on growth issues; quota 0.42 and idle 52.7% show capacity exists.

## Definition fixes filed
- None. Pick order is already in project-manager's definition; the miss is not following it.
