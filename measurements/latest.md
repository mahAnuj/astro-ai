# Analyst report — run 2026-11-19

**Window for every number below: 2026-10-20 → 2026-11-16** (28 days; the last 3 days are excluded, GSC lags 2–3 days and GA4 24–48h).
**Previous GSC window** where a delta is quoted: **2026-09-22 → 2026-10-19** (`gsc-trend-*.json`). **GA4 has no previous-window export, so no GA4 period-on-period number appears here.** #1115 (the fetch flag) and #1205 (the workflow call) are both open.
Every figure was read from `/tmp/*.json`, `src/astro_ai/festivals.py` or `gh` this run. Quotes from earlier reports are labelled as such. This window is the 2026-11-18 report's window moved forward one day.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | note |
|---|---|---|---:|---|---|
| `gsc-band.json` | page, position 6–20 | 10-20 → 11-16 | 100% of 28,918 property impressions (rows sum 29,002) | no | `emitted_*`: 97 pages, 21,667 impressions = **75%** |
| `gsc-all.json` | page | same | 100% | no | 141 pages |
| `gsc-daily.json` | date | same | 100% | no | 28 days, 28,918 impressions, 383 clicks |
| `gsc-trend-page.json` | page, now vs previous | 10-20 → 11-16 vs 09-22 → 10-19 | 100% | – | 141 pages now, 127 previous. Page-row sums: 29,002 / 383 now, 11,652 / 117 previous |
| `gsc-trend-query.json` | query, now vs previous | same | **14%** of 28,918 | – | partial view (Google withholds rare queries); 843 keys now, 214 previous; 965 rows, 4,167 impressions, 43 clicks. No site-wide conclusion can come from it |
| `ga4.json` | landing × channel | same | 100% of 776 sessions (rows sum 778) | no | 154 rows, 101 raw landings, 94 after folding query strings and trailing slashes |
| `ga4-daily.json` | date | same | 28 of 28 days | – | daily sessions sum to 780 against the property total 776; I use 776 for totals |
| `ga4-events.json` | event | same | 17 event names, 5,222 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688), so about 14 of the 28 days |
| `ga4-anomalies.json` | spike days | same | 2 spikes flagged | – | rule: active users ≥ max(2 × median, median + 10, 15); median 22, bar 44 |
| `gsc-discover.json` | Discover | same | – | – | 0 clicks, 0 impressions on all 28 days, `top_pages` empty |
| `verify-first.json` | busiest pages | same | top 10 by engaged sessions | – | |
| `measure/llm-usage.json` | app LLM calls | **7 days to 2026-11-19 02:13Z** | – | – | a different window from everything else |
| `index-status.json` | – | – | **absent** | – | not measured (section 10) |

## 1. Growth (lever 1)

**Search, GSC, 2026-10-20 → 11-16 against 2026-09-22 → 10-19** (page-row sums; property totals now 28,918 / 383):

| metric | now | previous | change |
|---|---:|---:|---:|
| impressions | 29,002 | 11,652 | 2.49× |
| clicks | 383 | 117 | 3.27× |
| CTR | 1.32% | 1.00% | +0.32 pt |
| average position (daily rows, now) | 6.1–7.6, no trend | – | – |

**GA4, 2026-10-20 → 11-16 only (no previous window):**

| metric | value |
|---|---:|
| sessions (`ga4.json` total) | 776 |
| new users (sum of daily rows; `first_visit` event = 640) | 640 |
| engaged sessions / engagement rate (row sums, 778 sessions) | 340 / 43.7% |
| average engagement per session | 107 s |

| channel | sessions | share | engaged rate | avg engagement per session | pages/session |
|---|---:|---:|---:|---:|---:|
| Organic Search | 474 | 61% | 57.0% | 140 s | 1.75 |
| Direct | 295 | 38% | 22.4% | 49 s | 1.66 |
| AI Assistant | 7 | 1% | 42.9% | 184 s | 4.71 |
| Unassigned | 2 | <1% | 50% | 260 s | 0.50 |

The 7 AI Assistant sessions landed on `second-marriage-yoga-kundli` (2) and one each on `gochar-2026-planetary-transits`, `griha-pravesh-muhurat-2026-2027`, `marriage-mahadasha-timing`, `saturn-in-10th-house-career` and `/matching`. 7 sessions cannot carry a conclusion.

**Within the window** (first 14 days 10-20 → 11-02 against last 14 days 11-03 → 11-16, same files):

| | first 14 days | last 14 days |
|---|---:|---:|
| GA4 sessions (daily rows) | 291 | 489 |
| GSC impressions | 12,189 | 16,729 |
| GSC clicks | 137 | 246 |

The last two days fall back (11-15: 1,110 impressions, 14 clicks; 11-16: 908 impressions, 9 clicks; 11-16 also has 14 GA4 sessions, the lowest since 10-22). Two days are not a trend and 11-16 is a Monday after Chhath; I draw no conclusion.

**Which page groups drive the GSC change** (`gsc-trend-page.json`, impressions / clicks now vs previous):

