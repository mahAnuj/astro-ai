# Analyst report — 2026-11-23

**Window for every number: W = 2026-10-24 → 2026-11-20** (28 days; the last 3 are excluded: GSC lags 2–3 days, GA4 24–48h).
**Previous window P = 2026-09-26 → 2026-10-23** (GSC trend files only; GA4 has no previous window).
Everything below was read from this run's files (`/tmp/*.json`, `/tmp/measure/*.json`), from `gh` this run, or from `festivals.py` this run. Anything not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 30,291 impressions | no | 403 clicks |
| `gsc-all.json` / `gsc-band.json` (`dimension: page`) | W | 100%; `rows_impressions` 30,374 vs property 30,291 | no | band printed **95 rows = 22,516 impressions = 74%** (`emitted_coverage_pct`), 287 clicks |
| `gsc-trend-page.json` | W vs P | W 100%; P coverage **not stated** | no | W page-sum 30,374 / 403 clicks; P page-sum 12,029 / 125 clicks |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **15%** (4,420 of 30,291 impressions visible; 919 query keys) | no | Google withholds the rest. No conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 790 sessions (rows sum 792) | no | 159 rows, 103 raw landings, **96 distinct paths** after folding query strings and trailing slashes |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum to **795**; `session_start` events 792. Three session totals (790 / 792 / 795) from GA4 reports that do not reconcile. I quote each from its own file |
| `ga4-events.json` | W | 20 event names, `events_total` 5,260 | no | `cta_click` exists only from 2026-11-03 (PR #688): partial history |
| `ga4-anomalies.json` | W | 2 spikes + 5 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | **0 clicks, 0 impressions on all 28 days**, `top_pages` empty | – | a measured zero |
| `verify-first.json` | W | 10 busiest pages by engaged sessions | – | |
| `measure/llm-usage.json` | last 7 days, generated 2026-11-23T01:22Z | – | – | **no error or fallback field** (#1208 open) |
| `measurements/index-status.json` | generated 2026-11-19T20:05Z, **not this run** | 214 of 214 URLs | – | four days older than the other files |
| GA4 previous window | – | **absent** | – | no `ga4-trend.json` in `/tmp`. Sessions/users against P **not measured** (#1205 open, held `needs-human-review`) |
| `git log origin/main --since` | – | 1 commit | – | checkout is shallow (`git rev-parse --is-shallow-repository` = true; #666, #974). Concurrent ships are taken from `gh pr list --state merged` |

## 1. The 6–20 position band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **Not measurable as written**: the query export covers 15% of impressions, and in page mode a band `position` is the page's average across its queries. The table is the page-level proxy.

| metric (W, `dimension: page`) | value |
|---|---|
| pages with impressions | 137 |
| pages at average position < 6 | 33 |
| pages at position 6–20 | **95**, 22,516 impressions (74% of the page-row total), 287 clicks, aggregate CTR **1.27%** |
| band pages with ≥ 100 impressions | 29 |
| median CTR of the 18 band pages with ≥ 300 impressions | 1.09% |
| top-10 pages by impressions at average position ≤ 5 | **1 of 10** (`gochar-2026-planetary-transits`, 5.0) |

Band list, ranked by the file's `band_opportunity` (W; position = page average; `P pos` from `gsc-trend-page.json`):

| # | page | impr | clicks | CTR | pos | P pos |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/debilitated-sun-career/ | 2,999 | 15 | **0.50%** | 6.5 | 6.2 |
| 2 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,526 | 61 | 1.73% | 6.4 | 7.3 |
| 3 | /learn/sade-sati/ | 2,072 | 17 | **0.82%** | 6.6 | 6.3 |
| 4 | /learn/jupiter-in-10th-house-career/ | 2,111 | 22 | 1.04% | 7.0 | 6.9 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,500 | 15 | 1.00% | 7.3 | 7.6 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,395 | 11 | **0.79%** | 6.8 | 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,056 | 15 | 1.42% | 7.2 | 6.9 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 624 | 4 | **0.64%** | 7.7 | 7.4 |
| 9 | /learn/10th-lord-in-6th-house-career/ | 852 | 24 | 2.82% | 6.8 | 7.0 |
| 10 | /learn/manglik-dosh/ | 494 | 4 | 0.81% | 6.8 | – |
| 11 | /learn/shukra-venus-in-vedic-astrology/ | 395 | 2 | **0.51%** | 6.1 | – |
| 12 | /learn/saturn-in-10th-house-career/ | 473 | 7 | 1.48% | 7.6 | – |

**Nearest to top 5** (all positions, top-10 by impressions): career-during-sade-sati 1,367 impr, pos **5.4** (P 7.0), 1.83% CTR; rahu-mahadasha-career-problems 1,159 impr, pos **5.7**, 1.98%. The other seven top-10 pages sit at 6.4–7.3.

### CTR outliers (against the band's own 1.27% aggregate)

| page | impr | CTR | pos | reading |
|---|---:|---:|---:|---|
| debilitated-sun-career | 2,999 | 0.50% | 6.5 | largest gap on the site: at 1.27% it would take about 38 clicks, not 15. #835 (answer-first lede, merged 2026-11-13) targets it; Google had not re-crawled as of 2026-11-19 (§9) |
| sade-sati | 2,072 | 0.82% | 6.6 | #685 title change (merged 2026-11-03), pending, and Google's last crawl predates it (§9) |
| planets-in-7th-house-marriage | 1,395 | 0.79% | 6.8 | position worse by 1.0 (P 5.8 → 6.8), CTR about 62% of the band |
| gochar-2026-planetary-transits | 3,191 | 0.85% | **5.0** | the only top-10 page at ≤ 5, yet CTR is under half of the 1.83% / 1.98% on the two pages at 5.4 / 5.7 |
| mangal-mars / shukra-venus | 624 / 395 | 0.64% / 0.51% | 7.7 / 6.1 | no issue found this run |
| /muhurat/griha-pravesh | 401 | 4.99% | 6.6 | best CTR among pages with ≥ 300 impressions |

### Decay (position worse by ≥ 2 with ≥ 50 impressions in P; `gsc-trend-page.json`)

| page | impr W / P | clicks W / P | pos W / P | note |
|---|---:|---:|---:|---|
| /matching | **119 / 342** | 4 / 0 | **10.0 / 4.4** | lost 65% of impressions and 5.6 positions. #508's title/meta shipped 2026-11-03; **#1076** is the open investigation; onset undated (needs the per-page × per-day export, #953) |
| /festivals | 275 / 235 | 0 / 0 | 38.1 / 25.8 | far outside the band, 0 clicks |

Left GSC entirely in W (P → W impressions): ketu-in-vedic-astrology 50 → 0 (`is_gone`), griha-pravesh-muhurat-2026-2027 24 → 0, financial-struggles 36 → 1 (position 6.4 → 3). **GA4 still shows landings on the last two**: griha-pravesh-muhurat-2026-2027 14 sessions (2 engaged) and financial-struggles 11 sessions, **0 engaged, 11 of 11 Direct**. Not explained; see §11.

## 2. Scores — issues closed in the last 45 days (since 2026-10-09) with a `thesis:` and a `metric:`

Rule: a window is clean when its start (today − 31 = 2026-10-23) is on or after the deploy. Of the closed issues carrying a GA4/GSC metric, **only #311, #276 and #329 were deployed on or before 2026-10-23**, and all three were already scored on earlier runs. Every other one deployed 2026-10-31 or later. **No new issue is scoreable today; nothing is posted on any issue this run.**

### Already scored — verdicts re-read from this run's files; nothing re-posted (none moved)

| issue | thesis | predicted | earlier clean window | verdict | W read this run |
|---|---|---|---|---|---|
| **#311 — MISS** | title/meta rewrite on four band pages lifts CTR at unchanged position | ≥ 1.5% combined on ≥ 1,500 impr | 0.937% | **MISS** | same four pages, W: 64 clicks / 6,763 impr = **0.95%** (rahu-career-problems 23/1,159, debilitated-sun 15/2,999, manglik-dosh 4/494, jupiter-10th 22/2,111). Unchanged. Still a miss |
| **#276** | /dasha CTA on the Rahu–Ketu article lifts pages/session | ≥ 1.20 | Organic 1.64 | bar met, **not attributable to the CTA** | Organic 1.65 (65 sessions, 44 engaged); Direct 1.00 (8 sessions). Unchanged |
| **#329** | Manglik checker link lifts pages/session | ≥ 1.30 on ≥ 10 sessions | 3 vs floor 10: unscoreable (posted once) | stopped | /learn/manglik-dosh: 8 sessions (4 Organic, 4 Direct), pages/session 1.00. Floor not reached |

**#311 is a miss and stays one.** A title rewrite alone did not reach its bar. The other title/lede ships on band pages (#685 sade-sati 0.82%, #835 debilitated-sun 0.50%) have no verdict yet and both sit under the band's 1.27%. Neither move would be attributable today: Google's last crawl predates both edits (§9).

### Pending — a note is already on every issue; nothing posted; one timer line per issue written to `/tmp/analyst-timers.txt` (26 lines)

I read each issue's comments this run: every issue below carries a "scoreable from" note by `claude`, except **#570**, whose note exists and whose `score-570` timer was already set by `github-actions` on 2026-11-18 (the line is rewritten here; setting is idempotent).

| issue | deploy → scoreable from | read this run, W (pre-deploy or mixed: **not a score**) |
|---|---|---|
| #553 | 2026-10-31 → 2026-12-01 | panch-mahapurush-yoga: 21 sessions in W (Organic 14, 8 engaged; Direct 7, 1 engaged), pages/session 1.00 on every row; pre-deploy, not a score |
| #426 | 2026-11-02 → 2026-12-03 | guard: sade-sati pos 6.6 (P 6.3) |
| #508 | 2026-11-03 → 2026-12-04 | /matching 119 impr at pos 10.0 (P 342 at 4.4). Reads INCONCLUSIVE; same page as #1076 |
| #685 | 2026-11-03 → 2026-12-04 | sade-sati CTR 0.82% (17 / 2,072); W holds 17 post-deploy days, so mixed |
| #570 | 2026-11-03 → 2026-12-04 | `cta_click` = **20** in W; 8 of the 20 carry `(not set)` from/to |
| #518 | 2026-11-06 → 2026-12-07 | – |
| #528 | 2026-11-09 → 2026-12-10 | – |
| #735 | 2026-11-11 → 2026-12-12 | `admin_sessions` = 0 on every day 2026-11-10 → 11-20 (11 days); 14 admin sessions in W, all dated 10-24 → 11-09 |
| #835 | 2026-11-13 → 2026-12-14 | "sun debilitated" query family 1,106 impr in W vs about 33 in P (33 queries visible); page CTR 0.50% |
| #1066, #1093 | 2026-11-15 → 2026-12-16 | **cannot score**: no export carries `page_location` (#1237) |
| #1073 / #1074 / #1075 | 2026-11-16 → 2026-12-17 | #1073 jupiter-10th: 2,111 impr, 22 clicks, pos 7.0 (P 6.9, 368 impr); #1075 rahu-ketu: 3,526 impr, 61 clicks, pos 6.4 (P 7.3). #1074 sample floor at risk: `/panchang*` pages total 94 impr in W (`gsc-trend-page.json`) |
| #1067, #1068, #1072, #1175, #1071 | 2026-11-17 → 2026-12-18 | `kundli_generated` = 50, `ask_answered` = 129, `dasha_deep_dive_viewed` = 2 in W. #1068 also needs a server-side count (#1272). #1072: "which mahadasha is best for career" family 65 impr, 0 clicks, pos 8.4 |
| #1217, #1226, #1229 | 2026-11-18 → 2026-12-19 | `tool_submitted` = 16, `form_submit` = 1, `subscribe_completed` = 1, `matching_completed` = 1, `dosha_check_completed` = 1 in W: the events exist; the counts are small |
| #1069 | 2026-11-19 → 2026-12-20 | `feature_view` 744 and `user_identified` 758 in W (pre-deploy for most of the window) |
| #1322, #1325, #1336 | 2026-11-21 → 2026-12-22 | /muhurat/griha-pravesh in W: 401 impr, 20 clicks, pos 6.6; 31 sessions, 29 engaged. **Three ships on one page family inside 24 h: no movement can be split among them.** `muhurat_searched` is not among the 20 event names |
| **#1115** | closed 2026-11-19 | **NOT MET, blocked on #1205**: this run again has one GA4 window, not two (`/tmp/ga4-trend.json` absent). Verdict unchanged since the 2026-11-20 comment; not re-posted. No timer: it waits on #1205, not a date |

**Closed, thesis is deterministic (not scoreable from GA4/GSC; not re-read):** #1277, #1326, #1331, #1332, #1338, #1293, #1294, #1300–#1302, #1313, #843, #1176–#1178, #838, #856, #978, #959, and the grounding/copy follow-ups #1321, #1359, #1370, #1377, #1380, #1386.

**Misses this run: #311 (above), unchanged. No new hit and no new miss.** Closed issues carrying a GA4/GSC metric number about 30; 3 are scoreable, 1 of the 3 is a clean miss, 1 is a pass with no attribution, 1 is unscoreable at this traffic. The rest wait on dates 2026-12-01 → 12-22.

## 3. Confounds, named before any delta

| confound | state |
|---|---|
| Concurrent ships in W | Git history unreadable (shallow). `gh pr list --state merged` shows, since 2026-11-17: a stream of learn-page copy edits (#1389 debilitated-sun, #1382/#1378 Rao-table wording, #1368 manglik-remedies, #1319, #1316, #1312, #1310), muhurat ships (#1323, #1328, #1337, #1348), festival registry (#1329, #1366), analytics (#1278, #1266). **Several landed on top-10 pages inside W, so no movement on a top-10 page can be attributed to one ship** |
| Google has not re-crawled the edits | `index-status.json` (2026-11-19T20:05Z): the ten largest pages are "changed after Google's last crawl", e.g. rahu-ketu changed 2026-11-16T04:15Z, last crawl 2026-11-08T08:35Z; sade-sati changed 11-15T20:31Z, last crawl 10-23T02:51Z; gochar-2026 changed 11-17, crawled 11-10. W position/CTR mostly predate Google seeing the edits. **A newer index file was not available; whether Google re-crawled since 11-19 is not measured** |
| Seasonality | Dhanteras 11-06, Diwali 11-08, Chhath 11-15 fall in W. None of the top-10 pages is a festival page. No year-earlier window exists. Seasonal share **not determined** |
| Was the page working? | `verify-production.yml`, last 100 runs (2026-11-16T03:17Z → 2026-11-22T23:05Z): 91 success, **4 failure** (11-16 03:17, 11-17 08:10, 13:27, 18:12 — all earlier than 11-18), 5 cancelled. **No failure in the last 5 days.** Causes not read. LLM fallbacks per route are not exported (#1208), so Groq-ceiling failures (#266-style) are **not measured** |
| Sample size | 403 clicks and 790 sessions in 28 days. A page with < 100 impressions or < 10 clicks does not carry a conclusion; said where it applies |
| Automated traffic | Direct is 284 of 792 session rows at 20% engaged. How much is automated is **not measured**: open as #1364 |

## 4. Lever 1 — Growth

### Site level, W

| series (W) | W total | week 1 → 4 | first 14 d → last 14 d |
|---|---:|---|---|
| GSC impressions | 30,291 | 6,772 → 7,912 → 8,827 → 6,780 | 14,684 → 15,607 (+6%) |
| GSC clicks | 403 | 77 → 102 → 139 → 85 | 179 → 224 (+25%) |
| GA4 sessions (daily report) | 795 | 156 → 201 → 231 → 207 | 357 → 438 (+23%) |
| GA4 active users (sum of daily; not unique people) | 699 | 126 → 188 → 211 → 174 | 314 → 385 |
| new users / returning users (daily sums) | 650 / 89 | – | – |
| GSC average position | 6.0–7.4 daily | stable | – |

Weeks: wk1 10-24 → 10-30, wk2 10-31 → 11-06, wk3 11-07 → 11-13, wk4 11-14 → 11-20.

**Watch:** impressions fell from 8,827 (wk3) to 6,780 (wk4), −23%; clicks 139 → 85, −39%. Daily GSC impressions 11-16 → 11-20: 908, 811, 798, 815, **1,001** (against 1,337–1,433 on 11-11 → 11-14). GA4 sessions 11-16 → 11-20: 14, 20, 21, 23, 26 (against 30–56 on 11-12 → 11-15). 11-20 is the first day moving back up. Cause **not determined**: calendar (post-Diwali, post-Chhath), Google re-ranking after the 11-14 → 11-18 edits, or a data artefact. Five days is not a trend; next run's window shows whether it persists.

### Against P (GSC only; `gsc-trend-page.json`, P coverage not stated)

| series | P (09-26 → 10-23) | W (10-24 → 11-20) | change |
|---|---:|---:|---:|
| impressions (page-sum) | 12,029 | 30,374 | **2.52×** |
| clicks (page-sum) | 125 | 403 | **3.22×** |
| CTR | 1.04% | 1.33% | +0.29 pt |
| pages with impressions | 126 | 137 | +11 |
| query keys visible (15% view) | 218 | 919 | – |

Where the change comes from (page-sum, impr P → W / clicks P → W):

| page group | impr P → W | clicks P → W | share of the +18,345 impression gain |
|---|---:|---:|---:|
| /learn/ articles | 10,754 → 28,474 | 103 → 349 | **96.6%** |
| /muhurat/* | 157 → 490 | 9 → 24 | 1.8% |
| /numerology | 4 → 185 | 0 → 10 | 1.0% |
| `/` | 111 → 215 | 8 → 8 | 0.6% |
| /hi/* | 8 → 70 | 0 → 0 | 0.3% |
| /matching | 342 → 119 | 0 → 4 | negative (−223) |

Single pages: gochar-2026 3 → 3,191 impr (+3,188 = **17.4% of the gain**; pos 7 → 5.0; 0 → 27 clicks), jupiter-10th 368 → 2,111, debilitated-sun 1,287 → 2,999, rahu-ketu 2,148 → 3,526, career-during-sade-sati 395 → 1,367 (pos 7.0 → 5.4; 4 → 25 clicks), 10th-lord-in-6th 150 → 852 (3 → 24 clicks), 7th-lord 291 → 1,500, sade-sati 1,200 → 2,072.
**Structural vs seasonal:** growth is concentrated in `/learn/` articles that gained impressions at similar or better position, a ranking-footprint gain; one time-bound exception (gochar-2026). GA4 sessions against P: **not measured** (#1205).

### Channels (`ga4.json`, W; sessions summed over landing × channel rows)

| channel | sessions | engaged | engaged rate | avg engagement s | bounce (weighted) | pages/session (weighted) |
|---|---:|---:|---:|---:|---:|---:|
| Organic Search | 503 | 288 | 57% | 150 | 0.43 | 1.90 |
| Direct | 284 | 56 | **20%** | 52 | 0.80 | 1.68 |
| AI Assistant | 4 | 1 | 25% | 120 | 0.75 | 3.50 |
| Unassigned | 1 | 0 | 0% | 186 | 1.00 | 0.00 |

North star (organic sessions): **503 in W** against 403 GSC clicks; the gap is Bing and other engines that GSC does not see.

### Returning users and internal traffic

| measure | W |
|---|---|
| `returning` (`status: ok`) | 89 user-days, **12.7%** of daily active users (user-days, not people) |
| `admin_sessions` | 14 in W (10-24: 1, 10-25: 3, 10-26: 2, 10-28: 1, 11-04: 2, 11-05: 3, 11-09: 2). **0 on every day from 2026-11-10 onward, including all days from 2026-11-12.** No internal-traffic leak after #735; nothing filed |

### Every day in `spikes` and `watch` (7 days; median 22 active users) — Discover is 0 clicks on every one of them

| date | users / sessions | tier | source named by the file (and my read) | GSC clicks | read |
|---|---:|---|---|---:|---|
| 2026-11-06 | 57 / 59 | spike | top row Direct on `/rashifal/aries` (6 sessions, 17% engaged, 3.5 s); **19 of 50 sessions zero engagement** (no-browser-name desktop US 10, Chrome desktop US 6, Chrome mobile US 3) | 17 | **Mixed, not growth.** About 19 sessions look automated; Organic readers of rahu-career-problems (4 sessions, 224 s) look real |
| 2026-11-09 | 32 / 37 | watch | google / organic, Chrome mobile India 15 sessions at 53% engaged, 127 s; jupiter-10th, rahu-ketu, griha-pravesh (5 each) | 21 | **Real readers, search-driven** |
| 2026-11-10 | 40 / 43 | watch | top row Direct on `/matching` (5 sessions, 0%), `/numerology` (4); bing / organic `/numerology` 4 sessions at 0%; **21 of 35 sessions zero engagement**, desktop US | 14 | **Mixed, mostly automated.** Not growth |
| 2026-11-12 | 34 / 37 | watch | google / organic, `/muhurat/griha-pravesh` 4 sessions at 100% engaged, 53 s avg for the cohort; Chrome mobile India 14 sessions at 71% | 24 | **Real readers, search-driven** |
| 2026-11-14 | 32 / 47 | watch | google / organic: 10 sessions on rahu-ketu (51% engaged, 111 s), 5 on chronic-health-issues-kundli; Chrome mobile India 11 + Indonesia 9 (67%) | 23 | **Real readers, search-driven.** Not Discover |
| 2026-11-15 | 51 / 56 | spike | google / organic on rahu-ketu (6 sessions, 83% engaged); **Chrome mobile China 9 sessions, 0% engaged, 0 s**; 5 Direct on `/panchang/2026-12-02` at 0%, 1.6 s; India mobile 17 sessions at 59% | 14 | **Mixed, not growth.** China-mobile and dated-panchang rows look automated; India readers look real |

Six days named (the earlier window's 10-23 has aged out). Three (11-06, 11-10, 11-15) carry zero-engagement cohorts that look automated; three (11-09, 11-12, 11-14) are search-driven readers. **None is Discover** (`gsc-discover.json`: 0 clicks, 0 impressions on all 28 days). Two of the three automated-looking dates (11-06, 11-10) carry US desktop sessions with no browser name; #1364 exists to size this cohort.

## 5. Lever 2 — where time is spent (`verify-first.json`, `ga4.json`; W)

| page | sessions | engaged | engaged rate | avg engagement s | GSC impr / clicks / pos |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 73 | 45 | 62% | 146 | 3,527 / 61 / 6.4 |
| `/` | 64 | 40 | 62% | 249 | 216 / 8 / 5.9 |
| /muhurat/griha-pravesh | 31 | 29 | **94%** | 90 | 401 / 20 / 6.6 |
| /learn/gochar-2026-planetary-transits | 45 | 17 | **38%** | **27** | 3,191 / 27 / 5.0 |
| /learn/10th-lord-in-6th-house-career | 29 | 17 | 59% | 159 | 852 / 24 / 6.8 |
| /learn/career-during-sade-sati | 30 | 15 | 50% | 223 | 1,367 / 25 / 5.4 |
| /learn/rahu-mahadasha-career-problems | 27 | 15 | 56% | 261 | 1,159 / 23 / 5.7 |
| /learn/sade-sati | 23 | 13 | 57% | 264 | 2,072 / 17 / 6.6 |
| /learn/7th-lord-placement-marriage-guide | 29 | 11 | **38%** | **54** | 1,500 / 15 / 7.3 |
| /learn/debilitated-sun-career | 25 | 10 | 40% | 214 | 2,999 / 15 / 6.5 |

Page groups (`ga4.json`, folded by landing path; sessions / engaged rate / avg engagement s): `/learn/<article>` 540 / 44% / 115 · `/` 64 / 62% / 249 · `/muhurat*` 45 / 82% / 94 · `/numerology` 19 / 47% / 176 · `/kundli` 19 / 42% / 133 · `/panchang*` 17 / 18% / 76 · `/rashifal*` 14 / 7% / 2 · `/matching` 12 / 17% / 58 · `/admin*` 14 / 36% / 3 (the pre-#735 leak, §4) · `(not set)` 18 / 6% / 12. `/learn/` articles are **68% of sessions** (540 of 792 rows).

**Gochar-2026 detail (`ga4.json` rows for that landing):** 45 sessions = Organic 27 (14 engaged, 52%, 1,148 s total ≈ 43 s each, 1.19 pages/session), **Direct 17 (3 engaged)**, AI Assistant 1. The page-level 27 s is dragged down by the Direct cohort; the Organic cohort is 52% engaged and still short on time. The two weakest large pages on time: **gochar-2026** (27 s) and **7th-lord-placement** (54 s); jupiter-10th is also low (25 sessions, 10 engaged, 60 s average).

**Tool funnels visible from `ga4-events.json` (W; events are not user-linked, so these are not conversion rates):** `form_start` 117 → `kundli_generated` 50 → `form_submit` 1; `tool_submitted` 16; `cta_click` **20** (8 with `(not set)` from/to; the rest: career-during-sade-sati → `/` 3, sade-sati → `/kundli` 2, and one each from kaal-sarp-dosh → `/kaal-sarp-check`, krittika → `/`, name-numerology → `/numerology`, rahu-career-problems → `/dasha`, rahu-ketu → `/dasha`, sade-sati → `/sade-sati-check`, saturn-10th → `/kundli`); `ask_answered` 129; `view_search_results` 5; `feedback_sent` 2; `subscribe_completed` 1; `matching_completed` 1; `dosha_check_completed` 1; `dasha_deep_dive_viewed` 2. `cta_click` is partial history (from 2026-11-03).
The CTA reaches **20 of 790 sessions (2.5%)**. Whether the click rate is low or the CTA is rarely seen is not determinable from event counts alone (no impression event).

## 6. Lever 3 — errors

| source | finding |
|---|---|
| `llm-usage.json` (last 7 days, generated 2026-11-23T01:22Z) | 158 calls, 116 cache hits (**73%**), 42 misses. Input tokens 129,694, output 24,353. **No error or fallback field**, so errors per route are **not measured**; tracked by **#1208** (open) |
| per route (calls / hit rate / tokens per measured call) | natal 97 / 89% / 6,531 (10 measured) · ask 26 / **0%** / 2,032 (26 measured) · rashifal 26 / 100% / not measured · monthly 3 / 66% / 2,116 · matching 3 / 0% / 1,847 · today 3 / 33% / 1,941 |
| tokens per day | `peak_day_tokens` 6,733 (2026-11-22); `peak_day_measured_tokens` 43,421 (2026-11-18). 43,421 against the 200,000 TPD figure in CLAUDE.md is 22%. The file does not say why the two fields differ |
| `verify-production.yml`, last 100 runs, 2026-11-16 → 11-22 | 91 success / 4 failure / 5 cancelled. All 4 failures on 11-16 and 11-17; none in the last 5 days. Causes not read |
| open issues | #1208 (LLM fallbacks export), #1272 (server-side kundli count), #1076 (/matching decay) |

`ask` is the only route with live per-request generation at volume: 26 calls, 0 cache hits, 52,835 input tokens in 7 days. It is per-visitor by nature; nothing here says it is over budget. Groq TPM-ceiling failures (#266-style) cannot be seen in this file.

## 7. Search demand (partial: `gsc-trend-query.json` covers **15%** of impressions — 4,420 of 30,291)

| theme (visible queries only) | queries | impr W | clicks | weighted pos | existing page |
|---|---:|---:|---:|---:|---|
| "sun debilitated" family | 33 | 1,106 (P 35) | 2 | 7.3 | `/learn/debilitated-sun-career/` (0.50% CTR; #835 targets it) |
| "rahu mahadasha / ketu antardasha" | 46 | 931 | 23 | 7.1 | `/learn/rahu-mahadasha-ketu-antardasha/` (1.73%) |
| "jupiter 10th / guru 10th" | 51 | 433 | 1 | 9.5 | `/learn/jupiter-in-10th-house-career/` (1.04%) |
| "7th house / 7th lord" | 48 | 173 | 2 | 10.3 | `/learn/7th-lord-placement-marriage-guide/`, `/learn/planets-in-7th-house-marriage/` |
| "manglik" | 31 | 75 | 1 | 11.6 | `/learn/manglik-dosh/` |
| "mahadasha ... career" | 3 | 65 | 0 | 8.4 | `/learn/rahu-mahadasha-career-problems/`; #1072 shipped for it |
| "gochar / transit" | 27 | 61 | 0 | 9.3 | `/learn/gochar-2026-planetary-transits/` (3,191 impr; most of its queries are withheld) |
| "mahapurush" | 23 | 57 | 0 | 16.2 | `/learn/panch-mahapurush-yoga/` |
| "sade sati" | 32 | 56 | 0 | 8.4 | `/learn/sade-sati/`, `/learn/career-during-sade-sati/` |
| "numerology" | 2 | 20 | 2 | 6.1 | `/numerology` (185 impr, 10 clicks) |
| "muhurat" | 9 | 14 | 0 | 12.6 | `/muhurat/*` |

Themes are keyword matches over the visible queries and sum to far less than 30,291. Top single queries: "rahu mahadasha ketu antardasha" 379 impr (P 260), pos 6.3, 13 clicks; "sun debilitated in which sign" 352 (P 12), pos 7.3, 1 click; "sun is debilitated in which sign" 156, pos 6.2, 0 clicks; "jupiter in 10th house" 118 (P 0), pos 10.9; "10th lord in 6th house" 99 (P 0), pos 8.7, 2 clicks; "guru in 10th house" 81, pos 8.8.

- **Queries with no page:** none with ≥ 10 impressions that lacks an existing page by topic in the visible 15%. Not proof none exist in the invisible 85%. "yes" (112 impr, pos 3.6, 0 clicks) is not a topic.
- **Landing page per query is not determined**: the query export has no page column; "sun debilitated" is attributed to debilitated-sun-career by topic only.
- **`/hi/*`**: 70 impressions in W against 8 in P, 0 clicks.
- **`/festivals`**: 275 impr, 0 clicks, position 38.1 (P 25.8).
- **`/rashifal`**: 137 impr at position 6.9, 1 click; the `/rashifal/{rashi}` pages are in the same group (182 impr in all, `/rashifal*` landings in GA4 are 7% engaged).
- **Zero visible queries match** the names of the six upcoming festivals in §8 (searched: purnima, kartik, vivah panchami/muhurat, gita jayanti, sankranti/pongal, dattatreya, bhairav). **There is no search signal in the visible 15% to read for them.**

## 8. Content opportunities (dates **only from `festivals.py`**, read this run via `festivals_for_date()` over 2026-11-23 → 2027-01-17)

| date | entry in `festivals.py` | slug | existing page found |
|---|---|---|---|
| 2026-11-24 | Kartika Purnima | `kartika-purnima` | `/festivals` only; no `learn/` template |
| 2026-12-01 | Kalabhairav Jayanti | `kalabhairav-jayanti` | `/festivals` only |
| 2026-12-14 | Vivah Panchami | `vivah-panchami` | `/festivals`; wedding-timing intent also served by `learn/vivah-muhurat-2027` (33 impr, pos 9.1, 0 clicks) and `/muhurat/vivah` |
| 2026-12-20 | Gita Jayanti (Mokshada Ekadashi) | `gita-jayanti` | `/festivals` only |
| 2026-12-23 | Dattatreya Jayanti (Margashirsha Purnima) | `dattatreya-jayanti` | `/festivals` only |
| 2027-01-15 | Makar Sankranti; Pongal (Thai Pongal) | `makar-sankranti`, `pongal` | `/festivals` only |

- Only the aggregate `/festivals` serves these, and it ranks 38.1 with 0 clicks. `routes/festivals.py` has one route, `/festivals`. Whether a dedicated page per festival is wanted is product-manager's decision; I name the demand: none appears in the visible queries. I did not check these dates against an almanac; the registry's own QA covers that.
- Kartika Purnima is **tomorrow** (2026-11-24); nothing in this run's data says a page could still earn traffic for it.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` is the largest-growth page (3,191 impr, pos 5.0, 27 clicks, 45 sessions, 38% engaged, 27 s). `gochar-2027-planetary-transits` exists (#1071); its index state was "URL is unknown to Google" on 2026-11-19. `diwali-muhurat-2026` (76 impr, pos 11.2) is past its date. `griha-pravesh-muhurat-2026-2027` left GSC (24 → 0 impr) yet still had 14 GA4 landings.
- **Time-bound page that works:** `/muhurat/griha-pravesh` (401 impr, 20 clicks, 4.99% CTR, 94% engaged, 31 sessions).

## 9. Index status (`measurements/index-status.json`, generated 2026-11-19T20:05Z — four days old; 214 URLs, 0 errors)

| state | URLs |
|---|---:|
| indexed | 166 |
| not indexed | **48** |
| changed after Google's last crawl (`stale`) | 174 |
| canonical mismatch / blocked / unknown | 0 / 0 / 0 |

Not-indexed split (`rows`, counted this run): Crawled – currently not indexed 29, Discovered – currently not indexed 12, URL is unknown to Google 7; Submitted and indexed 166.
Largest `request_indexing` entries read this run: rahu-ketu 3,912 impr (changed 11-16T04:15Z, crawled 11-08T08:35Z), gochar-2026 2,512 (11-17 vs 11-10), sade-sati 2,133 (11-15 vs 10-23), jupiter-10th 1,940 (11-16 vs 11-11), 7th-lord 1,509 (11-16 vs 11-08). The file's impression column is from an earlier window than W; a newer file was not available.

## 10. Measurement gaps, checked against my last three reports (2026-11-20, 11-21, 11-22)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window (sessions/users vs P) | yes, and this run | **#1205** (open, `needs-human-review`) | none: covered |
| `page_location` / query strings in GA4 exports | yes | **#1237** | none: covered |
| Errors / LLM fallbacks per route | yes | **#1208** | none: covered |
| Per-page × per-day export (date the /matching decay, split a page at its deploy) | yes | **#953**, **#1076** | none: covered |
| Shallow checkout: no `git log --since` | yes | **#666**, **#974** | none: covered |
| Server-side kundli submission count | yes | **#1272** | none: covered |
| Share of Direct traffic that is automated | yes | **#1364** (open, filed 2026-11-23 by the 11-22 run) | none: covered |
| Newer `index-status.json` than 2026-11-19 | yes (2026-11-22 and now) | #1065 | none: covered. Four days old now |
| `muhurat_searched` absent from `ga4-events.json` (half of #1336's metric) | second run | none | **not filed**: still one run past its first mention, and #1336's window opens 2026-12-22. It will be filed on the first run after that date if the event is still absent |

No gap is repeated in three reports without an open issue. **No issue filed this run.**

## 11. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| Sessions and users against the previous window | `fetch_ga4.py --trend` listed in `agent-measure` (#1205) |
| How much of Direct (284 sessions, 20% engaged) is automated | the cohort export in #1364 |
| Whether the wk4 dip (GSC impressions −23%, clicks −39% vs wk3) persists | next run's W; the per-page × per-day GSC export (#953) would say which pages fell |
| When /matching lost position (4.4 → 10.0) | `fetch_gsc.py --page-daily` (#953) |
| Whether Google has re-crawled the ten edited top pages | a fresh `index-status.json` (#1065) |
| LLM errors and fallbacks per route | #1208 |
| Why `griha-pravesh-muhurat-2026-2027` (14 landings) and `financial-struggles` (11 Direct landings, 0 engaged) get GA4 sessions with ≈ 0 GSC impressions | URL Inspection on both URLs plus the GA4 source/medium and browser for those 25 landings |
| The landing page behind each query | a query × page GSC export, which Google restricts for anonymised queries |
| Why gochar-2026 Organic readers average about 43 s | per-section scroll depth, which no export carries |
| Why 17 Direct sessions land on gochar-2026 (3 engaged) | GA4 source/browser/country for that landing × Direct cohort (#1364) |

## 12. Actions this run

| action | result |
|---|---|
| Issue comments | **none.** No new issue had a clean window; every pending issue already carries its note; #311, #276, #329 and #1115 verdicts unchanged |
| Issues filed | **none** (#1364 already open for the one repeated gap) |
| Timers | 26 lines written to `/tmp/analyst-timers.txt` (one per pending issue; #1115 has none because it waits on #1205) |
| Re-posts avoided | #311, #276, #329, #1115, and every pending issue |
