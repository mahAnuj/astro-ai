# Analyst report — 2026-11-13

**Window for every number unless a row says otherwise: W = 2026-10-14 → 2026-11-10** (28 days, last 3 excluded; GSC lags 2–3 days, GA4 24–48h).
**Previous window P = 2026-09-16 → 2026-10-13** (`gsc-trend-*.json` only; there is no GA4 previous-window file, so no GA4 period-on-period figure is stated).
All numbers read this run from `/tmp/*.json`. Nothing carried from BACKLOG.md or earlier comments except where marked "posted earlier".

## 0. Coverage — read before any number

| export | dimension | coverage | truncated | note |
|---|---|---|---|---|
| `gsc-all.json` | page | 100% of 23,843 impressions (141 rows) | no | rows sum to 23,921 (page sum vs property total) |
| `gsc-band.json` | page, position 6–20 | whole fetch 100%; **emitted 104 rows = 82% (19,648 impr.)** | no | position is the page's average across its queries, not one query's |
| `gsc-trend-page.json` | page, W vs P | 100% of W impressions | no | 141 pages now, 126 before; 50 new, 35 gone |
| `gsc-trend-query.json` | **query** | **14%** of W impressions (3,276 of 23,843) | no | partial view; Google withholds the rest. Nothing below concludes anything about the whole band from it |
| `ga4.json` | landing × channel | 100% of 677 sessions (146 rows, 94 landings; 87 after folding `?query` and trailing slash) | no | rows sum to 676 |
| `ga4-daily.json`, `gsc-daily.json` | date | 28 of 28 days with traffic | no | |
| `ga4-events.json` | eventName | present, 16 event names | no | `cta_click` exists only from 2026-11-03 04:42Z, so W holds 8 of 28 days of it (see §6) |

## 1. The band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* The query export covers 14%, so the **page** view is what can be measured; it stands in for the objective, and the ten highest-impression pages below are not the ten highest-impression queries.

| measure (W, GSC page) | value |
|---|---|
| property impressions / clicks / CTR | 23,843 / 296 / 1.24% |
| pages at position 6–20 | 104 pages = 19,648 impressions = 82% of all (emitted) |
| pages by position bucket (all 141) | 1–5: 13 pages, 134 impr., 5 clicks · 6–10: 99 pages, 23,081 impr., 290 clicks · 11–20: 20 pages, 373 impr., 1 click · 21+: 9 pages, 333 impr., 0 clicks |
| **ten highest-impression pages at position ≤ 5.0** | **0 of 10.** Best is 5.4 (career-during-sade-sati); the other nine are 5.9–7.3 |
| band median CTR | 0.0% over all 104 band pages (most have a handful of impressions); 1.0% among the 16 pages with ≥ 300 impressions |

98% of impressions (23,081 + 373 = 23,454 of 23,921, the page-row sum) are in the 6–20 band; the top-5 bucket holds 134. The objective is unmet on the page proxy, and the gap is one to two positions on the biggest pages.

### Band list, ranked by `band_opportunity` (top 15 of 104; W)

| # | page | impr. | clicks | CTR | avg pos | impr. P → W |
|---|---|---:|---:|---:|---:|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,699 | 54 | 1.46% | 6.5 | 1,753 → 3,699 |
| 2 | /learn/debilitated-sun-career/ | 2,515 | 14 | 0.56% | 6.6 | 986 → 2,515 |
| 3 | /learn/sade-sati/ | 1,967 | 13 | 0.66% | 6.6 | 911 → 1,967 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,623 | 14 | 0.86% | 6.9 | 349 → 1,623 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,310 | 13 | 0.99% | 7.3 | 222 → 1,310 |
| 6 | /learn/gochar-2026-planetary-transits/ | 1,147 | 16 | 1.39% | 6.2 | 17 → 1,147 |
| 7 | /learn/planets-in-7th-house-marriage/ | 909 | 8 | 0.88% | 6.1 | 491 → 909 |
| 8 | /learn/panch-mahapurush-yoga/ | 813 | 10 | 1.23% | 6.9 | 371 → 813 |
| 9 | /learn/manglik-dosh/ | 508 | 3 | 0.59% | 6.8 | 452 → 508 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 632 | 16 | 2.53% | 6.6 | 188 → 632 |
| 11 | /learn/mangal-mars-in-vedic-astrology/ | 407 | 3 | 0.74% | 7.3 | n/r |
| 12 | /learn/vimshottari-dasha-explained/ | 297 | 2 | 0.67% | 7.0 | n/r |
| 13 | /learn/saturn-in-10th-house-career/ | 241 | 2 | 0.83% | 8.1 | n/r |
| 14 | /learn/sun-mahadasha/ | 238 | 4 | 1.68% | 6.1 | n/r |
| 15 | /learn/name-numerology-explained/ | 200 | 2 | 1.00% | 6.8 | n/r |

