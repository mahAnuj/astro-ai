# Analyst report — 2026-10-24

**Window on every number: 2026-09-24 → 2026-10-21 (28 days; excludes the last 3 days, GSC/GA4 lag).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. Nothing was re-fetched. Numbers tagged *(issue)* come from an issue body and were **not** measured this run.

## 0. Coverage and what these exports can and cannot say

| Export | Dimension | Coverage | Truncated | Note |
|---|---|---|---|---|
| gsc-all | **page** (not query) | 100% of 11,828 impressions; 129 rows | no | rows sum to 11,867 vs property total 11,828 (+39, as exported) |
| gsc-band | **page** | 109 rows at position 6–16 = 10,504 impressions (89% of 11,867) | no | `position` is the page's average across its queries, not any one query's |
| ga4 | landing(+query string) × channel | 100% of 365 sessions; 106 rows; 70 landings (66 after folding query strings and trailing slashes) | no | rows sum to 366 sessions vs 365 total |

- **Query-level data was not exported**, so the OBJECTIVE's "ten highest-impression *queries*" cannot be reported. Everything below is **pages**. Query coverage is ~9% when fetched (#291).
- **Not determinable this run: decay.** No prior-window export was supplied, so no page can be called "losing ground". Single measurement that settles it: the same `--by page` GSC export for 2026-08-27 → 2026-09-23.
- **Not determinable: funnel step-through** (landing → form → result → second page). The export has landing, bounce and pages/session only, no events.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page-level proxy: the ten highest-impression pages, 2026-09-24 → 2026-10-21.

| Metric (window 2026-09-24..10-21) | Value |
|---|---|
| Band pages (position 6–16 observed) | **109** |
| Band impressions / clicks / weighted CTR | 10,504 / 111 / **1.06%** |
| Band pages with **zero clicks** | **77 of 109** |
| Band pages with ≥100 impressions | 24, holding 9,086 impressions (86% of band) |
| Median CTR of those 24 | 0.83% |
| Non-band pages | 20 rows, 1,363 impressions, 8 clicks |
| Site total | 11,867 impressions / 119 clicks (1.00%) |
| Learn-article share of band impressions | 10,009 of 10,504 (95%) |
| Ten highest-impression pages | 7,765 impressions, 69 clicks (0.89%); **8 in band**, 1 at 5.8, 1 at 4.4 |
| Pages in the top 5 with ≥30 impressions | **1** — `/matching`, 340 impressions, **0 clicks** |

**Where the objective stands:** none of the ten highest-impression pages with real click volume is in the top 5. Closest: `planets-in-7th-house-marriage` 5.8, `debilitated-sun-career` 6.1, `sade-sati` 6.2.

### Band list, ranked by `band_opportunity` (top 12 of 109)

| # | Page | Impr. | Clicks | CTR | Avg pos | Opportunity |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,019 | 26 | 1.29% | 7.5 | 95.1 |
| 2 | /learn/debilitated-sun-career/ | 1,245 | 7 | 0.56% | 6.1 | 67.7 |
| 3 | /learn/sade-sati/ | 1,098 | 10 | 0.91% | 6.2 | 55.9 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 797 | 9 | 1.13% | 6.9 | 38.8 |
| 5 | /learn/manglik-dosh/ | 473 | 2 | 0.42% | 7.4 | 26.4 |
| 6 | /learn/panch-mahapurush-yoga/ | 470 | 3 | 0.64% | 7.0 | 25.2 |
| 7 | /learn/jupiter-in-10th-house-career/ | 379 | 1 | 0.26% | 6.9 | 21.7 |
| 8 | /learn/career-during-sade-sati/ | 386 | 4 | 1.04% | 7.0 | 19.2 |
| 9 | /learn/marriage-mahadasha-timing/ | 244 | 1 | 0.41% | 6.4 | 13.6 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 274 | 5 | 1.82% | 7.7 | 11.4 |
| 11 | /learn/ | 140 | 0 | 0% | 10.5 | 8.4 |
| 12 | /learn/kundali-matching-ashtakoot-guna-milan/ | 139 | 0 | 0% | 7.8 | 8.3 |

