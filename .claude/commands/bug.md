---
description: Fix one defect end to end — reproduce, fix, verify independently, commit locally. Never pushes.
---

# /bug — fix one defect, with the loop that catches what a diff read misses

`$ARGUMENTS` is the issue number, or a description if there is no issue yet.

## Before dispatching anything

1. **Read the issue AND its comments.** Titles here lie and threads routinely invert
   them — #220 blamed a function that provably cannot raise; #212's own figures name
   a SHA one commit off. Never plan from a title.
2. **Read `BACKLOG.md`** for the standing verdict, then treat it as a cache, not evidence.
3. If the diagnosis in the issue does not match the code, **say so and stop.** Do not
   implement the wrong fix carefully.

## The loop

```
engineer  ->  qa (separate dispatch, own context)  ->  fix  ->  qa  ->  commit locally
```

**The engineer that wrote the code never verifies it.** That is the whole point — this
project has run fifteen QA passes and *every one failed its first submission*, twice on
defects the fix itself introduced. Collapsing the loop to save a round trip removes the
only thing that has been catching them.

Dispatch `architect` first when the change touches more than one module, changes a shape,
or when a ruling is needed before a constant is written. Dispatch `astro-auditor` before
writing any astrological or numerological constant.

## What the engineer's brief must carry

- The **verified** state of the code, with line numbers marked as drift-prone
- Any **correction to the issue** you have established, stated plainly
- The **gate** requirement — data, tables, dates and constants rot without one (#141, #146)
- What is explicitly **out of scope**, so scope creep is a decision and not a drift

## What QA must be asked to do

Reproduce the defect **first**, on the parent commit. Then confirm the fix. Then hunt for
what the fix broke. Then **write its own mutations** rather than trusting the engineer's.

## Non-negotiables

- **Nobody pushes.** Not the engineer, not QA, not you. Commit locally and hand back.
- No `skip`, no disabled test, no weakened assertion to get green.
- Comment on the issue when it lands locally; **close only with production evidence**.
- Every claim in a commit message must be something someone else can re-run.
