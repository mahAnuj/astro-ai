# chief_clear accepts the QA PASS authors agent-merge accepts, and pages its comment reads

- **Date:** 2026-11-28
- **PR / issue:** #1287

## Why, measured

`scripts/chief_clear.py` took a `QA: PASS` verdict only from `claude[bot]`, while the merge
gate in `agent-merge.yml` takes it from `claude[bot]` or the repo owner (a top-level session
records its verdict as the owner). An owner-authored PASS the merge gate would accept was
refused by the clearance carrier. Its comment reads also had no `--paginate`, so on a PR with
more than 100 comments the ruling or the verdict past the 100th read as missing.

Decided: the PASS author set is now `claude[bot]` plus the repo owner (`qa_authors(repo)`),
the same set `agent-merge` uses. The ruling comment (`chief-cleared at <sha>`) stays
`claude[bot]` only, so no authority widened: the owner could already clear a hold by hand, and
the verdict is still bound to the head sha. The reads now emit one comment id per match and
count lines, as `agent-merge` does, because `--paginate` runs `--jq` per page and a trailing
`length` printed one number per page. Anything but a digit-only line is not counted, so odd
output still refuses. Rejected: widening the ruling authors too (it is chief's act, and
`agent-merge` re-checks `claude[bot]` on that string).

No LLM call is added or changed: 0 tokens.
