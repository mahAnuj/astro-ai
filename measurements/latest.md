# Analyst report — run 2026-11-15

**Window for every number below: 2026-10-16 → 2026-11-12 (28 days; the last 3 days are excluded because GSC lags 2–3 days and GA4 24–48h).**
Prior window where a delta is quoted: **2026-09-18 → 2026-10-15** (`gsc-trend-*.json`).
All figures were read from `/tmp/*.json` this run. Anything taken from an issue comment is labelled as such.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | note |
|---|---|---|---:|---|---|
| `gsc-band.json` | page, position 6–20 | 10-16 → 11-12 | 100% of 25,802 property impressions (rows sum 25,880) | no | `emitted_*`: 101 pages, 19,408 impressions = 75% |
| `gsc-all.json` | page | 10-16 → 11-12 | 100% | no | 140 pages |
| `gsc-daily.json` | date | 10-16 → 11-12 | 100% | no | 28 days |
| `gsc-trend-page.json` | page, now vs prior | 10-16 → 11-12 vs 09-18 → 10-15 | 100% of 25,802 | – | 140 pages now, 126 prior |
| `gsc-trend-query.json` | query, now vs prior | same | **14%** of 25,802 | – | partial view: Google withholds rare queries. 722 query keys now vs 196 prior. No site-wide conclusion can be drawn from it. |
| `ga4.json` | landing × channel | 10-16 → 11-12 | 100% of 686 sessions (rows 685) | no | 149 rows, 97 raw landings, **89 after folding query strings and trailing slashes** |
| `ga4-daily.json` | date | 10-16 → 11-12 | – | – | 27 of 28 days have traffic. **11-12 is `no_data: true`**, i.e. GA4 has not delivered that day, so it is not a zero. |
| `ga4-events.json` | event | 10-16 → 11-12 | 16 event names, 4,631 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688), so ~10 of the 28 days |

GA4 sessions are summed across channel rows per folded landing; bounce and pages/session are session-weighted. A page's "position" in page mode is its average across queries, not any one query's rank.

## 1. Site level

| metric | 10-16 → 11-12 | 09-18 → 10-15 | change |
|---|---:|---:|---:|
| GSC impressions (page-row sum) | 25,880 | 10,938 | +137% |
| GSC clicks (page-row sum) | 341 | 105 | +225% |
| CTR | 1.32% (341 / 25,802 property) | 0.96% (105 / 10,938 rows) | +0.36 pt |
| pages with any impression | 140 | 126 | +14 |

| GSC daily, this window | impressions | clicks | impressions-weighted position |
|---|---:|---:|---|
| first 14 days (10-16 → 10-29) | 9,438 | 108 | daily 6.6–8.1 |
| last 14 days (10-30 → 11-12) | 16,364 | 233 | daily 6.1–7.4 |

| GA4, this window | sessions |
|---|---:|
| all, 10-16 → 11-12 | 686 |
| first 14 days (10-16 → 10-29) | 300 |
| 10-30 → 11-11 (13 days, 11-12 not delivered) | 387 |
| Organic Search | 384 (56%) |
| Direct | 285 (42%) |
| AI Assistant | 11 |
| Unassigned | 5 |

- The daily average position stayed in a 6.1–8.1 band all window while impressions rose about 3.3×, from 404 on 10-16 to 1,343 on 11-12. More pages ranked and more queries surfaced (722 query keys vs 196). The mean did not improve.
- GA4 has no prior-window export in this run, so **there is no GA4 week-on-week comparison**. Sessions are quoted only inside this window.

