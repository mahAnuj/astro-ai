# New decisions go in `docs/decisions/`, one file per decision; `ARCHITECTURE.md` §10 is frozen

- **Date:** 2026-11-09
- **PR / issue:** this PR

## Why, measured

On 2026-11-09, #809, #810, #811, #812 and #804 each went `mergeable_state: dirty` on
`ARCHITECTURE.md` alone, every time another PR merged, because each had appended a row to
the §10 decision table at the same place. Each conflict cost a `main` merge by hand and, for a
QA-passed PR, a fresh QA round on the new head (since 2026-11-05 a `QA: PASS` counts only for
the SHA it names). `scripts/merge_main_into_branch.py` already resolves this file mechanically
(`resolve_union_dated`), but GitHub still marks the PR conflicting until someone runs it.

Owner: *"I think we need to make PRs without the requirement to update a common file at one
place that could lead to conflicts."*

Same shape as `scripts/mutations/` (2026-11-03): one file per entry, so two PRs never edit
the same file.

**Rejected:** moving the 142 existing rows into files now. That diff would conflict with every
open PR that adds a 2026-11-09 row, which is the problem being solved. The table is frozen as
history instead; rows dated on or before 2026-11-09 are still accepted, so in-flight PRs merge
unchanged.

**Enforced by** `tests/test_decision_log_frozen.py`: a §10 row dated after 2026-11-09 fails,
and every file here must be `YYYY-MM-DD-<slug>.md` with a `# ` title and a `**Date:**` line
matching its name.
