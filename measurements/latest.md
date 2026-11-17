# Analyst report — run 2026-11-17

**Window for every number below: 2026-10-18 → 2026-11-14** (28 days; the last 3 days are excluded because GSC lags 2–3 days and GA4 24–48h).
**Previous window** where a delta is quoted: **2026-09-20 → 2026-10-17** (`gsc-trend-*.json`). **GA4 has no previous-window export, so no GA4 period-on-period number appears anywhere in this report** (#1115 is open).
Every figure was read from `/tmp/*.json` or `gh` this run. Quotes from earlier reports or issue comments are labelled as such.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | note |
|---|---|---|---:|---|---|
| `gsc-band.json` | page, position 6–20 | 10-18 → 11-14 | 100% of 27,771 property impressions (rows sum 27,852) | no | `emitted_*`: 104 pages, 21,113 impressions = 76% |
| `gsc-all.json` | page | same | 100% | no | 142 pages |
| `gsc-daily.json` | date | same | 100% | no | 28 days, 27,771 impressions, 375 clicks |
| `gsc-trend-page.json` | page, now vs previous | 10-18 → 11-14 vs 09-20 → 10-17 | 100% | – | 142 pages now, 126 previous. Previous rows sum to 11,348 impressions and 113 clicks |
| `gsc-trend-query.json` | query, now vs previous | same | **14%** of 27,771 | – | partial view (Google withholds rare queries). 801 keys now, 207 previous. No site-wide conclusion can come from it |
| `ga4.json` | landing × channel | same | 100% of 740 sessions | no | 152 rows, 99 raw landings, 92 after folding query strings and trailing slashes |
| `ga4-daily.json` | date | same | 28 of 28 days with traffic | – | daily sessions sum to 742 against the property total of 740; I use 740 for totals |
| `ga4-events.json` | event | same | 17 event names, 5,022 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688), so it covers about 12 of the 28 days |
| `ga4-anomalies.json` | spike days | same | rule: users ≥ max(2×median, median+10, 15) | – | 1 spike day flagged (11-06) |
| `gsc-discover.json` | Discover | same | – | – | **0 clicks and 0 impressions on all 28 days** |
| `verify-first.json` | busiest pages by engaged sessions | same | – | – | 10 rows |
| `measure/llm-usage.json` | app LLM calls | **7 days to 2026-11-17 03:22Z** | – | – | a different window from everything else; calls, hits and tokens only |
| `index-status.json` | – | – | **absent** | – | not measured (#1065 open) |

## 1. Growth

| metric | 10-18 → 11-14 | 09-20 → 10-17 | change |
|---|---:|---:|---:|
| GSC impressions (page-row sum) | 27,852 | 11,348 | **+145%** |
| GSC clicks (page-row sum) | 375 | 113 | **+232%** |
| CTR | 1.35% (375 / 27,771 property) | 1.00% (113 / 11,348 rows) | +0.35 pt |
| pages with any impression | 142 | 126 | +16 |
| query keys visible (14% view) | 801 | 207 | +594 |
| GA4 sessions | 740 | **not measured** | – |
| GA4 new users, sum of daily rows | 603 | **not measured** | – |

Inside this window:

| | first 14 days (10-18 → 10-31) | last 14 days (11-01 → 11-14) | change |
|---|---:|---:|---:|
| GSC impressions | 10,727 | 17,044 | +59% |
| GSC clicks | 124 | 251 | +102% |
| GA4 sessions | 284 | 458 | +61% |
| GA4 sessions excluding the 11-06 spike day (59 sessions) | 284 | 399 | +40% |
| first 7 days vs last 7 days, GSC impressions / clicks | 3,680 / 41 | 9,115 / 150 | – |
| first 7 days vs last 7 days, GA4 sessions | 123 | 255 | – |

GA4 sessions by channel (coverage 100%):

| channel | sessions | share | engaged sessions |
|---|---:|---:|---:|
| Organic Search | 451 | 61% | 256 |
| Direct | 278 | 38% | 67 |
| AI Assistant | 9 | 1% | 5 |
| Unassigned | 2 | 0% | 1 |

**Which page groups drive the change** (GSC page mode, impressions / clicks, now vs previous):

| group | impressions now | impressions previous | clicks now | clicks previous |
|---|---:|---:|---:|---:|
| `/learn/<article>` (all) | 25,858 | 10,253 | 319 | 97 |
| `/muhurat/*` | 559 | 49 | 27 | 7 |
| `/numerology*` | 173 | 4 | 10 | 0 |
| `/rashifal/*` (English) | 210 | 86 | 0 | 0 |
| `/` | 190 | 105 | 9 | 5 |
| `/matching` | 116 | 324 | 3 | 0 |
| `/kundli*` | 94 | 49 | 4 | 3 |
| `/hi/*` (Hindi) | 76 | 0 | 0 | 0 |

- `/learn` articles are 93% of impressions and 85% of clicks. Of the +16,504 impression rise, the learn articles account for +15,605.
- Top risers (impressions now vs previous, position now vs previous): `rahu-mahadasha-ketu-antardasha` 3,986 vs 1,969 (6.4 vs 7.5); `gochar-2026-planetary-transits` **2,097 vs 12** (5.3 vs 6.8); `debilitated-sun-career` 2,740 vs 1,141 (6.6 vs 6.0); `jupiter-in-10th-house-career` 1,840 vs 371 (7.0 vs 6.8); `7th-lord-placement-marriage-guide` 1,512 vs 247 (7.2 vs 7.8); `sade-sati` 2,100 vs 1,051 (6.6 vs 6.2); `career-during-sade-sati` 1,165 vs 401 (5.4 vs 7.0).
- The rise is mostly more pages ranking, not a move in position. Daily average position in `gsc-daily.json` stays between 6.1 and 8.1 across the window.

**Seasonal or structural.** Diwali was 2026-11-08, inside the window. Daily impressions climbed from 462 (10-18) to about 1,050 by 10-27, before Diwali, and most top risers are not festival topics. That points at structural growth. `/muhurat/griha-pravesh` (and the 559 vs 49 `/muhurat` group) is the one group likely to follow the wedding and housewarming season. **Not determined:** there is no prior-year window, so the calendar effect cannot be separated.

**Spike days, each with its source** (`ga4-anomalies.json`, checked against GSC daily clicks and Discover):

| date | GA4 users / sessions | median users | source breakdown (from the file) | GSC clicks that day | Discover | read |
|---|---:|---:|---|---:|---:|---|
| **2026-11-06** | 57 / 59 | 22 | Top landing `/rashifal/aries`: 6 Direct sessions, 17% engaged, 3.5s. `/r/zzzzzz`: 3 Direct sessions, 5.7s. Organic: 4 sessions on `/learn/rahu-mahadasha-career-problems` at 224s. By browser and country: **19 of the 50 sessions the file broke down had zero engagement** (no browser name / desktop / US 10, Chrome desktop / US 6, Chrome mobile / US 3) | 17 (11-05: 17; 11-07: 12) | 0 | **Mixed, not growth.** About 38% of the sessions the file covered look automated; the other 31 look like ordinary readers (8 India Chrome mobile sessions engaged for 86s). Search clicks did not move that day |

- Three other days sit above the surrounding level without crossing the file's threshold: 10-23 (34 users / 34 sessions), 11-10 (40 / 43) and 11-14 (32 / 47). **Their sources are not determined**: only flagged days are broken down. 11-14 has 47 sessions from 32 users, the highest sessions-to-users ratio in the window (1.47); GSC clicks were 23, not unusual.
- Discover is zero on every day, so no day's traffic came from Discover.
- Where it matters I give the number with and without 11-06.

**Confounds for the site-level rise (named, not resolved):**
- Concurrent ships: `git log origin/main` is unusable here (shallow checkout, 1 commit; #666 and #974 track it). Read via `gh pr list` instead: **409 PRs merged in the window, 260 touching something other than `measurements/`, 162 touching `src/`**. The ones that touched a ranking surface in the last week of the window include #833 (griha-pravesh muhurat guide, 11-10), #888, #892 and #870 (`/matching` result page, 11-11/12), #940 (debilitated-sun lede and FAQ, 11-13), and on **11-14** a run of grounding edits to the pages that rank: #994 (Rahu–Ketu antardasha), #989 / #991 / #997 (planets in 7th), #979 / #981 (7th lord), #1015 / #1031 / #1035 (Jupiter in 10th), #1009 (debilitated-sun). With that many, no movement is attributable to one ship.
- Seasonality: above.
- Reachability: `verify-production.yml`, last 40 runs, **38 success, 1 failure, 1 in progress**. The failure was run 43797263108 on 2026-11-16 03:17Z (`workflow_dispatch`), step "Wait for the deploy": `/health` never reported `build_sha` b8ac181 within ~12 min (last seen 7a67ce4). That is a deploy-wait failure, not a failed assertion on a page. #341 (the 12-minute wait for a SHA that may never deploy) is open. A green run says the invariants held; it does not say every page rendered for every visitor.
- Measurement contamination: GA4 holds **17 sessions landing on `/admin/ops` and 18 on `(not set)`** (35 of 740, 4.7%). They are not visitors, or cannot be attributed. #735's fix (PR #877) merged 2026-11-11, so 24 of this window's 28 days (10-18 → 11-10) are before it. I cannot split by day from these files.
- Sample size: 740 sessions in 28 days. A day-to-day move of 5–10 sessions is noise.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page mode measures pages (a page's position is its average across queries). Query mode covers 14%.

**Band, page mode** (`emitted_*`, 76% of impressions): 104 pages, 21,113 impressions, 271 clicks, **CTR 1.28%** (impressions-weighted). 85 of the 104 pages are at position ≤ 10 (20,841 impressions). **68 of the 104 had zero clicks**, covering 1,407 impressions (6.7% of the band).

Top 10 by `band_opportunity` (page mode):

| # | page | impressions | clicks | CTR | avg position | previous impressions / position |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,986 | 67 | 1.68% | 6.4 | 1,969 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,740 | 17 | 0.62% | 6.6 | 1,141 / 6.0 |
| 3 | /learn/sade-sati/ | 2,100 | 14 | 0.67% | 6.6 | 1,051 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,840 | 18 | 0.98% | 7.0 | 371 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,512 | 15 | 0.99% | 7.2 | 247 / 7.8 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,149 | 11 | 0.96% | 6.6 | 547 / 5.9 |
| 7 | /learn/panch-mahapurush-yoga/ | 964 | 14 | 1.45% | 6.7 | 411 / 6.9 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 498 | 3 | 0.60% | 7.8 | not read |
| 9 | /learn/manglik-dosh/ | 506 | 4 | 0.79% | 6.6 | 469 / 7.4 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 715 | 20 | 2.80% | 6.6 | 186 / 7.0 |

The ten highest-impression pages overall (`gsc-all.json`) add `gochar-2026-planetary-transits` (2,097 impressions, 21 clicks, position 5.3), `career-during-sade-sati` (1,165, 22, 5.4) and `rahu-mahadasha-career-problems` (1,031, 21, 5.9). **0 of those ten are at average position ≤ 5.0.** Three are within 1 position of it (5.3, 5.4, 5.9). Pages at ≤ 5.0 with ≥ 50 impressions: `chronic-health-issues-kundli` (403 impressions, position 5.0, 9 clicks) and `2nd-lord-placement-wealth-guide` (75, 4.4).

**Top-5 test on queries** (`gsc-trend-query.json`, **14% of impressions, partial**). Ten highest-impression queries:

| query | impressions | previous | clicks | position | previous position |
|---|---:|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 433 | 265 | 14 | 6.8 | 9.7 |
| sun debilitated in which sign | 276 | 0 | 0 | 7.7 | – |
| sun is debilitated in which sign | 126 | 0 | 0 | 6.9 | – |
| jupiter in 10th house | 102 | 0 | 0 | 10.5 | – |
| 10th lord in 6th house | 90 | 0 | 2 | 8.5 | – |
| yes | 88 | 7 | 0 | 3.7 | 3.9 |
| sun debilitated sign | 77 | 2 | 0 | 6.1 | 3.0 |
| guru in 10th house | 71 | 0 | 0 | 8.8 | – |
| sun debilitated | 69 | 0 | 0 | 8.8 | – |
| rahu mahadasha and ketu antardasha | 67 | 48 | 0 | 7.2 | 9.4 |

- **1 of 10 is at position ≤ 5, and it is `yes` (3.7), a query nobody targets.** None of the nine real queries is in the top 5. The objective is unmet on the measured 14%; the other 86% cannot be read.
- The best mover is the head query: position 9.7 → 6.8 on 265 → 433 impressions, 14 clicks in this window. Its previous-window clicks are not in this extract, so I do not quote a click change.
- The "sun debilitated" family is new this window (32 query rows, 913 impressions, 0 clicks, weighted position 7.5) and is the family #835 targets. #835's change (PR #940) merged 2026-11-13, so only the last two days of this window carry it.

**CTR outliers.** Pages with ≥ 500 impressions, position ≤ 7.5 and CTR below the band's own 1.28%:

| page | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,740 | 17 | 0.62% | 6.6 |
| /learn/sade-sati/ | 2,100 | 14 | 0.67% | 6.6 |
| /learn/gochar-2026-planetary-transits/ | 2,097 | 21 | 1.00% | 5.3 |
| /learn/jupiter-in-10th-house-career/ | 1,840 | 18 | 0.98% | 7.0 |
| /learn/7th-lord-placement-marriage-guide/ | 1,512 | 15 | 0.99% | 7.2 |
| /learn/planets-in-7th-house-marriage/ | 1,149 | 11 | 0.96% | 6.6 |
| /learn/marriage-mahadasha-timing/ | 665 | 8 | 1.20% | 5.3 |
| /learn/manglik-dosh/ | 506 | 4 | 0.79% | 6.6 |
| **eight pages** | **12,609** | **108** | **0.86%** | |

At the band rate the eight would have taken about 162 clicks, a gap of **about 54 clicks per 28 days**. Same-position pages that beat the band: `10th-lord-in-6th-house-career` 2.80% at 6.6, `rahu-mahadasha-career-problems` 2.04% at 5.9, `muhurat/griha-pravesh` 5.4% (21 clicks of 388 impressions) at 6.2. Their query mix was not examined. This run holds no CTR-by-position curve for the site, so I do not size a gain from position.

## 3. Decay

| page | impressions now / previous | clicks now / previous | position now / previous | read |
|---|---|---|---|---|
| **/matching** | **116 / 324** (−64%) | 3 / 0 | **8.8 / 4.3** | the only material decay on a page that had ranked well. Tracked by #1076 and #508 |
| /learn/griha-pravesh-muhurat-2026-2027/ | 0 / 38 (`is_gone`) | 0 / 0 | – / 7.3 | GA4 shows 12 sessions on this landing in the same window (7 Organic Search, 4 Direct, 1 AI Assistant), so the page is reachable. GSC shows none. Not determined why |
| /learn/the-9-grahas-overview/ | 25 / 104 | 0 / 0 | 9.6 / 7.9 | small |
| /learn/ketu-in-vedic-astrology/ | 4 / 63 | 0 / 1 | 8.5 / 7.2 | small |
| /learn/mars-remedies/ | 80 / 122 | 1 / 1 | 6.8 / 6.5 | small |
| /festivals | 298 / 240 | 0 / 0 | 34.6 / 28.4 | position far outside the band |
| /learn/ashwini-nakshatra/ | 96 / 102 | – | 7.7 / 5.6 | position down 2.1 on flat impressions; small |

- **/matching:** position was 7.8 in the 11-14 report, 9.3 in the 11-16 report (both quoted from those reports) and is 8.8 here; the three windows overlap, so I do not read that as a recovery or a slide. The onset cannot be dated: #696 (title and meta, merged 2026-11-03) is inside this window, and so are #750, #769, #870, #888 and #892 on the same page. The fetch cannot split a page at a date (`--page-daily` exists; `agent-measure` does not call it, #953 open). I do not attribute the drop to the title or to anything else. GA4: 16 sessions (3 Organic Search, 12 Direct, 1 AI Assistant), 75% bounce, 1.69 pages/session.
- No other page with ≥ 100 impressions lost ≥ 1.0 position, apart from `ashwini-nakshatra` above (96 impressions).

## 4. Scores for closed issues carrying `thesis:` and `metric:`

Rule applied: score once, when the window is clean (the window starts on or after the deploy). Today − 31 days is 2026-10-17, and this window starts 2026-10-18. I read the existing comments on every issue first.

**Posted this run (six comments, each the first analyst note on its issue):**

| issue | deploy | what I posted |
|---|---|---|
| #1073 Jupiter-in-10th headings | PR #1126, 2026-11-16 06:26Z | pending, scoreable from 2026-12-17. Reference before the deploy: 52 jupiter+10th query rows, 395 impressions, 1 click, weighted position 9.2 (14% view) against the issue's baseline of 46 rows, 280 impressions, position 9.2 |
| #1074 dated `/panchang/` titles | PR #1130, 2026-11-16 11:26Z | pending, scoreable from 2026-12-17, **floor at risk**: dated URLs had 101 impressions and 2 clicks this window against a floor of 150 |
| #1075 Rahu–Ketu effects/remedies headings | PR #1122, 2026-11-16 04:15Z | pending, scoreable from 2026-12-17. Reference: 8 effects/remedies query rows, 116 impressions, 2 clicks, position 7.9 (a different row set from the issue's baseline, so not a before/after) |
| #1066 `city=` out of GA4 | PR #1091, 2026-11-15 11:05Z | pending, scoreable from 2026-12-16. The metric reads `page_location`, which no export carries; the loop reads landings only (0 landings with `city=`) |
| #1093 `email=`/`token=` out of GA4 | PR #1096, 2026-11-15 14:56Z | pending, scoreable from 2026-12-16. Same export gap; 0 landings with `email=` or `token=` |
| #843 per-word compounds on `/numerology` | PR #850, 2026-11-10 16:37Z | **unscoreable at this traffic**: the metric is a render count; `/numerology` had 23 sessions in the window. Scoring stops |

**Already scored or pending, nothing posted this run** (the verdict has not changed and the number has not moved past what the metric calls material):

| issue | deploy | clean? | last posted | this run | verdict |
|---|---|---|---|---|---|
| **#311** four-page title/meta CTR test | PR #334, 2026-10-13 | yes | MISS, 2026-11-13: 0.937% (53 / 5,658) | combined CTR **0.981%** (60 / 6,117) vs bar ≥ 1.5%. Impressions floor met. Position 6.6. Previous window 17 / 2,800 = 0.607% | **MISS, unchanged** (0.937 → 0.981%, not material) |
| **#276** /dasha CTA on the Rahu–Ketu article | PR #342, 2026-10-14 | yes | BAR MET, not attributable, 2026-11-14: 1.42 | Organic Search **65 sessions, 1.38 pages/session** (bar ≥ 1.20 on ≥ 20). All channels 76 sessions, 1.32 | **BAR MET, not attributable**, unchanged |
| **#329** Manglik checker link | PR #344, 2026-10-14 | yes | UNSCOREABLE 3 vs 10, 2026-11-14 | Organic Search **3** sessions, 1.00 pages/session. All channels 7 | unscoreable at this traffic; scoring stays stopped |
| #508 /matching title/meta | PR #696, 2026-11-03 | no | pending, scoreable from 2026-12-04 | not scored. The pass condition needs ≥ 1.0% CTR on **≥ 300 impressions**; this window holds 116 impressions at position 8.8 | pending; the floor looks unreachable at the current rate |
| #685 /learn/sade-sati title | PR #690, 2026-11-03 | no | pending, scoreable from 2026-12-04 | reference only: 2,100 impressions, 14 clicks, 0.67%, position 6.6. Mixed window, not a score | pending |
| #426 sade-sati date guard | PR #673, 2026-11-02 | no | pending, scoreable from 2026-12-03 | reference only: position 6.6 (guard: within ±1 of 6.2). Mixed window | pending |
| #553 panch-mahapurush link | PR #615, 2026-10-31 | no | pending, scoreable from 2026-12-01 | reference only: 13 Organic Search sessions at 1.00 pages/session. Not a score | pending |
| #518 learn → tool routes | last slice PR #754, 2026-11-06 | no | pending, scoreable from 2026-12-07 | not scored | pending |
| #835 debilitated-sun lede and FAQ | PR #940, 2026-11-13 | no | pending, scoreable from 2026-12-14 | not scored. The deploy is the last 2 days of this window | pending |
| #570 `cta_click` event | PR #688, 2026-11-03 | no | pending, scoreable from 2026-12-04 | `cta_click` read in section 5: 15 events | pending |
| #528 /ask `q=` out of GA4 | PR #801, 2026-11-09 | no | pending, scoreable from 2026-12-10 | reference only: **1 landing still carries `q=` (2 sessions)** in this window; the window holds 22 days before the deploy (10-18 → 11-08), so it is not a score | pending |
| #735 /admin out of GA4 | PR #877, 2026-11-11 | no | pending, scoreable from 2026-12-12 | reference only: 17 sessions on `/admin/ops` in this window, which holds 24 pre-fix days | pending |
| #272 band measurable | 2026-10-08 | yes | PASS on shape; query-level half NOT MET, 2026-11-05 | this run's exports do carry channel and page; the top-10 **query** ranking URL is still not exported | unchanged |
| #514, #523 rashifal | 2026-10-25 / 2026-11-01 | – | unscoreable at this traffic, 2026-11-09 | not re-scored (`/rashifal/*` English: 210 impressions, 0 clicks) | stopped |

Deploy dates and the "last posted" column come from earlier comments on those issues, not from this run's files. The "this run" column is read from this run's files.

### The misses, as plainly as the hits

| result | what it says |
|---|---|
| **#311 MISS** (0.981% vs ≥ 1.5%) | A title/meta rewrite on four band pages did not reach the bar. CTR on the four rose from 0.607% to 0.981%, but their impressions grew 2.2× (2,800 → 6,117) and `rahu-mahadasha-career-problems` moved from position 7.1 to 5.9, so the rise is not attributable to the titles. Three of the four are still below 1% (`debilitated-sun-career` 0.62%, `jupiter-in-10th-house-career` 0.98%, `manglik-dosh` 0.79%) at position 6.6–7.0. |
| **#329 unscoreable** (3 organic sessions vs floor 10) | The page ranks (506 impressions, position 6.6) but yields 3 organic sessions in 28 days, so a link on it cannot be measured at that traffic. |
| **#843 unscoreable** (23 `/numerology` sessions) | A correctness change on a low-traffic page; nothing in GA4 or GSC can score it. |
| **#276 bar met, not attributable** (1.38 vs ≥ 1.20) | The page also took #518's first-screen tool link and #830's link rewording in the same window, and the metric has no pre-deploy comparison. All other `/learn/*` organic landings combined: **285 sessions at 1.61 pages/session**, above this page's 1.38. Not credited to the CTA. |
| **#508 will probably not be scoreable as written** | It needs ≥ 300 impressions in a window; `/matching` shows 116, and its position is 8.8 against a baseline of 4.3. |
| **#1074 at risk of the same fate** | 101 dated-panchang impressions against a floor of 150, spread over about 60 URLs. |

## 5. Funnel

`ga4-events.json`, 10-18 → 11-14, event counts (events, not sessions or users; no per-form split):

| event | count |
|---|---:|
| page_view | 1,301 |
| user_identified | 763 |
| feature_view | 746 |
| session_start | 740 |
| first_visit | 603 |
| user_engagement | 314 |
| scroll | 195 |
| form_start | 145 |
| ask_answered | 133 |
| kundli_generated | 52 |
| cta_click | 15 |
| view_search_results | 5 |
| dasha_deep_dive_viewed | 2 |
| feedback_sent | 2 |
| form_submit | 1 |
| subscribe_completed | 1 |

- `cta_click`: 15 events in about 12 days of history. **8 of 15 carry `(not set)` for both paths**, so the split is readable for 7: `career-during-sade-sati` → `/` (2), `krittika-nakshatra` → `/` (1), `kaal-sarp-dosh` → `/kaal-sarp-check` (1), `name-numerology-explained` → `/numerology` (1), `rahu-mahadasha-ketu-antardasha` → `/dasha` (1), `saturn-in-10th-house-career` → `/kundli` (1). Partial history by the file's own note.
- **No step-through rate can be computed.** `form_start` (145) and `kundli_generated` (52) are totals across several forms. `form_submit` = 1 reads as an instrumentation gap. #1070 (instrument the core funnels) is open.
- Landing mix, GA4 folded landings: `/learn/*` 481 of 740 sessions (65%); `/` 69; `/numerology` 23; `/kundli` 18; `/matching` 16; admin 17; `(not set)` 18.

## 6. Where time is spent (lever 2)

Basis: GA4 `engagedSessions` and `engagement_seconds` (`verify-first.json`, `ga4.json`). Site-wide: 329 engaged sessions of 740 (44%); 80,805 engagement seconds, average 109s per session. Organic Search sessions engage at 57% (256 of 451); Direct at 24% (67 of 278).

| page | sessions | engaged | engaged rate | avg engagement (s) | GSC impressions / clicks / position |
|---|---:|---:|---:|---:|---|
| / | 69 | 47 | 68% | 251 | 191 / 9 / 5.7 |
| /learn/rahu-mahadasha-ketu-antardasha | 76 | 44 | 58% | 130 | 3,986 / 67 / 6.4 |
| /muhurat/griha-pravesh | 30 | 29 | 97% | 94 | 388 / 21 / 6.2 |
| /learn/gochar-2026-planetary-transits | 38 | 15 | 39% | **29** | 2,097 / 21 / 5.3 |
| /learn/sade-sati | 18 | 14 | 78% | 162 | 2,100 / 14 / 6.6 |
| /learn/rahu-mahadasha-career-problems | 22 | 14 | 64% | 292 | 1,031 / 21 / 5.9 |
| /learn/career-during-sade-sati | 26 | 13 | 50% | 217 | 1,165 / 22 / 5.4 |
| /learn/7th-lord-placement-marriage-guide | 28 | 12 | 43% | 59 | 1,512 / 15 / 7.2 |
| /learn/10th-lord-in-6th-house-career | 25 | 12 | 48% | 100 | 715 / 20 / 6.6 |
| /learn/jupiter-in-10th-house-career | 21 | 9 | 43% | 75 | 1,840 / 18 / 7.0 |

- **`gochar-2026-planetary-transits`** is the largest new landing (38 sessions: 24 Organic Search, 13 Direct, 1 AI Assistant; 61% bounce) with the shortest engagement of the ten: **29s average, 39% engaged**, at position 5.3. A page ranking this high where readers leave within 30 seconds is the page to look at first. This is the symptom; I do not know why.
- **`/muhurat/griha-pravesh`** is the best converter of organic traffic: 30 sessions, all Organic Search, 97% engaged, 3% bounce, and 5.4% CTR on 388 impressions.
- Longest article engagement: `rahu-mahadasha-career-problems` 292s, `debilitated-sun-career` 281s (20 sessions, 65% bounce), `saturn-in-10th-house-career` 314s (11 sessions), `mercury-remedies` 286s (8 sessions, 12% bounce).
- Tool funnels visible by landing (landings, not completions): `/numerology` 23 sessions (12 Organic Search), 65% bounce, 85s; `/kundli` 18 sessions, 61% bounce, 47s; `/matching` 16 sessions, 75% bounce, 76s.

## 7. Errors (lever 3)

| source | window | result |
|---|---|---|
| `llm-usage.json` | 7 days to 2026-11-17 03:22Z | 153 calls, 124 cache hits (**81%**), 29 misses. **The file carries no error or fallback counts, so errors per route are not measured.** |
| `verify-production.yml` | last 40 runs; newest 2026-11-17 03:24Z | **38 success, 1 failure, 1 in progress.** The failure (2026-11-16 03:17Z, `workflow_dispatch`) is a deploy-wait timeout: `/health` never reported `build_sha` b8ac181 within ~12 min. Tracked by #341 |
| user-facing errors in issues | – | #1087 (`/ask?q=` blank page) and #1088 (`/kundli` 503 when the LLM fails) are **both closed now**; the 11-16 report listed them open. I did not re-verify them against production |

LLM usage by route (7 days):

| route | calls | hit rate | input tokens | tokens per measured call |
|---|---:|---:|---:|---:|
| natal | 107 | 91% | 59,687 | 6,631 (9 measured) |
| rashifal | 28 | 92% | 119,593 | 4,429 (27 measured) |
| ask | 13 | **0%** | 29,515 | 2,270 |
| monthly | 2 | 0% | 4,218 | 2,109 |
| today | 1 | 0% | 1,881 | 1,881 |
| dasha_deep_dive | 1 | 0% | 1,492 | 1,492 |
| matching | 1 | 0% | 1,774 | 1,774 |

- Overall: 218,160 input and 32,187 output tokens in 7 days. Peak day by the logged field: 12,796 on 2026-11-11; peak day by measured tokens: **139,799 on 2026-11-11**, 70% of the ~200k TPD ceiling named in CLAUDE.md. The two fields disagree by 11×. #925 (peak day at 83% of the Groq daily budget) is open and covers this.
- `ask` has no cache by construction (13 calls, 0 hits); at 13 calls in 7 days it is not the budget's problem.
- The calls and the token counts do not describe the same population (`rashifal` shows 28 calls and 27 measured calls; `natal` 107 and 9). I report both and do not reconcile them.

## 8. Search demand (lever 4)

Page mode is complete; query mode is the 14% view. For each theme the existing page is named. Nothing here proposes a new page.

| demand | impressions, position (window) | existing page | open issue |
|---|---|---|---|
| "sun debilitated" family (32 query rows) | 913 impressions, weighted position 7.5, 0 clicks | `/learn/debilitated-sun-career` (2,740 impressions, CTR 0.62%) | #835 shipped 2026-11-13, not yet scoreable |
| "jupiter in 10th house", "guru in 10th house" | 102 at 10.5, 71 at 8.8, 0 clicks | `/learn/jupiter-in-10th-house-career` (1,840 impressions, CTR 0.98%) | #1073 shipped 2026-11-16, pending |
| "10th lord in 6th house" | 90 at 8.5, 2 clicks | `/learn/10th-lord-in-6th-house-career` (715, 2.80%) | none needed: it converts |
| "rahu mahadasha ketu antardasha" family | 433 at 6.8 (14 clicks), 67 at 7.2, 50 "rahu ketu antardasha" at 7.5 | `/learn/rahu-mahadasha-ketu-antardasha` | #1075 shipped 2026-11-16, pending |
| `/matching` | 116 impressions at 8.8 | `/matching` | #1076, #508 |
| `gochar-2026-planetary-transits` | 2,097 at 5.3, CTR 1.00%, 29s engagement | itself | – |
| "which mahadasha is best for career" | 28 at 9.2, 0 clicks | **not determined**: query mode names no page | none |
| `yes` | 88 at 3.7, 0 clicks | **unknown** | not worth action: a one-word query |

- The query view cannot say which page serves which query. Attribution above is by topic, not measured.
- Hindi rashifal pages show impressions for the first time (`/hi/*`: 76 impressions, 0 clicks, 0 the window before).
- I found no query with real demand and no page in the 14% view. 86% of impressions are not readable by query, so that is "none seen", not "none exist".

## 9. Content opportunities — time-bound demand (lever 5)

Dates read from `src/astro_ai/festival_registry.py` this run (`DATA_YEARS` 2026–2028), via `upcoming()` from 2026-11-17. `learn_article_for()` is the registry's own test of whether an article exists.

| date | event | existing page | read |
|---|---|---|---|
| **2026-11-20** (3 days) | Devuthani Ekadashi (Prabodhini) | `/festivals`; `learn_article_for` returns **None**; `vivah-muhurat-2027` covers wedding timing | no dedicated learn article |
| **2026-11-21** (4 days) | Tulsi Vivah | `/festivals`; `learn_article_for` returns **None** | no dedicated learn article |
| 2027-01-15 (59 days) | Makar Sankranti; Pongal (Thai Pongal) | `/festivals`; `learn_article_for` returns **None** for both | just past the 8-week horizon |
| year ending | slugs carrying the year: `gochar-2026-planetary-transits` (2,097 impressions at 5.3), `diwali-muhurat-2026`, `karva-chauth-2026`, `griha-pravesh-muhurat-2026-2027` | themselves | the highest-ranking one is `gochar-2026` |
| year starting | `vivah-muhurat-2027` | exists | in place before the season |

- The registry returns no other festival between 2026-11-22 and 2027-01-14. I do not know whether that is complete; I did not check the registry's coverage rule. **A date is stated only if the registry holds it.**
- Of the 76 articles in `templates/learn/`, only `diwali-muhurat-2026` and `karva-chauth-2026` carry a festival slug.
- Cannibalisation rule: new pages go through `/learn`, after checking what already ranks. `/festivals` sits at position 34.6 on 298 impressions, so it is not a ranking page to protect.

## 10. Index status (lever 6)

`measurements/index-status.json` does not exist. #1065 (track index status per sitemap URL) is open. **Not measured.** The measurement that settles it is the URL Inspection API sweep #1065 describes, restricted to the 142 pages with impressions plus the sitemap URLs with none.

## 11. Measurement gaps (lever 7)

I read `measurements/2026-11-14.md`, `2026-11-15.md` and `2026-11-16.md` for repeats.

| gap | in each of the last three reports? | open issue | action |
|---|---|---|---|
| No GA4 previous-window export, so no GA4 period-on-period | yes (the 11-16 report filed #1115 after three in a row) | #1115 | none; still open |
| `--page-daily` not called by `agent-measure`; cannot split a page at its deploy date | yes | #953 | none |
| `git log origin/main --since` unusable (shallow checkout) | yes | #666, #974 | none |
| Per-form funnel step-through | yes | #1070 | none |
| Index status | named in the 11-16 report only | #1065 | none |
| Errors per route in `llm-usage.json` | **in the 11-16 report and this one; not in 11-14 or 11-15** | none | **not filed: two of three.** If the next report carries it and no issue exists by then, file it |
| GA4 `page_location` export (the metric for #1066 and #1093) | first appearance | none | not filed: first appearance. A new gap this run |
| Source of the unflagged high days 10-23, 11-10, 11-14 | first appearance | none | not filed |
| Admin and `(not set)` sessions before the fix (35 of 740) | yes | #735 closed | not filed: the first window that starts after the fix (2026-11-12) closes 2026-12-09 |

## 12. What I could not determine, and the measurement that settles each

| gap | single measurement |
|---|---|
| Whether sessions and users moved with GSC | the GA4 previous-window export (#1115) |
| Whether `/matching` lost position before or after the 2026-11-03 title change | `fetch_gsc.py --by date --page-daily --pages /matching --days 56` (#953 wires it into `agent-measure`) |
| Why `griha-pravesh-muhurat-2026-2027` shows no GSC impressions but 12 GA4 sessions | the same `--page-daily` export on both griha-pravesh URLs, plus GA4 `sessionSource` for that landing |
| Whether the rise is work or Diwali | the same window a year earlier; not available before 2027-11 |
| Query-level top-5 progress on 86% of impressions | not recoverable; Google withholds the queries |
| Source of 10-23, 11-10 and 11-14 | a GA4 source × landing breakdown for those three dates |
| Why `gochar-2026-planetary-transits` holds readers 29s | a per-section scroll or engagement read on that page; no export has it |
| Errors per LLM route | an `errors` / `fallbacks` count per route in `llm-usage.json` |
| Whether #1066 and #1093 worked | a GA4 Pages-and-screens export of `page_location` filtered on the query string |
| Index status | #1065's export |

## 13. Issues filed

None this run. Every finding that needs action already has an open issue (#1076 `/matching`, #1115 GA4 prior window, #953, #1065, #1070, #925, #341), and the one new gap (`page_location`) is a first appearance. Six comments were posted, listed in section 4.