The top 4 alone hold 5,159 impressions (49% of the band) and 52 clicks.

## 2. CTR outliers

Comparison basis: the band's own rates — weighted 1.06%, median 0.83% for pages with ≥100 impressions.

| Page | Impr. | Clicks | CTR | Pos | Why it is a finding |
|---|---:|---:|---:|---:|---|
| /matching | 340 | 0 | 0% | **4.4** | Best position on the site, no clicks. At the band's 1.06% you would expect ~3.6 clicks; P(0) ≈ 2.7%. Moderate evidence, not conclusive. **Already tracked: #508** — not re-filed |
| /learn/ | 140 | 0 | 0% | 10.5 | Index page, no clicks |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 139 | 0 | 0% | 7.8 | |
| /learn/guru-jupiter-in-vedic-astrology/ | 112 | 0 | 0% | 7.0 | |
| /learn/sun-in-10th-house-career/ | 110 | 0 | 0% | 7.0 | |
| /learn/the-9-grahas-overview/ | 103 | 0 | 0% | 8.0 | |
| /learn/rahu-in-vedic-astrology/ | 102 | 0 | 0% | 7.5 | |
| /learn/jupiter-in-10th-house-career/ | 379 | 1 | 0.26% | 6.9 | Lowest CTR among pages >300 impressions |
| /learn/manglik-dosh/ | 473 | 2 | 0.42% | 7.4 | Both #311 and #329 touched this page (see §3) |
| *Highest:* kaal-sarp-dosh 2.24% (134 impr), pushya-nakshatra 1.96% (102), 7th-lord-placement 1.82% (274), 10th-lord-in-6th-house 1.72% (174) | | | | | Small samples (2–5 clicks each); do not treat as a benchmark |

**Why this matters for §3:** #311 used `rahu-mahadasha-ketu-antardasha` at **2.05%** *(issue)* as the "what a good title earns" reference. In this window the same page is at **1.29%** (26/2,019, position 7.5 unchanged). The reference was not stable, so #311's 1.5% pass bar sits above what its own reference page now delivers.

## 3. Post-ship scores (issues closed 2026-09-26 → 2026-10-24 carrying `thesis:` + `metric:`)

27 issues qualified. 5 have a metric GA4/GSC can measure; scores posted as comments on each. The other 22 have repo/ops metrics (see §3b).

### 3a. Scoreable from GA4/GSC

| Issue | Shipped (deploy) | Predicted | Actual (window 2026-09-24..10-21) | Verdict |
|---|---|---|---|---|
| **#272** exports carry channel + page | PR #292, 2026-10-08 | Organic sessions reportable; ranking URL per band row | Organic Search **170 of 365 sessions**; GSC by page, 100% coverage | **PASS** (structural). Caveat: pages, not queries |
| **#311** rewrite title/meta on 4 band pages | PR #334, 2026-10-13T17:29Z | Combined CTR **≥1.5%** on ≥1,500 impr., position ±1 | 4 pages: **2,894 impr, 19 clicks, 0.66%**, pos 6.64. Baseline *(issue)* 0.71% | **NO LIFT VISIBLE — probable MISS, not final.** 20 of 28 days are pre-deploy |
| **#276** /dasha CTA on Rahu–Ketu article | PR #342, 2026-10-14T02:02Z | pps **≥1.20** (Organic), ≥20 sessions | Organic **28 sessions, pps 1.04**, bounce 35.7%. Baseline *(issue)* 1.0 | **NOT SCOREABLE — leaning no effect.** ~1 extra page-view in the whole window |
| **#329** Manglik checker link | PR #344, 2026-10-14T16:07Z | pps **≥1.30** on ≥10 organic sessions | Organic **3 sessions**, pps 1.00, bounce 100% | **INCONCLUSIVE** (below the issue's own 10-session floor) |
| **#515** nightly rashifal, traffic half of metric | PR #516, 2026-10-24 | `/rashifal/*` organic sessions up | **0 post-deploy days.** Baseline: 4 `/rashifal*` GA4 landings, 5 sessions (Direct 4, AI Assistant 1), 0 organic; GSC `/rashifal` 97 impr / 0 clicks / pos 10.1 | **NOT SCOREABLE.** Re-score on/after 2026-11-24 |

