# Analyst report — 2026-11-21

**Window W = 2026-10-22 → 2026-11-18** (28 days; the last 3 are excluded: GA4 lags 24–48h, GSC 2–3 days).
**Previous window P = 2026-09-24 → 2026-10-21** (GSC trend files only).
Everything below was read from this run's files. Anything I did not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 29,632 impressions | no | 394 clicks |
| `gsc-all.json` / `gsc-band.json` (`dimension: page`) | W | 100%; `rows_impressions` 29,715 vs property 29,632 (a page row can count a query once per page) | no | band printed 98 rows = 22,265 impressions = **75%** (`emitted_coverage_pct`) |
| `gsc-trend-page.json` | W vs P | 100% of W stated; P coverage **not stated** | no | P page-sum = 11,867 impressions |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **15%** (4,310 of 29,632) | no | Google withholds the rest. No conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 787 sessions (rows sum 789) | no | 93 distinct paths after folding query strings and trailing slashes (100 raw landings) |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum to 791, vs 787 in the landing report: two GA4 reports, not reconciled |
| `ga4-events.json` | W | 17 event names, `events_total` 5,268 | no | `cta_click` exists only from 2026-11-03 (PR #688): partial history |
| `ga4-anomalies.json` | W | 2 spikes, 5 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | 0 clicks, 0 impressions, `top_pages` empty | – | |
| `verify-first.json`, `llm-usage.json` | W / last 7 days | – | – | `llm-usage.json` is 7 days, generated 2026-11-21T01:56Z |
| GA4 previous window | – | **absent** | – | no `ga4-trend.json` in this run (#1205 open). Sessions and users against P are **not measured** |
| `git log origin/main --since` | – | **1 commit** | – | the checkout is shallow (`git rev-parse --is-shallow-repository` = true; #666, #974). Concurrent ships below come from `gh pr list --state merged` instead |

## 1. The 6–20 position band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.*
**The objective cannot be measured as written.** The query export covers 15% of impressions, and in page mode a band `position` is the page's average across its queries. The table below is the page-level proxy.

| metric (W, `dimension: page`) | value |
|---|---|
| pages with impressions | 139 |
| pages at position 6–20 | **98**, 22,265 impressions (75% of the property's), 282 clicks, aggregate CTR **1.27%** |
| of those, pages with ≥100 impressions | 29 |
| pages at average position < 6 | 32 (most with a handful of impressions) |
| of the top-10 pages by impressions, at average position ≤ 5 | **1** (`gochar-2026-planetary-transits`, 5.0) |

Band list, ranked by the file's `band_opportunity` (window W; position = page average):

| # | page | impr | clicks | CTR | pos | P pos |
|---|---|---|---|---|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,751 | 62 | 1.65% | 6.4 | 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,979 | 16 | **0.54%** | 6.6 | 6.1 |
| 3 | /learn/sade-sati/ | 2,135 | 16 | **0.75%** | 6.6 | 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 2,005 | 20 | 1.00% | 7.0 | 6.9 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,478 | 14 | 0.95% | 7.3 | 7.7 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,305 | 10 | 0.77% | 6.8 | 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,051 | 15 | 1.43% | 7.3 | 7.0 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 592 | 3 | **0.51%** | 7.6 | – |
| 9 | /learn/10th-lord-in-6th-house-career/ | 809 | 23 | 2.84% | 6.8 | 7.0 |
| 10 | /learn/manglik-dosh/ | 485 | 4 | 0.82% | 6.5 | – |
| 11 | /learn/shukra-venus-in-vedic-astrology/ | 394 | 2 | **0.51%** | 6.1 | – |
| 12 | /learn/saturn-in-10th-house-career/ | 437 | 6 | 1.37% | 7.7 | – |

Top-10 pages by impressions (all positions, W): rahu-ketu 3,751 · debilitated-sun 2,979 · gochar-2026 2,873 · sade-sati 2,135 · jupiter-10th 2,005 · 7th-lord 1,478 · career-during-sade-sati 1,308 (pos 5.4, P 7.0) · planets-in-7th 1,305 · rahu-mahadasha-career-problems 1,113 (pos 5.8) · panch-mahapurush 1,051. **Nearest to top 5:** career-during-sade-sati (0.4 away) and career-problems (0.8 away). The other seven sit at 6.4–7.3.

### CTR outliers (against the band's own rate: 1.27% aggregate; median of the 17 band pages with ≥300 impressions = 1.00%)

| page | impr | CTR | pos | reading |
|---|---|---|---|---|
| debilitated-sun-career | 2,979 | 0.54% | 6.6 | second-largest band page at roughly half the band rate. At 1.0% it would take about 30 clicks, not 16. #835 (answer-first lede, merged 2026-11-13) targets it; pending |
| sade-sati | 2,135 | 0.75% | 6.6 | #685 (title names the Moon signs, merged 2026-11-03); pending, scoreable 2026-12-04 |
| mangal-mars-in-vedic-astrology | 592 | 0.51% | 7.6 | no issue found on it this run (not searched) |
| shukra-venus-in-vedic-astrology | 394 | 0.51% | 6.1 | same |
| 10th-lord-in-6th-house-career | 809 | 2.84% | 6.8 | the in-band reference at this position |
| /muhurat/griha-pravesh | 381 | 5.51% | 6.1 | best CTR on the site |

### Decay (position worse by ≥1.5 with ≥100 impressions in W)

| page | impr W / P | pos W / P | clicks W / P | note |
|---|---|---|---|---|
| /matching | 121 / 340 | **9.9 / 4.4** | 4 / 0 | #1076 (onset undated; per-page × per-day export #953 not run). #508's title shipped 2026-11-03 |
| /festivals | 281 / 251 | 37.3 / 28.2 | 0 / 0 | far outside the band |

Pages gone from GSC in W (P → W impressions): ketu-in-vedic-astrology 57 → 0, griha-pravesh-muhurat-2026-2027 33 → 0. The index file reads "Crawled - currently not indexed" for the second (last crawl 2026-08-09), yet GA4 shows **14 landings on it in W**. Not explained.

## 2. Scores — issues closed in the last 45 days with a `thesis:` and a `metric:`

Rule: score once, when the window starts on or after the deploy date; otherwise one "pending" note and a timer. Today is 2026-11-21, so the first date a window can start is 2026-10-21: only issues deployed on or before it can score.

### Scored on earlier runs (verdicts re-read this run, nothing re-posted: none moved)

| issue | thesis | predicted | actual (earlier clean window) | verdict | W read this run |
|---|---|---|---|---|---|
| **#311** title/meta rewrite on four band pages | CTR rises at unchanged position | ≥ 1.5% combined on ≥ 1,500 impr | 0.937% (53 / 5,658) | **MISS** | same four pages in W: 62 clicks / 6,582 impr = **0.94%**. Unchanged |
| **#276** /dasha CTA on the Rahu–Ketu article | pages/session rises | ≥ 1.20 | Organic 1.64 | bar met, not attributable to the CTA | Organic 1.64 (66 sessions); all channels 1.54 (78). Unchanged |
| **#329** Manglik checker link | pages/session rises | ≥ 1.30 on ≥ 10 sessions | **3 vs floor 10**: unscoreable | stopped | /learn/manglik-dosh: 8 sessions (4 Organic), pages/session 1.00. Floor still not reached |

**#311 is a miss and stays one.** The title rewrite alone did not reach its bar on three of four pages. Same shape now: debilitated-sun 0.54%, manglik-dosh 0.82%.

### Posted this run

| issue | comment | why |
|---|---|---|
| **#1277** (returning users and `admin_sessions` in the daily export) | **MET**, posted once | `returning.user_days` = 84, status ok, share 11.9%. `admin_sessions` = 0 on all 7 days 2026-11-12 → 2026-11-18. The 15 admin sessions in W are all dated 2026-10-23 → 2026-11-09 (pre-#735) |
| **#1322** (muhurat finder, merged 2026-11-21) | "pending — scoreable from 2026-12-22", posted once | no note existed. Timer written |

### Pending (note already on the issue; nothing posted; timer line written for every one)

| issue | deploy (merge) | scoreable from | read this run, W (pre-deploy or mixed: **not a score**) |
|---|---|---|---|
| #553 | 2026-10-31 | 2026-12-01 | panch-mahapurush-yoga: 20 sessions, pages/session 1.00 |
| #426 | 2026-11-02 | 2026-12-03 | guard: sade-sati pos 6.6 (P 6.2) |
| #508 | 2026-11-03 | 2026-12-04 | /matching 121 impr at pos 9.9: its pass bar needs ≥300 impr within ±1.5 of 4.3. On today's numbers this reads INCONCLUSIVE. Same page as #1076 |
| #685 | 2026-11-03 | 2026-12-04 | sade-sati CTR 0.75% (16 / 2,135) vs 0.63% baseline: pass bar ≥1.2%. W holds 15 post-deploy days, so mixed |
| #570 | 2026-11-03 | 2026-12-04 | `cta_click` = 18 in W (see §5). Window starts before 2026-12-01: partial history |
| #518 | 2026-11-06 | 2026-12-07 | – |
| #528 | 2026-11-09 | 2026-12-10 | – |
| #735 | 2026-11-11 | 2026-12-12 | 0 admin-landing sessions on every day from 2026-11-12 (7 days only) |
| #835 | 2026-11-13 | 2026-12-14 | "sun debilitated" query cluster: 1,085 impr, 2 clicks, weighted pos 7.4 (P: 3 impr) |
| #1066, #1093 | 2026-11-15 | 2026-12-16 | **cannot score**: no export carries `page_location` (#1237) |
| #1073 / #1074 / #1075 | 2026-11-16 | 2026-12-17 | #1073 queries: 51 rows, 426 impr, 1 click, pos 9.6. #1075: 51 rows, 986 impr, 23 clicks, pos 7.3. #1074 floor (≥150 impr) at risk: `/panchang*` pages = 96 impr |
| #1067, #1068, #1072, #1175 | 2026-11-17 | 2026-12-18 | #1068 also needs a server-side count (#1272). #1072: "which mahadasha" queries 75 impr, 0 clicks, pos 7.7 |
| #1071 | 2026-11-17 | 2026-12-18 (guard), **2027-02-28** (main read) | `gochar-2027` index state: "URL is unknown to Google" |
| #1217, #1226, #1229 | 2026-11-18 | 2026-12-19 | – |
| #1069 | 2026-11-19 | 2026-12-20 | – |
| #1322 | 2026-11-21 | 2026-12-22 | muhurat/griha-pravesh: 32 sessions, 30 engaged, bounce 6%, 381 impr at 6.1 |
| #1115 | – | – | **NOT MET, blocked on #1205**: this run has one window, not two. No timer (it waits on #1205, not a date) |

Not scoreable from GA4/GSC (structural or deterministic metrics; noted once earlier): #843, #1176, #1177, #1178, #838, #856, #978, #959, and the infra issues. Not re-read this run.

**Misses this run: #311 (above). No new hit besides #1277.** The two band-page title/lede ships (#685, #835) have no verdict yet. Their pages' CTR in W reads 0.75% and 0.54%, both under the band's 1.27%.

## 3. Confounds, named before any delta

| confound | state |
|---|---|
| Concurrent ships in W | Git history unreadable (shallow). From `gh pr list --state merged`: **many.** Page content: #940 debilitated-sun (11-13), #1005/#1009/#1011 learn corrections (11-14), #1099/#1125 gochar-2026 dates rewritten (11-15/16), #1122 rahu-ketu headings, #1126 jupiter-10th sections (11-16), #1145 vimshottari (11-17). Site-wide: #1179 inbound links (11-17), #1182 nav, #1197 308 redirects (11-17), #1202 meta ≤160 chars (11-18). **Three or more landed on the top pages inside W, so no movement on a top-10 page can be attributed to one ship** |
| Google has not re-crawled the edits | `index-status.json` (2026-11-19T20:05Z) lists the ten largest pages as "changed after Google's last crawl" (rahu-ketu: changed 11-16T04:15Z, last crawl 11-08T08:35Z). Their W position and CTR therefore mostly predate Google seeing the edits |
| Seasonality | Dhanteras 11-06, Diwali 11-08, Chhath 11-15 fall in W (`festival_registry.py`). None of the top-10 pages is a festival page. No year-earlier window exists. Seasonal share: **not determined** |
| Was the page working? | `verify-production.yml`: **30 of 30 runs success**, 2026-11-18T17:15Z → 2026-11-21T01:24Z. That covers only the last 3 days, not W. #266-style Groq failures: see §6 (errors not measured) |
| Sample size | 394 clicks in 28 days. A page with <100 impressions or <10 clicks does not carry a conclusion. Said where it applies |
| Automated traffic | on the two spike days and two watch days named in §4, 19 of 50, 21 of 35 sessions had zero engagement. The share across all of Direct is not measured. I read Organic Search as readers |

## 4. Lever 1 — Growth

### Site level, W

| series | W total | weekly, wk1 → wk4 | first 14 days → last 14 days |
|---|---|---|---|
| GSC impressions | 29,632 | 5,844 → 7,842 → 8,228 → 7,718 | 13,686 → 15,946 (+17%) |
| GSC clicks | 394 | 62 → 93 → 127 → 112 | 155 → 239 (+54%) |
| GA4 sessions (daily report) | 791 | 161 → 153 → 252 → 225 | 314 → 477 (+52%) |
| GA4 active users (sum of daily) | 707 | 137 → 141 → 228 → 201 | – |
| new users (sum of daily) / returning user-days | 661 / 84 | returning 24, 17, 26, 17 | – |
| GSC average position | 6.0–7.5 daily | stable | – |

Weeks: wk1 10-22 → 10-28, wk2 10-29 → 11-04, wk3 11-05 → 11-11, wk4 11-12 → 11-18.

### Against P (GSC only; `gsc-trend-page.json`, P coverage not stated)

| | P (09-24 → 10-21) | W | change |
|---|---|---|---|
| page-summed impressions | 11,867 | 29,715 | **+150%** |
| page-summed clicks | 119 | 394 | **+231%** |
| /learn/* impressions / clicks | 10,615 / 100 | 27,805 / 337 | 94% of W impressions |
| /muhurat* | 147 / 8 | 470 / 25 | |
| / (home) | 105 / 6 | 213 / 10 | |
| /rashifal* | 101 / 0 | 208 / 1 | |
| /panchang* | 93 / 1 | 96 / 2 | flat |
| GA4 sessions / users vs P | **not measured** (#1205) | 787 sessions | |

**Drivers of the change (page, impressions P → W):** gochar-2026 10 → 2,873 (position 6.5 → 5.0; 26 clicks vs 0), debilitated-sun 1,245 → 2,979, rahu-ketu 2,019 → 3,751 (clicks 26 → 62), jupiter-10th 379 → 2,005, career-during-sade-sati 386 → 1,308 (position 7.0 → 5.4; clicks 4 → 23), 10th-lord-in-6th 174 → 809, 7th-lord 274 → 1,478. **Structural vs seasonal: not determined.** The gain is concentrated in /learn pages whose impressions grew 2–280×, which looks like Google surfacing pages it had under-served, not a festival effect. The 2027 comparison does not exist.

**The tail is falling.** Daily impressions 11-14 → 11-18: 1,337 → 1,110 → 908 → 811 → 798, and clicks 23 → 14 → 9 → 10 → 10, at stable position (6.0–7.4). Cause **not determined** (a post-Diwali/Chhath fade, a re-rank, or the late-GSC-data effect). The next run's daily rows settle whether it held.

### Organic vs other (`ga4.json`, W, sessions summed by channel)

| channel | sessions | engaged rate | avg engagement s |
|---|---|---|---|
| Organic Search | **480** (61%) | 58% | 143 |
| Direct | 303 (38%) | **19%** | 45 |
| AI Assistant | 5 | 40% | 157 |
| Unassigned | 1 | 0% | 186 |
| all | 789 | 43% | 105 |

The north star (organic sessions) is **480 in W**. GSC clicks are 394; the gap is Bing and other engines, which GSC does not see. Direct's 19% engagement is the lowest on the site. I did not measure how much of it is automated; §4 spike rows suggest a large share.

### Every day in `spikes` and `watch` — source named

| date | active users (median 22) | tier | source | engagement | GSC clicks that day | Discover | verdict |
|---|---|---|---|---|---|---|---|
| 2026-11-06 | 57 | spike | (direct)/(none) landing /rashifal/aries (6), /kundli, /numerology, /r/zzzzzz; browser "(not set)" desktop US 10 sessions, Chrome desktop US 6 | **19 of 50 sessions zero engagement**; the rest look like readers | 17 | 0 | **mixed, part automated.** Not growth |
| 2026-11-15 | 51 | spike | google/organic /learn/rahu-mahadasha-ketu-antardasha/ (6 sessions, 83% engaged, 242s), Chrome mobile India 17; **plus Chrome mobile China 9 sessions, 0% engaged**; direct /panchang/2026-12-02 5 sessions, 1.6s | – | 14 | 0 | **part real readers, part automated** (the China and /panchang/2026-12-02 rows have no engagement). GSC clicks were not high, so this is not a search jump |
| 2026-11-10 | 40 | watch | direct /matching (5), /numerology (4), bing/organic /numerology (4); "(not set)" desktop US 9, Chrome desktop US 8 | **21 of 35 zero engagement** | 14 | 0 | **automated**, not growth |
| 2026-10-23 | 34 | watch | direct /, /kundli, /matching, /numerology (3–6 each, 0–33% engaged, 3–6s); **Chrome mobile US 26 sessions, 12% engaged** | low | 7 | 0 | **automated-looking**, not growth |
| 2026-11-12 | 34 | watch | google/organic /muhurat/griha-pravesh (4, 100% engaged, 205s), India mobile 14 | real | 24 | 0 | **real search readers** |
| 2026-11-09 | 32 | watch | google/organic jupiter-10th (5), rahu-ketu (5), griha-pravesh (5), 10th-lord (3, 420s) | real | 21 | 0 | **real search readers** |
| 2026-11-14 | 32 | watch | google/organic rahu-ketu (10), chronic-health (5); Chrome mobile India 11, Indonesia 9 | real | 23 | 0 | **real search readers** |

**Google Discover: 0 clicks, 0 impressions on all 28 days, no top pages.** The anomaly file's hint that organic with flat GSC clicks "usually means Discover" does not apply. GSC clicks on the three organic-led watch days were 21, 24 and 23 against a W median I did not compute, and Discover is 0 on each, so I read them as ordinary search.

| series | value (W) |
|---|---|
| returning users (user-days, `returning.status: ok`) | **84 of 707 = 11.9%** (user-days, not people) |
| `admin_sessions`, days from 2026-11-12 (#735) | **0 on all 7 days.** No internal-traffic leak after the fix. The 15 sessions in W are 10-23 (1), 10-24 (1), 10-25 (3), 10-26 (2), 10-28 (1), 11-04 (2), 11-05 (3), 11-09 (2) |

## 5. Lever 2 — Where time is spent (`verify-first.json`, `ga4.json`, W)

| page | sessions | engaged | engaged rate | avg engagement s | GSC impr / clicks / pos |
|---|---|---|---|---|---|
| /learn/rahu-mahadasha-ketu-antardasha | 78 | 47 | 60% | 143 | 3,752 / 62 / 6.4 |
| / | 69 | 41 | 59% | **221** | 214 / 10 / 5.9 |
| /muhurat/griha-pravesh | 32 | 30 | **94%** | 89 | 381 / 21 / 6.1 |
| /learn/gochar-2026-planetary-transits | 43 | 17 | 40% | **29** | 2,873 / 26 / 5.0 |
| /learn/rahu-mahadasha-career-problems | 25 | 16 | 64% | **289** | 1,113 / 22 / 5.8 |
| /learn/10th-lord-in-6th-house-career | 27 | 14 | 52% | 95 | 809 / 23 / 6.8 |
| /learn/sade-sati | 22 | 12 | 55% | 225 | 2,135 / 16 / 6.6 |
| /learn/career-during-sade-sati | 26 | 12 | 46% | 217 | 1,308 / 23 / 5.4 |
| /learn/7th-lord-placement-marriage-guide | 27 | 11 | 41% | **57** | 1,478 / 14 / 7.3 |
| /learn/debilitated-sun-career | 24 | 10 | 42% | 223 | 2,979 / 16 / 6.6 |

- Longest reads: career-problems 289s, sade-sati 225s, debilitated-sun 223s, home 221s.
- Shortest on a large page: gochar-2026 at **29s and 40% engaged** on 43 sessions (the site's third-largest page, position 5.0). Its dates were rewritten 11-15/16, inside W.
- Tool pages in the landing list (sessions, bounce weighted by sessions): /numerology 23 (65%), /kundli 22 (68%), /matching 17 (82%). Pages per session: /numerology 1.13, /kundli 1.68, /matching 1.00.
- Learn pages are 520 of 789 landing-row sessions (66%).
- Home is the deepest page: pages/session 4.23.

### Event counts (`ga4-events.json`, W)

| event | count | caveat |
|---|---|---|
| page_view | 1,374 | |
| ask_answered | 130 | counted before #1157's fix of per-render firing (2026-11-17) for most of W: inflated |
| form_start | 128 | totals across several forms |
| kundli_generated | 54 | same: over-counted re-renders until 2026-11-17 |
| cta_click | **18** | exists from 2026-11-03; 8 of the 18 carry `(not set)` for both paths. The 10 with paths: sade-sati → /kundli 2, career-during-sade-sati → / 2, others 1 each (kaal-sarp-dosh → /kaal-sarp-check, name-numerology → /numerology, two Rahu pages → /dasha, saturn-in-10th → /kundli, krittika → /) |
| subscribe_completed | 1 | |
| form_submit | 1 | reads as instrumentation, not behaviour |
| feedback_sent | 2 | |
| feature_view 783, user_identified 798 | – | dropped from collection on 2026-11-19 (#1234); W counts are partly gone going forward |

**No step-through rate can be computed.** `form_start` and `kundli_generated` are totals across forms, the second inflated. #1070 and #1272 are the open work.

## 6. Lever 3 — Errors

| route (7 days to 2026-11-21, `llm-usage.json`) | calls | cache hits | hit rate | measured calls | tokens/call |
|---|---|---|---|---|---|
| natal | 110 | 101 | 91% | 9 | 6,499 |
| rashifal | 28 | 28 | 100% | 0 | **not measured** |
| ask | 25 | 0 | **0%** | 25 | 2,067 |
| today | 4 | 1 | 25% | 3 | 1,921 |
| matching | 1 | 0 | 0% | 1 | 1,929 |
| monthly | 1 | 0 | 0% | 1 | 2,075 |

- Totals: 169 calls, 130 hits (76%), 119,962 input + 21,737 output tokens.
- **Errors and fallbacks per route: not measured.** `llm-usage.json` carries no error or fallback key, so I cannot name a route with errors. Tracked by **#1208** (open). Not re-filed.
- Production health: `verify-production.yml` 30 of 30 recent runs succeeded (2026-11-18T17:15Z → 2026-11-21T01:24Z).
- `peak_day_tokens` 6,529 and `peak_day_measured_tokens` 43,421 both name 2026-11-18. I did not read `collect_llm_usage.py`, so I cannot say which one is the day's total. #925 (open) tracks the Groq daily budget.
- `ask` has 0% cache hits across 25 calls: expected for personal questions; it is the route that costs most per visit.

## 7. Lever 4 — Search demand

Query view covers **15%** (4,310 impressions of 29,632). It does not say which page serves a query. Themes by regex on query text; the page named is the one I know of, **not measured**.

| theme | queries | impr (W) | clicks | weighted pos | P impr | existing page |
|---|---|---|---|---|---|---|
| sun debilitated (which sign / libra / degree / meaning) | 34 | **1,085** | **2** | 7.4 | 3 | /learn/debilitated-sun-career (0.54% CTR; #835 pending) |
| rahu mahadasha / ketu antardasha | 51 | 986 | 23 | 7.3 | 561 | /learn/rahu-mahadasha-ketu-antardasha (#1075 pending) |
| jupiter / guru in 10th house | 51 | 426 | **1** | **9.6** | 1 | /learn/jupiter-in-10th-house-career (#1073 pending) |
| 10th lord in 6th house | 6 | 157 | 2 | 8.6 | 0 | /learn/10th-lord-in-6th-house-career |
| which mahadasha is best for career | 7 | 75 | 0 | 7.7 | 0 | /learn/vimshottari-dasha-explained (#1072 pending) |
| manglik / mangal dosha | 47 | 94 | 1 | 10.3 | 79 | /learn/manglik-dosh |
| sade sati / 7.5 sani | 47 | 81 | 0 | 8.1 | 38 | /learn/sade-sati |

Single queries worth naming: `rahu mahadasha ketu antardasha` 397 impr, 13 clicks, pos 6.5; `sun debilitated in which sign` 338, 1 click, pos 7.4; `jupiter in 10th house` 116, 0 clicks, pos 11.0; `bhagya chart` 26 impr, 4 clicks, pos 6.5; `cheiro numerology calculator` 17, 2 clicks, pos 5.8; **`yes` 108 impressions, 0 clicks, pos 3.6**, unexplained (not investigated).

**Queries with no page.** Not determinable from this export. `/numerology` is the likely page for the Cheiro query (173 impr, 9 clicks, pos 6.2 in W); that mapping is by topic, not measured. I name no new page. The three clusters new in W (sun debilitated, jupiter 10th, 10th lord in 6th) each have a page and a pending ship.

Pages with impressions and zero clicks worth a title look (impr ≥ 100, W): guru-jupiter-in-vedic-astrology (185, 0), kundali-matching-ashtakoot-guna-milan (122, 0), /learn/ (119, 0), pushya-nakshatra (101, 0, "Crawled - currently not indexed"). The first three are in the band list.

## 8. Lever 5 — Content opportunities (dates **only** from `festival_registry.py`, read this run)

| date | festival | tier | learn article by that name |
|---|---|---|---|
| 2026-11-20 | devuthani-ekadashi | – | none |
| 2026-11-21 | tulsi-vivah | major | none |
| 2027-01-15 | makar-sankranti | major | none |
| 2027-01-15 | pongal | major | none |

- **The registry holds no festival between 2026-11-22 and 2027-01-14 (54 days).** In my last three reports and this one. I supply no date. **Filed as #1326** (below).
- Existing time-bound pages: `diwali-muhurat-2026`, `karva-chauth-2026` (7 impr, 0 clicks: its date has passed), `gochar-2026-planetary-transits`, `gochar-2027-planetary-transits`, `vivah-muhurat-2027`, `griha-pravesh-muhurat-2026-2027`.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` is the site's third-largest page (2,873 impr, pos 5.0, 29s engagement). `gochar-2027-planetary-transits` exists (merged 2026-11-17) and Google reads it as **"URL is unknown to Google"** (index file 2026-11-19). `griha-pravesh-muhurat-2026-2027` and `vivah-muhurat-2027` are "Crawled - currently not indexed".
- Sibling pages in the query view show muhurat demand: /muhurat/griha-pravesh 381 impr, 21 clicks (5.5% CTR, pos 6.1); /muhurat/vivah 25 / 1 / 5.6; /muhurat/vidyarambh 45 / 0 / 6.1 (P 89 / 2).

## 9. Lever 6 — Index status (`measurements/index-status.json`, generated 2026-11-19T20:05Z)

| count | value |
|---|---|
| URLs inspected | 214 of 214, 0 errors, quota 214 of 2,000 |
| indexed | 166 |
| **not indexed** | **48** = 29 "Crawled - currently not indexed" + 12 "Discovered - currently not indexed" + 7 "URL is unknown to Google" |
| blocked / canonical mismatch | 0 / 0 |
| stale (changed after last crawl) | 174 (the file's own note says this overstates: base templates are excluded on purpose, `/rashifal*` and `/panchang*` change by data) |

Not indexed, ranked by W impressions: pushya-nakshatra 124 · ashwini-nakshatra 89 · mars-remedies 71 · vivah-muhurat-2027 42 · rohini-nakshatra 41 · jupiter-remedies 39 · swati-nakshatra 32 · dhana-yoga-wealth-combinations 31 · the-9-grahas-overview 24 · marriage-delayed 23. "Unknown to Google": /dasha, five /panchang dated URLs (2026-11-09, 2027-01-04, 01-15, 01-16, 01-17), gochar-2027.

**Request-indexing list (the file's own, ranked by value):** all ten are "changed after Google's last crawl": rahu-ketu (3,912 impr; changed 11-16, crawled 11-08), gochar-2026 (2,512), sade-sati (2,133; crawled **2026-10-23**, 29 days earlier), jupiter-10th (1,940), 7th-lord (1,509), career-during-sade-sati (1,239), planets-in-7th (1,221), rahu-mahadasha-career-problems (1,044), 10th-lord-in-6th (762), mangal-mars (557). **The edits the #685/#835/#1073/#1075 scores will measure may not have been seen by Google.** I cannot request indexing (no write path); #1065's remaining step is a workflows edit. This list is for chief or the owner.

## 10. Lever 7 — Measurement gaps (checked against `measurements/2026-11-18.md`, `-19.md`, `-20.md`)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window | yes, and this run | #1205 | covered |
| `page_location` / query strings in GA4 exports | yes | #1237 | covered |
| Errors / LLM fallbacks per route | yes | #1208 | covered |
| Per-page × per-day GSC export | yes | #953, #1076 | covered |
| Full git history (shallow checkout) | yes, and this run (1 commit) | #666, #974 | covered |
| Server-side completed-kundli count | 11-18, 11-19, 11-20 | #1272 | covered (filed last run) |
| Which page serves which query | 11-17, 11-19, 11-20, **and this run** (query export has no page column) | none | **not filed**: 11-18 did not name it as a gap, so it does not meet "all three". If 11-22 names it too, file |
| **Festival registry empty 2026-11-22 → 2027-01-14** | **11-18, 11-19, 11-20, and this run** | none found (searched open and closed) | **filed #1326** |
| Index status per URL | was a gap on 11-18, 11-19 | #1065 | resolved: the file exists |

## 11. What I did this run

| action | result |
|---|---|
| Comments posted | **#1277** (MET), **#1322** (pending → 2026-12-22) |
| Issues filed | **#1326** — festival registry has no entry for 54 days; label `growth`; Evidence Block passes `verify_issue_evidence.py` (a first draft failed on `corpus:`; fixed, re-run PASS) |
| Timers | **25 lines** in `/tmp/analyst-timers.txt`: every pending issue above, `#1322` new, `#1071` has two keys (`score-1071` 2026-12-18, `score-1071-final` 2027-02-28). `#1115` gets none (waits on #1205). I did not verify that `agent-measure` sets them |
| Re-read, nothing posted | #311, #276, #329: no verdict changed and no number moved past what the metric calls material |

## 12. What I could not determine, and the one measurement that settles each

| unknown | measurement |
|---|---|
| Sessions and users against the previous window | `fetch_ga4.py --trend` wired into `agent-measure` (#1205) |
| Whether the +150% impressions is the work, a seasonal effect, or Google re-ranking a young domain | a per-page × per-day export plus the dated ship list (#953); no year-earlier window exists |
| Which ship moved which page | a full-depth checkout in the analyst job (#666, #974) |
| Whether the 11-15 → 11-18 fall in impressions (1,110 → 798) held | the next run's daily rows |
| Whether any route is erroring for visitors | `fallbacks` and `fallback_reasons` in `llm-usage.json` (#1208) |
| How much of Direct (303 sessions, 19% engaged) is automated | a by-tech breakdown of the whole Direct channel, not only spike days |
| Whether the top-10-queries-into-top-5 objective is moving | cannot be recovered: 85% of impressions are withheld from the query export. The page-level proxy (1 of the top 10 at ≤5.0) is all I can state |
| Why `griha-pravesh-muhurat-2026-2027` gets GA4 sessions (14) with no GSC impressions and a "not indexed" verdict | a URL Inspection reading dated inside W; the file is dated 11-19 |
| Whether Google has now re-fetched the ten edited pages | the next index-status run's `lastCrawlTime` against `changed_at` |
| `peak_day_tokens` 6,529 vs `peak_day_measured_tokens` 43,421 (both 2026-11-18) | the field definitions in `collect_llm_usage.py`, which I did not read |
| What the `yes` query (108 impr, pos 3.6, 0 clicks) is | the page it lands on, from a page × query export |
| Whether #1066 / #1093's privacy fixes worked | an export carrying GA4 `page_location` (#1237) |
