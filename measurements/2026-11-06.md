# Analyst report — 2026-11-06

**Window for every number: W = 2026-10-07 → 2026-11-03** (28 days; the last 3 days are excluded because GSC is not final and GA4 lags 24–48h). Nothing below includes today.

Read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json` and `/tmp/ga4.json`. The APIs were not re-called. Any other number is labelled with where it came from (an issue body or an earlier comment).

## 0. Coverage — read before any figure

| export | dimension | window | coverage | truncated |
|---|---|---|---|---|
| `gsc-all.json` | `page` | W | 100% of 18,790 impressions, 140 rows | no |
| `gsc-band.json` | `page`, position 6–20 | W | fetch 100%; **emitted 101 rows = 15,522 impressions = 83%** | no |
| `ga4.json` | landing × channel | W | 100% of 510 sessions, 117 rows, 78 landings | no |

- GSC is the **page** dimension. A band `position` is the page's **average across its queries**, not any one query's. The objective says "queries"; this export answers it for pages only. `--by query` covers ~9%, so it cannot answer for the whole band.
- Reachability this run: `curl https://shubhagya.com/health` returned **HTTP 200** from the runner. I probed no individual page, and I did not probe a rashifal page (a cache miss spends ~3,330 tokens).
- GA4 aggregation: sessions summed by landing across channels, with the `?hl=en-IN` variant folded; `pages_per_session` and bounce weighted by sessions.

## 1. The band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

| measure (GSC `page`, W) | value |
|---|---:|
| property impressions / clicks | 18,790 / 205 |
| band pages (position 6–20) | 101 |
| band impressions / clicks | 15,522 (83% of all) / 164 |
| band CTR, impressions-weighted | 1.06% (164 / 15,522) |
| band pages with 0 clicks | 71 pages, 1,548 impressions |
| band pages with ≥ 100 impressions | 22 |
| pages already at position < 6 | 29 pages, 3,042 impressions, 41 clicks |
| pages at position > 20 | 10 pages, 257 impressions |

**Objective check, on pages.** The ten highest-impression pages total 12,621 impressions (67% of 18,790). Nine of the ten sit in the 6–20 band. The tenth is `/learn/career-during-sade-sati/` at 5.6, which is still not top 5. **Pages of those ten at position ≤ 5: 0 of 10.** For the stated query-level objective this is the best the export allows, not a measurement of it.

### Band list — top 15 by opportunity (`impressions × achievable CTR gain`, as emitted)

| page | impressions | clicks | CTR | position | band_opportunity |
|---|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,178 | 39 | 1.23% | 6.8 | 151.7 |
| /learn/debilitated-sun-career/ | 2,132 | 12 | 0.56% | 6.7 | 115.9 |
| /learn/sade-sati/ | 1,873 | 12 | 0.64% | 6.5 | 100.4 |
| /learn/jupiter-in-10th-house-career/ | 1,138 | 6 | 0.53% | 7.0 | 62.3 |
| /learn/7th-lord-placement-marriage-guide/ | 843 | 9 | 1.07% | 7.3 | 41.6 |
| /learn/rahu-mahadasha-career-problems/ | 900 | 16 | 1.78% | 6.4 | 38.0 |
| /learn/gochar-2026-planetary-transits/ | 692 | 10 | 1.45% | 6.0 | 31.5 |
| /learn/panch-mahapurush-yoga/ | 582 | 7 | 1.20% | 6.9 | 27.9 |
| /learn/manglik-dosh/ | 507 | 3 | 0.59% | 7.0 | 27.4 |
| /learn/mangal-mars-in-vedic-astrology/ | 306 | 2 | 0.65% | 7.2 | 16.4 |
| /learn/10th-lord-in-6th-house-career/ | 448 | 11 | 2.46% | 6.6 | 15.9 |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 202 | 0 | 0% | 7.6 | 12.1 |
| /learn/vimshottari-dasha-explained/ | 187 | 1 | 0.53% | 7.1 | 10.2 |
| /learn/pushya-nakshatra/ | 183 | 2 | 1.09% | 7.3 | 9.0 |
| /rashifal | 147 | 0 | 0% | 8.7 | 8.8 |

Top 4 pages alone are 8,321 impressions, which is 54% of the band's.

## 2. Scores — issues closed in the last 28 days that carry a `thesis:` and a `metric:`

