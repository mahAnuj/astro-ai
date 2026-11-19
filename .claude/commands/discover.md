---
description: Weekly discovery — seo-growth audits search and the funnels first, then product-manager specifies, reading the analyst's numbers, rivals and social. Files evidence-complete issues. Builds nothing.
---

# /discover — find the next thing worth building

Marketing's weekly loop. It produces **issues, not code**, and every issue it files must be
buildable the moment an engineer picks it up.

## Order matters: numbers before opinions

1. **The analyst's findings first.** The 6–20 band, CTR outliers, decay, and which of last month's
   ships actually moved. Starting anywhere else means specifying from intuition, and the objective
   is a measured one.
2. **Then rivals** — `WebFetch` on the pages that outrank us for a band
   query. A claim about a competitor needs a URL, not a recollection.
3. **Then social** — `WebSearch` across r/vedicastrology, r/astrology, Quora and X, for the
   questions people actually ask in their own words. Public search only; no scraping, no
   authenticated access.
4. **Then the corpus** — before specifying anything rule-shaped, check whether the rule is sourced.
   #177/#178 say the entire 36-point Ashtakoota engine is untraceable. Specifying a feature on an
   unsourced rule creates work Research will later ask to be removed.

## Step 1 — `seo-growth` first (since 2026-11-19)

**Dispatch both agents below; do not do their work yourself.** The run that reads this is the
coordinator. Measured on the 2026-11-17 run (Actions run 44005275102, `measurements/discover/2026-11-17.md`):
0 subagent calls in 17 turns, 2 minutes, every role done inline by the coordinator, which is why
`product-manager` showed 1 call in 30 days. A run whose log has no `seo-growth` dispatch did not
follow this file.

Search and the funnels are where users are won or lost, and until 2026-11-19 nobody owned them:
`product-manager` did keyword work as a side task, and `conversion-lead` was never called by
anything. So the run starts with `seo-growth`, in the FOREGROUND, and waits for it:

```
Agent(subagent_type="seo-growth", description="Weekly search and funnel audit",
      run_in_background=false,
      prompt="""Audit search and the funnels for <cwd>, against OBJECTIVE.md, following
.claude/agents/seo-growth.md. The numbers are already fetched: /tmp/gsc-band.json, /tmp/ga4.json,
measurements/latest.md and the measurements/gsc-trend-*.json and ga4-events.json files. File one
evidence-complete issue per finding (search open issues first). Return your findings in priority
order, one line each. Read-only on code. You never push.""")
```

## Step 2 — `product-manager` specifies

```
Agent(subagent_type="product-manager", description="Weekly discovery",
      run_in_background=false,
      prompt="""Lead discovery for <cwd>, against the objective in OBJECTIVE.md.

Start from seo-growth's findings (passed below) and the analyst's latest report
(measurements/latest.md), then rivals, then social, then the corpus. seo-growth has already filed
the search and funnel issues: do not re-file them; specify the ones that need a spec, and do the
rival and social work it did not.

File an issue ONLY if it carries a complete Evidence Block — gsc/ga4 with an explicit window,
competing with a URL, keyword, corpus with a line range or [UNSOURCED], measured tokens, an
executable repro, a thesis, and the metric that will judge it. An issue missing a field is not
filed. Cap at 30 per cycle.

Say when something should NOT be built. A feature whose per-request input exceeds the free Groq
TPM budget is unbuildable as specified — say so and propose the cheaper shape.

Read-only on code. You never push.""")
```

## The bar for filing

Acceptance criteria in `growth-manager`'s style — *"renders under 1s at p50 on the deployed
revision"*, never *"is fast"*.

`[UNSOURCED]` in the `corpus:` field is a valid answer. It routes the issue to the corpus loop and
blocks delivery until a source exists — which is correct, and far cheaper than building on it and
unbuilding later.

## Non-negotiables

- **Every issue carries a traffic thesis and the metric that will judge it.** The analyst scores it
  in 28 days; a thesis with no falsifiable metric is an opinion wearing a number.
- **Measured tokens, never estimated.**
- **A competitor claim needs a fetchable URL.**
- **Thirty issues a cycle, maximum.** The constraint is how many carry complete evidence, not how
  many can be written.
- **Files nothing it cannot justify from this cycle's data.** No carrying forward last month's hunch.
- **Builds nothing. Closes nothing. Never pushes.**
