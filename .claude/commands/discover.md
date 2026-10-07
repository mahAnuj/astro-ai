---
description: Weekly discovery — product-manager leads, reading the analyst's numbers first, then rivals and social. Files evidence-complete issues. Builds nothing.
---

# /discover — find the next thing worth building

Marketing's weekly loop. It produces **issues, not code**, and every issue it files must be
buildable the moment an engineer picks it up.

## Order matters: numbers before opinions

1. **The analyst's findings first.** The 6–20 band, CTR outliers, decay, and which of last month's
   ships actually moved. Starting anywhere else means specifying from intuition, and the objective
   is a measured one.
2. **Then rivals** — `competitor-scout`, and `WebFetch` on the pages that outrank us for a band
   query. A claim about a competitor needs a URL, not a recollection.
3. **Then social** — `WebSearch` across r/vedicastrology, r/astrology, Quora and X, for the
   questions people actually ask in their own words. Public search only; no scraping, no
   authenticated access.
4. **Then the corpus** — before specifying anything rule-shaped, check whether the rule is sourced.
   #177/#178 say the entire 36-point Ashtakoota engine is untraceable. Specifying a feature on an
   unsourced rule creates work Research will later ask to be removed.

```
Agent(subagent_type="product-manager", description="Weekly discovery",
      prompt="""Lead discovery for <cwd>, against the objective in OBJECTIVE.md.

Read the analyst's latest findings FIRST, then rivals, then social, then the corpus. Invoke the
seo-auditor, keyword-researcher and competitor-scout skills rather than re-deriving them.

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
