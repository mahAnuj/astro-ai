# Analyst report — 2026-10-13

**Window on every number: 2026-09-13 → 2026-10-10 (28 days; the exports exclude the last 3 days).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API re-called.
Every traffic figure below was computed from those three files this run. Nothing is carried from `BACKLOG.md`, `measurements/` or earlier comments. The git and issue facts in §2–§3 come from `git log origin/main` and `gh issue`, run this session.
**I make no "change since last run" claim.** The previous run's window (2026-09-12..10-09, per `measurements/latest.md`) overlaps this one by 27 of 28 days, and I have no earlier, non-overlapping window in this run's files.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-13..10-10 | 101% of 9,765 property impressions (rows sum 9,821). **Band printed 99 rows = 8,012 impr. = 82%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 126 rows = 9,821 impr. | no | — |
| ga4 | landing × channel | same | 101% of 278 sessions (rows sum 280); 101 rows; `landing_count` 69 as exported, **66 paths** after I stripped query strings and folded trailing slashes | no | bounce and pages/session are per channel; I weight by sessions below |

| fact | value | window |
|---|---:|---|
| GSC property clicks | 103 | 2026-09-13..10-10 |
| GSC property impressions | 9,765 | same |
| GA4 sessions (property total) | 278 | same |
| GA4 Organic Search sessions (sum of rows) | 136 of 280 row-sessions (49%) | same |

