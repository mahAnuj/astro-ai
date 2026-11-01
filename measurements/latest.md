# Analyst report — 2026-10-31

**Window W for every number below: 2026-10-01 → 2026-10-28** (28 days, last 3 days excluded; GSC lags 2–3 days, GA4 24–48h). Today is 2026-10-31, so W contains no incomplete day.
Read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API was re-called. Anything marked *quoted* came from an issue body or an earlier comment and was **not** fetched this run.

## 0. Coverage (read before any number)

| source | dimension | coverage | truncated | note |
|---|---|---|---|---|
| GSC `sc-domain:shubhagya.com` | **page** (not query) | 100% of 14,625 impressions (`rows_impressions` 14,662) | no | 133 pages. `position` is a page's *average across its queries*, not any one query's. |
| GSC band | page, position 6–20 | `emitted_coverage_pct` 88% = 12,818 impressions, 104 rows | no | the band file prints only the band; the 12% remainder is pages outside 6–20 |
| GA4 `543505751` | landing (+query string) × channel | 100% of 456 sessions (`rows_sessions` 457) | no | 111 rows, 75 landings. I folded query strings and trailing slashes before ranking pages. |

**Consequence for the objective:** OBJECTIVE.md says "ten highest-impression **queries**". Every export is **page**-level (query-level is a ~9% partial view). So "the band" below is a band of *pages*. The objective is not measurable as worded from these files.

## 1. The band against OBJECTIVE.md (W = 2026-10-01 → 2026-10-28)

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

| measure (W) | value |
|---|---|
| Site total | 14,625 impressions, 158 clicks (GSC) |
| Pages at average position < 6 | 22 pages, 1,585 impressions, 19 clicks |
| **Pages in the band (6–20)** | **104 pages, 12,818 impressions, 139 clicks, CTR 1.08%** |
| Pages > 20 | 7 pages, 259 impressions, 0 clicks |
| Ten highest-impression pages | 9,748 impressions, 93 clicks, positions 5.8–7.7 |
| **…of those ten, at position ≤ 5.0** | **0 of 10** (closest: `planets-in-7th-house-marriage` 5.8, 382 impr) |

→ The objective is **not met**. All ten sit between 5.8 and 7.7. The band holds 88% of the property's impressions.

### Band, ranked by `band_opportunity` (top 12 of 104)

| # | page | impr. | clicks | CTR | avg pos |
|--:|---|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,682 | 31 | 1.16% | 6.9 |
| 2 | /learn/debilitated-sun-career/ | 1,752 | 8 | **0.46%** | 6.4 |
| 3 | /learn/sade-sati/ | 1,601 | 11 | 0.69% | 6.4 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 793 | 12 | 1.51% | 6.7 |
| 5 | /learn/jupiter-in-10th-house-career/ | 561 | 2 | **0.36%** | 7.2 |
| 6 | /learn/panch-mahapurush-yoga/ | 549 | 5 | 0.91% | 6.8 |
| 7 | /learn/manglik-dosh/ | 500 | 4 | 0.80% | 7.0 |
| 8 | /learn/career-during-sade-sati/ | 574 | 9 | 1.57% | 6.3 |
| 9 | /learn/7th-lord-placement-marriage-guide/ | 354 | 5 | 1.41% | 7.7 |
| 10 | /learn/marriage-mahadasha-timing/ | 268 | 1 | 0.37% | 6.5 |
| 11 | /learn/kundali-matching-ashtakoot-guna-milan/ | 192 | 0 | 0.00% | 7.7 |
| 12 | /learn/10th-lord-in-6th-house-career/ | 293 | 8 | 2.73% | 6.6 |

The first three pages hold 6,035 of the band's 12,818 impressions (47%). The long tail is /panchang/{date} and /hi/rashifal pages with 1–9 impressions each; they carry no signal.

## 2. CTR outliers (W)

Comparator: the band's own rate *excluding* the reference page `rahu-mahadasha-ketu-antardasha` = 108 clicks / 10,136 impr. = **1.07%**. Among band pages with ≥ 100 impressions (20 pages): median CTR 1.04%, pooled 0.97%.

