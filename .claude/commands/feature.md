---
description: Build one specified feature — spec, design, subtasks, implement, verify independently. Never pushes.
---

# /feature — build one thing, shaped before it is written

`$ARGUMENTS` is the issue number or the request.

## The loop

```
product-manager  ->  architect  ->  engineer(s)  ->  qa  ->  commit locally
```

Skip `product-manager` only when the issue already carries a user story, checkable
acceptance criteria and a success metric. Skip `architect` only when the change is one
file and one function — and be honest about that, because "it's simple" is how a +33%
performance regression shipped in #150 and had to be re-factored out afterwards.

## What each stage owes

**`product-manager`** — a spec whose acceptance criteria are checkable, not aspirational.
"Renders in under 1s at p50 on the deployed revision", never "is fast". And the free-tier
answer: a feature whose per-day token cost exceeds what the chain can serve is not
expensive, it is **unbuildable as specified**.

**`architect`** — the shape, the rejected alternatives *with reasons*, and an **ordered
subtask breakdown**: file-and-function specific, each with a checkable done condition,
same-file work merged into one subtask, ordered by dependency then risk so the design
fails early and cheaply. State tokens per call and per day, GCS round-trips added, and
which cache layer is used with its key and TTL.

**`engineer`** — implements one subtask. Measures rather than estimates. Re-reads every
region immediately before editing, because `main.py` and `chart.py` are large and
concurrently edited.

**`qa`** — separate dispatch, own context, own mutations.

## Things this project has already paid for

- **Never put a per-request GCS read on a hot path.** #144 was a ~13-second homepage.
- **`storage.py` cannot list by prefix.** A design that assumes enumeration does not work.
- **`events.py` retention is 30 days.** Longer history needs its own aggregates.
- **New long-form content goes through the `/learn` pattern** — a parallel page type
  cannibalises pages that already rank.
- **Astrological claims must trace to `knowledge/*.md`.** If a rule cannot be sourced,
  mark it `[UNSOURCED — widely cited, not in corpus]` rather than inventing a citation.
- **Regional variation is legitimate** — state which convention a page uses.

## Non-negotiables

- **Nobody pushes.** Commit locally and hand back.
- `ARCHITECTURE.md` is updated **in the same commit** as the change it describes.
- A verification gate for anything data-shaped, and **mutate it to prove it goes red**.