n/r = not read this run (only the first ten rows were pulled from the trend file).

Pages 1–9 alone are 14,491 of the band's 19,648 emitted impressions (74%) at CTR 0.56%–1.46%. One position gained on #2–#5 is where the clicks are.

## 2. Scores — issues closed in the last 45 days with a `thesis:` and a `metric:`

| issue | deploy | window clean today? | action this run | verdict |
|---|---|---|---|---|
| **#311** four band pages, title/meta | PR #334, 2026-10-13 17:29Z | **yes** (W starts 10-14) | **scored, posted once** | **MISS** — 0.937% (53/5,658) vs ≥ 1.5% bar; baseline 0.574% (15/2,614) |
| #276 Rahu–Ketu antardasha CTA (pages/session ≥ 1.20) | PR #342, 2026-10-14 02:02Z | no — W's first day is the deploy day | none; "pending — scoreable from 2026-11-14" posted earlier | pending |
| #329 manglik-dosh tool link (≥ 1.30 on ≥ 10 sessions) | PR #344, 2026-10-14 16:07Z | no — deploy day inside W | none; pending note posted earlier | pending; at 3 organic sessions in W it will likely be unscoreable |
| #553 panch-mahapurush-yoga | PR #615, 2026-10-31 | no | none; pending to 2026-12-01 posted earlier | pending |
| #508 /matching title | PR #696, 2026-11-03 | no | none; pending to 2026-12-04 posted earlier | pending (see §4: position guard already breached) |
| #685 sade-sati title | PR #690, 2026-11-03 | no | none; pending to 2026-12-04 posted earlier | pending |
| #570 / #782 `cta_click` | PR #688, 2026-11-03 04:42Z | no | none; pending posted earlier | pending (§6) |
| #518 learn → tool routes | five slices 10-25 … 11-06 | no | none; pending to 2026-12-07 posted earlier | pending |
| #426 sade-sati guard | PR #673, 2026-11-02 | no | none; pending to 2026-12-03 posted earlier | pending |
| #735 /admin out of GA4 | PR #877, 2026-11-11 | no | none; pending to 2026-12-12 posted earlier | pending |
| #528 /ask `q=` out of the URL | PR #801, 2026-11-09 | no | none; pending to 2026-12-10 posted earlier | pending |
| **#835** debilitated-sun lede + FAQ | PR #940, 2026-11-13 00:29Z | no | **pending note posted once** | pending — scoreable from 2026-12-14 |
| #843 per-word compounds | PR #850, 2026-11-10 | n/a | none | the `metric:` is a render count, verified by the build, not a traffic figure. The issue itself says the analyst would call it unscoreable: /numerology had 24 landing sessions in W (GA4, folded) |
| #570-family, #896, #885, #397, #618, #602, #345, #272 | various | n/a | none | `metric:` is deterministic or tooling; no GA4/GSC figure to score |

### #311 in full (this is the miss)

