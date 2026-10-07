---
description: Cross-team syncup — each lead reports from the issue trail, contradictions surface, deadlocks escalate to chief. Produces decisions, never a status essay.
---

# /sync — the syncup

Four loops run on their own schedules and cannot see each other. Analytics scores a page while
Growth files an issue to rewrite it; Research proves a rule unsourced while Engineering ships a
feature built on it. Nothing in the architecture notices. **This is where they find out.**

A syncup that produces a summary has failed. It must end in decisions, escalations, or closures.

## Before anything: this is read-from-evidence, not read-from-memory

Every team's state lives in GitHub issue comments — that is the audit trail, and it is the only
thing here that is durable. `AGENT_STATUS.md` is a local heartbeat and is gitignored; it is not
evidence. Neither is `BACKLOG.md`, which has run six weeks stale and recorded 36 open against 50
actual.

```bash
gh issue list --state open --limit 200 --json number,title,labels,updatedAt
gh issue list --state closed --limit 40 --json number,title,closedAt
git log origin/main --oneline --since="7 days ago"
gh run list --limit 20 --json workflowName,conclusion,createdAt
```

## The four reports

Gather these from the trail. Do not dispatch an agent to re-derive work it already recorded —
a syncup that re-runs every loop costs four cycles and learns nothing new.

1. **Analytics** — what moved, what did not, which closed issues were scored and what they scored.
   A thesis that missed is the most useful line in the whole sync.
2. **Growth** — what was filed this cycle, and whether each carries a complete Evidence Block.
3. **Research** — what was sourced into `knowledge/`, and what came back `UNSOURCED`. An
   `UNSOURCED` finding against a shipped user-facing claim is the highest-severity output any
   loop produces here.
4. **Engineering** — what merged, what is open, what `pr-gates` rejected and why.

## What you are actually looking for

Four failure modes, in descending cost:

- **A contradiction.** Research says a rule is unsourced; Growth has filed an issue to promote the
  feature built on it. These must not both proceed. → escalate.
- **Duplicated work.** Two issues, one root cause, two loops. → merge, note the survivor.
- **A broken chain.** An issue blocked on a corpus entry nobody is extracting, or on a gate nobody
  is writing. A chain blocked for two consecutive syncs is a planning defect, not a queue item.
- **A thesis that missed.** Shipped, scored, moved nothing. → say so, and say whether the *idea*
  was wrong or the *execution* was. They have opposite remedies and the distinction is routinely
  skipped.

## Escalation

A contradiction two leads cannot resolve goes to `chief` — **with both positions verbatim**, the
Evidence Block, and the issue number. A summary of a disagreement is not an escalation; it is your
opinion of one.

Most escalations are already answered by the standing rulings in `chief.md` — the quarter's
objective, the canonical lineage table, authenticity-versus-traffic. **Check those first and quote
the clause.** Escalating something already ruled on burns a cycle and one of the three escalations
this cycle is allowed.

## What the syncup writes

One comment per affected issue — not a document nobody reads. Then append one block to
`SYNC_LOG.md`:

```
## 2026-10-06 — sync
decisions:    #262 merged into #260 (same root cause, templates/learn)
escalated:    #177 → chief (Research: unsourced; Growth: promote it)
missed:       #124 shipped 09-20, organic to /hi/ +2% over 28d vs thesis +25% — execution, not idea
blocked 2x:   #201 waits on Chaldean registration in fetch_corpus.py — nobody assigned
carried:      4 issues unchanged
```

Short, scannable, and comparable week to week. A sync log that reads like minutes will not be read
by the next sync, which is the only reader it has.

## Non-negotiables

- **End in decisions.** Merges, escalations, proposed closures, or a named blocker with an owner.
  A sync producing only a summary is a meeting, and this project cannot afford meetings.
- **Never close an issue.** Propose; the human closes. Comment with the evidence.
- **Nobody pushes.** A sync writes comments and `SYNC_LOG.md`. It does not touch code.
- **Carry the deadlock forward.** An item blocked at two consecutive syncs files a
  `needs-human-review` issue. Three syncs of "still blocked" is the loop failing quietly, which is
  exactly how `GROWTH_LOG.md` stopped after four cycles and nobody noticed for ten weeks.
