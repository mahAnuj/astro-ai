# Analyst report — 2026-11-27

Everything below was read this run from `/tmp/*.json` and `/tmp/measure/*.json`, from `gh` and `git` this run, from one `curl` of production, or from `festival_registry.py`. What I did not read is marked **not measured**.

**Windows.** **W** = 2026-10-28 → 2026-11-24 (28 days, last 3 excluded). **P** = 2026-09-30 → 2026-10-27, the 28 days before. Both GSC and GA4 trend files use these two windows.

**Coverage.** GSC `dimension: page` is 100% of the property's 31,891 W impressions and was not truncated. GA4 landing × channel is 100% of 834 sessions and was not truncated. GSC `dimension: query` is **14%** of W impressions, so it is a partial view and I draw no whole-site conclusion from it. GA4 `ga4-daily.json` sums to 838 sessions against 834 in the landing and trend files; I could not reconcile the 4-session gap from these files.

**Production is serving.** `/health` returned `ok: true`, revision `bhagya-00892-vgb`, `build_sha` `45550f1…`, which is the head of `main`.

## 0. The one number to read first

| | W | P | change |
|---|---:|---:|---:|
| GA4 sessions | 834 | 438 | **+90.4%** |
| GA4 active users | 692 | 336 | +106.0% |
| GA4 organic sessions | 542 | 210 | +158.1% |
| GSC clicks (page rows) | 445 | 153 | +190.8% |
| GSC impressions (page rows) | 31,974 | 13,953 | +129.2% |

Organic Search supplies 332 of the 396 added sessions. The growth is real and carried by `/learn` articles, and it has **not** moved rank: **1 of the top-10 pages by impressions is at position ≤ 5.0** (`gochar-2026`, 4.8; the others sit at 5.4 to 7.2). Impressions rose because more pages were shown, not because the band pages climbed.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md says: move the 6–20 band into the top 5 on the ten highest-impression queries. **That cannot be measured as worded**: the query export sees 14% of impressions, so the ten highest-impression queries cannot be named. The page proxy is the only readable figure.

| band, GSC page mode, W | value |
|---|---|
| pages at average position 6–20 | 104 pages, 23,399 impressions (73% of W; `emitted_coverage_pct`), 323 clicks |
| of those, pages with ≥ 200 impressions | 22 |
| pooled CTR of those 22 | 1.36%; median 1.16% |
| top-10 pages by impressions at position ≤ 5.0 | **1 of 10** |

Ranked by `band_opportunity` (impressions × achievable gain), W:

| # | page | impressions | clicks | CTR | position | note |
|---:|---|---:|---:|---:|---:|---|
| 1 | `/learn/debilitated-sun-career/` | 2,738 | 18 | **0.66%** | 6.4 | largest CTR gap on the site. At the band's 1.36% it would take about 37 clicks, not 18 |
| 2 | `/learn/rahu-mahadasha-ketu-antardasha/` | 3,076 | 57 | 1.85% | 6.5 | already above the band rate, the best earner |
| 3 | `/learn/jupiter-in-10th-house-career/` | 2,379 | 29 | 1.22% | 6.9 | |
| 4 | `/learn/sade-sati/` | 1,949 | 17 | **0.87%** | 6.8 | second-largest CTR gap |
| 5 | `/learn/7th-lord-placement-marriage-guide/` | 1,827 | 20 | 1.09% | 7.0 | |
| 6 | `/learn/planets-in-7th-house-marriage/` | 1,634 | 16 | 0.98% | 6.8 | position 5.8 in P, now 6.8 |
| 7 | `/learn/panch-mahapurush-yoga/` | 1,114 | 16 | 1.44% | 7.2 | |
| 8 | `/learn/mangal-mars-in-vedic-astrology/` | 643 | 3 | **0.47%** | 7.7 | |
| 9 | `/learn/saturn-in-10th-house-career/` | 571 | 9 | 1.58% | 7.3 | |
| 10 | `/learn/manglik-dosh/` | 489 | 4 | 0.82% | 6.9 | |