| group | impressions now | previous | clicks now | previous |
|---|---:|---:|---:|---:|
| `/learn/*` articles | 27,019 | 10,494 | 326 | 100 |
| `/muhurat/*` | 522 | 92 | 26 | 7 |
| other (tools, hubs) | 867 | 781 | 19 | 4 |
| home | 206 | 103 | 9 | 5 |
| `/rashifal*` | 287 | 91 | 1 | 0 |
| `/panchang*` | 101 | 91 | 2 | 1 |

Articles carry 93% of impressions and 85% of clicks. 46 pages are new this window (219 impressions in total) and 32 are gone. The rise is concentrated in a few pages: `gochar-2026-planetary-transits` 10 → 2,512 impressions, `rahu-mahadasha-ketu-antardasha` 1,996 → 3,912, `debilitated-sun-career` 1,210 → 2,915, `jupiter-in-10th-house-career` 369 → 1,940, `7th-lord-placement-marriage-guide` 259 → 1,509, `sade-sati` 1,065 → 2,133.

**Seasonal or structural?** Both inputs are present and I cannot separate them.
- **Calendar** (`festivals.py`, read this run): Dussehra 10-20, Sharad Purnima 10-25, Karva Chauth 10-29, **Dhanteras 11-06, Diwali 11-08**, Govardhan Puja 11-10, Bhai Dooj 11-11, Chhath Puja 11-15 are all inside the window. None of the ten highest-impression pages is a festival page: they are Rahu/Ketu, Sun-debilitated, Sade Sati, 7th-house and career guides. The rise is not a festival-page rise.
- **Structural:** the top gainers are pages the loop edited. 300 or more PRs merged since 2026-10-20 (`gh pr list`, capped at 300), so I cannot attribute the rise to any one. **This checkout is shallow** (`git rev-parse --is-shallow-repository` = true; `git log origin/main --since=2026-10-20` returns 1 commit) (#666, #974).
- **Not determinable:** how much is Google re-ranking a young domain versus the work. No year-earlier window exists.

**Spike days** (`ga4-anomalies.json`, rule bar 44 active users) — identical to the 2026-11-18 report's two days:

| date | active users | source named by the file | verdict |
|---|---:|---|---|
| 2026-11-06 (Dhanteras) | 57 (59 sessions) | top row `(direct) / (none)` on `/rashifal/aries` (6 sessions, 17% engaged, 3.5 s). 19 of 50 sessions had zero engagement: `(not set)`/desktop/US 10, Chrome/desktop/US 6, Chrome/mobile/US 3 | **Mixed.** About 19 sessions look automated. The rest include google/organic readers of `/learn/rahu-mahadasha-career-problems/` (4 sessions, 224 s). GSC clicks that day 17, level with 12–19 around it. Discover 0 |
| 2026-11-15 (Chhath Puja) | 51 (56 sessions) | top row google / organic on `/learn/rahu-mahadasha-ketu-antardasha/` (6 sessions, 83% engaged, 242 s). Chrome/mobile/**China** 9 sessions, 0% engaged, 0 s; Chrome/mobile/India 17 sessions (59% engaged, 61 s). 5 direct sessions on `/panchang/2026-12-02`, 0% engaged, 1.6 s | **Mixed.** The 9 China-mobile sessions and the 5 dated-panchang sessions look automated. The India readers look real. GSC clicks that day 14 against a window mean of 13.7 (383 / 28), so search did not spike. Discover 0, so **not Discover** |

Neither spike is reported as growth. **Five other days at or above `median + 10` (32 users) have no breakdown**: 10-23 (34 users, 34 sessions), 11-09 (32 / 37), 11-10 (40 / 43), 11-12 (34 / 37), 11-14 (32 users / 47 sessions, 1.47 sessions per user, the highest ratio). GSC clicks on those days: 7, 21, 14, 24, 23. I cannot name their source. **Filed as #1236.**

Two Direct oddities in `ga4.json`, not broken down by source: `/learn/financial-struggles` took **9 Direct sessions, 0 engaged**, against 4 GSC impressions; `/r/zzzzzz` took 4 sessions (3 Direct). Neither looks like an audience.

**Confound — Direct is not clean.** Direct is 38% of sessions at 22.4% engaged against 57.0% for Organic. Its pages per session (1.66) is close to Organic's (1.75), which is not what real repeat visitors look like, and both spike days carry zero-engagement Direct rows. I do not treat Direct sessions as audience. 17 of the 776 sessions are `/admin/ops` (16 Direct): internal.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page mode measures pages (a page's position is its average across its queries). Query mode covers 14%.

**Band, page mode** (`emitted_*`, 75% of impressions): 97 pages, 21,667 impressions, 273 clicks, **CTR 1.26%** (impressions-weighted). 82 of the 97 are at position ≤ 10 (21,423 impressions). **62 of the 97 had zero clicks**, covering 1,190 impressions (5.5% of the band).

Top 10 by `band_opportunity` (page mode):

| # | page | impressions | clicks | CTR | avg position | previous impressions / position |
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

**Top-5 test, pages.** The ten highest-impression pages (`gsc-all.json`) are `rahu-mahadasha-ketu-antardasha` (6.4), `debilitated-sun-career` (6.5), `gochar-2026-planetary-transits` (2,512 / 24 clicks / **5.1**), `sade-sati` (6.6), `jupiter-in-10th-house-career` (7.1), `7th-lord-placement-marriage-guide` (7.2), `career-during-sade-sati` (1,239 / 22 / **5.4**), `planets-in-7th-house-marriage` (6.8), `rahu-mahadasha-career-problems` (1,044 / 21 / **5.8**) and `panch-mahapurush-yoga` (7.1). **0 of the ten are at average position ≤ 5.0.** Three are within 1 position (5.1, 5.4, 5.8). Pages at ≤ 5.0 with ≥ 50 impressions: `chronic-health-issues-kundli` (439 impressions, 11 clicks, 4.9) and `2nd-lord-placement-wealth-guide` (79, 3 clicks, 4.3).

**Top-5 test, queries** (`gsc-trend-query.json`, **14% of impressions, partial**). Ten highest-impression queries:

| query | impressions | previous | clicks | position | previous position |
|---|---:|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 424 | 259 | 13 | 6.7 | 9.8 |
| sun debilitated in which sign | 319 | 0 | 1 | 7.5 | – |
| sun is debilitated in which sign | 138 | 0 | 0 | 6.7 | – |
| jupiter in 10th house | 112 | 0 | 0 | 11.1 | – |
| yes | 101 | 7 | 0 | 3.6 | 3.9 |
| 10th lord in 6th house | 94 | 0 | 2 | 8.6 | – |
| sun debilitated sign | 82 | 2 | 0 | 5.9 | 3.0 |
| sun debilitated | 76 | 0 | 0 | 8.9 | – |
| guru in 10th house | 73 | 0 | 0 | 8.9 | – |
| rahu mahadasha and ketu antardasha | 66 | 50 | 0 | 7.1 | 9.4 |

- **1 of 10 is at position ≤ 5, and it is `yes` (3.6), a query nobody targets.** None of the nine real queries is in the top 5. The objective is unmet on the measured 14%; the other 86% cannot be read.
- The best mover is the head query: position 9.8 → 6.7 on 259 → 424 impressions, 13 clicks now. Its previous-window clicks are not in the extract, so I quote no click change.
- The "sun debilitated" family (regex `sun.*debilit|debilit.*sun|surya.*neech`) is 33 rows, 1,022 impressions, **1 click**, weighted position 7.4. It is the family #835 targets (PR #940, merged 2026-11-13), so only the last 4 days of this window carry that change.

**CTR outliers.** Pages with ≥ 500 impressions, position ≤ 7.5 and CTR below the band's own 1.26%:

| page | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,915 | 16 | 0.55% | 6.5 |
| /learn/gochar-2026-planetary-transits/ | 2,512 | 24 | 0.96% | 5.1 |
| /learn/sade-sati/ | 2,133 | 16 | 0.75% | 6.6 |
| /learn/jupiter-in-10th-house-career/ | 1,940 | 18 | 0.93% | 7.1 |
| /learn/7th-lord-placement-marriage-guide/ | 1,509 | 14 | 0.93% | 7.2 |
| /learn/planets-in-7th-house-marriage/ | 1,221 | 11 | 0.90% | 6.8 |
| **six pages** | **12,230** | **99** | **0.81%** | |

At the band's own rate the six would have taken about 154 clicks, a gap of **about 55 clicks per 28 days**. Same-position pages that beat the band: `10th-lord-in-6th-house-career` 2.62% at 6.7, `rahu-mahadasha-career-problems` 2.01% at 5.8, `chronic-health-issues-kundli` 2.5% at 4.9. I did not examine their query mix and hold no CTR-by-position curve for the site, so I size no gain from position.

## 3. Decay

`gsc-trend-page.json`, pages with ≥ 30 impressions in the previous window and a worse position, fewer impressions, or a loss:

| page | impressions now / previous | position now / previous | clicks now / previous | note |
|---|---|---|---|---|
| /matching | 124 / 330 | **9.1 / 4.3** | 4 / 0 | the one loss on a tool page. #1076 open; #508 title change shipped 2026-11-03, and I still cannot date the onset (#953) |
| /learn/planets-in-7th-house-marriage/ | 1,221 / 563 | 6.8 / 5.8 | 11 / 6 | impressions doubled while position fell a place; a top-10 page |
| /festivals | 293 / 245 | 36.0 / 29.5 | 0 / 0 | impressions up, position down; no clicks in either window |
| /learn/the-9-grahas-overview/ | 24 / 104 | 9.8 / 7.9 | 0 / 0 | |
| /learn/ashwini-nakshatra/ | 89 / 103 | 7.7 / 5.6 | 1 / 1 | |
| /learn/mars-remedies/ | 71 / 124 | 6.9 / 6.6 | 1 / 1 | |
| /learn/ketu-in-vedic-astrology/ | **0** / 62 | – / 7.2 | 0 / 1 | gone from GSC this window |
| /learn/griha-pravesh-muhurat-2026-2027/ | **0** / 36 | – / 7.3 | 0 / 0 | gone from GSC, but GA4 shows **14 sessions** on it (9 Organic Search, 4 Direct, 1 AI Assistant; 2 engaged, 4 s average). Fourth report with this gap; noted on #953 |
| /learn/santan-prapti-children-in-kundli/ | 18 / 50 | 6.2 / 6.2 | 0 / 0 | |
| /learn/financial-struggles/ | 4 / 38 | 5.0 / 6.7 | 0 / 0 | see the 9 zero-engagement Direct sessions in section 1 |
| /learn/gajakesari-yoga/ | 5 / 33 | 3.2 / 6.0 | 0 / 0 | impressions down, position up |
| /learn/vivah-muhurat-2027/ | 42 / 54 | 9.2 / 8.6 | 0 / 0 | |

Every page here is small in absolute terms except `planets-in-7th-house-marriage` and `matching`. The clearest loss remains `/matching`.

**Confound — concurrent ships.** 300 or more PRs merged since 2026-10-20, many on the very pages that moved (content, grounding, title and link changes). With a shallow checkout I cannot list them by date from git, so I attribute no movement to any single ship.

## 4. Scores for closed issues carrying `thesis:` and `metric:`

Rule applied: score once, when the window is clean (window start on or after the deploy). Today − 31 days is 2026-10-19; this window starts 2026-10-20. I read the existing analyst comments on every issue first. Merge dates are from `gh pr view`. 185 closed issues since 2026-10-05 match `thesis:` and `metric:` by text; most carry a deterministic or infra metric, and the ones below are the ones a GA4/GSC read can speak to.

**Posted this run (7 comments on issues, each the first analyst note there; all deployed after the window ended, 2026-11-16 → 11-18):**

| issue | deploy | what I posted |
|---|---|---|
| #1217 completion events (matching, numerology, muhurat, doshas) | PR #1218, 2026-11-18T12:53Z | **pending, scoreable from 2026-12-19**. The metric is "four event names with a non-zero count in `ga4-events.json`". None of the new names is in this window's export (17 event names), so the baseline is zero by construction. Timer set |
| #1226 `tool_submitted` + `--journeys` | PR #1227, 2026-11-18T21:07Z | **pending, scoreable from 2026-12-19**: `tool_submitted` for ≥ 6 of 9 tools. Timer set |
| #1229 login, language_switched, share | PR #1230, 2026-11-18T23:22Z | **pending, scoreable from 2026-12-19**. Timer set |
| #1178 meta descriptions ≤ 160 | PR #1202, 2026-11-18T03:36Z | **not scoreable from GA4/GSC**: a count the gate enforces; the issue claims no CTR. Posted the CTR reference: band CTR 1.26% on 21,667 impressions. No timer |
| #1080 debilitated-sun grounding | PR #1118, 2026-11-16T03:17Z | **not scoreable from GA4/GSC**: deterministic. Posted reference: 2,915 impressions, 0.55% CTR, position 6.5; concurrent ship #835 (PR #940, 2026-11-13). No timer |
| #1083 10th-lord-in-6th grounding | PR #1121, 2026-11-18T02:13Z | **not scoreable from GA4/GSC**: deterministic. Posted reference: 762 impressions, 2.62% CTR, position 6.7. No timer |
| #953 (a comment on an open issue, not a score) | – | `griha-pravesh-muhurat-2026-2027`: 0 GSC impressions against 14 GA4 sessions; the `--page-daily` export settles the GSC half and not the GA4 source half |

**Already scored or pending, nothing posted this run** (the verdict has not changed and no number moved past what its metric calls material):

| issue | deploy | clean? | last posted | this run | verdict |
|---|---|---|---|---|---|
| **#311** four-page title/meta CTR test | PR #334, 2026-10-13 | yes | MISS, 2026-11-13 (0.937%); re-checked 2026-11-17 (0.981%) and 2026-11-18 (0.958%) | `rahu-mahadasha-career-problems`, `debilitated-sun-career`, `jupiter-in-10th-house-career`, `manglik-dosh`: **6,388 impressions, 59 clicks, CTR 0.924%** vs bar ≥ 1.5%; weighted position 6.6. Previous window: 2,880 impressions, 18 clicks, 0.625% | **MISS, unchanged** (0.958 → 0.924%, not material) |
| **#276** /dasha CTA on the Rahu–Ketu article | PR #342, 2026-10-14 | yes | BAR MET, not attributable (2026-11-14) | Organic Search **69 sessions, 1.61 pages/session** (bar ≥ 1.20 on ≥ 20). All other `/learn/*` organic landings combined: **307 sessions at 1.62** | **BAR MET, not attributable**. The comparison group is level, so the CTA is not credited |
| **#329** Manglik checker link | PR #344, 2026-10-14 | yes | UNSCOREABLE 3 vs 10 | Organic Search **4** sessions on `/learn/manglik-dosh/`, 1.00 pages/session (floor 10) | unscoreable at this traffic; scoring stays stopped |
| #508 /matching title/meta | PR #696, 2026-11-03 | no | pending, scoreable from 2026-12-04 | reference only: 124 impressions at 9.1 (pass condition needs ≥ 300 impressions at ≥ 1.0% CTR); 4 clicks | pending; the floor looks unreachable at 124 impressions |
| #685 /learn/sade-sati title | PR #690, 2026-11-03 | no | pending | reference only: 2,133 impressions, 16 clicks, 0.75%, position 6.6 (previous 1,065 / 6.2). Mixed window | pending |
| #426 sade-sati date guard | PR #673, 2026-11-02 | no | pending | reference only: position 6.6 (guard: within ±1 of 6.2) | pending |
| #553 panch-mahapurush link | PR #615, 2026-10-31 | no | pending, scoreable 2026-12-01 | not scored | pending |
| #518 learn → tool routes | last slice PR #754, 2026-11-06 | no | pending | not scored | pending |
| #835 debilitated-sun lede and FAQ | PR #940, 2026-11-13 | no | pending | not scored; the deploy is the last 4 days of this window | pending |
| #570 `cta_click` event | PR #688, 2026-11-03 | no | pending | `cta_click` read in section 5: 17 events | pending |
| #528 /ask `q=` out of GA4 | PR #801, 2026-11-09 | no | pending | reference only: **0** landings carry `?q=` in this window (previous report: 1), though it holds 20 pre-fix days. Not a score | pending |
| #735 /admin out of GA4 | PR #877, 2026-11-11 | no | pending | reference only: 17 sessions on `/admin/*` (all `/admin/ops`), the window holds 22 pre-fix days. Not a score | pending |
| #1071 / #1072 / #1175 / #1067 / #1068 / #1073 / #1074 / #1075 / #1066 / #1093 | 2026-11-15 → 11-17 | no | pending notes posted 2026-11-17 | not re-posted | pending, scoreable 2026-12-16 → 12-18 |
| #1176, #1177, #843 | – | – | not scoreable from GA4/GSC | not re-scored | stopped |
| #514, #523 | – | – | unscoreable at this traffic | not re-scored | stopped |

**Timers.** `/tmp/analyst-timers.txt` holds 23 lines (19 first-key timers for the pending issues, 3 new ones for #1217, #1226, #1229, and `score-1071-final` for 2027-02-28). I checked each of the 19 older pending issues for a `github-actions` timer comment this run: **19 of 19 have one** (due dates 2026-12-01 → 12-18). `score-1071-final` (2027-02-28) is **not** on #1071: only `score-1071` (2026-12-18) is. That matters to #1187's metric ("100% of the analyst's pending-score notes become timers"); the line is written again so `set --from-file` can retry it.

### The misses, as plainly as the hits

| result | what it says |
|---|---|
| **#311 MISS** (0.924% vs ≥ 1.5%) | A title/meta rewrite on four band pages did not reach the bar. CTR on the four rose from 0.625% to 0.924%, but their impressions grew 2.2× (2,880 → 6,388) and `rahu-mahadasha-career-problems` moved from position 7.0 to 5.8, so the rise is not attributable to the titles. Three of the four are still below 1% (`debilitated-sun-career` 0.55%, `jupiter-in-10th-house-career` 0.93%, `manglik-dosh` 0.82%) at position 6.5–7.1 |
| **#329 unscoreable** (4 organic sessions vs floor 10) | The page ranks (489 impressions, position 6.5) but yields 4 organic sessions in 28 days, so a link on it cannot be measured at that traffic |
| **#276 bar met, not attributable** (1.61 vs ≥ 1.20) | The comparison group of other `/learn/*` organic landings sits at 1.62 on 307 sessions. The CTA is not credited |
| **#508 will probably not be scoreable as written** | It needs ≥ 300 impressions in a window; `/matching` shows 124 at position 9.1 against a baseline of 4.3 |
| **#1074 at risk of the same fate** (carried from 2026-11-17) | 59 dated `/panchang/` URLs, 101 impressions, 2 clicks in this window, against a floor of 150 |
| **#1067's baseline was wrong** | The issue stated `dasha_deep_dive_viewed` = 0; this window's export reads **2** |
| **No GA4/GSC ship is a clear HIT yet** | Every ship with a traffic thesis is either not clean, unscoreable at traffic, or a MISS / not-attributable above. The site's growth in section 1 is real and cannot be credited to any scored ship |

## 5. Funnel

`ga4-events.json`, 10-20 → 11-16, event counts (events, not sessions or users; no per-form split):

| event | count |
|---|---:|
| page_view | 1,355 |
| user_identified | 799 |
| feature_view | 782 |
| session_start | 777 |
| first_visit | 640 |
| user_engagement | 323 |
| scroll | 197 |
| form_start | 137 |
| ask_answered | 130 |
| kundli_generated | 52 |
| cta_click | 17 |
| click | 4 |
| view_search_results | 3 |
| dasha_deep_dive_viewed | 2 |
| feedback_sent | 2 |
| form_submit | 1 |
| subscribe_completed | 1 |

- `cta_click`: 17 events in about 14 days of history. **8 of 17 carry `(not set)` for both paths**; the readable 9: `career-during-sade-sati` → `/` (2), `sade-sati` → `/kundli` (2), `krittika-nakshatra` → `/` (1), `kaal-sarp-dosh` → `/kaal-sarp-check` (1), `name-numerology-explained` → `/numerology` (1), `rahu-mahadasha-ketu-antardasha` → `/dasha` (1), `saturn-in-10th-house-career` → `/kundli` (1). Partial history.
- **No step-through rate can be computed.** `form_start` (137) and `kundli_generated` (52) are totals across several forms, and `form_submit` = 1 reads as an instrumentation gap. #1070 is open; completion events shipped 2026-11-17/18 (#1068, #1217, #1226, #1229) and are outside this window. `kundli_generated` and `ask_answered` counted re-renders until PR #1157 (2026-11-17), so both are inflated for this whole window.
- **A readable ratio:** `session_start` 777 to `feature_view` 782 is about 1:1. Landing mix (GA4, folded): `/learn/*` 508 articles + 5 index of 776 (66%); `/` 69; `/muhurat/*` 46; `/numerology` 23; `/kundli` 19; `/matching` 18; `/admin/*` 17; `(not set)` 17.
- Sessions landing on a core tool page: kundli 19 + matching 18 + numerology 23 + ask 1 = 61 of 776 = 7.9%. The traffic lands on articles and the tool funnels start from there; `cta_click` is the only measure of that step and it holds 17 events (9 readable).

## 6. Where time is spent (lever 2)

`verify-first.json` (GA4 `engagedSessions`, 10-20 → 11-16) with GSC joined:

| page | sessions | engaged | engaged rate | avg engagement | GSC impressions / clicks / position |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 81 | 49 | 60% | 140 s | 3,913 / 63 / 6.4 |
| / | 69 | 44 | 64% | 231 s | 207 / 9 / 5.7 |
| /muhurat/griha-pravesh | 31 | 30 | **97%** | 92 s | 384 / 21 / 6.2 |
| /learn/gochar-2026-planetary-transits | 42 | 17 | **40%** | **29 s** | 2,512 / 24 / 5.1 |
| /learn/sade-sati | 19 | 15 | 79% | 278 s | 2,133 / 16 / 6.6 |
| /learn/rahu-mahadasha-career-problems | 23 | 14 | 61% | 280 s | 1,044 / 21 / 5.8 |
| /learn/career-during-sade-sati | 26 | 12 | 46% | 207 s | 1,239 / 22 / 5.4 |
| /learn/10th-lord-in-6th-house-career | 25 | 12 | 48% | 100 s | 762 / 20 / 6.7 |
| /learn/jupiter-in-10th-house-career | 24 | 11 | 46% | 74 s | 1,940 / 18 / 7.1 |
| /learn/7th-lord-placement-marriage-guide | 27 | 11 | 41% | 57 s | 1,509 / 14 / 7.2 |

- Longest holds (`ga4.json`, folded landings): `saturn-in-10th-house-career` 304 s (12 sessions), `mercury-remedies` 286 s (8), `rahu-mahadasha-career-problems` 280 s, `sade-sati` 278 s, `debilitated-sun-career` 254 s (21 sessions, 7 engaged), `/` 231 s.
- **Weakest holds on pages with real search traffic:** `gochar-2026-planetary-transits` (42 sessions, 40% engaged, 29 s, 27 organic) — the most-improved ranking of any page (10 → 2,512 impressions) with the shortest time on page of the ten; `chronic-health-issues-kundli` (18 sessions, 4 engaged, 9 s average; its 14 organic sessions are 3 engaged) at position 4.9; `panch-mahapurush-yoga` (20 sessions, 38 s). The window cannot separate gochar-2026 before and after #1079 / #1100 (closed 2026-11-15 and 11-16); I did not check their deploy times.
- `/muhurat/griha-pravesh` remains the best tool-like landing: 31 sessions, all Organic Search, 97% engaged, 5.4% CTR (21 clicks on 384 impressions).
- **Tool funnels visible in GA4:** `/kundli` 19 sessions, 7 engaged, 50 s; `/matching` 18 sessions, 4 engaged, 68 s; `/numerology` 23 sessions, 8 engaged, 85 s. Most arrive Direct (kundli 15 of 19, matching 13 of 18, numerology 11 of 23), so these are not search visitors.
- Per-section engagement or scroll depth is not exported.

## 7. Errors (lever 3)

| source | window | reading |
|---|---|---|
| `llm-usage.json` | 7 days to 2026-11-19 02:13Z | 167 calls, 132 cache hits (**79%**), 35 misses. Input tokens 118,234, output 23,744. Peak day by `peak_day_tokens`: 2026-11-13, 6,849; by `peak_day_measured_tokens`: **2026-11-18, 43,421** (two measures in one file; the second is a new peak day against the 2026-11-18 report's 32,768 on 11-13) |
| route detail | same | `natal` 114 calls (104 hits, 91%; 6,548 input tokens per call over 10 measured calls); `rashifal` 28 calls, 28 hits, tokens not recorded; `ask` 20 calls, 0 hits, 2,161 tokens per call; `today` 2; `monthly` 2; `dasha_deep_dive` 1 |
| errors or fallbacks per route | – | **not in the file**: no error or fallback key. Not measured. #1208 is open (filed 2026-11-18), no change yet |
| `verify-production.yml`, last 60 runs (2026-11-15T18:33Z → 2026-11-19T01:28Z) | – | 51 success, 5 cancelled, **4 failure**. The four are the same as in the 2026-11-18 report: 2026-11-16 03:17Z (dispatch), 2026-11-17 08:10Z (dispatch), 13:27Z and 18:12Z (push). **No failure since 2026-11-17T18:12Z.** I opened one (run 44145312520, 11-17 18:12Z): the failing step is "Wait for the deploy". The other three I did not open this run; the 11-18 report says the same step (carried, not re-read) |
| open issues on a user-facing route error | – | none among the 80 open-issue titles I read. #925 (peak day vs Groq daily budget) and #1207 (queue) are open and are not route errors |

- `ask` runs 20 calls with a 0% hit rate, expected for personal questions: 43,221 input tokens in 7 days.
- **Peak day 2026-11-18 at 43,421 measured tokens** is the largest figure in the file. The file does not say which route; I cannot attribute it. #925 covers the budget question.
- **Gap, still open:** errors per route cannot be read (#1208).

## 8. Search demand (lever 4)

`gsc-trend-query.json`, **14% of impressions, partial**; 965 query rows, 4,167 impressions, 43 clicks. Themes by regex on the query text (overlapping, not additive), with the existing page named:

| theme | query rows | impressions | clicks | weighted position | existing page |
|---|---:|---:|---:|---:|---|
| Rahu–Ketu dasha | 47 | 1,009 | 22 | 7.3 | `/learn/rahu-mahadasha-ketu-antardasha/` (ranks, 63 clicks on the page overall) |
| sun debilitated | 33 | 1,022 | 1 | 7.4 | `/learn/debilitated-sun-career/`. #835 shipped 2026-11-13 |
| 10th house / 10th lord | 84 | 661 | 4 | 10.2 | `/learn/jupiter-in-10th-house-career/`, `10th-lord-in-6th-house-career`, `saturn-in-10th-house-career`, `sun-in-10th-house-career`. #1073 shipped 2026-11-16 |
| jupiter / guru | 71 | 463 | 1 | 9.6 | the same Jupiter pages and `guru-jupiter-in-vedic-astrology` |
| 7th house / marriage | 62 | 208 | 2 | 9.3 | `planets-in-7th-house-marriage`, `7th-lord-placement-marriage-guide` |
| manglik / mars | 39 | 82 | 1 | 10.9 | `/learn/manglik-dosh/`, `mangal-mars-in-vedic-astrology` |
| sade sati | 29 | 59 | 0 | 8.4 | `/learn/sade-sati/` (the page has 2,133 impressions; the 14% view holds 59) |
| gochar / transit | 24 | 54 | 0 | 9.1 | `/learn/gochar-2026-planetary-transits/`, `gochar-2027-planetary-transits` |
| kundli | 8 | 33 | 0 | 15.5 | `/kundli` |
| muhurat | 15 | 29 | 1 | 10.3 | `/muhurat/*`, the `/learn` muhurat guides |
| numerology | 2 | 20 | 2 | 6.1 | `/numerology`, `name-numerology-explained` |
| panchang | 8 | 15 | 1 | 16.9 | `/panchang`, the dated `/panchang/<date>` pages |
| rashifal / horoscope | 10 | 11 | 0 | 77.6 | `/rashifal` (154 impressions at 7.7 at page level) |
| brand (`bhagya`, `shubh`) | 13 | 67 | 4 | 7.6 | home (207 impressions, 9 clicks, position 5.7) |

- **At positions 11–20 with ≥ 15 impressions:** `jupiter in 10th house` (112 impressions, position 11.1) and `mangal dosha cancellation` (15, 16.5). Both have an existing page; no new page is indicated.
- **Brand queries:** `bhagya chart` 23 impressions, 3 clicks, position 6.0; `bhagya kundali astrology` 15 (position 6.3); `bhagya.com` 12 (3.8); `shubhagya` 2 (position 1.5). Demand for the name is mostly typed as "bhagya", not "shubhagya"; I cannot see which page a "bhagya chart" click lands on.
- **Time-bound queries in the 14% view:** dated panchang queries ("2 december 2026 panchang / hindu panchang / rahu kaal / nakshatra", "8 december 2026 tithi") are 8 impressions at positions 7.7–74, against 59 dated `/panchang/<date>` URLs holding 101 impressions and 2 clicks in total. Diwali muhurat queries (4 variants, 1–27 impressions each, positions 10–27) land on `/learn/diwali-muhurat-2026` (75 impressions, position 11.1), a past event as of 11-08. No query mentions Devuthani, Tulsi Vivah, Sankranti or Pongal.
- **Queries with no page:** none identified in the 14% view. "no page" cannot be tested for the other 86%.

## 9. Content opportunities — time-bound demand (lever 5)

Dates are read from `src/astro_ai/festivals.py` by `festivals_for_date()` for 2026-11-19 → 2027-01-27, not from memory.

| date | festival in the registry | existing page | GSC in this window |
|---|---|---|---|
| 2026-11-20 (**tomorrow**) | Devuthani Ekadashi (Prabodhini); registry note: Chaturmas ends and the wedding season reopens | registry entry only; `/festivals` hub (293 impressions, position 36.0, 0 clicks); `vivah-muhurat-2027` (42 impressions, position 9.2, 0 clicks) and `/muhurat/vivah` (23 impressions, position 5.3, 1 click) hold the wedding-season demand. I found no `/learn` article on Devuthani | no query in the 14% view |
| 2026-11-21 | Tulsi Vivah | same | none |
| 2026-11-22 → 2027-01-14 | **no entry in the registry** | – | – |
| 2027-01-15 | Makar Sankranti and Pongal | registry entries; `routes/panchang.py` handles the shared date; I found no `/learn` article on either | none |

- **The registry holds nothing between 2026-11-22 and 2027-01-14** (54 days). I name no December festival because the file does not carry one. Whether that is a gap in the registry or in its scope is not determined here.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` (2,512 impressions, position 5.1). Its 2027 sibling was deployed 2026-11-17 (#1071), **after this window ended**, so it holds no GSC or GA4 row by construction. `diwali-muhurat-2026` (75 impressions, 11.1) and `karva-chauth-2026` are past events. `griha-pravesh-muhurat-2026-2027` has 0 GSC impressions against 14 GA4 sessions. `vivah-muhurat-2027` 42 impressions at 9.2, 0 clicks.
- **Devuthani Ekadashi is one day away.** I have no index-status export, so I cannot say how fast a new page would be indexed on this site.

## 10. Index status (lever 6)

`measurements/index-status.json` does not exist. #1065 is open. **Not measured.** The measurement that settles it is the URL Inspection API sweep #1065 describes, over the 141 pages with impressions and the sitemap URLs with none. Cases it would settle: `griha-pravesh-muhurat-2026-2027` (0 GSC impressions, 14 GA4 sessions), `ketu-in-vedic-astrology` (62 → 0 impressions), `gochar-2027-planetary-transits` (no row; deployed after the window).

## 11. Measurement gaps (lever 7)

Compared against `measurements/2026-11-16.md`, `2026-11-17.md` and `2026-11-18.md` (the latest file is the 11-18 run) plus this run.

| gap | in each of the last three reports + this run? | open issue | action |
|---|---|---|---|
| No GA4 previous-window export, so no GA4 period-on-period | yes | #1115 (flag), #1205 (workflow call) | none; still open |
| `--page-daily` not called by `agent-measure`; cannot split a page at its deploy date | yes | #953 | none |
| `git log origin/main --since` unusable (shallow checkout) | yes | #666, #974 | none |
| Per-form funnel step-through | yes | #1070 | none; completion events shipped 11-17/18 |
| Index status | yes | #1065 | none |
| Errors per route in `llm-usage.json` | yes | #1208 | filed 2026-11-18; still open |
| Source of elevated days under the anomaly bar (10-23, 11-09, 11-10, 11-12, 11-14) | **yes (11-16, 11-17, 11-18, this run)** | none | **filed #1236** |
| GA4 `page_location` export (the metric for #1066 and #1093) | **yes (11-17, 11-18, this run)** | none | **filed #1237** |
| GSC impressions for pages GA4 shows organic sessions on (`griha-pravesh-muhurat-2026-2027`: 0 vs 14) | yes (11-16, 11-17, 11-18, this run) | #953 holds the GSC half | commented on #953; no new issue |
| Server-log count for #1068's metric | 11-18 and this run | none | not filed: two of three. If it appears again, file it |
| Source of the zero-engagement Direct sessions on `/learn/financial-struggles` (9) and `/r/zzzzzz` (4) | first appearance | none | not filed |
| Which route spent the 43,421-token peak day (2026-11-18) | first appearance | #925 covers the budget | not filed |

## 12. What I could not determine, and the measurement that settles each

| gap | single measurement |
|---|---|
| Whether sessions and users moved with GSC | the GA4 previous-window export (#1115 / #1205) |
| Whether `/matching` lost position before or after the 2026-11-03 title change | `fetch_gsc.py --by date --page-daily --pages /matching --days 56` (#953) |
| Why `griha-pravesh-muhurat-2026-2027` has 0 GSC impressions and 14 GA4 sessions | the same `--page-daily` export plus GA4 `sessionSource` for that landing |
| Whether the impressions rise is the work or the festival season | the same window a year earlier; not available before 2027-11 |
| Which ships landed in the window | a full-depth checkout (#974) |
| Query-level top-5 progress on 86% of impressions | not recoverable; Google withholds the queries |
| Source of 10-23, 11-09, 11-10, 11-12 and 11-14 | a source × landing × tech breakdown for those dates (#1236) |
| Why `gochar-2026-planetary-transits` and `chronic-health-issues-kundli` hold readers 29 s and 9 s | a per-section scroll or engagement read on those pages; no export has it |
| Errors and fallbacks per LLM route; which route spent 2026-11-18's 43,421 tokens | #1208, plus a per-route daily token series |
| Whether #1066 and #1093 worked | a `page_location` export (#1237) |
| Whether #1068's completion events now match the server | the server-log count of `POST /reading` 303 |
| Whether the 9 zero-engagement Direct sessions on `financial-struggles` are automated | GA4 `browser × deviceCategory × country` for that landing |
| Index status | #1065's export |

## 13. Issues filed

| # | title | why |
|---|---|---|
| **#1236** | analytics: anomaly breakdown skips every day under the spike bar — 5 elevated days in 28 have no named source (4 reports in a row) | lever 7 rule: the gap is in four consecutive reports and no open issue covers it. The edit is a "watch" tier at median + 10 in `fetch_ga4.py anomalies()` |
| **#1237** | analytics: no export carries GA4 page_location — #1066 and #1093 cannot be scored (3 reports in a row) | lever 7 rule: the gap is in 11-17, 11-18 and this run. Both issues have timers due 2026-12-16 |

Seven comments were posted on issues (section 4): #1217, #1226, #1229, #1178, #1080, #1083 and #953. `/tmp/analyst-timers.txt` holds 23 timer lines for the next step to set with `scripts/timers.py set --from-file`.
