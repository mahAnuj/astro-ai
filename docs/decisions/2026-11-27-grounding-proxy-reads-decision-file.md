# The grounding proxy also accepts a citation in the change's own decision file

- **Date:** 2026-11-27
- **PR / issue:** #1478

## Why, measured

`check_grounding_proxy` (`scripts/pre_qa_check.py`, #1255) failed a claim-bearing diff unless a
commit since the merge base carried a `corpus:` line. A squash merge drops commit-message lines,
so the only durable place a change records its source is the decision file. Replayed over
the 21 merged changes sampled for #1478, the proxy failed 2: `6906d32` (Vivah lagna windows,
#1455) and `59d9134` (#1430, empty 7th house). `6906d32`'s decision file cites
`knowledge/grahas.md` section 12.5 and `knowledge/vedic_reference.md` section 4.7 and has no
`corpus:` line anywhere, so the proxy cried wolf on a change that had written its source down.
`59d9134` has no decision file and no `corpus:` line; it still fails, correctly.

**The rule now:** the proxy passes when any ADDED line of any changed
`docs/decisions/*.md` (not `README.md`, not a subdirectory) starts with `corpus:` or names a
`knowledge/<file>.md`. The file merely existing never passes; removed lines never count.

## Rejected

- **`corpus:` line only, in the decision file** -- would not fix `6906d32`, which cites
  `knowledge/` paths.
- **Reading the PR's Evidence Block through `gh`** -- network access in a local fast check.
- **Editing the `.claude/` build prose** to ask for the line again -- a squash drops commit lines
  whatever the prose says.
- **Requiring a decision file for every claim-bearing diff** -- a change that edits a table
  constant has nothing to decide; `corpus: n/a -- why` exists for it.
- **Accepting mere presence of a decision file** -- a rubber stamp.
- **Parsing a section heading** -- brittle; decision files do not share one.

## Known limits

A negative mention ("not in `knowledge/x.md`") passes: the proxy cannot see negation. It is a
proxy, as its docstring says; `qa` and `verify_rule_citations` judge whether the claim is true.
`59d9134` still fails by design. Cost: 0 Groq tokens (a local check).