**CTR outliers (position fine, clicks poor).** These are title and meta problems, not content problems. Baseline: pooled 1.36% across the 22 band pages with ≥ 200 impressions.
- `debilitated-sun-career` 0.66% on 2,738.
- `sade-sati` 0.87% on 1,949.
- `mangal-mars-in-vedic-astrology` 0.47% on 643.
- `shukra-venus-in-vedic-astrology` 0.47% on 425 (position 6.2).

#835 and #685 target the first two and are pending (§2). Google re-crawled neither after its latest edit (§7).

**Decay (page rows, W vs P, ≥ 100 impressions in both windows).**

| page | impressions P → W | position P → W | clicks P → W | read |
|---|---|---|---|---|
| `/matching` | 343 → 115 | 4.4 → **10.2** | 1 → 3 | lost 5.8 positions and 66% of impressions. #508 shortened its title on 2026-11-03, inside W, so the fall is **confounded** by that edit and its cause is **not determined**. #1076 is the open investigation and #953 the missing per-page × per-day export |
| `/learn/planets-in-7th-house-marriage/` | 387 → 1,634 | 5.8 → 6.8 | 6 → 16 | gained impressions, lost one position |
| `/festivals` | 238 → 250 | 26.5 → 40.7 | 0 → 0 | no clicks in either window |

GSC daily position stayed at 6.0–7.4 on every day of W, so the site has no site-wide rank decay in this window.

## 2. Post-ship scoring (issues closed since 2026-10-13 with a `thesis:` and a `metric:`)

253 issues closed in the window carry a thesis and a metric. Most are greps, counts or "event appears", which need no analyst score. **47** mention a traffic or funnel term.

**A window is clean only if its start on or after the deploy.** Today's window starts 2026-10-28. Only the three issues deployed on or before 2026-10-27 have a clean window, and all three were scored once, on 2026-11-13 and 2026-11-14. **Nothing was re-posted.**

### Scored (verdicts unchanged, not re-posted)

| issue | thesis | predicted | actual, clean window | verdict |
|---|---|---|---|---|
| **#311** (PR #334, 2026-10-13) | title/meta rewrite on four band pages lifts CTR | ≥ 1.5% on ≥ 1,500 impressions | 0.937% (53 / 5,658), W 2026-10-14 → 11-10 | **MISS**: bar missed by 0.56 pp |
| **#276** (PR #342, 2026-10-14) | a dasha CTA after the first section lifts pages per session | ≥ 1.20 on ≥ 20 organic sessions | 1.42 on 55 organic sessions | **BAR MET, not attributable to the CTA**: the page also gained from search |
| **#329** (PR #344, 2026-10-14) | a tool link on the Manglik page lifts pages per session | ≥ 1.30 on ≥ 10 organic sessions | 3 organic sessions, 1.00 | **UNSCOREABLE: 3 vs 10** |

### Posted this run

| issue | what | metric read this run |
|---|---|---|
| **#1070** | **pending note, new this run.** Scoreable from 2026-12-25 (last slice PR #1446, 2026-11-24). **Blocked**: `measurements/ga4-journeys.json` does not exist and nothing writes it (see §9, #1534) | `ga4-events.json` `journey_events`: tool_submitted 49, kundli_generated 51, ask_answered 124, matching_completed 5, muhurat_searched 6, dosha_check_completed 3, numerology_completed 0 (these last four since 2026-11-18, partial history), subscribe_completed 1 |

### Met on this run's files (no new post)

| issue | metric | this run |
|---|---|---|
| #1277 (MET, posted 2026-11-21) | `returning.user_days` non-null; `admin_sessions` 0 on every day from 2026-11-12 | `returning.user_days` = **91**, `share_pct` 12.3, status ok; `admin_sessions` **0 on all 13 days** 2026-11-12 → 11-24. Still met |
| #1115 / #1205 (MET, posted 2026-11-20 and 11-26) | report carries GA4 sessions and users for two windows | `ga4-trend.json` is present with W and P. Still met |

### Pending, one note each, a timer for each (24 lines in `/tmp/analyst-timers.txt`)

