# Analyst report — run 2026-11-18

**Window for every number below: 2026-10-19 → 2026-11-15** (28 days; the last 3 days are excluded, GSC lags 2–3 days and GA4 24–48h).
**Previous window** where a delta is quoted: **2026-09-21 → 2026-10-18** (`gsc-trend-*.json`). **GA4 has no previous-window export, so no GA4 period-on-period number appears in this report.** #1115 (the fetch flag) and #1205 (the workflow call that would write the file) are both open.
Every figure was read from `/tmp/*.json`, `src/astro_ai/festivals.py` or `gh` this run. Quotes from earlier reports or issue comments are labelled as such.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | note |
|---|---|---|---:|---|---|
| `gsc-band.json` | page, position 6–20 | 10-19 → 11-15 | 100% of 28,419 property impressions (rows sum 28,501) | no | `emitted_*`: 106 pages, 21,537 impressions = 76% |
| `gsc-all.json` | page | same | 100% | no | 143 pages |
| `gsc-daily.json` | date | same | 100% | no | 28 days, 28,419 impressions, 384 clicks |
| `gsc-trend-page.json` | page, now vs previous | 10-19 → 11-15 vs 09-21 → 10-18 | 100% | – | 143 pages now, 124 previous. Row sums: 28,501 / 384 now, 11,518 / 110 previous |
| `gsc-trend-query.json` | query, now vs previous | same | **14%** of 28,419 | – | partial view (Google withholds rare queries); 826 keys now, 217 previous. No site-wide conclusion can come from it |
| `ga4.json` | landing × channel | same | 100% of 776 sessions | no | 158 rows, 103 raw landings, 95 after folding query strings and trailing slashes |
| `ga4-daily.json` | date | same | 28 of 28 days | – | daily sessions sum to 779 against the property total of 776; I use 776 for totals |
| `ga4-events.json` | event | same | 17 event names, 5,204 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688): about 13 of the 28 days |
| `ga4-anomalies.json` | spike days | same | 2 spikes flagged | – | rule: active users ≥ max(2 × median, median + 10, 15); median 22 |
| `gsc-discover.json` | Discover | same | – | – | 0 clicks, 0 impressions on all 28 days, `top_pages` empty |
| `verify-first.json` | busiest pages | same | top 10 by engaged sessions | – | |
| `measure/llm-usage.json` | app LLM calls | **7 days to 2026-11-18 02:42Z** | – | – | a different window from everything else; calls, hits and tokens only |
| `index-status.json` | – | – | **absent** | – | not measured (section 10) |

## 1. Growth (lever 1)

**Search, GSC, 2026-10-19 → 11-15 against 2026-09-21 → 10-18** (page-row sums; property totals now 28,419 / 384):

| metric | now | previous | change |
|---|---:|---:|---:|
| impressions | 28,501 | 11,518 | 2.5× |
| clicks | 384 | 110 | 3.5× |
| CTR | 1.35% | 0.96% | +0.39 pt |
| average position (daily rows, now) | 6.1–7.6, no trend | – | – |

**GA4, 2026-10-19 → 11-15 only (no previous window):**

| metric | value |
|---|---:|
| sessions (`ga4.json`) | 776 |
| new users (sum of daily rows; matches `first_visit` = 637) | 637 |
| engaged sessions / engagement rate | 340 / 43.8% |
| average engagement per session | 104 s |

| channel | sessions | share | engaged rate | avg engagement per session | pages/session |
|---|---:|---:|---:|---:|---:|
| Organic Search | 474 | 61% | 56.5% | 135 s | 1.71 |
| Direct | 293 | 38% | 22.9% | 49 s | 1.68 |
| AI Assistant | 8 | 1% | 50% | 164 s | 4.25 |
| Unassigned | 2 | <1% | – | – | – |

The 8 AI Assistant sessions landed on `/learn/second-marriage-yoga-kundli/` (2), and one each on `foreign-career-yoga-kundli`, `gochar-2026-planetary-transits`, `griha-pravesh-muhurat-2026-2027`, `marriage-mahadasha-timing`, `saturn-in-10th-house-career` and `/matching`. 8 sessions is too few to carry a conclusion.

**Within the window** (first 14 days 10-19 → 11-01 against last 14 days 11-02 → 11-15, same files):

| | first 14 days | last 14 days |
|---|---:|---:|
| GA4 sessions | 283 | 496 |
| GSC impressions | 11,494 | 16,925 |
| GSC clicks | 133 | 251 |

**Which page groups drive the GSC change** (`gsc-trend-page.json`, impressions / clicks now vs previous):