| four pages | P impr / clicks / CTR / pos | W impr / clicks / CTR / pos |
|---|---|---|
| career-problems | 827 / 6 / 0.73% / 7.2 | 1,012 / 22 / **2.17%** / 5.9 |
| debilitated-sun-career | 986 / 6 / 0.61% / 6.1 | 2,515 / 14 / **0.56%** / 6.6 |
| manglik-dosh | 452 / 2 / 0.44% / 7.3 | 508 / 3 / **0.59%** / 6.8 |
| jupiter-in-10th | 349 / 1 / 0.29% / 6.8 | 1,623 / 14 / **0.86%** / 6.9 |
| **combined** | 2,614 / 15 / 0.574% / 6.75 | 5,658 / 53 / **0.937%** / 6.58 |
| reference: rahu-ketu antardasha | 1,753 / 30 / 1.71% / 7.5 | 3,699 / 54 / 1.46% / 6.5 |

- The thesis, that a title/meta rewrite raises CTR at unchanged position, was **not** borne out: 3 of 4 stay below 0.9%; the one page above 2% also gained 1.3 positions.
- The sibling used as the target (2.05% in the filing window) fell to 1.46%, so the target was a one-window figure.
- **Lesson for the loop:** do not file another "rewrite the title of a low-CTR band page" issue on the strength of one sibling's CTR. Look first at whether the position moved.
- The same lever is in flight on #685 (sade-sati) and #835 (debilitated-sun); both are scored on their own windows and neither may be scored early.

## 3. Confounds (named before any delta)

| confound | what the data shows | effect on the reading |
|---|---|---|
| **Concurrent ships** (merged PRs 2026-10-14 → 11-13, from `gh pr list`) | #518's tool links on four band pages (10-25, 10-31, 11-01, 11-02); #685 sade-sati title 11-03; #696 /matching title 11-03; #615 panch-mahapurush edit 10-31; many `[UI]` text-size and a11y PRs 11-11/12 (#921, #922, #923, #927, #932 and others); privacy and loop-tooling PRs | cannot attribute any page-level move to a single ship. #311's pages took #518 links inside W |
| **Impression step-change** | site impressions run ~400–520/day to 10-22, then ~930–1,050 from 10-25, ~1,100–1,300 from 11-01 (`gsc-daily.json`). Not a festival spike: it plateaus, and the plateau begins before Diwali (2026-11-08) | W vs P (+127% impressions, +172% clicks, `gsc-trend-page.json` row sums 23,921 / 10,549 and 296 / 109) is mostly this step. Cause not determined |
| **Seasonality** | Diwali 2026-11-08 falls in W. Evergreen dasha/career pages dominate, which is not festival traffic, but festival effect is **not determined** | any 2026-11-0x single-day number is suspect |
| **Page reachable?** | no outage or stale-asset evidence in these files; not independently probed this run | traffic is read as real engagement only on that assumption |
| **Internal traffic in GA4** | `/admin/ops` = 20 landing sessions (19 Direct) of 677 in W; `(not set)` landing = 20 sessions, 95% bounce. #735's fix deployed 2026-11-11, **after** W ends | GA4 Direct (290 sessions, bounce 73.8%, 1.84 pages/session) is inflated by owner/loop traffic; Direct is not a clean read until a post-11-11 window exists |
| **Sample size** | most per-page CTRs rest on < 20 clicks | one click moves a 500-impression page by 0.2 points; a difference under ~1 point on a small page is noise |

## 4. Decay and CTR outliers

### Decay (`gsc-trend-page.json`, W vs P, pages with ≥ 50 impressions in P and position worse by ≥ 0.8)

| page | impr. P → W | clicks P → W | position P → W | read |
|---|---|---|---|---|
| **/matching** | 317 → 100 | 0 → 2 | 4.2 → 8.1 | the one top-5 tool landing; lost ~3.9 positions and two thirds of impressions. `#696` changed its title on 2026-11-03 (inside W), so cause is **not determinable** — a window cannot split it. Already breaches #508's ±1.5 position guard (4.3 ± 1.5), so #508 can only score INCONCLUSIVE |
| /learn/ashwini-nakshatra/ | 99 → 93 | 1 → 1 | 5.7 → 7.7 | lost two positions, impressions held |
| /learn/the-9-grahas-overview/ | 99 → 31 | 0 → 0 | 8.0 → 9.2 | |
| /learn/ketu-in-vedic-astrology/ | 64 → 4 | 1 → 0 | 7.5 → 8.5 | near-gone |
| /festivals | 267 → 293 | 1 → 0 | 29.3 → 32.3 | page 3+; not a band page |

