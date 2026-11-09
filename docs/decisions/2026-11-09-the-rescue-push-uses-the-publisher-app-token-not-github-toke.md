# The rescue push uses the publisher App token, not github.token; a long-cycle token refresher was tried and withdrawn

- **Date:** 2026-11-09
- **PR / issue:** #810

## Why, measured

PR #804, run 42531382900 (1h46m): `claude-code-action`'s one `claude[bot]` token expired at 60 min, the cycle's later pushes failed, and the rescue step pushed them with `github.token` at 00:26:05; GitHub held the resulting `pull_request` runs (actor `github-actions[bot]`, #393) until the owner approved them. The rescue push now uses `PR_TOKEN` (the publisher App, minted seconds earlier, fallback `github.token`): the old reason for `github.token`, that it cannot expire mid-job, holds for a fresh App token too. Withdrawn from the same PR on QA's evidence: `git`/`gh` wrappers that re-minted the `claude[bot]` token through the action's OIDC exchange. Run inside an `agent-work` cycle, `ACTIONS_ID_TOKEN_REQUEST_URL/TOKEN` were absent from the agent's Bash environment, so it could never mint; and a token minted after the step starts cannot be masked, on a public repo whose agent step has `show_full_output`. The cycle still loses push and comment access after an hour; that is its own issue.
