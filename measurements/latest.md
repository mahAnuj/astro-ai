# Analyst report — 2026-11-26

**Window for every number: W = 2026-10-27 → 2026-11-23** (28 days; the last 3 are excluded: GSC lags 2–3 days, GA4 24–48h).
**Previous window P = 2026-09-29 → 2026-10-26** (GSC and GA4 trend files both carry it this run).
Everything below was read from this run's `/tmp/*.json` and `/tmp/measure/*.json`, from `gh` this run, from `measurements/index-status.json` captures (git history) or from `festival_registry.py` this run. Anything not read is marked **not measured**.

## 0. Coverage — read before any number

| file | window | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-daily.json` (site, by date) | W | 100% of 31,350 impressions | no | 440 clicks |
| `gsc-all.json` (`dimension: page`) | W | 100%; page rows sum 31,433 vs property 31,350 | no | 139 pages |
| `gsc-band.json` (`dimension: page`) | W | whole fetch 100%; **printed 100 rows = 23,129 impressions = 74%** (`emitted_coverage_pct`) | no | band figures are the printed rows |
| `gsc-trend-page.json` | W vs P | W 100%; P coverage not stated | no | page-row sums: W 31,433 impr / 440 clicks; P 13,288 impr / 139 clicks |
| `gsc-trend-query.json` (`dimension: query`) | W vs P | **14%** of W impressions visible (981 query keys vs 277 in P) | no | Google withholds the rest; no conclusion about the whole band from it |
| `ga4.json` (landing × channel) | W | 100% of 817 sessions | no | 162 rows, 105 raw landings |
| `ga4-trend.json` | W vs P | totals plus 4 channels | – | **present for the first time this run** (#1205) |
| `ga4-daily.json` | W | 28 of 28 days with traffic | – | daily sessions sum **820**, users sum 723. Session totals do not reconcile (817 property / 817 rows / 818 `session_start` / 820 daily); each is quoted from its own file |
| `ga4-events.json` | W | 23 event names, `events_total` 5,300 | no | `cta_click` exists only from 2026-11-03; matching/numerology/muhurat/dosha events only from 2026-11-18 (partial history) |
| `ga4-anomalies.json` | W | 2 spikes + 5 watch days, 0 omitted | – | |
| `gsc-discover.json` | W | **0 clicks, 0 impressions on all 28 days**, `top_pages` empty | – | a measured zero |
| `kundli-submissions.json` | 2026-10-30 → 11-26 | present for the first time (#1409) | – | 23 of 28 days have `probe: null` |
| `index-status.json` | generated 2026-11-26T03:43Z | 214 of 214 inspected, 0 errors | – | `partial: false` |
| `llm-usage.json` | last 7 days, generated 2026-11-26T03:21Z | – | – | has `fallbacks` and `fallback_reasons` |

## 1. The 6–20 position band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **Not measurable as worded:** the query export sees 14% of impressions, so the ten highest-impression queries cannot be named. The page proxy below is the only readable figure.

| the ten pages with most impressions, W | impr | clicks | CTR | position (P) |
|---|---:|---:|---:|---:|
| gochar-2026-planetary-transits | 3,472 | 29 | 0.84% | **4.9** (6.1) |
| rahu-mahadasha-ketu-antardasha | 3,222 | 58 | 1.80% | 6.5 (7.1) |
| debilitated-sun-career | 2,791 | 18 | 0.64% | 6.5 (6.4) |
| jupiter-in-10th-house-career | 2,353 | 27 | 1.15% | 6.9 (7.0) |
| sade-sati | 1,950 | 18 | 0.92% | 6.7 |
| 7th-lord-placement-marriage-guide | 1,696 | 18 | 1.06% | 7.1 (7.6) |
| planets-in-7th-house-marriage | 1,541 | 13 | 0.84% | 6.8 (5.8) |
| career-during-sade-sati | 1,387 | 25 | 1.80% | 5.4 (6.6) |
| rahu-mahadasha-career-problems | 1,216 | 23 | 1.89% | 5.7 |
| panch-mahapurush-yoga | 1,099 | 17 | 1.55% | 7.1 (6.9) |

**1 of the 10 at position ≤ 5.0** (gochar-2026, which sits outside the 6–20 band). Two more are at 5.4 and 5.7. Seven are still at 6.5–7.1. The footprint grew (§3), the rank within it has barely moved.

### Band list, ranked by clicks missing against the band's own median CTR (1.48%, pages ≥ 300 impressions, n = 18)

| page | impr | clicks | CTR | position | clicks missing at 1.48% |
|---|---:|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,791 | 18 | 0.64% | 6.5 | **23.3** |
| /learn/sade-sati/ | 1,950 | 18 | 0.92% | 6.7 | 10.9 |
| /learn/planets-in-7th-house-marriage/ | 1,541 | 13 | 0.84% | 6.8 | 9.8 |
| /learn/jupiter-in-10th-house-career/ | 2,353 | 27 | 1.15% | 6.9 | 7.8 |
| /learn/7th-lord-placement-marriage-guide/ | 1,696 | 18 | 1.06% | 7.1 | 7.1 |
| /learn/mangal-mars-in-vedic-astrology/ | 640 | 3 | 0.47% | 7.7 | 6.5 |
| /learn/manglik-dosh/ | 489 | 3 | 0.61% | 6.9 | 4.2 |
| /learn/shukra-venus-in-vedic-astrology/ | 416 | 2 | 0.48% | 6.2 | 4.2 |
| /learn/vimshottari-dasha-explained/ | 438 | 3 | 0.68% | 7.6 | 3.5 |

CTR outlier outside the band: **gochar-2026** at position 4.9 takes 0.84%; at 1.48% it would take about 51 clicks, not 29 (22 missing). That is a title/meta shape, not a content one. Counter-case: `/muhurat/griha-pravesh` 531 impr, **4.33%** at 6.4 (23 clicks); `/numerology` 200 impr, 4.50% at 6.1. Tool pages convert at about 3× the article band at the same position.

## 2. Scoring closed issues that carried a `thesis:` and a `metric:`

The fetch cannot split a page at its deploy date (#490); a window is clean only if its start (today − 31 = 2026-10-26) is on or after the deploy. Only #311, #276, #329 and #515 are older than that. Every verdict below was posted once earlier and is **unchanged**; nothing was re-posted.

| issue | deployed | status | verdict | this run's supporting read (W, not a re-score) |
|---|---|---|---|---|
| **#311** manglik/band title+meta | 2026-10-13 | scored 11-13 | **MISS**: CTR 0.937% vs ≥ 1.5% bar | manglik-dosh now 489 impr, 3 clicks, 0.61% |
| #276 rahu-ketu CTA | 2026-10-14 | scored 11-14 | BAR MET (1.42 vs 1.20 pages/session), **not attributable to the CTA** | rahu-ketu Organic: 64 sessions, 1.61 pages/session, 37.5% bounce; 1 `cta_click` to `/dasha` in W |
| **#329** manglik-dosh CTA | 2026-10-14 | scored 11-14 | **UNSCOREABLE: 3 vs 10 floor** | W: 0 `cta_click` rows name this page |
| #515 nightly rashifal | 2026-10-24 | scored 11-09 | UNSCOREABLE at this traffic | `/rashifal*` landings: 19 sessions in W (Direct 15, Organic 4) |
| #1277 returning users + admin count | 2026-11-20 | MET 11-21 | unchanged | returning 92 user-days = 12.7%; `admin_sessions` 0 on every day 2026-11-10 → 11-23 |
| **#1115** GA4 previous window | 2026-11-18 | **flipped this run: NOT MET → MET** | posted on #1115, pointer on #1205 | 2 windows now in `ga4-trend.json` |
| #1400 re-capture index status | 2026-11-23 | **scored this run** (read-only measurement) | delivered; top-10 re-crawled **2 → 1 → 6 of 10** (11-19 → 11-23 → 11-26) | posted on #1400 |
| #1068 kundli ratio | 2026-11-17 | **ratio not computable** (note posted, #1068 is closed) | see §6 | 3 of 28 GA4 days are in `non_probe_dates` |

**Pending, scoreable from a stated date (note already on each issue; timers written to `/tmp/analyst-timers.txt`):**

| issue | thesis in one line | scoreable from |
|---|---|---|
| #553 panch-mahapurush yoga link | CTA to matching/kundli | 2026-12-01 |
| #426 Saturn exit date | guard on sade-sati/gochar | 2026-12-03 |
| #570, #685, #508 | cta_click, sade-sati title, /matching title | 2026-12-04 |
| #518 learn → tool route | 71% of articles had no route to a tool | 2026-12-07 |
| #735 admin analytics off | `admin_sessions` 0 | 2026-12-12 |
| #835 debilitated-sun answer-first lede | 480+ "which sign" impr, 0 clicks | 2026-12-14 |
| #1075, #1073, #1074 | rahu-ketu intents, jupiter-10th, panchang titles | 2026-12-17 |
| #1072, #1071 | vimshottari answer, gochar-2027 | 2026-12-18 |
| #1217, #1226, #1229 | completion events, tool_submitted, login/share | 2026-12-19 |
| #1322, #1325, #1336 | muhurat finder honesty, next-5 dates, share URL | 2026-12-22 |
| **#1416, #1411** (new notes this run) | `tool_error` for /matching and dosha checks | 2026-12-24 |

**Not scoreable from GA4/GSC (code-state metrics, already checkable by a grep or a test):** the QA follow-ups #1483, #1457, #1451, #1450, #1439, #1408, #1376 and similar; #1466 (token metric in `loop.json`, scored after a read log exists); #1178 (said so on 11-19).

**Early read, not a score (window still contains the deploy):** #1336 asked for ≥ 10 `/muhurat` landings with query parameters; W holds **0** landing rows with a query string, but the deploy (2026-11-21) is 2 days before W ends. #1325/#1322: `/muhurat/griha-pravesh` is at 531 impr, position 6.4, CTR 4.33%, 33 sessions, 29 engaged (88%), bounce 9.4%; those are the baselines' neighbours (position 6.1, CTR 5.91%, bounce 8.7% at filing), which fall inside the "no MISS" bounds so far. The window mixes before and after.

**Misses, stated plainly:** #311 missed its bar by 0.56 pp; #329 never reached a sample; #276's bar was met by a page that also gained from search (not the CTA); #685 and #835 target the two biggest CTR gaps in §1 (sade-sati, debilitated-sun) and neither is scoreable yet, so **the largest single CTR gap on the site (debilitated-sun-career, 0.64% on 2,791) still shows no response to #835's lede, merged 2026-11-13**; Google had not re-crawled it after the 11-22 edit (§7).

## 3. Confounds, named before any delta

| confound | what the files say |
|---|---|
| Concurrent ships | `git log origin/main --since=2026-11-12`: **330 commits**. Of those touching traffic pages: the `/learn` answer-first and title edits (#835, #685, #1072–#1075, #1148 gochar-2027, #1430 7th-house pair), the muhurat finder slices (#1017: #1322, #1325, #1336, #1341, #1348), Manglik/remedies copy edits (#1368–#1389, #1418). **I attribute the movement to no single ship.** |
| Seasonality | Sade Sati / Saturn transit and griha pravesh topics are calendar-driven (Kharmas starts mid-December per the finder's own zero-result logic, #1336). A rise in `/learn/gochar-2026-planetary-transits` (140 → 3,472 impr) is the end-of-year transit season as much as any ship. Not separable from these files. |
| Was the page reachable | `verify-production.yml`, last 100 runs (2026-11-18 → 11-26): **95 success, 3 cancelled, 1 failure**. The one failure (run 45635418554, 2026-11-25 14:33Z) was `DEPLOY_GATE: timeout` — no new revision appeared for a superseded push; it is the deploy gate (#341), not a page error. LLM `fallbacks: 0` over 7 days. |
| Sample size | 817 sessions in 28 days. Most page-level GA4 figures rest on single digits; CTR on 3 clicks (manglik-dosh) is not a rate. |
| Index lag | the ten largest pages' re-crawl state is in §7; a title edit that Google has not re-fetched cannot have moved CTR yet. |

## 4. Lever 1 — Growth against the previous window

| site level | P | W | change | source |
|---|---:|---:|---:|---|
| GA4 sessions | 424 | **817** | +92.7% | `ga4-trend.json` |
| GA4 active users | 322 | **680** | +111.2% | same |
| GA4 new users | 312 | 672 | +115.4% | same |
| GA4 engaged sessions | 194 | 352 | +81.4% | same |
| engaged share of sessions | 45.8% | **43.1%** | −2.7 pp | derived (194/424, 352/817) |
| engagement seconds per session | 89.6 | **122.1** | +36% | derived (37,970/424, 99,719/817) |
| GSC impressions (page rows) | 13,288 | **31,433** | +136.6% | `gsc-trend-page.json` (P coverage not stated) |
| GSC clicks | 139 | **440** | +216.5% | same |

| GA4 channel | sessions P → W | engaged P → W | engaged share W |
|---|---|---|---:|
| Organic Search | 199 → **528** (+165%) | 109 → 297 | **56.3%** |
| Direct | 199 → 284 (+43%) | 72 → **54 (−25%)** | **19.0%** (P 36.2%) |
| AI Assistant | 19 → 5 (−74%) | 11 → 1 | 20% |
| Unassigned | 8 → 1 | 2 → 0 | 0% |

**Read:** the doubling is **organic and structural-looking**: Organic Search accounts for 329 of the 393 added sessions and 188 of 158 net added engaged sessions (Direct lost 18). **Direct added 85 sessions and lost 18 engaged ones; 19.0% engaged is the weakest cohort on the site.** `ga4-anomalies.json` names automated desktop-US traffic on two days (below), and `fetch_ga4.py --cohorts` (#1398, merged) has no file in this run to size the Direct share, so I do not say how much of Direct is automated. **AI Assistant referrals fell from 19 to 5 sessions** — small numbers, but the only channel that went the wrong way; cause not determined.

| page group (GSC page rows) | impr P → W | clicks P → W |
|---|---|---|
| /learn/* | 12,110 → **29,506** | 114 → **384** |
| /muhurat* | 166 → 638 | 10 → 27 |
| other (tools, snapshots etc.) | 434 → 545 | 5 → 18 |
| / | 123 → 219 | 9 → 8 |
| /festivals* | 240 → 248 | 0 → 0 |
| /rashifal* | 150 → 167 | 0 → 1 |
| /panchang* | 65 → 110 | 1 → 2 |

Top risers by impressions (P → W): gochar-2026 140 → 3,472 (clicks 0 → 29); jupiter-in-10th 372 → 2,353; 7th-lord-placement 304 → 1,696; debilitated-sun 1,585 → 2,791; planets-in-7th 411 → 1,541; career-during-sade-sati 506 → 1,387; rahu-ketu 2,460 → 3,222 (clicks 31 → 58); sun-mahadasha 9 → 507 (clicks 0 → 12). **All risers are `/learn` articles**; the tool pages did not grow with them.

Decay (position worse with ≥ 50 impressions in P): **`/matching` 346 → 116 impr, position 4.4 → 10.2** (clicks 1 → 3). #508 changed its title on 2026-11-03; #1076 holds the investigation and #508's own note says the title is not shown to have moved it. Smaller: pushya-nakshatra 138 → 58, mars-remedies 117 → 57, vidyarambh 93 → 60; `/festivals` sits at position 39.9, 0 clicks.

**Daily shape (GSC, W):** 2026-11-09 → 11-14 ran 1,295–1,433 impressions/day, then **11-16 → 11-19 fell to 798–908**, then 11-20 → 11-23 recovered (1,001 / 1,177 / 1,237 / 1,260). Clicks on 11-23 were **36**, the highest day of W (others 7–27). Position was flat at 6.0–7.4 all window. Whether the dip was a re-rank or a Google-side reporting gap is not determinable from these files.

**Returning users (`ga4-daily.json`, `status: ok`):** 92 returning user-days of 723, **12.7%** (user-days, not people).

**Internal traffic:** `admin_sessions` = 8 in W (10-28: 1, 11-04: 2, 11-05: 3, 11-09: 2). **0 on every day from 2026-11-10 onward, including every day from 2026-11-12.** No leak after #735; nothing filed.

### Every day in `spikes` and `watch` (7 days; median 22 active users). Discover is 0 clicks on every one

| date | users / sessions | tier | source named by the file | GSC clicks that day | read |
|---|---|---|---|---:|---|
| 2026-11-06 | 57 / 59 | spike | top row Direct `/rashifal/aries`; **19 of 50 sessions zero-engagement** (no-browser-name desktop US 10, Chrome desktop US 6, Chrome mobile US 3) | 17 | **Mixed, not growth.** ~19 sessions look automated; Organic readers of rahu-career-problems (4 sessions, 224 s) look real |
| 2026-11-10 | 40 / 43 | watch | Direct `/matching`; **21 of 35 sessions zero-engagement**, desktop US | 14 | **Automated, not growth** |
| 2026-11-15 | 51 / 56 | spike | google / organic, rahu-ketu (6 sessions), 30% engaged, 52.9 s, Chrome mobile India | 14 | Real readers; **source unexplained**: the file's "flat GSC clicks means Discover" hint does not hold, Discover is 0 and clicks are an ordinary 14 |
| 2026-11-09 | 32 / 37 | watch | google / organic, jupiter-10th (5), 53% engaged, 127 s, Chrome mobile India | 21 | Real readers, search-driven |
| 2026-11-12 | 34 / 37 | watch | google / organic, griha-pravesh (4), 38% engaged, 53 s | 24 | Real readers, search-driven |
| 2026-11-14 | 32 / 47 | watch | google / organic, rahu-ketu (10), 51% engaged, 111 s | 23 | Real readers, search-driven |
| 2026-11-23 | 38 / 42 | watch | google / organic, griha-pravesh (4), 35% engaged, 160 s | **36** | Real readers; matches the day's click peak |

## 5. Lever 2 — Where time is spent (`verify-first.json`, `ga4.json`, W)

| page (path folded across query strings) | sessions | engaged | engaged rate | avg engagement s | GSC impr / pos |
|---|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha | 70 | 41 | 59% | 128 | 3,223 / 6.5 |
| / | 60 | 35 | 58% | **270** | 219 / 5.7 |
| /muhurat/griha-pravesh | 33 | 29 | **88%** | 95 | 531 / 6.4 |
| /learn/10th-lord-in-6th-house-career | 28 | 18 | 64% | 166 | 812 / 6.8 |
| /learn/gochar-2026-planetary-transits | 49 | 17 | **35%** | **26** | 3,472 / 4.9 |
| /learn/career-during-sade-sati | 30 | 16 | 53% | 230 | 1,387 / 5.4 |
| /learn/rahu-mahadasha-career-problems | 29 | 14 | 48% | 242 | 1,216 / 5.7 |
| /learn/sade-sati | 25 | 13 | 52% | 204 | 1,950 / 6.7 |
| /learn/debilitated-sun-career | 24 | 12 | 50% | 231 | 2,791 / 6.5 |
| /learn/7th-lord-placement-marriage-guide | 30 | 11 | **37%** | **45** | 1,696 / 7.1 |

Findings: the best-engaged organic page is the tool landing (`griha-pravesh`, 88%). **The two pages with the shortest stays are also top-10 impression pages**: gochar-2026 (26 s) and 7th-lord-placement (45 s). Landings that **never engage**: `/learn/financial-struggles` 11 sessions, 11 Direct, **0 engaged, 3 s total**; `/learn/chronic-health-issues-kundli` 21 sessions (Organic 16 with 3 engaged, Direct 5 with 1), 164 s in total; `/learn/griha-pravesh-muhurat-2026-2027` 12 sessions, 2 engaged, 61 s. Whether these three pages are broken or bad-intent landings is **not determined** by these files (needs a render check and scroll depth).

Tools visible in `ga4-events.json` (W): `kundli_generated` **51**, `ask_answered` 128, `tool_submitted` 47, `form_start` 103, `matching_completed` 5, `muhurat_searched` 6, `dosha_check_completed` 2, `subscribe_completed` 1, `share` 1, `feedback_sent` 2. `cta_click` **23** (2.8% of 817 sessions; partial history from 2026-11-03): 15 with a named from/to, 8 `(not set)`. Of the named ones, `/learn/*` → `/` 6, `/kundli` 4, `/dasha` 2, one each to `/kaal-sarp-check`, `/numerology`, `/sade-sati-check`. There is no impression event, so low click rate vs low exposure is not determinable. `form_start` 103 → `kundli_generated` 51 is the only funnel ratio the file supports (~50%), and `form_start` is not split by tool.

## 6. Lever 3 — Errors

| source | window | reading |
|---|---|---|
| `llm-usage.json` | last 7 days, generated 2026-11-26T03:21Z | **156 calls, 111 cache hits (71%), 45 misses. `fallbacks`: 0, `fallback_reasons`: {}.** Input 145,718 tokens, output 26,900 |
| peak day | `peak_day_measured_tokens` **42,994** on 2026-11-23 | 21.5% of the 200,000 TPD figure; `peak_day_tokens` reads 6,733 on 11-22 (the file does not say why the two fields differ) |
| `verify-production.yml` | last 100 runs, 2026-11-18 → 11-26 | 95 success / 3 cancelled / **1 failure**: a deploy-gate timeout, not a page (#341) |
| HTTP 5xx per non-LLM route | – | **not measured** — filed as **#1506** (third report in a row) |

| route | calls | hit rate | tokens per measured call | open issue |
|---|---:|---:|---:|---|
| natal | 89 | 88% | **6,610** (10 measured) | none; no fallback |
| rashifal | 28 | 100% | not measured | none |
| ask | 25 | **0%** | 2,418 (25 measured) | none; per-visitor by nature |
| today | 6 | 33% | 1,917 | none |
| matching | 5 | 0% | 1,870 | none |
| monthly | 3 | 66% | 2,116 | none |

No route has an LLM error or fallback in 7 days. Observation, not a finding: one natal miss measures 6,610 tokens against an 8,000 TPM bucket per model, so two natal misses inside one minute on one model would exceed it; the file records 10 measured natal calls and 0 fallbacks, so nothing here shows it happening. Groq TPM-ceiling failures (#266-style) would show as `fallbacks` and there are none.

**Kundli GA4 ↔ server ratio: not computable.** GA4 `kundli_generated` = 51 over W (2026-10-27 → 11-23). `totals.non_probe_dates` = 2026-10-30, 11-03, 11-08, 11-24, 11-25; only 3 of those fall inside W, and the collector's `window.from` (2026-10-30) is after W's start. 23 days have `probe: null`. Nothing was divided by `totals.fresh_generations`. Posted on #1068.

## 7. Lever 6 — Index status (`index-status.json`, generated 2026-11-26T03:43Z)

| count | 11-19 | 11-23 | **11-26** |
|---|---:|---:|---:|
| inspected / sitemap URLs | – | – | **214 of 214**, 0 errors |
| indexed / not indexed | – | 165 / 49 (per last report) | **166 / 48** |
| "changed after Google's last crawl" | – | 168 | **164** |
| canonical mismatch / blocked / unknown | – | 0 / 0 / 0 | 0 / 0 / 0 |
| ten largest pages crawled after their last change | 2 of 10 | 1 of 10 | **6 of 10** |

Pages Google has **not** re-fetched since their last content change, ranked by value (`request_indexing` in the file; I have no write path to request indexing, so this is the owner's list):

| URL | impr | changed | last crawl |
|---|---:|---|---|
| /learn/debilitated-sun-career/ | 2,791 | 2026-11-22 | 2026-11-16 |
| /learn/sade-sati/ | 1,950 | 2026-11-22 | 2026-11-20 |
| /learn/7th-lord-placement-marriage-guide/ | 1,696 | 2026-11-24 | 2026-11-23 |
| /learn/rahu-mahadasha-career-problems/ | 1,216 | 2026-11-16 | **2026-11-11** |
| /learn/10th-lord-in-6th-house-career/ | 812 | 2026-11-18 | 2026-11-11 |
| /learn/mangal-mars-in-vedic-astrology/ | 640 | 2026-11-25 | 2026-11-10 |
| /learn/saturn-in-10th-house-career/ | 541 | 2026-11-17 | 2026-11-04 |
| /muhurat/griha-pravesh | 531 | 2026-11-26 | 2026-11-08 |
| /learn/manglik-dosh/ | 489 | 2026-11-25 | 2026-11-18 |
| /learn/vimshottari-dasha-explained/ | 438 | 2026-11-17 | **2026-10-24** |

`impressions_matched`: 135 of 139 pages with impressions are in the file. **The two edits that target the largest CTR gaps (#835 on debilitated-sun, #685 on sade-sati) are in this list** — their edits are newer than Google's crawl, so a CTR effect of the latest edit cannot exist yet.

## 8. Lever 4 — Search demand (partial: `gsc-trend-query.json` covers **14%** of W impressions)

| theme (visible queries only) | impressions W (P) | position | existing page |
|---|---:|---|---|
| "sun debilitated in which sign" family (319 + 155 + 65 + 64 + 45 …) | 648+ (P 60 for the head query) | 5.8–9.1 | `/learn/debilitated-sun-career/` (CTR 0.64% on 2,791 impr; #835 pending) |
| "sun debilitation degree" | 58 (P 0) | 6.6 | same page; the template mentions "degree" once, whether it answers the query is **not determined** |
| "rahu mahadasha ketu antardasha" family (head 340 impr, 12 clicks; 15+ wordings) | 340 (287) | 6.3–10.4, each up 2–9 vs P | `/learn/rahu-mahadasha-ketu-antardasha/` |
| "jupiter in 10th house", "guru in 10th house" | 127 (2) + 98 (0) | 10.6 / 8.6 | `/learn/jupiter-in-10th-house-career/` (#1073 pending) |
| "10th lord in 6th house" | 78 (22) | 8.6 | `/learn/10th-lord-in-6th-house-career/` |
| "which mahadasha is best for career" | 67 (0) | 8.4 | `/learn/vimshottari-dasha-explained/` (#1072 pending) |
| "yes" | 122 (12) | 3.8 | **no page nameable**; ambiguous one-word query, not a theme to act on |

**Queries with no page:** not determinable from this export. `fetch_gsc.py --by query-page` exists since #1436 (merged 2026-11-25) but writes no file in this run's inputs, so I name no page that would be new, and I flag no cannibalisation beyond the 7th-house pair (`7th-lord-placement-marriage-guide` 1,696 impr and `planets-in-7th-house-marriage` 1,541 impr share a theme; #1430 covered it). `/matching` fell to position 10.2 on 116 impressions (§4). `/festivals` sits at 39.9.

## 9. Lever 5 — Content opportunities (next 6–8 weeks, 2026-11-26 → 2027-01-21)

Dates read from `festival_registry.py` this run; I did **not** re-verify any date against an almanac.

| date | festival (slug) | learn article (`learn_article_for`) |
|---|---|---|
| 2026-12-01 | kalabhairav-jayanti | none |
| 2026-12-14 | vivah-panchami | none |
| 2026-12-20 | gita-jayanti | none |
| 2026-12-23 | dattatreya-jayanti | none |
| 2027-01-15 | makar-sankranti | none |
| 2027-01-15 | pongal | none |

- All six registry entries in the window have no linked `/learn` article. **None appears among the 139 pages in `gsc-all.json`**; the existing surface is `/festivals` (248 impressions, position 39.9, 0 clicks). product-manager decides whether any is worth a page.
- **Lohri is not in the registry** (a count over `festival_registry.py` and `festivals.py` is 0): I state no Lohri date.
- Annual pages: `gochar-2026-planetary-transits` is the largest page on the site (3,472 impr, position 4.9) and its year ends in five weeks; `gochar-2027-planetary-transits` exists in the templates and is **absent from `gsc-all.json`** (0 impressions).
- `griha-pravesh` demand is live now (33 sessions, 88% engaged), and the Kharmas pause starts in December, so the finder's zero-result path (#1336) will matter. `learn/griha-pravesh-muhurat-2026-2027` left GSC (24 → 0 in the last report) but still lands 12 GA4 sessions.

## 10. Lever 7 — Measurement gaps vs my last three reports (2026-11-23, 11-24, 11-25)

| gap | in each of the last three? | this run | open issue |
|---|---|---|---|
| GA4 previous window | yes | **resolved** (`ga4-trend.json` present) | #1205 closed; verdict on #1115 |
| `muhurat_searched` absent from GA4 | 11-24, 11-25 | **resolved**: 6 events, partial history from 2026-11-18 | #1469 (still open; I read it as met for existence, not as proof that the event fires on every search) |
| LLM errors/fallbacks per route | 11-23 | **resolved** (`fallbacks` field present) | #1208 closed |
| Server-side kundli count | yes | file present; **ratio still not computable** (§6) | #1068 note, #1272 |
| **HTTP 5xx per non-LLM route** | **yes (11-23 as "errors not measured", 11-24, 11-25)** | not measured | **filed #1506 this run** |
| Per-page × per-day export | yes | not in this run's inputs | #953, #1076 |
| Share of Direct traffic that is automated | yes | `--cohorts` merged (#1398) but no file in this run | #1364 |
| Query → page map | yes | `--by query-page` merged (#1436) but no file in this run | #1432 |
| `page_location` query strings in GA4 | yes | not read this run | #1237, #1448 |

## 11. What I could not determine, and the one measurement that settles each

| not determined | measurement |
|---|---|
| Whether the objective (ten highest-impression queries into the top 5) is moving | not recoverable while 86% of impressions are withheld; page proxy is 1 of 10 at ≤ 5.0 |
| How much of Direct (284 sessions, 19% engaged) is automated | the cohort export output (#1364) written by `agent-measure` |
| Why AI Assistant referrals fell 19 → 5, and why 2026-11-15's 51 users arrived from organic with ordinary GSC clicks | a daily landing × source export for those dates; not in these files |
| Why `/matching` lost 5.8 positions | per-page × per-day export (#953, #1076) |
| Whether the 11-16 → 11-19 impressions dip (798–908/day) was a re-rank | the next runs' daily rows |
| Whether `financial-struggles`, `chronic-health-issues-kundli` and `griha-pravesh-muhurat-2026-2027` are broken or bad-intent landings | a render check plus scroll depth |
| HTTP 5xx per non-LLM route | request log or counter (#1506) |
| Which page serves each visible query | the `query-page` export file (#1436 script, #1432) |
| Whether `tool_error` events deliver (#1416, #1411) | window clean from 2026-12-24 |

## 12. Handed back

| item | value |
|---|---|
| Issues filed | **#1506** (no export carries HTTP 5xx per route; third report in a row) |
| Comments posted | **#1115** MET (verdict flip) · **#1205** pointer · **#1068** ratio not computable · **#1400** score (2 → 1 → 6 of 10) · **#1416** and **#1411** pending notes (scoreable 2026-12-24) |
| Verdicts unchanged and not re-posted | #311 MISS, #276 BAR MET not attributable, #329 UNSCOREABLE, #515 UNSCOREABLE, #1277 MET |
| Timers | 21 lines in `/tmp/analyst-timers.txt` (#553 12-01; #426 12-03; #570, #685, #508 12-04; #518 12-07; #735 12-12; #835 12-14; #1075, #1073, #1074 12-17; #1072, #1071 12-18; #1217, #1226, #1229 12-19; #1322, #1325, #1336 12-22; #1416, #1411 12-24). #1217, #1226 and #1229 were missing from last report's list |
| The one number to read first | **GA4 sessions 424 → 817 (+92.7%) and users 322 → 680 (+111%); Organic Search is 329 of the 393 added sessions, Direct added 85 sessions and lost 18 engaged ones.** The growth is real, `/learn`-only and not yet in rank (1 of the top-10 pages at ≤ 5.0). |