Issues closed on or after 2026-10-09 whose body has a `thesis:` line: **47** found in a fetch of the repository's 312 closed issues. Eight have a metric that GA4 or GSC can measure. Each of those has a comment posted this run (links are in section 6). The other 39 have repo-count or gate metrics (tokens, gates, workflow behaviour, security) and are scored by their own tests, not by traffic; I did not post on them and I did not check their gates.

### Misses and hits, in the same table

| issue | predicted (`metric:`) | actual, W | verdict |
|---|---|---|---|
| **#311** title/meta on four band pages | CTR ≥ 1.5% on ≥ 1,500 impr. (before 0.71%) | **37 / 4,677 = 0.79%** at position 6.75 | **MISS so far.** Bar missed by about half. |
| **#276** dasha CTA on Rahu–Ketu antardasha | pages/session ≥ 1.20 (inconclusive below 20 sessions) | **1.34** on 53 sessions | **PROVISIONAL, above the bar, not attributable** (mix alone moves it). |
| **#329** Manglik checker link | pages/session ≥ 1.30 on ≥ 10 Organic sessions | **1.00** on **3** Organic sessions | **INCONCLUSIVE** (sample below the floor). |
| **#685** Sade Sati title | CTR ≥ 1.2% on ≥ 1,200 impr. | 12 / 1,873 = 0.64% | **NOT SCOREABLE** (about half a post-deploy day in W). |
| **#426** Saturn dates correction (guard) | position within ±1 of 6.2; impressions not down > 20% | 6.5; 1,873 vs 1,017 | **NOT SCOREABLE** (no post-deploy day). No regression visible, none could be. |
| **#515** nightly rashifal | organic sessions to `/rashifal/*`, 28d post-deploy | **0** organic sessions (4 of 510 all channels) | **NOT SCOREABLE** (~11 post-deploy days). |
| **#514** rashifal layout fields | organic + email re-open, 28d post-deploy | **0** organic; re-open not in exports | **NOT SCOREABLE.** |
| **#570** `cta_click` event | ≥ 1 event row per tool-linked article that got a click | undetermined | **NOT IN EXPORTS.** `ga4.json` has no event dimension. Not zero; unknown. |

**The plain reading.** Of the three traffic ships that have been live long enough to read, **#311 is a miss, #329 cannot be scored at this traffic, and #276 clears its bar for a reason the data cannot separate from channel mix.** No shipped traffic thesis has a clean pass this cycle.

### #311 detail (the miss)

| page (GSC, W) | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| rahu-mahadasha-career-problems | 900 | 16 | 1.78% | 6.4 |
| debilitated-sun-career | 2,132 | 12 | 0.56% | 6.7 |
| manglik-dosh | 507 | 3 | 0.59% | 7.0 |
| jupiter-in-10th-house-career | 1,138 | 6 | 0.53% | 7.0 |
| **four combined** | **4,677** | **37** | **0.79%** | **6.75** |
| three excluding career-problems | 3,777 | 21 | 0.56% | |

- The issue body gave 0.65–0.83% per page before. The three pages other than career-problems are below that range.
- To reach the 1.5% bar on W's impressions, the four pages needed ~70 clicks; they got 37.
- **Implication for #685.** #685 uses the same lever (title/meta rewrite at unchanged position) with a bar of ≥ 1.2% on the same kind of page. #311 is the prior and it is not encouraging. #685's own body already says that if it misses, no more title tests should be filed for this band.

### #276 detail

| `/learn/rahu-mahadasha-ketu-antardasha/` (GA4, W) | sessions | pages/session | bounce |
|---|---:|---:|---:|
| Organic Search | 40 | 1.45 | 35.0% |
| Direct | 12 | 1.00 | 91.7% |
| Direct, `?hl=en-IN` variant | 1 | 1.00 | 0% |
| all, session-weighted | 53 | 1.34 | |

- The page mix is 40 Organic at 1.45 and 13 Direct at 1.00, so pages/session moves with channel mix. There is no landing × day split to separate the CTA from the mix.

## 3. Confounds, stated before any delta

