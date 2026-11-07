# Analyst report — run of 2026-11-07

**Window on every number unless stated: W = 2026-10-08 → 2026-11-04** (28 days, last 3 days excluded; GSC lags 2-3 days, GA4 24-48h).
**Prior window P = 2026-09-10 → 2026-10-07** (from `/tmp/gsc-trend-*.json`).
Sources, all read this run from `/tmp/`: `gsc-band`, `gsc-all`, `ga4`, `gsc-daily`, `ga4-daily`, `gsc-trend-page`, `gsc-trend-query`. No API was re-called.

## 0. Coverage — read before any number

| export | dimension | coverage | truncated | note |
|---|---|---|---|---|
| GSC band / all / trend-page | page | 100% of 19,608 impressions | no | page `position` is the page's average across its queries |
| GSC daily | date | 100% | no | |
| GSC trend-query | query | **13%** of 19,608 impressions | n/a | partial view; Google withholds anonymised queries. Nothing below about queries describes the whole site |
| GA4 landing x channel | landing x channel | 100% of 529 sessions | no | 121 rows, 78 landings, 71 distinct paths after folding query strings and trailing slashes |
| GA4 daily | date | 28 of 28 days with traffic | n/a | daily sum is 531 vs property total 529; the 2-session gap is unexplained and immaterial |

Reachability: `curl https://shubhagya.com/health` returned HTTP 200 this run, `build_sha` f581b1a, revision `bhagya-00591-r56`. Individual pages were not probed.

## 1. The band against OBJECTIVE.md

Objective: *move the 6-20 position band into the top 5 on the ten highest-impression queries.*
The query export covers 13% of impressions, so "the ten highest-impression queries" **cannot be measured**. The page-level proxy below is the best available. It is not the same thing.

### 1a. Site level, W vs P (GSC, page dimension, 100% coverage)

| metric | P 2026-09-10 → 10-07 | W 2026-10-08 → 11-04 | note |
|---|---:|---:|---|
| impressions | 9,026 (sum of page rows) | 19,608 | W is 2.17x P |
| clicks | 97 | 217 | |
| CTR | 1.07% | 1.11% | flat while impressions doubled |
| GA4 sessions | not in this run's files | 529 | first 14 days of W: 217, last 14: 314 |
| GA4 Organic Search sessions | not in this run's files | 281 (53%) | bounce 0.44, 1.54 pages/session |

The daily series is a step, not a ramp. GSC impressions ran ~380-520 a day through 2026-10-22, then rose to 640 (10-23), 927 (10-25) and 1,000-1,240 a day from 10-27 to 11-04. Average position stayed 6.5-7.5 throughout. Same rank, many more impressions, so the cause is more queries or more demand, not a ranking gain. Clicks followed (62 in the first 14 days of W, 155 in the last 14).

### 1b. Position distribution of the 138 pages in W (GSC page, 100%)

| bucket | pages | impressions | share of impressions |
|---|---:|---:|---:|
| position ≤ 5 | 14 | 534 | 2.7% |
| position 6-20 (the band) | 114 | 18,839 | 96% |
| position > 20 | 10 | 268 | 1.4% |