| issue | window opens | thesis, in brief |
|---|---|---|
| #553 | 2026-12-01 | pages per session on panch-mahapurush-yoga |
| #426 | 2026-12-03 | guard only: sade-sati position and impressions hold |
| #570, #685, #508 | 2026-12-04 | `cta_click` export; sade-sati title CTR; `/matching` title CTR |
| #518 | 2026-12-07 | tool routes on `/learn` articles lift pages per session |
| #528 | 2026-12-10 | no `q=` landing rows in GA4 |
| #735 | 2026-12-12 | no `/admin` landings |
| #835 | 2026-12-14 | debilitated-sun "which sign" clicks |
| #1075, #1073, #1074 | 2026-12-17 | Rahu–Ketu effects/remedies; Jupiter-10th long tail; dated panchang CTR |
| #1072, #1071, #1068 | 2026-12-18 | mahadasha-for-career; gochar-2027 (the main metric is **2027-02-28**); kundli ratio |
| #1217, #1226, #1229 | 2026-12-19 | completion events and `tool_submitted` |
| #1322, #1325, #1336 | 2026-12-22 | muhurat finder bounce, position, shared URLs |
| #1416, #1411 | 2026-12-24 | `tool_error` events deliver |
| #1070 | 2026-12-25 | funnel completion export (blocked) |

**Reference reads from this run, not scores (each window still contains its deploy):**

| issue | read | caution |
|---|---|---|
| #508 `/matching` | position **10.2**, 115 impressions, 3 clicks | the metric's own guard is position within ±1.5 of 4.3. The page is outside it, so the first clean window will probably read **INCONCLUSIVE on position, not a CTR result**. Cause of the fall is #1076's |
| #835 `debilitated-sun-career` | CTR 0.66% on 2,738, position 6.4 | edit merged 2026-11-13, and a second edit (#1389) on 2026-11-22. Google last crawled it 2026-11-16, **before** the latest edit |
| #1074 dated panchang URLs | 37 URLs, **118 impressions**, 2 clicks in W (P: 66) | the floor is ≥ 150 impressions. It is likely unscoreable at this traffic, and I will post "unscoreable" once if the first clean window stays under 150 |
| #1071 gochar-2027 | the page is **"Discovered - currently not indexed"** 10 days after its deploy, with no GSC row | the main metric is not reachable until it is indexed |

## 3. Confounds