| confound | what I found | effect on the readings |
|---|---|---|
| **Concurrent ships** | `git log origin/main --since=2026-10-06` lists 303 commits; the history was deepened to 400 to read it. The ones under `src/` in or near W include learn-page edits #512, #530, #556, #579, #587, #590 (Manglik, remedies, Jupiter/Mercury), #521, #615, #658, #680 (tool routing on learn articles), #673 and #690 (both on `/learn/sade-sati/`), #696 (/matching title). | On #311 and #329 the content edits overlap the topic of the pages scored; no CTR or pages/session change is attributable to one ship. I did not diff each PR's files. |
| **Two ships on one page** | #426 (2026-11-02 12:18Z) and #690 (#685, 2026-11-03 10:58Z) both changed `/learn/sade-sati/`. | Any move on that page after 2026-11-03 is joint. |
| **Pre/post split** | The three exports hold one 28-day window. W includes ~7 pre-deploy days for #311/#276/#329 (deploys 2026-10-13/14, dates taken from earlier comments on those issues). | No clean post-only figure for any of them from these files. |
| **Seasonality** | Diwali is 2026-11-08 (stated in the #685 body, not re-verified by me). Sade Sati and Saturn-transit interest is plausibly lifted by news. No seasonal baseline is in these files. | Raises the impressions on seasonal pages; CTR is less exposed than clicks. |
| **Page working?** | `/health` 200. I did not probe any content page. #266 (Groq TPM ceiling) is the standing intermittent-failure risk for LLM pages. | Rashifal figures (section 2, #515/#514) are **not** read as engagement; I could not confirm those pages rendered a reading. |
| **Sample size** | Per-page clicks in the band are 0–39. 71 of 101 band pages have 0 clicks. | Differences under ~0.5 pt of CTR on a page with < 20 clicks are noise. |
| **Admin and unattributed traffic in GA4** | 14 sessions landed on `/admin/*` and 15 on `(not set)` (section 5). | ~5.7% of the 510 sessions are not visitors or not attributable. Small, but it sits in the denominator of the north-star. |

## 4. CTR outliers and decay

### CTR outliers (against the band's own weighted CTR of 1.06%)

| page (GSC, W) | impressions | clicks | CTR | position | clicks at band CTR |
|---|---:|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,132 | 12 | 0.56% | 6.7 | 22.5 |
| /learn/sade-sati/ | 1,873 | 12 | 0.64% | 6.5 | 19.8 |
| /learn/jupiter-in-10th-house-career/ | 1,138 | 6 | 0.53% | 7.0 | 12.0 |
| /learn/manglik-dosh/ | 507 | 3 | 0.59% | 7.0 | 5.4 |
| **sum** | 5,650 | 33 | 0.58% | | **59.7** |
| contrast: /learn/10th-lord-in-6th-house-career/ | 448 | 11 | 2.46% | 6.6 | 4.7 |

- These four pages hold the largest below-band gap: ~27 clicks per 28 days against 59.7 at the band's own rate. Three of them (all but sade-sati) were in #311's rewrite.
- `10th-lord-in-6th-house-career` at position 6.6 clicks at 4.4× the rate of `debilitated-sun-career` at 6.7. That gap is a title/snippet difference, or a query-mix difference; I did not determine which.
- A CTR gap that survives a title rewrite (#311) is less likely to be a title problem alone. This is a reading, not a finding I can prove from one window.

### Decay

**Not determinable from these three files.** Each holds one window. A month-over-month position change needs a prior window; the same fetch also wrote `gsc-trend-page.json`, `gsc-trend-query.json`, `gsc-daily.json` and `ga4-daily.json` to `/tmp`, but they were not on this run's list so I did not read them. Reading `gsc-trend-page.json` would settle decay, and the daily files would give the pre/post split for #311, #276, #329.

## 5. Funnel and traffic quality (GA4, W)

| measure | value |
|---|---:|
| sessions, all channels | 510 |
| Organic Search / Direct / AI Assistant / Unassigned | 268 / 223 / 15 / 5 |
| pages/session, all channels, session-weighted | 1.81 |
| Organic Search: pages/session / bounce | 1.57 / 44.8% |
| Organic `/learn/*` sessions / pages/session | 209 / 1.41 |
| Organic `/learn/*` landing rows with pages/session = 1.00 | 22 rows, 69 sessions |
| `/` landings, sessions / pages/session | 91 / 3.70 |

| tool landings (GA4, W) | channel | sessions | pages/session |
|---|---|---:|---:|
| /kundli | Direct / Organic | 13 / 10 | 1.15 / 2.50 |
| /matching | Direct / Organic / AI Assistant | 10 / 1 / 1 | 1.00 / 1.00 / 12.0 |
| /numerology | Direct / Organic | 9 / 2 | 1.00 / 1.00 |
| /muhurat/griha-pravesh | Organic | 12 | 2.17 |

- **A funnel by step cannot be built from this export** (landing only, no event or step dimension). `cta_click` (#570) is the instrument, and it is not in the export (see #570 above).
- Organic `/learn/*` is 209 of 268 organic sessions (78%) and 1.41 pages/session; 22 landing rows with 69 sessions never went to a second page.
- **Admin traffic in the denominator:** `/admin/ops` 13 sessions (11 Direct, 1 Organic, 1 on `?window=1`) and `/admin/activity` 1 session, 14 total (2.7%). `admin_ops.html` documents that it carries no analytics. Filed as **#735**.
- **`(not set)` landings:** 15 sessions (11 Organic Search, 3 Unassigned, 1 Direct), 93% bounce, 0 pages/session. Cause not determined.

## 6. What was posted and filed this run

| action | where |
|---|---|
| score comment | #311 https://github.com/mahAnuj/astro-ai/issues/311#issuecomment-6674105686 |
| score comment | #276 https://github.com/mahAnuj/astro-ai/issues/276#issuecomment-6674105915 |
| score comment | #329 https://github.com/mahAnuj/astro-ai/issues/329#issuecomment-6674106185 |
| score comment | #426 https://github.com/mahAnuj/astro-ai/issues/426#issuecomment-6674106403 |
| score comment | #685 https://github.com/mahAnuj/astro-ai/issues/685#issuecomment-6674106774 |
| score comment | #515 https://github.com/mahAnuj/astro-ai/issues/515#issuecomment-6674107166 |
| score comment | #514 https://github.com/mahAnuj/astro-ai/issues/514#issuecomment-6674107445 |
| score comment | #570 https://github.com/mahAnuj/astro-ai/issues/570#issuecomment-6674107724 |
| issue filed | **#735** `[MEASURE]` 14 GA4 sessions landed on `/admin/*`, 15 on `(not set)`; Evidence Block included, cause undetermined |

**No other issue filed.** The low-CTR band pages are already the subject of #311 and #685; a new title issue would restate a thesis that has not been scored. I did not file an issue for rashifal's zero organic clicks because the traffic base is too small and I could not confirm the pages rendered.

## 7. What I could not determine, and the one measurement that settles each

| open question | the measurement |
|---|---|
| Did #311, #276, #329 move anything, separate from the pre-deploy days? | `ga4-daily.json` / `gsc-daily.json` from this fetch, or a post-only window from 2026-10-14. That window closes 2026-11-10 and is readable ~2026-11-13. |
| Did #685 / #426 move `/learn/sade-sati/`? | GSC `page` for window 2026-11-04 → 2026-12-01, readable ~2026-12-04; treat as one joint test. |
| Is any page losing ground (decay)? | `gsc-trend-page.json` from this fetch (a prior-window comparison). |
| Did `cta_click` record clicks (#570)? | GA4 events report on `cta_click` with `from_path` / `to_path` registered as custom dimensions, 2026-11-04 → 2026-12-01. |
| Did the nightly rashifal change organic traffic or email re-open (#515, #514)? | Organic sessions to `/rashifal/*` for 2026-10-25 → 2026-11-21, plus the email provider's re-open rate (not in any export). |
| Do rashifal pages render a reading right now? | Fetch one `/rashifal/{rashi}` and assert on the `.speakable-body` div (see the `verify-production` header). I did not, to avoid a ~3,330-token cache miss. |
| Why do 13 sessions land on `/admin/ops`? | See #735. |
| Per-query band position (the objective as written) | Needs `--by query`, which covers ~9% of impressions; a whole-band query answer is unavailable from GSC. |

## 8. Honest summary

- The band is real and unmoved: 101 pages, 83% of impressions, and **0 of the ten top pages at position ≤ 5**.
- The one ship of this kind that has been live long enough to read, **#311, is a miss** (0.79% against a 1.5% bar). Its sibling lever, #685, has no post-deploy data yet.
- #276 clears its bar and I am not calling it a hit. #329 cannot be scored at ~3 organic sessions per 28 days.
- Five of the eight traffic-scored issues are **not scoreable yet** because their deploys fall at or after the end of W. That reads as "wait", not "worked".
- Nothing in these three files shows a regression on a ranking page, and nothing could, because none of the exports separates pre-deploy from post-deploy days.
