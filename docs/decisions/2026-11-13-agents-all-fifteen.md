# A card for every agent definition, grouped, each saying where it runs

- **Date:** 2026-11-13
- **PR / issue:** this PR (owner, in a session: *"add cards for all agents, it's okay if they don't run automatically or whatever the logic is, we just show it upfront. Helps understand the system better."*)

## Why, measured

The page and anujmahajan.com/agent-cycle advertise **15 agents** (`ls .claude/agents | wc -l` = 15)
and showed **8 cards**, two of which (developer, merge) were not agent definitions. Each of the
15 now has a card, grouped build / decide / measure / operate / on request, plus `merge`,
labelled on its card as a workflow, not an agent. Every card states where the agent runs.

Where each runs, read from `.github/workflows/`, `.claude/commands/` and `chief.md`:

| agent | runs from | state source |
| --- | --- | --- |
| dev-lead | every build cycle (agent-work) | the build run, exact target |
| architect, engineer, frontend-engineer | called inside a build cycle | **standby** while a build run is live |
| qa | QA rounds | the QA round, PR labels |
| chief | held PRs; oversight review (agent-sync) | held PRs, then an agent-sync run |
| project-manager / product-manager | agent-prioritise / agent-discover | that run, else agents.json |
| analyst | agent-measure | that run, else agents.json |
| astro-auditor, numerologist | agent-research | that run, else agents.json |
| steward / infra-lead | agent-steward / agent-infra | that run, else agents.json |
| conversion-lead, qa-lead | **no schedule**: chief's routing table or a session | idle, "not on any schedule" |

**`standby` is a new state, and deliberately not `running`.** Which helper a build cycle is using
at a given minute happens inside the Claude step and is not visible from the GitHub API; a
"running" light on all three would assert something nobody measured. Standby says only what is
known: the run they are called from is live. Hollow dot, no pulse.

**Found while mapping, and corrected everywhere it was stated:** `CLAUDE.md` said conversion-lead,
frontend-engineer, qa-lead (and five others) "are driven by their own scheduled loops"; three of
them never were. anujmahajan.com said "18 workflows" in seven places while the repo has 19.

**Cost:** none added. The new cards read the same three GitHub responses; agent-research,
agent-infra and agent-sync history comes from the committed `agents.json`, which already has
rows for them. `tests/test_agent_status.py::test_every_agent_definition_has_a_card` fails when
a new file lands in `.claude/agents/` without a card.