| confound | state |
|---|---|
| Concurrent ships | `git log origin/main --since=2026-10-28` lists **592 commits**. 41 mention learn, title, meta or SEO. They include title/meta (#690, #696, #796, #1202), answer-first ledes (#835, #1075, #1073, #1072, #1440), tool routes (#615, #658, #680, #754), gochar date rewrites (#1099, #1125, #1148), and, on 2026-11-27, price-and-motive removals on 12+ `/learn` pages (#1526, #1532). The last two fall **after** W. **A delta on any band page cannot be attributed to one of them** |
| Seasonality | Dhanteras 2026-11-06, Diwali 2026-11-08 and Chhath 2026-11-15 fall in W. No top-10 page is a festival page. `gochar-2026` is time-bound and supplies 3,441 of the +18,021 page-row impression gain (19%). **No year-earlier window exists**, so the seasonal share is not determined |
| Page reachable | production `/health` ok. A `curl` render check this run of `chronic-health-issues-kundli`, `financial-struggles` and `gochar-2026`: HTTP 200 in 0.7 s, 3,438–4,439 words, 14–18 `<h2>`. Not broken. The LLM path has 0 fallbacks (§5). `verify-production` had 1 failure and 3 cancelled in the last 30 runs, all at 2026-11-25 14:09–14:33Z, and 26 successes |
| Sample size | ~834 sessions in 28 days. Pages with ≤ 20 sessions carry no per-page conclusion |
| Index lag | 172 of 214 sitemap URLs are flagged changed after Google's last crawl (§7). A title edit Google has not re-fetched cannot have moved CTR |

## 4. Lever 1 — Growth (W vs P)

| metric | W | P | change |
|---|---:|---:|---:|
| GA4 sessions | 834 | 438 | +90.4% |
| GA4 active users (not summable across channels) | 692 | 336 | +106.0% |
| GA4 new users | 684 | 325 | +110.5% |
| Engaged sessions | 359 (43%) | 196 (45%) | +83.2% |
| Engagement time per session | 122 s | 84 s | +45% (total +175.5%) |
| GSC clicks (page rows) | 445 | 153 | +190.8% |
| GSC impressions (page rows) | 31,974 | 13,953 | +129.2% |
| GSC CTR | 1.39% | 1.10% | +0.3 pp |
| Returning user-days (`ga4-daily.json`, status ok; user-days, not people) | 91 (12.3%) | not measured | – |

| channel (GA4, W vs P) | sessions | engaged | read |
|---|---|---|---|
| Organic Search | 542 vs 210 (+158.1%) | 304 vs 113 (56% engaged) | carries the growth |
| Direct | 287 vs 203 (+41.4%) | 54 vs 71 (**19% engaged**, fell −23.9%) | the weakest cohort; #1364 is open and there is no cohort file in this run, so the automated share is **not determined** |
| AI Assistant | **5 vs 19 (−73.7%)** | 1 vs 11 | the only channel that went the wrong way; small numbers, cause not determined |
| Unassigned | 1 vs 7 | 0 vs 1 | noise |

**Which page group drives it (GSC page rows, impressions P → W, clicks P → W):**

| group | impressions | clicks |
|---|---|---|
| `/learn/*` | 12,612 → 29,880 | 127 → 387 |
| `/muhurat/*` | 169 → 682 | 11 → 29 |
| `/rashifal*` | 156 → 166 | 0 → 1 |
| `/panchang*` | 66 → 118 | 1 → 2 |
| other | 950 → 1,128 | 14 → 26 |

Top gainers by impressions: `gochar-2026` +3,441 (234 → 3,675), `jupiter-in-10th` +1,907, `7th-lord` +1,507, `planets-in-7th` +1,247, `debilitated-sun` +1,085, `career-during-sade-sati` +854. **Structural vs seasonal:** mostly a wider ranking footprint on articles at similar position, with `gochar-2026` the one time-bound exception.

**Daily shape (W).** GSC impressions ran 1,295–1,433 per day on 2026-11-09 → 11-14, fell to 798–908 on 11-16 → 11-19, and recovered to 1,260 on 11-23 and 1,594 on 11-24. The first half of W had 15,656 impressions and 200 clicks, and the second half 16,235 and 245. GA4 sessions were 399 in the first half and 439 in the second. The cause of the dip is **not determined**: it is either a re-rank or late GSC data, and position held at 6.0–7.4 throughout. Discover is **0 clicks and 0 impressions on all 28 days**, so none of this is Discover.

**Every day in `spikes` and `watch`, with its source (`ga4-anomalies.json`):**

| date | users (median 22) | tier | source | engagement | classification |
|---|---:|---|---|---|---|
| 2026-11-06 | 57 | spike | Direct, `/rashifal/aries`, `/r/zzzzzz`, `/numerology`; desktop, US | 19 of 50 sessions had **zero** engagement | **MIXED: part automated** (not growth); the rest are organic readers on `rahu-mahadasha-career-problems` |
| 2026-11-15 | 51 | spike | google / organic `rahu-mahadasha-ketu-antardasha` 6 sessions at 83% engaged; Direct `/panchang/2026-12-02` 5 sessions at 0%; Direct `/kundli` 3 at 0% | mixed | **MIXED**: real organic readers on mobile in India, plus short Direct sessions. GSC clicks that day were 14 and Discover was 0, so the "usually Discover" hint does not apply |
| 2026-11-10 | 40 | watch | Direct `/matching`, `/numerology`; bing organic `/numerology` 4 sessions at 0% | 21 of 35 sessions had zero engagement | **automated-looking** (desktop, US) |
| 2026-11-23 | 38 | watch | google / organic `/muhurat/griha-pravesh` and `/learn/*` | real readers | organic. GSC clicks were **36**, the highest day of W |
| 2026-11-24 | 37 | watch | google / organic `chronic-health-issues-kundli` 5 sessions, `jupiter-in-10th` 4 | real readers | organic. GSC clicks 22 |
| 2026-11-12 | 34 | watch | google / organic `/muhurat/griha-pravesh` 4 sessions at 100% | real readers | organic. GSC clicks 24 |
| 2026-11-09 | 32 | watch | google / organic `jupiter-in-10th`, `rahu-ketu`, `griha-pravesh` 5 each | real readers | organic. Includes 2 sessions on `/admin/ops` (before the #735 fix) |
| 2026-11-14 | 32 | watch | google / organic `rahu-mahadasha-ketu-antardasha` 10 sessions | real readers | organic. GSC clicks 23 |

**`admin_sessions`.** There were 8 sessions in W, all **before** 2026-11-12: 1 on 10-28, 2 on 11-04, 3 on 11-05 and 2 on 11-09. They were **0 on every day from 2026-11-12 to 11-24**. There is **no internal-traffic leak and nothing to file**.

## 5. Lever 2 — Where time is spent (`verify-first.json`, `ga4.json`, W)

| landing (query strings folded) | sessions | engaged rate | engagement per session | pages per session | GSC impressions · position |
|---|---:|---:|---:|---:|---|
| `/learn/rahu-mahadasha-ketu-antardasha` | 69 | 58% | 126 s | 1.57 | 3,077 · 6.5 |
| `/` | 59 | 58% | **266 s** | **4.49** | 216 · 5.7 |
| `/learn/gochar-2026-planetary-transits` | 46 | **39%** | **24 s** | 1.15 | 3,675 · 4.8 |
| `/muhurat/griha-pravesh` | 32 | **88%** | 94 s | 2.53 | 571 · 6.4 |
| `/learn/jupiter-in-10th-house-career` | 32 | 38% | 50 s | 1.25 | 2,379 · 6.9 |
| `/learn/7th-lord-placement-marriage-guide` | 32 | 38% | 50 s | 1.09 | 1,827 · 7.0 |
| `/learn/career-during-sade-sati` | 30 | 50% | 237 s | 1.97 | 1,396 · 5.4 |
| `/learn/rahu-mahadasha-career-problems` | 30 | 47% | 233 s | 2.23 | 1,219 · 5.6 |
| `/learn/10th-lord-in-6th-house-career` | 27 | 70% | 187 s | 2.48 | 799 · 7.1 |
| `/learn/chronic-health-issues-kundli` | 27 | **22%** | **18 s** | 1.04 | 556 · 4.6 |

- Best-engaged organic page is the tool landing `/muhurat/griha-pravesh` (88% engaged). The homepage holds the longest stays and the most pages per session.
- The shortest stays sit on top-10 impression pages: `gochar-2026` (24 s), `jupiter-in-10th` and `7th-lord` (50 s), and `chronic-health-issues-kundli` (18 s at position 4.6). These pages are being found and not read.
- `/learn/financial-struggles` had 11 sessions, all Direct, 0 engaged and 3 s in total.
- The render check found these pages are not broken. Whether the visitors are bad-intent or the page is poorly framed is **not determined**; it needs the landing × event export (§9, #1534).

**Tool funnels visible in GA4 (W, `ga4-events.json`).**

| step | count |
|---|---:|
| `form_start` | 98 |
| `kundli_generated` | 51 |
| `tool_submitted` | 49 |
| `ask_answered` | 124 |
| `cta_click` (partial history from 2026-11-03) | 25 (3.0% of 834 sessions); 17 with a named from/to, 8 `(not set)` |
| `matching_completed` / `muhurat_searched` / `dosha_check_completed` (since 2026-11-18) | 5 / 6 / 3 |
| `numerology_completed` (since 2026-11-18) | **0** |
| `subscribe_completed` | 1 |

`form_start` 98 → `kundli_generated` 51 is about 52%, the only ratio the file supports, and `form_start` is not split by tool. **Kundli server-side ratio:** not computable, same as the note on #1068 from 2026-11-26. The GA4 window starts 10-28, which is before the collector's `window.from` (2026-10-31), and only 3 of its 28 days (11-03, 11-08, 11-24) are in `non_probe_dates`. Nothing is divided, and `totals.fresh_generations` (41) is not compared to GA4.

## 6. Lever 3 — Errors

| source | read |
|---|---|
| `llm-usage.json` (7 days ending at generation, 2026-11-27) | 151 calls, 110 cache hits (**72%**), **0 fallbacks**, 132,930 input and 24,048 output tokens. Peak measured day 2026-11-23: 42,994 tokens, about 21% of the 200,000 TPD ceiling |
| `natal` | 85 calls, 76 hits (89%), 6,646 tokens per call on 9 measured calls |
| `ask` | 22 calls, 0 hits, 2,453 tokens per call (22 measured) |
| `rashifal` | 28 calls, 100% hits, tokens **not measured** |
| `today` / `matching` / `monthly` | 9 calls, 44% hits / 4 calls, 0% / 3 calls, 66% |
| `verify-production.yml`, last 30 runs | 26 success, 3 cancelled, 1 failure, all non-success runs within 2026-11-25 14:09–14:33Z. #1506 attributes the failure to the deploy gate, not a page error |
| HTTP 5xx per non-LLM route | **not measured** → **#1506 open** |

No route has errors or fallbacks in this window. Issue #925 ("peak day used 83% of the Groq daily budget") is still open and **I did not re-measure the figure it cites**; this run's peak day is 21%.

## 7. Lever 6 — Index status (`index-status.json`, generated 2026-11-27T03:50Z, 214 sitemap URLs)

| state | URLs |
|---|---:|
| submitted and indexed | 165 |
| crawled, currently not indexed | 27 |
| discovered, currently not indexed | 21 |
| unknown to Google | 1 |
| flagged changed after Google's last crawl (`stale`) | 172 |

Not indexed, by type: 27 `/learn`, 18 `/panchang`, 2 `/muhurat`, 1 `/dasha`, 1 `/hi`.

**Ranked by value (impressions in W):**

| page | state | impressions | why it matters |
|---|---|---:|---|
| `/learn/debilitated-sun-career/` | edited 2026-11-22, last crawled 11-16 | 2,738 | the largest CTR gap; `request_indexing` list |
| `/learn/sade-sati/` | edited 11-26, last crawled 11-20 | 1,949 | #685's page |
| `/learn/7th-lord-placement-marriage-guide/` | edited 11-24, last crawled 11-23 | 1,827 | |
| `/learn/planets-in-7th-house-marriage/` | edited 11-26, last crawled 11-25 | 1,634 | |
| `/learn/career-during-sade-sati/` | edited 11-27, last crawled 11-23 | 1,396 | |
| `/learn/rahu-mahadasha-career-problems/` | edited 11-27, last crawled **11-11** | 1,219 | 16 days stale |
| `/muhurat/griha-pravesh` | edited 11-26, last crawled **11-08** | 571 | the best-engaged organic landing |
| `/learn/ashwini-nakshatra/` | crawled, not indexed | 70 | top not-indexed page by impressions |
| `/learn/gochar-2027-planetary-transits/` | **discovered, not indexed** | 0 | time-bound; #1071's metric needs it indexed |
| `/learn/vivah-muhurat-2027/`, `/learn/griha-pravesh-muhurat-2026-2027/` | crawled, not indexed (last crawl 2026-10-01 and 2026-08-09) | 18 and 11 | wedding and housewarming season pages that Google has seen and declined to index |

Tracked by #1065, whose `request_indexing` list already names these ten.

## 8. Lever 4 — Search demand, and Lever 5 — Content opportunities

### Search demand
Coverage: the query dimension is 14% of W impressions (1,011 query keys now, 307 in P), so these are themes, not totals. This run had no `--by query-page` file, so I name a page only where the query's topic matches an existing page. **I name no page that would be new.**

| theme (query, W) | impressions (P) | position | existing page |
|---|---|---|---|
| "sun debilitated in which sign" and variants | 307 (76) + 150 (25) | 7.1; 6.1 | `debilitated-sun-career` (#835) |
| "sun debilitation degree" | 60 (0) | 6.5 | same page; whether its text answers the query is **not determined** |
| "jupiter in 10th house", "guru in 10th house" | 140 (18), 98 (7) | 10.2; 8.7 | `jupiter-in-10th-house-career` (#1073) |
| "which mahadasha is best for career" | 68 (0) | 8.4 | `vimshottari-dasha-explained` (#1072) |
| Rahu–Ketu antardasha cluster | 324 plus about 10 variants | 6.4–10.6 | `rahu-mahadasha-ketu-antardasha`, the best-converting page (#1075) |
| "7th lord in 12th house love or arranged marriage" | 25 (0) | 6.2 | `7th-lord-placement-marriage-guide` |

- The 7th-house pair (`7th-lord-placement-marriage-guide`, 1,827 impressions, and `planets-in-7th-house-marriage`, 1,634) share a theme and one lost position. No cannibalisation is proven by this export.
- `yes` shows 125 impressions at 3.9 as a query with no clear page; it is not a content opportunity.
- `/matching` fell to position 10.2 on 115 impressions (§1).

### Content opportunities (`festival_registry.py`, read this run; dates are the registry's and I did not independently verify them)

| date | festival (registry slug) | `/learn` article |
|---|---|---|
| 2026-12-01 | kalabhairav-jayanti | none found by `learn_article_for` |
| 2026-12-14 | vivah-panchami | none |
| 2026-12-20 | gita-jayanti | none |
| 2026-12-23 | dattatreya-jayanti | none |
| 2027-01-15 | makar-sankranti, pongal | none |

- Existing time-bound pages are `vivah-muhurat-2027`, `griha-pravesh-muhurat-2026-2027` (both crawled and not indexed, §7), `gochar-2027` (not indexed) and `diwali-muhurat-2026` and `karva-chauth-2026` (past; 72 and 7 impressions in W).
- Annual page whose year is ending: **`gochar-2026`** (3,675 impressions at 4.8, the top page). Its 2027 sibling is live and not indexed, so the handover is at risk.
- I name the demand and the existing pages. Whether to build any of these is product-manager's call.

## 9. Lever 7 — Measurement gaps against my last three reports (2026-11-24, 11-25, 11-26)

| gap | in each of the last three? | this run | open issue |
|---|---|---|---|
| HTTP 5xx per route | yes | not measured | **#1506** |
| Per-page × per-day export (`/matching` fall, band-page deploy splits) | yes | not in this run's inputs | #953, #1076, #490 |
| Share of Direct that is automated (`--cohorts`) | yes | no file | #1364 |
| Query → page map (`--by query-page`) | yes | no file | #1432, #1437 |
| `page_location` query strings in GA4 | yes | not read | #1237 |
| **Short-stay landings: broken, bad-intent or unrouted?** (`chronic-health-issues-kundli`, 8 s → 18 s) | yes: render check and scroll depth wanted in all three | render check done this run (not broken). Intent unresolved | **#1534, filed this run** |
| GA4 previous window | resolved | `ga4-trend.json` present | #1205 closed |

**Filed this run:** **#1534** — `agent-measure.yml` has 0 `--journeys` steps (`grep -c -e "--journeys"` → 0), so `measurements/ga4-journeys.json`, which #1070's own metric names, has never been written. Without a landing × event export the short-stay pages cannot be classed. The evidence-block fields are all filled.

## 10. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| Whether the objective (ten highest-impression queries into the top 5) is moving | not recoverable while 86% of impressions are withheld. The page proxy is 1 of 10 at ≤ 5.0 |
| How much of Direct (287 sessions, 19% engaged) is automated | the `--cohorts` file (#1364) |
| Why `/matching` lost 5.8 positions (4.4 → 10.2) | per-page × per-day export (#953, #1076) |
| Why AI Assistant referrals fell from 19 to 5 sessions | a daily landing × source export |
| Whether the 11-16 → 11-19 impressions dip was a re-rank | the next runs' daily rows |
| Whether low-engagement landings are bad-intent or badly framed | landing × event export (#1534) |
| HTTP 5xx per non-LLM route | request log or counter (#1506) |
| Which page serves each visible query | the `query-page` export file (#1432, #1437) |
| The 4-session gap between `ga4-daily.json` (838) and the trend file (834) | not investigated; the two exports may differ in definition |

## 11. Handed back

| item | value |
|---|---|
| Issue filed | **#1534** (no landing × event export; `--journeys` never run by `agent-measure`) |
| Comment posted | **#1070**, pending note, scoreable 2026-12-25 and blocked on #1534 |
| Verdicts unchanged and not re-posted | #311 MISS, #276 BAR MET not attributable, #329 UNSCOREABLE, #1277 MET, #1115 MET |
| Timers | 24 lines in `/tmp/analyst-timers.txt`, #553 (12-01) through #1070 (12-25); #528 and #1068 are included although last report's list omitted them |
| Read-only | no code, template, content or `BACKLOG.md` change |
