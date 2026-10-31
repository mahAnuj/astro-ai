# Analyst report — run of 2026-10-31

**Window for every number below: W = 2026-10-01 → 2026-10-28** (28 days, last 3 excluded; GA4 lags 24–48h, GSC 2–3 days).
Source files, read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. Nothing was re-fetched.

| coverage check | value |
|---|---|
| GSC, `dimension: page` | 14,625 impressions / 158 clicks; rows sum to 14,662 (**100%**); `truncated: false` |
| GSC band file | 104 rows at position 6–20 = **12,818 impressions, 88%** of the fetch (`emitted_coverage_pct`); 139 clicks |
| GA4, landing × channel | 456 sessions; rows sum to 457 (**100%**); 111 rows, 75 raw landings (**69** after folding `?query` and trailing-slash variants); `truncated: false` |
| Query-level view | **not in these files.** Everything below is *pages*; a band `position` is the page's average across its queries, not any one query's |

**Read the objective with that in mind.** `OBJECTIVE.md` says "top 5 on the ten highest-impression *queries*". These files cannot show queries, so the objective is scored on the ten highest-impression *pages*.

---

## 1. The band against the objective (W = 2026-10-01 → 10-28, GSC page)

| measure | value |
|---|---|
| pages at average position 6–20 | **104** of 133 pages with impressions |
| their share of site impressions | 12,818 / 14,662 = **87%** |
| band CTR (impressions-weighted) | 139 / 12,818 = **1.08%** |
| site CTR | 158 / 14,625 = **1.08%** |
| band pages by position bucket | 6.x: 29 · 7.x: 28 · 8.x: 12 · 9.x: 14 · 10.x: 8 · 11.x: 7 · 13–19: 6 |
| ten highest-impression pages with average position ≤ 5.0 | **0 of 10** (they sit at 5.8–7.7) |
| pages at position ≤ 5.0, any impressions | 11, totalling 359 impressions (2.4% of 14,662); `/matching` is 346 of those |

**Verdict on the objective: not met, and the data shows no movement toward it.** None of the ten top pages is in the top 5. The band is where the traffic is: 87% of impressions. A single read cannot show movement, because no prior window is in these three files.

### Top 12 band pages, ranked by `band_opportunity` (W, GSC page, coverage 100%)

| # | page | impr. | clicks | CTR | avg pos | opportunity |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,682 | 31 | 1.16% | 6.9 | 129.9 |
| 2 | /learn/debilitated-sun-career/ | 1,752 | 8 | **0.46%** | 6.4 | 97.1 |
| 3 | /learn/sade-sati/ | 1,601 | 11 | 0.69% | 6.4 | 85.1 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 793 | 12 | 1.51% | 6.7 | 35.6 |
| 5 | /learn/jupiter-in-10th-house-career/ | 561 | 2 | **0.36%** | 7.2 | 31.7 |
| 6 | /learn/panch-mahapurush-yoga/ | 549 | 5 | 0.91% | 6.8 | 27.9 |
| 7 | /learn/manglik-dosh/ | 500 | 4 | 0.80% | 7.0 | 26.0 |
| 8 | /learn/career-during-sade-sati/ | 574 | 9 | 1.57% | 6.3 | 25.4 |
| 9 | /learn/7th-lord-placement-marriage-guide/ | 354 | 5 | 1.41% | 7.7 | 16.2 |
| 10 | /learn/marriage-mahadasha-timing/ | 268 | 1 | **0.37%** | 6.5 | 15.1 |
| 11 | /learn/kundali-matching-ashtakoot-guna-milan/ | 192 | 0 | **0.00%** | 7.7 | 11.5 |
| 12 | /learn/10th-lord-in-6th-house-career/ | 293 | 8 | 2.73% | 6.6 | 9.6 |

Top 3 = 6,035 impressions, 47% of the band's 12,818.

## 2. CTR outliers (W, GSC page)

Reference: the 20 band pages with ≥ 100 impressions have an impressions-weighted CTR of **0.97%** (median 1.04%). Outliers below are ≥ 250 impressions and under 0.6× that reference.

