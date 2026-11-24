# chief_clear judges the latest `gates` run, not every run joined together

- **Date:** 2026-11-24
- **PR / issue:** #1442

## Why, measured

`scripts/chief_clear.py` read every `gates` check run on the head and required each to be
`success`. PR #1428, head `c2621f7cf2bebc77bc2440958e2a08f66ef7bd36`, had `gates` run
138216580157 `failure` (started 2026-11-24T04:25:30Z) and run 138219560717 `success`
(started 04:33:27Z). The latest run was green and chief's clearance was refused anyway,
because the superseded failure was still in the list.

The check now takes the single run with the greatest `(started_at, id)` and requires
`status == completed` and `conclusion == success`. A null `started_at` (a queued re-run)
sorts last, so a pending re-run over an older green refuses. Empty output, malformed JSON,
a line with no `id` and an API error all refuse. The request is `--paginate` with
`per_page=100&filter=all`, one JSON object per run.

Replayed against the real #1428 head with `gh api`, `filter=all` and the default filter
returned the same two runs, so `filter=all` is not needed for that case. It is kept
because it lists every run rather than leaving "latest" to GitHub's per-suite rule, and we
pick the latest ourselves.

Rejected: "ignore failures" and "any success". Both would clear a head whose latest run is
red. A `failure` then `success` pair clears; `success` then `failure` refuses
(`tests/test_chief_clear.py`, mutation rows in
`scripts/mutations/2026_11_24_1442_chief_clear_latest_gates.py`).

`.claude/agents/chief.md` precondition 2 says "`pr-gates` green on the head commit" and is
unchanged: it never said "every run".
