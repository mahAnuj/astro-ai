# Analyst report — 2026-11-20

**Window for every number: W = 2026-10-21 → 2026-11-17** (28 days; the last 3 are excluded: GSC lags 2–3 days, GA4 24–48h). **Previous window P = 2026-09-23 → 2026-10-20** (GSC only: GA4 has no previous window in this run, see §10).
Everything below was read from this run's files. What I did not read is marked **not measured**.

## 0. What was in this run

| file | read | coverage / note |
|---|---|---|
| `gsc-band.json` | yes | `dimension: page`; coverage 100% of 29,253 impressions; **emitted** 95 pages at position 6–20 = 21,735 impressions (74%); not truncated |
| `gsc-all.json` | yes | page mode, 139 pages, coverage 100% |
| `ga4.json` | yes | landing × channel: 152 rows, 99 landings (92 distinct paths after folding query strings and trailing slashes); property total 780 sessions, row sum 782, 100% coverage, not truncated |
| `gsc-daily.json`, `ga4-daily.json` | yes | 28 of 28 days with traffic. GA4 daily rows sum to **784** sessions, the other two figures are 780 and 782. I quote each from its own file |
| `gsc-trend-page.json` | yes | page mode W vs P, 100% of W impressions (page-row sum 29,335 vs property total 29,253) |
| `gsc-trend-query.json` | yes | **query mode covers 14% of impressions** (4,233 of 29,253; 867 query keys). Google withholds the rest |
| `ga4-events.json` | yes | 17 event names, 5,224 events, not truncated. `cta_click` exists only from 2026-11-03 |
| `ga4-anomalies.json` | yes | 2 `spikes` + 5 `watch` days (first run carrying the watch tier, #1236) |
| `gsc-discover.json` | yes | **0 clicks, 0 impressions on all 28 days** (a measured zero) |
| `verify-first.json` | yes | 10 busiest pages |
| `measure/llm-usage.json` | yes | trailing 7 days, generated 2026-11-20T01:59Z. **No error or fallback field** (#1208 open) |
| `measurements/index-status.json` | **yes, first run it exists** | generated 2026-11-19T20:05Z, 214 URLs inspected, 0 errors. Its impression column comes from the committed `measurements/gsc-all.json`, an earlier window than W |

## 1. Growth (lever 1)

**Search, GSC, W vs P** (page-row sums; W property totals 29,253 impressions / 389 clicks from `gsc-daily.json`):

| metric | W 10-21 → 11-17 | P 09-23 → 10-20 | change |
|---|---:|---:|---:|
| impressions (page-row sum) | 29,335 | 11,788 | 2.49× |
| clicks (page-row sum) | 389 | 116 | 3.35× |
| CTR | 1.33% | 0.98% | +0.35 pt |
| pages with any impression | 139 | 126 | +13 |
| query keys visible (14% view) | 867 | 215 | +652 |

**GA4, W only** (no previous window, so no growth ratio can be stated): 780 sessions (`ga4.json` total) / 784 (daily rows); sum of daily active users 698; sum of daily new users 648. Organic Search 475 sessions (61% of the 782 row-sum), Direct 300 (38%), AI Assistant 6, Unassigned 1.

**Inside W, by week (daily files):**

| week | GA4 sessions | GA4 active users (sum of days) | GSC impressions | GSC clicks |
|---|---:|---:|---:|---:|
| 10-21 → 10-27 | 150 | 129 | 5,244 | 60 |
| 10-28 → 11-03 | 146 | 131 | 7,621 | 86 |
| 11-04 → 11-10 | 253 | 227 | 8,035 | 114 |
| 11-11 → 11-17 | 235 | 211 | 8,353 | 129 |

First 14 days vs last 14: sessions 296 → 488, impressions 12,865 → 16,388, clicks 146 → 243. **Watch item:** impressions fall from 1,337 (11-14) to 1,110, 908 and 811 on 11-15 to 11-17, and GA4 sessions to 14 and 20 on 11-16 and 11-17. The two Mondays/Tuesdays before (11-09, 11-10) read 1,295 and 1,256 impressions. Three days are not a trend and I draw no conclusion; the next run's window shows whether it held.

**Which page groups drive the GSC change** (`gsc-trend-page.json`, page-row sums, W vs P):

| group | impr W | impr P | clicks W | clicks P |
|---|---:|---:|---:|---:|
| `/learn/*` | 27,523 | 10,704 | 333 | 97 |
| `/muhurat/*` | 480 | 137 | 25 | 8 |
| `/festivals` | 288 | 254 | 0 | 0 |
| `/` | 211 | 100 | 9 | 6 |
| `/rashifal/*` | 211 | 94 | 1 | 0 |
| `/numerology` | 174 | 4 | 10 | 0 |
| `/matching` | **122** | **336** | 4 | 0 |
| `/panchang*` | 99 | 91 | 2 | 1 |
| `/kundli` | 96 | 58 | 4 | 4 |
| `/hi/rashifal*` | 77 | 0 | 0 | 0 |
| `/about` | 36 | 0 | 1 | 0 |

`/learn/*` is 93.8% of W impressions and 85.6% of W clicks. Largest single gains (impressions P → W): gochar-2026 (10 → 2,694), rahu-mahadasha-ketu-antardasha (2,010 → 3,821), debilitated-sun-career (1,237 → 2,945), jupiter-in-10th-house-career (376 → 1,965), 7th-lord-placement (267 → 1,492), sade-sati (1,092 → 2,125), career-during-sade-sati (384 → 1,267).

**Seasonal or structural? Both inputs are present and I cannot separate them.**
- Calendar (`festivals_for_date()` over W, run this run): Sharad Purnima 10-25, Karva Chauth 10-29, Dhanteras 11-06, Diwali 11-08 (with Narak Chaturdashi), Govardhan Puja 11-10, Bhai Dooj 11-11, Chhath 11-15. **None of the ten highest-impression pages is a festival page** (Rahu/Ketu, Sun debilitated, gochar, Sade Sati, house and career guides), so the rise is not a festival-page rise. `/muhurat/*` (480 vs 137) is the one group that may follow the wedding / housewarming season.
- Structural: the top gainers are pages the loop edited. **522 PRs merged since 2026-10-21** (`gh pr list --search "merged:>=2026-10-21"`). I cannot attribute the rise to any one ship.
- Not determinable: how much is Google re-ranking a young domain versus the work. No year-earlier window exists.

**Every day in `spikes` and `watch` (all 7 days at or above median 22 + 10), with its source** — Discover is 0 on every one of these days:

| date | users / sessions | tier | source named by the file (and my read of its rows) | GSC clicks | read |
|---|---:|---|---|---:|---|
| 2026-10-23 | 34 / 34 | watch | Direct, landing on `/`, `/kundli`, `/matching`, `/numerology` (6, 6, 5, 5 sessions, each 0–33% engaged, 3–6s on the tool pages). File says "real readers", 23% engaged, 20.5s, Chrome mobile US | 7 | **Unresolved, leans Direct tool-page visits with little engagement.** Not search (7 clicks) |
| 2026-11-06 | 57 / 59 | spike | Top row Direct on `/rashifal/aries` (6 sessions, 17% engaged, 3.5s). **19 of 50 sessions zero engagement** (no-browser-name desktop US 10, Chrome desktop US 6, Chrome mobile US 3) | 17 | **Mixed, not growth.** About 19 sessions look automated; Organic readers of `/learn/rahu-mahadasha-career-problems/` (4 sessions, 224s) look real. Search did not spike |
| 2026-11-09 | 32 / 37 | watch | google / organic, Chrome mobile India; `jupiter-in-10th`, `rahu-mahadasha-ketu`, `griha-pravesh` (5 sessions each); 53% engaged, 127s | 21 | **Real readers, search-driven.** Clicks above the window mean of 13.9 |
| 2026-11-10 | 40 / 43 | watch | Top row Direct on `/matching` (5 sessions, 0% engaged, 2.2s), `/numerology` (4); bing / organic `/numerology` 4 sessions at 0%. **21 of 35 sessions zero engagement**, desktop US | 14 | **Mixed, mostly automated.** Not growth |
| 2026-11-12 | 34 / 37 | watch | google / organic, `/muhurat/griha-pravesh` (4 sessions, 100% engaged, 205s), Chrome mobile India; 38% engaged, 53s | 24 | **Real readers, search-driven** |
| 2026-11-14 | 32 / 47 | watch | google / organic: 10 sessions on `/learn/rahu-mahadasha-ketu-antardasha/` (40% engaged, 80s), 5 on `chronic-health-issues-kundli`; 51% engaged, 111s. Sessions per user 1.47, the highest in W | 23 | **Real readers, search-driven.** Not Discover |
| 2026-11-15 | 51 / 56 | spike | google / organic on the Rahu page (6 sessions, 83% engaged, 242s). **Chrome mobile China 9 sessions, 0% engaged, 0s**; Chrome mobile India 17 sessions (59%, 61s); 5 Direct on `/panchang/2026-12-02` at 0%, 1.6s | 14 | **Mixed, not growth.** China-mobile and dated-panchang rows look automated; the India readers look real. Not Discover |

- Of the seven days, **three are search-driven real readers (11-09, 11-12, 11-14), three carry zero-engagement automated-looking traffic (11-06, 11-10, 11-15), one is unresolved (10-23).** None of the seven is growth by itself.
- **Direct is not clean.** Direct is 38% of sessions at 21% engaged against 58% for Organic Search. 17 of 782 row-sessions landed on `/admin/ops` (16 Direct; internal; #735's fix merged 2026-11-11, so W is mostly before it and I cannot split by day). `/learn/financial-struggles` took 9 Direct sessions, 0 engaged. I do not treat Direct as audience.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page mode measures pages (a page's position is its average over its queries). **Query mode covers 14%, so the objective is readable only on the visible share.**

**Band, page mode, W** (`emitted_*`, 74% of impressions): **95 pages, 21,735 impressions, 278 clicks, impressions-weighted CTR 1.28%** (the band's median CTR is 0). 80 of 95 sit at position ≤ 10 (21,493 impressions). **61 of 95 had zero clicks**, on 1,198 impressions (5.5% of the band).

Top 10 by `band_opportunity`:

| # | page | impr W | clicks W | CTR W | position W | impr P / position P |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,821 | 63 | 1.65% | 6.4 | 2,010 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,945 | 16 | 0.54% | 6.5 | 1,237 / 6.1 |
| 3 | /learn/sade-sati/ | 2,125 | 17 | 0.80% | 6.6 | 1,092 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,965 | 18 | 0.92% | 7.1 | 376 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,492 | 14 | 0.94% | 7.2 | 267 / 7.8 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,265 | 11 | 0.87% | 6.8 | 557 / 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,030 | 15 | 1.46% | 7.3 | 451 / 7.0 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 580 | 3 | 0.52% | 7.6 | 123 / 7.7 |
| 9 | /learn/10th-lord-in-6th-house-career/ | 783 | 21 | 2.68% | 6.7 | 179 / 7.0 |
| 10 | /learn/manglik-dosh/ | 492 | 4 | 0.81% | 6.5 | 471 / 7.5 |

**Top-5 reading:** of the ten highest-impression pages (rahu-ketu 3,821, debilitated-sun 2,945, gochar-2026 2,694, sade-sati 2,125, jupiter-10th 1,965, 7th-lord 1,492, career-during-sade-sati 1,267, planets-in-7th 1,265, rahu-career-problems 1,077, panch-mahapurush 1,030) **none has an average position ≤ 5.0** (gochar-2026 is closest at 5.1; career-during-sade-sati 5.5). In the 14% query view **1 of the 10 highest-impression queries is at position ≤ 5, and it is `yes` (3.6, 105 impressions, 0 clicks), a query nobody targets**. The real head query `rahu mahadasha ketu antardasha` is at 6.6 (P 9.8) on 410 impressions (P 262) with 13 clicks. **The objective is not met on the visible share; the other 86% cannot be read.**

**CTR outliers.** Band pages with ≥ 500 impressions, position ≤ 7.5 and CTR below the band's own weighted 1.28%:

| page | impr | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,945 | 16 | 0.54% | 6.5 |
| /learn/sade-sati/ | 2,125 | 17 | 0.80% | 6.6 |
| /learn/jupiter-in-10th-house-career/ | 1,965 | 18 | 0.92% | 7.1 |
| /learn/7th-lord-placement-marriage-guide/ | 1,492 | 14 | 0.94% | 7.2 |
| /learn/planets-in-7th-house-marriage/ | 1,265 | 11 | 0.87% | 6.8 |
| **five pages** | **9,792** | **76** | **0.78%** | |

At the band's 1.28% these five would have taken about 125 clicks, not 76: a gap of **about 49 clicks per 28 days**. In-band references at similar position: `10th-lord-in-6th-house` 2.68% at 6.7 (783 impr), `rahu-mahadasha-ketu-antardasha` 1.65%. This run holds no CTR-by-position curve for the site, so I size no gain from position. **New confound for the title tests on these pages, from the index file: see §9** (Google had not re-crawled several of them since their edits).

**Decay** (position worse by ≥ 1.5 and ≥ 50 impressions in either window; GSC page mode, W vs P):

| page | impr P → W | clicks P → W | position P → W | note |
|---|---|---|---|---|
| /matching | **336 → 122** | 0 → 4 | **4.3 → 9.2** | lost 64% of impressions and 4.9 positions. Index status: "Submitted and indexed", last crawl 2026-11-08, so Google has seen the #508 title/meta change (deployed 2026-11-03). **#1076** is the open investigation; this run does not date the onset (needs `--page-daily`, #953) |
| /learn/magha-nakshatra/ | 21 → 131 | 0 → 6 | 6.1 → 7.6 | impressions rose 6×, position fell on a changed query mix |
| /learn/shani-saturn/ | 6 → 99 | 0 → 0 | 6.7 → 9.7 | small |
| /learn/diwali-muhurat-2026/ | 2 → 75 | 0 → 1 | 7.0 → 11.1 | event passed 11-08 |
| /learn/the-9-grahas-overview/ | 104 → 22 | 0 → 0 | 7.9 → 10.0 | impressions fell 79%; index status: crawled, **not indexed** |
| /learn/ashwini-nakshatra/ | 99 → 88 | 1 → 1 | 5.4 → 7.7 | index status: crawled, **not indexed** (last crawl 2026-09-18) |
| /festivals | 254 → 288 | 0 → 0 | 29.4 → 37.1 | far outside the band |

Pages gone from W (impressions in P, 0 in W): **`ketu-in-vedic-astrology` (60 → 0)** and **`griha-pravesh-muhurat-2026-2027` (34 → 0)**. **Both are now explained by the index file:** each reads "Crawled – currently not indexed" (last crawl 2026-10-15 and 2026-08-09). The second still took 14 GA4 sessions in W (9 Organic Search, 4 Direct, 1 AI Assistant; 2 engaged), so organic visits arrived on a page the index file calls not indexed; I do not know how.

## 3. Post-ship scores (closed in the last 45 days with `thesis:` and `metric:`)

**I read the comment thread on every issue before writing.** Four comments posted this run (below); every other thread already holds its pending note, its score or its not-scoreable note, and none of the clean verdicts moved.

### Posted this run

| issue | predicted (`metric:`) | actual (this run) | verdict | comment |
|---|---|---|---|---|
| **#1236 HIT** | days at or above median + 10 with a named source: 2 of 7 → 7 of 7, from the first run after merge | **7 of 7** (2 `spikes` + 5 `watch`, `watch_omitted` 0; PR #1266 merged 2026-11-19T23:35Z, this is the first run after) | **HIT** (an export fact, so no seasonal or traffic confound) | posted |
| **#1115 NOT MET yet** | 2 GA4 windows in the report: 0 → 2, next run after merge | **1** window. No `ga4-trend` file in the run (`ls /tmp/ga4-trend.json` → absent) | **MISS so far, blocked on #1205** (the `agent-measure.yml` line; owner act #1). Re-score once, on the first run after #1205 merges | posted |
| #1069 | 0 `user_identified` events in the first clean 28-day window (701 before) | baseline this run: `user_identified` 797, `feature_view` 780, window almost wholly pre-deploy | **pending, scoreable from 2026-12-20** (deploy PR #1234, 2026-11-19T02:30Z) | posted pending note; timer written |
| #685 (confound, still pending) | CTR of `/learn/sade-sati/` ≥ 1.2% on ≥ 1,200 impressions, window from 2026-12-04 | W: 17 / 2,125 = 0.80% at 6.6 (**not a score**; W contains pre-deploy days) | pending | posted the index confound (§9): last crawl 2026-10-23, before the 11-03 title change |

### Clean windows already scored (re-read this run, nothing posted)

| issue | predicted | W actual (10-21 → 11-17) | earlier score on the issue | verdict now |
|---|---|---|---|---|
| **#311 MISS** | four pages' combined CTR ≥ 1.5% on ≥ 1,500 impressions, position within ±1 | **59 / 6,479 = 0.91%**, impressions-weighted position 6.58 | 2026-11-13: 0.937% on 5,658 → MISS | **MISS, unchanged.** Bar missed by 0.59 pt. Per page: career-problems 21 / 1,077 = 1.95% (5.9), debilitated-sun 16 / 2,945 = 0.54% (6.5), manglik 4 / 492 = 0.81% (6.5), jupiter-10th 18 / 1,965 = 0.92% (7.1). The rise sits on career-problems |
| **#276 BAR MET, not attributable** | `pages_per_session` ≥ 1.20 on ≥ 20 organic sessions | Organic Search **1.64** on **66** sessions (`/learn/rahu-mahadasha-ketu-antardasha/`) | 2026-11-14: 1.42 on 55 | **Unchanged.** Number 1.61 → 1.64 is not material. Still not attributable: #680 (2026-11-02) and #830 (2026-11-09) also changed this article; `cta_click` shows 1 click from this page to `/dasha` in W |
| **#329 UNSCOREABLE** | ≥ 1.30 on ≥ 10 organic sessions | Organic **4** sessions (floor 10) | 2026-11-14: 3 vs 10, scoring stopped | **Stopped as the issue's own floor requires.** 4 vs 10 |

**Misses as plainly as hits: #311 did not reach its bar; #329 cannot be scored at this traffic; #1115's metric is not met until the workflow line (#1205) lands.** #276 reads as a hit on the metric but I do not claim the CTA caused it.

### Pending (a window cannot be clean before its date); a note already exists on each; one timer line written for each

| issue | deploy (merge) | scoreable from |
|---|---|---|
| #553 | 2026-10-31 | 2026-12-01 |
| #426 | 2026-11-02 | 2026-12-03 |
| #508, #685, #570 | 2026-11-03 | 2026-12-04 |
| #518 | 2026-11-06 | 2026-12-07 |
| #528 | 2026-11-09 | 2026-12-10 |
| #735 | 2026-11-11 | 2026-12-12 |
| #835 | 2026-11-13 | 2026-12-14 |
| #1066, #1093 | 2026-11-15 | 2026-12-16 (both need an export that does not exist, #1237) |
| #1073, #1074, #1075 | 2026-11-16 | 2026-12-17 |
| #1067, #1068, #1072, #1175, #1071 (guard) | 2026-11-17 | 2026-12-18 (#1068 also needs the server count, **#1272**; #1071's main read 2027-02-28) |
| #1217, #1226, #1229 | 2026-11-18 | 2026-12-19 |
| #1069 | 2026-11-19 | 2026-12-20 |

Deploy dates for all of these were read from the closing PR's `mergedAt` this run.

**Timers: 24 lines written to `/tmp/analyst-timers.txt`.** I verified one end of the loop: `#685` carries a `github-actions[bot]` marker `key=score-685 due=2026-12-04` written 2026-11-18T02:48Z. I did not check the other markers.

### Not scoreable from GA4/GSC (structural counts, noted once on the issues earlier)
#1176, #1177, #1178, #1080, #1083, #843, and the infra issues. I did not re-read them.

**Two things to watch in the pending list, stated now, scored on their dates:**
- **#508 (`/matching`)**: its pass condition needs ≥ 300 impressions at a position within ±1.5 of 4.3. In W, `/matching` has 122 impressions at 9.2. On today's numbers the score would read **INCONCLUSIVE, not a pass**. Not a score, because W still contains pre-deploy days. Same page as #1076.
- **#835 / #1073 / #1075** families show their baseline queries in the 14% view: `sun debilitated in which sign` 323 impressions (0 in P) at 7.4, 1 click; `jupiter in 10th house` 113 at 11.1, 0 clicks; `10th lord in 6th house` 94 at 8.6, 2 clicks. **The Rahu, Jupiter-10th and 7th-lord pages were edited after Google's last crawl (§9), so the edits the scores will measure may not have been seen by Google yet.**

## 4. Confounds

| confound | state |
|---|---|
| Concurrent ships | **522 PRs merged since 2026-10-21.** `git log origin/main --since=2026-10-21` returns **1 commit**: the checkout is shallow (`git rev-parse --is-shallow-repository` = true; #666, #974). No movement in §1 or §2 is attributable to one ship |
| Google's crawl | **New this run.** The ten highest-impression pages are all flagged "changed after Google's last crawl" (§9). A change that Google has not re-fetched cannot have moved that page's ranking or snippet, so a score on those pages may measure the old page |
| Seasonality | Diwali, Dhanteras, Chhath inside W. The top 10 pages are not festival pages. No prior-year window exists |
| Was the page reachable | `verify-production.yml`, last 40 runs (2026-11-17T10:46Z → 11-19T23:35Z): **33 success, 5 cancelled, 2 failure.** Both failures (11-17 13:27Z and 18:12Z) are the step "Wait for the deploy" (#341 open), not a page assertion. A green run does not say every page rendered for every visitor |
| Sample size | 780 sessions in 28 days. A swing of 5–10 sessions a day is noise; per-landing figures under about 20 sessions carry no conclusion |
| Automated traffic | Three of seven elevated days carry zero-engagement rows (§1). Direct is 21% engaged |
| Event counts | `kundli_generated` and `ask_answered` over-counted re-renders until #1157 (merged 11-17, near W's end). `cta_click` history starts 11-03 |

## 5. Funnel (events, W) and lever 2: where time is spent

`ga4-events.json`, 2026-10-21 → 11-17, 5,224 events:

| event | count |
|---|---:|
| page_view | 1,355 |
| user_identified | 797 |
| session_start | 781 |
| feature_view | 780 |
| first_visit | 648 |
| form_start | 135 |
| ask_answered | 126 |
| kundli_generated | 52 |
| cta_click | 17 |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |
| dasha_deep_dive_viewed | 2 |

- **`cta_click` 17 in W (split available):** 8 have `(not set)` for both paths. The other 9: `career-during-sade-sati` → `/` 2, `sade-sati` → `/kundli` 2, and one each `kaal-sarp-dosh` → `/kaal-sarp-check`, `krittika-nakshatra` → `/`, `name-numerology-explained` → `/numerology`, `rahu-mahadasha-ketu-antardasha` → `/dasha`, `saturn-in-10th-house-career` → `/kundli`. 17 clicks on 780 sessions is under 2.2%, history partial.
- **No landing → form → result → second-page rate can be computed.** `form_start` (135) and `kundli_generated` (52) are totals across several forms and mostly pre-#1157; `form_submit` = 1 is an instrumentation fact, not a user fact. The completion events from #1217, `tool_submitted` from #1226 (shipped 11-18) are not in `ga4-events.json` for W.

`verify-first.json`, ranked by engaged sessions, W:

| page | sessions | engaged | engaged rate | avg engagement | GSC impr / clicks / position |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 78 | 47 | 60% | 143s | 3,822 / 63 / 6.4 |
| / | 68 | 43 | 63% | 234s | 212 / 9 / 5.8 |
| /muhurat/griha-pravesh | 32 | 30 | **94%** | 89s | 384 / 21 / 6.1 |
| /learn/gochar-2026-planetary-transits | 42 | 17 | **40%** | **29s** | 2,694 / 24 / 5.1 |
| /learn/rahu-mahadasha-career-problems | 24 | 15 | 62% | 275s | 1,077 / 21 / 5.9 |
| /learn/sade-sati | 21 | 14 | 67% | 251s | 2,125 / 17 / 6.6 |
| /learn/10th-lord-in-6th-house-career | 26 | 13 | 50% | 98s | 783 / 21 / 6.7 |
| /learn/career-during-sade-sati | 26 | 12 | 46% | 217s | 1,267 / 23 / 5.5 |
| /learn/7th-lord-placement-marriage-guide | 27 | 11 | 41% | 57s | 1,492 / 14 / 7.2 |
| /learn/jupiter-in-10th-house-career | 23 | 10 | 43% | 65s | 1,965 / 18 / 7.1 |

Site: **43.6% engaged, 105.7s engagement per session** (session-weighted over the 782 row-sessions). By channel: Organic Search 475 sessions, 58% engaged, 141s; Direct 300, 21%, 47s; AI Assistant 6, 50%, 213s. `/learn/*` landings are 518 of 782 sessions (66%).

**Tool landings, W:** `/kundli` 22 sessions (Direct 18, Organic 4; 7 engaged, 43s); `/numerology` 23 (Organic 12, Direct 11; 8 engaged, 85s); `/matching` 18 (Direct 13; 4 engaged); `/muhurat/griha-pravesh` 32 (Organic 31; 30 engaged, 89s).

Read: the best-engaged page, `/muhurat/griha-pravesh` (94%), is a tool page fed entirely by search. The pages that win impressions engage far less: gochar-2026, 7th-lord and jupiter-10th at 40–43% for 29–65s. Pages per session: Rahu–Ketu 1.54, gochar-2026 1.12, 7th-lord 1.11, jupiter-10th 1.30 vs `/` 4.22; Organic Search overall 1.75. The homepage is the only landing that reliably produces a second page.

## 6. Errors (lever 3)

| source | what it says | tracked by |
|---|---|---|
| `llm-usage.json`, 7 days to 2026-11-20T01:59Z | 171 calls, 136 hits (79%), 35 misses; 112,190 input and 20,431 output tokens; `peak_day_tokens` 6,529 (2026-11-18) and `peak_day_measured_tokens` 43,421 (2026-11-18); the two peak figures differ and I do not know why | #925 |
| per route | natal 116 calls, 107 hits (92%), 6,513 tokens per measured call (9 measured); rashifal 28 calls, 28 hits, tokens null (served from cache); ask 22 calls, **0 hits**, 2,078 tokens per call; today 4 calls, 1 hit; monthly 1 call, 0 hits | — |
| **errors / fallbacks per route** | **not in the file.** No error or fallback field exists, so I cannot report an error count for any route | **#1208** (open) |
| `verify-production.yml`, last 40 runs 11-17 → 11-19 | 33 success, 5 cancelled, 2 failure, both "Wait for the deploy" on 11-17 | #341 |

**I cannot say whether any route is failing for visitors.**

## 7. Search demand (lever 4) — query mode, 14% coverage (4,233 of 29,253 impressions)

Themes by first-matching regex on the query text; the query export has no page column, so the page is named by topic, **not measured**. I propose no page.

| theme (query rows) | impressions W / P | clicks W | position | existing page |
|---|---|---:|---|---|
| Rahu Mahadasha / Ketu Antardasha (53) | 1,009 / 556 | 23 | head `rahu mahadasha ketu antardasha` 6.6 (P 9.8), 410 impr, 13 clicks | `/learn/rahu-mahadasha-ketu-antardasha/` (#1075 shipped effects and remedies sections; pending) |
| Sun debilitated (33) | 1,051 / 3 | 2 | `which sign` 323 at 7.4 (1 click), `is … in which sign` 143 at 6.6 (0), `sign` 84 at 5.9, `degree` 54 at 6.5 | `/learn/debilitated-sun-career/` (0.54% CTR; #835 pending) |
| Jupiter in 10th (50) | 420 / 0 | 1 | `jupiter in 10th house` 113 at 11.1, `guru in 10th house` 76 at 8.9 | `/learn/jupiter-in-10th-house-career/` (#1073 pending) |
| 10th lord in 6th (6) | 154 / 0 | 2 | `10th lord in 6th house` 94 at 8.6 | `/learn/10th-lord-in-6th-house-career/` |
| 7th house / lord (45) | 157 / 0 | 2 | spread thin, 12–18 impressions per query | `/learn/7th-lord-placement-marriage-guide/`, `/learn/planets-in-7th-house-marriage/` |
| mahadasha, career (31) | 132 / 1 | 0 | `which mahadasha is best for career` 44 at 8.8, 0 clicks | #1072 shipped a section on `vimshottari-dasha-explained`; pending |
| Sade Sati / Shani (86) | 234 / 54 | 3 | `7.5 sani` 13 at 5.9, `7.5 years shani effects` 13 at 6.5 | `/learn/sade-sati/` (2,125 impressions, 0.80% CTR) |
| Manglik / Mars (62) | 128 / 62 | 1 | `mangal dosha cancellation` 15 at 16.5; `what is manglik dosh` fell 15 → 1 | `/learn/manglik-dosh/` |
| `bhagya chart` (26) / `cheiro numerology calculator` (17) | 26 vs 10 earlier; 17 | — | 6.5 and 5.8 | landing page **not determined** from the query export; `/numerology` overall 174 impr, 10 clicks, position 6.2 |

- **Queries with no page:** in the visible 14% I found none with ≥ 10 impressions that lacks an existing page by topic. This is not proof that none exist in the invisible 86%. `yes` (105 impressions, 3.6, 0 clicks) is not a topic.
- **Low CTR with real position:** the head `sun debilitated` family has about 700 impressions in the 5.9–8.9 range for 2 clicks. The page's own CTR is the lowest of the band's large pages (0.54%).
- `/hi/rashifal/*`: 77 impressions in W, 0 in P, 0 clicks; the Hindi pages exist and are being shown (#124 covers the Hindi URL work).
- `/festivals` is at position 37.1 (288 impressions, 0 clicks), P 29.4.

## 8. Content opportunities (lever 5) — time-bound demand

Dates **only from `festivals.py`**, read this run (`festivals_for_date()` over 2026-11-20 → 2027-01-18):

| date | entry | existing page |
|---|---|---|
| 2026-11-20 | `devuthani-ekadashi` | no dedicated `/learn` template by name (`ls templates/learn \| grep` for devuthani, tulsi, makar, pongal returns none); `/festivals`, `/muhurat/vivah` (24 impr, 1 click, position 5.5 in W) |
| 2026-11-21 | `tulsi-vivah` | same |
| 2027-01-15 | `makar-sankranti`, `pongal` | no dedicated page by name |

- **`festivals.py` holds no entry between 2026-11-22 and 2027-01-14** (54 days). I do not know which festivals fall there and supply no dates. This is a finding about the file; product-manager and the corpus decide.
- **Search signal for these dates, visible 14%:** the only time-bound queries are Diwali muhurat queries at 1 impression each and a few 2027 muhurat queries at 1 each. No query names `devuthani`, `tulsi vivah`, `makar sankranti` or `pongal`. **No demand is readable for those dates this run.**
- Time-bound pages in W: `/muhurat/griha-pravesh` is the best-engaged page on the site (32 sessions, 30 engaged, 89s; 384 impressions at 6.1, 21 clicks). `learn/vivah-muhurat-2027` 41 impressions at 9.2 (P 54), 0 clicks, **crawled, not indexed**. `learn/griha-pravesh-muhurat-2026-2027` 34 → 0 impressions, **crawled, not indexed**. `learn/diwali-muhurat-2026` is past its date.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` is the site's third-largest page (2,694 impressions at 5.1, 24 clicks, 42 sessions at 40% engaged, 29s). **`gochar-2027-planetary-transits` exists, and the index file reads "URL is unknown to Google"** (sitemap priority 0.7, no crawl time) as of 2026-11-19. #1071's main metric (0 → ≥ 300 impressions by 2027-02-28) cannot start moving until Google knows the URL.

## 9. Index status (lever 6) — `measurements/index-status.json`, generated 2026-11-19T20:05Z

First run with this file. Counts: **214 inspected, 0 errors; 166 indexed (78%), 48 not indexed; 0 canonical mismatches, 0 blocked.**

| coverage state | URLs | where |
|---|---:|---|
| Submitted and indexed | 166 | — |
| Crawled – currently not indexed | 29 | almost all `/learn/*` |
| Discovered – currently not indexed | 12 | `/panchang/*` 10, `/muhurat`, `/hi/rashifal/virgo` |
| URL is unknown to Google | 7 | `/dasha`, `gochar-2027-planetary-transits`, 5 dated `/panchang/*` |

By section, not indexed: `/learn` 29, `/panchang` 15, `/muhurat` 2, `/dasha` 1, `/hi` 1. 25 of the 48 carry impressions in the file's source window.

**Not indexed, ranked by impressions (file's impression source = committed `measurements/gsc-all.json`, not W):**

| page | impressions | state | last crawl |
|---|---:|---|---|
| /learn/pushya-nakshatra/ | 124 | Crawled – not indexed | 2026-10-29 |
| /learn/ashwini-nakshatra/ | 89 | Crawled – not indexed | 2026-09-18 |
| /learn/mars-remedies/ | 71 | Crawled – not indexed | 2026-11-09 |
| /learn/vivah-muhurat-2027/ | 42 | Crawled – not indexed | 2026-10-01 |
| /learn/rohini-nakshatra/ | 41 | Crawled – not indexed | 2026-10-06 |
| /learn/jupiter-remedies/ | 39 | Crawled – not indexed | 2026-09-18 |
| /learn/swati-nakshatra/ | 32 | Crawled – not indexed | 2026-10-29 |
| /learn/dhana-yoga-wealth-combinations/ | 31 | Crawled – not indexed | 2026-10-11 |
| /learn/the-9-grahas-overview/ | 24 | Crawled – not indexed | 2026-09-12 |
| /learn/marriage-delayed/ | 23 | Crawled – not indexed | 2026-11-13 |

These are small. The not-indexed set holds no page with more than 124 impressions, so it is not what explains the site's top-of-band pages.

**Changed after Google's last crawl (`request_indexing`, top 10 by impressions — all ten):**

| page | impressions | changed | Google's last crawl |
|---|---:|---|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,912 | 2026-11-16 | 2026-11-08 |
| /learn/gochar-2026-planetary-transits/ | 2,512 | 2026-11-17 | 2026-11-10 |
| /learn/sade-sati/ | 2,133 | 2026-11-15 | **2026-10-23** |
| /learn/jupiter-in-10th-house-career/ | 1,940 | 2026-11-16 | 2026-11-11 |
| /learn/7th-lord-placement-marriage-guide/ | 1,509 | 2026-11-16 | 2026-11-08 |
| /learn/career-during-sade-sati/ | 1,239 | 2026-11-16 | 2026-11-12 |
| /learn/planets-in-7th-house-marriage/ | 1,221 | 2026-11-14 | **2026-11-01** |
| /learn/rahu-mahadasha-career-problems/ | 1,044 | 2026-11-16 | 2026-11-11 |
| /learn/10th-lord-in-6th-house-career/ | 762 | 2026-11-18 | 2026-11-11 |
| /learn/mangal-mars-in-vedic-astrology/ | 557 | 2026-11-14 | 2026-11-10 |

The file says its own staleness test is conservative (commit-based; 174 of 214 URLs read stale), so this is a "may not have been seen" list, not a proof. Two readings with weight: **`sade-sati` was last crawled 2026-10-23, before #685's 11-03 title change** (posted on #685), and **`planets-in-7th-house-marriage` was last crawled 2026-11-01**, before most of its recent edits. The pending scores for #685, #835, #1073, #1075 and #1072 each read a page whose live edits Google may not have re-fetched; I will read `lastCrawlTime` for the URL when each is scored.

**Cannot settle:** how long Google takes to re-crawl. The measurement is the next inspection run's `lastCrawlTime` against `changed_at` for these ten.

## 10. Measurement gaps (lever 7), checked against my last three reports (11-17, 11-18, 11-19)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window | yes (all three, and this run) | **#1205** (owner act #1); #1115 closed with the code half | none: covered |
| Source of the elevated days under the spike bar | yes in 11-17, 11-18, 11-19 | #1236 | **resolved this run**: 7 of 7 named, scored HIT |
| `page_location` (query strings) in GA4 exports | yes | **#1237** | none: covered |
| Errors / LLM fallbacks per route | yes | **#1208** | none: covered |
| Index status per URL | yes in all three | #1065 (its remaining step is a workflows edit) | **resolved as a measurement this run**: the file exists |
| Per-page × per-day export | yes | **#953** | none: covered; this is why the `/matching` onset is undated |
| Full git history (shallow checkout) | yes | **#666**, **#974** | none: covered. `git log --since` returned 1 commit again |
| **Server-side count of completed `POST /reading` / kundli submissions** (#1068's metric compares it with `kundli_generated`) | **11-18, 11-19 and this run** (three consecutive reports including this one) | none | **filed #1272** |
| Which page serves which query (query export has no page column) | 11-17 and 11-19 and this run; 11-18 mapped by topic without stating a gap | none | **not filed**: not named in all three; recorded here. If next run names it too it meets the rule |

## 11. What I did this run

| action | result |
|---|---|
| Comments posted | **#1236** (HIT 7 of 7), **#1115** (not met, blocked on #1205), **#1069** (pending to 2026-12-20), **#685** (index confound), **#1068** (pointer to #1272) |
| Issues filed | **#1272** — no export carries the server-side kundli submission count. Evidence Block passes `verify_issue_evidence.py` |
| Timers | 24 lines in `/tmp/analyst-timers.txt` (22 carried forward, plus `#1069` and the second `#1071` key; #1115 gets no timer because its re-score waits on #1205, not on a date) |
| Re-read, nothing posted | #311 (MISS, 0.91%), #276 (bar met, 1.61 → 1.64), #329 (stopped, 4 vs 10): no verdict changed and no number moved past what the metric calls material |

## 12. What I could not determine, and the one measurement that settles each

| unknown | measurement |
|---|---|
| Whether site-level growth is the work or Google re-ranking a young domain | a pre-ship or year-earlier window does not exist; #953's per-page × per-day export plus the dated ship list would split it |
| Which ship moved which page | full git history in the analyst checkout (#666, #974) |
| Onset day of the `/matching` fall (4.3 → 9.2) and whether #508 caused it | `fetch_gsc.py --page-daily` for `/matching` (#953, #1076) |
| Sessions and users against the previous window | #1205 |
| Whether any route is erroring for visitors | #1208 |
| Whether the 86% of impressions outside the query view change the top-5 objective | cannot be recovered; Google withholds it |
| Whether the kundli GA4 event is now honest | server-side count (#1272) |
| Whether Google has re-fetched the ten edited pages in §9 | next index-status run's `lastCrawlTime` against `changed_at` |
| Why `griha-pravesh-muhurat-2026-2027` took 9 Organic sessions while the index file reads "not indexed" | a URL Inspection reading on a date inside W; the file is dated 11-19 |
| Whether the fall in 11-15 → 11-17 impressions (1,110, 908, 811) held | the next run's daily rows |
| Why `peak_day_tokens` (6,529) and `peak_day_measured_tokens` (43,421) differ for 2026-11-18 | the field definitions in `collect_llm_usage.py`; I did not read it |