No decay on a page with ≥ 1,000 impressions beyond 0.5 of a position (debilitated-sun 6.1 → 6.6, sade-sati 6.2 → 6.6); `career-during-sade-sati` 7.3 → 5.4 is the largest gain. Gone pages with ≥ 30 prior impressions: `/learn/griha-pravesh-muhurat-2026-2027/` (40 impressions, 1 click in P; 0 in W). Cause not determined; the page is also seasonal (muhurat).

**Not filed as an issue:** /matching moved on 100 impressions in a window that holds its own title change. Filing "fix /matching" now would act on a signal the data cannot separate from the 11-03 change. The #508 score will carry it.

### CTR outliers (W, GSC page; comparison = median CTR 1.0% across the 16 pages with ≥ 300 impressions)

| page | impr. | CTR | pos | gap |
|---|---:|---:|---:|---|
| /learn/debilitated-sun-career/ | 2,515 | 0.56% | 6.6 | 1.0% of 2,515 ≈ 25 clicks vs 14 actual, ≈ 11 short; **#835 is the in-flight fix, deployed today** |
| /learn/sade-sati/ | 1,967 | 0.66% | 6.6 | ≈ 7 clicks at median; #685 in flight |
| /learn/jupiter-in-10th-house-career/ | 1,623 | 0.86% | 6.9 | ≈ 2 clicks at median; **already carried a #311 title rewrite** |
| /learn/manglik-dosh/ | 508 | 0.59% | 6.8 | small |
| /learn/shukra-venus-in-vedic-astrology/ | 310 | 0.65% | 5.7 | CTR low at position 5.7; no issue open that I read |
| /learn/mangal-mars-in-vedic-astrology/ | 407 | 0.74% | 7.3 | |
| High-side: /muhurat/griha-pravesh | 237 | 5.91% | 6.1 | 22 organic landing sessions, **bounce 9.1%, 2.32 pages/session** (GA4, W) — the best-converting organic landing on the site |
| High-side: /numerology | 109 | 5.50% | 5.6 | |

## 5. Traffic and funnel (W)

| channel (GA4) | sessions | bounce (session-weighted) | pages/session (session-weighted) |
|---|---:|---:|---:|
| Organic Search | 371 | 46.1% | 1.59 |
| Direct | 290 | 73.8% | 1.84 |
| AI Assistant | 10 | 30.0% | 4.40 |
| Unassigned | 5 | 80.0% | 0.40 |
| **total** | **676 (property total 677)** | | |

- GSC clicks in W: 296. GA4 Organic Search sessions: 371. The two are not the same measure; GA4 organic can include non-Google engines, and the gap is **not determined**.
- GA4 sessions by half of W (`ga4-daily.json`): 2026-10-14..10-27 = 279, 10-28..11-10 = 399. Single-day spikes with no stated cause: **2026-10-16 (42)** and **2026-11-06 (59 sessions, 53 new users)**; channel mix per day is not in the export, so what they were is **not determined**.

| landing (folded), W | sessions | bounce | pages/session | read |
|---|---:|---:|---:|---|
| / | 87 | 37.9% | 4.01 | 78 Direct; the deepest landing and the only one above 2 pages |
| /learn/rahu-mahadasha-ketu-antardasha | 67 | 44.8% | 1.30 | 53 organic; organic row 1.38 pages/session. #276's bar was ≥ 1.20 on this landing; **not a score** (deploy day inside W) |
| /learn/gochar-2026-planetary-transits | 28 | 67.9% | 1.11 | 16 organic |
| /learn/rahu-mahadasha-career-problems | 25 | 44.0% | 2.04 | 24 organic |
| /kundli | 24 | 66.7% | 1.62 | |
| /numerology | 23 | 78.3% | 1.00 | the tool landing with the worst step-through |
| /muhurat/griha-pravesh | 22 | 9.1% | 2.32 | all organic |
| /matching | 19 | 84.2% | 1.58 | |
| /learn/manglik-dosh (organic only) | 3 | 33.3% | 1.00 | #329 floor is 10; unreachable at this traffic |