- GSC clicks and GA4 sessions are different measures. I do not equate them.
- **Unit is pages, not queries.** OBJECTIVE.md says "ten highest-impression **queries**". These exports are `dimension: page`, so the objective cannot be scored literally. Everything in §1 is a page-level proxy.
- **Sample size.** 103 clicks in 28 days. Every per-page CTR below is small-number territory (§1c).
- **Production reachability: not checked this run.** I did not probe the site. `/rashifal/*` (#266) is untested by me.

## 1. The 6–20 band against OBJECTIVE.md (2026-09-13..10-10, `dimension: page`)

### 1a. Band size

| measure | value | window |
|---|---:|---|
| pages at average position 6–20 (printed) | 99 | 2026-09-13..10-10 |
| impressions in the printed band | 8,012 (82% of 9,821 row impressions) | same |
| clicks in the printed band | 89 of 103 property clicks | same |
| median CTR, all 99 band pages | 0.00% (most pages have 0 clicks) | same |
| median CTR, the 18 band pages with ≥100 impressions | 0.77% | same |

### 1b. Objective proxy: are the ten highest-impression pages in the top 5?

| measure | value | window |
|---|---:|---|
| ten highest-impression pages (gsc-all) | 6,349 impr. = 65% of 9,821 | 2026-09-13..10-10 |
| of those, at average position ≤ 5 | **0 of 10** | same |
| pages at average position < 6, all of gsc-all | 23 pages, 569 impr. (6% of impressions) | same |

The pages that are already in the top 5 are low-volume. The pages with the volume are one to three places short of it.

### 1c. Band list, ranked by the file's `band_opportunity` (top 15, 2026-09-13..10-10)

| # | page | impr. | clicks | CTR | avg pos |
|--:|---|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,561 | 28 | 1.79% | 7.6 |
| 2 | /learn/rahu-mahadasha-career-problems/ | 835 | 6 | 0.72% | 7.3 |
| 3 | /learn/sade-sati/ | 800 | 8 | 1.00% | 6.3 |
| 4 | /learn/manglik-dosh/ | 419 | 2 | 0.48% | 7.1 |
| 5 | /learn/planets-in-7th-house-marriage/ | 465 | 5 | 1.08% | 6.4 |
| 6 | /learn/jupiter-in-10th-house-career/ | 321 | 1 | 0.31% | 6.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 333 | 2 | 0.60% | 6.7 |
| 8 | /learn/career-during-sade-sati/ | 380 | 5 | 1.32% | 7.3 |
| 9 | /learn/marriage-mahadasha-timing/ | 208 | 2 | 0.96% | 6.6 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 192 | 3 | 1.56% | 8.4 |
| 11 | /learn/10th-lord-in-6th-house-career/ | 173 | 2 | 1.16% | 7.1 |
| 12 | /learn/sun-in-10th-house-career/ | 147 | 1 | 0.68% | 7.1 |
| 13 | /learn/ | 122 | 0 | 0.00% | 13.5 |
| 14 | /learn/chronic-health-issues-kundli/ | 134 | 1 | 0.75% | 6.3 |
| 15 | /learn/mangal-mars-in-vedic-astrology/ | 126 | 1 | 0.79% | 7.3 |

- **Gap in the band file (inferred, not proven).** `/learn/debilitated-sun-career/` is the **second-highest-impression page on the property** (902 impr., 6 clicks, 0.67%, position displayed as 6.0 in gsc-all). It is not in `gsc-band.json`. The file's rounded 6.0 suggests its true average is just under 6, so the band filter dropped it. I cannot confirm that, because the files carry one decimal place.
- **Concentration.** The top 3 band pages (/learn/rahu-mahadasha-ketu-antardasha/, /learn/rahu-mahadasha-career-problems/, /learn/sade-sati/) hold 3,196 of the 8,012 printed band impressions (40%).
- The reference page (/learn/rahu-mahadasha-ketu-antardasha/) alone is 28 of 103 property clicks (27%).

### 1d. CTR outliers — none can be called from this sample

Comparison base: the band's own median among pages with ≥100 impressions, **0.77%** (not a blog table).

| page | impr. | observed clicks | clicks at 0.77% | reading |
|---|---:|---:|---:|---|
| /learn/jupiter-in-10th-house-career/ | 321 | 1 | 2.5 | below base, but 1 click vs 2.5 expected is not distinguishable |
| /learn/manglik-dosh/ | 419 | 2 | 3.2 | same |
| /learn/rahu-mahadasha-career-problems/ | 835 | 6 | 6.4 | on base |
| /learn/debilitated-sun-career/ | 902 | 6 | 6.9 | on base |
| /matching (avg pos 4.8, outside the band) | 157 | 0 | 1.2 | 0 clicks at 1.2 expected has a ~30% chance of happening anyway |
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,561 | 28 | 12.0 | **above base** — about 2.3× expected. The one clear outlier, and it is a positive one |

- **Finding: no title/meta problem is demonstrable at this sample size.** I am not filing a CTR issue. The only separable result is that the reference page converts impressions better than the rest of the band. Why is unmeasured (I did not read titles or SERP snippets).

### 1e. Decay

**Not determined.** Decay needs a prior non-overlapping window per page. This run has one window. The single measurement that settles it: `fetch_gsc.py --days 28` for 2026-08-16..09-12, then a page-by-page position diff.

## 2. Post-ship scoring — issues closed in the last 28 days with `thesis:` and `metric:`

I listed the closed issues with `closedAt ≥ 2026-09-15` and tested each body for both keys. Three qualify. **No issue closed since the last analyst run carried both keys.** The other 8 closed in the period (#306, #305, #304, #285, #280, #270, #268, #260) carry no `thesis:` and are not scorable.

| issue | closed | `metric:` | existing analyst score | does this run's data change it? | verdict |
|---|---|---|---|---|---|
| #272 measurement dimensions | 2026-10-08 | organic sessions as a separate number; ranking URL beside the band | PASS / PARTIAL, posted 2026-10-09 and 2026-10-10 | **Re-checked from today's files, window 2026-09-13..10-10:** `ga4.json` carries `channel` (Organic Search 136 of 280 row-sessions); `gsc-band.json` is `dimension: page`, 99 rows with the URL as key. Columns exist and are populated. Per-query view still absent | **PARTIAL, unchanged** |
| #313 workflow static gate | 2026-10-11 | a reintroduced instance of each defect is caught | HIT (with the 2/2 split revised), posted 2026-10-12 | No: infra, not a GA4/GSC quantity. I did not re-execute the gate this run | **HIT, unchanged** |
| #316 weekly loop-outcome report | 2026-10-11 | replay against 2026-10-08..09 flags all four defect rows | PARTIAL, posted 2026-10-12 | No: still unresolved — the fixtures are reconstructions and the live-run mapping is unread | **PARTIAL, unchanged** |

**Comments posted this run: none.** All three issues already hold an analyst score, and I have no new evidence that changes any verdict. Re-posting an identical score each day would bury the real comments. If you want a dated re-affirmation on each, say so.

**The miss that matters, repeated because it has not changed:** #316's thesis ("catches the defect classes a static gate cannot see") is demonstrated on fixtures only. #313's report half rests on it too.

### Shipped to users this window with no scoreable thesis

These went live in the window with no `thesis:`/`metric:`, so I cannot score them. I list them so nobody reads silence as success.

| change | merged | effect I can see in this run's files |
|---|---|---|
| #124 Hindi `/hi/{path}` surface, 13 URLs (merged 2026-10-04) | 2026-09-20 → 10-06 | **GSC impressions for any `/hi/` URL: 0 pages. GA4 sessions landing on `/hi…`: 0.** Six days of exposure at most — too early to read, and indexing lag alone explains it. A finding to watch, not a verdict |
| #268 rashifal cache (cached combined reading) | 2026-10-09 | `/rashifal*` has 3 GA4 sessions in total and 69 GSC impressions. Too small to say anything about demand |
| #304 mobile sticky CTA lift, #306 /kundli autofocus, #260 shloka fonts | 2026-10-09..11 | The latest merge is 2026-10-11, inside the final 3 days that the export excludes. **No post-ship data exists for any of these** |

## 3. Confounds, named before any delta

| confound | what I found |
|---|---|
| Concurrent ships in the window | `git log origin/main`: **66 commits** since 2026-09-13, of which **21 touched `src/`**. Most are the #124 Hindi branch's 17 commits (2026-09-20 and 10-04..06). Others: #268, #299, #304, #306, #260/#319. With that many, **no traffic delta can be attributed to any one of them**, and I report none |
| Overlapping windows | This window shares 27 of 28 days with the prior run. Any "change" between the two is almost entirely noise |
| Seasonality | **Could not determine.** I did not find a dated festival table for this window in `festivals.py` (one grep for Navratri/Pitru/Dussehra/Sharad matched only a comment), and CLAUDE.md forbids stating festival dates from memory. `/learn/griha-pravesh-muhurat-2026-2027/` (10 sessions) and `/muhurat/griha-pravesh/` (6 sessions) are calendar-driven pages in the top landings, so some of the traffic may be seasonal rather than earned |
| Was the page working? | **Not tested this run.** Organic pages are static `/learn/` articles. The LLM-backed `/rashifal/*` pages (#266) draw 3 sessions in total, so a failure there would not distort the numbers above. #253 (stale stylesheet) is closed and I did not re-check it |
| Sample size | 103 clicks, 278 sessions. Per-page figures are below the threshold for conclusions. 66 landing paths share 278 sessions |
| Query vs page | Band positions are page-level averages. Two pages "at 7.1" may be a mix of a position-2 query and a position-30 query |

## 4. Funnel and engagement (GA4, 2026-09-13..10-10, sessions-weighted)

| channel | sessions | bounce | pages/session |
|---|---:|---:|---:|
| Organic Search | 136 | 33.8% | 1.67 |
| Direct | 103 | 53.4% | 2.85 |
| AI Assistant | 33 | 42.4% | 2.94 |
| Unassigned | 8 | 37.5% | 0.88 |

| organic cut | sessions | bounce | pages/session |
|---|---:|---:|---:|
| Organic landing on a /learn/ article (39 landing rows) | 117 | 35.0% | 1.49 |
| … excluding /learn/rahu-mahadasha-ketu-antardasha/ | 87 | 39.1% | 1.64 |
| Organic landing somewhere other than /learn/ | 19 | not computed | not computed |

- **Organic readers mostly do not go on to a second page.** Sessions-weighted across channels, the largest organic /learn/ landings sit at about 1.0–1.25 pages/session (Rahu–Ketu 1.03, Sade Sati 1.09, Rahu career-problems 1.25). Only 4 organic sessions landed on `/kundli` itself.
- **Not determinable:** how many organic readers *later* reach `/kundli`, `/matching` or `/numerology`. The export gives landing page and pages/session, but not the second page. A `pagePath` × `landingPage` funnel export would settle it. This is the funnel measurement from #272's fifth gap, still not available.
- **AI Assistant is a real channel:** 33 sessions (12% of the 280 row-sessions), 2.94 pages/session, and 7 of them land on `/`. That is more engaged than organic search. It is small, and not attributable to any ship.
- Direct traffic's `/` landing is 53 of 103 Direct sessions at 24.5% bounce and 4.26 pages/session. That looks like the owner or testers, not the public. I cannot prove it.

## 5. Issues filed this run

**None.** Candidates considered and rejected:

| candidate | why not filed |
|---|---|
| CTR/title problem on /learn/jupiter-in-10th-house-career/ and /learn/manglik-dosh/ | 1 and 2 clicks — indistinguishable from the 0.77% base (§1d). No Evidence Block can be completed |
| `/learn/debilitated-sun-career/` missing from `gsc-band.json` | Inferred from rounding, unproven. Needs a position at two decimals, which the export does not give. Flagged in §1c instead |
| OBJECTIVE.md wording ("queries" vs pages) | A ruling for `chief`, not a defect. The 2026-10-09 score on #272 already raised it |
| `/hi/` shows zero impressions | Six days at most since publication; indexing lag explains it. Revisit in the next two runs |

## 6. What I could not determine, and the one measurement that settles each

| unknown | settled by |
|---|---|
| Decay per page | a non-overlapping prior-window GSC page export (2026-08-16..09-12) |
| Query-level band (the objective as written) | `fetch_gsc.py --by query --band` with `page` as a second dimension, plus its `coverage_pct` |
| Whether `/learn/debilitated-sun-career/` is in the band | the page's average position at two decimals |
| Seasonality of the muhurat and Rahu/Sade Sati pages | a sourced festival and transit calendar for 2026-09-13..10-10; I will not supply one from memory |
| Whether `/hi/` is being indexed | a GSC URL-inspection or `/hi/` page-prefix filter, repeated in two to three weeks |
| Organic → tool conversion | a GA4 export of second-page path per landing |
| Whether the live loop-outcome run flagged defect rows 1 and 4 (#316) | the report artefact or issue #326 mapped to the four defects |
| Production health of `/rashifal/*` today | a `/rashifal/{rashi}` probe; I did not run one |