`--band` printed 96 of those 114 pages (16,036 impressions, 82% of the property's, 170 clicks, pooled CTR **1.06%**). The other 18 band pages are outside the 96 the band export emitted. The band's median per-page CTR is 0.0, because most band pages have no click at all, so the pooled rate is the comparator used below.

**Nothing in the top 10 by impressions is in the top 5.** Nine of the ten sit at 6.0-7.3; `/learn/career-during-sade-sati/` is at 5.5.

### 1c. Top band pages by opportunity (GSC page, W; Δ vs P)

| page | impr W | impr P | clicks W | CTR W | position W (P) | opportunity |
|---|---:|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,263 | 1,381 | 41 | 1.26% | 6.7 (7.5) | 154.8 |
| /learn/debilitated-sun-career/ | 2,197 | 805 | 12 | 0.55% | 6.7 (6.0) | 119.8 |
| /learn/sade-sati/ | 1,897 | 668 | 11 | 0.58% | 6.5 (6.2) | 102.8 |
| /learn/jupiter-in-10th-house-career/ | 1,232 | 316 | 7 | 0.57% | 6.9 (6.8) | 66.9 |
| /learn/7th-lord-placement-marriage-guide/ | 942 | 191 | 11 | 1.17% | 7.3 (8.6) | 45.5 |
| /learn/rahu-mahadasha-career-problems/ | 912 | 821 | 16 | 1.75% | 6.3 (7.4) | 38.7 |
| /learn/gochar-2026-planetary-transits/ | 747 | 20 | 11 | 1.47% | 6.0 (7.3) | 33.8 |
| /learn/panch-mahapurush-yoga/ | 613 | 273 | 8 | 1.31% | 6.8 (6.8) | 28.8 |
| /learn/manglik-dosh/ | 521 | 375 | 3 | 0.58% | 7.0 (7.8) | 28.3 |
| /learn/mangal-mars-in-vedic-astrology/ | 315 | 149 | 2 | 0.63% | 7.3 (6.9) | 16.9 |

Top 10 together: 12,639 impressions, 122 clicks. Every one of them gained impressions; the only flat one is `/learn/rahu-mahadasha-career-problems/` (+11%).

### 1d. Query-level view (13% coverage, W vs P) — partial, do not generalise

| query | impr W | impr P | clicks W | position W (P) |
|---|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 341 | 184 | 9 | 8.5 (9.6) |
| sun debilitated in which sign | 188 | 0 | 0 | 8.1 (none) |
| sun is debilitated in which sign | 85 | 0 | 0 | 7.7 (none) |
| jupiter in 10th house | 65 | 0 | 0 | 10.4 (none) |
| sun debilitated sign | 64 | 2 | 0 | 6.3 (3.0) |
| rahu ketu antardasha | 59 | 20 | 0 | 8.9 (9.0) |

The measured query share (2,478 impressions) has 178 queries at position ≤ 5, worth 286 impressions. None of the biggest queries is at ≤ 5.

## 2. Post-ship scores — closed issues with a `thesis:` and a `metric:`

Method: 119 issues closed since 2026-09-22 were listed; those whose body carries a `thesis:` line and a `metric:` line were selected. About 60 do. **Only nine carry a traffic metric (GSC or GA4)**; the rest are infra or gate issues scored by a count, a mutation row or a test, which GA4/GSC cannot score and which I did not score.

**A window is clean only if it starts on or after the deploy.** The earliest deploy among the nine is 2026-10-13. W starts 2026-10-08. **None of the nine has a clean window yet, so none is scored this run.** Every figure in the "reading on W" column is a reference on a mixed or mostly-pre-deploy window. It is not a verdict.

| issue | deploy (merge to main) | window clean from | prior analyst note says when it settles | reading on W (reference only) |
|---|---|---|---|---|
| #311 four-page title rewrite | PR #334, 2026-10-13 17:29Z | 2026-11-13 | yes (#311, "readable ~2026-11-13") | see 2a |
| #276 /dasha CTA on Rahu-Ketu article | PR #342, 2026-10-14 02:02Z | 2026-11-14 | yes (needs `cta_click`) | see 2b |
| #329 Manglik link | PR #344, 2026-10-14 16:07Z | 2026-11-14 | yes (needs `cta_click`) | see 2b |
| #685 Sade Sati title | PR #690, 2026-11-03 10:58Z | 2026-12-04 | yes | `/learn/sade-sati/` 1,897 impr, 11 clicks, 0.58%, pos 6.5 |
| #426 Saturn dates, guard metric | PR #673, 2026-11-02 12:18Z | 2026-12-03 | yes | pos 6.5 vs guard 6.2 ±1; impressions 1,897 vs P 668 |
| #570 `cta_click` event | PR #688, 2026-11-03 04:42Z | not a GSC/GA4-landing metric | yes | event data **not in this run's exports**: undetermined, not zero |
| #508 /matching title | PR #696, 2026-11-03 20:59Z | **2026-12-04** | **no, posted this run** | `/matching` 351 impr, 2 clicks, 0.57%, pos 4.4 |
| #553 Mahapurusha page | PR #615, 2026-10-31 02:26Z | **2026-12-01** | **no, posted this run** | 7 organic sessions, 1.00 pages/session |
| #518 route learn articles to a tool | 5 slices, 2026-10-25 → 2026-11-06 | **2026-12-07** (last slice #754) | **no, posted this run** | learn landings 1.33 pages/session on 330 sessions |

Comments posted this run: **3**, one each on #508, #553 and #518, each "pending — scoreable from <date>". The other six already hold a note naming the date or the instrument that settles them. The repeated nightly notes on #311/#276/#329/#685/#426/#570 are not added to, per the 2026-11-06 rule. Nothing is repeated here on the issues.

### 2a. #311 — the one that reads as a miss so far (not attributable yet)

Predicted (issue): combined CTR of the four pages ≥ 1.5% on ≥ 1,500 impressions at position within ±1 of before. Before = 16 clicks / 2,251 impressions = 0.71% (2026-09-09 → 10-06).

| page (GSC page, W = 2026-10-08 → 11-04) | impr W | clicks W | CTR W | position W (P) |
|---|---:|---:|---:|---:|
| /learn/rahu-mahadasha-career-problems/ | 912 | 16 | 1.75% | 6.3 (7.4) |
| /learn/debilitated-sun-career/ | 2,197 | 12 | 0.55% | 6.7 (6.0) |
| /learn/manglik-dosh/ | 521 | 3 | 0.58% | 7.0 (7.8) |
| /learn/jupiter-in-10th-house-career/ | 1,232 | 7 | 0.57% | 6.9 (6.8) |
| **combined** | **4,862** | **38** | **0.78%** | |

- **Reading:** 0.78% against a 1.5% bar, on a window of which about 5 of 28 days are pre-deploy. Only one of the four (`career-problems`, 1.75%) clears 1.5%; the two largest by impressions sit at 0.55-0.57%.
- **Why it is not a verdict:** W includes 2026-10-08 → 10-12, before the deploy, and cannot be split by page and date. Impressions more than doubled inside W for reasons unrelated to the title, and a larger share of the impressions arrived after the deploy.
- **What would make it a miss:** the clean window (starts 2026-10-14, readable 2026-11-13) staying under 1.5%. If it does, the title lever did not work on these pages and it should not be re-filed as the next thing to try.
- **Do not act on 1c's two 0.55-0.57% rows before 2026-11-13.** Another title test on `debilitated-sun-career` or `jupiter-in-10th-house-career` would contaminate the very window that scores #311.

### 2b. #276 / #329 — conversion

| landing (GA4, W, 28d) | channel | sessions | pages/session | bounce |
|---|---|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha/ | Organic Search | 43 | 1.42 | 0.33 |
| same landing, all channels | all | 57 | 1.32 | 0.46 |
| /learn/manglik-dosh/ | Organic Search | 3 | 1.00 | 0.33 |
| same landing, all channels | all | 9 | 1.00 | 0.78 |

- **#276** bar was ≥ 1.20 pages/session; the reading is 1.42 organic (1.32 all channels). It is over the bar, **not attributable** to the CTA: the page's organic sessions went from 27 to 43 as impressions went 1,381 → 3,263, and a mix shift in query intent can move pages/session without any CTA.
- **#329** floor is 10 sessions; the page has 3 organic sessions. **Inconclusive at this traffic**; the earlier notes already say so.
- Both wait on `cta_click` (#570), which is not in the exports.

## 3. Confounds, named before any delta

| confound | evidence | effect on reading |
|---|---|---|
| **A traffic step inside W** | GSC impressions ~400/day to 1,000+/day from 2026-10-23 → 10-27; position flat at 6.5-7.5 | any W-vs-P delta is dominated by it. Cause not determined: more queries, seasonality or indexing. Sade Sati / Saturn-transit and Diwali (2026-11-08) season are plausible but no seasonality baseline exists in these files |
| **One new ranking page** | `/learn/gochar-2026-planetary-transits/` 20 → 747 impressions (+3,635%) | adds 727 impressions to W on its own; it is a new entrant, not decay or a ship effect |
| **Concurrent ships on the same pages** | #334 (10-13), #342 (10-14), #344 (10-14) in W; #572 Sade Sati phases (10-28); #673 and #690 both edit `/learn/sade-sati/` (11-02, 11-03); #518 slices 10-25 → 11-06 touch many `/learn` articles | cannot be attributed to a single ship. `git log origin/main --since=2026-10-08` shows 307 commits, mostly infra |
| **Window mixes pre and post deploy** | fetch is one trailing 28-day window (#490) | no W reading above is a score |
| **Was the page reachable?** | `/health` 200 this run. Pages not probed. #266 (Groq TPM) affects LLM pages only, not `/learn` | traffic to `/learn` pages is static HTML; no reachability concern found for them |
| **Skip link and `<main>` landmark on every page** | #737 merged 2026-11-06, after W | no effect on W |
| **Sample size** | 217 clicks, 529 sessions, 2-16 clicks per page | per-page CTR moves of 1-2 clicks swing it by 0.1-0.3 points. Most per-page deltas here are noise; the pooled band is the usable number |

## 4. Decay and CTR outliers

### 4a. Decay (GSC page, W vs P, pages with ≥ 100 impressions in P)

The flagged rows are the only ones that met any of: position worse by ≥ 1.0, impressions down ≥ 30%, or gone.

| page | impr P → W | clicks P → W | position P → W | comment |
|---|---:|---:|---:|---|
| /festivals | 364 → 248 | 1 → 0 | 30.0 → 31.0 | position ~30, not in the band; the impression drop is not the ranking |
| /learn/sun-in-10th-house-career/ | 137 → 27 | 1 → 0 | 7.3 → 6.0 | impressions down 80% at a *better* position: demand or query set shrank, not rank. Possibly displaced by the `debilitated-sun-career` page, not determined |
| /learn/the-9-grahas-overview/ | 100 → 39 | 0 → 0 | 7.9 → 9.1 | small |

One more flagged row at lower volume: `/learn/ashwini-nakshatra/`, 93 → 69 impressions, position 5.5 → 7.9, below the P ≥ 100 cut. No band page with real volume lost ground. **No decay finding clears the bar for an issue.**

### 4b. CTR outliers (GSC page, W; position ≤ 7.5 and ≥ 300 impressions; band pooled CTR = 1.06%)

| page | impr | clicks | CTR | position | ratio to band |
|---|---:|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,197 | 12 | 0.55% | 6.7 | 0.52x |
| /learn/sade-sati/ | 1,897 | 11 | 0.58% | 6.5 | 0.55x |
| /learn/jupiter-in-10th-house-career/ | 1,232 | 7 | 0.57% | 6.9 | 0.54x |
| /learn/marriage-mahadasha-timing/ | 430 | 2 | 0.47% | 5.7 | 0.44x |
| /matching | 351 | 2 | 0.57% | 4.4 | 0.54x |
| /learn/manglik-dosh/ | 521 | 3 | 0.58% | 7.0 | 0.54x |

Reference highs: `/learn/10th-lord-in-6th-house-career/` 2.74% (475 impr, pos 6.7) and `/learn/rahu-mahadasha-career-problems/` 1.75%.
Three of the six already have a live test (#311, #685, #508) and are not re-flagged. `debilitated-sun-career` and `jupiter-in-10th-house-career` are #311 pages, so they wait on 2026-11-13. `marriage-mahadasha-timing` (430 impressions, 2 clicks) has no test running and is the only unowned outlier; at 2 clicks it is too small to file.

## 5. Funnel and engagement (GA4, W, landing aggregated across channels)

| segment | sessions | pages/session | bounce |
|---|---:|---:|---:|
| all | 529 | | |
| Organic Search | 281 | 1.54 | 0.44 |
| Direct | 229 | 1.99 | 0.68 |
| AI Assistant | 15 | 3.40 | 0.33 |
| `/learn/*` landings (all channels) | 330 (62% of 530 row-sessions) | 1.33 | |
| `/learn/*`, Organic Search | 224 | 1.39 | |
| `/` landing | 90 | 3.69 | 0.36 |

- Learn articles are 62% of sessions and 80% of organic sessions (224 of 281) and hand on at 1.33-1.39 pages per session. The homepage hands on at 3.69. The #518 thesis (the articles are the front door and do not pass readers on) is still what the data shows. Its routing slices are mostly too recent to show here.
- 15 sessions have landing `(not set)` (11 organic, 0 pages/session, bounce 0.93): a GA4 attribution artefact, not a page.
- 15 sessions landed on `/admin/ops/`: the owner's own page; this is not audience traffic and inflates "Direct".
- **A funnel step losing most of its traffic** (kundli form → result → second page) **cannot be read from these files**; GA4 here is landing x channel only, with no event or step dimension.

## 6. What I could not determine, and the one measurement that settles each

| not determined | settled by |
|---|---|
| Top-ten highest-impression **queries** and their position (the objective's literal measure) | the query dimension covers 13%; nothing recovers the other 87%. Use pages as the proxy, or a GSC query export per top page |
| Whether any ship in section 2 worked | the clean windows in the table in section 2, earliest 2026-11-13 (#311) |
| Why impressions doubled from 2026-10-23 | a prior-year same-weeks series, or a GSC query-by-date export on the three pages that grew most |
| Whether tool links in articles are clicked | GA4 `cta_click` by `from_path`/`to_path` (#570, live 2026-11-03), not in the current exports; the parameters must be registered as custom dimensions to show |
| Funnel drop-out on kundli/matching/numerology | a GA4 events export by step; not fetched |
| Per-page reachability | not probed this run |
| Organic sessions in P (north-star delta) | `ga4.json` carries W only; no prior-window GA4 file was supplied |

## 7. Issues filed

**None.** No finding in this run needs action that is not already owned by an open or scored issue. The one candidate (a second title test on `/learn/debilitated-sun-career/`, 2,197 impressions at 0.55%) is premature: it would land inside the window that scores #311, which is readable on 2026-11-13. Revisit that day.
