# Analyst report — 2026-11-08

**Window for every number below: 2026-10-09 → 2026-11-05** (28 days, last 3 days excluded; GSC lags 2–3 days, GA4 24–48h) unless a row names another. Previous window where used: 2026-09-11 → 2026-10-08.

| source | file | dimension | coverage | truncated |
|---|---|---|---|---|
| GSC | gsc-band / gsc-all / gsc-trend-page | page | 100% of 20,334 impressions (rows sum 20,368) | no |
| GSC | gsc-trend-query | query | **13%** (partial view; Google withholds the rest) | no |
| GSC | gsc-daily | date | 100% | no |
| GA4 | ga4.json | landing × channel | 100% of 539 sessions (120 rows, 77 landings, 70 distinct paths once query strings are folded) | no |
| GA4 | ga4-daily | date | 28 of 28 days with traffic | — |

Reachability: `curl /health` returned HTTP 200 this run. Individual pages were not probed except `/learn/debilitated-sun-career/`, whose live `<title>` and meta description were fetched and match the registry. Groq TPM failures (#266) were **not determinable** from these files.

---

## 1. Headline, against OBJECTIVE.md

The objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* **It has not moved.**

| measure (window 2026-10-09 → 11-05) | value | note |
|---|---:|---|
| Ten highest-impression queries (query view, 13% coverage) now in top 5 | **0 of 10** | positions 6.3, 7.7, 8.1, 8.3, 8.5, 8.5, 8.6, 8.6, 8.8, 10.2 |
| Queries at position < 5 in the query view | 174 queries, 287 impressions, 1 click | long-tail, near-zero demand |
| Band pages (position 6–20, page mode) | 101 pages, 16,670 impressions (82% of rows), 183 clicks | weighted band CTR **1.10%** |
| Site clicks / impressions | 231 / 20,334 | previous window: 100 / 9,232 (sum of page rows) |
| GA4 sessions, all channels | 539 | Organic Search 291 (54%), Direct 232, AI Assistant 12, Unassigned 5 |

The north star (organic sessions) is growing and the lever has not yet produced a top-5 query. Traffic is arriving because impressions doubled inside the band, not because anything crossed into the top 5.

Weekly shape, same window:

| 7-day block | GSC impressions | GSC clicks | GA4 sessions |
|---|---:|---:|---:|
| 10-09 → 10-15 | 3,000 | 24 | 77 |
| 10-16 → 10-22 | 3,062 | 38 | 132 |
| 10-23 → 10-29 | 6,376 | 70 | 168 |
| 10-30 → 11-05 | 7,896 | 99 | 164 |

Impressions step up in the 10-23 block and clicks follow. GA4 sessions flatten after 10-23 (168, then 164), so the click gain is not yet showing up as more sessions. One-day spike: 10-16, 42 sessions against a 5–19 baseline.

## 2. The band, ranked by opportunity (top 15 of 101; GSC page mode, `position` = the page's average across its queries)

| page | impressions | clicks | CTR | avg position | band opportunity |
|---|---:|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,315 | 41 | 1.24% | 6.7 | 157.9 |
| /learn/debilitated-sun-career/ | 2,248 | 12 | 0.53% | 6.6 | 122.9 |
| /learn/sade-sati/ | 1,911 | 11 | 0.58% | 6.4 | 103.7 |
| /learn/jupiter-in-10th-house-career/ | 1,298 | 10 | 0.77% | 6.9 | 67.9 |
| /learn/7th-lord-placement-marriage-guide/ | 1,010 | 12 | 1.19% | 7.3 | 48.6 |
| /learn/rahu-mahadasha-career-problems/ | 954 | 19 | 1.99% | 6.2 | 38.2 |
| /learn/gochar-2026-planetary-transits/ | 798 | 12 | 1.50% | 6.1 | 35.9 |
| /learn/panch-mahapurush-yoga/ | 640 | 8 | 1.25% | 6.8 | 30.4 |
| /learn/manglik-dosh/ | 513 | 3 | 0.58% | 7.0 | 27.8 |
| /learn/10th-lord-in-6th-house-career/ | 496 | 12 | 2.42% | 6.5 | 17.8 |
| /learn/mangal-mars-in-vedic-astrology/ | 329 | 2 | 0.61% | 7.4 | 17.7 |
| /learn/vimshottari-dasha-explained/ | 214 | 1 | 0.47% | 7.1 | 11.8 |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 194 | 0 | 0% | 7.7 | 11.6 |
| /rashifal | 152 | 0 | 0% | 8.5 | 9.1 |
| /learn/pushya-nakshatra/ | 180 | 2 | 1.11% | 7.3 | 8.8 |

The top five pages hold 9,782 impressions (48% of the property total) and 86 clicks.

## 3. CTR outliers (compared with the band's own weighted CTR, 1.10%)

| page | impressions | clicks | CTR | position | clicks at band CTR | gap |
|---|---:|---:|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 2,248 | 12 | 0.53% | 6.6 | 24.7 | −12.7 |
| /learn/sade-sati/ | 1,911 | 11 | 0.58% | 6.4 | 21.0 | −10.0 |
| /learn/jupiter-in-10th-house-career/ | 1,298 | 10 | 0.77% | 6.9 | 14.2 | −4.2 |
| /learn/marriage-mahadasha-timing/ (pos < 6) | 464 | 2 | 0.43% | 5.6 | 5.1 | −3.1 |
| /matching (pos < 6) | 354 | 2 | 0.56% | 4.5 | 3.9 | −1.9 |
| /learn/shukra-venus-in-vedic-astrology/ (pos < 6) | 229 | 1 | 0.44% | 5.8 | 2.5 | −1.5 |

**Query-intent mismatch on the largest outlier (observation, not filed).** Five of the top 15 queries in the partial query view are phrasings of "sun debilitated in which sign": 193 + 91 + 67 + 46 + 36 impressions, all at positions 6.3–8.6, **0 clicks** between them. The page's live `<title>` is "Debilitated Sun: Why Authority at Work Feels Borrowed"; the answer ("Libra") appears only in the meta description. The query export carries no page column, so the mapping of those queries to this page is an inference from the wording, not a measurement. If it holds, those 433 impressions are about 19% of the page's 2,248, and the query view is 13% coverage, so the real share is not known.

**Why no issue.** #311 (a title/meta test on this same page) has no clean score until 2026-11-13, and #685 (the query-wording version of that test, on `/learn/sade-sati/`) has none until 2026-12-04. #685's own body says *"If this misses too, stop filing title tests for this band."* Filing a third test of the same shape before either has a clean read would pre-empt that rule. Revisit when #311 and #685 score.

## 4. Decay

Site impressions grew 2.2× between windows (9,232 → 20,368), so any loss below is against the tide.

| page | impressions prev → now | position prev → now | clicks prev → now |
|---|---|---|---|
| /learn/ketu-in-vedic-astrology/ | 61 → 10 (−84%) | 7.6 → 7.7 | 1 → 0 |
| /learn/sun-in-10th-house-career/ | 137 → 54 (−61%) | 7.2 → 7.6 | 1 → 2 |
| /learn/the-9-grahas-overview/ | 98 → 39 (−60%) | 7.9 → 9.1 | 0 → 0 |
| /learn/ashwini-nakshatra/ | 95 → 71 (−25%) | **5.5 → 8.0** | 1 → 0 |
| /festivals | 344 → 267 (−22%) | **28.4 → 31.3** | 1 → 0 |
| /muhurat/vidyarambh | 6 → 107 | 5.5 → 7.0 | — |

No ranking page with real volume decayed. Every row above is under 150 impressions, so none carries a conclusion; `/festivals` at position 31 is outside the band, and Diwali (2026-11-08) is the confound for anything festival- or muhurat-shaped. No page present in the previous window was gone. Two queries lost their rows: "rahu dasha with sun mahadasha and job" (32 impressions, position 9.3) and "what is manglik dosh" (23, position 9.5), both in the 13%-coverage view.

## 5. Scores — issues closed in the last 45 days (since 2026-09-24) with a `thesis:` and `metric:`

131 issues closed in the window; **64 carry both a `thesis:` and a `metric:`**. Most of the 64 (infra, security, gates, prompts, ops) have deterministic metrics that were verified at close and cannot be scored from GA4 or GSC; they are out of scope for this report. The traffic-linked ones are below. **No traffic-linked ship has a clean score yet, and none can be called a hit or a miss.** A window is clean only when it starts on or after the deploy.

| issue | ship (merge) | metric | scoreable from | posted this run |
|---|---|---|---|---|
| #311 title/meta on four band pages | PR #334, 2026-10-13 | pooled CTR ≥ 1.5% on ≥ 1,500 impr, position ±1 | **2026-11-13** | pending note (new) |
| #276 /dasha CTA, Ketu antardasha | PR #342, 2026-10-14 | organic pages/session ≥ 1.20 | **2026-11-14** | pending note (new) |
| #329 Manglik checker link | PR #344, 2026-10-14 | organic pages/session ≥ 1.30 on ≥ 10 sessions | 2026-11-14, likely unscoreable | pending note (new) |
| #426 transit-date correction | PR #673, 2026-11-02 | guard: position ±1 of 6.2, impressions not −20% | 2026-12-03 | pending note (new) |
| #685 Sade Sati title | PR #690, 2026-11-03 | CTR ≥ 1.2% on ≥ 1,200 impr, position ±1 of 6.4 | 2026-12-04 | pending note (new) |
| #570 `cta_click` event | PR #688, 2026-11-03 | `cta_click` rows by from/to path | not determinable, see §7 | pending note (new), filed #782 |
| #508 /matching title/meta | PR #696, 2026-11-03 | CTR ≥ 1.0% on ≥ 300 impr, position ±1.5 of 4.3 | 2026-12-04 | already noted 2026-11-07, nothing posted |
| #553 panch-mahapurush link | PR #615, 2026-10-31 | organic pages/session ≥ 1.30 on ≥ 10 sessions | 2026-12-01 | already noted 2026-11-07, nothing posted |
| #518 tool routes on 76 articles | five slices, last PR #754, 2026-11-06 | zero-route articles; pages/session on /learn/* | 2026-12-07 | already noted 2026-11-07, nothing posted |

Six pending notes went on issues that had none. Each of those threads held 4–20 daily "NOT SCOREABLE" / "MISS so far" / "INCONCLUSIVE" comments written before the 2026-11-06 rule. This run read every thread's last comments first and wrote one note per issue.

### What the numbers show before the clean windows, not a score

| page | window | what it shows | direction vs bar |
|---|---|---|---|
| #311, four pages pooled | 10-09 → 11-05 | 5,013 impr, 44 clicks, **0.88%** CTR (previous window 2,353 / 16 / 0.68%) | below the 1.5% bar by 0.6 points; this window holds 4 pre-deploy days |
| of which career-problems | same | 954 / 19 / **1.99%**, position 7.4 → 6.2 | the only one of the four above 1% |
| of which debilitated-sun, manglik, jupiter-10th | same | 0.53% / 0.58% / 0.77% | flat or worse |
| #276 Ketu antardasha, GA4 | same | organic 42 sessions at **1.40** pages/session; all channels 56 at 1.30 | above the 1.20 bar, but the window holds 5 pre-deploy days and PR #680 added a second tool route on 2026-11-02 |
| #329 Manglik, GA4 | same | organic **3** sessions at 1.00 | sample 3 vs the 10 floor |
| #685 Sade Sati, GSC | same | 1,911 impr, 11 clicks, **0.58%**, position 6.4 | baseline only; deploy was 11-03 |
| #508 /matching, GSC | same | 354 impr, 2 clicks, 0.56%, position 4.5 (previous window: 45 impr, position 6.4) | baseline only |

**If #311 reads as it does now on a clean window, it is a miss** and #276's CTA will not be separable from #680's. Neither is a result today.

### Confounds, named

| confound | evidence |
|---|---|
| Concurrent ships on the same pages | PR #680 (2026-11-02) added a first-screen tool route to Sade Sati, Ketu antardasha and Manglik the day before #685/#426 cleared their first full day. #518 slices touched debilitated-sun and jupiter-10th (10-25), career-problems (10-31), manglik (11-02). `git log origin/main --since=2026-10-09 -- src` lists 96 commits touching `src/`. |
| Claim rewrites on ranking pages | Manglik pages: 10-28, 10-29, 11-07. Sade Sati: 10-21, 10-28, 11-02 ×2. These are truth corrections, not SEO changes, and they sit on the same pages being scored. |
| Seasonality | Diwali is 2026-11-08, and the impression doubling begins in the 10-23 block. Seasonality is **not determined** for the learn pages, since there is no year-ago window on a site this young. |
| Query mix | Impressions on the four #311 pages went 2,353 → 5,013. A CTR measured over a changing query mix is not a before/after of one title. |
| Page working? | `/health` 200 this run; the debilitated-sun title/description were fetched live and match the registry. #266 (Groq TPM) affects LLM pages, not these static `/learn/` articles. |
| Sample size | #329 has 3 organic sessions. #685's baseline is 11 clicks, a doubling to ~22 is about 2 Poisson standard deviations, as #685 itself says. |

## 6. Funnel and engagement (GA4 landing × channel, 2026-10-09 → 11-05, folded across query strings and trailing slashes)

GA4 here has landing and channel only. Form-start, form-submit and result events are **not in the export**, so the landing → form → result → second page funnel cannot be drawn.

| landing group | sessions | organic sessions | pages/session (weighted) | note |
|---|---:|---:|---:|---|
| `/` | 87 | 7 | 3.77 | mostly Direct; the best-engaged landing |
| all `/learn/*` | 339 (63% of 539) | 232 | 1.35 (organic 1.41) | the front door |
| `/learn/rahu-mahadasha-ketu-antardasha/` | 56 | 42 | 1.30 (organic 1.40) | single largest organic landing |
| `/kundli` | 23 | 10 | 1.74 | bounce 70% |
| `/matching` | 12 | 1 | 1.92 | bounce 75% |
| `/numerology` | 11 | 2 | 1.00 | bounce 82% |
| `/learn/sade-sati` | 14 | 12 | 1.93 | bounce 29% |
| `/learn/panch-mahapurush-yoga` | 8 | 7 | 1.00 | bounce 14% — a low bounce with 1.00 pages/session is a measurement oddity, not engagement |
| `/admin/ops` | 18 | 1 | 1.33 | the owner's own visits, in Direct |
| `(not set)` | 16 | 12 | 0.00 | bounce 94% |

Organic-weighted pages/session across the whole property: **1.55** on 291 sessions.

Measurement noise to carry: 19 `/admin/*` sessions (3.5% of the property) and 16 `(not set)` sessions are in the 539. They do not affect Organic Search except for 1 + 12 sessions, but they inflate Direct and pull down any whole-property pages/session. 12 sessions arrive as a new "AI Assistant" channel; no earlier window was read this run, so whether it is new is **not determined**.

## 7. What I could not determine, and the single measurement that settles each

| gap | single measurement |
|---|---|
| Whether `cta_click` fired once since 2026-11-03 (#570, and the secondary metrics of #518, #276, #329, #553) | a GA4 events export of `eventName = cta_click` split by `from_path` / `to_path`. **Filed as #782.** |
| Any per-page score before its clean window | a GSC `page × date` export (#490); until then only windows starting after the deploy are scoreable |
| Whether the band moved at the **query** level | the query export covers 13% of impressions; 87% of the band cannot be recovered. No query-level claim about the whole band is made here |
| Seasonality of the learn-page impression doubling | a year-ago window, which does not exist; or the same pages' impressions after Diwali (2026-11-08) falls out of the 28 days |
| The form → result funnel | GA4 events for form start and result render, which the export does not carry |
| #272's second half (ranking URL beside each top-10 query) | `gsc-trend-query.json` has no page column; the first half (organic sessions as a separate number, 291) is present |

## 8. Filed and posted this run

| action | where |
|---|---|
| Issue filed | **#782** `[MEASURE] fetch_ga4.py cannot export events…` with an Evidence Block |
| Pending notes (once each) | #311, #276, #329, #426, #685, #570 |
| Deliberately not posted | #508, #553, #518 (notes already there); no unchanged verdict repeated |
| Deliberately not filed | a title/meta issue for `/learn/debilitated-sun-career/`, see §3 |
