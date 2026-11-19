# Architect plans every build change; the team is renamed and pruned to the roles the loop runs

- **Date:** 2026-11-19
- **PR / issue:** this PR (owner request in session); measurements from #1238

## Why, measured

The owner, 2026-11-19: *"ideally every change should first go through architect, which know about
all the changes going in the repo and it should help in breaking the implementation in steps or
guiding the engineer on how to properly handle it and then engineer follows that path"*, then
*"yes with all of it"* to the restructure below.

Measured from 365 `agent-work` job logs over 30 days (the `agents_called` collector, #1238):
`qa` 211 runs, `project-manager` 164, `engineer` 74, `frontend-engineer` 19, **`architect` 6**,
`astro-auditor` 4, `numerologist` 1, **`product-manager` 1**. `conversion-lead` and `qa-lead` were
called by no workflow and no cycle at all. The Monday discovery run (Actions run 44005275102)
made **0** subagent dispatches in 17 turns: its coordinator did product-manager's work inline.

Decided:

1. **`architect` on every build, before any engineer.** It reads what else is changing on the same
   files, names the established pattern, checks robustness, reliability, scalability, security and
   maintainability, and returns ordered steps the engineer follows and QA checks against. A
   one-file change gets a short plan, never none.
2. **`product-manager` first on a feature without a spec**; bugs skip it.
3. **`astro-auditor` / `numerologist` first on any rule-file change**, named by path.
4. **`engineer` → `backend-engineer`**, so the build team reads as backend + frontend;
   `dev-lead.md` no longer sends every change to "engineer".
5. **`conversion-lead` → `seo-growth`**, owning search and the funnels, dispatched as Step 1 of
   `/discover` every Monday (no new workflow: a new job fails `verify_workflow_permissions.py`
   closed, and discovery already holds the GSC and GA4 data it needs). The discover prompt now
   requires the dispatches.
6. **`qa-lead` removed**; its routing table folded into `qa.md`. Its rows named skills that are
   not installed in this repo.
7. **`infra-lead` → `infra-reviewer`**: it reviews and files, it never writes code.

Rejected: a separate weekly SEO workflow (new permissions, owner's act #3, for data discovery
already fetches); keeping the architect conditional with a stricter threshold (the owner asked for
every change, and a threshold is what produced 6 of 365).

Cost: one architect dispatch per build cycle on the shared Claude Max subscription. #1238 records
every call, so the first week measures it; if it binds, the short-plan path is the lever, not
skipping the architect.
