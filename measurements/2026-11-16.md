# Analyst report — run 2026-11-16

**Window for every number below: 2026-10-17 → 2026-11-13 (28 days; the last 3 days are excluded because GSC lags 2–3 days and GA4 24–48h).**
Prior window where a delta is quoted: **2026-09-19 → 2026-10-16** (`gsc-trend-*.json`). **GA4 has no prior-window export, so no GA4 delta appears anywhere in this report** (filed as #1115).
All figures were read from `/tmp/*.json` this run, or from `gh` this run. Issue comments are labelled as such.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | note |
|---|---|---|---:|---|---|
| `gsc-band.json` | page, position 6–20 | 10-17 → 11-13 | 100% of 26,809 property impressions (rows sum 26,884) | no | `emitted_*`: 104 pages, 20,499 impressions = 76% |
| `gsc-all.json` | page | same | 100% | no | 142 pages |
| `gsc-daily.json` | date | same | 100% | no | 28 days, 26,809 impressions, 357 clicks |
| `gsc-trend-page.json` | page, now vs prior | 10-17 → 11-13 vs 09-19 → 10-16 | 100% | – | 142 pages now, 128 prior. Prior rows sum to 11,178 impressions |
| `gsc-trend-query.json` | query, now vs prior | same | **14%** of 26,809 | – | partial view: Google withholds rare queries. 757 keys now vs 206 prior. No site-wide conclusion can be drawn from it |
| `ga4.json` | landing × channel | 10-17 → 11-13 | 100% of 711 sessions (rows sum 710) | no | 153 rows, 100 raw landings, 93 after folding query strings and trailing slashes |
| `ga4-daily.json` | date | same | – | – | 28 of 28 days have traffic |
| `ga4-events.json` | event | same | 17 event names, 4,793 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688), so about 10 of the 28 days |
| `ga4-anomalies.json` | spike days | same | rule: users ≥ max(2×median, median+10, 15) | – | 1 spike day flagged (11-06) |
| `gsc-discover.json` | Discover | same | – | – | **0 clicks, 0 impressions on all 28 days** |
| `verify-first.json` | busiest pages by engaged sessions | same | – | – | 10 rows |
| `measure/llm-usage.json` | app LLM calls | **7 days to 2026-11-16 00:40Z** | – | – | a different window from everything else; calls, hits and tokens only |
| `index-status.json` | – | – | **absent** (#1065 open) | – | not measured |

Page-mode GSC rows overcount the property total by 0.3% (26,884 vs 26,809). Site-level CTR below uses the property totals. GA4 sessions are summed across channel rows per folded landing.

## 1. Growth — users, sessions, impressions, clicks

| metric | 10-17 → 11-13 | 09-19 → 10-16 | change |
|---|---:|---:|---:|
| GSC impressions (page-row sum) | 26,884 | 11,178 | **+140%** |
| GSC clicks | 357 | 109 | **+228%** |
| CTR | 1.33% (357 / 26,809 property) | 0.98% (109 / 11,178 rows) | +0.35 pt |
| pages with any impression | 142 | 128 | +14 |
| query keys visible (14% view) | 757 | 206 | +551 |
| GA4 sessions | 711 | **not measured** | – |
| GA4 new users, sum of daily | 582 | **not measured** | – |

Inside this window, halves of 14 days:

| | 10-17 → 10-30 | 10-31 → 11-13 | change |
|---|---:|---:|---:|
| GSC impressions | 10,070 | 16,739 | +66% |
| GSC clicks | 116 | 241 | +108% |
| GA4 sessions | 280 | 432 | +54% |
| GA4 sessions excluding the 11-06 spike day (59 sessions) | 280 | 373 | +33% |
| GA4 daily active users, sum (a person can repeat across days) | 234 | 399 | not a user count |
| average GSC position, daily range | 6.6 – 8.1 | 6.1 – 7.4 | no clear shift |

GA4 sessions by channel, this window (coverage 100%):

| channel | sessions | share |
|---|---:|---:|
| Organic Search | 425 | 60% |
| Direct | 271 | 38% |
| AI Assistant | 10 | 1% |
| Unassigned | 4 | 1% |

**Which page groups drive the GSC change** (page mode, impressions / clicks, now vs prior):

| group | impressions now | impressions prior | clicks now | clicks prior |
|---|---:|---:|---:|---:|
| `/learn/<article>` (all) | 24,968 | 10,100 | 301 | 96 |
| `/muhurat/*` | 522 | 47 | 26 | 7 |
| `/numerology` | 165 | 5 | 9 | 0 |
| `/rashifal/*` (English) | 206 | 80 | 0 | 0 |
| `/` | 181 | 103 | 8 | 4 |
| `/matching` | 112 | 322 | 3 | 0 |
| `/kundli` | 89 | 45 | 5 | 2 |

- `/learn` articles are 93% of impressions and 84% of clicks. Of the 11,178 → 26,884 rise, the learn articles account for +14,868 of +15,706.
- Top risers by impressions: `rahu-mahadasha-ketu-antardasha` 1,943 → 3,910 (position 7.5 → 6.4), `gochar-2026-planetary-transits` **12 → 1,863** (position 6.8 → 5.5), `debilitated-sun-career` 1,099 → 2,684, `jupiter-in-10th-house-career` 372 → 1,791, `7th-lord-placement-marriage-guide` 231 → 1,457, `sade-sati` 1,017 → 2,078.
- The Hindi rashifal pages (`/hi/rashifal*`) show impressions for the first time (about 70 across seven URLs) and 0 clicks.

**Seasonal vs structural.** Diwali was 2026-11-08, inside the window. Most of the top risers are not festival topics (Rahu–Ketu dasha, debilitated Sun, Jupiter in the 10th, 7th lord), and the daily impressions climbed from 375 (10-17) to 1,049 (10-29), before Diwali. That points at more pages ranking, not a festival bump. `/muhurat/griha-pravesh` (30 → 351 impressions) is the one group likely to follow the wedding and housewarming season. **Not determined**: there is no prior-year window, so the calendar effect cannot be separated.

**Spike days, each with its source** (`ga4-anomalies.json`, checked against GSC daily clicks and Discover):

| date | GA4 active users / sessions | median users | source breakdown | GSC clicks that day | Discover | read |
|---|---:|---:|---|---:|---:|---|
| **2026-11-06** | 57 / 59 | 21 | Top landing `/rashifal/aries`, 6 Direct sessions, 17% engaged, 3.5s. `/r/zzzzzz`: 3 Direct sessions at 5.7s. Organic: 4 sessions on `/learn/rahu-mahadasha-career-problems` at 224s | 17 (11-05: 17; 11-07: 12) | 0 | **Mixed, not growth.** Of the top 10 browser/country rows (50 of 59 sessions), 3 rows are zero-engagement US sessions: desktop with no browser name 10, Chrome desktop 6, Chrome mobile 3. That is **19 of 59 sessions (32%) with no engagement at all**. The file's own explanation says "looks like real readers" because 8 India Chrome mobile sessions engaged for 86s; both are true of different slices. Search clicks did not move that day. I treat the 19 as automated or unattributable, and the other 40 as ordinary traffic |

- 2026-10-23 had 34 users and 34 sessions against a median of 21, below the file's threshold of 42 (this day is not flagged), with GSC at 7 clicks. Its source is **not determined**: it was not broken down.
- Discover is zero on every day, so no day's traffic came from Discover.
- Every increase quoted above is reported with and without 11-06 where it matters.

**Confounds for the site-level rise (named, not resolved):**
- Concurrent ships: `git log origin/main` is unusable (shallow checkout, 1 commit; #666 and #974 track it). Read via `gh pr list` instead: **257 non-measurement PRs merged in this window**. The ones that touch a ranking surface include #658 / #680 / #754 (learn → tool routing), #690 (sade-sati title), #696 (matching title), #796 (7 learn meta descriptions), #772 (numerology SEO strings), #673 (Saturn and Jupiter dates on sade-sati and gochar). With that many, no movement is attributable to one ship.
- Seasonality: above.
- Reachability: `verify-production.yml` shows 12 of 12 most recent runs `success` (2026-11-15 10:39Z to 21:35Z), and 40 of 40 in the last 40 runs. That says the invariants held. It does not say every page rendered for every visitor.
- Measurement contamination: GA4 holds **17 sessions landing on `/admin/ops`, 1 on `/admin/activity` and 20 on `(not set)`** (38 of 710, 5.4%). They are not visitors, or cannot be attributed. #735 is closed and its fix deployed 2026-11-11 per the earlier reports (not re-verified this run), so the window holds days before it. I cannot split by day from these files.
- Sample size: 711 sessions in 28 days. A day-to-day move of 5–10 sessions is noise.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**Band, page mode, 10-17 → 11-13** (`emitted_*`, 76% of impressions): 104 pages, 20,499 impressions, 261 clicks, **CTR 1.27%** (impressions-weighted). **67 of the 104 pages had zero clicks**, covering 1,407 impressions (6.9% of the band).

Top 10 by `band_opportunity`:

| # | page | impressions | clicks | CTR | avg position | prior impressions / position |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,910 | 62 | 1.59% | 6.4 | 1,943 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,684 | 17 | 0.63% | 6.6 | 1,099 / 6.0 |
| 3 | /learn/sade-sati/ | 2,078 | 14 | 0.67% | 6.6 | 1,017 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,791 | 16 | 0.89% | 7.0 | 372 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,457 | 15 | 1.03% | 7.3 | 231 / 7.8 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,090 | 10 | 0.92% | 6.5 | 550 / 5.9 |
| 7 | /learn/panch-mahapurush-yoga/ | 945 | 14 | 1.48% | 6.7 | 400 / 6.9 |
| 8 | /learn/manglik-dosh/ | 508 | 4 | 0.79% | 6.7 | 473 / 7.4 |
| 9 | /learn/mangal-mars-in-vedic-astrology/ | 477 | 3 | 0.63% | 7.7 | not read |
| 10 | /learn/10th-lord-in-6th-house-career/ | 702 | 20 | 2.85% | 6.6 | 186 / 7.0 |

The ten are 15,642 impressions (76% of the band's emitted impressions) and 175 clicks. All ten sit at average position 6.4–7.7. **None is at ≤ 5.0.** The ten highest-impression pages overall (`gsc-all.json`) also have none at ≤ 5.0. Pages at ≤ 5 with ≥ 50 impressions: `chronic-health-issues-kundli` (382 impressions, position 5.0, CTR 2.36%) and `2nd-lord-placement-wealth-guide` (75, 4.5).

**Top-5 test on queries** (`gsc-trend-query.json`, **14% of impressions, partial**). Ten highest-impression queries:

| query | impressions | prior | clicks | position | prior position |
|---|---:|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 418 | 265 | 13 | 7.0 | 9.6 |
| sun debilitated in which sign | 262 | 0 | 0 | 7.9 | – |
| sun is debilitated in which sign | 120 | 0 | 0 | 7.1 | – |
| jupiter in 10th house | 98 | 0 | 0 | 10.3 | – |
| 10th lord in 6th house | 90 | 0 | 2 | 8.5 | – |
| yes | 76 | 7 | 0 | 3.5 | 3.9 |
| sun debilitated sign | 75 | 2 | 0 | 6.2 | 3.0 |
| guru in 10th house | 71 | 0 | 0 | 8.8 | – |
| sun debilitated | 67 | 0 | 0 | 8.8 | – |
| rahu mahadasha and ketu antardasha | 67 | 46 | 0 | 7.3 | 9.5 |

- **1 of 10 is at position ≤ 5, and it is `yes` (3.5), a query nobody targets.** None of the nine real queries is in the top 5. The objective is unmet on the measured 14%; the other 86% cannot be read.
- The best mover is the head query: position 9.6 → 7.0 and clicks 7 → 13 on a base of 265 → 418 impressions.
- `sun debilitated in which sign` and its variant are new this window and are the family #835 targets (merged 2026-11-13 00:29Z, so the page change is the last day of this window, not a measurement of it).

**CTR outliers.** Compared with the band's own rate of 1.27%, pages with ≥ 500 impressions, position ≤ 7.5 and CTR below it:

| page | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,684 | 17 | 0.63% | 6.6 |
| /learn/sade-sati/ | 2,078 | 14 | 0.67% | 6.6 |
| /learn/gochar-2026-planetary-transits/ | 1,863 | 20 | 1.07% | 5.5 |
| /learn/jupiter-in-10th-house-career/ | 1,791 | 16 | 0.89% | 7.0 |
| /learn/7th-lord-placement-marriage-guide/ | 1,457 | 15 | 1.03% | 7.3 |
| /learn/planets-in-7th-house-marriage/ | 1,090 | 10 | 0.92% | 6.5 |
| /learn/marriage-mahadasha-timing/ | 645 | 7 | 1.09% | 5.2 |
| /learn/manglik-dosh/ | 508 | 4 | 0.79% | 6.7 |
| **eight pages** | **12,116** | **103** | **0.85%** | |

At the band rate the eight would have taken about 154 clicks, a gap of **about 51 clicks per 28 days**. Same-position pages that beat the band: `10th-lord-in-6th-house-career` 2.85% at 6.6, `chronic-health-issues-kundli` 2.36% at 5.0, `muhurat/griha-pravesh` 5.7% at 6.1. Their query mix was not examined. This run holds no CTR-by-position curve for the site, so I do not size the gain from position.

## 3. Decay

| page | impressions now / prior | clicks now / prior | position now / prior | read |
|---|---|---|---|---|
| **/matching** | **112 / 322** (−65%) | 3 / 0 | **9.3 / 4.2** | the only material decay on a page that had ranked well, and **worse than last run** (position 7.8 → 9.3 between the two reports' windows). Tracked by #1076 and #508 |
| /learn/griha-pravesh-muhurat-2026-2027/ | 0 / 38 (`is_gone`) | 0 / 0 | – / 7.3 | GA4 shows 12 sessions (8 Organic) on this landing in the same window, so the page is reachable. Not determined why GSC shows none |
| /learn/the-9-grahas-overview/ | 28 / 101 | 0 / 0 | 9.5 / 7.9 | small |
| /learn/ketu-in-vedic-astrology/ | 4 / 63 | 0 / 1 | 8.5 / 7.2 | small |
| /learn/mars-remedies/ | 84 / 120 | 1 / 1 | 6.8 / 6.5 | small |
| /festivals | 293 / 241 | 0 / 0 | 34.3 / 28.9 | position far outside the band |

- **/matching:** onset cannot be dated. #696 (title/meta shortened, merged 2026-11-03) is inside this window, and so are #750, #769, #870, #888 and #892 on the same page. The fetch cannot split a page at a date (`--page-daily` exists but `agent-measure` does not call it, #953 open). I do not attribute the drop to the title or to anything else. GA4: 15 sessions (3 Organic), 73% bounce, 1.73 pages/session.
- No other page with ≥ 100 impressions lost ≥ 1.0 position.

## 4. Scores for closed issues carrying `thesis:` and `metric:`

Rule applied: score once, when the window is clean (window start on or after deploy). Today − 31 days = 2026-10-16. I read the existing comments on #311, #276 and #329 first. **Nothing was posted to any issue this run.**

| issue | deploy | window clean? | already posted | this run | verdict | posted? |
|---|---|---|---|---|---|---|
| **#311** four-page title/meta CTR test | PR #334, 2026-10-13 | yes | MISS, 2026-11-13, 0.937% (53 / 5,658) | combined CTR **0.951%** (57 / 5,993) vs bar ≥ 1.5%. Impressions floor met. Position 6.59. Prior window 16 / 2,769 = 0.578% | **MISS, unchanged** | no: 0.937 → 0.951%, not material |
| **#276** /dasha CTA on the Rahu–Ketu article | PR #342, 2026-10-14 | yes | BAR MET, not attributable, 2026-11-14 (1.42) | Organic Search **58 sessions, 1.40 pages/session** (bar ≥ 1.20 on ≥ 20). All channels 69 sessions, 1.34 | **BAR MET, not attributable**, unchanged | no |
| **#329** Manglik checker link | PR #344, 2026-10-14 | yes | UNSCOREABLE 3 vs 10, 2026-11-14; scoring stopped | Organic Search **3** sessions, 1.00 pages/session. All channels 6 | unscoreable at this traffic | no: scoring stays stopped |
| #508 /matching title/meta | PR #696, 2026-11-03 | no | pending, scoreable from 2026-12-04 | not scored; page decay in section 3 | pending | no |
| #685 /learn/sade-sati title | PR #690, 2026-11-03 | no | pending, scoreable from 2026-12-04 | reference only: 2,078 impressions, 14 clicks, 0.67%, position 6.6. Mixed window, not a score | pending | no |
| #426 sade-sati date correction (guard) | PR #673, 2026-11-02 | no | pending, scoreable from 2026-12-03 | not scored | pending | no |
| #553 panch-mahapurush link | PR #615, 2026-10-31 | no | pending, scoreable from 2026-12-01 | reference only: 13 Organic sessions at 1.00 pages/session. Not a score | pending | no |
| #518 learn → tool routes | last slice PR #754, 2026-11-06 | no | pending, scoreable from 2026-12-07 | not scored | pending | no |
| #835 debilitated-sun lede/FAQ | PR #940, 2026-11-13 | no | pending, scoreable from 2026-12-14 | the deploy is the last day of this window | pending | no |
| #570 `cta_click` event | PR #688, 2026-11-03 | no | pending, scoreable from 2026-12-04 | `cta_click` count read in section 6; not a score | pending | no |
| #514, #523 rashifal | 2026-10-25 / 2026-11-01 | – | unscoreable at this traffic, 2026-11-09 | not re-scored | stopped | no |

(Deploy dates and "already posted" columns come from earlier comments on those issues, not from this run's files. The "this run" column is read from this run's files.)

### The misses, as plainly as the hits

| result | what it says |
|---|---|
| **#311 MISS** (0.951% vs ≥ 1.5%) | A title/meta rewrite on four band pages did not reach the bar. CTR on the four rose from 0.578% to 0.951%, but impressions grew 2.2× over the same period (2,769 → 5,993) and `rahu-mahadasha-career-problems` moved from position 7.1 to 5.8, so the rise is not attributable to the titles. Three of the four are still below 1% (`debilitated-sun-career` 0.63%, `jupiter-in-10th-house-career` 0.89%, `manglik-dosh` 0.79%) at position 6.6–7.0. |
| **#329 unscoreable** (3 organic sessions vs floor 10) | The page ranks (508 impressions, position 6.7) but yields 3 organic sessions in 28 days, so a link on it cannot be measured at that traffic. |
| **#276 bar met, not attributable** (1.40 vs ≥ 1.20) | A positive number, but the page also took #518's first-screen tool link and #830's link rewording in the same window, and the metric has no pre-deploy comparison. Not credited to the CTA. |
| **#508 will not pass as written** | The pass condition needs position within ±1.5 of 4.3 (from the earlier note on that issue); `/matching` is at 9.3. |

## 5. Funnel

`ga4-events.json`, 10-17 → 11-13, event counts (events, not sessions or users; no per-form split):

| event | count |
|---|---:|
| page_view | 1,231 |
| user_identified | 724 |
| session_start | 709 |
| feature_view | 707 |
| first_visit | 582 |
| user_engagement | 301 |
| scroll | 186 |
| form_start | 140 |
| ask_answered | 132 |
| kundli_generated | 53 |
| cta_click | 15 |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |

- `cta_click`: 15 events in about 10 days of history. **8 of 15 carry `(not set)` for both paths**, so the split is readable for 7: `career-during-sade-sati` → `/` (2), `krittika-nakshatra` → `/` (1), `kaal-sarp-dosh` → `/kaal-sarp-check` (1), `name-numerology-explained` → `/numerology` (1), `rahu-mahadasha-ketu-antardasha` → `/dasha` (1), `saturn-in-10th-house-career` → `/kundli` (1). The count is partial history by the file's own note.
- **No step-through rate can be computed.** `form_start` (140) and `kundli_generated` (53) are totals across several forms. `kundli_generated` and `ask_answered` are known to fire on re-render and, on some loads, not at all (#1067, #1068, #1069 open), so even the totals are not completions. `form_submit` = 1 reads as an instrumentation gap. #1070 (instrument the core funnels) is open.
- Landing mix, GA4 folded landings: `/learn/*` 462 of 710 sessions (65%); `/` 67; tools and other 143; admin and `(not set)` 38.

## 6. Where time is spent

Basis: GA4 `engagedSessions` and `engagement_seconds` (`verify-first.json`, `ga4.json`). Site-wide: 311 engaged sessions of 710 (44%); 77,505 engagement seconds, average 109s per session.

| page | sessions | engaged | engaged rate | avg engagement (s) | GSC impressions / clicks / position |
|---|---:|---:|---:|---:|---|
| / | 67 | 45 | 67% | 238 | 182 / 8 / 5.9 |
| /learn/rahu-mahadasha-ketu-antardasha | 69 | 41 | 59% | 133 | 3,910 / 62 / 6.4 |
| /muhurat/griha-pravesh | 29 | 27 | 93% | 87 | 351 / 20 / 6.1 |
| /learn/sade-sati | 17 | 14 | 82% | 171 | 2,078 / 14 / 6.6 |
| /learn/rahu-mahadasha-career-problems | 23 | 14 | 61% | 280 | 1,010 / 20 / 5.8 |
| /learn/career-during-sade-sati | 25 | 13 | 52% | 226 | 1,138 / 20 / 5.5 |
| /learn/gochar-2026-planetary-transits | 35 | 12 | 34% | **28** | 1,863 / 20 / 5.5 |
| /learn/7th-lord-placement-marriage-guide | 26 | 12 | 46% | 64 | 1,457 / 15 / 7.3 |
| /learn/10th-lord-in-6th-house-career | 22 | 10 | 45% | 113 | 702 / 20 / 6.6 |
| /learn/jupiter-in-10th-house-career | 22 | 9 | 41% | 72 | 1,791 / 16 / 7.0 |

- **`gochar-2026-planetary-transits`** is the second-biggest new landing (35 sessions, 22 Organic, 66% bounce) with the shortest engagement of the ten: **28s on average, 34% engaged**. A page ranking at 5.5 where readers leave within 30 seconds is the page to look at first. This is a measurement of the symptom; I do not know why. Note that #1079 (merged 2026-11-15, after the window) rewrote this page's dates.
- The homepage keeps visitors longest (238s average engagement) and `rahu-mahadasha-career-problems` has the longest article engagement (280s). `debilitated-sun-career` also engages for 277s on 21 sessions (62% bounce).
- Tool funnels visible by landing: `/numerology` 22 sessions (11 Organic), 68% bounce, 85s; `/kundli` 17 sessions, 59% bounce, 50s; `/matching` 15 sessions, 73% bounce, 81s. These are landings, not completions.

## 7. Errors

| source | window | result |
|---|---|---|
| `llm-usage.json` | 7 days to 2026-11-16 00:40Z | 147 calls, 119 cache hits (**80%**), 28 misses. **The file carries no error or fallback counts, so errors per route are not measured.** |
| `verify-production.yml` | last 40 runs; most recent run 2026-11-15 21:35Z | **40 of 40 success** |
| open issues on a user-facing error | – | #1088 (`/kundli` returns a 503 page when the LLM fails), #1087 (`/ask?q=` renders a blank page when the answer is not in that instance's SQLite). Both exist and are open |

LLM usage by route (7 days):

| route | calls | hit rate | input tokens | tokens per measured call |
|---|---:|---:|---:|---:|
| natal | 107 | 92% | 53,478 | 6,684 (8 measured) |
| rashifal | 24 | 83% | 234,684 | 4,428 (53 measured) |
| ask | 13 | **0%** | 29,464 | 2,266 |
| dasha_deep_dive | 1 | 0% | 1,492 | 1,492 |
| monthly | 1 | 0% | 2,143 | 2,143 |
| matching | 1 | 0% | 1,774 | 1,774 |

- Overall: 323,035 input and 41,388 output tokens in 7 days. Peak day by the logged field: 13,804 on 2026-11-10; peak day by measured tokens: **141,908 on 2026-11-10**. The two fields disagree by 10×, and the measured one is 71% of the ~200k TPD ceiling named in CLAUDE.md. #925 (peak day at 83% of the Groq daily budget) is open and covers this.
- `ask` has no caching by construction (13 calls, 0 hits); it is personal. At 13 calls in 7 days it is not the budget's problem.
- "Tokens per call" for `rashifal` is measured on 53 calls, while the route's `calls` field says 24; the two counts are not the same population. I report both and do not reconcile them.

## 8. Search demand

Themes with impressions at positions 5–20 or low CTR (page mode complete; query mode is the 14% view). For each, the existing page is named. Nothing here proposes a new page.

| demand | impressions, position (window) | existing page | open issue |
|---|---|---|---|
| "sun debilitated in which sign" family (4 queries, 262 + 120 + 75 + 67) | 524 impressions, positions 6.2–8.8, 0 clicks | `/learn/debilitated-sun-career` (2,684 impressions, CTR 0.63%) | #835 shipped 2026-11-13 (not yet scoreable) |
| "jupiter in 10th house", "guru in 10th house" | 98 at 10.3, 71 at 8.8, 0 clicks | `/learn/jupiter-in-10th-house-career` (1,791 impressions, CTR 0.89%) | #1073 |
| "10th lord in 6th house" | 90 at 8.5, 2 clicks | `/learn/10th-lord-in-6th-house-career` (702, 2.85%) | none needed: it converts |
| "rahu mahadasha ketu antardasha" family | 418 at 7.0 (13 clicks), 67 at 7.3, 50 "ketu antardasha in rahu mahadasha" at 7.0 (2 clicks) | `/learn/rahu-mahadasha-ketu-antardasha` | #1075 |
| `/matching` | 112 impressions at 9.3 | `/matching` | #1076, #508 |
| `gochar-2026-planetary-transits` | 1,863 at 5.5, CTR 1.07%, 28s engagement | itself | #1071 (the 2027 sibling) |
| `yes` | 76 at 3.5, 0 clicks | **unknown**: query mode has no page | not worth action: a one-word query |

- The query view cannot tell me which page serves which query. Attribution above is by topic, not measured.
- I found no query with demand and no page in the 14% view. 86% of impressions are not readable by query, so that is "none seen", not "none exist".

## 9. Content opportunities — time-bound demand

Dates read from `src/astro_ai/festival_registry.py` this run (35 festivals; the registry carries 2026–2028 dates):

| date | event | existing page | read |
|---|---|---|---|
| **2026-11-20** (4 days) | Devuthani Ekadashi | `/festivals`; `vivah-muhurat-2027` covers wedding timing | no dedicated learn article. `learn/` has no `devuthani` or `ekadashi` page (checked by filename) |
| **2026-11-21** (5 days) | Tulsi Vivah | `/festivals` | no learn article by filename |
| 2027-01-15 | Makar Sankranti, Pongal | `/festivals` | no learn article by filename. Both fall after the 8-week horizon but inside the window the page needs to be indexed in |
| year ending | `gochar-2026-planetary-transits`, `diwali-muhurat-2026`, `karva-chauth-2026` carry the year in the slug | themselves | `gochar-2026` already draws 1,863 impressions at 5.5; #1071 files its 2027 sibling |
| year starting | `vivah-muhurat-2027` | exists | in place before the season |

- The registry has no festival dates between 2026-11-21 and 2027-01-14 apart from the two Sankranti entries. I do not know whether that is complete; I did not check the registry's coverage rule. **A date is stated here only if the registry holds it.**
- The festival-page cannibalisation rule applies: new pages go through `/learn`, and only after checking what already ranks. `/festivals` sits at position 34.3 with 293 impressions, so it is not a ranking page to protect.

## 10. Index status

`measurements/index-status.json` does not exist. #1065 (track index status per sitemap URL) is open. **Not measured.** The measurement that settles it is the URL Inspection API sweep #1065 describes, restricted to the 142 pages with impressions and the sitemap URLs with none.

## 11. Measurement gaps

| gap | in last three reports? | open issue | action |
|---|---|---|---|
| No GA4 prior-window export, so no GA4 period-on-period | **yes** (2026-11-13, 2026-11-14, 2026-11-15) | none was open | **filed #1115** |
| `--page-daily` not called by `agent-measure`; cannot split a page at its deploy date | yes | #953 | none |
| `git log origin/main --since` unusable (shallow checkout) | yes | #666, #974 | none |
| Index status | this run only (the file did not exist at the earlier runs) | #1065 | none |
| Per-form funnel step-through | yes | #1070, #1067, #1068, #1069 | none |
| Errors per route in `llm-usage.json` | this run only | none | not filed: first appearance. File if it repeats |
| Which pre-fix days hold the 38 admin and `(not set)` sessions | yes | #735 closed | not filed: ages out by 2026-12-11 |

## 12. What I could not determine, and the measurement that settles each

| gap | single measurement |
|---|---|
| Whether sessions and users moved with GSC | the GA4 previous-window export (#1115) |
| Whether `/matching` lost position before or after the 2026-11-03 title change | `fetch_gsc.py --by date --page-daily --pages /matching --days 56` (#953 wires it into `agent-measure`) |
| Why `griha-pravesh-muhurat-2026-2027` shows no GSC impressions but 12 GA4 sessions | the same `--page-daily` export on both griha-pravesh URLs plus GA4 `sessionSource` for that landing |
| Whether the rise is work or Diwali | the same window a year earlier; not available before 2027-11 |
| Query-level top-5 progress on 86% of impressions | not recoverable; Google withholds the queries |
| Source of 2026-10-23's 34-user day | a GA4 source × landing breakdown for that one date |
| Why `gochar-2026-planetary-transits` holds readers 28s | a per-section scroll or engagement read on that page; no export has it |
| Errors per LLM route | an `errors` / `fallbacks` count per route in `llm-usage.json` |
| Index status | #1065's export |

## 13. Issues filed

| # | title | why |
|---|---|---|
| **#1115** | analytics: add a GA4 previous-window export (`fetch_ga4.py --trend`) | the same gap appears in three consecutive reports and no open issue covered it; Evidence Block included. The `agent-measure.yml` half is a workflow edit the loop cannot push (#421), so it is stated in the issue |

No other finding needs an action I can state from this run's data. The `/matching` decay is already #1076, the `gochar-2026` engagement finding is in section 6 (no issue: the cause is unknown and the page was rewritten by #1079 after this window ends, so a re-measure is the next step, not a fix).
