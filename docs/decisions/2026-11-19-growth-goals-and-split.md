# Growth goals at every level, a meter for each, and 60% of build cycles on growth

- **Date:** 2026-11-19
- **PR / issue:** #1241 (owner request in session)

## Why, measured

The owner, 2026-11-19: *"our objective is the user-base growth for shubhagya.com website, who is
making sure that it is happening or not ... split everyday work into 60% growth and 40% other work
... CEO should monitor if weekly goals are met, what is lacking and direct the loop accordingly for
next week. CEO direction should be taken into account."* Then: *"a meter should be added for daily,
weekly goal, overall goal ... Let's also set monthly, quarterly goal and have a meter for that"*;
*"Week is 7 days work not 5 days ... It should be Sunday review and Monday next week start"*; and
the ops dashboard must show *"the agents decisioning, actions, outcomes in graphs if possible or
tables otherwise"* before this merges.

Measured that day with `scripts/growth_split.py` against `measurements/loop.json` and the live
issue labels: week 2026-W47 had **13 of 62** build cycles on growth work (21%); November **16 of
230** (7%); **3** open growth issues; OBJECTIVE.md's lever at **1 of 10** top queries in the top 5.

Decided:

1. **`chief` sets and scores goals in a new Sunday review** (`agent-sync.yml`, `23 15 * * 0`,
   20:53 IST, before Sunday's 22:30 IST ranking): weekly every Sunday, monthly and quarterly when
   none exist, each goal with a `metric_key` the collector measures. The workflow posts chief's
   files on the one `weekly-goals` issue with `github.token`; chief, denied `gh api` in that
   review, posts nothing. Weeks are ISO, Monday to Sunday, IST. On the last day of a period
   (Sunday, for a week), the next period's goals take over as soon as they are posted, so
   Sunday's 22:30 IST ranking already plans against them (QA on #1241 measured them waiting
   for Monday). Posting refuses a period other than this one or the next (goals) / the last
   (scores), a goal no meter can measure, a body over 60,000 characters, and neutralises
   `@` mentions.
2. **60/40, enforced at ranking.** `project-manager` runs the script before every ranking; when
   `must_pick_growth` is true the top item is a growth issue, unless production is broken
   (exempt, outside the split). Growth = label `growth` (or the labels that already meant it), or
   named by a current goal.
3. **Five meters and the decisions on `/admin/ops`**, from `measurements/growth.json` written by
   `agent-measure`: daily share, weekly / monthly / quarterly goal progress, the objective meter;
   the daily split chart against the 60% line; the last 15 decisions (issue picked, kind, agents
   called, outcome); agent calls per day (from #1238); scores, chief's direction, open growth.

Rejected: goals under `measurements/` (CLAUDE.md: nothing load-bearing there; it never ships, and
the owner cannot edit it); a new workflow for the review (a new job fails
`verify_workflow_permissions.py`, and agent-sync already holds `issues: write`); a fixed daily
quota instead of the running rule (it starves growth when early cycles go to production fixes).

Cost: no new LLM run. The Sunday review is one more chief dispatch a week on the shared Max
subscription; the collector is stdlib plus ~10 GitHub API reads per run.