| group | impressions now | previous | clicks now | previous |
|---|---:|---:|---:|---:|
| `/learn/*` articles | 26,623 | 10,549 | 327 | 93 |
| `/muhurat/*` | 553 | 59 | 26 | 8 |
| other (tools, hubs) | 817 | 631 | 19 | 3 |
| home | 194 | 106 | 9 | 5 |
| `/rashifal*` | 211 | 87 | 1 | 0 |
| `/panchang*` | 103 | 86 | 2 | 1 |

Articles carry 93% of impressions and 85% of clicks. 49 pages are new this window (234 impressions in total). The rise is concentrated: `gochar-2026-planetary-transits` went 12 → 2,325 impressions, `rahu-mahadasha-ketu-antardasha` 1,977 → 3,977, `debilitated-sun-career` 1,187 → 2,824, `jupiter-in-10th-house-career` 361 → 1,900.

**Seasonal or structural?** Both inputs are present and I cannot separate them.
- **Calendar:** `festivals.py` puts Dussehra 10-20, Karva Chauth 10-29, **Dhanteras 11-06, Diwali 11-08**, Bhai Dooj 11-11 and Chhath Puja 11-15 inside this window. None of the top 10 impression pages is a festival page; they are Rahu/Ketu, Sade Sati, 7th-house and career guides. The rise is not a festival-page rise.
- **Structural:** the top gainers are the pages that took content or title changes from the loop (#311, #835, #685, #1073 and others), but the loop closed many issues in the same weeks (section 3), and **this checkout is shallow (`git rev-parse --is-shallow-repository` = true; `git log origin/main --since=2026-10-19` returns one commit)**, so I cannot list them from git (#666, #974).
- **Not determinable from this run:** how much is Google re-ranking a young domain versus the work. The same window a year earlier does not exist.

**Spike days** (`ga4-anomalies.json`, rule active users ≥ 44):

| date | active users | source named by the file | verdict |
|---|---:|---|---|
| 2026-11-06 (Dhanteras) | 57 (59 sessions) | top row `(direct) / (none)` on `/rashifal/aries` (6 sessions, 17% engaged). 19 of 50 sessions had zero engagement: `(not set)`/desktop/United States 10, Chrome/desktop/United States 6, Chrome/mobile/United States 3 | **Mixed.** About 19 sessions look automated (US desktop, 0 s engagement). The remainder include google/organic readers of `/learn/rahu-mahadasha-career-problems/` (4 sessions, 224 s). GSC clicks that day: 17, near the surrounding days (12–19), so search did not spike. Discover: 0 |
| 2026-11-15 (Chhath Puja) | 51 (56 sessions) | top row google / organic on `/learn/rahu-mahadasha-ketu-antardasha/` (6 sessions, 83% engaged, 242 s). Tech split: Chrome/mobile/**China** 9 sessions with 0% engaged, 0 s; Chrome/mobile/India 17 sessions (59% engaged, 61 s). 5 direct sessions on `/panchang/2026-12-02` with 0% engaged, 1.6 s | **Mixed.** 9 China-mobile sessions and 5 dated-panchang direct sessions look automated (0 engagement). The India readers look real. GSC clicks that day: 14, against a 28-day mean of 13.7 (384 / 28), so no search spike. Discover: 0 on every day, so **not Discover** |

Neither spike is reported as growth. Two further high days sit under the threshold and were not broken down by the file: 10-23 (34 sessions, 34 users) and 11-14 (47 sessions, 32 users; 1.5 sessions per user is the highest ratio in the window). I cannot name their source from this run.

**Confound — Direct is not clean.** Direct is 38% of sessions at a 22.9% engaged rate against 56.5% for Organic. Its pages per session (1.68) is level with Organic's, which is not what real repeat visitors look like, and both spikes carry zero-engagement Direct rows. I do not treat Direct sessions as audience.

## 2. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page mode measures pages (a page's position is its average across its queries). Query mode covers 14%.

**Band, page mode** (`emitted_*`, 76% of impressions): 106 pages, 21,537 impressions, 277 clicks, **CTR 1.29%** (impressions-weighted). 89 of the 106 are at position ≤ 10 (21,278 impressions). **68 of the 106 had zero clicks**, covering 1,278 impressions (5.9% of the band).

Top 10 by `band_opportunity` (page mode):

| # | page | impressions | clicks | CTR | avg position | previous impressions / position |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,977 | 67 | 1.68% | 6.4 | 1,977 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,824 | 17 | 0.60% | 6.6 | 1,187 / 6.0 |
| 3 | /learn/sade-sati/ | 2,118 | 14 | 0.66% | 6.6 | 1,046 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,900 | 18 | 0.95% | 7.1 | 361 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,514 | 14 | 0.92% | 7.2 | 259 / 7.9 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,155 | 11 | 0.95% | 6.7 | 568 / 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 994 | 15 | 1.51% | 7.0 | 418 / 6.9 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 529 | 3 | 0.57% | 7.7 | 122 / 7.8 |
| 9 | /learn/manglik-dosh/ | 498 | 4 | 0.80% | 6.6 | 469 / 7.5 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 743 | 20 | 2.69% | 6.7 | 185 / 7.0 |

**Top-5 test, pages.** The ten highest-impression pages (`gsc-all.json`) are the first, second, fourth, fifth and sixth rows above plus `gochar-2026-planetary-transits` (2,325 / 23 clicks / **5.2**), `career-during-sade-sati` (1,204 / 22 / **5.4**), `planets-in-7th-house-marriage` (1,155), `rahu-mahadasha-career-problems` (1,038 / 21 / **5.8**) and `panch-mahapurush-yoga` (994). **0 of the ten are at average position ≤ 5.0.** Three are within 1 position (5.2, 5.4, 5.8). Pages at ≤ 5.0 with ≥ 50 impressions: `chronic-health-issues-kundli` (423, 11 clicks, 4.9) and `2nd-lord-placement-wealth-guide` (76, 3 clicks, 4.4).

**Top-5 test, queries** (`gsc-trend-query.json`, **14% of impressions, partial**). Ten highest-impression queries:

| query | impressions | previous | clicks | position | previous position |
|---|---:|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 434 | 259 | 14 | 6.8 | 9.7 |
| sun debilitated in which sign | 296 | 0 | 0 | 7.7 | – |
| sun is debilitated in which sign | 133 | 0 | 0 | 6.8 | – |
| jupiter in 10th house | 107 | 0 | 0 | 11.1 | – |
| yes | 97 | 7 | 0 | 3.6 | 3.9 |
| 10th lord in 6th house | 93 | 0 | 2 | 8.6 | – |
| sun debilitated sign | 80 | 2 | 0 | 6.0 | 3.0 |
| sun debilitated | 73 | 0 | 0 | 8.8 | – |
| guru in 10th house | 71 | 0 | 0 | 8.8 | – |
| rahu mahadasha and ketu antardasha | 67 | 49 | 0 | 7.1 | 9.4 |

- **1 of 10 is at position ≤ 5, and it is `yes` (3.6), a query nobody targets.** None of the nine real queries is in the top 5. The objective is unmet on the measured 14%; the other 86% cannot be read.
- The best mover is the head query: position 9.7 → 6.8 on 259 → 434 impressions, 14 clicks now. Its previous-window clicks are not in the extract, so I do not quote a click change.
- The "sun debilitated" family is 34 query rows, 970 impressions, 0 clicks, weighted position 7.5. It is the family #835 targets (PR #940, merged 2026-11-13), so only the last 3 days of this window carry the change.

**CTR outliers.** Pages with ≥ 500 impressions, position ≤ 7.5 and CTR below the band's own 1.29%:

| page | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,824 | 17 | 0.60% | 6.6 |
| /learn/sade-sati/ | 2,118 | 14 | 0.66% | 6.6 |
| /learn/7th-lord-placement-marriage-guide/ | 1,514 | 14 | 0.92% | 7.2 |
| /learn/planets-in-7th-house-marriage/ | 1,155 | 11 | 0.95% | 6.7 |
| /learn/jupiter-in-10th-house-career/ | 1,900 | 18 | 0.95% | 7.1 |
| /learn/gochar-2026-planetary-transits/ | 2,325 | 23 | 0.99% | 5.2 |
| **six pages** | **11,836** | **97** | **0.82%** | |

At the band's own rate the six would have taken about 152 clicks, a gap of **about 55 clicks per 28 days**. Same-position pages that beat the band: `10th-lord-in-6th-house-career` 2.69% at 6.7, `rahu-mahadasha-career-problems` 2.02% at 5.8, `muhurat/griha-pravesh` 5.4% (21 of 389) at 6.2. I did not examine their query mix. This run holds no CTR-by-position curve for the site, so I size no gain from position. `gochar-2026` is the odd one: position 5.2, CTR 0.99%, and 27 s average engagement in GA4 (section 6).

## 3. Decay

`gsc-trend-page.json`, pages with ≥ 30 impressions in the previous window and a worse position or a loss:

| page | impressions now / previous | position now / previous | clicks now / previous | note |
|---|---|---|---|---|
| /matching | 121 / 325 | **8.6 / 4.3** | 3 / 0 | the one loss on a tool page. #1076 open; #508 title change shipped 2026-11-03 and I still cannot date the onset (#953) |
| /learn/the-9-grahas-overview/ | 25 / 103 | 9.6 / 7.9 | 0 / 0 | |
| /learn/ashwini-nakshatra/ | 91 / 103 | 7.7 / 5.7 | 1 / 1 | |
| /festivals | 295 / 243 | 34.0 / 29.9 | 0 / 0 | impressions up, position down; no clicks in either window |
| /learn/ketu-in-vedic-astrology/ | **0** / 65 | – / 7.2 | 0 / 1 | gone from GSC this window |
| /learn/griha-pravesh-muhurat-2026-2027/ | **0** / 37 | – / 7.3 | 0 / 0 | gone from GSC, but GA4 shows **13 sessions** on it (8 Organic Search, 4 Direct, 1 AI Assistant). Same gap named in the 2026-11-17 report; the GA4 organic landings with no GSC impressions are not explained |
| /learn/mars-remedies/ | 75 / 124 | 7.0 / 6.5 | 1 / 1 | |
| /learn/santan-prapti-children-in-kundli/ | 18 / 51 | 6.2 / 6.2 | 0 / 0 | |
| /learn/financial-struggles/ | 5 / 37 | 6.2 / 6.6 | 0 / 0 | |
| /learn/gajakesari-yoga/ | 6 / 32 | 3.8 / 5.9 | 0 / 0 | impressions down, position up |

All the losses are small in absolute terms (every page above has under 330 impressions in either window). The clearest loss is `/matching`.

**Confound — concurrent ships.** The closed-issue list shows many merges in this window (content and grounding fixes on the very pages that moved, title changes, SEO redirect and link work); I did not count them, and the checkout cannot. With a shallow checkout I cannot list them by date from git, so I attribute no movement to any single ship.

## 4. Scores for closed issues carrying `thesis:` and `metric:`

Rule applied: score once, when the window is clean (the window starts on or after the deploy). Today − 31 days is 2026-10-18, and this window starts 2026-10-19. I read the existing comments on every issue first. Merge dates are from `gh pr view`.

**Posted this run (seven comments, each the first analyst note on its issue, all deployed 2026-11-17):**

| issue | deploy | what I posted |
|---|---|---|
| #1072 "which mahadasha is best for career" section | PR #1145, 2026-11-17T03:23Z | pending, scoreable from 2026-12-18. Reference: 33 impressions, 0 clicks, position 9.0 (+ 8 impressions at 9.6 for the "good" variant), 14% view. Guard page `vimshottari-dasha-explained` 373 impressions at 7.2. Likely position-only at this coverage |
| #1071 gochar-2027 page | PR #1148, 2026-11-17T04:56Z | pending. Guard (gochar-2026 no worse than 7.2): from 2026-12-18; reference 2,325 impressions at 5.2. Main metric: from **2027-02-28** per the issue's own window. `gochar-2027` has no GSC row yet |
| #1175 tool pages ↔ articles links | PR #1179, 2026-11-17T13:03Z | pending, scoreable from 2026-12-18; reference landings and the confound with #518/#276 |
| #1068 completion events | PR #1157, 2026-11-17T07:58Z | pending; the metric needs a server-log count the loop cannot read; will post "unscoreable here" once on 2026-12-18 if not supplied |
| #1067 analytics-before-load fix | PR #1150, 2026-11-17T06:19Z | pending; `dasha_deep_dive_viewed` is **2** in this window, not 0 as the issue's baseline said, so a pass needs a count well above 2 to show a change |
| #1176 308 on slash variants | PR #1197, 2026-11-17T20:29Z | **not scoreable from GA4/GSC**, structural, asserted by `verify-production`; no timer |
| #1177 no 303 in no-chart nav | PR #1182, 2026-11-17T17:31Z | **not scoreable from GA4/GSC**, same; no timer |

**Already scored or pending, nothing posted this run** (the verdict has not changed and the number has not moved past what the metric calls material):

| issue | deploy | clean? | last posted | this run | verdict |
|---|---|---|---|---|---|
| **#311** four-page title/meta CTR test | PR #334, 2026-10-13 | yes | MISS, 2026-11-13 (0.937%); re-checked 2026-11-17 (0.981%) | pages `rahu-mahadasha-career-problems`, `debilitated-sun-career`, `jupiter-in-10th-house-career`, `manglik-dosh`: **6,260 impressions, 60 clicks, CTR 0.958%** vs bar ≥ 1.5%; weighted position 6.6. Previous window: 2,862 impressions, 15 clicks, 0.524% | **MISS, unchanged** (0.981 → 0.958%, not material) |
| **#276** /dasha CTA on the Rahu–Ketu article | PR #342, 2026-10-14 | yes | BAR MET, not attributable | Organic Search **70 sessions, 1.60 pages/session** (bar ≥ 1.20 on ≥ 20). All other `/learn/*` organic landings combined: **304 sessions at 1.56** | **BAR MET, not attributable**. The number moved 1.38 → 1.60 but the verdict did not, and the comparison group sits at 1.56, so the CTA is not credited |
| **#329** Manglik checker link | PR #344, 2026-10-14 | yes | UNSCOREABLE 3 vs 10 | Organic Search **4** sessions on `/learn/manglik-dosh/`, 1.00 pages/session (floor 10) | unscoreable at this traffic; scoring stays stopped |
| #508 /matching title/meta | PR #696, 2026-11-03 | no | pending, scoreable from 2026-12-04 | reference only: 121 impressions at 8.6 (the pass condition needs ≥ 300 impressions at ≥ 1.0% CTR) | pending; the floor looks unreachable at 121 impressions |
| #685 /learn/sade-sati title | PR #690, 2026-11-03 | no | pending | reference only: 2,118 impressions, 14 clicks, 0.66%, position 6.6. Mixed window | pending |
| #426 sade-sati date guard | PR #673, 2026-11-02 | no | pending | reference only: position 6.6 (guard: within ±1 of 6.2). Mixed window | pending |
| #553 panch-mahapurush link | PR #615, 2026-10-31 | no | pending | reference only. Mixed window | pending |
| #518 learn → tool routes | last slice PR #754, 2026-11-06 | no | pending | not scored | pending |
| #835 debilitated-sun lede and FAQ | PR #940, 2026-11-13 | no | pending | not scored. The deploy is the last 3 days of this window | pending |
| #570 `cta_click` event | PR #688, 2026-11-03 | no | pending | `cta_click` read in section 5: 15 events | pending |
| #528 /ask `q=` out of GA4 | PR #801, 2026-11-09 | no | pending | reference only: 1 landing still carries `q=` (1 session, `/ask?q=…`) in this window, which holds 21 pre-fix days. Not a score | pending |
| #735 /admin out of GA4 | PR #877, 2026-11-11 | no | pending | reference only: 17 sessions on `/admin/*` in this window, which holds 23 pre-fix days | pending |
| #1073 / #1074 / #1075 / #1066 / #1093 | 2026-11-15 / 16 | no | pending notes posted 2026-11-17 | not re-posted | pending, scoreable 2026-12-16 / 12-17 |
| #843, #514, #523 | – | – | unscoreable at this traffic | not re-scored | stopped |

For every pending issue I wrote a timer line to `/tmp/analyst-timers.txt` (20 lines; `#1071` has two keys, `score-1071` for 2026-12-18 and `score-1071-final` for 2027-02-28).

### The misses, as plainly as the hits

| result | what it says |
|---|---|
| **#311 MISS** (0.958% vs ≥ 1.5%) | A title/meta rewrite on four band pages did not reach the bar. CTR on the four rose from 0.524% to 0.958%, but their impressions grew 2.2× (2,862 → 6,260) and `rahu-mahadasha-career-problems` moved from position 7.1 to 5.8, so the rise is not attributable to the titles. Three of the four are still below 1% (`debilitated-sun-career` 0.60%, `jupiter-in-10th-house-career` 0.95%, `manglik-dosh` 0.80%) at position 6.6–7.1 |
| **#329 unscoreable** (4 organic sessions vs floor 10) | The page ranks (498 impressions, position 6.6) but yields 4 organic sessions in 28 days, so a link on it cannot be measured at that traffic |
| **#276 bar met, not attributable** (1.60 vs ≥ 1.20) | The page also took #518's first-screen tool link and #830's link rewording, and the metric has no pre-deploy comparison. Other `/learn/*` organic landings: 304 sessions at 1.56, level with this page |
| **#508 will probably not be scoreable as written** | It needs ≥ 300 impressions in a window; `/matching` shows 121 at position 8.6, against a baseline of 4.3 |
| **#1074 at risk of the same fate** (carried from 2026-11-17) | 59 dated `/panchang/` URLs, 103 impressions, 2 clicks, against a floor of 150 |
| **#1067's baseline was wrong** | The issue stated `dasha_deep_dive_viewed` = 0; the events export for this window reads 2 |

## 5. Funnel

`ga4-events.json`, 10-19 → 11-15, event counts (events, not sessions or users; no per-form split):

| event | count |
|---|---:|
| page_view | 1,337 |
| user_identified | 802 |
| feature_view | 785 |
| session_start | 776 |
| first_visit | 637 |
| user_engagement | 328 |
| scroll | 194 |
| form_start | 140 |
| ask_answered | 128 |
| kundli_generated | 48 |
| cta_click | 15 |
| click | 4 |
| view_search_results | 4 |
| dasha_deep_dive_viewed | 2 |
| feedback_sent | 2 |
| form_submit | 1 |
| subscribe_completed | 1 |

- `cta_click`: 15 events in about 13 days of history. **8 of 15 carry `(not set)` for both paths**; the readable 7 are `career-during-sade-sati` → `/` (2), `krittika-nakshatra` → `/` (1), `kaal-sarp-dosh` → `/kaal-sarp-check` (1), `name-numerology-explained` → `/numerology` (1), `rahu-mahadasha-ketu-antardasha` → `/dasha` (1), `saturn-in-10th-house-career` → `/kundli` (1). Partial history.
- **No step-through rate can be computed.** `form_start` (140) and `kundli_generated` (48) are totals across several forms, and `form_submit` = 1 reads as an instrumentation gap. #1070 is open. `kundli_generated` and `ask_answered` were counting re-renders until PR #1157 (2026-11-17), so both are inflated for this whole window.
- **A readable ratio:** `session_start` 776 to `feature_view` 785 is about 1:1. Landing mix, GA4 folded landings: `/learn/*` 509 of 776 sessions (66%; 504 articles + 5 index); `/` 70; `/muhurat/*` 47; `/numerology` 23; `/kundli` 20; `/matching` 17; `/admin/*` 17; `(not set)` 17.
- Sessions landing on a core tool page: kundli 20 + matching 17 + numerology 23 + ask 2 = 62 of 776 = 8.0%. The site's traffic lands on articles and the tool funnels start from there; `cta_click` is the only measure of that step and it holds 15 events.

## 6. Where time is spent (lever 2)

`verify-first.json` (GA4 `engagedSessions`, 10-19 → 11-15) with GSC joined:

| page | sessions | engaged | engaged rate | avg engagement | GSC impressions / clicks / position |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 82 | 49 | 60% | 139 s | 3,978 / 67 / 6.4 |
| / | 70 | 45 | 64% | 226 s | 195 / 9 / 5.7 |
| /muhurat/griha-pravesh | 31 | 30 | **97%** | 92 s | 389 / 21 / 6.2 |
| /learn/gochar-2026-planetary-transits | 41 | 16 | **39%** | **27 s** | 2,325 / 23 / 5.2 |
| /learn/sade-sati | 18 | 14 | 78% | 162 s | 2,118 / 14 / 6.6 |
| /learn/rahu-mahadasha-career-problems | 23 | 14 | 61% | 280 s | 1,038 / 21 / 5.8 |
| /learn/7th-lord-placement-marriage-guide | 28 | 12 | 43% | 59 s | 1,514 / 14 / 7.2 |
| /learn/career-during-sade-sati | 26 | 12 | 46% | 207 s | 1,204 / 22 / 5.4 |
| /learn/10th-lord-in-6th-house-career | 25 | 12 | 48% | 100 s | 743 / 20 / 6.7 |
| /learn/jupiter-in-10th-house-career | 23 | 10 | 43% | 68 s | 1,900 / 18 / 7.1 |

- Longest holds: `rahu-mahadasha-career-problems` 280 s, `debilitated-sun-career` 268 s (21 sessions, 38% engaged), `/` 226 s, `career-during-sade-sati` 207 s.
- **Weakest hold on a top page:** `gochar-2026-planetary-transits`, 41 sessions, 27 s, 39% engaged, 26 organic. It has the most-improved ranking of any page (12 → 2,325 impressions) and the shortest time on page of the ten. #1079 and #1100 (gochar-2026 date and per-rashi fixes) closed on 2026-11-15 and 2026-11-16, so part of the window holds the page before them; the window cannot separate the two versions, and I did not check their deploy times.
- `/muhurat/griha-pravesh` is the best tool-like landing: 31 sessions, all Organic Search, 97% engaged, 5.4% CTR.
- **Tool funnels visible in GA4:** `/kundli` 20 sessions at 35% engaged and 48 s, `/matching` 17 sessions at 24% engaged, `/numerology` 23 sessions at 35% engaged and 85 s. These three are low; most arrive Direct (kundli 15 of 20, matching 13 of 17, numerology 11 of 23), so they are not search visitors.
- Per-section engagement or scroll depth is not exported.

## 7. Errors (lever 3)

| source | window | reading |
|---|---|---|
| `llm-usage.json` | 7 days to 2026-11-18 02:42Z | 161 calls, 131 cache hits (**81%**), 30 misses. Input tokens 104,336, output 21,376. Peak day `2026-11-13`: 6,849 tokens by `peak_day_tokens`, 32,768 by `peak_day_measured_tokens` (two different measures in the file) |
| route detail | same | `natal` 112 calls (103 hits, 91%, 6,607 tokens per measured call over 9 calls); `rashifal` 28 calls, 28 hits, tokens not recorded (served from cache); `ask` 16 calls, 0 hits, 2,218 tokens per call; `monthly` 2; `today` 1; `dasha_deep_dive` 1; `matching` 1 |
| errors or fallbacks per route | – | **not in the file**. It carries no error or fallback key (keys listed in #1208). Not measured |
| `verify-production.yml`, last 60 runs (2026-11-15 → 11-18) | – | 51 success, 5 cancelled, **4 failure**. All 4 failures are the step "Wait for the deploy" (2 push runs on 2026-11-17 13:27 and 18:12, 2 dispatch runs on 2026-11-17 08:10 and 2026-11-16 03:17); no production invariant failed. The run after each succeeded. This is the shape #341 describes |
| open issues on a user-facing error | – | #1087 (`/ask?q=` blank page) and #1088 (`/kundli` 503 on an LLM failure) are **closed** (2026-11-16). No open issue tracks a user-facing route error. #925 (peak day vs Groq daily budget) and #1207 (queue) are open and are not route errors |

- `ask` runs 16 calls with a 0% hit rate, which is expected for personal questions. 16 calls at 2,218 tokens is 35,502 input tokens in 7 days.
- **Gap, now in three consecutive reports:** errors per route cannot be read. **Filed as #1208** (export `fallbacks` and `fallback_reasons`, which `llm_stats.py` already records, in `llm-usage.json`).

## 8. Search demand (lever 4)

`gsc-trend-query.json`, **14% of impressions, partial**; 951 query rows, 4,077 impressions, 43 clicks. Themes by regex on the query text, all with the existing page named:

| theme | query rows | impressions | clicks | weighted position | existing page |
|---|---:|---:|---:|---:|---|
| Rahu–Ketu dasha | 61 | 1,026 | 23 | 7.4 | `/learn/rahu-mahadasha-ketu-antardasha/` (ranks, 67 clicks on the page overall) |
| sun debilitated | 34 | 970 | 0 | 7.5 | `/learn/debilitated-sun-career/`. #835 shipped 2026-11-13 |
| 10th house / 10th lord | 87 | 645 | 4 | 10.1 | `/learn/jupiter-in-10th-house-career/`, `10th-lord-in-6th-house-career`, `saturn-in-10th-house-career`, `sun-in-10th-house-career`. #1073 shipped 2026-11-16 |
| jupiter / guru | 74 | 452 | 1 | 9.6 | the same Jupiter pages and `guru-jupiter-in-vedic-astrology` |
| 7th house / marriage | 59 | 199 | 2 | 9.2 | `planets-in-7th-house-marriage`, `7th-lord-placement-marriage-guide` |
| manglik / mars | 71 | 132 | 1 | 12.6 | `/learn/manglik-dosh/`, `mangal-mars-in-vedic-astrology` |
| sade sati | 38 | 59 | 0 | 8.4 | `/learn/sade-sati/` (the page has 2,118 impressions; the 14% view holds 59) |
| dasha / career | 3 | 43 | 0 | 8.9 | `/learn/vimshottari-dasha-explained/` section from #1072 |
| gochar / transit | 25 | 54 | 0 | 9.1 | `/learn/gochar-2026-planetary-transits/`, `gochar-2027-planetary-transits` |
| kundli | 10 | 34 | 0 | 15.3 | `/kundli` |
| muhurat | 14 | 28 | 1 | 9.8 | `/muhurat/*`, the `/learn` muhurat guides |

- **At positions 11–20 with ≥ 15 impressions:** only `jupiter in 10th house` (107 impressions, position 11.1) and `mangal dosha cancellation` (15, 16.5). Both have an existing page; no new page is indicated.
- **Brand queries:** `bhagya chart` 21 impressions / 3 clicks / 6.0; `bhagya.com` 12 / 1 / 3.8; `cheiro numerology calculator` 17 / 2 / 5.8 (`/numerology`).
- **`yes`** (97 impressions at 3.6) is not a topic; I do not count it.
- **Queries with no page:** I found none this run. Every theme above maps to a page that exists. `7.5 sani`, `shani 7.5 years` and `7.5 years shani effects` (12–13 impressions each) map to `/learn/sade-sati/`. I have not verified that those pages carry the sentence the query asks for; that is for product-manager.
- **Pages with demand and no clicks:** the 68 band pages with zero clicks cover 1,278 impressions; the four largest are named in section 2's CTR table.

## 9. Content opportunities — time-bound demand (lever 5)

Dates are read from `src/astro_ai/festivals.py` / `festival_registry.py` by `festivals_for_date()` for 2026-11-18 → 2027-01-27, not from memory.

| date | festival in the registry | existing page | GSC in this window |
|---|---|---|---|
| 2026-11-20 | Devuthani Ekadashi (Prabodhini) | registry entry only; `/festivals` hub (295 impressions at position 34.0, 0 clicks). I found no `/learn` article | – |
| 2026-11-21 | Tulsi Vivah | same | – |
| 2026-11-22 → 2027-01-14 | **no entry in the registry** | – | – |
| 2027-01-15 | Makar Sankranti and Pongal | registry entries; no `/learn` article found | – |

- **The registry holds nothing between 2026-11-22 and 2027-01-14.** I name no December festival because the file does not carry one. Whether that is a gap in the registry or a true gap in its scope is not determined here.
- **Annual pages whose year is ending:** `gochar-2026-planetary-transits` (2,325 impressions, position 5.2). Its 2027 sibling shipped 2026-11-17 (#1071) and has no GSC row yet. `diwali-muhurat-2026` (75 impressions, position 11.1) and `karva-chauth-2026` (7 impressions) are past events. `griha-pravesh-muhurat-2026-2027` has 0 GSC impressions in this window against 13 GA4 sessions. `vivah-muhurat-2027` has 42 impressions at 9.2 and 0 clicks.
- **The two nearest dated events (11-20, 11-21) are 2 and 3 days away.** I have no index-status export (section 10), so I cannot say how fast a new page is indexed on this site.

## 10. Index status (lever 6)

`measurements/index-status.json` does not exist. #1065 is open. **Not measured.** The measurement that settles it is the URL Inspection API sweep #1065 describes, restricted to the 143 pages with impressions and the sitemap URLs with none. The cases it would settle here: `griha-pravesh-muhurat-2026-2027` (0 GSC impressions, 13 GA4 sessions), `ketu-in-vedic-astrology` (65 → 0 impressions), `gochar-2027-planetary-transits` (no row after 1 day live).

## 11. Measurement gaps (lever 7)

I read `measurements/2026-11-15.md`, `2026-11-16.md` and `2026-11-17.md` for repeats.

| gap | in each of the last three reports? | open issue | action |
|---|---|---|---|
| No GA4 previous-window export, so no GA4 period-on-period | yes | #1115 (flag), #1205 (workflow call) | none; still open |
| `--page-daily` not called by `agent-measure`; cannot split a page at its deploy date | yes | #953 | none |
| `git log origin/main --since` unusable (shallow checkout) | yes (this run: 1 commit visible since 2026-10-19) | #666, #974 | none |
| Per-form funnel step-through | yes | #1070 | none |
| Index status | yes | #1065 | none |
| Errors per route in `llm-usage.json` | **2026-11-16, 2026-11-17 and this run** | none until now | **filed as #1208** |
| GA4 `page_location` export (the metric for #1066 and #1093) | 2026-11-17 and this run | none | not filed: two of three. If it appears again tomorrow with no issue, file it |
| Source of the high days under the anomaly threshold (10-23, 11-14) | 2026-11-17 and this run | none | not filed: two of three |
| Server-log count for #1068's metric | first appearance | none | not filed |
| GSC impressions for pages that GA4 shows organic sessions on (`griha-pravesh-muhurat-2026-2027`: 0 vs 13) | 2026-11-17 and this run | none | not filed: two of three |

## 12. What I could not determine, and the measurement that settles each

| gap | single measurement |
|---|---|
| Whether sessions and users moved with GSC | the GA4 previous-window export (#1115 / #1205) |
| Whether `/matching` lost position before or after the 2026-11-03 title change | `fetch_gsc.py --by date --page-daily --pages /matching --days 56` (#953 wires it into `agent-measure`) |
| Why `griha-pravesh-muhurat-2026-2027` has 0 GSC impressions and 13 GA4 sessions | the same `--page-daily` export, plus GA4 `sessionSource` for that landing |
| Whether the impressions rise is the work or the festival season | the same window a year earlier; not available before 2027-11 |
| Which ships landed in the window | a full-depth checkout (#974) |
| Query-level top-5 progress on 86% of impressions | not recoverable; Google withholds the queries |
| Source of the high days 10-23 and 11-14 | a GA4 source × landing × tech breakdown for those dates (the anomaly file only covers days over the threshold) |
| Why `gochar-2026-planetary-transits` holds readers 27 s | a per-section scroll or engagement read on that page; no export has it |
| Errors and fallbacks per LLM route | #1208 |
| Whether #1066 and #1093 worked | a GA4 Pages-and-screens export of `page_location` filtered on the query string |
| Whether #1068's completion events now match the server | the server-log count of `POST /reading` 303 |
| Index status | #1065's export |

## 13. Issues filed

| # | title | why |
|---|---|---|
| **#1208** | analytics: export LLM fallbacks (and reasons) in llm-usage.json — errors per route are unmeasured in three consecutive analyst reports | lever 7 rule: the gap appeared in 2026-11-16, 2026-11-17 and this run, and no open issue covers it. `llm_stats.py` already records `fallbacks` / `fallback_reasons`; `collect_llm_usage.py` drops them |

Seven comments were posted on issues (section 4): #1072, #1071, #1175, #1068, #1067, #1176, #1177. `/tmp/analyst-timers.txt` holds 20 timer lines for the next step to set with `scripts/timers.py set --from-file`.
