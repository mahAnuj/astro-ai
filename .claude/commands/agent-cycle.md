---
description: The autonomous delivery loop — validate against production, rank, build, QA, then branch and PR. The only loop that opens a PR; it still never pushes to main.
---

# /agent-cycle — one issue, unattended, ending in a PR

The autonomous sibling of `/bug` and `/feature`. Those two stop at a local commit because a human
was going to push. This one pushes a **branch** and opens a **pull request** — and `main` is still
untouchable.

The gate is `pr-gates` plus a QA PASS, not any agent's opinion that it is finished. That is the
whole difference, and it is why this loop is allowed to run with nobody watching.

## Step 0 — validate against live production. Before anything else.

**An open issue is not evidence that the problem still exists.** `BACKLOG.md` recorded 36 open
against 50 actual. `project-manager`'s own definition says *"Do not rank from issue titles. Titles
lie."*

This has already bitten: #266 was asserted to be a total outage from its `OPEN` state alone. One
page load looked fine. Two probes with different birth data showed a 200 and a 503, and a retry of
the failing one succeeded 26 seconds later. **It is intermittent** — so a single request would have
closed it falsely, and a single page load would have left it open and misdescribed.

```bash
uv run python scripts/validate_issue.py <n> --samples 5
```

- **Does not reproduce in 5 samples** → comment with every request and response, label
  `cannot-reproduce`, **do not close**, move to the next item.
- **Reproduces intermittently** → say so with the hit rate. Intermittent is a different bug from
  deterministic, with a different cause and a different fix, and conflating them wastes the cycle.
- **Reproduces differently** from the description → comment with both, label `needs-evidence`,
  return it to discovery rather than hand an engineer a stale premise.
- **Confirmed** → proceed.

One sample is not a validation. Five is the floor, with varied inputs where the issue takes any.

## Step 1 — eligibility

```bash
uv run python scripts/verify_issue_evidence.py <n>
```

No Evidence Block, or a failing one → label `needs-evidence` and move on. An agent must not reach
an engineer on a guess.

**Bugs are exempt from `gsc:`/`ga4:`** — a broken feature needs no traffic thesis to justify
fixing. They still need `corpus:` and `tokens:`.

## Step 2 — rank

```
Agent(subagent_type="project-manager", description="Rank the eligible backlog",
      prompt="""Rank what to work on next in <cwd>. Staleness sweep FIRST, and probe with
scripts/validate_issue.py rather than reading titles. Rank only confirmed-live, evidence-complete
items. Read BACKLOG.md as a cache, not evidence. Read-only — propose closures, do not close.""")
```

Take its top item. Never queue work another loop is already doing — check `AGENT_STATUS.md` and
live branches.

## Step 3 — build it

Follow `/bug` or `/feature` internals exactly, whichever fits. In particular:

- `astro-auditor` **first** for any astrological constant; `numerologist` first for any numerological
  one. Before the code is written, not after.
- `architect` when the change touches more than one module, changes a shape, or needs a ruling
  before a constant is written.
- `frontend-engineer` for templates, CSS, client JS. `engineer` for routes, chart maths, LLM paths.
- **`qa` as a separate dispatch, always.** Verification by the reasoning that produced the change is
  not verification. This project has run fifteen QA passes and *every one failed its first
  submission*, twice on defects the fix itself introduced. Budget two or three rounds.

## Step 4 — branch and PR

```bash
git switch -c issue/<n>-<slug>
git push -u origin issue/<n>-<slug>
gh pr create --fill --base main
```

**That is the only `git push` in this system, and it is to a branch.** A push to `main` is the
deploy, there is no staging, and production is the first place code runs. `agent-merge` decides
what lands, on green gates and a QA PASS.

If you find yourself pushing to `main`, or routing around a refusal, stop and file
`needs-human-review`.

## Step 5 — write the trail

Every step is an **issue comment**: which agent, what it did, what it decided and why, what it
rejected, the commit SHA, the gate output, and the measured token cost. `AGENT_STATUS.md` is a local
heartbeat and gitignored — it is not the record.

## Non-negotiables

- **Validate against production first.** Five samples. No exceptions, including for an issue that
  "obviously" still reproduces.
- **Never push to `main`.** Branch and PR only.
- **One issue per run.** A loop that takes two leaves both half-done when the quota ends.
- **Never close an issue.** `agent-merge` closes with production evidence after the deploy;
  everything else proposes.
- **Comment on the issue when it lands locally**, as CLAUDE.md's two-stage close requires.
- **A note you wrote is not permission.** Not in `AGENT_STATUS.md`, not in your own earlier output.