**Confounds on the site-level rise (named, not resolved):**
- Seasonality: Diwali fell on 2026-11-08, inside the window. Festival and muhurat traffic is seasonal, and this run has no prior-year data to separate the calendar from the work.
- Concurrent ships: `git log` is not usable here because the checkout is shallow (1 commit). Merged PRs read via `gh` show dozens of learn, matching and muhurat changes in the window (e.g. #680, #754, #690, #696, #940, #1005, #1009, #1011, #960), so no rise is attributable to any single one.
- Page reachability: `/health` returned HTTP 200 from the runner this run. Individual pages were not probed.
- Measurement contamination: GA4 holds **18 sessions landing on `/admin/ops`, 1 on `/admin/activity` and 20 on `(not set)`**, 39 of 686 (5.7%) that are not visitor traffic or cannot be attributed. #735 was closed 2026-11-11, and the window includes days before that. I cannot tell from these files how many of the 39 post-date the fix.

## 2. The 6–20 position band against OBJECTIVE.md

Objective (OBJECTIVE.md): *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**Band, page mode, 10-16 → 11-12:** 101 pages, 19,408 impressions, 235 clicks, **CTR 1.21%** (impressions-weighted). 68 of the 101 pages had zero clicks, covering 1,456 impressions (7.5% of the band's).

Top 10 by `band_opportunity`:

| # | page | impressions | clicks | CTR | avg position | prior-window impressions / position |
|---:|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,839 | 60 | 1.56% | 6.5 | 1,873 / 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,602 | 16 | 0.61% | 6.6 | 1,058 / 6.1 |
| 3 | /learn/sade-sati/ | 2,041 | 12 | 0.59% | 6.6 | 981 / 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,743 | 16 | 0.92% | 6.9 | 363 / 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,420 | 15 | 1.06% | 7.3 | 218 / 7.9 |
| 6 | /learn/planets-in-7th-house-marriage/ | 1,000 | 10 | 1.00% | 6.4 | 547 / 5.9 |
| 7 | /learn/panch-mahapurush-yoga/ | 918 | 14 | 1.53% | 6.8 | 385 / 6.9 |
| 8 | /learn/manglik-dosh/ | 510 | 4 | 0.78% | 6.8 | 462 / 7.3 |
| 9 | /learn/mangal-mars-in-vedic-astrology/ | 438 | 2 | 0.46% | 7.5 | 120 / 7.9 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 683 | 19 | 2.78% | 6.6 | 188 / 7.1 |

Together these ten are 15,194 impressions (78% of the band) and 168 clicks. All ten sit at position 6.4–7.5. **None is at average position ≤ 5.0.**

**Top-5 test on queries.** Query mode covers 14% of impressions, so this is a partial read. Of the ten highest-impression queries in `gsc-trend-query.json`:

| query | impressions | clicks | position |
|---|---:|---:|---:|
| rahu mahadasha ketu antardasha | 404 | 12 | 7.1 |
| sun debilitated in which sign | 253 | 0 | 8.0 |
| sun is debilitated in which sign | 116 | 0 | 7.2 |
| jupiter in 10th house | 96 | 0 | 10.3 |
| 10th lord in 6th house | 89 | 2 | 8.5 |
| sun debilitated sign | 74 | 0 | 6.2 |
| yes | 71 | 0 | 3.6 |
| guru in 10th house | 69 | 0 | 8.8 |
| rahu mahadasha and ketu antardasha | 64 | 0 | 7.5 |
| sun debilitated | 63 | 0 | 8.7 |

- **1 of 10 is at position ≤ 5, and it is `yes` (3.6), a query nobody targets.** None of the nine real ones is in the top 5. The quarter's objective is unmet on the measured 14% of query impressions. The other 86% is unreadable.
- `sun debilitated in which sign` and `sun is debilitated in which sign` are new this window (0 impressions in the prior window) at 253 and 116 impressions. This is the query family #835 targets (merged 2026-11-13 00:29Z, so the page change is after this window ends).

**CTR outliers.** Compared with the band's own impressions-weighted rate of 1.21%: six pages with ≥ 500 impressions and position ≤ 7.5 sit below it.

| page | impressions | clicks | CTR | position |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,602 | 16 | 0.61% | 6.6 |
| /learn/sade-sati/ | 2,041 | 12 | 0.59% | 6.6 |
| /learn/jupiter-in-10th-house-career/ | 1,743 | 16 | 0.92% | 6.9 |
| /learn/7th-lord-placement-marriage-guide/ | 1,420 | 15 | 1.06% | 7.3 |
| /learn/planets-in-7th-house-marriage/ | 1,000 | 10 | 1.00% | 6.4 |
| /learn/manglik-dosh/ | 510 | 4 | 0.78% | 6.8 |
| **six pages** | **9,316** | **73** | **0.78%** | |

At the band rate the six would have taken ~113 clicks, a gap of **about 40 clicks per 28 days**. That is small. The bigger lever is position, and this run holds no CTR-by-position curve for this site, so I do not size it.

Two pages at the same positions beat the band: `10th-lord-in-6th-house-career` (2.78% at 6.6) and `rahu-mahadasha-career-problems` (2.17% at 5.8). Their query mix was not examined.

## 3. Decay

| page | impressions now / prior | clicks now / prior | position now / prior | read |
|---|---|---|---|---|
| **/matching** | **106 / 321** (−67%) | 3 / 0 | **7.8 / 4.2** | the only material decay on a page that had ranked well. See below |
| /learn/griha-pravesh-muhurat-2026-2027/ | **0 / 38** (`is_gone`) | 0 / 0 | – / 7.3 | GA4 contradicts it. See below |
| /learn/the-9-grahas-overview/ | 29 / 100 | 0 / 0 | 9.4 / 7.9 | small |
| /learn/mars-remedies/ | 89 / 115 | 1 / 1 | 6.9 / 6.5 | small |
| /learn/career-not-progressing/ | 0 / 20 (`is_gone`) | 0 / 0 | – / 7.9 | small |
| /festivals | 294 / 243 | 0 / 0 | 33.5 / 28.8 | position far outside the band |

**/matching (the one to watch).**
- It fell from 321 impressions at position 4.2 to 106 at 7.8 between two adjacent windows. Position 7.8 is now **outside** the ±1.5-of-4.3 range that #508's metric requires, so that issue will read INCONCLUSIVE.
- #696 (title/meta shortened, merged 2026-11-03 20:59Z) falls inside the later window. These two windows are adjacent, and this export cannot split a page at a date, so **I cannot tell whether the drop came before or after the title change.** A title change that lowered position is possible, and so is a ranking that had already slipped. I do not attribute it either way.
- Concurrent `/matching` changes in this window (not title changes): #750 (2026-11-07), #870, #888 (2026-11-11), #892 (2026-11-12), #769. #696's own PR note asked that nothing else be bundled in the measurement window.
- GA4: `/matching` had 19 sessions (16 Direct, 2 Organic, 1 AI Assistant), 84% bounce.
- **Single measurement that settles it:** `uv run python scripts/fetch_gsc.py --by date --page-daily --pages /matching --days 56`. The `--page-daily` flag exists in `fetch_gsc.py` (#490 closed 2026-11-13). `agent-measure` does not write it to `/tmp`, so it was not available in this run, and I did not call the API myself.

**/learn/griha-pravesh-muhurat-2026-2027/.**
- GSC shows zero impressions in the window and the page is flagged gone, yet GA4 shows 12 sessions on that landing in the same window: 9 Organic Search, 2 Direct and 1 AI Assistant. The template exists in the tree.
- `/muhurat/griha-pravesh` rose from 29 to 319 impressions (position 6.4 → 6.1) and has 23 organic sessions at 9% bounce. That may be a shift of ranking between the two pages, or the GA4 "Organic Search" sessions may come from non-Google engines. **Not determined.** The measurement is the same `--page-daily` export on both URLs plus GA4's `sessionSource` split for the landing.

## 4. Scores for closed issues carrying `thesis:` and `metric:`

Rule applied: score once, when the window is clean (window start on or after deploy). Today's window starts 2026-10-16, so a deploy on or before 10-16 is clean. I read the existing comment thread on every issue first.

| issue | deploy (PR, merge) | window clean? | already posted | this run | verdict | action |
|---|---|---|---|---|---|---|
| **#311** four-page title/meta CTR test | #334, 2026-10-13 17:29Z | **yes** | MISS, clean window, 2026-11-13 (0.937% vs bar ≥ 1.5%) | combined CTR **0.99%** (58 / 5,870) vs bar ≥ 1.5%. Impressions floor met. Prior window 14 / 2,713 = 0.52% | **MISS, unchanged** | none: the number moved 0.937 → 0.99%, not material, same verdict |
| **#276** /dasha CTA on Rahu–Ketu article | #342, 2026-10-14 02:02Z | **yes** | BAR MET, not attributable, 2026-11-14 (1.42 pages/session) | Organic Search: **54 sessions, 1.43 pages/session** (bar ≥ 1.20 on ≥ 20); all channels 68 sessions, 1.34 | **BAR MET, not attributable**, unchanged | none |
| **#329** Manglik checker link | #344, 2026-10-14 16:07Z | **yes** | UNSCOREABLE 3 vs 10, 2026-11-14, scoring stopped | Organic Search **3** sessions, 1.00 pages/session. All channels 7 | unscoreable at this traffic | none: scoring on this issue stays stopped |
| #508 /matching title/meta | #696, 2026-11-03 20:59Z | no, first clean window starts 11-04 | pending, scoreable from 2026-12-04 | not scored. Reference only: page decay above | pending | none |
| #685 /learn/sade-sati title | #690, 2026-11-03 10:58Z | no | pending, scoreable from 2026-12-04 | reference: 2,041 impressions, 12 clicks, 0.59%, position 6.6. Prior window 981 / 10 / position 6.2. **Mixed window, not a score** | pending | none |
| #426 sade-sati date correction (guard) | #673, 2026-11-02 12:18Z | no | pending, scoreable from 2026-12-03 | reference: position 6.6 vs 6.2, impressions up 981 → 2,041 | pending | none |
| #553 panch-mahapurush link | #615, 2026-10-31 02:26Z | no | pending, scoreable from 2026-12-01 | reference: 9 Organic sessions, 1.00 pages/session. The bar needs ≥ 10 sessions, so it is likely unscoreable at ≥ 10. Re-check on the clean window | pending | none |
| #518 learn → tool routes (5 slices) | last slice #754, 2026-11-06 | no | pending, scoreable from 2026-12-07 | not scored | pending | none |
| #835 debilitated-sun lede/FAQ | #940, 2026-11-13 00:29Z | no | pending, scoreable from 2026-12-14 | not scored. The deploy post-dates the window | pending | none |
| #570 `cta_click` event | #688, 2026-11-03 04:42Z | no | pending, scoreable from 2026-12-04 | **the events export now exists in this run.** `cta_click` 12 events, 10-16 → 11-12, partial history (starts 11-03). Not a score | pending | none |
| #514, #523 rashifal | 2026-11-01 / 2026-10-25 | – | unscoreable at this traffic, posted 2026-11-09 | not re-scored | stopped | none |

Nothing was posted to any issue this run. Every issue has its one note, and the three clean-window verdicts did not move materially.

### The misses, as plainly as the hits

| result | what it says |
|---|---|
| **#311 MISS** (0.99% vs ≥ 1.5%) | A title/meta rewrite on four band pages did not reach the bar. Three of the four are still below 1% CTR at position 6.6–6.9 (debilitated-sun 0.61%, jupiter-10th 0.92%, manglik 0.78%). The page that cleared 2% (`rahu-mahadasha-career-problems`, 2.17%) also moved from position 7.2 to 5.8, so that gain is not attributable to the title. |
| **#329 unscoreable** (3 organic sessions vs floor 10) | The page ranks (489 impressions at position 6.8 per the earlier note; 510 / 4 clicks / 6.8 in this run's band file), but yields 3 organic sessions in 28 days. A link on it cannot be measured at that traffic. |
| **#276 bar met, not attributable** (1.43 vs ≥ 1.20) | Positive number, but the page also took #518's first-screen tool link, and the metric has no pre-deploy comparison. Not credited to the CTA. |
| **#508 will not pass as written** | The pass condition needs position within ±1.5 of 4.3; `/matching` is at 7.8. The page moved before anyone can score the title. |

## 5. Funnel

`ga4-events.json`, 10-16 → 11-12, GA4 event counts (events, not sessions or users; no per-form split):

| event | count |
|---|---:|
| page_view | 1,192 |
| user_identified | 701 |
| feature_view | 683 |
| session_start | 683 |
| first_visit | 556 |
| user_engagement | 296 |
| scroll | 174 |
| form_start | 137 |
| ask_answered | 130 |
| kundli_generated | 55 |
| cta_click | 12 |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |

- `cta_click` counts only 12 events over ~10 days of history. Of those, **8 carry `(not set)` for both `from_path` and `to_path`**, so the split is readable for 4: learn → `/` (1), `/learn/kaal-sarp-dosh/` → `/kaal-sarp-check` (1), `/learn/name-numerology-explained/` → `/numerology` (1), `/learn/rahu-mahadasha-ketu-antardasha/` → `/dasha` (1). Coverage note, verbatim: *"a window starting before 2026-12-01 holds partial history"*.
- **I cannot compute a step-through rate.** `form_start` (137) and `kundli_generated` (55) are event totals across several forms with no per-form or per-session split, so 55 / 137 is not a step-through rate. `form_submit` is 1, which looks like an instrumentation gap rather than 1 submission; not determined.

Landing mix (GA4 sessions, folded landings, 10-16 → 11-12):

| landing group | sessions | read |
|---|---:|---|
| any `/learn/*` | 423 (of which Organic Search 301) | 62% of 686 sessions. Learn is the front door |
| `/` | 78 | 4.22 pages/session, 38% bounce |
| tool and calculator landings (`/kundli`, `/matching`, `/numerology`, `/muhurat/*`, `/rashifal/*` and similar) | 127 | |

| landing (all channels) | sessions | Organic | bounce | pages/session |
|---|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha | 68 | 54 | 0.46 | 1.34 |
| /learn/gochar-2026-planetary-transits | 32 | 19 | 0.69 | 1.10 |
| /learn/7th-lord-placement-marriage-guide | 24 | 20 | 0.50 | 1.08 |
| /learn/rahu-mahadasha-career-problems | 24 | 24 | 0.42 | 2.08 |
| /numerology | 24 | 9 | 0.75 | 1.12 |
| /kundli | 23 | 7 | 0.65 | 1.65 |
| /muhurat/griha-pravesh | 23 | 23 | 0.09 | 2.26 |
| /matching | 19 | 2 | 0.84 | 1.58 |

- Learn landings mostly end after one page (1.0–1.3 pages/session) against 4.22 on the homepage. The two pages with 2+ pages/session (`rahu-mahadasha-career-problems` 2.08, `muhurat/griha-pravesh` 2.26) are the exceptions.
- The unmeasured step is learn → tool. Only `cta_click`, 12 events from 11-03, instruments it, and 8 of those 12 have no path split. This is the largest gap in the funnel read.

## 6. What I could not determine, and the measurement that settles each

| gap | single measurement |
|---|---|
| Whether `/matching` lost position before or after the 2026-11-03 title change | `fetch_gsc.py --by date --page-daily --pages /matching --days 56` (flag exists; not in this run's exports) |
| Whether `griha-pravesh-muhurat-2026-2027` lost its Google ranking or GA4's 9 "Organic" sessions came from other engines | the same `--page-daily` export for both griha-pravesh URLs, plus GA4 `sessionSource` for that landing |
| Whether the 2026-10-16 → 11-12 rise (impressions ×2.4, clicks ×3.2) is work or Diwali | the same windows a year earlier, or the post-festival window, not before ~2026-12-04. Not determinable now |
| Query-level top-5 progress on the other 86% of impressions | not recoverable; Google withholds the queries |
| Learn → tool step-through | `cta_click` with a populated `from_path`/`to_path` over a window starting on or after 2026-12-01. 8 of the 12 events so far have no split, so check why |
| Site-level GA4 trend | add a prior-window GA4 export; none was in this run |
| Which of the 39 non-visitor sessions pre-date #735's fix | a GA4 landing × day export for `/admin/*` and `(not set)` |

## 7. Issues filed

**None.** No finding needs an action I can state from this run's data. The `/matching` decay and the griha-pravesh discrepancy are each answered by one export (section 6) rather than by an engineering change, and #508 and the pending scores already carry their notes. I filed nothing rather than file an issue without an Evidence Block.