| page | impr. | clicks | CTR | avg pos | note |
|---|--:|--:|--:|--:|---|
| /learn/debilitated-sun-career/ | 1,752 | 8 | 0.46% | 6.4 | 2nd-largest band page, 12% of all site impressions. Title/meta was rewritten under #311 — see §4 |
| /learn/jupiter-in-10th-house-career/ | 561 | 2 | 0.36% | 7.2 | also a #311 page |
| /learn/marriage-mahadasha-timing/ | 268 | 1 | 0.37% | 6.5 | not touched by #311 |
| **/matching** (outside band) | 346 | 1 | **0.29%** | **4.4** | the worst gap in the data: a top-5 position with the lowest CTR of any page ≥ 300 impressions. Open: **#508** |

Positive reference for contrast: `/learn/10th-lord-in-6th-house-career/` 2.73% at 6.6, `/learn/kaal-sarp-dosh/` 2.80% at 6.3, and the homepage `/` 6.62% at 5.9 (136 impressions, 9 clicks).
Zero-click pages with ≥ 150 impressions: `/festivals` (249, position **28.1**, outside the band), `/learn/kundali-matching-ashtakoot-guna-milan/` (192, 7.7), `/learn/chronic-health-issues-kundli/` (155, 5.7).

## 3. Decay

| | |
|---|---|
| **Not determined.** | The three files hold one window. Decay needs the same page in an earlier window, and `/tmp/gsc-*.json` carry none. The single measurement that settles it is one page × prior-28-day export (`measurements/gsc-trend-page.json` appears to be that; I did not read it, since the brief fixed the inputs). |

## 4. Post-ship scores — issues closed 2026-10-03 → 2026-10-31 with `thesis:` + `metric:`

30 closed issues carry both fields (`#286` has a thesis only). **Only four have a metric that GA4 or GSC can measure**; the other 26 are repository, CI or tooling properties.

### 4a. Traffic metrics — scored from the three files

