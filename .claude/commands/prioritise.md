---
description: Decide what to work on next across the whole backlog — staleness sweep, then an ordered queue with reasons.
---

# /prioritise — what should we work on next

The user wants the backlog triaged and ordered. Dispatch to the `project-manager` agent.

## Your action

```
Agent(
  subagent_type="project-manager",
  description="Prioritise the backlog",
  prompt="""Decide what we should work on next across the whole backlog in <cwd>.

Follow your agent definition. In particular:

1. **Staleness sweep FIRST.** Find issues that are already fixed, no longer reproduce, subsumed by another, or overtaken by a refactor. Verify against `origin/main`, not against claims in comments. Report these separately — closing stale issues is cheaper and more valuable than ranking them.

2. **Then the queue.** At most 5-7 items, ordered by user harm, then unblocking power. For each: what is broken, why it sits at that position, what it blocks or waits on, rough size, which loop should take it, and whether it needs a verification gate.

3. **Then the two lists**: what is blocked and on what (noting where a blocked *value* still has an unblocked *disclosure* fix), and what looks urgent but should NOT be done, with reasons.

Read `BACKLOG.md` (the standing overview from the last scan) FIRST, then the issues, the
git and deploy state, and AGENT_STATUS.md before ranking. Treat `BACKLOG.md` as a cache,
not as evidence: use it to decide where to look, re-verify anything whose files changed
since the SHA in its header, and never restamp a carried-forward verdict with today's SHA.
Hand back the delta against it — what changed, what you carried unchecked, what is new.
Never queue work another loop is already doing. Read-only — propose closures, do not close,
and do not write `BACKLOG.md` yourself.

<args>
"""
)
```

If the user named a focus (`/prioritise correctness`, `/prioritise mobile`), pass it through and rank within that slice, but still run the staleness sweep across everything — stale issues in other areas are still worth surfacing.

## After the agent returns — update `BACKLOG.md`

`BACKLOG.md` (repo root, tracked) is the standing overview. **You** write it; the agent
never does. Update it in place rather than regenerating it:

- Bump the header's scan date and `origin/main` SHA.
- Move rows between sections as verdicts change. Keep issues closed since the last scan in
  a *Recently resolved* section for one cycle, so a reopened issue does not read as new.
- Carry forward each row's `checked@` SHA **unchanged** unless the agent actually
  re-verified it this pass. An em-dash means "not individually re-verified" and must stay
  an em-dash. Restamping unchecked rows is how this file turns into the thing CLAUDE.md
  warns about — a written justification treated as a fact.
- Append a row to the *Scan history* table at the bottom.
- Record the environment gaps that limited the scan (unreachable production, a partial
  `data/`, no venv), so a later reader knows which verdicts are narrower than they look.

Then commit it with the scan, and relay the queue and stale list to the user.

## Notes

- Do not rank the backlog yourself in the main conversation. Reading 49 issues with comments is exactly the context load this agent exists to keep out of here.
- The agent proposes closures; **the human closes**. Relay its stale list and ask.
- If it returns a queue whose top item is already in flight, that is a bug in its input — tell it what is running and have it re-rank.
