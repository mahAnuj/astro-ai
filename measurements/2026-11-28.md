# Analyst report — 2026-11-28

Everything below was read this run from `/tmp/*.json`, `/tmp/measure/*.json`, `gh`, `git` and the checkout (`festival_registry.py`, `fetch_index_status.py`). What I did not read is marked **not measured**.

**Windows.** **W** = 2026-10-29 → 2026-11-25 (28 days, last 3 excluded). **P** = 2026-10-01 → 2026-10-28, the 28 days before (`window_prev` in both trend files). The index capture is `/tmp/measure/index-status.json`, generated 2026-11-28T03:26Z.

**Coverage.** GSC `dimension: page` is 100% of the property's 32,592 W impressions (page rows sum to 32,680), not truncated. GA4 landing × channel is 100% of 848 sessions, not truncated. GSC `dimension: query` is **14%** of W impressions (a partial view; Google withholds the rest), so I draw no whole-site conclusion from it. Band export: 100 rows printed, 23,419 impressions = **72%** (`emitted_coverage_pct`).

## 0. The one number to read first

| | W | P | change |
|---|---:|---:|---:|
| GA4 sessions | 848 | 456 | **+86.0%** |
| GA4 active users (not summable across channels) | 703 | 349 | +101.4% |
| GA4 Organic Search sessions | 555 | 224 | +147.8% |
| GSC impressions (page rows) | 32,680 | 14,662 | +122.9% |
| GSC clicks | 454 | 158 | +187.3% |
| GSC CTR (clicks / page-row impressions) | 1.39% | 1.08% | +0.31 pp |

Organic Search supplies 331 of the 392 added sessions. The growth is real and carried by `/learn` articles. It did **not** come from rank: **1 of the top-10 pages by impressions is at position ≤ 5.0** (`gochar-2026`, 4.7); the rest sit at 5.4 to 7.2 (`gsc-all.json`, W). Impressions rose because more pages were shown, not because the band pages climbed.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md says to move the 6–20 band into the top 5 on the ten highest-impression queries. **Not measurable as worded**: the query export sees 14% of impressions, so the ten top queries cannot be named. The page proxy is the only readable figure.

| band, GSC page mode, W | value |
|---|---|
| pages at average position 6–20 (`gsc-all.json`) | 101 pages, 23,900 impressions (73% of page-row impressions) |
| printed band list (`gsc-band.json`) | 100 pages, 23,419 impressions, 313 clicks (CTR 1.34%) |
| band pages with ≥ 200 impressions | 22 |
| band median CTR (28 pages with ≥ 100 impressions) | **1.275%** |
| pages at position ≤ 5 | 21 pages, 4,606 impressions |
| top-10 pages by impressions at position ≤ 5.0 | **1 of 10** |

Ranked by the file's `band_opportunity`; "gap" is my arithmetic: impressions × 1.275% minus actual clicks (a ceiling, not a forecast).

