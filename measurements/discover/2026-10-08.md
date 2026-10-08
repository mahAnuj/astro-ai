# /discover — 2026-10-08

Window for all numbers: GSC and GA4, 2026-09-08 → 2026-10-05 (the last 3 days are excluded because the data is not final).

**Filed: 1 issue (#276). Held back: 5 ideas, listed below with reasons.** The cap is 30. Only one idea carried a complete Evidence Block that this cycle's data supports.

## Inputs, and what was missing

| Input | State |
|---|---|
| `/tmp/gsc-band.json` | Read. 61 queries in positions 6–20. |
| `/tmp/ga4.json` | Read. About 70 landing rows. |
| `/tmp/measure/report.md` | **Absent.** No analyst report exists, so there are no scored theses to defer to. I leaned on #272, the analyst's 2026-10-07 issue, for the measurement limits. |
| Rivals (WebFetch) | astromedha.in and satyori.com fetched. shubhagya.com fetched, but the response had no `<title>` or meta tags. |
| Social (WebSearch) | **Produced nothing usable.** `reddit.com` is rejected by the search tool (400). The unfiltered Quora-targeted query returned no Quora pages. Treat every social-intent claim as unmeasured this cycle. |
| Corpus | **Not measured.** `scripts/corpus_search.py` fails because `pdftotext` is not installed. `data/` holds 1 of 7 books (`vedic_astro_textbook.pdf`). Any absence measured here would be worthless, so I made none. |

## What the numbers show

- **The band is almost one topic.** Of the 61 band queries, the "rahu mahadasha ketu antardasha" phrasing family dominates:
  - The head query has 157 impressions, 4 clicks and CTR 2.55% at position 9.6.
  - About 170 more impressions spread over 11 variants, all with 0–1 clicks, at positions 8.6–9.9.
  - Every band query is ≤157 impressions over 28 days, so the whole band is tiny.
- **Manglik definitional queries are the second cluster.** `what is manglik dosh`, `manglik dosh in english`, `manglik dosh means`, `manglik means` and `manglik status means` total about 60 impressions at positions 6.8–10.2, with 0 clicks.
- **`/learn/rahu-mahadasha-ketu-antardasha/` has 29 sessions and pages/session of exactly 1.0.** It is the largest non-homepage landing. The next `/learn/` page has 10 sessions.
  - Its GA4 sessions (29) are far above the family's GSC clicks (about 6). At least 23 sessions came from somewhere the exports cannot name (#272).
  - The `/?fbclid=` rows show Meta traffic exists.
- **The Rahu–Ketu page's metadata is still unshipped.** The registry's `seo_title` and `seo_description` for this slug are empty (38 of 76 articles are in that state). That is #267 work item 1, so it is already specified and still open.

## Filed

### #276 — [CONVERSION] Top /learn landing sends 0 of 29 sessions onward

- **Finding:** the page has a `/dasha` callout at line 87 of 120, after six of its eight sections. No session went on to a second page.
- **Rivals:** neither rival gives the visitor their own start date. astromedha.in has no timing tool and upsells a ₹599 report. satyori.com has no calculator.
- **Thesis:** a "find your Ketu antardasha dates" CTA before the second `<h2>` turns some of the 0-of-29 into onward visits.
- **Metric:** GA4 pages/session for that landing in the next 28 days. ≥1.20 passes, 1.0 means the thesis is false, and under 20 sessions is inconclusive.
- **Limits stated in the issue:**
  - Traffic source is unknown (#272), so the sessions may not be organic.
  - n = 29, so the 1.20 bar is a pre-registered threshold, not a significance test.
  - It must not ship alongside the #267 title/description change, or the read is confounded.
  - The corpus field says n/a because the issue adds no rule. The page's existing 10.5-year arithmetic was not re-audited, because the corpus was unavailable.
- **Correction:** I mis-described the callout's position in the first draft of the issue body and fixed it with `gh issue edit` straight after filing.

## Considered and NOT filed

1. **Title and description for the Rahu–Ketu page and the other 37 articles with no `seo_title`.** This duplicates #267 work item 1, which is open and unshipped. It is the best-supported lever in the data, since the head query has CTR 2.55% at position 9.6. The next step is to ship #267's item, not to file a new issue. I did not comment on #267, to keep this run's outward writes to one issue.
2. **A Manglik "what is it" definition lead.** `manglik-dosh` already opens with an "In short" callout that defines the term, and its `seo_title` already contains "What It Means". The page is optimised for these queries, and the position has not moved. GSC has no page dimension, so I cannot confirm that this page is the one ranking. At about 60 impressions and 0 clicks, the expected gain is about 1 click. Re-raise only if #272's page dimension shows a different URL ranking.
3. **A new article for `rahu dasha with sun mahadasha and job` (32 impressions, position 9.3).** #267 holds new articles until 2026-12-19 because supply is not the constraint. I also cannot tell which existing page ranks for this query.
4. **The `bhagya score`, `bhagya chart` and `bhagya astrology` queries (8–9 impressions each).** These look like brand or navigational queries, and the data is too thin to justify anything.
5. **The Hindi, Arabic and single-impression noise queries.** These are `एच कैलेंडर`, `نعم`, `ha`, `job` and `tell me more`. They are not actionable. The Hindi surface belongs to #124.

## Should NOT be built

Nothing was specified that touches the Groq budget. #276 uses 0 tokens, and I added no LLM feature.

## For the next run

- **Ship #267 work item 1 first.** Until then every band query on the Rahu–Ketu family is stuck at the fallback metadata, and any other Rahu page change is confounded.
- **#272 has to land** (a GSC page dimension and a GA4 channel dimension). Without them, "which page ranks for this band query" and "are these sessions organic" cannot be answered, and I could only reason by topic.
- **Fix the sandbox before the next corpus-dependent discovery.** Install `pdftotext` and fetch the missing books. Right now any rule-shaped issue would have to be filed as `[UNSOURCED]` by default.
- **Social needs another route.** Reddit is blocked for the search tool. Quora and X returned nothing through unfiltered queries.