Learn landings on organic carry 1.0–2.3 pages/session; the homepage carries 4.0. Whether the in-body tool links from #518 lifted that is a question for the 2026-12-07 window, not this one.

## 6. Events (`/tmp/ga4-events.json`, W; present this run)

| event | count | note |
|---|---:|---|
| page_view | 1,169 | |
| session_start / first_visit | 674 / 541 | |
| feature_view | 670 | |
| form_start | 140 | |
| ask_answered | 137 | |
| kundli_generated | 52 | 52 kundlis in W; `form_start` is not split by form, so a kundli-specific drop-off cannot be computed |
| **cta_click** | **10** | 8 `(not set)→(not set)`; 1 `/learn/kaal-sarp-dosh/ → /kaal-sarp-check`; 1 `/learn/name-numerology-explained/ → /numerology`. `split_available: true`; event exists from 2026-11-03 04:42Z, so W holds ~8 days of it and the count is **partial history**, not a 28-day figure |
| form_submit / subscribe_completed | 1 / 1 | |
| feedback_sent | 2 | |

- 10 `cta_click` events in ~8 days with 8 carrying no path: the **split is unreadable for 80% of them** (reason not determined from this export). It is a measurement, not zero, and it cannot score #570/#518 yet.
- `user_identified` 689 ≈ `session_start` 674 — likely a client-side event fired once per session; not interpreted.

## 7. #835's baseline, read from `gsc-trend-query.json` (W, pre-deploy; query view = 14% of impressions)

| set | queries | impressions | clicks |
|---|---:|---:|---:|
| any query matching `sun.*debilitat` or `debilitat.*sun` | 33 | 761 | 0 |
| of those, wording asking which sign / where / when | 16 | 557 | 0 |

Top single query: "sun debilitated in which sign" 231 impressions, position 8.3, 0 clicks (new this window; 0 in P). That is the 2026-10-14 → 11-10 pre-deploy baseline for #835; its clean window opens 2026-11-13.

## 8. Issues filed

**None.** Reason, per finding:

| finding | why not filed |
|---|---|
| /matching decay 4.2 → 8.1 | cause confounded with #696's title change in the same window; the #508 score will read it |
| low-CTR band pages (debilitated-sun, sade-sati) | #835 and #685 already own them and are unscored; #311's miss argues against a third title-only issue |
| /learn/shukra-venus-in-vedic-astrology/ at 0.65% on 310 impressions, pos 5.7 | single window, small sample, one page; not enough to act on |
| GA4 Direct inflated by internal traffic | #735 shipped 2026-11-11; its fix is not yet inside any window |

## 9. What I could not determine, and the one measurement that would settle each

| unknown | measurement |
|---|---|
| why impressions doubled around 2026-10-23..25 | a per-page daily GSC series (`dimension: date,page`) would show which pages stepped up and when; the current export is site-level per day |
| whether /matching's drop came from the 11-03 title change | the same per-page daily series, split at 2026-11-03 |
| what the 2026-11-06 GA4 spike (59 sessions) was | GA4 daily × channel × landing for that date |
| whether `cta_click`'s 8 `(not set)` rows are a tagging gap | `eventName=cta_click` split by the event's `link_text`/`from_path` raw parameter over a post-11-03 window |
| GA4 period-on-period change | a GA4 previous-window export (the fetch writes only W) |
| whether any band-page gain is attributable to the title vs the #518 link vs the step-change | not separable in a 28-day window; needs per-page daily data and non-overlapping ship dates |
| GSC clicks (296) vs GA4 organic sessions (371) | GA4 organic session `sessionSource` split (Google vs other engines) |
