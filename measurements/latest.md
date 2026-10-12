# Analyst report — 2026-10-12

**Window on every number: 2026-09-12 → 2026-10-09 (28 days; the exports exclude the last 3 days).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API re-called. Every figure was computed from those three files this run, except where a row says otherwise (git history, GitHub issue state, tests I executed, one `/health` probe). Nothing is carried from `BACKLOG.md`, `measurements/` or earlier comments. I make no "change since last run" claim: this window overlaps the previous run's by 27 of 28 days.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-12..10-09 | 101% of 9,417 property impressions (rows sum 9,474). **Band emitted 103 rows = 8,830 impr. = 94%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 128 rows = 9,474 impr. | no | — |
| ga4 | landing × channel | same | 101% of 276 sessions (rows sum 278); 99 rows; 67 landings as exported, **64 paths** after stripping query strings and folding trailing slashes | no | bounce / pages-per-session are per channel; weighted by sessions below |

- Property clicks (GSC): **102**. GA4 Organic Search sessions: **137**. Different measures; not equated.
- **Unit is pages, not queries.** OBJECTIVE.md says "ten highest-impression **queries**". These exports are `dimension: page`, so the objective cannot be scored literally. The page-level numbers below are a proxy.
- **Sample size.** 102 clicks in 28 days. Every per-page CTR below is small-number territory.
- **Production reachable:** `GET https://shubhagya.com/health` → 200 at run time. One probe, not a sweep. `/rashifal/*` (#266) not tested.

## 1. The 6–20 band against OBJECTIVE.md (2026-09-12..10-09, `dimension: page`)

### 1a. Band size

| measure | value |
|---|---:|
| pages with average position 6–20 | 103 |
| impressions in band | 8,830 (93% of 9,474 row impressions) |
| clicks in band | 95 (of 102 property clicks) |
| band CTR, impressions-weighted | 1.08% |
| band CTR excluding the reference page (Rahu–Ketu antardasha) | 0.92% (67 clicks / 7,314 impr.) |
| gsc-all pages by avg position: ≤5 | 15 pages, **30 impr., 0 clicks** |
| gsc-all pages by avg position: 5–6 | 7 pages, 265 impr., 5 clicks |
| gsc-all pages by avg position: 6–20 | 103 pages, 8,830 impr., 95 clicks |
| gsc-all pages by avg position: >20 | 3 pages, 349 impr., 2 clicks |
| top-10 band pages by `band_opportunity` | 6,033 impr. (68% of band), 67 clicks (71% of band clicks) |

Nothing high-volume is in the top 5: the 15 pages at ≤5 total 30 impressions and 0 clicks.

### 1b. Top 10 band pages by `band_opportunity`

| # | page | impr. | clicks | CTR | avg pos | band_opp. |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,516 | 28 | 1.85% | 7.6 | 63.0 |
| 2 | /learn/debilitated-sun-career/ | 871 | 6 | 0.69% | 6.0 | 46.3 |
| 3 | /learn/rahu-mahadasha-career-problems/ | 823 | 6 | 0.73% | 7.4 | 43.4 |
| 4 | /learn/sade-sati/ | 755 | 8 | 1.06% | 6.3 | 37.3 |
| 5 | /learn/planets-in-7th-house-marriage/ | 457 | 5 | 1.09% | 6.3 | 22.4 |
| 6 | /learn/manglik-dosh/ | 402 | 3 | 0.75% | 7.2 | 21.1 |
| 7 | /learn/jupiter-in-10th-house-career/ | 321 | 1 | 0.31% | 6.8 | 18.3 |
| 8 | /learn/career-during-sade-sati/ | 376 | 5 | 1.33% | 7.3 | 17.6 |
| 9 | /learn/panch-mahapurush-yoga/ | 312 | 3 | 0.96% | 6.8 | 15.7 |
| 10 | /learn/marriage-mahadasha-timing/ | 200 | 2 | 1.00% | 6.7 | 10.0 |

- All ten are `/learn/` articles.
- **Objective status, page-level proxy: 0 of these 10 are at position ≤ 5.** The nearest is `debilitated-sun-career` at 6.0 (printed rounded; it is in the band file this window, so its unrounded position is ≥ 6). The rest sit at 6.3–7.6. A single window cannot show movement, so none is claimed.

### 1c. Non-band pages worth naming (2026-09-12..10-09)

| page | impr. | clicks | CTR | avg pos | read |
|---|--:|--:|--:|--:|---|
| /festivals | 344 | 1 | 0.29% | **27.5** | page-3 ranking; in `gsc-all`, not in the band |
| / | 92 | 3 | 3.26% | 5.3 | best CTR of any page with >50 impr. |

## 2. Post-ship scores — issues closed 2026-09-14 → 2026-10-11

`gh issue list --state closed --search "closed:>=2026-09-14"` returned **11** issues. Three carry both `thesis:` and `metric:` in the body: #272, #313, #316. The other eight carry neither and cannot be scored under this role's rule.

| issue | closed | thesis + metric | verdict | posted |
|---|---|---|---|---|
| #313 workflow static gate + outcome report | 2026-10-11 | yes | **HIT** (thesis's 2-of-4 / 2-of-4 split revised to 3 / 1) | comment on #313 |
| #316 weekly loop-outcome report | 2026-10-11 | yes | **PARTIAL** | comment on #316 |
| #272 export dimensions | 2026-10-08 | yes | **PARTIAL** (unchanged) | not re-posted, see 2c |
| #304, #305, #306, #268, #260, #270, #280, #285 | 2026-10-08..11 | no | not scorable | — |

### 2a. #313 — HIT (executed this run)

| | predicted (`metric:`) | actual |
|---|---|---|
| Reintroduced instance of each defect is caught by the gate | yes | `scripts/verify_workflows.py` → `PASS - 15 workflow files`; `scripts/mutate_verify_workflows.py` → `19/19 controls+mutations behaved` |

- The gate catches 3 of the 4 original defects (self-reference, gh-vs-permissions, `pull_request` types); the thesis predicted 2. The outcome report was to cover the rest. Its live replay is PARTIAL (2b), so that half is shown on fixtures only.
- Confound: none for traffic. This is infrastructure.

### 2b. #316 — PARTIAL (executed this run)

| | predicted (`metric:`) | actual | verdict |
|---|---|---|---|
| Re-run against 2026-10-08..09 flags all four defect rows | all four | `tests/test_loop_outcomes.py` passes in full, including one test per defect (`test_defect1`..`4`). **But** `MANIFEST.json` marks the `defect1`–`4` fixtures `"recorded": false` — reconstructed, not captured from the real runs. The live run the closing comment cites (38156743088, window 10-08..**11**) gave `6 BROKEN, 2 UNKNOWN, 7 OK`; I could not read it (HTTP 403 for this token). Per the comment, defect 3 appears only as `UNKNOWN` on 14/14 runs; defects 1 and 4 are not named among the live findings. | **PARTIAL** — hit on reconstructed fixtures, not shown on live data |

- Not determined: whether the live run flagged defects 1 and 4. The measurement that settles it is the run's report body / issue #326 mapped to the four rows.

### 2c. #272 — PARTIAL, not re-posted

| | predicted (`metric:`) | actual (2026-09-12..10-09) | verdict |
|---|---|---|---|
| Organic sessions as a separate number | yes | **yes** — Organic Search = 137 of 278 row-sessions | PASS |
| Ranking URL beside each top-10 band **query** | queries | **pages, not queries** — GSC `dimension: page`, 103 band rows | PARTIAL |

Two analyst scores with the same verdict already sit on #272. The window moved but the verdict did not, so a third copy would bury the first two. Not determined: whether a query→URL join is obtainable. The measurement that settles it: `fetch_gsc.py --by query` with `page` as a second dimension, and its `coverage_pct`.

### 2d. The scoring gap

| fact | value |
|---|---|
| closed issues in window with a scorable traffic `thesis:`/`metric:` | **0 of 11** |
| user-facing ships among the 11 | #304 (sticky CTA, 2026-10-09), #305 (kundli tiles, 2026-10-11), #306 (autofocus, 2026-10-11), #268 (rashifal cache, 2026-10-09), #260 (shlokas font, 2026-10-10), #270 (Hindi rashifal) |
| of these, shipped inside the data window (≤ 2026-10-09) | #304, #268 only, both on its last day or two |

**No ship in this period has an outcome I can call a hit or a miss on traffic.** That is the finding. Nothing that shipped carried a traffic metric, so the loop has no read on whether the last month's work moved sessions. An honest read of #304 needs a window starting after 2026-10-09 with a non-overlapping before-window, which is about 2026-11-09 onward.

## 3. Confounds

| confound | what I found (2026-09-12..10-09) |
|---|---|
| Concurrent ships (`git log origin/main --since=2026-09-12 --until=2026-10-10`, history fetched to depth 300 this run) | 57 commits in the window, 19 touch `src/`. User-facing: the **#124 Hindi `/hi/` surface** (2026-09-20, 2026-10-04..06), rashifal localisation (#299, 2026-10-08), #268 and #304 (both 2026-10-09). **No commit in the window touched a `/learn/` article body or title** that I found among the `src/` commits listed. |
| Hindi surface footprint | **0 `/hi/` rows** in `gsc-all.json` and **0** in `ga4.json`. No measurable footprint yet. |
| Workflow / agent churn | The other 38 of the 57 commits are `.github/`, `scripts/`, `.claude/`, `measurements/` or root docs; they do not ship to the site. |
| Seasonality | **Not determined.** One window, no prior-year data. The ranked pages are mostly evergreen `/learn/` articles, which argues against a festival spike, but I cannot size one. `/learn/griha-pravesh-muhurat-2026-2027/` landing (10 sessions) is the one seasonal-looking page. |
| Page reachable? | `/health` 200. #253 (stale stylesheet) and #266 (TPM ceiling) were not probed; neither is likely to touch the static `/learn/` pages that dominate the band. |
| Sample size | 102 clicks, 276 sessions in 28 days. Most per-page deltas are noise. |

## 4. CTR outliers (2026-09-12..10-09; pages ≥ 100 impr.)

Reference rate = band CTR **excluding** the Rahu–Ketu reference page, 0.92%. `P(≥k)` = binomial upper tail; `P(≤k)` lower tail.

| page | impr. | clicks | expected | pos | read |
|---|--:|--:|--:|--:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,516 | 28 | 13.9 | 7.6 | **high outlier**, P(≥28) = 0.0005 |
| /learn/debilitated-sun-career/ | 871 | 6 | 8.0 | 6.0 | within noise, P(≤6) = 0.32 |
| /learn/rahu-mahadasha-career-problems/ | 823 | 6 | 7.5 | 7.4 | within noise, P(≤6) = 0.37 |
| /learn/jupiter-in-10th-house-career/ | 321 | 1 | 2.9 | 6.8 | within noise, P(≤1) = 0.21 |
| /learn/mars-remedies/ | 102 | 3 | 0.9 | 6.7 | high, P(≥3) = 0.07; too few to read |

- **#311's four pages** (`career-problems`, `debilitated-sun`, `manglik-dosh`, `jupiter-in-10th`): **2,417 impr., 16 clicks = 0.66%**. At the band's own rate (0.92%) they would expect 22.1 clicks; seeing ≤ 16 has probability **0.11 — not distinguishable from noise.** Against the reference page's rate the gap looks large, but the reference page is the outlier, not the four. #311's target is therefore a bet that the reference page's CTR can be reproduced by a title change. It is not a gap against baseline.
- Already stated on #311 in an earlier run; the conclusion is unchanged on this window, so I did not post it again.

## 5. Funnel and traffic mix (2026-09-12..10-09, GA4, 278 row-sessions; bounce and pages/session weighted by sessions)

| landing group | sessions | bounce | pages/session | sessions at exactly 1.00 pages |
|---|--:|--:|--:|--:|
| `/` (home) | 64 | 20% | 4.83 | 0 |
| `/learn/*` | 188 | 51% | 1.38 | **116 (62%)** |
| `/learn/*`, Organic Search only | 119 | 36% | 1.48 | 61 |
| everything else (tools, panchang, muhurat) | 26 | 39% | 2.38 | 6 |

| channel | sessions | share | bounce | pages/session |
|---|--:|--:|--:|--:|
| Organic Search | 137 | 49% | 35% | 1.61 |
| Direct | 100 | 36% | 53% | 3.07 |
| AI Assistant | 33 | 12% | 42% | 2.94 |
| Unassigned | 8 | 3% | 38% | 0.88 |

- **The organic reader finds the article and stops.** `/learn/rahu-mahadasha-ketu-antardasha/` alone: 32 sessions at 1.03 pages/session. The export has no CTA-click event, so I cannot say why.
- **Home is not an organic story:** 53 of its 64 sessions are `Direct`. Could be the owner, testers or automated checks; I cannot tell. The measurement that settles it: the same export with `newVsReturning` or an internal-traffic filter.
- **Tool funnel cannot be measured.** Kundli, matching and numerology landings total a handful of sessions (`/kundli/` 3, `/matching/` 2), too small to rank, and the export has no landing → form → result sequence.
- AI Assistant is a real channel (33 sessions, 2.94 pages/session), but the sample is small. No action.

## 6. Decay

**Not determinable this run.** Only one trailing window is in the files and the previous run's export overlaps it by 27 of 28 days. A decay claim needs a non-overlapping prior 28 days. The fetch scripts take `--days` only, so the single change that would settle it is an offset flag on both, or a stored export from ≥ 28 days ago to diff.

## 7. Issues filed / comments posted this run

| action | target | why |
|---|---|---|
| comment | #313 | score: HIT, executed gate + mutation proof |
| comment | #316 | score: PARTIAL, fixtures reconstructed, live replay not verifiable by me |
| not re-posted | #272, #311 | verdict/conclusion unchanged; earlier comments stand |
| none filed | — | No finding is new, evidenced, and untracked. `/festivals` at position 27.5 with 344 impressions is the one unfiled observation: no ship and no metric exist for it, so it is a `product-manager` question, not a defect. |

## 8. What I could not determine

| question | the one measurement that settles it |
|---|---|
| Whether the objective ("ten highest-impression **queries**") can be scored at all | `fetch_gsc.py --by query` with `page` as a second dimension, and its `coverage_pct` |
| Whether any page decayed | a non-overlapping prior 28-day export |
| Whether #316's live run flagged defects 1 and 4 | the report body of run 38156743088 / issue #326 (my token gets 403) |
| Effect of #304 / #268 / #260 / #270 / #305 / #306 on traffic | none carries a metric; #304 needs a window starting after 2026-10-09 |
| Who the 53 Direct sessions on `/` are | `newVsReturning` or an internal-traffic filter in the GA4 request |
| Whether `/rashifal/*` was reachable (#266) | a production sweep, which the verification workflow deliberately no longer does |
| Seasonality | a prior-year window; the property has none in these files |
