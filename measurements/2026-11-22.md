# Analyst report — 2026-11-22

**Window W = 2026-10-23 → 2026-11-19** (28 days; the last 3 are excluded: GA4 lags 24–48h, GSC 2–3 days).
**Previous window P = 2026-09-25 → 2026-10-22** (GSC trend files only).
Everything below was read from this run's files (`/tmp/*.json`, `/tmp/measure/*.json`) unless it says otherwise. Anything I could not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 29,930 impressions | no | 399 clicks |
| `gsc-all.json` / `gsc-band.json` (`dimension: page`) | W | 100%; `rows_impressions` 30,013 vs property 29,930 (a page row can count a query once per page) | no | band printed 97 rows = 22,357 impressions = **75%** (`emitted_coverage_pct`) |
| `gsc-trend-page.json` | W vs P | W 100%; P coverage **not stated** | no | P page-sum = 11,934 impressions, W page-sum = 30,013 |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **15%** | no | Google withholds the rest. 4,354 impressions are visible in the rows. No conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 799 sessions (rows sum 801) | no | 95 distinct paths after folding query strings and trailing slashes (102 raw landings) |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum to 803, vs 799 / 801 in the landing report: three session totals from two GA4 reports, not reconciled |
| `ga4-events.json` | W | 18 event names, `events_total` 5,299 | no | `cta_click` exists only from 2026-11-03 (PR #688): partial history |
| `ga4-anomalies.json` | W | 2 spikes, 5 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | 0 clicks, 0 impressions, `top_pages` empty | – | |
| `verify-first.json`, `llm-usage.json` | W / last 7 days | – | – | `llm-usage.json` generated 2026-11-22T00:53Z, 7 days |
| `measurements/index-status.json` | **generated 2026-11-19T20:05Z, not this run** | 214 of 214 URLs inspected | – | read from the repo checkout; three days older than the other files |
| GA4 previous window | – | **absent** | – | no `ga4-trend.json`. Sessions and users against P are **not measured** (#1205 open) |
| `git log origin/main --since=2026-10-20` | – | **1 commit** | – | checkout is shallow (`git rev-parse --is-shallow-repository` = true; #666, #974). Concurrent ships come from the PR lists on the issues, not from git |

## 1. The 6–20 position band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **That cannot be measured as written**: the query export covers 15% of impressions, and in page mode a band `position` is the page's average across its queries. The table is the page-level proxy.

| metric (W, `dimension: page`) | value |
|---|---|
| pages with impressions | 137 |
| pages at average position < 6 | 31 (most with a handful of impressions) |
| pages at position 6–20 | **97**, 22,357 impressions (75% of the property's), 285 clicks, aggregate CTR **1.27%** |
| of those, pages with ≥ 100 impressions | 28 |
| top-10 pages by impressions that sit at average position ≤ 5 | **1** of 10 (`gochar-2026-planetary-transits`, 5.0) |

Band list, ranked by the file's `band_opportunity` (W; position = page average; P pos from `gsc-trend-page.json`):

| # | page | impr | clicks | CTR | pos | P pos |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/debilitated-sun-career/ | 3,006 | 16 | **0.53%** | 6.5 | 6.1 |
| 2 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,642 | 62 | 1.70% | 6.4 | 7.4 |
| 3 | /learn/sade-sati/ | 2,133 | 17 | **0.80%** | 6.6 | 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 2,047 | 21 | 1.03% | 7.0 | 6.9 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,461 | 13 | 0.89% | 7.3 | 7.7 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,345 | 10 | **0.74%** | 6.8 | 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,051 | 15 | 1.43% | 7.2 | 7.0 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 601 | 3 | **0.50%** | 7.7 | 7.4 |
| 9 | /learn/10th-lord-in-6th-house-career/ | 833 | 24 | 2.88% | 6.8 | 7.0 |
| 10 | /learn/manglik-dosh/ | 485 | 4 | 0.82% | 6.7 | 7.4 |
| 11 | /learn/shukra-venus-in-vedic-astrology/ | 394 | 2 | **0.51%** | 6.1 | – |
| 12 | /learn/saturn-in-10th-house-career/ | 454 | 6 | 1.32% | 7.6 | – |

Top-10 pages by impressions (all positions, W): rahu-ketu 3,642 (1.70%, 6.4) · gochar-2026 3,066 (0.85%, **5.0**) · debilitated-sun 3,006 (0.53%, 6.5) · sade-sati 2,133 (0.80%, 6.6) · jupiter-10th 2,047 (1.03%, 7.0) · 7th-lord 1,461 (0.89%, 7.3) · planets-in-7th 1,345 (0.74%, 6.8) · career-during-sade-sati 1,335 (1.80%, **5.4**, P 7.0) · rahu-mahadasha-career-problems 1,134 (2.03%, **5.8**, P 6.9) · panch-mahapurush 1,051 (1.43%, 7.2). **Nearest to top 5:** career-during-sade-sati (0.4 away) and career-problems (0.8 away); the other seven sit at 6.4–7.3.

### CTR outliers (against the band's own rate: 1.27% aggregate; median CTR of the 18 band pages with ≥ 300 impressions = 1.11%)

| page | impr | CTR | pos | reading |
|---|---:|---:|---:|---|
| debilitated-sun-career | 3,006 | 0.53% | 6.5 | largest gap on the site: at the band's 1.27% it would take about 38 clicks, not 16 (≈ 22 clicks per 28 days). #835 (answer-first lede, merged 2026-11-13) targets it; pending |
| planets-in-7th-house-marriage | 1,345 | 0.74% | 6.8 | position worse by 1.0 (P 5.8 → 6.8) and CTR still about 60% of the band |
| sade-sati | 2,133 | 0.80% | 6.6 | #685 (title names the Moon signs, merged 2026-11-03); pending |
| gochar-2026-planetary-transits | 3,066 | 0.85% | **5.0** | the only top-10 page already at position ≤ 5, and its CTR is 0.85% against 1.80% / 2.03% on the two other pages at 5.4 / 5.8. 45 landings, 38% engaged, 27 s average (`verify-first.json`) |
| mangal-mars / shukra-venus | 601 / 394 | 0.50% / 0.51% | 7.7 / 6.1 | no issue found this run |
| 10th-lord-in-6th-house-career | 833 | 2.88% | 6.8 | the in-band reference at this position |
| /muhurat/griha-pravesh | 379 | 5.54% | 6.3 | best CTR on the site |

### Decay (position worse by ≥ 1.5 with ≥ 50 impressions in either window; `gsc-trend-page.json`)

| page | impr W / P | clicks W / P | pos W / P | note |
|---|---:|---:|---:|---|
| /matching | **119 / 341** | 4 / 0 | **10.0 / 4.4** | lost 65% of impressions and 5.6 positions. Index file (2026-11-19): "Submitted and indexed", last crawl 2026-11-08. #508's title/meta shipped 2026-11-03; **#1076** is the open investigation and onset is still undated (needs the per-page × per-day export, #953) |
| /festivals | 275 / 243 | 0 / 0 | 37.7 / 26.4 | far outside the band |
| /learn/ashwini-nakshatra/ | 85 / 88 | 1 / 1 | 7.8 / 5.6 | index file: "Crawled – currently not indexed" |

Pages that left GSC in W (P → W impressions): ketu-in-vedic-astrology 55 → 0, griha-pravesh-muhurat-2026-2027 31 → 0. The index file lists the second as "Crawled – currently not indexed" (last crawl 2026-08-09), yet **GA4 shows 14 landings on it in W** (9 Organic Search, 4 Direct, 1 AI Assistant; 2 engaged). Not explained.

## 2. Scores — issues closed in the last 45 days with a `thesis:` and a `metric:`

Rule: score once, when the window starts on or after the deploy date. The first W start a window can have today is 2026-10-22, so **no issue deployed after 2026-10-22 can be scored today.**

### Already scored (verdicts re-read this run; nothing re-posted — none moved)

| issue | thesis | predicted | earlier clean window | verdict | W read this run |
|---|---|---|---|---|---|
| **#311** title/meta rewrite on four band pages | CTR rises at unchanged position | ≥ 1.5% combined on ≥ 1,500 impr | 0.937% | **MISS** | same four pages in W: 64 clicks / 6,672 impr = **0.96%** (rahu-career-problems 23/1,134, debilitated-sun 16/3,006, manglik-dosh 4/485, jupiter-10th 21/2,047). Unchanged, still a MISS |
| **#276** /dasha CTA on the Rahu–Ketu article | pages/session rises | ≥ 1.20 | Organic 1.64 | bar met, not attributable to the CTA | Organic 1.65 (65 sessions); Direct 1.00 (10 sessions). Unchanged |
| **#329** Manglik checker link | pages/session rises | ≥ 1.30 on ≥ 10 sessions | 3 vs floor 10: unscoreable | stopped | /learn/manglik-dosh: 8 sessions (4 Organic, 4 Direct), pages/session 1.00. Floor still not reached |

**#311 is a miss and stays one.** The title rewrite alone did not reach its bar. The two other title/lede ships on band pages (#685 sade-sati 0.80%, #835 debilitated-sun 0.53%) have no verdict yet and both sit under the band's 1.27%.

### Posted this run

| issue | comment | why |
|---|---|---|
| **#1325** (muhurat landing dates, PR #1328 merged 2026-11-21) | "pending — scoreable from 2026-12-22", posted once | no note existed |
| **#1336** (shareable muhurat URL, PR #1337 merged 2026-11-21) | "pending — scoreable from 2026-12-22", posted once (one sentence corrected after posting) | no note existed. `muhurat_searched` is not among the 18 event names in `ga4-events.json`, so half of its metric cannot be read from today's exports |

### Pending (note already on the issue; nothing posted; a timer line written for every one in `/tmp/analyst-timers.txt`)

| issue | deploy (merge) | scoreable from | read this run, W (pre-deploy or mixed: **not a score**) |
|---|---|---|---|
| #553 | 2026-10-31 | 2026-12-01 | panch-mahapurush-yoga: 21 sessions, pages/session 1.00 |
| #426 | 2026-11-02 | 2026-12-03 | guard: sade-sati pos 6.6 (P 6.2) |
| #508 | 2026-11-03 | 2026-12-04 | /matching 119 impr at pos 10.0, against a pass bar needing ≥ 300 impr within ±1.5 of 4.3. Reads INCONCLUSIVE on today's numbers. Same page as #1076 |
| #685 | 2026-11-03 | 2026-12-04 | sade-sati CTR 0.80% (17 / 2,133); pass bar ≥ 1.2% (earlier note); W holds 16 post-deploy days, so mixed |
| #570 | 2026-11-03 | 2026-12-04 | `cta_click` = 19 in W; 8 of the 19 have `(not set)` from/to (see §5) |
| #518 | 2026-11-06 | 2026-12-07 | – |
| #528 | 2026-11-09 | 2026-12-10 | – |
| #735 | 2026-11-11 | 2026-12-12 | `admin_sessions` = 0 on every day 2026-11-10 → 11-19 (10 days); 15 admin sessions in W, all dated 2026-10-23 → 11-09 |
| #835 | 2026-11-13 | 2026-12-14 | "sun debilitated" query cluster: 1,108 impr, 2 clicks, weighted pos 7.3 (33 queries visible; P: ~3 impr). Page CTR 0.53% |
| #1066, #1093 | 2026-11-15 | 2026-12-16 | **cannot score**: no export carries `page_location` (#1237) |
| #1073 / #1074 / #1075 | 2026-11-16 | 2026-12-17 | #1073 jupiter-10th page: 2,047 impr, 21 clicks, pos 7.0 (P 6.9, 374 impr); #1075 rahu-ketu page: 3,642 impr, 62 clicks, pos 6.4 (P 7.4). #1074 floor (≥ 150 impr) at risk: `/panchang*` pages total 94 impr in W |
| #1067, #1068, #1072, #1175 | 2026-11-17 | 2026-12-18 | #1068 also needs a server-side count (#1272). `kundli_generated` = 49 and `ask_answered` = 128 events in W, so #1067's events are now arriving. #1072 "which mahadasha is best for career" 50 impr at pos 8.4, 0 clicks |
| #1071 | 2026-11-17 | 2026-12-18 (guard); main read 2027-02-28 | `gochar-2027` index state: "URL is unknown to Google"; gochar-2026 guard: position 5.0 (bar: no worse than 7.2) |
| #1217, #1226, #1229 | 2026-11-18 | 2026-12-19 | `tool_submitted` = 7, `form_submit` = 1, `subscribe_completed` = 1 in W (the events exist; the counts are small) |
| #1069 | 2026-11-19 | 2026-12-20 | `feature_view` = 777 and `user_identified` = 792 in W (pre-deploy for part of the window) |
| #1322, #1325, #1336 | 2026-11-21 | 2026-12-22 | /muhurat/griha-pravesh in W: 379 impr, 21 clicks, pos 6.3; 32 sessions, 30 engaged, bounce 6%. **Three ships on one page family inside 24 h: no movement can be split among them** |
| #1115 | – | – | **NOT MET, blocked on #1205**: this run has one GA4 window, not two. No timer (it waits on #1205, not a date) |

**Closed, thesis is deterministic (not scoreable from GA4/GSC; not re-read):** #1277 (scored MET on 2026-11-21: `returning` present, `admin_sessions` = 0 from 2026-11-12), #1326, #1331, #1332, #1338, #1293, #1294, #1300–#1302, #1313, #843, #1176–#1178, #838, #856, #978, #959.

**Misses this run: #311 (above), unchanged.** No new hit.

## 3. Confounds, named before any delta

| confound | state |
|---|---|
| Concurrent ships in W | Git history unreadable (shallow). From the issue trails: content and site-wide ships landed on the top pages inside W (the 2026-11-21 report listed #940, #1005/#1009/#1011, #1099/#1125, #1122, #1126, #1145, #1179, #1182, #1197, #1202). **Three or more landed on the top pages inside W, so no movement on a top-10 page can be attributed to one ship** |
| Google has not re-crawled the edits | `index-status.json` (2026-11-19T20:05Z) lists the ten largest pages as "changed after Google's last crawl": e.g. rahu-ketu changed 2026-11-16T04:15Z, last crawl 2026-11-08T08:35Z; sade-sati changed 11-15T20:31Z, last crawl 10-23T02:51Z. Their W position and CTR mostly predate Google seeing the edits. **I did not read a newer index file; whether Google has re-crawled since 11-19 is not measured** |
| Seasonality | Dhanteras 11-06, Diwali 11-08, Chhath 11-15 fall in W. None of the top-10 pages is a festival page. No year-earlier window exists. Seasonal share: **not determined** |
| Was the page working? | `verify-production.yml`, the last 100 runs (2026-11-15T11:17Z → 2026-11-21T22:06Z): 91 success, **4 failure** (2026-11-16 03:17, 11-17 08:10, 11-17 13:27, 11-17 18:12), 5 cancelled. No failure after 11-17 18:12 in that list. I did not read the failure causes. LLM fallbacks per route are not exported (#1208), so Groq-ceiling failures (#266-style) are **not measured** |
| Sample size | 399 clicks in 28 days. A page with < 100 impressions or < 10 clicks does not carry a conclusion; said where it applies |
| Automated traffic | Direct is 311 of 799 sessions at 19% engaged. The share that is automated is **not measured**: filed as #1364 (§8) |

## 4. Lever 1 — Growth

### Site level, W

| series | W total | weekly, wk1 → wk4 | first 14 days → last 14 days |
|---|---:|---|---|
| GSC impressions | 29,930 | 6,376 → 7,896 → 8,468 → 7,190 | 14,272 → 15,658 (+10%) |
| GSC clicks | 399 | 70 → 99 → 134 → 96 | 169 → 230 (+36%) |
| GA4 sessions (daily report) | 803 | 168 → 164 → 260 → 211 | 332 → 471 (+42%) |
| GA4 active users (sum of daily) | 716 | 141 → 150 → 238 → 187 | – |
| new users / returning user-days (daily) | 668 / 88 | – | – |
| GSC average position | 6.0–7.4 daily | stable | – |

Weeks: wk1 10-23 → 10-29, wk2 10-30 → 11-05, wk3 11-06 → 11-12, wk4 11-13 → 11-19.

**Watch:** the last four days are the lowest GSC impressions since 10-26: 11-16 908, 11-17 811, 11-18 798, 11-19 815, against 1,337–1,433 on 11-11 → 11-14 (about 40% lower). GA4 sessions fell the same way (11-16: 14, 11-17: 20, 11-18: 21, 11-19: 23, against 37–56 on 11-12 → 11-15). Whether this is the calendar (post-Diwali, post-Chhath), Google re-ranking after the 11-14 → 11-18 edits and redirects, or a data artefact is **not determined**. Four days is not a trend; the next run's window shows whether it persists.

### Against P (GSC only; `gsc-trend-page.json`, P coverage not stated)

| series | P (2026-09-25 → 10-22) | W (2026-10-23 → 11-19) | change |
|---|---:|---:|---:|
| impressions (page-sum) | 11,934 | 30,013 | **+151%** |
| clicks (page-sum) | 121 | 399 | **+230%** |
| pages with impressions | 132 | 137 | +5 |

Where the change comes from (page-sum, impr P → W / clicks P → W):

| page group | impr P → W | clicks P → W | share of the impression gain |
|---|---:|---:|---:|
| /learn/ articles | 10,661 → 28,136 | 100 → 344 | 96% of +18,079 |
| /muhurat/* | 154 → 467 | 8 → 25 | 2% |
| /numerology | 4 → 175 | 0 → 10 | 1% |
| `/` | 109 → 213 | 8 → 8 | 1% |
| /matching | 341 → 119 | 0 → 4 | negative (−222) |

By page: gochar-2026 9 → 3,066 impr (+3,057; pos 6.6 → 5.0; 0 → 26 clicks), debilitated-sun 1,246 → 3,006, rahu-ketu 2,055 → 3,642, jupiter-10th 374 → 2,047, sade-sati 1,123 → 2,133, career-during-sade-sati 387 → 1,335 (pos 7.0 → 5.4), 10th-lord-in-6th 162 → 833 (3 → 24 clicks). **Structural vs seasonal:** the growth is concentrated in `/learn/` articles that gained impressions at similar or better position (a ranking-footprint gain), with one time-bound exception: gochar-2026 contributes 17% of the gain. GA4 sessions against P: **not measured** (no previous GA4 window; #1205).

### Channels (`ga4.json`, W)

| channel | sessions | engaged rate | avg engagement s |
|---|---:|---:|---:|
| Organic Search | 485 | 57% | 143 |
| Direct | 311 | 19% | 44 |
| AI Assistant | 4 | 25% | 120 |
| Unassigned | 1 | 0% | 186 |

North star (organic sessions): **485 in W**, against 399 GSC clicks. The gap is Bing and other engines, which GSC does not see.

### Returning users and internal traffic

| measure | W |
|---|---|
| `returning.user_days` / share | 88 / **12.3%** (status ok; user-days, not people) |
| `admin_sessions` per day | 0 on every day from **2026-11-10** onward, including all days from 2026-11-12. Nonzero days: 10-23 (1), 10-24 (1), 10-25 (3), 10-26 (2), 10-28 (1), 11-04 (2), 11-05 (3), 11-09 (2), 15 in total, all before #735 (merged 2026-11-11). **No internal-traffic leak after the fix; nothing filed** |

### Every day in `spikes` and `watch` (7 days at or above median 22 + 10), with its source — Discover is 0 on every one of them

| date | users / sessions | tier | source named by the file (and my read) | GSC clicks | read |
|---|---:|---|---|---:|---|
| 2026-10-23 | 34 / 34 | watch | Direct on `/`, `/kundli`, `/matching`, `/numerology` (6, 6, 5, 5 sessions, 0–33% engaged, 3–6 s on tool pages); Chrome mobile **US 26 sessions, 12% engaged, 4.5 s** | 7 | **Leans automated or low-intent Direct.** Not search (7 clicks, below window mean 14.25) |
| 2026-11-06 | 57 / 59 | spike | top row Direct on `/rashifal/aries` (6 sessions, 17% engaged, 3.5 s); **19 of 50 sessions zero engagement** (no browser name desktop US 10, Chrome desktop US 6, Chrome mobile US 3) | 17 | **Mixed, not growth.** About 19 sessions look automated; Organic readers of `/learn/rahu-mahadasha-career-problems/` (4 sessions, 224 s) look real |
| 2026-11-09 | 32 / 37 | watch | google / organic, Chrome mobile India; `jupiter-in-10th`, `rahu-ketu`, `griha-pravesh` (5 sessions each); 53% engaged, 127 s | 21 | **Real readers, search-driven** |
| 2026-11-10 | 40 / 43 | watch | top row Direct on `/matching` (5, 0% engaged, 2.2 s), `/numerology` (4); bing / organic `/numerology` 4 sessions at 0%. **21 of 35 sessions zero engagement**, desktop US | 14 | **Mixed, mostly automated.** Not growth |
| 2026-11-12 | 34 / 37 | watch | google / organic, `/muhurat/griha-pravesh` (4 sessions, 100% engaged, 205 s), Chrome mobile India 14 sessions at 71% engaged | 24 | **Real readers, search-driven** |
| 2026-11-14 | 32 / 47 | watch | google / organic: 10 sessions on `/learn/rahu-mahadasha-ketu-antardasha/` (40% engaged, 80 s), 5 on `chronic-health-issues-kundli`; Chrome mobile Indonesia 9 sessions at 67% engaged, 186 s | 23 | **Real readers, search-driven.** Not Discover. Sessions per user 1.47, highest in W |
| 2026-11-15 | 51 / 56 | spike | google / organic on the Rahu page (6 sessions, 83% engaged, 242 s). **Chrome mobile China 9 sessions, 0% engaged, 0 s**; Chrome mobile India 17 (59%, 61 s); 5 Direct on `/panchang/2026-12-02` at 0%, 1.6 s | 14 | **Mixed, not growth.** China-mobile and dated-panchang rows look automated; the India readers look real. Not Discover |

Seven of seven named. Three days (11-06, 11-10, 11-15) carry zero-engagement cohorts that look automated; three days (11-09, 11-12, 11-14) are search-driven readers. **None of the seven is Discover** (`gsc-discover.json`: 0 clicks, 0 impressions on all 28 days).

## 5. Lever 2 — where time is spent (`verify-first.json`, `ga4.json`; W)

| page | sessions | engaged | engaged rate | avg engagement s | GSC impr / clicks / pos |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 76 | 46 | 61% | 143 | 3,643 / 62 / 6.4 |
| `/` | 68 | 40 | 59% | 225 | 214 / 8 / 5.9 |
| /muhurat/griha-pravesh | 32 | 30 | **94%** | 89 | 379 / 21 / 6.3 |
| /learn/gochar-2026-planetary-transits | 45 | 17 | **38%** | **27** | 3,066 / 26 / 5.0 |
| /learn/10th-lord-in-6th-house-career | 29 | 16 | 55% | 126 | 833 / 24 / 6.8 |
| /learn/rahu-mahadasha-career-problems | 25 | 15 | 60% | 282 | 1,134 / 23 / 5.8 |
| /learn/career-during-sade-sati | 27 | 13 | 48% | 228 | 1,335 / 24 / 5.4 |
| /learn/sade-sati | 22 | 12 | 55% | 225 | 2,133 / 17 / 6.6 |
| /learn/debilitated-sun-career | 25 | 10 | 40% | 214 | 3,006 / 16 / 6.5 |
| /learn/jupiter-in-10th-house-career | 25 | 10 | 40% | **60** | 2,047 / 21 / 7.0 |

Page groups (`ga4.json`, folded by landing path; sessions / engaged rate / avg engagement s): `/learn/<article>` 528 / 43% / 111 · `/` 68 / 59% / 225 · `/muhurat/*` 41 / 88% / 88 · `/kundli` 25 / 28% / 38 · `/numerology` 23 / 35% / 85 · `/matching` 17 / 18% / 43 · `/rashifal*` 14 / 7% / 2 · `/panchang/*` 13 / 8% / 2 · `/festivals` 5 / 0% / 0. `/learn/` articles are 66% of sessions (528 of 801).

**Tool funnels visible from `ga4-events.json` (W; the events are not user-linked, so these are not a conversion rate):** `form_start` 123 → `kundli_generated` 49 → `form_submit` 1; `tool_submitted` 7; `cta_click` **19** (8 have `(not set)` from/to; the rest: career-during-sade-sati → `/` 3, sade-sati → `/kundli` 2, and one each from kaal-sarp-dosh, krittika, name-numerology, rahu-career-problems, rahu-ketu, saturn-10th). `ask_answered` 128. `feedback_sent` 2, `subscribe_completed` 1. `cta_click` exists only from 2026-11-03, so this is partial history.

The two largest pages that are weak on time: **gochar-2026** (45 sessions, 27 s) and **jupiter-in-10th** (25 sessions, 60 s). They are also two of the top-5 pages by impressions.

## 6. Lever 3 — errors

| source | finding |
|---|---|
| `llm-usage.json` (last 7 days, generated 2026-11-22T00:53Z) | 155 calls, 114 cache hits (**73%**), 41 misses. Input tokens 123,736, output 22,223. **The file has no error or fallback field**, so errors per route are **not measured**; tracked by **#1208** |
| per route | natal 98 calls / 89 hits (90%) / 6,504 tokens per measured call (9 measured calls) · ask 27 / **0 hits** / 2,052 per call · rashifal 24 / 24 hits (100%) · today 4 / 1 hit · matching 1 / 0 · monthly 1 / 0 |
| tokens per day | `peak_day_tokens` 6,529 and `peak_day_measured_tokens` 43,421, both 2026-11-18. 43,421 against the 200,000 TPD figure in CLAUDE.md is 22%. The file does not say why the two fields differ |
| `verify-production.yml`, last 100 runs, 2026-11-15 → 2026-11-21 | 91 success / 4 failure / 5 cancelled. Failures on 11-16 03:17Z, 11-17 08:10Z, 13:27Z, 18:12Z. Causes **not read** |
| open issues | #1208 (LLM fallbacks export), #1272 (server-side kundli count), #1076 (/matching decay) |

`ask` is the only route with live per-request generation at scale: 27 calls, 0 cache hits, 55,424 input tokens in 7 days. It is per-visitor by nature; nothing here says it is over budget.

## 7. Lever 4 — search demand (partial: `gsc-trend-query.json` covers **15%** of impressions)

| theme | impressions | clicks | weighted position | visible queries | existing page |
|---|---:|---:|---:|---:|---|
| "sun debilitated" family | 1,108 | 2 | 7.3 | 33 | `/learn/debilitated-sun-career/` (0.53% CTR; #835 targets it) |
| "rahu mahadasha / ketu antardasha" | 952 | 22 | 7.2 | 47 | `/learn/rahu-mahadasha-ketu-antardasha/` (1.70%) |
| "jupiter 10th house" | 395 | 1 | 9.5 | 47 | `/learn/jupiter-in-10th-house-career/` (1.03%) |
| "7th house / 7th lord marriage" | 162 | 2 | 10.4 | 46 | `/learn/7th-lord-placement-marriage-guide/`, `/learn/planets-in-7th-house-marriage/` |
| "gochar / transit / 2026" | 105 | 1 | 18.8 | 61 | `/learn/gochar-2026-planetary-transits/` (the page has 3,066 impr; most of its queries are withheld) |
| manglik | 73 | 1 | 11.1 | 31 | `/learn/manglik-dosh/` |
| mahapurush | 56 | 0 | 16.3 | 23 | `/learn/panch-mahapurush-yoga/` |
| sade sati | 53 | 0 | 8.5 | 29 | `/learn/sade-sati/`, `/learn/career-during-sade-sati/` |
| numerology | 23 | 2 | 6.0 | 4 | `/numerology` (174 impr, 10 clicks, pos 6.1; P 4 impr) |

Themes are matched by keyword over the visible queries and sum to far less than the property's 29,930. Top single queries: "rahu mahadasha ketu antardasha" 389 impr (P 260), pos 6.4, 13 clicks; "sun debilitated in which sign" 349 (P 1), pos 7.4, 1 click; "sun is debilitated in which sign" 154, pos 6.4, 0 clicks; "jupiter in 10th house" 116, pos 11.0; "which mahadasha is best for career" 50, pos 8.4, 0 clicks.

- **Queries with no page:** none with ≥ 10 impressions that lacks an existing page by topic in the visible 15%. This is not proof none exist in the invisible 85%. "yes" (111 impr, pos 3.6, 0 clicks) is not a topic.
- **Landing page per query is not determined**: the query export has no page column. The "sun debilitated" family is attributed to debilitated-sun-career by topic only.
- **`/hi/*`**: 71 impressions in W against 6 in P, 0 clicks. Hindi pages exist and are being shown (#124).
- **`/festivals`**: 275 impressions, 0 clicks, position 37.7 (P 26.4).
- **`/rashifal`** moved from position 10.4 to 7.1 (145 impr, 1 click); the `/rashifal/{rashi}` pages hold 194 impressions in total.

## 8. Lever 5 — content opportunities (dates **only from `festivals.py`**, read this run: `festivals_for_date()` over 2026-11-22 → 2027-01-17)

| date | entry in `festivals.py` | existing page |
|---|---|---|
| 2026-11-24 | Kartika Purnima | `/festivals` only; no dedicated page found; `/muhurat/*` unrelated |
| 2026-12-01 | Kalabhairav Jayanti | `/festivals`; copy corrected under #1331 |
| 2026-12-14 | Vivah Panchami | `/festivals`; wedding-timing intent also served by `/learn/vivah-muhurat-2027` (33 impr, pos 9.1, 0 clicks; index state "Crawled – currently not indexed") and `/muhurat/vivah` (28 impr, pos 6.4) |
| 2026-12-20 | Gita Jayanti (Mokshada Ekadashi) | `/festivals` |
| 2026-12-23 | Dattatreya Jayanti (Margashirsha Purnima) | `/festivals` |
| 2027-01-15 | Makar Sankranti; Pongal (Thai Pongal) | `/festivals` |

- **The 54-day registry gap reported on 2026-11-19 → 11-21 is closed** (#1326, merged 2026-11-21): six dated entries now sit in the window. I did not check the dates against an almanac; the PR's QA covers that.
- Only the aggregate `/festivals` page serves these. It ranks 37.7 with 0 clicks. Whether a dedicated page per festival is wanted is product-manager's decision; I name the demand: none of the six names appears in the visible 15% of queries, so **there is no search signal to read for them this run**.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` is the second-largest page (3,066 impr, pos 5.0, 26 clicks, 45 sessions at 38% engaged, 27 s). **`gochar-2027-planetary-transits` already exists** (#1071); index state "URL is unknown to Google". `diwali-muhurat-2026` (76 impr, pos 11.2) is past its date. `griha-pravesh-muhurat-2026-2027` dropped out of GSC (31 → 0 impr) but still received 14 GA4 landings.
- **Time-bound page that works:** `/muhurat/griha-pravesh` (379 impr, 21 clicks, 94% engaged, 32 sessions). Three ships on it landed 2026-11-21 (§2).

## 9. Lever 6 — index status (`measurements/index-status.json`, generated 2026-11-19T20:05Z; 214 URLs, 0 errors)

| state | URLs |
|---|---:|
| Submitted and indexed | 166 |
| Crawled – currently not indexed | 29 |
| Discovered – currently not indexed | 12 |
| URL is unknown to Google | 7 |
| **not indexed in total** | **48** |
| changed after Google's last crawl (`stale`) | 174 |

Not indexed, ranked by impressions (W): pushya-nakshatra 124, ashwini-nakshatra 89, mars-remedies 71, vivah-muhurat-2027 42, rohini-nakshatra 41, jupiter-remedies 39, swati-nakshatra 32, dhana-yoga-wealth-combinations 31, the-9-grahas-overview 24, marriage-delayed 23 — all "Crawled – currently not indexed". Largest changed-after-crawl pages (the file's `request_indexing` list): rahu-ketu 3,912 impr (changed 11-16, crawled 11-08), gochar-2026 2,512 (11-17 vs 11-10), sade-sati 2,133 (11-15 vs 10-23), jupiter-10th 1,940, 7th-lord 1,509, career-during-sade-sati 1,239, planets-in-7th 1,221, rahu-career-problems 1,044, 10th-lord-in-6th 762, mangal-mars 557. **This list is a request for a re-crawl on the ten biggest pages; the file is three days old** and I could not tell whether Google has acted.

## 10. Lever 7 — measurement gaps, checked against my last three reports (2026-11-19, 11-20, 11-21)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window (sessions/users vs P) | yes, and this run | **#1205** | none: covered |
| `page_location` / query strings in GA4 exports | yes | **#1237** | none: covered |
| Errors / LLM fallbacks per route | yes | **#1208** | none: covered |
| Per-page × per-day export (date the /matching decay, split a page at its deploy) | yes | **#953**, **#1076** | none: covered |
| Shallow checkout: no `git log --since` | yes | **#666**, **#974** | none: covered |
| Server-side kundli submission count | yes | **#1272** | none: covered |
| **Share of Direct traffic that is automated** | **yes** — 11-19 ("Direct is not clean"), 11-20 (same), 11-21 ("not measured") — and this run | none open | **filed #1364** |
| `muhurat_searched` (the other half of #1336's metric) is not among the 18 event names in `ga4-events.json` | first time | none | not filed: one run. It will be filed if the event is still absent after #1336's window opens, unless it is simply not firing because no visitor reached it |
| Newer `index-status.json` than 2026-11-19 | first time | #1065 (tracks the export) | none: covered |

## 11. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| Sessions and users against the previous window | `fetch_ga4.py --trend` in `agent-measure` (#1205) |
| How much of Direct (311 sessions, 19% engaged) is automated | the cohort export in #1364 |
| Whether the last-4-days dip (798–908 impressions a day vs 1,337–1,433) persists | next run's W; a per-day export of GSC by page (#953) would also say which pages fell |
| When /matching lost position (4.4 → 10.0) | `fetch_gsc.py --page-daily` (#953) |
| Whether Google has re-crawled the ten edited top pages | a fresh `index-status.json` (#1065) |
| LLM errors and fallbacks per route | #1208 |
| Why `griha-pravesh-muhurat-2026-2027` is "not indexed" yet drew 14 GA4 landings and 0 GSC impressions | URL Inspection on that URL plus GA4 source for those 14 landings |
| The landing page behind each query | `fetch_gsc.py` with a query × page dimension, which Google restricts for anonymised queries |
| Why `/learn/jupiter-in-10th-house-career` and `gochar-2026` hold readers for only 60 s and 27 s | per-section scroll depth, which no export carries |

## 12. Actions this run

| action | result |
|---|---|
| Comment on #1325 | "pending — scoreable from 2026-12-22" |
| Comment on #1336 | "pending — scoreable from 2026-12-22" (edited once to fix one sentence) |
| Issue filed | **#1364** — no export sizes automated traffic (Evidence Block: repro printed `311 59 485 276`, as stated) |
| Timers | 26 lines in `/tmp/analyst-timers.txt` (one per pending issue, including #1322, #1325, #1336) |
| Re-posts avoided | #311, #276, #329 (verdicts unchanged), and every pending issue other than the two above |
