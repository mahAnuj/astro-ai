# Analyst report — 2026-11-24

**Window for every number: W = 2026-10-25 → 2026-11-21** (28 days; the last 3 are excluded: GSC lags 2–3 days, GA4 24–48h).
**Previous window P = 2026-09-27 → 2026-10-24** (GSC trend files only; GA4 has no previous window in this run).
Everything below was read from this run's files (`/tmp/*.json`, `/tmp/measure/*.json`), from `gh` this run, from `measurements/index-status.json` (generated 2026-11-23T03:12Z), or from `festival_registry.py` this run. Anything not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 30,711 impressions | no | 409 clicks |
| `gsc-all.json` (`dimension: page`) | W | 100%; page rows sum 30,795 vs property 30,711 | no | 137 pages |
| `gsc-band.json` (`dimension: page`) | W | whole fetch 100%; **printed 97 rows = 22,729 impressions = 74%** (`emitted_coverage_pct`) | no | band figures below are the printed rows |
| `gsc-trend-page.json` | W vs P | W 100%; P coverage **not stated** | no | page-row sums: W 30,795 impr / 409 clicks; P 12,284 impr / 128 clicks |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **14%** (4,442 of 30,711 impressions visible; 954 query keys vs 225 in P) | no | Google withholds the rest. No conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 799 sessions (rows sum 801) | no | 162 rows, 105 raw landings, **97 distinct paths** after folding query strings and trailing slashes |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum **804**, daily users sum 703. Session totals from GA4 reports do not reconcile (799 property / 801 rows / 804 daily / 802 `session_start`); each is quoted from its own file |
| `ga4-events.json` | W | 20 event names, `events_total` 5,275 | no | `cta_click` exists only from 2026-11-03 (PR #688): partial history |
| `ga4-anomalies.json` | W | 2 spikes + 4 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | **0 clicks, 0 impressions on all 28 days**, `top_pages` empty | – | a measured zero |
| `verify-first.json` | W | 10 busiest pages by engaged sessions | – | |
| `measure/llm-usage.json` | last 7 days, generated 2026-11-24T05:07Z | – | – | now carries `fallbacks` and `fallback_reasons` (#1208) |
| `measurements/index-status.json` | generated 2026-11-23T03:12Z | 214 of 214 URLs inspected, 0 errors | – | **newer than the 2026-11-19 file the last three reports used** |
| GA4 previous window | – | **absent** | – | no `ga4-trend.json` in `/tmp`. Sessions and users against P are **not measured** (#1205, open, `needs-human-review`) |
| `measurements/kundli-submissions.json` | – | **absent** | – | the kundli GA4 ↔ server ratio is **not computable** (§7) |
| `git log origin/main --since=2026-10-25` | – | 100 commits after `git fetch --unshallow` (history 560 commits) | – | `gh pr list --state merged --search "merged:>=2026-10-25"` hit its 300 cap. The two counts do not reconcile; I use PR titles (§3) |

## 1. The 6–20 position band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **Not measurable as written**: the query export covers 14% of impressions, and in page mode a band `position` is the page's average across its queries. The table is the page-level proxy.

| metric (W, `dimension: page`) | value |
|---|---|
| pages with impressions | 137 |
| pages at average position < 6 | 31 (7,753 impressions) |
| pages at position 6–20 (printed rows) | **97**, 22,729 impressions (74% of the page-row total), 294 clicks, aggregate CTR **1.29%** |
| band pages with ≥ 100 impressions | 29 |
| median CTR of the 18 band pages with ≥ 300 impressions | 1.11% |
| top-10 pages by impressions at average position ≤ 5 | **1 of 10** (`gochar-2026-planetary-transits`, 4.9) |

Band list, ranked by the file's `band_opportunity` (W; position = page average; `P pos` from `gsc-trend-page.json`):

| # | page | impr | clicks | CTR | pos | P pos |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/debilitated-sun-career/ | 2,904 | 16 | **0.55%** | 6.5 | 6.2 |
| 2 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,424 | 61 | 1.78% | 6.4 | 7.2 |
| 3 | /learn/jupiter-in-10th-house-career/ | 2,192 | 22 | 1.00% | 7.0 | 6.9 |
| 4 | /learn/sade-sati/ | 2,033 | 19 | **0.93%** | 6.6 | 6.3 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,560 | 16 | 1.03% | 7.2 | 7.7 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,448 | 11 | **0.76%** | 6.8 | 5.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 1,074 | 16 | 1.49% | 7.2 | 6.9 |
| 8 | /learn/10th-lord-in-6th-house-career/ | 850 | 24 | 2.82% | 6.9 | 7.0 |
| 9 | /learn/mangal-mars-in-vedic-astrology/ | 636 | 4 | **0.63%** | 7.7 | – |
| 10 | /learn/manglik-dosh/ | 509 | 4 | 0.79% | 6.8 | 7.6 |
| 11 | /learn/saturn-in-10th-house-career/ | 504 | 6 | 1.19% | 7.5 | – |
| 12 | /learn/sun-in-10th-house-career/ | 459 | 6 | 1.31% | 6.1 | – |

**Nearest to top 5** (top-10 by impressions): `career-during-sade-sati` 1,364 impr, pos **5.4** (P 6.8), CTR 1.83%; `rahu-mahadasha-career-problems` 1,195 impr, pos **5.7** (P 6.8), CTR 1.84%. The other seven top-10 pages sit at 6.4–7.2.

### CTR outliers (against the band's own 1.29% aggregate; ≥ 300 impressions, CTR < 0.76%)

| page | impr | CTR | pos | reading |
|---|---:|---:|---:|---|
| /learn/debilitated-sun-career/ | 2,904 | 0.55% | 6.5 | largest gap on the site: at 1.29% it would take about 37 clicks, not 16. Title/meta-shaped. #835 (answer-first lede, merged 2026-11-13) targets it; Google crawled it 2026-11-16 (§9) |
| /learn/mangal-mars-in-vedic-astrology/ | 636 | 0.63% | 7.7 | same shape, no open ship named in this run |
| /learn/vimshottari-dasha-explained/ | 430 | 0.70% | 7.6 | #1072 (merged 2026-11-17) pending |
| /learn/shukra-venus-in-vedic-astrology/ | 403 | 0.50% | 6.0 | position 6.0 and 0.50% CTR |

Counter-case: `muhurat/griha-pravesh` 432 impr, 4.63% CTR at 6.5; `numerology` 190 impr, 4.74% at 6.1. Tool pages convert at 3–4× the article band at the same position.

## 2. Decay and rises — W vs P (`gsc-trend-page.json`, page-row sums)

| page group | impr W | impr P | clicks W | clicks P |
|---|---:|---:|---:|---:|
| /learn/* articles | 28,870 | 10,984 | 355 | 105 |
| /muhurat* | 525 | 161 | 24 | 9 |
| /festivals* | 266 | 236 | 0 | 0 |
| / | 216 | 115 | 9 | 8 |
| /numerology* | 191 | 4 | 10 | 0 |
| /rashifal* | 170 | 141 | 1 | 0 |
| /matching* | 117 | 347 | 3 | 1 |
| /learn/ (index) | 113 | 145 | 0 | 0 |
| /panchang* | 98 | 71 | 2 | 1 |
| /kundli* | 97 | 61 | 4 | 4 |

| decay (impr ≥ 50 in both windows, position worse by ≥ 1.5) | impr W / P | pos W / P | clicks W / P |
|---|---|---|---|
| /matching | 117 / 347 | **10.1 / 4.4** | 3 / 1 |
| /festivals | 266 / 236 | **38.6 / 25.7** | 0 / 0 |

- `/matching` lost 6 positions (4.4 → 10.1) and 66% of its impressions in W vs P. #508 (title/meta shortened, PR #696, merged 2026-11-03) is pending; its window opens 2026-12-04. Cause of the fall **not determined**: no per-page × per-day export (#953, #1076).
- `/festivals` was at position 38.6 on 266 impressions and 0 clicks; its registry had no entry for 2026-11-22 → 2027-01-14 until #1326 (PR #1329, 2026-11-21).
- Pages that lost impressions without a position collapse (fewer than 130 impressions in P): `mars-remedies` 126 → 46, `jupiter-remedies` 74 → 21, `the-9-grahas-overview` 68 → 12, `pushya-nakshatra` 121 → 75. Small numbers; **too small to carry a conclusion**.

Rises: gochar-2026 16 → 3,326 impressions (27 clicks vs 0, pos 5.6 → 4.9), jupiter-10th 357 → 2,192, debilitated-sun 1,409 → 2,904, 7th-lord 301 → 1,560, career-during-sade-sati 414 → 1,364 (pos 6.8 → 5.4; clicks 4 → 25), 10th-lord-in-6th 172 → 850 (3 → 24 clicks), rahu-ketu 2,244 → 3,424 (29 → 61 clicks), `chronic-health-issues-kundli` 120 → 532 (pos 6.5 → 4.7; 1 → 12 clicks). 39 pages are new in W; 27 are gone.

## 3. Post-ship scores — issues closed in the last 45 days with a `thesis:` and a `metric:`

Scoring rule: score once, when the window is clean (starts on or after the deploy). Read every earlier analyst comment on each thread first.

### 3a. Clean window already scored — re-read this run, nothing posted

| issue | deploy | predicted (`metric:`) | actual this run (W) | posted earlier | change | action |
|---|---|---|---|---|---|---|
| **#311** (four band pages' title/meta) | PR #334, 2026-10-13 | combined CTR **≥ 1.5%** on ≥ 1,500 impr, position within ±1 | **0.941%** (64 clicks / 6,800 impr), pos in range; P (2026-09-27 → 10-24) 0.665% (20 / 3,009) | **MISS** 0.937% (2026-11-13, W 10-14 → 11-10) | verdict and number unchanged | not re-posted |
| **#276** (Rahu–Ketu dasha CTA) | PR #342, 2026-10-14 | pages/session **≥ 1.20** on ≥ 20 sessions | Organic **1.61 on 64 sessions** (all channels 1.55 on 71) | BAR MET, not attributable (1.42 on 55) | number moved 1.42 → 1.61, verdict unchanged | not re-posted (below) |
| **#329** (manglik-dosh checker link) | PR #344, 2026-10-14 | ≥ 1.30 on ≥ 10 Organic sessions | **4** Organic sessions, 1.00 pages/session | UNSCOREABLE at this traffic: 3 vs 10 | unchanged, 4 vs 10 | scoring stopped, nothing posted |
| #397, #345 | 2026-10-15/20 | tree and file checks | already scored once on their issue | – | – | none |
| #1277 (returning users, `admin_sessions`) | PR #1278, 2026-11-20 | `admin_sessions` 0 every day from 2026-11-12 | **0 on all 10 days 2026-11-12 → 11-21**; `returning.user_days` 89, `share_pct` 12.7, `status: ok` | MET (2026-11-21) | unchanged | none |

**#311 is a miss and stays one.** Per-page CTR over W (`gsc-trend-page.json`): rahu-mahadasha-career-problems 1.84% at 5.7 (P 10 clicks / 782 impr, pos 6.8), debilitated-sun-career **0.55%** at 6.5 (16 / 2,904), manglik-dosh **0.79%** at 6.8 (4 / 509), jupiter-in-10th **1.00%** at 7.0 (22 / 2,192). Three of four stay under 1.0% CTR at positions 6.5–7.0. The one at 1.84% also moved 1.1 positions, so its gain is not attributable to the title at unchanged position. The reference page `rahu-mahadasha-ketu-antardasha` is 1.78% at 6.4, so the "sibling converts at 2.05%" premise also did not persist.

**#276:** 1.61 against a bar of 1.20 is a pass of the stated bar; it is still not attributable to the CTA. All other `/learn/*` organic landings combined are **347 sessions at 1.82 pages/session**, above this page's 1.61. `cta_click` from this page to `/dasha` in W: **1** (`ga4-events.json`, partial history from 2026-11-03), unchanged from the 2026-11-14 note. The page took #342, #680 and #830 in the same window.

### 3b. Pending — window not clean; notes already posted, timers written

Every issue below already carries one "pending — scoreable from …" note from an earlier run (read this run; none repeated). One line per issue is in `/tmp/analyst-timers.txt` (16 lines) so the scoring run is queued on the day.

| issue | thesis (short) | deploy (PR, merge) | scoreable from | note |
|---|---|---|---|---|
| #553 | panch-mahapurush: tool link + false matching claim removed | #615, 2026-10-31 | **2026-12-01** | floor ≥ 10 Organic sessions: W Organic landing sessions on the page are 15 — reachable |
| #426 | Saturn/Jupiter dates fixed; guard on sade-sati position ±1 of 6.2 | #673, 2026-11-02 | **2026-12-03** | guard only |
| #570 | `cta_click` by from/to path | #688, 2026-11-03 | **2026-12-04** | the export exists since #782: 20 events in W (§7), partial history; not a score |
| #685 | sade-sati title names Moon signs | #690, 2026-11-03 | **2026-12-04** | **new confound, commented on #685 this run**: Google's first re-crawl was 2026-11-20 (§9), 12 of the window's 28 days |
| #508 | /matching title/meta shortened | #696, 2026-11-03 | **2026-12-04** | position fell 4.4 → 10.1 (§2); floor ≥ 300 impressions at position within ±1.5 of 4.3 is **at risk**: W has 117 at 10.1 |
| #518 | tool routes on learn articles; pages/session ≥ 2.0 | last slice #754, 2026-11-06 | **2026-12-07** | `/learn/*` article landings in W: 548 sessions at **1.61** pages/session (session-weighted, all channels; home 62 sessions at 4.55). Baseline in the issue was 1.32. Not a score |
| #735 | no GA4 sessions on `/admin*` (14 → 0) | #877, 2026-11-11 | **2026-12-12** | W holds 13 admin sessions, all dated 2026-10-25 → 11-09 (before the fix); **0 on the 10 days since 11-12** |
| #835 | debilitated-sun 'which sign' lede | #940, 2026-11-13 | **2026-12-14** | Google crawled the page **2026-11-16**, three days after the merge (§9) — a good sign for a clean read |
| #1075, #1073, #1074 | rahu-ketu headings; jupiter-10th sections; dated panchang titles | #1122 / #1126 / #1130, 2026-11-16 | **2026-12-17** | #1074 floor ≥ 150 impressions on dated panchang URLs is at risk (W: `/panchang/*` 98 impressions in all) |
| #1072, #1071 | vimshottari 'which mahadasha is best' answer; gochar-2027 | #1145 / #1148, 2026-11-17 | **2026-12-18** | #1071's main metric (≥ 300 impressions in the window ending 2027-02-25) is not readable before ~2027-02-28; `gochar-2027-planetary-transits` has **0 impressions** in W |
| #1322, #1325, #1336 | muhurat finder and landing changes | #1323 / #1328 + #1348 / #1337, 2026-11-21 | **2026-12-22** | `muhurat/griha-pravesh` in W: 432 impr, 4.63% CTR, pos 6.5, 31 sessions at **94% engaged** (baseline for #1322/#1325). `muhurat_searched` is **not** among the 20 event names in `ga4-events.json` (§10) |

### 3c. No traffic claim — nothing to score
#515 (unscoreable, posted once), #523, #528, #843, #885, #896, #959, #978, #838, #856, #1066, #1093 (cannot score: no export carries `page_location`, #1237), #1178, #1217, #1226, #1229, #1115, #1236, #1208, #1326, #1332, #1400, #1408, #1411, #1416. Their metrics are greps, counts or "event appears".

## 4. Confounds

| confound | read | consequence |
|---|---|---|
| Concurrent ships in W | `gh pr list --state merged` titles, 2026-10-25 → 11-23 (hit the 300 cap). Pages in the top 10 were edited repeatedly: debilitated-sun (#940 11-13, #1009, #1389 11-22), sade-sati (#690 11-03, #673 11-02, #1382 11-22), rahu-ketu (#1122 11-16, #1113 11-16), jupiter-10th (#1126, #1054), 7th-lord (#979, #981), career-during-sade-sati (#1082 earlier). Site-wide tool-link edits (#518 slices, #1179 2026-11-17) | no single ship is attributable for the W vs P rise; per-page deltas are scored only on each issue's own window |
| Google has not re-crawled many edits | `index-status.json` 2026-11-23: 168 of 214 URLs "changed after Google's last crawl" (§9) | W position and CTR on edited pages partly predate Google seeing the edit |
| Seasonality | Dhanteras 2026-11-06, Diwali 2026-11-08, Chhath 2026-11-15 in W (`festival_registry.py`). None of the top-10 pages is a festival page; `gochar-2026` is time-bound (transit year) | seasonal share **not determined**: no year-earlier window exists |
| Page working? | `verify-production.yml`, last 100 runs (2026-11-17T04:57Z → 2026-11-24T03:39Z): 92 success, **3 failure** (2026-11-17 08:10, 13:27, 18:12), 5 cancelled. **No failure in the last 6 days.** Failure causes not read. `llm-usage.json` shows **0 fallbacks** in the last 7 days | pages were up for the 2026-10-25 → 11-21 window except possibly on 2026-11-17; Groq-ceiling failures: 0 recorded |
| Sample size | 28-day page deltas on < 30 clicks | #311, #329, #1074 and #508 are at or under their own floors |
| Automated traffic | §5 | Direct is 281 of 801 sessions at 19% engaged; raw sessions overstate people |

## 5. Lever 1 — Growth against the previous window

### Site level

| metric | W (2026-10-25 → 11-21) | P (2026-09-27 → 10-24) | change | source |
|---|---:|---:|---:|---|
| GSC impressions (page-row sum) | 30,795 | 12,284 | **+151%** | `gsc-trend-page.json`; W property total 30,711 |
| GSC clicks (page-row sum) | 409 | 128 | **+220%** | same |
| GA4 sessions (daily sum) | 804 | **not measured** | – | no previous GA4 window (#1205) |
| GA4 active users (daily sum, not unique people) | 703 | **not measured** | – | |
| GA4 organic sessions (landing × channel rows) | 515 | not measured | – | Organic Search, 293 engaged (57%), 151 s per session |
| Direct sessions | 281 | not measured | – | 54 engaged (19%), 52 s per session |
| Returning user-days | 89 (**12.7%**) | not measured | – | `ga4-daily.json`, `status: ok`; user-days, not people |
| `admin_sessions` | 13 in W (all 2026-10-25 → 11-09) | – | – | **0 on every day from 2026-11-12** — no internal-traffic leak |
| Discover | **0 clicks, 0 impressions** | – | – | measured zero, all 28 days |

### Inside W, by 7-day block (GSC `gsc-daily.json`, GA4 `ga4-daily.json`)

| block | impressions | clicks | sessions | active users (sum) | returning users (sum) |
|---|---:|---:|---:|---:|---:|
| 10-25 → 10-31 | 7,047 | 83 | 161 | 133 | 26 |
| 11-01 → 11-07 | 7,929 | 101 | 203 | 191 | 19 |
| 11-08 → 11-14 | 9,115 | 150 | 255 | 221 | 25 |
| 11-15 → 11-21 | 6,620 | **75** | 185 | 158 | 19 |

The last block is **27% lower on impressions and 50% lower on clicks** than the block before. Daily GSC impressions 11-16 → 11-21: 908, 811, 798, 815, 1,001, 1,177 (against 1,337–1,433 on 11-11 → 11-14); position stayed 6.0–7.4. The last two days are rising. Cause **not determined** (post-Diwali/Chhath calendar, a re-rank, or late GSC data). Six days is not a trend; the next run settles it.

### Which pages drive the change (W vs P, GSC page rows)

`/learn/*` articles are 28,870 of the 30,795 W impressions and 355 of 409 clicks. The gain is concentrated in articles whose impressions grew 2–200×: gochar-2026 (+3,310), jupiter-10th (+1,835), debilitated-sun (+1,495), 7th-lord (+1,259), rahu-ketu (+1,180), career-during-sade-sati (+950), sade-sati (+756), planets-in-7th (+953), 10th-lord-in-6th (+678). **Structural vs seasonal:** a ranking-footprint gain on articles at similar or better position, with one time-bound exception (gochar-2026 is 18% of the impression gain (3,310 of 18,511), and its engaged rate is 36% at 26 s per session, §6). Not determined further.

### Anomaly days — every day in `spikes` and `watch` (`ga4-anomalies.json`), checked against search clicks that day

| date | tier | active users (median 22) | source and landing (top) | engagement | GSC clicks that day | Discover | reading |
|---|---|---:|---|---|---:|---:|---|
| 2026-11-06 | spike | 57 | (direct) 21 of 50 sessions; top row `/rashifal/aries` 6 sessions at 17% engaged; also `/r/zzzzzz`, `/numerology` | 21 of 50 session rows are in 0%-engaged cohorts; "(not set)/desktop/United States" 10 and "Chrome/desktop/United States" 6 at 0% | 17 | 0 | **mixed: automated traffic, not growth.** The organic rows (google/organic 14) are readers |
| 2026-11-15 | spike | 51 | google / organic 15 (`rahu-mahadasha-ketu-antardasha` 6 at 83% engaged); (direct) 21 incl. `/panchang/2026-12-02` 5 sessions at 0% / 1.6 s | Chrome/mobile/**China** 9 sessions at 0%; Chrome/mobile/India 17 at 59% | 14 | 0 | organic part is real; the direct part is automated (China cohort, a future-dated panchang URL). Search clicks flat; **not Discover** |
| 2026-11-10 | watch | 40 | (direct) 23 of 35 incl. `/matching` 5 at 0%; bing / organic 4 | 23 of 35 rows are 0%-engaged; "(not set)/desktop/United States" 9, "Chrome/desktop/United States" 8 | 14 | 0 | **automated** (same cohort as 11-06) |
| 2026-11-12 | watch | 34 | google / organic 17 (`/muhurat/griha-pravesh` 4 at 100%) | Chrome/mobile/India 14 at 71% | 24 | 0 | real readers; search clicks high that day |
| 2026-11-09 | watch | 32 | google / organic 26 (jupiter-10th 5, rahu-ketu 5, griha-pravesh 5) | Chrome/mobile/India 15 at 53% | 21 | 0 | real readers |
| 2026-11-14 | watch | 32 | google / organic 28 (`rahu-mahadasha-ketu-antardasha` 10; chronic-health 5; `/` 4) | Chrome/mobile/India 11 at 82%; Chrome/mobile/**Indonesia** 9 at 67% | 23 | 0 | real readers; search clicks high |

A recurring cohort (browser "(not set)" or Chrome, desktop, United States, 0% engaged) appears on 2026-11-06 and 11-10. **Its window-wide size is not measured** (#1364, open).

## 6. Lever 2 — Where time is spent (`verify-first.json`, `ga4.json`, W)

| page | sessions | engaged | engaged rate | avg engagement s | GSC impr | pos |
|---|---:|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha | 71 | 44 | 62% | 146 | 3,425 | 6.4 |
| / | 62 | 37 | 60% | **255** | 217 | 5.7 |
| /muhurat/griha-pravesh | 31 | 29 | **94%** | 90 | 432 | 6.5 |
| /learn/10th-lord-in-6th-house-career | 30 | 18 | 60% | 165 | 850 | 6.9 |
| /learn/gochar-2026-planetary-transits | 47 | 17 | **36%** | **26** | 3,326 | 4.9 |
| /learn/career-during-sade-sati | 31 | 15 | 48% | 215 | 1,364 | 5.4 |
| /learn/rahu-mahadasha-career-problems | 26 | 14 | 54% | **269** | 1,195 | 5.7 |
| /learn/sade-sati | 23 | 13 | 57% | 264 | 2,033 | 6.6 |
| /learn/debilitated-sun-career | 24 | 10 | 42% | 223 | 2,904 | 6.5 |
| /learn/jupiter-in-10th-house-career | 25 | 10 | 40% | 60 | 2,192 | 7.0 |

Whole property (`ga4.json`): 801 sessions, 348 engaged (43%), 93,358 engagement seconds (**117 s** per session). By channel: Organic Search 515 sessions at 57%, 151 s; Direct 281 at 19%, 52 s; AI Assistant 4; Unassigned 1.

Pages worth a look for "traffic to a page that is not working":

| landing (folded) | sessions | engaged rate | avg engagement s | channels | reading |
|---|---:|---:|---:|---|---|
| /learn/chronic-health-issues-kundli | 20 | **20%** | **8** | Organic 15, Direct 5 | pos 4.7, 532 impressions, 12 clicks; readers leave at once. Cause **not determined** |
| /learn/gochar-2026-planetary-transits | 47 | 36% | 26 | Organic 28, Direct 18 | the page now gaining most from search is the one readers abandon fastest among the top five |
| /learn/griha-pravesh-muhurat-2026-2027 | 14 | 14% | 4 | Organic 9, Direct 4 | |
| /learn/financial-struggles | 11 | **0%** | 0 | **Direct 11** | GSC impressions 1 in W (34 in P): direct sessions on a page that left search are automated or referred; Direct cohort, not growth |
| "(not set)" landing | 19 | 5% | 12 | Organic 16 | organic sessions with no landing recorded; **not determined** |
| /admin/ops | 13 | 38% | 4 | Direct 13 | all before 2026-11-12 (see `admin_sessions`) |

Tool funnels visible (W, `ga4-events.json`, event counts not users; `session_start` 802):

| step | count | note |
|---|---:|---|
| `page_view` | 1,479 | 1.84 per session |
| `feature_view` | 722 | |
| `form_start` | 114 | |
| `kundli_generated` | 50 | 44% of `form_start` — but the event counts re-renders on some paths (#1068 closed); read as an upper bound |
| `ask_answered` | 129 | the one high-volume generative path |
| `tool_submitted` | 21 | #1226 |
| `cta_click` | **20** (2.5% of sessions) | 12 of 20 have a named from/to; 8 are `(not set)`. From `/learn/*` to tools: `/` 4, `/kundli` 3, `/dasha` 2, `/kaal-sarp-check` 1, `/numerology` 1, `/sade-sati-check` 1. Partial history (from 2026-11-03). No impression event, so whether the click rate or the exposure is low is not determinable |
| `matching_completed` | 1 | |
| `dosha_check_completed` | 1 | |
| `subscribe_completed` | 1 | |
| `feedback_sent` | 2 | |
| `dasha_deep_dive_viewed` | 2 | |
| `muhurat_searched` | **absent** | not among the 20 event names |

Kundli GA4 ↔ server ratio: **not computable** — `measurements/kundli-submissions.json` does not exist in this run. GA4 window 2026-10-25 → 11-21 is 28 days; I did not divide anything by `totals.fresh_generations`. Writing "ratio not computable" for #1068/#1272.

## 7. Lever 3 — Errors per route

| source | window | reading |
|---|---|---|
| `llm-usage.json` | last 7 days, generated 2026-11-24T05:07Z | 164 calls, 111 cache hits (**67%**), 53 misses. Input 166,431 tokens, output 30,523. **`fallbacks`: 0; `fallback_reasons`: {}** |
| peak day | `peak_day_tokens` 6,733 on 2026-11-22; `peak_day_measured_tokens` **43,421** on 2026-11-18 | 43,421 is 21.7% of the 200,000 TPD the repo cites. #925 says a peak day used 83%; this file does not reproduce that, and I did not read `collect_llm_usage.py` to say which field is the day's total |
| `verify-production.yml` | last 100 runs, 2026-11-17T04:57Z → 11-24T03:39Z | 92 success, 3 failure (all 2026-11-17), 5 cancelled; last 12 runs all success |

| route | calls | hits | hit rate | input tokens | tokens per measured call | errors / fallbacks | tracked by |
|---|---:|---:|---:|---:|---:|---|---|
| natal | 91 | 80 | 87% | 72,159 | 6,559 (11 measured) | 0 | – |
| ask | 34 | 0 | **0%** | 78,921 | 2,321 (34 measured) | 0 | per-visitor by nature; nothing here says it is over budget |
| rashifal | 28 | 28 | 100% | not measured | not measured | 0 | the nightly job (#515) serves it from cache |
| matching | 5 | 0 | 0% | 9,352 | 1,870 | 0 | – |
| monthly | 3 | 2 | 66% | 2,116 | 2,116 (1 measured) | 0 | – |
| today | 3 | 1 | 33% | 3,883 | 1,941 (2 measured) | 0 | – |

No route has an error or fallback in the 7 days. The earlier "errors not measured" gap (#1208, closed 2026-11-23) is closed in this file. Still **not measured**: HTTP error rate per route (the file records LLM fallbacks only, not 5xx on non-LLM routes), and the cause of the 3 `verify-production` failures on 2026-11-17.

## 8. Lever 4 — Search demand (partial: query export covers 14% of impressions)

Themes from `gsc-trend-query.json`, W vs P. **The export has no page column**, so the "page" is named by topic, not measured (#1432 filed this run).

| theme (W, visible queries only) | impressions W (P) | clicks W | pos W (P) | existing page | note |
|---|---:|---:|---:|---|---|
| "sun debilitated in which sign" family (4 wordings, e.g. 341 + 156 + 75 + 71) | 643 (58) | 2 | 5.9–7.3 | `/learn/debilitated-sun-career/` | the page's CTR is 0.55% on 2,904 impressions. #835 pending |
| "rahu mahadasha ketu antardasha" family (15+ wordings; head 362 impr, 13 clicks) | 763 across the 12 wordings listed (head query 362) | 20 | 6.3–10.2 (P 9.2–16.6) | `/learn/rahu-mahadasha-ketu-antardasha/` | every wording moved up 2–3 positions vs P |
| "jupiter in 10th house", "guru in 10th house", "jupiter in pisces 10th house" | 121 + 90 + 30 (P 0) | 1 | 8.3–10.9 | `/learn/jupiter-in-10th-house-career/` | new in W; #1073 added Pisces/Sagittarius sections, pending |
| "10th lord in 6th house", "10th house lord in 6th house" | 94 + 30 | 1 | 8.2–8.6 (P 9) | `/learn/10th-lord-in-6th-house-career/` | |
| "which mahadasha is best for career" | 59 (P 0) | 0 | 8.4 | `/learn/vimshottari-dasha-explained/` (#1072) | pending |
| "bhagya chart" | 27 (15) | 3 | 6.6 (5.9) | not determined | likely the brand/tool; not verified |
| "yes" | 117 (10) | 0 | 3.7 | **not determined** | a one-word query at position 3.7: ambiguous, no page can be named. Not a theme to act on |

- **Queries with no page: not determinable from this export.** I name no new page. The three clusters new in W (sun debilitated, jupiter 10th, 10th lord in 6th) each have a page and a pending ship.
- `/matching` fell from position 4.4 to 10.1 on 347 → 117 impressions (§2). `/festivals` sits at 38.6.
- Cannibalisation check: the page-level band list has `7th-lord-placement-marriage-guide` (1,560 impressions, 7.2) and `planets-in-7th-house-marriage` (1,448, 6.8) — two pages in one theme. #1430 (open) already covers the 7th-house pair. I do not propose a new page.

## 9. Lever 6 — Index status (`measurements/index-status.json`, generated 2026-11-23T03:12Z)

| count | value |
|---|---:|
| URLs in sitemap, inspected | 214 of 214, 0 errors, 214 of 2,000 daily quota |
| indexed / not indexed | **165 / 49** |
| stale ("changed after Google's last crawl") | **168** |
| canonical mismatch / blocked / unknown | 0 / 0 / 0 |

Not indexed, ranked by impressions (as the file states them; all "Crawled – currently not indexed"): ashwini-nakshatra 83 (last crawl 2026-09-18), pushya-nakshatra 82 (10-29), rohini-nakshatra 33 (10-06), **vivah-muhurat-2027 33 (10-01)**, swati-nakshatra 27 (10-29), dhana-yoga-wealth-combinations 26, jupiter-remedies 23, marriage-delayed 22 (11-13), ketu-remedies 14, marriage-timing-kundli 13. `vivah-muhurat-2027` is a time-bound page that Google has crawled and declined to index since 2026-10-01; `griha-pravesh-muhurat-2026-2027` has 14 sessions at 4 s average engagement.

The ten largest pages are all "changed after the last crawl". What the new file adds over the 2026-11-19 file the last three reports used:

| page | impr | last edit (file) | `lastCrawlTime` | crawled since the ship under test? |
|---|---:|---|---|---|
| /learn/sade-sati/ | 2,072 | 2026-11-22T17:01Z | **2026-11-20T04:32Z** (was 10-23 in the 11-19 file) | title change #690 merged 11-03; Google first re-fetched it between 11-19T20:05Z and 11-20T04:32Z, **16–17 days later** — commented on #685 |
| /learn/debilitated-sun-career/ | 2,999 | 2026-11-22T18:40Z | 2026-11-16T15:56Z | #940 merged 11-13: crawled **3 days later**, so #835's window sees it. The later 11-22 edit (#1389) has not been crawled |
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,526 | 2026-11-16T04:15Z | 2026-11-08T08:35Z | **no** — #1122 (11-16) not yet seen as of the file, 7 days |
| /learn/jupiter-in-10th-house-career/ | 2,111 | 2026-11-16T06:26Z | 2026-11-11T05:04Z | **no** — #1126 not yet seen |
| /learn/gochar-2026-planetary-transits/ | 3,191 | 2026-11-17T04:56Z | 2026-11-13T04:17Z | no (edit after crawl) |
| /learn/7th-lord-placement-marriage-guide/ | 1,500 | 2026-11-16T03:32Z | 2026-11-08T10:46Z | no |
| /learn/planets-in-7th-house-marriage/ | 1,395 | 2026-11-14T04:04Z | 2026-11-01T22:59Z | no (22 days) |
| /learn/career-during-sade-sati/ | 1,367 | 2026-11-22T17:01Z | 2026-11-12T16:18Z | no |
| /learn/rahu-mahadasha-career-problems/ | 1,159 | 2026-11-16T03:17Z | 2026-11-11T20:15Z | no |
| /learn/10th-lord-in-6th-house-career/ | 852 | 2026-11-18T02:13Z | 2026-11-11T17:38Z | no |

Each editorial commit resets a page's freshness, so a page edited for wording on 11-22 (#1382, #1389) shows "changed after crawl" again even when Google had seen the ship that matters. This list is a request for a re-crawl on the ten largest pages; **I have no write path to request indexing**. For `chief` or the owner (#1065 holds the export).

## 10. Lever 5 — Content opportunities (next 6–8 weeks, 2026-11-24 → 2027-01-19)

Dates read from `festival_registry.py` this run (`dates={...}` per entry; the file's comments record "verified 2026-11-21 · Drik Panchang, New Delhi"). I did not re-verify any date against an almanac.

| date | festival (slug) | learn article in the registry |
|---|---|---|
| 2026-11-24 | kartika-purnima | none (`learn_article_for` returns None) |
| 2026-12-01 | kalabhairav-jayanti | none |
| 2026-12-14 | vivah-panchami | none |
| 2026-12-20 | gita-jayanti | none |
| 2026-12-23 | dattatreya-jayanti | none |
| 2027-01-15 | makar-sankranti | none |
| 2027-01-15 | pongal | none |

- All seven registry entries in the window have no linked `/learn` article. Search demand for them in W: none of these appears among the 137 landing pages in `gsc-all.json`; the festivals index `/festivals` has 266 impressions at position 38.6 and 0 clicks. product-manager decides whether a page is worth building; the existing surface is `/festivals`.
- **Lohri is not in the registry** (`grep -i lohri` over `festival_registry.py` and `festivals.py` returns nothing). I state no Lohri date.
- Ekadashi and Pradosh observances in the window come from `lunar_observances`, not the registry, and I did not read them here.
- **Annual pages and their year:** `gochar-2026-planetary-transits` (3,326 impressions, pos 4.9, 28 days) — a 2026 transit-year page; `gochar-2027-planetary-transits` exists since #1148 (2026-11-17) and has **0 impressions** in W. `diwali-muhurat-2026` (76 impressions, pos 11.2) and `karva-chauth-2026` (7 impressions) are past-event pages for 2026. `vivah-muhurat-2027` (28 impressions, pos 9.4, not indexed). `griha-pravesh-muhurat-2026-2027` (14 sessions).
- `/panchang/2026-12-02` has 35 impressions at position 9.1 in W, and 5 zero-engagement direct sessions landed on it on 2026-11-15 (§5).

## 11. Lever 7 — Measurement gaps, checked against my last three reports (2026-11-21, 11-22, 11-23)

| gap | in each of the last three? | open issue | action |
|---|---|---|---|
| GA4 previous window (sessions/users vs P) | yes, and this run | **#1205** (open, `needs-human-review`) | none: covered |
| `page_location` / query strings in GA4 exports | yes | **#1237** | none: covered |
| Per-page × per-day export | yes | **#953**, **#1076** | none: covered |
| Shallow checkout: no `git log --since` | yes (this run: unshallowed with `git fetch --unshallow`, 100 commits since 2026-10-25) | **#666**, **#974** | none: covered |
| Server-side kundli submission count | yes | **#1272** | none: covered |
| Share of Direct traffic that is automated | yes | **#1364** (open, `qa-pass`) | none: covered |
| Errors / LLM fallbacks per route | yes (all three) | #1208 **closed 2026-11-23; the file now carries the field** | resolved |
| Newer `index-status.json` than 2026-11-19 | yes | #1065 | **resolved this run**: the file is dated 2026-11-23 |
| **Which page serves which query** (query export has no page column) | **yes — 11-21, 11-22, 11-23 ("Landing page per query is not determined") and this run** | **none** | **filed #1432** |
| `muhurat_searched` absent from `ga4-events.json` (half of #1336's metric) | 11-22 and 11-23 (first named 11-22) — **two** of the last three, third time this run | none | not filed: two of the last three reports. It meets the rule when the next report is written; #1336's window opens 2026-12-22 |

## 12. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| GA4 sessions and users against the previous window | `ga4-trend.json` written by `agent-measure` (#1205) |
| Whether the objective (ten highest-impression queries into the top 5) is moving | cannot be recovered: 86% of impressions are withheld from the query export. Page proxy: 1 of the top 10 pages at ≤ 5.0 |
| Which page serves a visible query | a `query × page` GSC export (#1432, filed this run) |
| Window-wide share of Direct traffic that is automated | cohort export (#1364) |
| Why `/matching` lost 6 positions between P and W | per-page × per-day export (#953, #1076) |
| Why the 2026-11-15 → 11-21 block fell 50% on clicks | the next run's daily rows; four more days |
| Whether `chronic-health-issues-kundli` (8 s average engagement, 20% engaged) is broken or just a bad-intent landing | page render check plus a scroll-depth read; not in these files |
| HTTP errors per non-LLM route; cause of the three 2026-11-17 `verify-production` failures | Cloud Run request log; failure logs of those runs |
| Whether any spike day was Discover | nothing to settle: Discover is 0 on all 28 days |
| Whether Google has seen the 11-16 ships (#1075, #1073) | the next `index-status.json` |

## 13. Handed back

| item | value |
|---|---|
| Issues filed | **#1432** (query → page export) |
| Comments posted | #685: one note — Google's first re-crawl of `/learn/sade-sati/` was 2026-11-20, 16–17 days after the title change |
| Verdict changes | none: #311 MISS, #276 BAR MET (not attributable), #329 UNSCOREABLE, #1277 MET all unchanged |
| Timers | 16 lines in `/tmp/analyst-timers.txt` (#553 12-01, #426 12-03, #570/#685/#508 12-04, #518 12-07, #735 12-12, #835 12-14, #1075/#1073/#1074 12-17, #1072/#1071 12-18, #1322/#1325/#1336 12-22) |
| The one number to read first | clicks 409 vs 128 and impressions 30,711 vs 12,284 (W vs P): the footprint grew ~2.5×, and the last 7 days are 50% below the block before it — the growth is real, concentrated in 10 `/learn` pages, and not yet shown to be durable |