| # | page (W) | impr | clicks | CTR | pos | `band_opportunity` | gap at band median | pending ship on it |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | /learn/debilitated-sun-career/ | 2,656 | 17 | **0.64%** | 6.4 | 142.4 | +16.9 | #835, scoreable 2026-12-14 |
| 2 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,984 | 55 | 1.84% | 6.6 | 124.0 | above median; rank is the lever | #1075, 12-17 |
| 3 | /learn/jupiter-in-10th-house-career/ | 2,471 | 29 | 1.17% | 6.9 | 119.3 | +2.5 | #1073, 12-17 |
| 4 | /learn/sade-sati/ | 1,959 | 17 | **0.87%** | 6.9 | 100.5 | +8.0 | #685, 12-04 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,978 | 23 | 1.16% | 7.0 | 95.7 | +2.2 | none |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,755 | 16 | **0.91%** | 6.7 | 89.3 | +6.4 | none |
| 7 | /learn/panch-mahapurush-yoga/ | 1,159 | 16 | 1.38% | 7.2 | 53.5 | above median | #553, 12-01 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 656 | 3 | **0.46%** | 7.7 | 36.4 | +5.4 | none |
| 9 | /learn/saturn-in-10th-house-career/ | 600 | 9 | 1.50% | 7.3 | 27.0 | above median | none |
| 10 | /learn/manglik-dosh/ | 480 | 4 | 0.83% | 6.8 | 24.8 | +2.1 | none (#329 unscoreable) |

Other CTR gaps on the band list: shukra-venus 433 impr / 2 clicks (0.46%, +3.5), rahu-in-vedic-astrology 311 / 1 (0.32%, +3.0), guru-jupiter 234 / 0 (+3.0), vimshottari-dasha-explained 438 / 3 (0.68%, +2.6).

## 2. CTR outliers and decay

| finding | evidence (GSC page mode) | comparison that makes it a finding |
|---|---|---|
| **gochar-2026: top page, worst CTR for its position** | W: 3,827 impr, 28 clicks, **0.73%** at 4.7. P: 311 impr, 3 clicks, 5.8 | `chronic-health-issues-kundli` 551 impr at 4.6 got **3.27%**; `career-during-sade-sati` 1,395 at 5.4 got 1.94%. At the band's 1.275% gochar would have ~49 clicks, not 28. GA4: 44 sessions, 16 engaged, 25 s. Title/snippet-shaped, and the page is year-bound (§9) |
| **/matching decay** | impr 346 → **111**, position 4.4 → **10.3**, clicks 1 → 3 (P → W). GA4 W: 12 sessions, 1 engaged | **Confounded:** #508 shortened its title on 2026-11-03 (PR #696), inside W. Index capture: indexed, but changed 2026-11-27 after Google's 2026-11-22 crawl. Cause **not determined**; #508's guard (position within ±1.5 of 4.3) is already outside, so a pass on #508 is impossible on position |
| /festivals | position 28.1 → 40.7, 237 impr, 0 clicks | below the band; decay of a page that never ranked |
| Nakshatra pages | `pushya-nakshatra` 156 → 37 impr, `rohini-nakshatra` 48 → 23, `ashwini-nakshatra` 67 now | all three are **"Crawled - currently not indexed"** in the capture. A link between losing impressions and losing the index is plausible and **not shown**: this run has one capture, not two |
| vimshottari-dasha-explained, magha-nakshatra | position 5.6 → 7.7 and 6.3 → 8.3 | impressions **rose** 72 → 438 and 26 → 194; a wider footprint, not decay |

Pages new in W: 34; pages gone: 25 (`gsc-trend-page.json`).

## 3. Scores — issues closed in the last 45 days with a `thesis:` and a `metric:`

263 closed issues since 2026-10-14 carry both. Clean window = deploy on or before 2026-10-28 (start of W is 10-29). **Only #311, #276, #329 and #515 are older than that**; each already has its one verdict. Nothing else is scoreable today, so nothing is re-posted.

| issue | verdict | basis | action this run |
|---|---|---|---|
| #311 | **MISS** | four pages CTR 0.937% against ≥ 1.5% (W 2026-10-14 → 11-10), read on the issue | none (posted 2026-11-13) |
| #276 | **BAR MET, not attributable to the CTA** | 1.42 pages/session vs ≥ 1.20 on 55 organic sessions; other `/learn` organic landings 1.58 | none (posted 2026-11-14) |
| #329 | **UNSCOREABLE at this traffic: 3 vs 10** | organic sessions on `/learn/manglik-dosh/` | none (posted 2026-11-14); the page's sessions in this run's W are not re-scored |
| #515 | unscoreable at this traffic | 1 organic session on `/rashifal*` | none (posted 2026-11-09) |
| #1326 | **partially met** (structural count) | registry holds 5 festivals 2026-11-22 → 2027-01-14 (0 before). Nov 1, Dec 4, **Jan 1–14: 0**; Makar Sankranti and Pongal are 2027-01-15, one day outside | **posted on #1326 this run** |
| #1469 | premise no longer true | `muhurat_searched` = 9 events since 2026-11-18 in `ga4-events.json` | **posted on #1469 this run** |

**Misses, stated plainly.** #311 missed its bar by 0.56 pp. #329 never reached a sample. #276 cleared its bar, but the page also gained from search and trails the `/learn` average, so the CTA is not shown to work. #508's `/matching` thesis is already contradicted on position (4.4 → 10.3, §2). The two largest CTR gaps on the site (debilitated-sun 0.64%, sade-sati 0.87%) have shipped edits (#835, #685) that are **not yet scoreable**, and Google's crawl is older than the edits (§10).

**Pending, one timer each** (all 21 written to `/tmp/analyst-timers.txt` for `timers.py set --from-file`; each issue already carries its one "pending" note, so nothing new was posted):

| issue | due | issue | due | issue | due |
|---|---|---|---|---|---|
| #553 | 2026-12-01 | #835 | 12-14 | #1325 | 12-22 |
| #426 | 12-03 | #1073, #1075, #1074 | 12-17 | #1322, #1336 | 12-22 |
| #685, #508 | 12-04 | #1072, #1071, #1175, #1068 | 12-18 | #1416, #1411 | 12-24 |
| #518 | 12-07 | | | #1070 | 12-25 |
| #528 | 12-10 | | | | |
| #735 | 12-12 | | | | |

Two caveats on those dates: #1071's own metric (≥ 300 impressions for `gochar-2027` in the window ending 2027-02-25) is not readable until about 2027-02-28; the 12-18 timer scores only its guard. #1070 is blocked on `ga4-journeys.json`, which nothing writes (#1534, open).

Not scoreable from GA4 or GSC (structural counts): #1546, #1341, #1409, #1436 (scored on #1432), #1176, #1177, #1178, #843. I posted nothing on those this run.

## 4. Confounds, before any delta above

| confound | what I read | consequence |
|---|---|---|
| Concurrent ships | `git log origin/main --since=2026-10-29` lists **606 commits**. Dozens touch `/learn` copy (grounding rewrites, claim removals), titles/descriptions (#690, #696, #1202), answer-first ledes (#835, #1075, #1073, #1072), tool routes (#615, #658, #680, #754), muhurat rules (many), and on 2026-11-26/27 price-and-motive removals on 12+ `/learn` pages (#1526, #1532) | a delta on any band page **cannot be attributed to one ship** |
| Seasonality | registry: Dhanteras 2026-11-06, Diwali 2026-11-08 fall in W. No top-10 page is a festival page, except that `gochar-2026` is year-bound | no year-earlier window exists; the seasonal share is **not determined** |
| Index lag | 172 of 214 sitemap URLs are flagged changed after Google's last crawl (§10) | a title or lede edit Google has not re-fetched cannot have moved CTR yet |
| Page reachable? | `verify-production` last 300 runs (2026-11-08T07:05Z → 11-28T03:10Z): 280 success, 10 failure, 10 cancelled; last failure 2026-11-25T14:33Z; every run since 2026-11-26T20:12Z succeeded (§7) | traffic in W was served; failure causes not read |
| Sample size | most single pages have under 30 sessions | per-page GA4 deltas are noise; GSC page rows are the readable signal |
| Automated traffic | two spikes and one watch day are partly automated (§5) | session counts overstate readers on those days; the Direct channel is the weakest cohort |

## 5. Lever 1 — Growth

**Against the previous window (GA4 trend, W vs P).**

| channel | sessions W / P | engaged sessions W / P | engaged rate W / P |
|---|---|---|---|
| Organic Search | 555 / 224 (+147.8%) | 318 / 113 | 57.3% / 50.4% |
| Direct | 288 / 206 (+39.8%) | 55 / 71 (**−22.5%**) | **19.1%** / 34.5% |
| AI Assistant | 5 / 20 (**−75.0%**) | 0 / 12 | 0% / 60% |
| Unassigned | 1 / 7 | 0 / 1 | – |
| **all** | 848 / 456 (+86.0%) | 374 / 197 | 44.1% / 43.2% |

Engagement: 100,171 s in W vs 40,768 s in P = 118 s per session vs 89 s. Direct added 82 sessions and lost 16 engaged ones: the weakest cohort, and its automated share is **not determined** (#1364, no cohort file in this run). AI Assistant fell from 20 to 5 sessions: small numbers, cause not determined.

**Which page groups drive it (GSC page rows, W vs P).**

| group | impressions W / P | clicks W / P | pages in W |
|---|---|---|---:|
| `/learn/*` | 30,590 / 13,419 | 392 / 132 | 77 |
| `/muhurat*` | 781 / 173 | 31 / 11 | 5 |
| `/numerology*` | 215 / 0 | 10 / 0 | 2 |
| `/festivals` | 237 / 249 | 0 / 0 | 1 |
| `/` | 215 / 136 | 9 / 9 | 1 |
| `/matching` | 111 / 346 | 3 / 1 | 1 |
| `/panchang/*` | 136 / 68 | 2 / 1 | 53 |

`/learn` is 93.6% of impressions; the ten largest articles are 65.5% of impressions and 251 of 454 clicks. Biggest risers by impressions: gochar-2026 (311 → 3,827), jupiter-in-10th (561 → 2,471), 7th-lord (354 → 1,978), planets-in-7th (382 → 1,755), debilitated-sun (1,752 → 2,656), career-during-sade-sati (574 → 1,395). **Structural or seasonal:** the gain is mostly a wider ranking footprint at similar position, with one time-bound exception: gochar-2026 is +3,516 of the +18,018 page-row impression gain (19.5%). A split into seasonal and structural is **not determined** (no year-earlier window).

**Daily shape.** GSC impressions: 16,070 in the first 14 days of W, 16,522 in the second; clicks 220 and 234. GA4 sessions: 405 and 446. Impressions dipped to 798–908 per day on 2026-11-16 → 11-19 (position stayed 6.0–7.4) and recovered to 1,594 and 1,720 on 11-24 and 11-25. Cause of the dip **not determined** (re-rank or late GSC data).

**Every day in `spikes` and `watch`, with its source** (`ga4-anomalies.json`; GSC clicks from `gsc-daily.json`; Discover is **0 clicks and 0 impressions on all 28 days**, so none of this is Discover):

| date | tier | active users (median 23) | source, from the file | GSC clicks that day | read |
|---|---|---:|---|---:|---|
| 2026-11-06 | spike | 57 | direct, landing `/rashifal/aries` 6 sessions; **19 of 50 sessions zero engagement** ((not set) desktop US 10, Chrome desktop US 6, Chrome mobile US 3) | 17 | **part automated** (38% of sessions); not growth |
| 2026-11-15 | spike | 51 | google/organic, `rahu-mahadasha-ketu-antardasha` 6 sessions (83% engaged); Direct `/panchang/2026-12-02` 5 sessions, 0 engaged, 1.6 s; Chrome **mobile China 9 sessions, 0% engaged**; Chrome mobile India 17 sessions, 59% engaged | 14 | **mixed**: real India mobile readers plus a zero-engagement cohort that looks automated. The file's own text says "looks like real readers"; the by-tech rows say otherwise for 9 sessions. Not Discover (0) |
| 2026-11-10 | watch | 40 | direct, `/matching` 5 sessions, 0 engaged; **21 of 35 sessions zero engagement** ((not set) desktop US 9, Chrome desktop US 8) | 14 | **automated-looking**; not growth |
| 2026-11-12 | watch | 34 | google/organic, `/muhurat/griha-pravesh` 4 sessions (100% engaged); Chrome mobile India 14 (71% engaged) | 24 | real search traffic |
| 2026-11-23 | watch | 38 | google/organic, griha-pravesh 4, jupiter-10th 3, planets-in-7th 3; Chrome mobile India 18 | **36** (highest of W; the other 27 days ran 8–27) | real search traffic; the strongest click day |
| 2026-11-24 | watch | 37 | google/organic, `chronic-health-issues-kundli` 5 (40% engaged), jupiter-10th 4; Chrome mobile India 16 | 22 | real, with a short-stay landing (§6) |

**Returning users** (`ga4-daily.json`, `status: ok`): **90 returning user-days = 12.0%** of daily active users. These are user-days, not people. **Internal-traffic leak (#735):** `admin_sessions` is **0 on every day from 2026-11-12 to 11-25** (14 days). The 7 admin sessions in W fall on 2026-11-04 (2), 11-05 (3) and 11-09 (2), all before the cutoff. No leak; nothing filed.

## 6. Lever 2 — Where time is spent

`verify-first.json` (basis: GA4 engaged sessions, W), joined to GSC:

| landing (GA4 folded) | sessions | engaged | rate | avg engaged s | GSC impr | GSC pos |
|---|---:|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha | 72 | 42 | 58% | 128 | 2,985 | 6.6 |
| / | 61 | 36 | 59% | **265** | 215 | 5.6 |
| /muhurat/griha-pravesh | 37 | 32 | **86%** | 91 | 657 | 6.4 |
| /learn/10th-lord-in-6th-house-career | 26 | 19 | 73% | 194 | 787 | 7.1 |
| /learn/gochar-2026-planetary-transits | 44 | 16 | **36%** | **25** | 3,827 | 4.7 |
| /learn/career-during-sade-sati | 30 | 16 | 53% | 240 | 1,395 | 5.4 |
| /learn/rahu-mahadasha-career-problems | 28 | 15 | 54% | 252 | 1,226 | 5.7 |
| /learn/jupiter-in-10th-house-career | 34 | 13 | 38% | 71 | 2,471 | 6.9 |
| /learn/7th-lord-placement-marriage-guide | 36 | 13 | **36%** | **47** | 1,978 | 7.0 |
| /learn/sade-sati | 24 | 13 | 54% | 217 | 1,959 | 6.9 |

Pages with the shortest stays: gochar-2026 (25 s), 7th-lord (47 s), `chronic-health-issues-kundli` (28 sessions, 7 engaged, 19 s), `sun-mahadasha` (14 sessions, 3 engaged, 12 s). Two of these are top-5 impression pages. Whether they are bad-intent landings or badly framed is **not determined**; it needs the landing × event export (#1534, open). The tool landings engage best: griha-pravesh 86%, `/` 59%, `/kundli` 22 sessions, 10 engaged, 154 s, 3.0 pages/session. `(not set)` landing: 16 sessions, 0 engaged.

**Funnel and tool events** (`ga4-events.json`, W; 5,336 events): `ask_answered` 123, `form_start` 94, `tool_submitted` 60, `kundli_generated` **52**, `cta_click` **26** (3.1% of 848 sessions; exists only from 2026-11-03), `muhurat_searched` 9, `matching_completed` 5, `dosha_check_completed` 4, `numerology_completed` **0**, `subscribe_completed` **0**. The last five carry `since: 2026-11-18`, so they cover 8 of 28 days. `cta_click`: 8 are `(not set)`; of the named ones, from `/learn/*` to `/` 6, `/kundli` 5, `/sade-sati-check` 3, `/dasha` 2, `/numerology` 1, `/kaal-sarp-check` 1. There is no impression event, so a low click rate cannot be told from low exposure. `form_start` 94 → `kundli_generated` 52 is the only ratio the file supports (~55%), and `form_start` is not split by tool.

**Kundli server-side ratio (#1068): not computable.** The GA4 window is 2026-10-29 → 2026-11-25. `kundli-submissions.json` starts 2026-11-01 and lists only 7 `non_probe_dates` (11-03, 11-08, 11-24 → 11-28), none of which makes the GA4 window whole. I do not divide `fresh_generations` (41) by anything. `numerology_completed` is 0 against 18 `/numerology` landing sessions across all of W; broken versus unused cannot be told (commented on #1469).

**Index state of the pages above (§10)** matters here: Google's crawl is older than the edits on debilitated-sun-career, sade-sati, griha-pravesh and others.

## 7. Lever 3 — Errors

| source | reading | window |
|---|---|---|
| LLM fallbacks | **0**; `fallback_reasons` empty | 2026-11-22 → 11-28 (7 days) |
| HTTP 5xx per route | **0** total, `http_5xx_by_route` empty; **only 1 of 7 days recorded** (`http_5xx_days_recorded: 1`) | same |
| `verify-production` | 280 success, 10 failure, 10 cancelled of the last 300 runs; failures cluster 2026-11-10 → 11-18 and 11-25 14:09 → 14:33Z; **all 20 most recent runs succeeded** (since 2026-11-26T20:12Z) | 2026-11-08T07:05Z → 11-28T03:10Z |

#1506 (HTTP 5xx per route) is closed and the counter now exists, but the zero rests on one recorded day. It becomes a measurement as the days accrue. Failure causes of the 10 `verify-production` failures were **not read** this run; whether an issue tracks them is not determined.

| route | calls | cache hits | hit rate | measured calls | tokens per measured call |
|---|---:|---:|---:|---:|---:|
| natal | 93 | 82 | 88% | 11 | **6,646** |
| rashifal | 28 | 28 | 100% | 0 | not measured |
| ask | 22 | 0 | 0% | 22 | 2,455 |
| today | 10 | 4 | 40% | 6 | 1,919 |
| matching | 5 | 0 | 0% | 5 | 1,839 |
| monthly | 3 | 2 | 66% | 1 | 2,116 |

Total 161 calls, 116 hits (72%), 149,970 input + 27,547 output tokens in 7 days. Peak measured day 2026-11-23: 42,994 tokens (peak across all days by the file's other field: 6,733 on 11-22; the two fields measure different sets, and I do not reconcile them). A natal miss at 6,646 tokens is 83% of one 8,000-token-per-minute model bucket. That is a design fact for the chain, not an error, and not mine to rule on.

## 8. Lever 4 — Search demand

GSC query export, W vs P, coverage **14%** (partial view). Themes by impressions, with the existing page named by topic. **A query-to-page export does not exist** (`--by query-page` exists; no file in this run; #1432 and #1437 open), so a page is named by topic, not measured.

| theme (query regex over the partial export) | queries | impressions W / P | clicks W | existing page | read |
|---|---:|---|---:|---|---|
| sun debilitated | 34 | 945 / 280 | 2 | `debilitated-sun-career` | 0.2% CTR on the partial view; matches the page's CTR gap in §1. "sun debilitation degree" (61 impr, pos 6.4) has a candidate page: its template mentions "10°", but whether the text answers the query is not determined |
| rahu–ketu dasha | 43 | 785 / 680 | 21 | `rahu-mahadasha-ketu-antardasha` | the one theme that converts (2.7%) |
| jupiter / guru in 10th | 60 | 577 / 61 | 1 | `jupiter-in-10th-house-career` | "jupiter in 10th house" 162 impr at **position 10.0**, 0 clicks: the head term is at the foot of page one |
| 7th lord / house | 80 | 279 / 2 | 4 | `7th-lord-placement-marriage-guide`, `planets-in-7th-house-marriage` | two pages share this theme; cannibalisation not measured |
| sade sati / "yelinati" | 85 | 144 / 46 | 0 | `sade-sati`, `career-during-sade-sati` | "does yelinati sani effect my career" 20 impr, pos 7.5 |
| which mahadasha is best for career | 4 | 91 / 1 | 0 | `vimshottari-dasha-explained` (#1072) | 73 impr at pos 8.4, 0 clicks; #1072 pending 12-18 |
| 10th lord in 6th house | 8 | 141 / 44 | 1 | `10th-lord-in-6th-house-career` | |
| "yes" | 1 | 120 / 21 | 0 | none nameable | one-word query at position 3.9; not a theme to act on |

**Queries with no page: not determinable** from this export; I name no new page. Every theme above has an existing page and a pending ship. I flag no new cannibalisation beyond the 7th-house pair. `/matching` fell to position 10.3 (§2).

## 9. Lever 5 — Content opportunities

Dates only from `festival_registry.py` (this checkout). Entries dated 2026-11-28 → 2027-01-23:

| date | registry slug | existing `/learn` article for it | GSC impressions in W |
|---|---|---|---:|
| 2026-12-01 | kalabhairav-jayanti | none (`templates/learn` has no file by that name) | 0 |
| 2026-12-14 | vivah-panchami | none | 0 |
| 2026-12-20 | gita-jayanti | none | 0 |
| 2026-12-23 | dattatreya-jayanti | none | 0 |
| 2027-01-15 | makar-sankranti, pongal | none | 0 |

The registry holds **6 entries in 8 weeks**. It has no entry for any Ekadashi in that window, nor for Lohri (slug search: only `devshayani-ekadashi` and `devuthani-ekadashi` exist). Absence from the registry is not absence from the calendar; I assert no date outside it. Demand is not measured for any of these.

Time-bound pages that exist, with W impressions: `/panchang/2026-12-02` **54** at position 9.1 (not a registry date; the demand reason is not determined), `/panchang/2026-12-11` 12, `/panchang/2026-12-01` 8, `vivah-muhurat-2027` 16 at 9.2 (crawled, not indexed), `diwali-muhurat-2026` 73 at 11.2 (past), `karva-chauth-2026` 6 (past), `griha-pravesh-muhurat-2026-2027` (crawled, not indexed, last crawl 2026-08-09).

**Annual page whose year is ending: `gochar-2026`**: 3,827 impressions at 4.7, the top page, 11.7% of property impressions, with 25 s average engagement. Its 2027 successor (`gochar-2027-planetary-transits`, PR #1148, 2026-11-17) is **"Discovered - currently not indexed"** with 0 impressions and no crawl, 11 days after deploy, and the ranking that picks which URLs to request indexing for cannot list it. **Filed as #1571.** I name the demand and the existing pages; whether to build anything is product-manager's call.

## 10. Lever 6 — Index status

`/tmp/measure/index-status.json`, generated 2026-11-28T03:26Z, **214 of 214 URLs inspected, 0 errors**, not partial, quota 214 of 2,000. 137 of 142 pages with impressions matched.

| state | count |
|---|---:|
| Submitted and indexed | 165 |
| Crawled - currently not indexed | 27 |
| Discovered - currently not indexed | 17 |
| URL is unknown to Google | 5 |
| **not indexed, total** | **49** (`/learn` 27, `/panchang` 18, `/muhurat` 2, `/dasha` 1, `/hi` 1) |
| changed after Google's last crawl (stale) | **172** of 214; 11 of them with ≥ 500 impressions |
| canonical mismatch / blocked | 0 / 0 |

Ranked by value (the file's `request_indexing`, all "changed after Google's last crawl"): debilitated-sun-career (2,656 impr; edited 2026-11-22, crawled 11-16), 7th-lord (1,978; edited 11-24, crawled 11-23), sade-sati (1,959; 11-26 vs 11-20), planets-in-7th (1,755; 11-26 vs 11-25), career-during-sade-sati (1,395; 11-27 vs 11-23), rahu-mahadasha-career-problems (1,226; 11-27 vs 11-11), 10th-lord-in-6th (787; 11-27 vs 11-11), griha-pravesh (657; 11-27 vs 11-08), mangal-mars (656; 11-25 vs 11-10), saturn-in-10th (600; 11-27 vs 11-04). The owner-side act is "Request indexing" in Search Console for these ten; no agent can do it.

Not indexed with impressions: ashwini-nakshatra 67, pushya 37, rohini 23, swati 22, marriage-delayed 18, dhana-yoga 16, vivah-muhurat-2027 16, ketu-remedies 14. All "Crawled - currently not indexed": Google fetched them and declined, a content-quality or duplication signal, not a discovery problem.

## 11. Lever 7 — Measurement gaps against my last three reports (2026-11-25, 11-26, 11-27)

| gap | in each of the last three? | this run | open issue |
|---|---|---|---|
| Per-page × per-day export (`/matching` fall, deploy splits) | yes | not in inputs | #953, #1076 (both open), #490 |
| Share of Direct that is automated (`--cohorts`) | yes | no file | #1364 (open) |
| Query → page map | yes | no file | #1432, #1437 (open) |
| `page_location` query strings in GA4 | yes | not read | #1237, #1448 (open) |
| Short-stay landings broken / bad-intent / unrouted | yes | unresolved | #1534 (open) |
| HTTP 5xx per route | yes | **now present, 1 of 7 days** | #1506 closed |
| Index capture | partial before | **present** | – |
| GA4 previous window | resolved | present | #1205 closed |
| 3-session gap between `ga4-daily.json` sessions (851) and `ga4.json` (848) | the 11-27 report names a 4-session gap; not in the other two | not reconciled | none needed yet |

Every gap that appears in all three reports has an open issue. **Nothing filed for lever 7.** Filed this run: **#1571** (lever 5/6, evidence in §9–10).

## 12. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| Whether the objective (ten top queries into the top 5) is moving | not recoverable while 86% of impressions are withheld. Page proxy: 1 of 10 at ≤ 5.0 |
| How much of Direct (288 sessions, 19.1% engaged) is automated | the `--cohorts` file (#1364) |
| Why `/matching` lost 5.9 positions (4.4 → 10.3) and 235 impressions | per-page × per-day export (#953, #1076) |
| Why AI Assistant referrals fell from 20 to 5 | a daily landing × source export |
| Whether the 11-16 → 11-19 impressions dip was a re-rank | the next runs' daily rows |
| Whether short-stay landings are bad-intent or badly framed | landing × event export (#1534) |
| Whether Nakshatra pages lost impressions because they left the index | a second index capture to diff against the first |
| Which page serves each visible query | the `query-page` export file (#1432, #1437) |
| HTTP 5xx per route over a full week | six more days of the counter |
| Whether `numerology_completed` = 0 is unused or broken | server-side count of numerology computations after 2026-11-18 |
| Causes of the 10 `verify-production` failures | the run logs (not read) |
| The 3-session gap, 851 vs 848 | not investigated; the two exports may define a session differently |

## 13. Handed back

| item | value |
|---|---|
| Issue filed | **#1571** — `request_indexing` ranks by current impressions, so `gochar-2027` can never be listed |
| Comments posted | **#1326** (count read, Nov and Dec met, Jan 1–14 slice 0), **#1469** (`muhurat_searched` present; `numerology_completed` 0 noted) |
| Timers written | 21 lines in `/tmp/analyst-timers.txt` (every issue pending a clean window) |
| Verdicts unchanged and not re-posted | #311 MISS, #276 BAR MET not attributable, #329 UNSCOREABLE 3 vs 10, #515 unscoreable, #1277 MET, #1115 MET |
