# Analyst report — 2026-11-25

**Window for every number: W = 2026-10-26 → 2026-11-22** (28 days; the last 3 are excluded: GSC lags 2–3 days, GA4 24–48h).
**Previous window P = 2026-09-28 → 2026-10-25** (GSC trend files only; GA4 has no previous window in this run).
Everything below was read from this run's `/tmp/*.json` and `/tmp/measure/*.json`, from `gh` this run, from `measurements/index-status.json` (generated 2026-11-23T03:12Z) or from `festival_registry.py` this run. Anything not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 31,021 impressions | no | 416 clicks |
| `gsc-all.json` (`dimension: page`) | W | 100%; page rows sum 31,106 vs property 31,021 | no | 140 pages |
| `gsc-band.json` (`dimension: page`) | W | whole fetch 100%; **printed 97 rows = 22,486 impressions = 72%** (`emitted_coverage_pct`) | no | band figures are the printed rows |
| `gsc-trend-page.json` | W vs P | W 100%; P coverage **not stated** | no | page-row sums: W 31,106 impr / 416 clicks; P 12,802 impr / 129 clicks |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **14%** (4,446 of 31,021 impressions visible; 967 query keys vs 254 in P) | no | Google withholds the rest. No conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 800 sessions (rows sum 801) | no | 163 rows, 105 raw landings, **97 distinct paths** after folding query strings and trailing slashes |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum **804**, daily users sum 707. Session totals do not reconcile (800 property / 801 rows / 804 daily / 802 `session_start`); each is quoted from its own file |
| `ga4-events.json` | W | 21 event names, `events_total` 5,244 | no | `cta_click` exists only from 2026-11-03 (PR #688): partial history |
| `ga4-anomalies.json` | W | 2 spikes + 4 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | **0 clicks, 0 impressions on all 28 days**, `top_pages` empty | – | a measured zero |
| `verify-first.json` | W | 10 busiest pages by engaged sessions | – | |
| `measure/llm-usage.json` | last 7 days, generated 2026-11-25T03:55Z | – | – | carries `fallbacks` and `fallback_reasons` |
| `measurements/index-status.json` | generated 2026-11-23T03:12Z | 214 of 214 URLs inspected, 0 errors | – | same file as the 2026-11-24 report read; **no newer capture** |
| GA4 previous window | – | **absent** | – | no `ga4-trend.json` in `/tmp`. Sessions and users against P are **not measured** (#1205, open, `needs-human-review`) |
| `measurements/kundli-submissions.json` | – | **absent** | – | kundli GA4 ↔ server ratio **not computable** (#1409 wires the collector, open) |
| `git log origin/main --since=2026-10-26` | – | 568 commits after `git fetch --unshallow` | – | the checkout was shallow (`git rev-parse --is-shallow-repository` = true) before the fetch |

## 1. The 6–20 position band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **Not measurable as written**: the query export covers 14% of impressions, and in page mode a band `position` is the page's average across its queries. The tables are the page-level proxy.

| metric (W, `dimension: page`) | value |
|---|---|
| pages with impressions | 140 |
| pages at average position < 6 | 33 (7,913 impressions) |
| pages at position 6–20 (printed rows) | **97**, 22,486 impressions (72%), 295 clicks, aggregate CTR **1.31%** |
| band pages with ≥ 100 impressions | 29; median CTR 1.35% |
| top-10 pages by impressions at average position ≤ 5 | **1 of 10** (`gochar-2026-planetary-transits`, 5.0) |

Band list, ranked by the file's `band_opportunity` (W; position = page average; P pos from `gsc-trend-page.json`):

| # | page | impr | clicks | CTR | pos | P pos |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/debilitated-sun-career/ | 2,840 | 17 | **0.60%** | 6.5 | 6.3 |
| 2 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,307 | 59 | 1.78% | 6.5 | 7.1 |
| 3 | /learn/jupiter-in-10th-house-career/ | 2,273 | 23 | 1.01% | 7.0 | 7.0 |
| 4 | /learn/sade-sati/ | 1,971 | 18 | **0.91%** | 6.7 | 6.4 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,634 | 16 | 0.98% | 7.1 | 7.6 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,503 | 12 | **0.80%** | 6.8 | 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,089 | 17 | 1.56% | 7.2 | 6.9 |
| 8 | /learn/mangal-mars-in-vedic-astrology/ | 643 | 3 | **0.47%** | 7.7 | 7.3 |
| 9 | /learn/10th-lord-in-6th-house-career/ | 841 | 25 | 2.97% | 6.9 | 6.8 |
| 10 | /learn/manglik-dosh/ | 497 | 4 | 0.80% | 6.8 | 7.3 |
| 11 | /learn/saturn-in-10th-house-career/ | 520 | 7 | 1.35% | 7.5 | – |
| 12 | /learn/vimshottari-dasha-explained/ | 442 | 3 | 0.68% | 7.6 | – |

**Nearest to top 5** (top-10 by impressions): `career-during-sade-sati` 1,377 impr, pos **5.4** (P 6.7), CTR 1.89%; `rahu-mahadasha-career-problems` 1,213 impr, pos **5.7** (P 6.8), CTR 1.81%. `marriage-mahadasha-timing` 717 impr at 5.1 (P 6.6). `chronic-health-issues-kundli` 539 impr at 4.6.

### CTR outliers (≥ 300 impressions, position ≤ 8, CTR < 0.9% against the band's 1.31% aggregate)

| page | impr | CTR | pos | reading |
|---|---:|---:|---:|---|
| /learn/gochar-2026-planetary-transits/ | 3,402 | **0.79%** | 5.0 | at position 5.0 the page earns 27 clicks; the band aggregate would give 45 |
| /learn/debilitated-sun-career/ | 2,840 | 0.60% | 6.5 | largest gap among band pages: at 1.31% it would take ~37 clicks, not 17. Title/meta-shaped. #835 pending |
| /learn/planets-in-7th-house-marriage/ | 1,503 | 0.80% | 6.8 | #1430 (closed 2026-11-24) covers the 7th-house pair |
| /learn/mangal-mars-in-vedic-astrology/ | 643 | 0.47% | 7.7 | no open ship named in this run |
| /learn/manglik-dosh/ | 497 | 0.80% | 6.8 | the #311 page; see §3 |
| /learn/vimshottari-dasha-explained/ | 442 | 0.68% | 7.6 | #1072 pending |
| /learn/shukra-venus-in-vedic-astrology/ | 406 | 0.49% | 6.0 | position 6.0, 2 clicks |

Counter-case: `muhurat/griha-pravesh` 480 impr, 3.96% CTR at 6.5 (19 clicks); `numerology` converts at 3–4× the article band at the same position (194 impr, 10 clicks in the `/numerology*` group).

## 2. Decay and rises — W vs P (`gsc-trend-page.json`, page-row sums)

| page group | impr W | impr P | clicks W | clicks P |
|---|---:|---:|---:|---:|
| /learn/* articles | 29,127 | 11,486 | 363 | 105 |
| /muhurat* | 584 | 163 | 23 | 10 |
| /festivals* | 254 | 240 | 0 | 0 |
| / | 217 | 120 | 9 | 8 |
| /numerology* | 194 | 3 | 10 | 0 |
| /rashifal* | 167 | 145 | 1 | 0 |
| /matching* | 118 | 348 | 3 | 1 |
| /learn/ (index) | 113 | 147 | 0 | 0 |
| /panchang* | 101 | 67 | 2 | 1 |
| /kundli* | 100 | 58 | 4 | 4 |

| decay (impr ≥ 50 in P, position worse by ≥ 2) | impr W / P | pos W / P | clicks W / P |
|---|---|---|---|
| /matching | 118 / 348 | **10.1 / 4.4** | 3 / 1 |
| /festivals | 254 / 240 | **39.3 / 25.8** | 0 / 0 |

- `/matching` lost 5.7 positions and 66% of its impressions in W vs P. #508 (title/meta shortened, PR #696, merged 2026-11-03) is pending, scoreable 2026-12-04. Cause **not determined**: no per-page × per-day export (#953, #1076).
- `/festivals` sits at position 39.3 with 0 clicks. The registry had no entry for 2026-11-22 → 2027-01-14 until #1326 (closed 2026-11-21).
- Fallers with a small base: `mars-remedies` 125 → 47, `pushya-nakshatra` 128 → 68, `jupiter-remedies` 72 → 21, `the-9-grahas-overview` 60 → 10, `muhurat/vidyarambh` 92 → 58. **Too small to carry a conclusion.**

Rises (impr W vs P): gochar-2026 73 → 3,402 (27 clicks vs 0, pos 6.0 → 5.0), jupiter-10th 362 → 2,273 (23 vs 1), debilitated-sun 1,504 → 2,840, 7th-lord 307 → 1,634, planets-in-7th 487 → 1,503, rahu-ketu 2,358 → 3,307 (59 vs 29 clicks), career-during-sade-sati 456 → 1,377 (pos 6.7 → 5.4; 26 vs 5 clicks), 10th-lord-in-6th 203 → 841 (25 vs 3 clicks). 37 pages are new in W, 25 are gone.

## 3. Post-ship scores — closed issues with a `thesis:` and a `metric:`

Rule: score once, when the window is clean (W starts 2026-10-26; clean means the deploy is on or before that date). Earlier analyst comments were read on every thread; **nothing was posted on any scored issue this run**, because no verdict changed.

### 3a. Clean window — re-read this run

| issue | deploy | predicted (`metric:`) | actual this run (W) | posted earlier | action |
|---|---|---|---|---|---|
| **#311** (four band pages' title/meta) | PR #334, 2026-10-13 | combined CTR **≥ 1.5%** on ≥ 1,500 impr, position within ±1 | **0.967%** (66 clicks / 6,823 impr); P 0.673% (21 / 3,121) | **MISS** (0.937%, 2026-11-13) | verdict unchanged, not re-posted |
| **#276** (Rahu–Ketu dasha CTA) | PR #342, 2026-10-14 | pages/session **≥ 1.20** on ≥ 20 sessions | Organic **1.62 on 63 sessions**; all channels 1.56 on 70 | BAR MET, not attributable | unchanged, not re-posted |
| **#329** (manglik-dosh checker link) | PR #344, 2026-10-14 | ≥ 1.30 on ≥ 10 Organic sessions | **5** Organic sessions (3.0 pages/session) | UNSCOREABLE: 4 vs 10 | scoring stopped, nothing posted |
| **#1277** (`admin_sessions`) | PR #1278, 2026-11-20 | 0 on every day from 2026-11-12 | **0 on all 11 days 2026-11-12 → 11-22**; `returning.user_days` 88, `share_pct` 12.4, `status: ok` | MET (2026-11-21) | unchanged |

**#311 is a miss and stays one.** Per page over W: rahu-mahadasha-career-problems 1.81% at 5.7 (P pos 6.8, so it moved 1.1 positions and the gain is not attributable to the title at unchanged position); debilitated-sun-career **0.60%** at 6.5; manglik-dosh **0.80%** at 6.8; jupiter-in-10th **1.01%** at 7.0. Three of the four are under 1.1% at positions 6.5–7.0. The reference sibling `rahu-mahadasha-ketu-antardasha` is 1.78% at 6.5, so the "sibling converts at 2.05%" premise did not persist.

**#276:** 1.62 against a bar of 1.20 passes the stated bar and is still not attributable to the CTA. Other `/learn/*` Organic landings combined are **351 sessions at 1.83 pages/session**, above this page's 1.62. `cta_click` from this page to `/dasha` in W: **1** (`ga4-events.json`; `rahu-mahadasha-ketu-antardasha` → `/dasha`). The page took #342, #680, #830 and #1122 inside the same weeks.

### 3b. Pending — window not clean, note already on the issue, timer written

Every issue below already carries a "pending — scoreable from …" note (verified with `gh issue view`; none repeated). All 16 lines are in `/tmp/analyst-timers.txt`; merge dates re-read with `gh pr view` this run.

| issue | thesis (short) | deploy (PR, merge) | scoreable from | note |
|---|---|---|---|---|
| #553 | panch-mahapurush: tool link, false matching claim removed | #615, 2026-10-31 | **2026-12-01** | floor ≥ 10 Organic sessions: W has 17 Organic landing sessions at 1.00 pages/session on the page, so the floor is reachable |
| #426 | Saturn/Jupiter dates fixed; guard on sade-sati position | #673, 2026-11-02 | **2026-12-03** | guard only |
| #570 | `cta_click` by from/to path | #688, 2026-11-03 | **2026-12-04** | 21 `cta_click` events in W (8 with `(not set)` from/to); partial history; not a score |
| #685 | sade-sati title names Moon signs | #690, 2026-11-03 | **2026-12-04** | confound already noted on the thread: Google's first re-crawl was 2026-11-20 |
| #508 | /matching title/meta shortened | #696, 2026-11-03 | **2026-12-04** | floor ≥ 300 impressions near the old position is **at risk**: W has 118 at 10.1 |
| #518 | tool routes on learn articles; pages/session ≥ 2.0 | last slice #754, 2026-11-06 | **2026-12-07** | `/learn/*` article landings in W: 555 sessions at **1.62** pages/session (session-weighted, all channels). Not a score |
| #735 | no GA4 sessions on `/admin*` | #877, 2026-11-11 | **2026-12-12** | W holds 10 `/admin/ops` sessions, last on 2026-11-09; **0 on the 11 days since 11-12** |
| #835 | debilitated-sun 'which sign' lede | #940, 2026-11-13 | **2026-12-14** | page CTR 0.60% on 2,840 impressions in W |
| #1075, #1073, #1074 | rahu-ketu headings; jupiter-10th sections; dated panchang titles | #1122 / #1126 / #1130, 2026-11-16 | **2026-12-17** | #1074 floor ≥ 150 impressions on dated panchang URLs is **at risk**: `/panchang*` is 101 impressions in all |
| #1072, #1071 | vimshottari 'which mahadasha is best'; gochar-2027 | #1145 / #1148, 2026-11-17 | **2026-12-18** | "which mahadasha is best for career": 65 impr at 8.4, P 0 |
| #1322, #1325, #1336 | muhurat finder and landing changes | #1323 / #1328 / #1337, 2026-11-21 | **2026-12-22** | `muhurat/griha-pravesh` W: 480 impr, 3.96% CTR, 29 sessions at 93% engaged (baseline). Three ships inside 24 h: no movement can be split. `muhurat_searched` is absent (§9, #1469) |

### 3c. No traffic claim — nothing to score
Issues whose metric is a grep, a count or "event appears" (#1217, #1226, #1229, #1115, #1236, #1208, #1326, #1332, #1400, #1408, #1411, #1416, #1178, #1175–#1177 and similar). #1093 cannot be scored (no export carries `page_location`; #1237 and #1448 track it).

## 4. Confounds

| confound | read | consequence |
|---|---|---|
| Concurrent ships in W | `git log origin/main --since=2026-10-26`: **568 commits** after unshallowing. The ten largest pages were each edited repeatedly (#940, #1122, #1126, #690, #673 and others named in the earlier report) | no single ship is attributable for the W vs P rise; per-page deltas are scored only on each issue's own window |
| Google has not re-crawled many edits | `index-status.json` 2026-11-23: **168 of 214** URLs "changed after Google's last crawl" | W position and CTR on edited pages partly predate Google seeing the edit |
| Seasonality | Dhanteras 2026-11-06, Diwali 2026-11-08, Chhath 2026-11-15 fall in W (`festival_registry.py`). None of the top-10 pages is a festival page; `gochar-2026` is time-bound | seasonal share **not determined**: no year-earlier window |
| Page working? | `verify-production.yml`, last 100 runs (2026-11-17T09:41Z → 2026-11-25T02:27Z): 93 success, **2 failure** (both 2026-11-17: 13:27Z, 18:12Z), 5 cancelled. No failure in the last 7 days. `llm-usage.json`: **0 fallbacks** in 7 days | pages were up for W except possibly on 2026-11-17 (the failure causes were not read) |
| Sample size | most page deltas rest on < 30 clicks | #311, #329, #1074 and #508 are at or under their own floors |
| Automated traffic | §5 | Direct is 281 of 801 sessions at 19% engaged: raw sessions overstate people |

## 5. Lever 1 — Growth against the previous window

| metric | W (2026-10-26 → 11-22) | P (2026-09-28 → 10-25) | change | source |
|---|---:|---:|---:|---|
| GSC impressions (page-row sum) | 31,106 | 12,802 | **+143%** | `gsc-trend-page.json`; W property total 31,021 |
| GSC clicks (page-row sum) | 416 | 129 | **+222%** | same |
| GA4 sessions (daily sum) | 804 | **not measured** | – | no previous GA4 window (#1205) |
| GA4 active users (daily sum, not people) | 707 | **not measured** | – | |
| Organic Search sessions | 514 | not measured | – | 57% engaged, 153 s per session |
| Direct sessions | 281 | not measured | – | 19% engaged, 53 s per session |
| AI Assistant sessions | 5 | not measured | – | 20% engaged |
| Returning user-days | 88 (**12.4%**) | not measured | – | `ga4-daily.json`, `status: ok` |
| `admin_sessions` | 10 in W, all 2026-10-26 → 11-09 | – | – | **0 on every day from 2026-11-12** (#735): no internal-traffic leak |
| Discover | **0 clicks, 0 impressions** | – | – | measured zero, all 28 days |

### Inside W, by 7-day block (`gsc-daily.json`, `ga4-daily.json`)

| block | impressions | clicks | sessions | active users (sum) |
|---|---:|---:|---:|---:|
| 10-26 → 11-01 | 7,349 | 88 | 157 | 135 |
| 11-02 → 11-08 | 7,740 | 106 | 215 | 196 |
| 11-09 → 11-15 | 9,185 | 145 | 281 | 249 |
| 11-16 → 11-22 | 6,747 | **77** | 151 | 127 |

The last block is **27% lower on impressions and 47% lower on clicks** than the block before, and 46% lower on sessions. Daily GSC impressions 11-16 → 11-22: 908, 811, 798, 815, 1,001, 1,177, 1,237 (11-11 → 11-14 were 1,337–1,433); average position stayed 6.0–7.4. **The last four days are rising** and the 11-22 reading is within 14% of the 11-14 level. Cause **not determined** (post-Diwali/Chhath calendar, a re-rank, or late GSC data). A week is not a trend; Discover is 0 throughout, so it is not a Discover loss.

**Which pages drive the change (W vs P, GSC page rows):** `/learn/*` articles are 29,127 of the 31,106 W impressions and 363 of 416 clicks. The gain sits in articles whose impressions grew 2–45×: gochar-2026 (+3,329), jupiter-10th (+1,911), debilitated-sun (+1,336), 7th-lord (+1,327), planets-in-7th (+1,016), rahu-ketu (+949), career-during-sade-sati (+921). **Structural vs seasonal:** a ranking-footprint gain on articles at similar or better position, with one time-bound exception: gochar-2026 is 3,329 of the 18,304 page-row impression gain (18%), and its engaged rate is 35% at 26 s (§6). A year-earlier window does not exist, so the split is not determined further.

### Anomaly days — every day in `spikes` and `watch` (`ga4-anomalies.json`), against search clicks that day

| date | tier | active users (median 22) | source and landing | engagement | GSC clicks | Discover | reading |
|---|---|---:|---|---|---:|---:|---|
| 2026-11-06 | spike | 57 | (direct) top row `/rashifal/aries` 6 sessions at 17% engaged, 3.5 s; also `/r/zzzzzz`, `/kundli`; google/organic `rahu-mahadasha-career-problems` 4 at 50% | 19 of 50 sessions zero-engaged: "(not set)/desktop/United States" 10 at 0%, Chrome/desktop/US 6 | 17 | 0 | **mixed: automated traffic, not growth.** The organic rows are readers |
| 2026-11-15 | spike | 51 | google/organic `rahu-mahadasha-ketu-antardasha` 6 at 83%, 242 s; (direct) `/panchang/2026-12-02` 5 sessions at 0%, 1.6 s; `/kundli` 3 at 0% | Chrome/mobile/**China** 9 sessions at 0%; Chrome/mobile/India 17 at 59% | 14 | 0 | organic part real; the direct part is automated (China cohort, a future-dated panchang URL). Search clicks flat; **not Discover** |
| 2026-11-10 | watch | 40 | (direct) `/matching` 5 at 0%, `/numerology` 4; bing/organic `/numerology` 4 at 0% | 21 of 35 sessions zero-engaged: "(not set)/desktop/US" 9, Chrome/desktop/US 8 | 14 | 0 | **automated** (same cohort as 11-06) |
| 2026-11-12 | watch | 34 | google/organic `/muhurat/griha-pravesh` 4 at 100%, 205 s | Chrome/mobile/India 14 at 71% | 24 | 0 | real readers |
| 2026-11-09 | watch | 32 | google/organic `jupiter-in-10th` 5, `rahu-ketu` 5, `griha-pravesh` 5 | Chrome/mobile/India 15 at 53% | 21 | 0 | real readers |
| 2026-11-14 | watch | 32 | google/organic `rahu-mahadasha-ketu-antardasha` 10 at 40%; `chronic-health-issues-kundli` 5 at 20% | Chrome/mobile/India 11 at 82%; Chrome/mobile/**Indonesia** 9 at 67% | 23 | 0 | real readers |

A recurring cohort ("(not set)" or Chrome, desktop, United States, 0% engaged) appears on 2026-11-06 and 11-10. **Its window-wide size is not measured** (#1364, open, `qa-pass`).

## 6. Lever 2 — Where time is spent (`verify-first.json`, `ga4.json`, W)

| page | sessions | engaged | engaged rate | avg engagement s | GSC impr | pos |
|---|---:|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha | 70 | 42 | 60% | 131 | 3,308 | 6.5 |
| / | 60 | 35 | 58% | **258** | 218 | 5.7 |
| /muhurat/griha-pravesh | 29 | 27 | **93%** | 88 | 480 | 6.5 |
| /learn/10th-lord-in-6th-house-career | 30 | 19 | 63% | 167 | 841 | 6.9 |
| /learn/gochar-2026-planetary-transits | 48 | 17 | **35%** | **26** | 3,402 | 5.0 |
| /learn/sade-sati | 25 | 15 | 60% | 251 | 1,971 | 6.7 |
| /learn/career-during-sade-sati | 31 | 15 | 48% | 215 | 1,377 | 5.4 |
| /learn/rahu-mahadasha-career-problems | 27 | 14 | 52% | **259** | 1,213 | 5.7 |
| /learn/debilitated-sun-career | 23 | 11 | 48% | 234 | 2,840 | 6.5 |
| /learn/jupiter-in-10th-house-career | 26 | 10 | 38% | 58 | 2,273 | 7.0 |

Whole property (`ga4.json`): 801 session rows, 347 engaged (43%), average engagement **118 s** per session. By channel: Organic Search 514 sessions at 57% engaged, 153 s; Direct 281 at 19%, 53 s; AI Assistant 5; Unassigned 1.

Pages that get traffic and do not hold it (folded landings, W):

| landing | sessions | engaged | avg engagement s | channels | reading |
|---|---:|---:|---:|---|---|
| /learn/chronic-health-issues-kundli | 21 | 4 (19%) | **8** | Organic 16 | position 4.6, 539 impressions, 13 clicks; readers leave at once. Cause **not determined** |
| /learn/gochar-2026-planetary-transits | 48 | 17 (35%) | 26 | Organic 28 | the page gaining most from search is the one readers abandon fastest among the top five |
| /learn/7th-lord-placement-marriage-guide | 28 | 10 | 41 | – | 1.11 pages/session |
| /learn/panch-mahapurush-yoga | 24 | 10 | 38 | Organic 17 | 1.00 pages/session |
| /learn/jupiter-in-10th-house-career | 26 | 10 | 58 | – | 1.27 pages/session |

Tool funnel (W, `ga4-events.json`, event counts not users; `session_start` 802):

| step | count | note |
|---|---:|---|
| `page_view` | 1,477 | 1.84 per session |
| `feature_view` | 704 | |
| `form_start` | 109 | |
| `kundli_generated` | 52 | 48% of `form_start`; may count re-renders on some paths, read as an upper bound |
| `ask_answered` | 126 | the one high-volume generative path |
| `tool_submitted` | 27 | #1226 |
| `cta_click` | **21** (2.6% of sessions) | 13 with a named from/to, 8 `(not set)`. From `/learn/*` to tools: `/` 5, `/kundli` 3, `/dasha` 2, `/kaal-sarp-check` 1, `/numerology` 1, `/sade-sati-check` 1. Partial history (from 2026-11-03). No impression event, so low click rate vs low exposure is not determinable |
| `matching_completed` | 3 | |
| `dosha_check_completed` | 2 | |
| `subscribe_completed` | 1 | |
| `feedback_sent` | 2 | |
| `muhurat_searched` | **absent** | not among the 21 names; filed as **#1469** this run (§9) |

Kundli GA4 ↔ server ratio: **not computable** (`measurements/kundli-submissions.json` does not exist in this run). I divided nothing by `totals.fresh_generations`.

## 7. Lever 3 — Errors per route

| source | window | reading |
|---|---|---|
| `llm-usage.json` | last 7 days, generated 2026-11-25T03:55Z | 150 calls, 108 cache hits (**72%**), 42 misses. Input 135,871 tokens, output 25,353. **`fallbacks`: 0; `fallback_reasons`: {}** |
| peak day | `peak_day_tokens` 6,733 on 2026-11-22; `peak_day_measured_tokens` **42,994** on 2026-11-23 | 42,994 is 21.5% of the 200,000 TPD the repo cites. #925 (open) says a peak day used 83%; this file does not reproduce that, and I did not read the collector to say which field is the day's total |
| `verify-production.yml` | last 100 runs, 2026-11-17T09:41Z → 11-25T02:27Z | 93 success, 2 failure (both 2026-11-17), 5 cancelled |

| route | calls | hits | hit rate | input tokens | tokens per measured call | errors / fallbacks | tracked by |
|---|---:|---:|---:|---:|---:|---|---|
| natal | 86 | 77 | 89% | 59,417 | 6,601 (9 measured) | 0 | – |
| ask | 26 | 0 | **0%** | 63,045 | 2,424 (26 measured) | 0 | per-visitor by nature; nothing here says it is over budget |
| rashifal | 28 | 28 | 100% | not measured | not measured | 0 | nightly job (#515) serves it from cache |
| matching | 5 | 0 | 0% | 9,352 | 1,870 | 0 | – |
| monthly | 3 | 2 | 66% | 2,116 | 2,116 (1 measured) | 0 | – |
| today | 2 | 1 | 50% | 1,941 | 1,941 (1 measured) | 0 | – |

No route has a recorded LLM error or fallback in 7 days. Still **not measured**: HTTP 5xx per non-LLM route (the file records LLM fallbacks only) and the cause of the two 2026-11-17 `verify-production` failures.

## 8. Lever 4 — Search demand (partial: query export covers 14% of impressions)

Themes from `gsc-trend-query.json`, W vs P. **The export has no page column**, so "the page" below is named by topic, not measured. #1432 (query × page export) is open with halves #1436 (script, `qa-pass`) and #1437 (workflow).

| theme (W, visible queries only) | impressions W (P) | clicks | pos W (P) | existing page | note |
|---|---:|---:|---:|---|---|
| "sun debilitated in which sign" family: 332 + 153 + 70 + 68 (+ "sun debilitation degree" 57, "debilitated sun" 53) | 623 for the first four (P 92); 733 with the last two | 2 | 5.8–8.8 | `/learn/debilitated-sun-career/` | page CTR 0.60% on 2,840 impressions. #835 pending |
| "rahu mahadasha ketu antardasha" family: 350, 61, 46 for three wordings | 457 (P 344) | 12 for the head query | 6.3–10.2 (P 9.1–16.4) | `/learn/rahu-mahadasha-ketu-antardasha/` | every listed wording gained 2–6 positions vs P |
| "jupiter in 10th house", "guru in 10th house" | 123 + 94 (P 0) | 0 | 8.7–10.9 | `/learn/jupiter-in-10th-house-career/` | new in W; #1073 pending |
| "10th lord in 6th house" | 89 (P 11) | 1 | 8.7 (8.7) | `/learn/10th-lord-in-6th-house-career/` | |
| "which mahadasha is best for career" | 65 (P 0) | 0 | 8.4 | `/learn/vimshottari-dasha-explained/` (#1072) | pending |
| "yes" | 121 (P 10) | 0 | 3.8 | **not determined** | a one-word query: no page can be named. Not a theme to act on |

- **Queries with no page: not determinable from this export.** I name no new page. Each new cluster has a page and a pending ship.
- `/matching`: 348 → 118 impressions, position 4.4 → 10.1 (§2). `/festivals` sits at 39.3.
- Cannibalisation check: `7th-lord-placement-marriage-guide` (1,634 impr, 7.1) and `planets-in-7th-house-marriage` (1,503 impr, 6.8) share a theme; #1430 covered the pair and is closed. I do not propose a new page.

## 9. Lever 6 — Index status (`measurements/index-status.json`, generated 2026-11-23T03:12Z; not re-captured since the last report)

| count | value |
|---|---:|
| URLs in sitemap, inspected | 214 of 214, 0 errors |
| indexed / not indexed | **165 / 49** |
| stale ("changed after Google's last crawl") | **168** |
| canonical mismatch / blocked / unknown | 0 / 0 / 0 |

The ten largest pages by W impressions are stale in the file; the file predates every ship after 2026-11-23. This is a request for a re-crawl; **I have no write path to request indexing.** `request_indexing` is a key in the file; I did not read it. #1065 holds the export.

## 10. Lever 5 — Content opportunities (next 6–8 weeks, 2026-11-25 → 2027-01-20)

Dates read from `festival_registry.py` this run (`dates={...}`); I did not re-verify any date against an almanac.

| date | festival (slug) | learn article (`learn_article_for`) |
|---|---|---|
| 2026-12-01 | kalabhairav-jayanti | none |
| 2026-12-14 | vivah-panchami | none |
| 2026-12-20 | gita-jayanti | none |
| 2026-12-23 | dattatreya-jayanti | none |
| 2027-01-15 | makar-sankranti | none |
| 2027-01-15 | pongal | none |

- All six registry entries in the window have no linked `/learn` article. None appears among the 140 pages in `gsc-all.json`; `/festivals` has 254 impressions at 39.3 and 0 clicks. product-manager decides whether a page is worth building; the existing surface is `/festivals`.
- Kartika Purnima (2026-11-24) has just passed. **Lohri is not in the registry** (grep over `festival_registry.py` and `festivals.py` returns nothing): I state no Lohri date.
- Annual pages: `gochar-2026-planetary-transits` (3,402 impr, pos 5.0, 2026 transit year, ends in about five weeks); `gochar-2027-planetary-transits` exists (#1148); it is **absent** from the 140 pages in `gsc-all.json` (0 impressions).
- `/panchang/2026-12-02` drew 5 zero-engagement direct sessions on 2026-11-15 (§5).

## 11. Lever 7 — Measurement gaps vs my last three reports (2026-11-22, 11-23, 11-24)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window | yes, and this run | **#1205** | none: covered |
| `page_location` / query strings in GA4 exports | yes | **#1237**, #1448 | none: covered |
| Per-page × per-day export | yes | **#953**, **#1076** | none: covered |
| Shallow checkout (no `git log --since`) | yes (unshallowed this run, 568 commits) | **#974** | none: covered |
| Server-side kundli submission count | yes | **#1272**, #1409 | none: covered |
| Share of Direct traffic that is automated | yes | **#1364** | none: covered |
| Query → page map | yes | **#1432**, #1436, #1437 | none: covered |
| **`muhurat_searched` absent from `ga4-events.json`** | **yes: 11-22, 11-23, 11-24, and this run** | none (#1017 and #1336 mention it in passing) | **filed #1469** |
| Errors / LLM fallbacks per route | resolved by #1208 | – | – |

## 12. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| GA4 sessions and users against P | `ga4-trend.json` written by `agent-measure` (#1205) |
| Whether the objective (ten highest-impression queries into the top 5) is moving | not recoverable: 86% of impressions are withheld. Page proxy: 1 of the top 10 pages at ≤ 5.0 |
| Which page serves a visible query | `query × page` export (#1432) |
| Window-wide share of Direct traffic that is automated | cohort export (#1364) |
| Why `/matching` lost ~6 positions | per-page × per-day export (#953, #1076) |
| Whether the 11-16 → 11-19 dip (impressions ~800/day, 47% lower clicks week-on-week) was a re-rank | the next run's daily rows; 11-20 → 11-22 already read 1,001 / 1,177 / 1,237 |
| Whether `chronic-health-issues-kundli` (8 s average engagement) is broken or a bad-intent landing | page render check plus scroll depth; not in these files |
| Whether `muhurat_searched` is broken or unused | `fetch_ga4.py --journeys` for `tool_submitted` with `tool=muhurat`, plus the server-side POST count (#1469) |
| HTTP 5xx per non-LLM route; cause of the two 2026-11-17 `verify-production` failures | Cloud Run request log; those runs' logs |
| Which of the 168 stale pages Google has re-fetched | a new `index-status.json` capture |

## 13. Handed back

| item | value |
|---|---|
| Issues filed | **#1469** (`muhurat_searched` absent from GA4 in four consecutive reports) |
| Comments posted on issues | none: no verdict changed and every pending note already exists |
| Verdict changes | none: #311 MISS (0.967%), #276 BAR MET (not attributable), #329 UNSCOREABLE (5 vs 10), #1277 MET |
| Timers | 16 lines in `/tmp/analyst-timers.txt` (#553 12-01; #426 12-03; #570, #685, #508 12-04; #518 12-07; #735 12-12; #835 12-14; #1075, #1073, #1074 12-17; #1072, #1071 12-18; #1322, #1325, #1336 12-22) |
| The one number to read first | clicks 416 vs 129 and impressions 31,021 vs 12,802 (W vs P): the footprint is ~2.4× larger, concentrated in `/learn` articles. The 11-16 → 11-22 week is 47% below the week before on clicks, with the last three days recovering. Not yet shown to be durable |
