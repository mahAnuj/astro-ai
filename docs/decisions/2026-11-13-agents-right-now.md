# /admin/ops shows what each agent is doing now, on a light background, and serves it as JSON

- **Date:** 2026-11-13
- **PR / issue:** this PR (owner's request in a session: live agent status on the ops dashboard and on anujmahajan.com/agent-cycle, and "make ops page - light background")

## Why, measured

The page answered "how is the loop doing over 7-30 days" and nothing answered "what is each
agent doing right now": a running build cycle, a QA round, a PR held for chief or failed in QA
were only visible by opening GitHub. `agent_status.py` builds eight cards (developer, QA,
merge, chief, steward, analyst, discover, prioritise), each with one state from a closed list
(building, running, queued, blocked, waiting, done, failed, idle).

**Cost: 3 GitHub reads per refresh** (runs in progress, runs queued, open PRs with labels),
cached 60 s with `OPS_GH_TOKEN` and 300 s without, behind one lock with a re-check (the #450
pattern), so at most 36 reads an hour unauthenticated however many renders or JSON callers.
**Rejected:** reading each workflow's last run from the API (one request per agent, about 8
more per refresh, against the same 60/hour budget `ops_today` already measured at its ceiling);
the last run comes from the committed `agents.json` instead. Measured against the live repo
2026-11-13: all eight cards filled, and it showed a real failure (`agent-prioritise` failed
2026-11-11, also issue #936). 0 LLM tokens.

`/api/agents/status` is public and CORS-scoped to anujmahajan.com: it carries only what GitHub
already shows for a public repository. Measurement PRs (`measurements/*`) are left out of the
QA and merge cards because they self-merge without a verdict.

**Light background:** the owner's request. The tokens are redefined once at the end of the
page's style block, plus the few rules that carried dark-only hexes; status colours were
darkened to clear AA as text on white (shipped 5.3:1, open 5.6:1, failed 6.3:1, judged 5.8:1,
ink-mute 5.4:1). `verify_contrast` does not scan this page, so these are stated here.