Deploys (from each issue's own comment trail): #334 merged **2026-10-13 17:29Z**, #342 **2026-10-14 02:02Z**, #344 **2026-10-14 16:07Z**. W therefore holds **13 pre-deploy and 15 post-deploy days**. The data has no per-day split (#490), so no score below separates the two halves.

| issue | predicted (`metric:`) | actual, W | verdict |
|---|---|---|---|
| **#311** title/meta on four band pages | combined CTR **≥ 1.5%** on ≥ 1,500 impr., average position within ±1 of before | **0.721%** (26 clicks / 3,606 impr.), weighted position 6.67; before (quoted from the issue, **not fetched**): 0.71% = 16 / 2,251 | **MISS.** Impressions condition met (3,606). CTR is 0.78 points under the bar and equal to the issue's own before-figure |
| **#276** early dasha CTA | organic pages/session **≥ 1.20**; < 20 sessions = inconclusive | **1.17** on **30** organic sessions (all channels 40 sessions, 1.13; folded) | **INCONCLUSIVE, below the bar.** 30 × 0.17 ≈ 5 extra page-views against the ≥ 6 the issue implies. Not the "still 1.0" falsification, and not a pass |
| **#329** Manglik checker link | organic pages/session ≥ 1.30 on **≥ 10** sessions; < 10 = inconclusive | **1.00** on **5** organic sessions (all channels 11, pps 1.00) | **INCONCLUSIVE** — half the sample floor. At 4 clicks in 28 days the floor may never be reached |
| **#272** channel + page dimensions in the exports | organic sessions reported separately; ranking URL beside band entries | GA4 has the channel dimension on every row (Organic Search = 224 of 457 row-sessions); GSC has `dimension: page` at 100% coverage | **PASS on shape.** Query-level coverage is not in these files and is not claimed (already re-scored 2026-10-29; not repeated on the issue) |

**The #311 result in detail (W, GSC page):**

| page | impr. | clicks | CTR | avg pos |
|---|--:|--:|--:|--:|
| debilitated-sun-career | 1,752 | 8 | **0.46%** | 6.4 |
| rahu-mahadasha-career-problems | 793 | 12 | 1.51% | 6.7 |
| jupiter-in-10th-house-career | 561 | 2 | **0.36%** | 7.2 |
| manglik-dosh | 500 | 4 | 0.80% | 7.0 |
| four combined | 3,606 | 26 | **0.721%** | 6.67 |

- One page reaches 1.5%; the other three do not, and the two with the most impressions are the lowest.
- **49% of the four pages' impressions** (1,752 / 3,606) sit on `debilitated-sun-career` at 0.46%. If the rewrite was ever going to work, it had to work there.
- Rest of the site, same window: 132 clicks / 11,056 impr. = **1.19%**. The four pages are below it.
- **The rewrite has not shown an effect, and this window cannot show one either way.** It is a miss against the bar as written; the half-pre-deploy mix would only matter if the post-deploy half were far above the average, and a 0.78-point gap is a large thing to hide.

**Not scored from these files, and not claimed:** #345 (needs a band-count delta between two windows) and #355 (needs `llm_stats` over 30 days).

### 4b. Tree and CI metrics — checked by execution this run

| issue | predicted (`metric:`) | actual | verdict |
|---|---|---|---|
| **#607** agent trail rule | 15 of 15 agent definitions carry the rule, asserted by a gate | `ls .claude/agents/*.md` = **15** files; `scripts/verify_agent_trail.py` printed *"PASS — all 15 agent definitions name the issue and the PR, and CLAUDE.md names the three surfaces"* | **PASS** (gate run, not mutation-tested by me) |
| **#338** loop outcomes committed | `measurements/loop.json` on `main`, refreshed within 24h of each scheduled run, ≥ 20 cycles | present; `generated_at` 2026-10-30T23:27:59Z; **94** rows; last commit to it 2026-10-30 23:31Z | **PASS** on presence, row count and freshness at read time. The "each scheduled run" clause is not checked |
| **#396** prefix-cache hits | `cached_tokens` in `src/` 0 → ≥ 1; `/admin/usage` shows a ratio; TPD question answerable | `grep -rn cached_tokens src` = **33** occurrences | **PARTIAL.** Clause 1 holds; clauses 2–3 not checked |

### 4c. Not scored by me — 23 issues

`#313 #316 #320 #349 #355 #362 #369 #372 #373 #374 #397 #400 #405 #408 #409 #442 #449 #493 #495 #510 #515 #286 #345`

Their metrics are properties of the tree, CI, or the LLM-provider blobs (for example "a mutation turns `pr-gates` red", "0 non-loopback connections in the suite", "78/252 readings name a forbidden planet"). None of these is a GA4 or GSC measurement. Running each means executing the gates or reading GCS, which is not what this brief fetched. **One concrete limit:** this checkout is shallow (`git rev-list --count origin/main` = 1), so `#405`'s "commits touching `ARCHITECTURE.md` 60/100 → near 0" cannot be counted here and I did not report a number for it. **I did not post "not scoreable" comments on these 23: they would add noise to issues that carry no traffic claim.**

## 5. Funnel and traffic (GA4, W, landing × channel, coverage 100% of 456 sessions)

Aggregated by landing and channel before ranking; bounce and pages/session are weighted by sessions. Counts use the 457 row-sessions.

| channel | sessions | share | bounce | pages/session |
|---|--:|--:|--:|--:|
| Organic Search | **224** | 49.0% | 49.6% | 1.54 |
| Direct | 206 | 45.1% | 65.5% | 2.11 |
| AI Assistant | 20 | 4.4% | 40.0% | 3.05 |
| Unassigned | 7 | 1.5% | 85.7% | 0.43 |

| landing group | sessions | bounce | pages/session |
|---|--:|--:|--:|
| `/learn/*` (50 landings) | 265 | 60.4% | 1.34 |
| `/` | 90 (Direct 79) | 32.2% | 3.72 |
| `/kundli` | 22 | 77.3% | 1.45 |
| `/matching` | 13 | 69.2% | 2.23 |
| `/numerology` | 9 (all Direct) | 100% | 1.00 |
| `/muhurat*` | 17 | 47.1% | 1.83 |

- **`/learn` is 58% of all sessions and its pages/session is 1.34.** The strongest single rows: `/learn/sade-sati` 16 sessions, bounce 31%, pps 1.87; the weakest: `/learn/griha-pravesh-muhurat-2026-2027` 18 sessions, pps 1.00; `/learn/10th-lord-in-6th-house-career` 12 sessions, bounce 83%, pps 1.00.
- **`/learn/rahu-mahadasha-ketu-antardasha`** is the biggest landing outside `/` with 40 sessions (30 organic, pps 1.17).
- **Owner traffic is not separated.** `/admin/ops` is a top-10 landing with 13 sessions (12 Direct, bounce 61.5%). It sits inside the 206 Direct sessions and the `/` count of 79 Direct sessions is plausibly partly the owner's too. I cannot tell how much.
- **14 sessions (3.1%) land on `(not set)`** — bounce 92.9%, 0 pages/session, 10 of them Organic Search. Cause not determined.

## 6. Confounds — named before any delta

| confound | what it means for §4 |
|---|---|
| **Concurrent ships.** Merged PRs touching reader-facing templates since 2026-10-13 (from the GitHub API; the checkout is shallow, so `git log` could not be used): **#451** (10-21, edits `10th-lord-in-6th-house-career`, `career-during-sade-sati`, others), **#521** (10-25, adds tool links to `debilitated-sun-career`, `jupiter-in-10th-house-career`, `7th-lord-placement-marriage-guide`), **#530** (10-26), **#480**, **#487**, **#556**, **#572**, **#587** (10-22 → 10-29, several touching `manglik-dosh`, `sade-sati`, `debilitated-sun-career`) | **Four pages in the #311 set and the #329 page were edited by one or more other PRs inside W.** The CTR and pages/session movement on them cannot be attributed to a single ship. I do not pick one |
| **Seasonality.** Diwali is **2026-11-08**; muhurat and festival interest rises into it | W ends 11 days before it. I cannot size the effect from one window; it raises impressions more reliably than CTR, so CTR scores are less exposed than session counts |
| **Was the page reachable?** | #253 (stale stylesheet) was fixed by #427 on 2026-10-20 and affected returning visitors, not search arrivals. #266 (`/kundli` "high demand" under the Groq ceiling) closed 2026-10-21. **I have no uptime or error-rate series for W**, so I cannot rule out that some `/kundli` or tool sessions hit a degraded page |
| **Sample size.** | 26 clicks on the four #311 pages: one click moves their combined CTR by about 0.03 points. #276 is 30 sessions and #329 is 5. The #311 miss is large enough to stand; the other two are too small to call |
| **Pre/post mix.** | W is 13 pre-deploy days and 15 post-deploy days. Rescoring cleanly needs a window of post-deploy days only: first fetch on or after **2026-11-13** for #311/#276 and **2026-11-14** for #329 |

## 7. Issues filed this run

**None.** Each finding that needs action is already tracked or is a measurement gap with an owner:

| finding | where it already lives |
|---|---|
| `/matching` at position 4.4, CTR 0.29% | open **#508** |
| no per-page × per-day export, so ships cannot be separated from a mixed window | open **#490** |
| no click event on in-article tool links | open **#570** |
| `debilitated-sun-career` at 0.46% after #311 | a *second* title test would re-file the idea #311 just failed to confirm; that decision belongs to product-manager, which reads this report. Not filed |

## 8. What I could not determine, and the one measurement that settles each

| unknown | measurement that settles it |
|---|---|
| Whether #311 / #276 / #329 moved anything on their own | a **page × day** export (#490), then pre vs post on days only; failing that, a fetch after 2026-11-13 |
| Whether #276's onward views reached `/dasha` | a click event on in-article tool links (#570) |
| Decay on any page | the same page in the prior 28-day window |
| Query-level band positions (the objective's unit) | the `--by query` export covers ~9–10% of impressions, as recorded on #272; it cannot be completed |
| How much of Direct / `/` / `/admin/ops` is the owner | a GA4 internal-traffic filter, or `/admin/ops` excluded from the export |
| What the 14 `(not set)` sessions are | GA4 event-level view for those sessions |
| 23 closed issues' non-traffic metrics | running each gate; out of this brief's inputs |

## 9. Comments posted this run

| issue | verdict posted | link |
|---|---|---|
| #311 | MISS so far | https://github.com/mahAnuj/astro-ai/issues/311#issuecomment-6536436847 |
| #276 | INCONCLUSIVE, below the bar | https://github.com/mahAnuj/astro-ai/issues/276#issuecomment-6536437170 |
| #329 | INCONCLUSIVE, below sample floor | https://github.com/mahAnuj/astro-ai/issues/329#issuecomment-6536437459 |
| #607 | PASS | https://github.com/mahAnuj/astro-ai/issues/607#issuecomment-6536437703 |
| #338 | PASS (presence, size, freshness) | https://github.com/mahAnuj/astro-ai/issues/338#issuecomment-6536437917 |

Not commented: #272 (re-scored 2026-10-29, which said it would not repeat daily), #396 (partial; one clause of three checked), and the 23 issues in §4c.
