# Analyst report — 2026-11-19

**Window for every number: W = 2026-10-20 → 2026-11-16** (28 days; the last 3 are excluded because GSC lags 2–3 days and GA4 24–48h). **Previous window P = 2026-09-22 → 2026-10-19** (GSC only; there is no GA4 previous window, see §10).
Everything below was read from the files this run fetched. Anything I did not read is marked **not measured**.

## 0. What was in this run

| file | read | coverage / note |
|---|---|---|
| `gsc-band.json` | yes | `dimension: page`; coverage 100% of 28,918 impressions; **emitted** 97 pages at position 6–20 = 21,667 impressions (75%); not truncated |
| `gsc-all.json` | yes | page mode, 141 pages, 100%, not truncated |
| `ga4.json` | yes | landing × channel, 154 rows, 101 landings (94 distinct paths after folding query strings and trailing slashes), 100% of 776 sessions, not truncated |
| `gsc-daily.json`, `ga4-daily.json` | yes | 28/28 days with traffic. GA4 daily rows sum to **780** sessions vs **776** in `ga4.json` (4 apart; I quote each from its own file) |
| `gsc-trend-page.json` | yes | page mode W vs P, 100% |
| `gsc-trend-query.json` | yes | **query mode covers 14% of impressions** (4,167 of 28,918). Google withholds the rest; it describes only the visible share |
| `ga4-events.json` | yes | 17 event names, 5,222 events, not truncated. `cta_click` exists only from 2026-11-03 |
| `ga4-anomalies.json` | yes | 2 spike days (rule: active users ≥ max(2×median, median+10, 15)) |
| `gsc-discover.json` | yes | **0 clicks, 0 impressions on all 28 days** (a measured zero) |
| `verify-first.json` | yes | 10 busiest pages |
| `measure/llm-usage.json` | yes | trailing 7 days, generated 2026-11-19T07:54Z. **Has no error or fallback field** (#1208) |
| `index-status.json` | **absent** | not measured (#1065 open) |

## 1. Growth (lever 1)

**Search, GSC, W vs P** (page-row sums; property totals in W are 28,918 impressions / 383 clicks):

| metric | W 10-20 → 11-16 | P 09-22 → 10-19 | change |
|---|---:|---:|---:|
| impressions | 29,002 | 11,652 | 2.49× |
| clicks | 383 | 117 | 3.27× |
| CTR | 1.32% | 1.00% | +0.32 pt |
| pages with any impression | 141 | 127 | +14 |
| query keys visible (14% view) | 843 | 214 | +629 |

**GA4, W only** (no previous window): 776 sessions (`ga4.json`) / 780 (daily rows); sum of daily active users 691; sum of daily new users 640. Organic Search 474 sessions (61%), Direct 295 (38%), AI Assistant 7, Unassigned 2.

**Inside W, by week (daily files):**

| week | GA4 sessions | GSC impressions | GSC clicks |
|---|---:|---:|---:|
| 10-20 → 10-26 | 139 | 4,667 | 47 |
| 10-27 → 11-02 | 152 | 7,522 | 90 |
| 11-03 → 11-09 | 231 | 7,931 | 113 |
| 11-10 → 11-16 | 258 | 8,798 | 133 |

First 14 days vs last 14 days: sessions 291 → 489, impressions 12,189 → 16,729, clicks 137 → 246. The last two days fall back (11-15: 1,110 impr / 14 clicks; 11-16: 908 / 9; 11-16 has 14 GA4 sessions). Two days are not a trend; I draw no conclusion.

**Which page groups drive the GSC change** (`gsc-trend-page.json`, impressions / clicks, W vs P):

| group | impr W | impr P | clicks W | clicks P |
|---|---:|---:|---:|---:|
| `/learn/*` | 27,142 | 10,635 | 326 | 100 |
| `/muhurat/*` | 522 | 92 | 26 | 7 |
| `/festivals` | 293 | 245 | 0 | 0 |
| `/rashifal/*` | 210 | 91 | 1 | 0 |
| `/` | 206 | 103 | 9 | 5 |
| `/numerology` | 174 | 4 | 10 | 0 |
| `/matching` | **124** | **330** | 4 | 0 |
| `/panchang*` | 101 | 91 | 2 | 1 |
| `/kundli` | 98 | 53 | 4 | 4 |
| `/hi/rashifal*` | 77 | 0 | 0 | 0 |

`/learn/*` is 94% of W impressions and 85% of W clicks. The largest single gains in impressions: gochar-2026 (10 → 2,512), rahu-mahadasha-ketu-antardasha (1,996 → 3,912), debilitated-sun-career (1,210 → 2,915), jupiter-in-10th-house-career (369 → 1,940), 7th-lord-placement (259 → 1,509), sade-sati (1,065 → 2,133), career-during-sade-sati (393 → 1,239).

**Seasonal or structural? Both inputs are present and I cannot separate them.**
- Calendar (`festivals.py`, read this run): Dussehra 10-20, Karva Chauth 10-29, Dhanteras 11-06, Diwali 11-08, Bhai Dooj 11-11, Chhath 11-15 are inside W. **None of the ten highest-impression pages is a festival page** (Rahu/Ketu, Sun-debilitated, gochar, Sade Sati, 7th-house, career guides), so the rise is not a festival-page rise. `/muhurat/*` (522 vs 92) is the one group that may follow the wedding / housewarming season.
- Structural: the top gainers are pages the loop edited, and **at least 500 PRs merged since 2026-10-20** (`gh pr list --search merged:>=2026-10-20`, result equal to my 500 cap). I cannot attribute the rise to any one ship.
- Not determinable: how much is Google re-ranking a young domain versus the work. No year-earlier window exists.

**Spike days (`ga4-anomalies.json`), each with its source:**

| date | active users / sessions | source named by the file | GSC clicks that day | Discover | read |
|---|---:|---|---:|---:|---|
| 2026-11-06 (Dhanteras) | 57 / 59 (median 22) | Top row `(direct)/(none)` on `/rashifal/aries` (6 sessions, 17% engaged, 3.5s). **19 of the 50 sessions the file broke down had zero engagement** (no browser name/desktop/US 10, Chrome/desktop/US 6, Chrome/mobile/US 3). Organic readers of `/learn/rahu-mahadasha-career-problems/`: 4 sessions, 224s | 17 (11-05: 17, 11-07: 12) | 0 | **Mixed, not growth.** ~19 sessions look automated; the rest look like readers (Chrome mobile India 8 sessions, 62% engaged, 86s). Search did not spike |
| 2026-11-15 (Chhath) | 51 / 56 (median 22) | Top row google/organic on `/learn/rahu-mahadasha-ketu-antardasha/` (6 sessions, 83% engaged, 242s). **Chrome/mobile/China 9 sessions, 0% engaged, 0s**; Chrome/mobile/India 17 sessions (59% engaged, 61s); 5 Direct sessions on `/panchang/2026-12-02`, 0% engaged, 1.6s | 14 (window mean 13.7) | 0 | **Mixed, not growth.** The China-mobile and dated-panchang sessions look automated. The India readers look real. **Not Discover** |

- Other high days **have no breakdown** because the file only explains flagged days: 10-23 (34 users / 34 sessions), 11-09 (32/37), 11-10 (40/43), 11-12 (34/37), 11-14 (32 users / 47 sessions, the highest sessions-per-user, 1.47). I cannot name their source. Tracked by **#1236**.
- **Direct is not clean.** Direct is 38% of sessions at 22% engaged against 57% for Organic Search; 17 of the 776 sessions landed on `/admin/ops` (internal; #735's fix merged 2026-11-11, so W is mostly before it and I cannot split by day). `/learn/financial-struggles` took 9 Direct sessions, 0 engaged, against 4 GSC impressions. I do not treat Direct as audience.
- Discover is zero on every day.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page mode measures pages (a page's position is its average across its queries). **Query mode covers 14%, so the objective is only readable on the visible share.**

**Band, page mode, W** (`emitted_*`, 75% of impressions): **97 pages, 21,667 impressions, 273 clicks, impressions-weighted CTR 1.26%.** 82 of the 97 sit at position ≤ 10 (21,423 impressions). **62 of the 97 had zero clicks**, on 1,190 impressions (5.5% of the band).

Top 10 by `band_opportunity`:

| # | page | impr W | clicks W | CTR W | position W | impr P / position P |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,912 | 63 | 1.61% | 6.4 | 1,996 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,915 | 16 | 0.55% | 6.5 | 1,210 / 6.1 |
| 3 | /learn/sade-sati/ | 2,133 | 16 | 0.75% | 6.6 | 1,065 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,940 | 18 | 0.93% | 7.1 | 369 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,509 | 14 | 0.93% | 7.2 | 259 / 7.9 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,221 | 11 | 0.90% | 6.8 | 563 / 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,016 | 15 | 1.48% | 7.1 | 441 / 6.9 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 557 | 3 | 0.54% | 7.6 | 121 / 7.8 |
| 9 | /learn/10th-lord-in-6th-house-career/ | 762 | 20 | 2.62% | 6.7 | 182 / 7.0 |
| 10 | /learn/manglik-dosh/ | 489 | 4 | 0.82% | 6.5 | 469 / 7.5 |

Top-5 reading on what is visible: no page in the top 10 by impressions has an average position ≤ 5.0 (gochar-2026 is closest at 5.1, 2,512 impressions, 24 clicks; career-during-sade-sati 5.4). In the 14% query view only **1 of the 10 highest-impression queries is at position ≤ 5, and it is `yes` (3.6, 101 impressions), a query nobody targets**; the real head query `rahu mahadasha ketu antardasha` is at 6.7 (was 9.8) on 424 impressions (was 259) with 13 clicks. The objective is **not met** on the visible share; the other 86% cannot be read.

**CTR outliers.** Pages in the band with ≥ 500 impressions, position ≤ 7.5 and CTR below the band's own impressions-weighted 1.26% (the band's *median* CTR is 0, so I used the weighted rate):

| page | impr | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,915 | 16 | 0.55% | 6.5 |
| /learn/sade-sati/ | 2,133 | 16 | 0.75% | 6.6 |
| /learn/jupiter-in-10th-house-career/ | 1,940 | 18 | 0.93% | 7.1 |
| /learn/7th-lord-placement-marriage-guide/ | 1,509 | 14 | 0.93% | 7.2 |
| /learn/planets-in-7th-house-marriage/ | 1,221 | 11 | 0.90% | 6.8 |
| **five pages** | **9,718** | **75** | **0.77%** | |

At the band's 1.26% these five would have taken ~122 clicks, not 75. The in-band reference at a similar position is `10th-lord-in-6th-house` at 2.62% (762 impr, position 6.7) and `rahu-mahadasha-ketu-antardasha` at 1.61%. `debilitated-sun-career` has the largest gap (#835 and #311 target it; see §3).

**Decay** (position worse by ≥ 1.5 and ≥ 50 impressions in either window; GSC page mode, W vs P):

| page | impr W / P | clicks W / P | position W / P | note |
|---|---|---|---|---|
| /matching | **124 / 330** | 4 / 0 | **9.1 / 4.3** | the only finding that matters here: the page lost 62% of its impressions and 4.8 positions. #508's title/meta test shipped 2026-11-03 inside W. **#1076** is the open investigation; this run does not date the onset (needs `--page-daily`, #953) |
| /learn/magha-nakshatra/ | 115 / 17 | 4 / 0 | 7.3 / 5.6 | impressions rose 7×, so position fell on a changed query mix |
| /learn/diwali-muhurat-2026/ | 75 / 2 | 1 / 0 | 11.1 / 7.0 | event passed 11-08 |
| /learn/shani-saturn/ | 99 / 7 | 0 / 0 | 9.7 / 7.1 | small |
| /learn/the-9-grahas-overview/ | 24 / 104 | 0 / 0 | 9.8 / 7.9 | impressions fell 77% |
| /festivals | 293 / 245 | 0 / 0 | 36.0 / 29.5 | far outside the band |
| /learn/ashwini-nakshatra/ | 89 / 103 | 1 / 1 | 7.7 / 5.6 | |

Pages gone from W (impressions in P, 0 in W): `ketu-in-vedic-astrology` (62), `griha-pravesh-muhurat-2026-2027` (36). The second is a time-bound article; it still took 14 GA4 sessions in W (9 Organic, 86% bounce).

## 3. Post-ship scores (issues closed in the last 45 days with `thesis:` and `metric:`)

**I re-read the comment thread on every issue before writing. No new comment was posted this run: every thread already holds its pending note, its score, or its "not scoreable from GA4/GSC" note, and none of the clean verdicts moved.** The 28-day check below is the re-read of the three clean scores.

### Clean windows already scored (re-read this run, unchanged, nothing posted)

| issue | predicted (`metric:`) | W actual (10-20 → 11-16) | earlier score on the issue | verdict now |
|---|---|---|---|---|
| **#311 MISS** | four pages' combined CTR ≥ 1.5% on ≥ 1,500 impressions, position within ±1 | **59 / 6,388 = 0.92%**, position 6.57 (P: 18 / 2,880 = 0.63%, W above) | 2026-11-13: 0.937% on 5,658 → MISS | **MISS, unchanged.** Bar missed by 0.58 pt. Per page W: career-problems 21 / 1,044 = 2.01% (5.8), debilitated-sun 16 / 2,915 = 0.55% (6.5), manglik 4 / 489 = 0.82% (6.5), jupiter-10th 18 / 1,940 = 0.93% (7.1). Three of four moved a little; the rise sits mostly on career-problems |
| **#276 BAR MET, not attributable** | `pages_per_session` ≥ 1.20 on ≥ 20 organic sessions | Organic Search **1.61** on **69** sessions; all channels 1.52 on 81 sessions | 2026-11-14: 1.42 on 55 → bar met, not attributable | **Unchanged.** The number moved (1.42 → 1.61), the verdict did not. Still not attributable: #680 (2026-11-02) and #830 (2026-11-09) also changed this article, and `cta_click` shows 1 click from this page to `/dasha` in W (partial history from 11-03) |
| **#329 UNSCOREABLE** | ≥ 1.30 on ≥ 10 organic sessions | Organic **4** sessions (floor 10) | 2026-11-14: unscoreable, 3 vs 10, scoring stopped | **Stopped as the issue's own floor requires.** 4 vs 10 |

Misses reported as plainly as hits: **#311 did not reach its bar, and #329 cannot be scored at this traffic.** #276 reads as a hit on the metric but I do not claim the CTA caused it.

### Pending (a window cannot be clean before its date); a note already exists on each, one timer line written for each

| issue | deploy | scoreable from | note on the issue |
|---|---|---|---|
| #426, #553 | 11-02 / 10-31 | 12-03 / 12-01 | yes |
| #508, #685, #570 | 11-03 | 12-04 | yes (#570 also waits on the cta_click export; it now exists, 17 events in W) |
| #518 | last slice 11-06 | 12-07 | yes |
| #528, #735 | 11-09 / 11-11 | 12-10 / 12-12 | yes |
| #835 | 11-13 | 12-14 | yes |
| #1066, #1093 | 11-15 | 12-16 | yes; both need an export that does not exist (**#1237**) |
| #1073, #1074, #1075 | 11-16 | 12-17 | yes (#1074's floor of 150 impressions is at risk) |
| #1067, #1068, #1071, #1072, #1175 | 11-17 | 12-18 | yes (#1071's main read is 2027-02-28) |
| #1217, #1226, #1229 | 11-18 | 12-19 | yes; baseline is zero by construction: none of their event names appear in W's `ga4-events.json` |

Timers: **22 lines written to `/tmp/analyst-timers.txt`**, one per pending issue, in the exact format.

### Not scoreable from GA4/GSC (structural counts, noted once on the issues)
#1176, #1177, #1178, #1080, #1083, #843, plus the earlier infra issues (#523/#513/#514/#515 are marked "unscoreable at this traffic").

**Two things to watch inside the pending list, stated now, scored on their dates:**
- **#508 (`/matching`)**: its pass condition needs position within ±1.5 of 4.3 and ≥ 300 impressions. In W, `/matching` has 124 impressions at position 9.1 (4 clicks, 3.2% CTR). Both guards would currently trip, so on today's numbers the score would read **INCONCLUSIVE, not a pass**, and this is the same page #1076 is investigating. Not a score, because W still contains pre-deploy days.
- **#835 / #1073 / #1075 families** show their baseline queries in the 14% query view: `sun debilitated in which sign` 319 impressions (0 before) at 7.5, 1 click; `jupiter in 10th house` 112 impressions at 11.1; `10th lord in 6th house` 94 at 8.6 with 2 clicks. Most of these shipped after or at the end of W, so none is an effect yet.

## 4. Confounds

| confound | state |
|---|---|
| Concurrent ships | **≥ 500 PRs merged since 2026-10-20** (my `gh` search returned exactly the cap I set). `git log origin/main --since=2026-10-20` returns **1 commit** because the checkout is **shallow** (`git rev-parse --is-shallow-repository` = true; #666, #974). No movement in §1 or §2 is attributable to one ship |
| Seasonality | Diwali week is inside W. The top 10 pages are not festival pages. No prior-year window exists |
| Was the page reachable | `verify-production.yml`, last 40 runs (2026-11-17T08:10Z → 11-19T07:09Z): **32 success, 5 cancelled, 3 failure.** All 3 failures are the step "Wait for the deploy" on 2026-11-17 (08:10Z, 13:27Z, 18:12Z) — a deploy-wait failure (#341 open), not an assertion on a page. 11-19 runs are all green. A green run does not say every page rendered for every visitor |
| Sample size | 776 sessions in 28 days. A swing of 5–10 sessions a day is noise; per-landing figures under ~20 sessions carry no conclusion |
| Automated traffic | Both spike days carry zero-engagement rows (see §1). Direct is 22% engaged |
| Event counts | `kundli_generated` and `ask_answered` over-count on re-render until #1157 (merged 11-17, after W). `cta_click` history starts 11-03 |

## 5. Funnel (events, W)

`ga4-events.json`, 2026-10-20 → 11-16, 5,222 events, not truncated:

| event | count |
|---|---:|
| page_view | 1,355 |
| session_start | 777 |
| first_visit | 640 |
| form_start | 137 |
| ask_answered | 130 |
| kundli_generated | 52 |
| cta_click | 17 |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |
| dasha_deep_dive_viewed | 2 |

- **`cta_click` 17 in W, split available:** 8 have `(not set)` for both paths; the other 9: `/learn/career-during-sade-sati/` → `/` 2, `/learn/sade-sati/` → `/kundli` 2, and one each from `kaal-sarp-dosh` → `/kaal-sarp-check`, `krittika-nakshatra` → `/`, `name-numerology-explained` → `/numerology`, `rahu-mahadasha-ketu-antardasha` → `/dasha`, `saturn-in-10th-house-career` → `/kundli`. 17 clicks against ~776 sessions is under 2.2%, and history is partial.
- **I cannot compute a landing → form → result → second-page rate:** the completion events for matching, numerology, muhurat and doshas (#1217), `tool_submitted` (#1226) and `--journeys` (#1226) shipped 11-18 and are not in W. `form_submit` = 1 is an instrumentation fact, not a user fact. `kundli_generated` / `form_start` = 38% would be a guess because of the re-render over-count.
- Measured instead, from `ga4.json`: tool landings are small — `/kundli` 19 sessions (Organic 4 sessions at 4 engaged, 177s; Direct 15 at 3 engaged), `/numerology` 23 (Organic 12 at 7 engaged, 161s; Direct 11 at 1), `/matching` 18 (Direct 13 at 1 engaged), `/muhurat/griha-pravesh` 31 (Organic, 30 engaged, 92s).

## 6. Where time is spent (lever 2)

`verify-first.json`, ranked by engaged sessions, W:

| page | sessions | engaged | engaged rate | avg engagement | GSC impr / clicks / position |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 81 | 49 | 60% | 140s | 3,913 / 63 / 6.4 |
| / | 69 | 44 | 64% | 231s | 207 / 9 / 5.7 |
| /muhurat/griha-pravesh | 31 | 30 | **97%** | 92s | 384 / 21 / 6.2 |
| /learn/gochar-2026-planetary-transits | 42 | 17 | **40%** | **29s** | 2,512 / 24 / 5.1 |
| /learn/sade-sati | 19 | 15 | 79% | 278s | 2,133 / 16 / 6.6 |
| /learn/rahu-mahadasha-career-problems | 23 | 14 | 61% | 280s | 1,044 / 21 / 5.8 |
| /learn/career-during-sade-sati | 26 | 12 | 46% | 207s | 1,239 / 22 / 5.4 |
| /learn/10th-lord-in-6th-house-career | 25 | 12 | 48% | 100s | 762 / 20 / 6.7 |
| /learn/jupiter-in-10th-house-career | 24 | 11 | 46% | 74s | 1,940 / 18 / 7.1 |
| /learn/7th-lord-placement-marriage-guide | 27 | 11 | 41% | 57s | 1,509 / 14 / 7.2 |

Site: **43.7% engaged, 107 s average engagement per session** (session-weighted over all 778 landing×channel rows). By channel: Organic Search 474 sessions, 57% engaged, 140s; Direct 295, 22%, 49s; AI Assistant 7, 43%, 184s.

Read: the best-engaged page, `/muhurat/griha-pravesh` (97%), is a tool page that took 31 Organic sessions. The three heaviest pages by impressions after the Rahu page (gochar-2026, 7th-lord, jupiter-10th) engage 40–46% for 29–74 s. Pages per session on the busiest learn landings: Rahu–Ketu 1.52, gochar-2026 1.12, 7th-lord 1.11, jupiter-10th 1.29, vs `/` 4.20. The homepage is the only landing that reliably produces a second page.

## 7. Errors (lever 3)

| source | what it says | tracked by |
|---|---|---|
| `llm-usage.json`, trailing 7 days to 2026-11-19 | 180 calls, 138 hits (76%), 42 misses; 137,410 input and 26,917 output tokens; `peak_day_measured_tokens` 43,421 on 2026-11-18 | — |
| per route | natal 121 calls, 90% hit, 6,557 tokens/measured call (11 measured); rashifal 28 calls, 100% hit, **tokens null** (served from cache); ask 26 calls, 0% hit, 2,143 tokens/call; today 2; monthly 2; dasha_deep_dive 1 | — |
| **errors / fallbacks per route** | **not in the file.** `llm-usage.json` carries no error or fallback field, so I cannot report an error count for any route | **#1208** (open, "errors per route are unmeasured in three consecutive reports") |
| `verify-production.yml` (last 40 runs, 11-17 → 11-19) | 32 success, 5 cancelled, 3 failure; all 3 failures in step "Wait for the deploy" on 11-17 | #341 |
| Groq daily budget | #925 ("Peak day used 83%") and #949 are open; I did not re-measure them from this run's files (the file's `peak_day_measured_tokens` of 43,421 is the only daily figure I read) | #925 |

I cannot say whether any route is failing for visitors.

## 8. Search demand (lever 4) — query mode, 14% coverage (4,167 of 28,918 impressions)

Themes with impressions and the page that already exists. **I propose no page.**

| theme (queries, W) | impressions W / P | position | clicks | existing page |
|---|---|---|---:|---|
| Rahu Mahadasha / Ketu Antardasha, ~15 variants (head `rahu mahadasha ketu antardasha` 424) | 424 vs 259 for the head | 6.7 (was 9.8) | 13 on the head | `/learn/rahu-mahadasha-ketu-antardasha/` (#1075 shipped effects/remedies sections; pending) |
| "sun debilitated" family: `which sign` 319, `is … in which sign` 138, `sign` 82, `debilitation degree` 51, others | ~970 across 34 rows (0 in P for the top ones) | 5.9–8.9 | 1 | `/learn/debilitated-sun-career/` (#835 pending) |
| `jupiter in 10th house` 112, `guru in 10th house` 73, `10th house jupiter` 21 | ~280 | 8.6–11.1 | 0–1 | `/learn/jupiter-in-10th-house-career/` (#1073 pending) |
| `10th lord in 6th house` 94, `10th house lord in 6th house` 29 | 123 | 8.2–8.6 | 2 | `/learn/10th-lord-in-6th-house-career/` |
| `which mahadasha is best for career` 35 | 35 vs 0 | 8.8 | 0 | #1072 shipped a section on `vimshottari-dasha-explained`; pending |
| Shani 7.5 years family (`7.5 years shani effects` 13, `shani 7.5 years` 12, `7.5 years of shani` 9, others) | ~60 | 6.5–9.5 | 1 | `/learn/sade-sati/` (2,133 page impressions, 0.75% CTR) |
| `bhagya chart` 23 | 23 vs 10 | 6.0 | 3 | landing page for this query **not determined** (the query-mode export has no page column); 3 clicks of 23 is a 13% CTR |
| `cheiro numerology calculator` 17 | 17 | 5.8 | 2 | landing page **not determined** from the query export; the `/numerology` page overall has 173 impr, 9 clicks, position 6.2 |

- **Queries with no page:** in the visible 14% I found none with ≥ 10 impressions that lacks an existing page. This is not proof that none exist in the invisible 86%. `yes` (101 impressions, position 3.6, 0 clicks) is not a topic.
- `/hi/rashifal/*`: 77 impressions in W, 0 in P, 0 clicks. `/hi/rashifal/leo` is at position 56.6. The Hindi pages exist and are being shown; #124 covers the Hindi URL work.
- `/festivals` is at position 36.0 (293 impressions, 0 clicks). It was 29.5.

## 9. Content opportunities (lever 5) — time-bound demand

Dates **only from `festivals.py`**, read this run (`festivals_for_date()` over 2026-11-19 → 2027-01-17):

| date | entry in `festivals.py` | existing page |
|---|---|---|
| 2026-11-20 | Devuthani Ekadashi (Prabodhini); its own note says Chaturmas ends and the wedding season reopens | no dedicated `/learn` page found by name; `/festivals`; `/muhurat/vivah` (23 impr, position 5.3, 1 click) |
| 2026-11-21 | Tulsi Vivah | same |
| 2027-01-15 | Makar Sankranti; Pongal | no dedicated page found by name; readable from 2027-01-15, out of W's data |

- **`festivals.py` holds no entry between 2026-11-22 and 2027-01-14** (the one calendar gap, 54 days). I do not know which festivals fall there and do not supply dates. This is a finding about the file, not a page request; product-manager and the corpus decide.
- Time-bound pages in W: `/muhurat/griha-pravesh` is the best-engaged page on the site (31 sessions, 30 engaged, 92s, 384 impressions at 6.2, 21 clicks); `learn/vivah-muhurat-2027` 42 impressions at 9.2, 0 clicks; `learn/griha-pravesh-muhurat-2026-2027` dropped from 36 to 0 impressions; `learn/diwali-muhurat-2026` is past its date (75 impressions at 11.1).
- Annual pages whose year is ending: `learn/gochar-2026-planetary-transits` is the site's third-largest page (2,512 impressions at 5.1, 24 clicks, 42 sessions at 40% engaged and 29 s). **`gochar-2027-planetary-transits` already exists** (shipped under #1071; its metric reads 0 → ≥ 300 impressions in the window ending 2027-02-25, guard on the 2026 page: position no worse than 7.2, today 5.1). `vivah-muhurat-2027` exists. No query in the visible 14% names `devuthani`, `tulsi vivah`, `makar sankranti` or `pongal`, so there is no search signal to read for those dates this run.

## 10. Index status (lever 6) and measurement gaps (lever 7)

**Index status: not measured.** `measurements/index-status.json` does not exist. The one measurement that would settle it is the URL Inspection export in **#1065**.

Gaps in this run, checked against my last three reports (`measurements/2026-11-17.md`, `-18.md`, `-19.md`):

| gap | in all three reports? | open issue |
|---|---|---|
| GA4 previous window (growth for sessions/users cannot be compared) | yes | **#1205** (agent-measure wiring; owner act #1) and the closed **#1115** |
| Source of the days that sit under the spike bar | yes | **#1236** |
| `page_location` (query strings) in GA4 exports, which #1066 and #1093 need | yes | **#1237** |
| Errors / LLM fallbacks per route | yes | **#1208** |
| Index status per URL | yes | **#1065** |
| Per-page × per-day export (cannot split a page at its deploy date; #490's closed fix is not in the nightly run) | yes | **#953** |
| Full git history (shallow checkout; concurrent ships cannot be listed) | yes | **#666**, **#974** |
| Internal / automated traffic share (17 `/admin/ops` sessions, zero-engagement China-mobile and US-desktop rows) | yes (from 11-17) | #735 closed; its effect is invisible here until a post-11-11 window exists; **#1236** covers the breakdown |
| Server-log count of `POST /reading` 303s that #1068's metric compares against `kundli_generated` | I did not find it in the gap lines of those three reports (I searched them for gap wording, not line by line) | no issue found by number; the note on #1068 says it will be declared unscoreable on 2026-12-18 if the count is not supplied. **Not filed** — fewer than three reports, so the rule does not require it |

**Every gap that appears in all three reports already has an open issue, so I filed none.**

## 11. What I did this run

| action | result |
|---|---|
| Issue comments posted | **none** — every issue in the window already carries its pending note, its clean score or its not-scoreable note, and no verdict or material number moved on #311 (MISS 0.937% → 0.924%), #276 (bar met, 1.42 → 1.61) or #329 (stopped) |
| Issues filed | **none** — no finding needs a new issue (`/matching` decay is #1076; the gaps are #1205/#1208/#1236/#1237/#1065/#953/#666/#974) |
| Timers | 22 lines in `/tmp/analyst-timers.txt` |

## 12. What I could not determine, and the one measurement that settles each

| unknown | measurement |
|---|---|
| Whether the site-level growth is the work or Google's re-ranking of a young domain | a year-earlier or pre-ship window does not exist; the per-page × per-day export (#953) plus the dated ship list would split it |
| Which ship moved which page | full git history in the analyst checkout (#666/#974) |
| Onset day of the `/matching` fall and whether #508 caused it | `fetch_gsc.py --page-daily` for `/matching` (#953 / #1076) |
| Sources of the five unexplained high days | #1236 |
| Whether any route is erroring for visitors | #1208 |
| Whether the 86% of impressions outside the query view change the top-5 objective | cannot be recovered; Google withholds it |
| GA4 growth in sessions/users against the previous window | #1205 (needs a workflow edit) |
