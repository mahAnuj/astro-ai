# A merge-starved PR behind the owner's ruled agent-merge fix is not an obliged action

- **Date:** 2026-11-25
- **PR / issue:** #1387

## Why, measured

2026-11-25: `scripts/detect_stalls.py` printed `OBLIGED_ACTIONS=4` for five `mergeable-but-open`
PRs (#1438, #1428, #1405, #1375, #1342). #1405 is the owner's own fix to `agent-merge.yml`
(owner-authored, `qa-pass`, its diff includes `.github/workflows/agent-merge.yml`) and was already excluded by
`agent_pushable`. The other four obliged a dispatch nobody can perform: the gate is a workflow
file, the App token is refused on those, and chief had already ruled the cause on #1352
(option 1, irreducible act #1, merging that PR). So `agent-steward.yml` woke chief on every run
to rule a ruled thing.

Now a `mergeable-but-open` stall becomes `merge-starved-owner-blocked` when a DIFFERENT open PR
is (a) authored by the repo owner (`REPO.split("/")[0]` against the API `author.login`),
(b) touches `.github/workflows/agent-merge.yml`, and (c) carries `qa-pass`. The kind is still
printed and is in neither `OBLIGED_PUSH_KINDS` nor `OBLIGED_RULING_KINDS`. After the change,
the same command printed `OBLIGED_ACTIONS=0` with the four starved PRs under the new kind and
#1405 itself still `mergeable-but-open`.

- No title, body or comment is read, so nothing an author writes can suppress a wake.
- It expires on its own: only while the fix PR is open. A `mergeable-but-open` left after it
  merges obliges again, so a new misread still wakes chief.
- It fails open: any `gh` error, missing key or bad JSON returns None (not suppressed).
- Cost: one `gh pr list --author <owner> --json number,author,labels,files`, lazily, at most once
  per run and only when a `mergeable-but-open` exists. 0 LLM tokens.

Residual risk, accepted: while a trusted fix PR is open, an unrelated gate misread also shows as
the new kind. It is still printed with the fix PR's number, and the owner's act is the same.

Rejected: a chief-comment marker on #1352 (per-defect, manual, never expires, so it hides later
misreads); collapsing N PRs into one stall (still wakes chief once for a ruled cause);
suppressing on failed `agent-merge` sweep runs (needs Actions API reads, which the agent token
403s on, #323); editing `agent-steward.yml` or `agent-merge.yml` (owner act #1); adding
`mergeable-but-open` to the `agent_pushable` filter (hides real gate defects on any workflow PR).

Not determined: whether #1405 actually ends the starvation. If it merges and the stall persists,
the detector obliges again, which is the intended behaviour.
