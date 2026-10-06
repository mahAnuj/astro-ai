# The teams

Eight teams, three levels. Every one of them ladders to the single line in `OBJECTIVE.md`:
**move the 6–20 position band into the top 5 on the ten highest-impression queries** — which is to
say, more users.

A team's remit is what it owns. Its **goal** is the number it is judged on. They are not the same
thing, and a team optimising its remit instead of its goal is the failure this file exists to
prevent.

| Team | Lead | Owns | Judged on | Cadence |
|---|---|---|---|---|
| **Analytics** | `analyst` | GA4, GSC, scoring every ship | Were the misses reported as plainly as the hits | daily |
| **Marketing** | `growth-manager` | SEO, keywords, competitors, social, content | Did the queries it picked actually move | weekly |
| **Sales** | `conversion-lead` | The five funnels, retention, readiness to monetise | Step-through on the worst funnel step | weekly |
| **Backend** | `engineer` | Routes, chart engine, LLM paths, storage | Merged work that moved its metric, no ranking regression | daily |
| **Frontend** | `frontend-engineer` | Templates, CSS, client JS, service worker | Same — plus nothing broke silently | daily |
| **Design** | `ui-designer` skill | Visual direction, signature moments, mobile | CTR at unchanged position | weekly |
| **Research** | `astrologer` · `numerologist` | Corpus, citations, authenticity | Unsourced claims left on user-facing pages | weekly |
| **IT** | `infra-lead` | Cloud Run, GCS, free tiers, deploys, latency | Headroom at 10x, and deploy proof that proves something | weekly |
| — | **`chief`** | Ties, the objective, the lineage table | Nothing. It produces only when escalated to. | on escalation |

Supporting roles sit inside teams and are dispatched by them: `architect` and `qa` serve Backend and
Frontend; `product-manager` serves Marketing; `project-manager` ranks the whole backlog for
Engineering. `qa` is always a separate dispatch — *verification by the same reasoning that produced
the change is not verification*.

## How a team's work reaches a user

```
  Analytics finds the band           ──┐
  Marketing picks winnable queries   ──┤
  Sales finds the step losing people ──┼──▶  issue with a complete Evidence Block
  IT finds the ceiling it will hit   ──┤      (gsc/ga4 · competing · corpus · tokens
  Research supplies the source       ──┘       · repro · thesis · metric)
                                                        │
                                   project-manager ranks ▼ (refuses an unevidenced issue)
                                                        │
                    Backend / Frontend / Design build it ▼ → qa → PR → pr-gates → auto-merge
                                                        │
                                   Analytics scores it  ▼ against the thesis it claimed
                                                        │
                                              /sync      ▼ reconciles, escalates, closes the loop
```

No team ships straight to a user. **Every path goes through an Evidence Block, a QA dispatch and a
gate** — including Design's, because this is where change breaks silently.

## Escalation

A disagreement two teams cannot settle goes to `chief` with **both positions verbatim**. Most are
already answered by the standing rulings — the objective, the canonical lineage table,
authenticity-versus-traffic — so quote the clause before escalating. Three escalations a cycle; a
fourth files `needs-human-review` and stops.

Deadlock is information. Resolving it harder is how a guess becomes a decision.

## What keeps eight teams from pulling apart

1. **One objective**, in `OBJECTIVE.md`, rewritten at most once a quarter and only from measured
   data.
2. **Anti-goals per team**, also in `OBJECTIVE.md` — the local optimum each one would otherwise
   reach. Filing more issues, merging more PRs and redesigning more pages are all ways to look
   productive while the band does not move.
3. **`/sync`**, which is the only place the loops see each other. It must end in decisions,
   escalations or closures — never a summary.
4. **The issue trail.** Every action and decision is an issue comment. `AGENT_STATUS.md` is a local
   heartbeat and gitignored; `BACKLOG.md` is a cache that has run six weeks stale. Neither is
   evidence.

## Cadence and why it is uneven

Daily: Analytics, Backend, Frontend. Weekly: everything else. `chief` never runs on a schedule.

This is a quota decision, not a judgment about importance. The agents run on a Claude subscription
with a five-hour rolling cap that this machine has already hit once — `com.vivatrades.stock-analysis.plist`
was moved from 02:00 to 04:30 for exactly that reason. Eight teams running daily would spend the
budget on coordination rather than work, and the first casualty is a cycle dying mid-run and
leaving a half-finished branch.
