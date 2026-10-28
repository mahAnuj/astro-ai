# /discover report — 2026-10-26

**Filed 1 issue: #553.** It passes `scripts/verify_issue_evidence.py` (PASS, 0 problems). Everything else I considered is under "Not filed", with the reason.

## Inputs and their limits

- **Read first, as instructed:** `/tmp/gsc-band.json`, `/tmp/ga4.json`, then `OBJECTIVE.md`, the prior `/discover` report (2026-10-13), and open issues.
- **`/tmp/measure/report.md` does not exist** in this run. I used the analyst's 2026-10-25 report from the repo, `measurements/latest.md`, instead. Its window is 09-25 → 10-22. The fetched files cover **2026-09-26 → 2026-10-23**, one day later. The windows overlap by 27 of 28 days, so I read no movement into the difference.
- **The data is page-level, not query-level.** The file is named "queries at positions 6-20" but is `dimension: page`: 102 rows, 10,636 impressions (89% of the property's 11,995). No query strings exist, so every `keyword:` field is a page-level inference, not a measured query. This is already tracked in #272 and #291, and the analyst's report says the objective's "ten highest-impression queries" cannot be scored. I added nothing to that.
- **Sample size is tiny.** 125 clicks and 390 sessions in 28 days. Most per-page figures are 3–12 sessions.
- **Social search returned no Reddit or Quora threads, again.** I ran three public WebSearches (debilitated Sun and career, Sade Sati ending and career, and a Quora-targeted query). All results were astrology commercial sites or blogs, and the tool itself said so. I invented no social evidence. Two consecutive cycles now return nothing from these platforms, so this step is not producing evidence in this environment.
- **Skills not invoked:** `seo-auditor`, `keyword-researcher` and `competitor-scout` are not in this session's skill list. Rivals came from WebSearch and WebFetch only.
- **Corpus:** checked for the one filed issue. The rule is sourced (`knowledge/yogas.md:157-175`, `yogas.md:600` for Rao §11.4, `vedic_reference.md:477`), and the issue changes no astrological claim.

## What the numbers say this cycle

1. **The band is concentrated.** 64 of the 102 band rows are `/learn/*` and carry 10,211 of the 10,636 band impressions and 95 of 109 band clicks. Muhurat pages are 4 rows and 157 impressions, rashifal 3 rows and 127, and `/panchang/YYYY-MM-DD` is 24 rows with 62 impressions and 1 click combined.
2. **The top five band pages by opportunity are unchanged from the analyst's.** Rahu–Ketu antardasha (2,148 impr, 27 clicks, pos 7.3), debilitated-sun-career (1,287, 7, 6.2), sade-sati (1,200, 8, 6.3), rahu-mahadasha-career-problems (783, 9, 6.8), manglik-dosh (477, 2, 7.5). All of them already have an owner: #276, #311, #329, #426, #518.
3. **`/muhurat/griha-pravesh` is the best-converting page in the band.** It has 48 impressions, 7 clicks (14.6% CTR) at position 6.7, with 10 organic sessions and 2.1 pages per session. The learn article behind it already links the tool (`griha-pravesh-muhurat-2026-2027.html:135`). Nothing to fix. The volume is too low to specify anything on.
4. **I looked for a tool-fit article the analyst's CTR-outlier list did not cover** and found `/learn/panch-mahapurush-yoga/` (488 impr, 3 clicks, pos 6.9). Its callout points to the homepage rather than `/kundli`, and it claims Kundali Matching compares yogas between two people. `matching.py` has 0 occurrences of "yoga". That is the one finding with a deterministic, checkable defect, and it is #553.

## Filed

| # | title | why it passed the bar |
|---|---|---|
| **#553** | `/learn/panch-mahapurush-yoga/` tells readers Kundali Matching compares yogas (it does not) and never links `/kundli` | The false sentence is verified in the template (`grep -c "overlap between two people"` → 1) and on the production page (fetched 2026-10-26). Rival URL fetched: daanyam.in/pancha-mahapurusha-yoga, calculator form right after the intro. The corpus citation is a file and line range. Tokens are 0. The repro is an executable grep with an expected result. The metric has an explicit "fewer than 10 sessions is inconclusive" clause. |

**Weakness, stated plainly.** The traffic evidence is thin (4 organic sessions, 3 clicks), so the GA4 metric will probably come back inconclusive. I filed it because the false product claim is deterministic and stands regardless of traffic, and because authenticity wins on the claim under `OBJECTIVE.md`. The issue says the sentence removal alone is a complete, shippable change, and that the CTA half is the same shape as #276, which the analyst scored INCONCLUSIVE, leaning no effect.

## Not filed, and why

| idea | why not |
|---|---|
| **A tool CTA on `rahu-mahadasha-career-problems`** (783 impr, 9 clicks, pos 6.8; only `/ask` and `/` at line 145 of 149) | Same shape as #276, which the analyst scored INCONCLUSIVE, leaning no effect (28 sessions, 1.04 pages/session). #518 owns this family. Adding a second thesis of a type that has not yet shown an effect is activity, not progress. Revisit after #276 rescores (about 2026-11-11). |
| **Title/meta changes on `debilitated-sun-career`, `manglik-dosh`, `jupiter-in-10th-house-career`** | #311 already rewrote these titles on 2026-10-13. Its metric window runs to about 2026-11-10, and a second change would confound it. |
| **`/matching` title/meta** (pos 4.4, 0 clicks) | Already filed as #508. The analyst confirmed it. |
| **`kundali-matching-ashtakoot-guna-milan`** (154 impr, 0 clicks, pos 7.9) | Specifying work on it means leaning on the Ashtakoota engine, which #177/#178 say is untraceable. Its `corpus:` field would be `[UNSOURCED]`, which blocks delivery. Those issues are the unblocker. |
| **`/learn/sade-sati/`** (1,200 impr, 8 clicks) | It already links `/sade-sati-check` at line 43, and #426 covers a Saturn-exit date discrepancy. A rival search showed other sites answering "when does it end" in the same way. I found no new defect. |
| **`/rashifal`** (114 impr, 0 clicks, pos 10.3) | The analyst recorded a baseline for #515, deployed 10-24. Any change now would contaminate that score. |
| **`/festivals`** (pos 26.4, down from 54, impressions −77%) | Outside the band. The festival-date sourcing problem from the last cycle is unresolved, so any content claim would be a dates-verification task first. |
| **`/panchang/YYYY-MM-DD` pages** (24 rows, 62 impressions, 1 click) | Too small to carry a metric. |
| **Hindi `/hi/` pages** (4 rows, 6 impressions) | Nothing to specify until volume exists. #124 stands. |
| **Sitewide `seo_title` backfill** | Last cycle's cohort comparison did not support it, and this cycle's data does not change that. |
| **New `/learn` articles** | `OBJECTIVE.md`: optimise the band before publishing more. Nothing in this cycle's data argues otherwise. |
| **Anything on `/kundli`, `/matching` or `/numerology` funnels** | Landings are a handful of sessions, mostly Direct with bounce rate 0.9–1.0, and the export has no step sequence to measure. |

## Left open for the next cycle

- A per-query export. Without it no `keyword:` field can be measured, and the objective stays unscoreable.
- Rescore of #276, #311 and #329 around 2026-11-10 to 11-14. Whether CTA-type theses are worth filing again depends on those results.
- Reddit and Quora evidence. Two cycles of public WebSearch have returned none, so someone should decide whether this step stays in the command.
- I did not audit the other Yogas-category articles for the same "tool does X" claim pattern. Only the Panch Mahapurush page was verified.

Builds nothing, closes nothing, pushed nothing.