| page | impr. | clicks | CTR | expected at 1.07% | P(≤ observed clicks) |
|---|--:|--:|--:|--:|--:|
| /learn/debilitated-sun-career/ | 1,752 | 8 | 0.46% | 18.7 | **0.005** (binomial) |
| /learn/jupiter-in-10th-house-career/ | 561 | 2 | 0.36% | 6.0 | 0.062 |
| /learn/manglik-dosh/ | 500 | 4 | 0.80% | 5.3 | 0.38 |
| /learn/rahu-mahadasha-career-problems/ | 793 | 12 | 1.51% | 8.4 | 0.91 (above, not below) |

- `debilitated-sun-career` is the only page whose shortfall is unlikely to be chance on its own (P = 0.005). Across the ~20 pages with ≥ 100 impressions that was one of ~20 looks, so with a Bonferroni factor of 20 it is ≈ 0.09. **Suggestive, not established.** About 10 clicks per 28 days are at stake.
- **I did not file an issue for it.** The rewrite of its title/meta already shipped (#311, see §3) and did not lift it. A second CTR attempt with no SERP evidence would be a guess, and there is no SERP access in this loop.
- **Watch threshold:** if on the 2026-11-13 fetch the page is still < 0.6% on ≥ 1,500 impressions at unchanged position, file it then with the SERP check as the first step.

## 3. Post-ship scores

Closed since 2026-10-03 = 78 issues (`gh issue list`). Of those, 38 carry both `thesis:` and `metric:` in the body. **Only three of the 38 have a metric GA4 or GSC can decide**: #311, #276, #329 (#272 is a measurement-shape check, scored below). The other 34 are loop, CI, security, copy or admin-page fixes whose metric is a grep, a gate or a page that needs auth. I did not score them from traffic data and I do not call them hits or misses.

**All three deployed 2026-10-13/14, so W holds 13 pre-deploy and 15 post-deploy days.** There is no page × day export (#490), so W cannot be split at the deploy. The numbers below are whole-W, not post-deploy-only; a verdict is therefore provisional in every row.

### Scoreboard

| issue | predicted (`metric:`) | actual in W | verdict |
|---|---|---|---|
| **#311** title/meta on 4 band pages (PR #334, 2026-10-13 17:29Z) | combined CTR **≥ 1.5%** on ≥ 1,500 impr., position within ±1 | **0.721%** (26 clicks / 3,606 impr.), weighted position 6.67 | **MISS (so far).** 0.78 pp below the bar. Rest of the site in W: 132 clicks / 11,056 impr. = 1.19%, so the four pages are below it. |
| **#276** /dasha CTA before 2nd h2 (PR #342, 2026-10-14 02:02Z) | organic pages/session **≥ 1.20**; < 20 sessions = inconclusive | **1.17** on **30** organic sessions, bounce 36.7% | **Not a pass.** The 20-session floor is met, 1.17 < 1.20, and it is not the "still 1.0" outcome either. About 5 extra page-views implied against ≥ 6 needed. |
| **#329** link Manglik checker (PR #344, 2026-10-14 16:07Z) | organic pages/session **≥ 1.30** on ≥ 10 sessions; < 10 = inconclusive | **1.00** on **5** organic sessions, bounce 60% | **INCONCLUSIVE.** Half the sample floor. All 11 sessions on the page, any channel, sit at exactly 1.00. |

### #311 detail (W)

| page | impr. | clicks | CTR | position |
|---|--:|--:|--:|--:|
| debilitated-sun-career | 1,752 | 8 | 0.46% | 6.4 |
| rahu-mahadasha-career-problems | 793 | 12 | 1.51% | 6.7 |
| jupiter-in-10th-house-career | 561 | 2 | 0.36% | 7.2 |
| manglik-dosh | 500 | 4 | 0.80% | 7.0 |
| **combined** | **3,606** | **26** | **0.721%** | 6.67 |
| *before, quoted from the issue body, not fetched* | 2,251 | 16 | 0.71% | — |

- Only `career-problems` clears 1.5%. `debilitated-sun-career` carries 49% of the four pages' impressions at 0.46%.
- The pre-ship gap was itself weak: an earlier analyst note on the issue recorded that the four pages were not statistically distinguishable from the band before the rewrite. That caveat applies in both directions here.
- **Not CTR *or* position moved:** combined CTR is 0.721% against a quoted 0.71% before. At 26 clicks one click is 0.03 pp, so a miss of this size is not sampling noise.

### #276 detail (W)

| `/learn/rahu-mahadasha-ketu-antardasha/` | value |
|---|---|
| Organic Search sessions / pages per session / bounce | 30 / 1.17 / 36.7% |
| Direct | 10 sessions, pages/session 1.00, bounce 90% |
| All channels | 40 sessions, ≈ 1.13 |
| GSC, same page, W | 2,682 impr., 31 clicks, 1.16%, position 6.9 |

- Audience volume moved independently of the CTA (impressions are high), so pre/post populations differ.
- GA4 is landing-level: it cannot show whether an onward view went to `/dasha` (#570).

### #329 detail (W)

| `/learn/manglik-dosh/` | value |
|---|---|
| Organic Search | 5 sessions, pages/session 1.00, bounce 60% |
| Direct | 6 sessions, pages/session 1.00, bounce 100% |
| GSC, same page | 500 impr., 4 clicks, 0.80%, position 7.0 |

- At 4 GSC clicks in 28 days, the 10-organic-session floor may never be reached in any 28-day window. **The metric as written may be unscoreable.**

### One more: #272 (measurement columns exist)

| predicted | actual in W | verdict |
|---|---|---|
| organic sessions reported separately; ranking URL beside band entries | `sessionDefaultChannelGroup` populated on every GA4 row; Organic Search = **224** of 457 session-rows (Direct 206, AI Assistant 20, Unassigned 7). GSC band rows carry `page`. | **PASS on shape.** The *query-level* half remains NOT MET (the export is page-level). |

## 4. Confounds I must name before any delta above

| confound | detail | effect on the scores |
|---|---|---|
| **Concurrent ships on the same pages** | Merged PRs in the W period (titles and dates from `gh pr list --state merged`; **which pages each touched is taken from the earlier analyst comments on #311/#329/#276 and was not re-verified by diff this run**): #451 (10-21, retire remedy claims), #521 (10-25, tool links on `debilitated-sun-career` and `jupiter-in-10th-house-career`), #530 (10-26, remedy pages), #556 (10-28) and #587 (10-29) on Manglik, #304/#312 (10-09, sticky CTA lift, same reader as #276) | **Not separable.** Three of the four #311 pages and the #329 page were edited by something else inside W. I will not attribute the movement to one ship. |
| **No git history available** | This checkout is shallow (1 commit), so `git log origin/main --since` cannot be run. I used merged-PR titles and dates from `gh` instead; file-level overlap for each PR is **not** verified by diff. | The confound list may be incomplete |
| **No per-day split** | No page × day GA4 or GSC export (#490) | W straddles the deploy for all three scores |
| **Seasonality** | Diwali is 2026-11-08 (stated by the repo's own festival table). W ends 10-28, so the run-up is only partly in it. I did **not** size the seasonal effect. | Muhurat and festival pages (`griha-pravesh` 12 organic sessions) may be inflated; the #311/#276/#329 pages are astrology-concept pages and are less festival-driven, but not demonstrably unaffected |
| **Was the page reachable?** | I did not probe production this run (data-only run). #253 (stale stylesheet) closed 2026-10-20 and #266 (/kundli "high demand") closed 2026-10-21; both fixes fall inside W. | Traffic to /kundli before 10-21 may include failed readings; see §5 |
| **Sample size** | 26 clicks (#311), 5 organic sessions (#329), 30 (#276) | #329 cannot carry any conclusion; #311 and #276 can carry "not a pass", not "thesis false" |
| **Baseline provenance** | The "before" figures (0.71%, 0 of 29 onward) are quoted from the issue bodies. They were fetched in earlier runs, not this one. | The deltas are only as good as those |

## 5. Traffic, funnel and measurement notes (GA4, W)

| measure | value |
|---|---|
| Sessions by channel (landing × channel rows) | Organic Search 224, Direct 206, AI Assistant 20, Unassigned 7 |
| Organic Search, weighted | 224 sessions, bounce 49.6%, 1.54 pages/session |
| `/learn/*` landings, organic | 172 of 224 organic sessions (77%) |
| Top organic landing | `/learn/rahu-mahadasha-ketu-antardasha/` — 30 sessions |
| `/` | 90 sessions (Direct 79, bounce 34%, 3.62 pages/session; Organic 9, bounce 11%, 4.44) |
| `/kundli` | 22 sessions: **Direct 12, bounce 100%, 1.00**; Organic 10, bounce 50%, 2.00 |
| `/numerology` | Direct 9, bounce 100% |
| `/matching` | Direct 10, bounce 90%; AI Assistant 2 sessions at 9.00 pages/session |
| `(not set)` landing | **14 sessions** (Organic 10 at bounce 90%, Unassigned 4 at 100%), 0.0 pages/session. The earlier `measurements/latest.md` records the same 14-session pattern as "cause not determined". |
| `/admin/ops` | 13 sessions — owner traffic in the property; Direct is not a clean visitor count |

- **Funnel:** the Direct tool landings (`/kundli`, `/numerology`, `/matching`) bounce at 90–100%. I cannot tell from landing-level GA4 whether those are visitors who abandoned the form or sessions that never fire the result event (#570). **This is the single measurement that would settle the funnel question.**
- **AI Assistant is 20 sessions (4%)** and its two `/matching` sessions averaged 9.00 pages/session. n = 2; reported, not interpreted.

## 6. Decay

**Not determinable from these three files.** They hold one window. Decay needs a prior-window comparison; the repo's earlier exports (`measurements/gsc-trend-page.json`) were not part of the files I was told to read, so I made no claim. I report no decay finding rather than a quoted one.

## 7. Issues filed

**None.** Candidates considered and why each was not filed:

| candidate | why not |
|---|---|
| `debilitated-sun-career` CTR 0.46% | P = 0.005 uncorrected, ≈ 0.09 corrected for ~20 looks; #311 already tried the title; watch threshold set in §2 |
| `(not set)` landing, 14 sessions | already recorded in `measurements/latest.md`; no cause determined by me either |
| Direct tool-landing bounce | needs the form-submit event (#570); a filing now would repeat it |
| Objective names *queries* but exports are *page*-level | known to the repo (the analyst definition documents it); this is chief's call at the next quarterly rewrite, not an analyst issue |

## 8. What I could not determine

| gap | the single measurement that would settle it |
|---|---|
| Whether #311/#276/#329 moved anything | a page × day export, then a fetch of **post-deploy days only**: first on or after **2026-11-13** for #311/#276 (28 days after 10-13/14 is 2026-11-10/11; +3 days GSC lag) and **2026-11-14** for #329 |
| Whether any of the other 34 closed `thesis:` issues achieved theirs | not GA4/GSC quantities; needs the gate output or the admin pages named in each |
| Whether onward views from #276 went to `/dasha` | a GA4 event or link-click for that CTA (#570) |
| Seasonal size of the Diwali run-up | last year's same-window export; none in these files |
| Whether the pages were serving correctly | an HTTP probe of the four pages and `/kundli` — not part of this run |
| File-level overlap of concurrent PRs | a full-depth clone for `git log origin/main --since` |
| Query-level band | a query-level GSC export; only ~9% visible and cannot be recovered |

## 9. Headline (what a reader should take away)

| | |
|---|---|
| **Objective** | Not met: 0 of the 10 highest-impression pages are at position ≤ 5.0 (W) |
| **Misses** | **#311 is a miss so far** (0.721% against ≥ 1.5%). **#276 is not a pass** (1.17 against ≥ 1.20 on 30 sessions). Neither is reported more softly than a hit would be. |
| **Hits** | None among the traffic-scoreable ships |
| **Inconclusive** | #329 (5 sessions against a floor of 10) |
| **Reliability of all three** | provisional — W straddles the deploy and other ships touched the same pages |
