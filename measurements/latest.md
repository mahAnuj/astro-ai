# Analyst report — 2026-11-11 run

**Window read this run: 2026-10-12 → 2026-11-08 (28 days, last 3 days excluded; GSC lags 2–3 days, GA4 24–48h).**
**Previous window (GSC trend files only): 2026-09-14 → 2026-10-11.** There is no GA4 previous window, so no GA4 delta against it is possible.

Every number below was read from `/tmp/*.json` this run unless marked otherwise. GSC is `dimension: page` (position = the page's *average* across its queries) unless a row says query.

## 0. Coverage — read before any number

| Export | Window | Coverage | Truncated | Note |
|---|---|---|---|---|
| `gsc-all.json` (page) | 2026-10-12 → 11-08 | 100% of 22,106 impressions; 140 pages | no | page rows sum to 22,150 (a page can appear under more than one URL variant) |
| `gsc-band.json` (page) | same | 100% fetched; **emitted 100 rows = 83% (18,356 imp)** | printed rows are capped at 100 | band totals below come from `gsc-all.json` (all 115 band pages), not this capped list |
| `gsc-trend-query.json` (query) | same vs prev | **13% of impressions (2,948 of 22,106)** | n/a | PARTIAL view: Google withholds rare queries. Nothing about "the whole band" may be concluded from it |
| `gsc-trend-page.json` | same vs prev | 100% | n/a | 140 pages now, 127 before; 48 new, 35 gone |
| `ga4.json` (landing × channel) | same | 100% of 624 sessions; 138 rows; 88 landings (82 paths after folding query strings) | no | `ga4-daily.json` sums to 626 sessions, 2 more than the landing export (not explained) |
| `ga4-events.json` | same | 16 event names, 4,255 events | no | `cta_click` split is NOT available, see §6 |

## 1. The band against OBJECTIVE.md

OBJECTIVE: *"Move the 6–20 position band into the top 5 on the ten highest-impression queries."*

### 1a. Site level (GSC, window 2026-10-12 → 11-08, 100% coverage)

| Position bucket (page average) | Pages | Impressions | Clicks | CTR |
|---|---:|---:|---:|---:|
| ≤ 5 | 14 | 390 | 9 | 2.31% |
| **6–20 (the band)** | **115** | **21,455** | **258** | **1.20%** |
| > 20 | 11 | 305 | 0 | 0.00% |
| All | 140 | 22,150 | 267 | 1.21% |

- The band holds 96.9% of all impressions. Pages already in the top 5 hold 1.8%. The lever is as unmoved as before: the site's traffic sits one or two places from page one.
- ≤ 5 earns 2.31% against 1.20% in the band, but that rests on 9 clicks, so treat it as a direction rather than a rate.
- Site totals vs the previous window (page rows, GSC): impressions 10,138 → 22,150 (+118%), clicks 107 → 267 (+150%), CTR 1.06% → 1.21%.

### 1b. The objective's own metric: the ten highest-impression queries (QUERY dimension, **13% coverage, partial**)

| # | Query | Impressions | Clicks | Position | Prev position (prev imp) |
|---|---|---:|---:|---:|---|
| 1 | rahu mahadasha ketu antardasha | 365 | 11 | 7.8 | 9.5 (222) |
| 2 | sun debilitated in which sign | 213 | 0 | 8.1 | none (0) |
| 3 | sun is debilitated in which sign | 106 | 0 | 7.7 | none (0) |
| 4 | jupiter in 10th house | 81 | 0 | 10.3 | none (0) |
| 5 | 10th lord in 6th house | 70 | 2 | 8.5 | none (0) |
| 6 | sun debilitated sign | 70 | 0 | 6.3 | 3.0 (2) |
| 7 | rahu mahadasha and ketu antardasha | 64 | 0 | 8.0 | 9.3 (36) |
| 8 | guru in 10th house | 59 | 0 | 8.7 | none (0) |
| 9 | sun debilitated | 56 | 0 | 8.6 | none (0) |
| 10 | rahu ketu antardasha | 50 | 0 | 8.4 | 9.2 (34) |

| Measure (measured query share only) | Value |
|---|---|
| Top-10 queries in the top 5 | **0 of 10** (positions 6.3–10.3) |
| Queries in 6–20 / in top 5 | 304 (2,440 imp) / 204 (331 imp) |
| Clicks across all measured queries | 29 |

- 6 of the 10 had zero impressions in the previous window (#2, 3, 4, 5, 8, 9); 8 of the 10 have zero clicks. The baseline against the objective is 0/10 in the top 5. This is a floor, because 87% of impressions are invisible at query level.
- Clusters: 4 of the top 10 are "sun debilitated" (445 imp, 0 clicks, all on `/learn/debilitated-sun-career/`, page CTR 0.54%). 4 are the Rahu–Ketu antardasha family. 2 are 10th-house queries.
- Of the four with a previous position, #1 (9.5 → 7.8), #7 (9.3 → 8.0) and #10 (9.2 → 8.4) all moved up by 0.8–1.7 places, while #6 moved from 3.0 to 6.3 (on 2 prior impressions, so no signal). #1 is the only one with clicks of note (11).

### 1c. Band pages ranked by opportunity (page dimension, `band_opportunity` from `gsc-band.json`)

| Page | Imp | Clicks | CTR | Avg pos | Prev imp → now | Prev pos → now |
|---|---:|---:|---:|---:|---|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,507 | 50 | 1.43% | 6.5 | 1,635 → 3,507 | 7.5 → 6.5 |
| /learn/debilitated-sun-career/ | 2,408 | 13 | 0.54% | 6.7 | 925 → 2,408 | 6.0 → 6.7 |
| /learn/sade-sati/ | 1,922 | 12 | 0.62% | 6.6 | 844 → 1,922 | 6.2 → 6.6 |
| /learn/jupiter-in-10th-house-career/ | 1,493 | 13 | 0.87% | 6.9 | 332 → 1,493 | 6.8 → 6.9 |
| /learn/7th-lord-placement-marriage-guide/ | 1,199 | 13 | 1.08% | 7.3 | 204 → 1,199 | 8.2 → 7.3 |
| /learn/gochar-2026-planetary-transits/ | 953 | 12 | 1.26% | 6.2 | 17 → 953 | 7.1 → 6.2 |
| /learn/rahu-mahadasha-career-problems/ | 969 | 20 | 2.06% | 6.0 | 822 → 969 | 7.3 → 6.0 |
| /learn/panch-mahapurush-yoga/ | 712 | 9 | 1.26% | 6.7 | 345 → 712 | 6.7 → 6.7 |
| /learn/manglik-dosh/ | 497 | 3 | 0.60% | 6.7 | 435 → 497 | 7.2 → 6.7 |
| /learn/10th-lord-in-6th-house-career/ | 556 | 16 | 2.88% | 6.5 | 177 → 556 | 7.1 → 6.5 |

The ten pages above carry 14,216 of the band's 21,455 impressions (66%).

## 2. Post-ship scoring: issues closed in the last 45 days with a `thesis:` and `metric:`

**Result of this run: nothing is scoreable. No hit and no miss can be stated for any of them.** I scanned 161 issues closed since 2026-09-27; 83 carry both fields and 11 of those have a traffic or analytics metric. Today the fetch window starts 2026-10-12 (today − 31 = 2026-10-11 under the rule). None of the 11 deploys falls on or before that date, so every window still mixes before and after, and none of the 11 meets the clean-window rule. I read each issue's earlier analyst comment first.

| Issue | Thesis (short) | Deploy (PR merge) | First clean window | Readable from | Earlier analyst note? | Action this run |
|---|---|---|---|---|---|---|
| #311 | title/meta rewrite on four band pages lifts CTR toward the reference page | #334, 2026-10-13 17:29Z | 10-14 → 11-10 | **2026-11-13** | yes, "pending" 11-08 | none |
| #276 | CTA before 2nd heading on the Rahu–Ketu page lifts pages/session to ≥ 1.20 | #342, 2026-10-14 02:02Z | 10-15 → 11-11 | **2026-11-14** | yes, "pending" 11-08 | none |
| #329 | Manglik checker link lifts pages/session to ≥ 1.30 on ≥ 10 organic sessions | #344, 2026-10-14 16:07Z | 10-15 → 11-11 | **2026-11-14** | yes, "pending, likely unscoreable" 11-08 | none (see below) |
| #553 | tool link on Panch Mahapurush lifts pages/session | #615, 2026-10-31 02:26Z | 11-01 → 11-28 | 2026-12-01 | yes 11-07 | none |
| #426 | Saturn-exit date correction; guard: position within ±1 of 6.2 | #673, 2026-11-02 12:18Z | 11-03 → 11-30 | 2026-12-03 | yes 11-08 | none |
| #685 | Moon signs in the Sade Sati title: CTR ≥ 1.2% on ≥ 1,200 imp | #690, 2026-11-03 10:58Z | 11-04 → 12-01 | 2026-12-04 | yes 11-08 | none |
| #508 | shorter /matching title/meta lifts CTR to ≥ 1.0% on ≥ 300 imp | #696, 2026-11-03 20:59Z | 11-04 → 12-01 | 2026-12-04 | yes 11-07 | none |
| #570 | `cta_click` by `from_path` / `to_path` | #688, 2026-11-03 04:42Z | 11-04 → 12-01 | 2026-12-04 | yes 11-08 | none |
| #518 | route every dead-end article to a tool (five slices) | last slice #754, 2026-11-06 18:32Z | 11-07 → 12-04 | 2026-12-07 | yes 11-07 | none |
| #528 | `/ask` question stays out of the GA4 landing URL | #801, 2026-11-09 00:53Z | 11-10 → 12-07 | **2026-12-10** | **none** | **posted one "pending" note** (issue #528 comment 6783779120) |
| #782 | `fetch_ga4.py --events` writes the events export | #785/#788, 2026-11-08 | n/a, verified by a live run | n/a | closed with evidence 11-09 | none |

`#843` carries a correctness metric on 14 sessions per 28 days and `#618`, `#817`, `#818` carry non-traffic metrics, so none is a traffic-scoring item.

**#329 and the sample floor:** the issue's floor is ≥ 10 organic sessions. This run reads `/learn/manglik-dosh/` Organic Search at **3 sessions at 1.00 pages/session** (GA4, 2026-10-12 → 11-08), with GSC at 3 clicks in the same window (prev window 2 clicks). The floor looks out of reach, but my earlier note said to wait for the clean window (2026-10-15 → 11-11, readable 11-14) before stating "unscoreable at this traffic". I'm keeping to that rather than posting a second note now.

**Baselines for the next run (not scores; the window still contains the deploys):**

| Issue | Number read this run (2026-10-12 → 11-08) |
|---|---|
| #276 | Rahu–Ketu antardasha landing: 62 sessions all channels at 1.29 pages/session; organic 48 sessions at 1.38 |
| #311 pages | `debilitated-sun-career` 0.54% CTR (13/2,408), pos 6.7. `jupiter-in-10th-house-career` 0.87% (13/1,493), pos 6.9. `manglik-dosh` 0.60% (3/497), pos 6.7. `rahu-mahadasha-career-problems` 2.06% (20/969), pos 6.0 |
| #685 | `/learn/sade-sati/` 0.62% (12/1,922), pos 6.6, vs the issue's 0.63% before and its pass bar of 1.2% |
| #508 | `/matching` 1.32% (2/151), pos 6.7. See §4: position fell from 4.2 |
| #528 | 1 landing row carries a visitor-typed `q=` (`/ask?q=…`, 2 sessions): pre-fix data |

I'll post a score on #311, #276 and #329 only when their clean windows are readable (11-13 / 11-14).

## 3. Confounds (named before any delta)

| Confound | State this run |
|---|---|
| **Concurrent ships** | **Many, so no movement below can be attributed to one change.** `git log origin/main` is unusable here (the checkout is shallow, 1 commit), so the list is taken from issue timelines (merge times above). In the window: #334 title/meta on four pages (10-13), #342/#344 CTAs (10-14), #521 (10-25), #615 (10-31), #658 (11-01), #680 (11-02), #673 date corrections on sade-sati/gochar (11-02), #690 sade-sati title (11-03), #696 matching title (11-03), #688 `cta_click` (11-03), #754 (11-06), #796 seo_description shortening on 7 learn pages (11-09). That is at least 12 merges on pages carrying the band |
| **Seasonality** | Sade Sati and 2026-transit pages (`gochar-2026` 17 → 953 impressions) are calendar-sensitive, and festival traffic is violently seasonal. I have no year-over-year data to separate the calendar from the work. Not determinable |
| **Was the page reachable?** | Not measured this run. #266 (intermittent failure under the Groq TPM ceiling) affects `/rashifal` and generated pages, not the static `/learn` pages carrying the band. No outage evidence in these files, but no uptime series either |
| **Sample size** | Most per-page clicks are 2–20 in 28 days. A page at 3 clicks (`manglik-dosh`, `/matching` at 2) cannot carry a CTR conclusion. 8 of the top-10 queries have zero clicks |
| **Non-human / internal traffic in GA4** | Of 624 sessions: **19 landed on `/admin/*`** (internal, #735 tracks it) and **19 on `(not set)` at 94.7% bounce**. Direct is 270 sessions at 71.5% bounce. Direct without admin and `(not set)` is 252 sessions at 72.2% bounce and 1.96 pages/session. Direct cannot be called human growth |
| **Spike days** | GA4 sessions 42 on 2026-10-16, 34 on 10-23 and **59 on 11-06** (57 active users, 53 new), against a typical 12–30. There is no per-day channel split in the files, so I can't say what caused them. GSC clicks on 11-06 were 17, so the spike is not search |

## 4. Decay and CTR outliers

### 4a. Decay (GSC page, 2026-10-12 → 11-08 vs 2026-09-14 → 10-11)

| Page | Impressions prev → now | Clicks prev → now | Position prev → now | Read |
|---|---|---|---|---|
| /matching | 263 → 151 (−43%) | 0 → 2 | **4.2 → 6.7** | The only page that was in the top 5 with real impressions and lost it. **Confound: #696 shortened its title/meta on 2026-11-03, inside this window.** Page-level data cannot split by day, so I cannot say whether the title change caused the drop. #508's clean window (readable 12-04) is the first fair test |
| /festivals | 310 → 274 | 1 → 0 | 27.1 → 33.0 | Position beyond 20 on both sides. Not in the band, 0 clicks |
| /learn/saturn-in-10th-house-career/ | 109 → 200 | 0 → 2 | 7.3 → 8.4 | Impressions up while position slipped. Not decay |
| /learn/griha-pravesh-muhurat-2026-2027/ | 42 → 0 | 1 → 0 | 7.5 → none | Gone from the window. GA4 still shows 15 sessions landed on it in this window at 66.7% bounce, so the GSC disappearance is not a traffic collapse in sessions |
| /learn/career-not-progressing/ | 21 → 0 | 0 → 0 | 8.0 → none | Gone |
| /learn/the-9-grahas-overview/, ketu-in-vedic-astrology, financial-struggles | 99 → 32, 60 → 10, 45 → 10 | 0, 1→0, 0 | 8.0 → 9.2, 7.5 → 7.7, 6.3 → 6.8 | Small. Each is under 100 impressions, so noise-sized |

Net: only 3 pages with ≥ 100 impressions in **both** windows lost ≥ 1 position (`/matching`, `saturn-in-10th-house-career`, `/festivals`). Site average position is stable at 6.3–8.1 on every day of the window. Decay is not the main story this window, growth is.

### 4b. CTR outliers (compared against the band's own rate, 258/21,455 = **1.20%**)

| Page | Imp | Pos | CTR | Read |
|---|---:|---:|---:|---|
| /learn/marriage-mahadasha-timing/ | 529 | **5.4** | **0.38%** (2 clicks) | The best-ranked of the large pages and the worst CTR: a snippet problem at a top-5 position. **This is the clearest title/meta candidate in this run.** (n = 2 clicks, treat as a lead, not a rate) |
| /learn/debilitated-sun-career/ | 2,408 | 6.7 | 0.54% | Second-largest page, under half the band's rate. Four of the ten top queries land here, all "which sign" lookups. A query answered in the snippet is a likely zero-click, but the files do not say that |
| /learn/sade-sati/ | 1,922 | 6.6 | 0.62% | Title changed 11-03 (#690): not scoreable until 12-04 |
| /learn/manglik-dosh/ | 497 | 6.7 | 0.60% | 3 clicks |
| /learn/jupiter-in-10th-house-career/ | 1,493 | 6.9 | 0.87% | 13 clicks |
| /learn/10th-lord-in-6th-house-career/ | 556 | 6.5 | **2.88%** | Best CTR among large pages, 2.4× the band |
| /learn/rahu-mahadasha-career-problems/ | 969 | 6.0 | 2.06% | |
| /muhurat/griha-pravesh | 171 | 5.8 | 7.02% (12 clicks) | Highest CTR on the site. GA4 organic landing: 16 sessions, 12.5% bounce, 2.25 pages/session. A tool page that converts organic, not a /learn article |

## 5. Traffic, by channel and by landing (GA4, 2026-10-12 → 11-08, 624 sessions, 100% coverage)

Sessions aggregated by landing path (query strings and trailing slashes folded); bounce and pages/session weighted by sessions.

| Channel | Sessions | Bounce | Pages/session |
|---|---:|---:|---:|
| Organic Search | 337 | 45.1% | 1.57 |
| Direct | 270 | 71.5% | 1.91 |
| AI Assistant | 12 | 33.3% | 4.00 |
| Unassigned | 5 | 80.0% | 0.40 |

| Organic Search segment | Sessions | Bounce | Pages/session |
|---|---:|---:|---:|
| /learn/* landings | 268 | 45.2% | 1.47 |
| non-/learn landings | 69 | 44.9% | 1.94 |

| Top landings (all channels) | Sessions | Bounce | Pages/session |
|---|---:|---:|---:|
| / | 93 | 36.6% | 3.86 |
| /learn/rahu-mahadasha-ketu-antardasha | 62 | 46.8% | 1.29 |
| /learn/rahu-mahadasha-career-problems | 24 | 45.8% | 2.08 |
| /kundli | 24 | 66.7% | 1.67 |
| /learn/gochar-2026-planetary-transits | 24 | 66.7% | 1.13 |
| /learn/7th-lord-placement-marriage-guide | 22 | 50.0% | 1.10 |
| /learn/career-during-sade-sati | 20 | 50.0% | 1.60 |
| /muhurat/griha-pravesh | 16 | 12.5% | 2.25 |

- Organic Search is 337 of 624 sessions (54%). GSC reports 267 clicks in the same window, so GA4 organic exceeds GSC clicks by 70. The gap is not explained by these files (other engines and AI referrers are possible).
- Time shape: GA4 sessions in the first 14 days of the window 254, in the last 14 days 372 (+46%). GSC impressions 7,017 → 15,089 and clicks 73 → 194 over the same halves. The step is between 2026-10-22 (517 impressions) and 10-27 (1,053), and impressions have been flat at about 1,040–1,240 a day since. **Last 7 days vs the 7 before (GSC): impressions 7,740 vs 7,349 (+5%), clicks 106 vs 88 (+20%).** Growth has plateaued in impressions.

## 6. Funnel and events (GA4, 2026-10-12 → 11-08, 16 event names, 4,255 events)

| Event | Count | Event | Count |
|---|---:|---|---:|
| page_view | 1,093 | ask_answered | 134 |
| session_start | 622 | kundli_generated | 53 |
| first_visit | 492 | cta_click | **8** |
| feature_view | 629 | form_submit | 1 |
| form_start | 135 | subscribe_completed | 1 |
| user_engagement | 272 | feedback_sent | 2 |

| Derived (this window) | Value |
|---|---|
| `kundli_generated` per `session_start` | 53 / 622 = 8.5% |
| `ask_answered` per `session_start` | 134 / 622 = 21.5% |
| `subscribe_completed` | 1 |

- **`cta_click`: 8 events, split NOT available.** Every row reports `(not set)` for `from_path` and `to_path`. The file's own `coverage_note` says the parameters are not registered as custom dimensions, or were never collected, and that `cta_click` exists only from 2026-11-03 04:42Z, so this window holds 6 days of it. Per #782's closing comment the owner registered both dimensions on 2026-11-08, and GA4 does not backfill. **What would settle it:** if the split is still `(not set)` for clicks after 2026-11-12, the parameters are not reaching GA4, and that is a new issue. I'll re-read it on the first run whose window covers 2026-11-09 onward. Until then #570's metric cannot be scored.
- **The event counts include the site's own automation.** #618 changed `verify-production` to stop posting real forms, but I can't say from these files how much of `kundli_generated`, `ask_answered` and `form_start` is human. They are not segmented by channel. Do not read 8.5% as a conversion rate.
- `subscribe_completed` = 1 and `form_submit` = 1 in 28 days. **Monetisation or return-visit levers have no measured volume to work on.**
- Landing funnel: `/kundli` receives 24 landing sessions at 66.7% bounce. Organic `/learn` landings average 1.47 pages/session, so an organic reader typically reads one article and leaves. `/` is the only landing that walks readers onward (3.86 pages/session, 36.6% bounce).

## 7. Findings that could justify an issue, and why none was filed

I filed none. Each candidate is either already tracked by a pending score or lacks a determinable cause.

| Candidate | Why no issue |
|---|---|
| `/matching` 4.2 → 6.7 | The #696 title change sits inside the window and the files can't split by day. #508 is the test and is readable 12-04 |
| `marriage-mahadasha-timing` 0.38% CTR at position 5.4 (2 clicks) | n = 2 clicks. A lead for the next run, since it needs a second window to confirm before it carries an Evidence Block |
| `debilitated-sun-career`, 4 of the top 10 queries, 0 clicks | The query view is 13% coverage, and the files can't tell a zero-click lookup from a weak snippet |
| `cta_click` split `(not set)` | Owner action on 2026-11-08, covered by #782's closing comment. Re-check after 2026-11-12 |
| `/admin/*` and `(not set)` sessions in GA4 (38 of 624) | #735 already tracks it |

## 8. What I could not determine, and the single measurement that settles each

| Not determined | Measurement that would settle it |
|---|---|
| Any shipped change's effect on CTR or pages/session (#311, #276, #329, #685, #508, #553, #426, #518) | Read one clean window after each deploy (dates in §2). A per-day page export would remove the wait (#490) |
| Whether `/matching` lost position because of #696 | GSC `page` × `date` rows for `/matching` around 2026-11-03 |
| What the 87% of impressions the query view withholds do | Not recoverable; page-level is the only full view |
| Which `/learn` page sends readers to a tool (#570) | `cta_click` by `from_path`/`to_path` for clicks from 2026-11-09 onward |
| What the 2026-10-16, 10-23 and 11-06 session spikes were | GA4 `date` × `sessionDefaultChannelGroup` |
| How much of `kundli_generated` / `ask_answered` is human | GA4 events split by channel, or with the verification traffic excluded |
| Seasonality | No year-over-year data exists for a site this young |
| Whether the GA4 organic surplus over GSC clicks (337 vs 267) is other engines | GA4 `sessionSource` for the Organic Search channel |