**The misses, plainly:**
- **#311 and #276 have shown nothing so far.** Neither window has finished, so neither is a confirmed miss — but neither has produced any evidence of a hit, and the indicative arithmetic points the wrong way for both (#311: post-deploy slice implied ≈0.5% if the pre-deploy days ran at the 0.71% baseline; #276: ≈1 extra page-view in 28 sessions). Both inferences rest on an assumed baseline and an unsplittable window.
- **Neither can be called until:** post-deploy 28-day windows close on **2026-11-10** (#311) and **2026-11-11** (#276/#329); fetch the GSC/GA4 exports on or after 2026-11-13.
- **The #276/#329 thesis class** ("add a link inside a /learn article → onward visits") has now produced 0 observed onward visits on 31 organic sessions combined (28 + 3). That is too small to refute it and large enough to stop calling it validated.

### 3b. Closed with a thesis, but no GA4/GSC metric — not scored

Out of the analyst's data. Their metrics are counts in the repo, workflow behaviour or ops figures. No comment posted; stated here so the omission is visible.

| Group | Issues |
|---|---|
| Loop / CI / workflow | #286, #313, #316, #320, #374, #442, #493 |
| /admin/ops and measurement plumbing | #338, #345, #349, #369, #372 |
| Token, LLM and test hygiene | #355, #396, #400, #449, #362 |
| Security / correctness | #373, #408, #409, #397, #405 |

(22 issues.) #397 (Nadi copy on `/matching`) is the only one with a plausible reader-facing effect, but its metric is a string count, not traffic.

## 4. Confounds — named before any delta

| Confound | Finding |
|---|---|
| **Concurrent ships** (`git log origin/main --since=2026-09-24`, repo is shallow; fetched with `--shallow-since`) | 160 commits on `main` since 2026-09-24; 44 touch `src/`. Touching the five scored pages' templates in-window: **#451** (10-21: rahu-career-problems, manglik-dosh, rahu-ketu), **#344** (10-14: manglik-dosh), **#342** (10-14: rahu-ketu), **#334** (10-13: titles for 4 pages). #480 and the Sahasranama fix touch debilitated-sun / jupiter-10th on 10-22 and 10-23 — **after** the window. Manglik-dosh is hit by #311, #329 and #451 inside the window: **its movement cannot be attributed to one ship.** |
| **Seasonality** | Window spans Pitru Paksha (2026-09-27), **Navratri (2026-10-11)** and **Dussehra (2026-10-20)** per `festival_registry.py` — dates read from the repo, not independently verified. Diwali (2026-11-08) is 18 days after the window ends. The scored pages are dasha/dosha/career topics rather than festival pages, but the window is not a neutral baseline. |
| **Was the page reachable?** | #253 (stale `/static/` cache) fix merged **2026-10-20**; #266 (/kundli "high demand") closed **2026-10-21**. So for **~24 of 28 days the stale-stylesheet defect was live**, and `/kundli` 413s ran for the whole window. `/kundli` numbers (below) are therefore not clean engagement. Not checked: whether the scored `/learn` pages themselves returned errors — no uptime data in the exports. |
| **Sample size** | Site total is 365 sessions / 119 clicks in 28 days. Most per-page figures rest on <10 clicks; ±1 click on the #311 group moves its CTR by 0.03 pts. |
| **Window mixing** | Every post-ship page-level number here spans pre- and post-deploy days and cannot be split by day from these exports. |

## 5. Traffic context (GA4, window 2026-09-24..10-21, 365 sessions)

| Channel | Sessions | Share |
|---|---:|---:|
| Organic Search | 170 | 46.6% |
| Direct | 163 | 44.7% |
| AI Assistant | 25 | 6.8% |
| Unassigned | 8 | 2.2% |

| Landing (channels folded) | Sessions | Bounce | Pages/session | Note |
|---|---:|---:|---:|---|
| / | 92 | 29.3% | 3.82 | Direct 78 |
| /learn/rahu-mahadasha-ketu-antardasha | 33 | 45.5% | 1.03 | Organic 28 |
| /kundli | 16 | 68.8% | 1.62 | Organic 10: bounce 50%, pps 2.0 |
| /learn/sade-sati | 15 | 26.7% | 1.13 | |
| /learn/griha-pravesh-muhurat-2026-2027 | 14 | 64.3% | 1.00 | |
| /matching | 8 | 62.5% | 3.13 | Direct 5 (bounce 100%), AI Assistant 3 (pps 6.67) |

- Organic Search: 170 sessions, bounce 44.1%, pps 1.60 (session-weighted). GSC reports 119 clicks in the same window; GA4 organic is 43% higher, which is plausible for non-Google engines but is **not reconciled** here.
- **AI Assistant is 25 sessions across 16 landings**, including `/matching` (3, pps 6.67, bounce 0%) — the highest-engagement entry to a tool page in the export. Sample is 3 sessions.
- `/numerology`: 4 sessions, all Direct; no organic numerology tool landing. `/matching` has no organic landing despite 340 GSC impressions (position 4.4, 0 clicks).
- **Internal traffic in GA4:** `/admin/ops` 5 sessions and `/admin/activity` 1 = 6 of 365 (1.6%); `(not set)` 8. Small; not filed.

## 6. Filed

| Issue | Why |
|---|---|
| **#528** privacy: the visitor's `/ask` question travels in the URL and is recorded by GA4 | One GA4 landing is `/ask?q=But+you+said+i+am+very+unlikely+to+get+stable+relstionship.&c=general` (Organic Search, 2 sessions). `ask.py:611-616` redirects with the question in the URL; `analytics.js:43` sends the full URL. Scale unknown beyond this row. |

Not filed, deliberately:
- `/matching` 0 clicks at position 4.4 — already **#508**.
- #311 / #276 / #329 under-performance — windows are still open; filing a bug now would be the story, not the measurement.
- Decay, funnel — undeterminable from these exports (§0).

## 7. What I could not determine, and the measurement that would settle it

| Question | Settled by |
|---|---|
| Is any page losing ground (decay)? | GSC `--by page` for 2026-08-27 → 2026-09-23 |
| Did #311's titles lift CTR? | Same 4 pages, GSC `--by page`, 2026-10-14 → 2026-11-10 (fetch on/after 2026-11-13); also a SERP check that Google shows the new titles |
| Did #276 / #329's links lift onward visits? | GA4 for those landings 2026-10-15 → 2026-11-11, or a click event on the CTA links |
| Which *queries* sit at 6–20 (the objective's unit)? | `--by query`, accepting ~9% coverage |
| Why `/matching` earns 0 clicks at 4.4 | SERP snapshot of its title/description for its queries; #508 owns it |
| Did the scored `/learn` pages serve errors in the window? | Cloud Run request logs for those paths, 2026-09-24..10-21 |
| GA4 organic (170) vs GSC clicks (119) | Per-engine source split in GA4 |

## 8. Method notes

- Folded GA4 landings by path (query string and trailing slash removed) before ranking; bounce and pages/session are session-weighted across channel rows.
- Deploy times are PR merge times from `gh pr list`; the deploy follows within minutes but the exact serving revision per commit was not checked (`/health` not queried).
- Score comments posted: #272, #276, #311, #329, #515. Issue filed: #528. No code, template or `BACKLOG.md` edited.
