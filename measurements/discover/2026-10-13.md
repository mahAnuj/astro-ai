# /discover report — 2026-10-13

**Filed 1 issue: #329.** Everything else I considered is under "Not filed" below, with the reason.

## Inputs and their limits

- Read first, as instructed: `/tmp/gsc-band.json`, `/tmp/ga4.json`, `/tmp/measure/report.md` (analyst, 2026-10-12), then `OBJECTIVE.md`.
- **The fetched files are one day newer than the analyst's.**
  - Fetched files: window 2026-09-13 → 2026-10-10. Analyst's: 2026-09-12 → 2026-10-09. The two overlap by 27 of 28 days, so I did not read the difference as movement.
  - `/tmp/measure/gsc-all.json` is the older window. I used it only for pages outside the band.
- **The data is page-level, not query-level.** The "queries at positions 6-20" file is `dimension: page`: 99 rows, 8,012 impressions, 82% of the property's 9,765. OBJECTIVE.md's "ten highest-impression queries" cannot be scored literally. This is already tracked in #272 and #291, and I added nothing.
- **Sample size is tiny.** 103 clicks and 278 sessions in 28 days. Most per-page claims below are directional only.
- **Social search returned no Reddit or Quora threads.**
  - I ran three public WebSearches (r/vedicastrology-style queries for Rahu-Ketu timing and Sade Sati start). All results were astrology sites.
  - So the "questions in their own words" step produced no social evidence. I did not invent any.
  - What those searches do show is rival content answering the same "when does it start / end" questions with a calculator link.
- **Corpus:** nothing I specified is rule-shaped, so there was nothing to check. #329 changes no astrological claim.

## What the numbers say this cycle

1. **`/learn/debilitated-sun-career/` left the band.** The analyst had 871 impressions at position 6.0. It is absent from the new band file, and band impressions fell from 8,830 to 8,012 (-818). That is roughly the page's own impressions.
   - **I cannot tell which direction it moved.** It could be position < 6 (a gain) or > 20 (a loss). The band file cannot say, and the new `gsc-all` was not fetched.
   - **Next step:** the analyst should check this page first next run. It is the only top-10 page whose status changed.
2. **The "backfill `seo_title`" premise from #267 is not supported by this window.** 38 of the 76 articles have an override. Of the 64 articles in the band file, I split them by that flag:

   | cohort | pages | impressions | clicks | CTR | weighted position |
   |---|--:|--:|--:|--:|--:|
   | with `seo_title` override | 33 | 4,670 | 39 | 0.84% | 7.02 |
   | without override | 31 | 3,009 | 43 | 1.43% | 7.39 |
   | without override, excluding `rahu-mahadasha-ketu-antardasha` | 30 | 1,448 | 15 | 1.04% | — |

   - The best-converting page on the site, `rahu-mahadasha-ketu-antardasha` (28 clicks), has **no override**. Its title is the card copy, "Surviving the Nodal Axis Flip".
   - All four pages #311 calls under-performing **do have** compliant overrides.
   - With the reference page excluded, the no-override cohort is 1.04% vs 0.84% for the override cohort. That difference is not significant: P(≥ 15 clicks) is about 0.24 at the override rate.
   - The honest reading is that this window gives **no evidence that a compliant override raises CTR**, and a little evidence against. Intent and topic are confounded.
3. **The funnel picture is unchanged from the analyst's.**
   - 188 `/learn` sessions, 62% single-page. The tracked pieces are #276 (CTA position), #304 (sticky CTA hidden) and #311 (titles).
   - The `/learn/sade-sati/` organic sessions are 7 at 1.00 pages/session. The article does link `/sade-sati-check` at line 43 of 121, so the tool is present and the gap is not a missing link.

## Filed

| # | title | why it passed the bar |
|---|---|---|
| **#329** | [CONVERSION] `/learn/manglik-dosh/` explains how to check Manglik status but never links the site's own checker | **Verified in the template and on production.** The article's section "How to check if you're Manglik" (line 30) has no link to `/manglik-check`. The closing "Janma Kundli generator" mention at line 126 has no href. Production's only two `manglik-check` matches on that page are the nav and footer. Competitor evidence is a fetched URL (dashaclub.com). Tokens are 0, because the checker has no LLM call. The metric has an explicit "inconclusive below 10 sessions" clause. |

**Weakness, stated plainly:** the traffic evidence for #329 is thin (5 landing sessions across channels, 419 impressions). I filed it because the defect is deterministic and checkable, the fix is a link, and it costs nothing in free-tier terms. The metric cannot settle it quickly if traffic stays this low.

## Not filed, and why

| idea | why not |
|---|---|
| **Blanket `seo_title`/`seo_description` backfill for the 38 articles without overrides** (#267's "one edit to one file") | The cohort comparison above does not support it. It would also confound #311's measurement. If anyone raises it again, the minimum is a per-query SERP check, not a bulk edit. |
| **Zero-click title tests** on `the-9-grahas-overview`, `shukra-venus`, `rahu-in-vedic-astrology`, `saturn-in-10th-house-career` | 97–109 impressions at position 6–8. At the band's own 0.92% rate the expected clicks are about 1, so 0 clicks is P ≈ 0.37, indistinguishable from noise. Filing a "title mismatch" on that would be an opinion with a number attached. |
| **`/festivals` at position 27.5** (344 impressions, 1 click) | The analyst flagged it as a product question. I could not pin down a rival or an executable repro this cycle. A WebSearch for October 2026 festival lists returned sources disagreeing on Dussehra, Sharad Purnima, Karwa Chauth and Diwali dates. That makes any festival-content claim a dates-verification task first, per CLAUDE.md, and no source could be recorded. Not filed, but a future cycle with a fetched competitor page and the new `gsc-all` could. |
| **A Sade Sati / Rahu-Ketu "calculator above the fold" CTA** | Already specified in #276 (Rahu-Ketu). Sade Sati already links its checker at line 43. n = 7. |
| **Query-level objective scoring** | Tracked in #272 and #291. |
| **Hindi `/hi/` surface** | Zero rows in GSC and GA4 (analyst, section 3). Nothing to specify until it gets impressions. #124 stands. |
| **Anything about tool funnels (kundli, matching, numerology)** | Landings total a handful of sessions and the export has no landing → form → result sequence. Cannot be measured, so cannot carry a metric. |
| **Home page (`/`) Direct traffic** | 53 of 64 sessions are Direct and unattributable. The analyst's open question, not a build. |
| **New `/learn` articles** | OBJECTIVE.md: optimise the band before publishing more, and nothing in this cycle's data argues otherwise. |

## Left open for the next cycle

- Where `debilitated-sun-career` went (above). Needs the new `gsc-all.json` or a query-level fetch.
- Whether any no-override article at position 6–8 has a per-query title mismatch. Needs the query dimension, which these exports lack.
- No competitor SERP was fetched for the top band pages (`rahu-mahadasha-career-problems`, `sade-sati`). The one search I ran for the first returned only astromedha.in pages and generic results, so I have no fetched comparison for it.

## Not done

- I did not run `competitor-scout`, `seo-auditor` or `keyword-researcher` skills; none was listed as available to me this session, so rivals came from WebSearch and WebFetch only.
- I did not comment on #311. Its thesis is the one the cohort table questions, and the analyst has already posted twice on it. The cohort table above is for whoever picks it up.
- Builds nothing, closes nothing, pushed nothing.
