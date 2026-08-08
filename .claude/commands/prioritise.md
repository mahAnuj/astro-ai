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

Read the issues, the git and deploy state, and AGENT_STATUS.md before ranking. Never queue work another loop is already doing. Read-only — propose closures, do not close.

<args>
"""
)
```

If the user named a focus (`/prioritise correctness`, `/prioritise mobile`), pass it through and rank within that slice, but still run the staleness sweep across everything — stale issues in other areas are still worth surfacing.

## Notes

- Do not rank the backlog yourself in the main conversation. Reading 49 issues with comments is exactly the context load this agent exists to keep out of here.
- The agent proposes closures; **the human closes**. Relay its stale list and ask.
- If it returns a queue whose top item is already in flight, that is a bug in its input — tell it what is running and have it re-rank.
