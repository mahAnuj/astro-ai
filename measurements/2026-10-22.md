# Analyst report — 2026-10-22

**Window W = 2026-09-22 → 2026-10-19** (28 days; the last 3 days are excluded by the exports). Previous window W′ = 2026-08-25 → 2026-09-21.
Every figure below was read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, and from the sibling exports fetched in the same run (`gsc-trend-page.json`, `gsc-trend-query.json`, `gsc-daily.json`, `ga4-daily.json`, all written 23:51Z). I did not re-call any API.
Figures marked *(issue body)* are quoted from an issue body, not fetched this run. Figures marked *(arith)* are my arithmetic on this run's figures.

## 0. Coverage — read before any number

| Export | Dimension | Window | Coverage | Truncated |
|---|---|---|---|---|
| `gsc-band.json` | page, position 6–20 only | W | whole fetch 100% of 11,615 impressions; **emitted** 109 rows = 10,273 impressions = **88%** | no |
| `gsc-all.json` | page | W | 100% of 11,615 impressions (127 rows) | no |
| `gsc-trend-query.json` | **query** | W vs W′ | **8%** of 11,615 impressions — a partial view, Google withholds the rest | n/a |
| `gsc-trend-page.json` | page | W vs W′ | 100% for W; W′ coverage not stated in the file | n/a |
| `ga4.json` | landing × channel | W | 101% of 348 sessions (350 in rows) | no |
| `ga4-daily.json`, `gsc-daily.json` | **site-level** by day | W | 28 of 28 days with traffic; GSC 100% | no |

**There is no per-page × per-day series in any export.** It is why §2 cannot split a page's window at its deploy date (filed as an issue, §6).

Everything under "band" is **pages, not queries**: a page's `position` is its average across its queries.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression queries."*

| Measure (window W) | Value |
|---|---|
| Property impressions / clicks / CTR | 11,615 / 117 / 1.01% *(arith)* |
| Pages with average position 6–20 | **109**, 10,273 impressions (88% of property), 110 clicks, CTR 1.07% *(arith)* |
| Top 10 band pages by `band_opportunity` | 7,279 impressions, 68 clicks, CTR 0.93% *(arith)* |
| Pages at position ≤5 with ≥50 impressions | **1**: `/matching`, 330 impressions, 0 clicks, position 4.3 (14.7 in W′, on 9 impressions — a new, volatile reading, not a trend) |
| Impressions W vs W′ (page rows) | 11,652 vs 5,909 (about 2×); clicks 117 vs 59 |

**Verdict on the objective: not met, and not yet measurable as worded.** No ranking band page has crossed into the top 5. The two nearest (`debilitated-sun-career` 6.1, `sade-sati` 6.2) are about one place from the line. The objective is stated on *queries*; the query view covers 8% of impressions (974 of 11,615). The "ten highest-impression queries" are therefore the ten highest *visible* ones, and 8 of those 10 are variants of one Rahu–Ketu phrase. Page-level is the honest unit.

### Band list — top 15 by opportunity (pages; window W; export `gsc-band.json`, emitted coverage 88%)

| # | Page | Impr. | Clicks | CTR | Avg pos | Opportunity |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,996 | 28 | 1.40% | 7.5 | 91.8 |
| 2 | /learn/debilitated-sun-career/ | 1,210 | 7 | 0.58% | 6.1 | 65.6 |
| 3 | /learn/sade-sati/ | 1,065 | 9 | 0.85% | 6.2 | 54.9 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 832 | 8 | 0.96% | 7.0 | 41.9 |
| 5 | /learn/manglik-dosh/ | 469 | 2 | 0.43% | 7.5 | 26.1 |
| 6 | /learn/panch-mahapurush-yoga/ | 441 | 2 | 0.45% | 6.9 | 24.5 |
| 7 | /learn/jupiter-in-10th-house-career/ | 369 | 1 | 0.27% | 6.8 | 21.1 |
| 8 | /learn/career-during-sade-sati/ | 393 | 5 | 1.27% | 7.0 | 18.6 |
| 9 | /learn/marriage-mahadasha-timing/ | 245 | 1 | 0.41% | 6.5 | 13.7 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 259 | 5 | 1.93% | 7.9 | 10.5 |
| 11 | /learn/ | 141 | 0 | 0% | 10.8 | 8.5 |
| 12 | /learn/10th-lord-in-6th-house-career/ | 182 | 3 | 1.65% | 7.0 | 7.9 |
| 13 | /learn/kundali-matching-ashtakoot-guna-milan/ | 122 | 0 | 0% | 7.9 | 7.3 |
| 14 | /learn/sun-in-10th-house-career/ | 116 | 0 | 0% | 7.1 | 7.0 |
| 15 | /learn/mars-remedies/ | 124 | 1 | 0.81% | 6.6 | 6.4 |

Rows 1–4 hold 5,103 impressions *(arith)*, which is 49.7% of the band's 10,273. Nothing past row 10 carries more than 182 impressions.

### CTR outliers (window W; compared with the band aggregate 1.07%, because the band *median* is 0% and tells you nothing)

| Page | Impr. | Clicks | CTR | Pos | Read |
|---|--:|--:|--:|--:|---|
| /matching | 330 | 0 | 0% | 4.3 | Best position on the site, zero clicks. At the band rate you would expect ~3.5 clicks, P(0) ≈ 3% *(arith)*. Position is new (14.7 in W′), so this may be a transient SERP test. **Watch, not an action.** GA4 shows 7 `/matching` landing sessions, 0 organic. |
| /learn/debilitated-sun-career/ | 1,210 | 7 | 0.58% | 6.1 | In #311's set. Page-1 edge, lowest CTR of the big four. |
| /learn/sade-sati/ | 1,065 | 9 | 0.85% | 6.2 | **Not in any open or closed title test.** Sibling `kaal-sarp-dosh` at 6.1 gets 2.38%, but on 126 impressions. |
| /learn/panch-mahapurush-yoga/ | 441 | 2 | 0.45% | 6.9 | Not in any title test. |
| /learn/marriage-mahadasha-timing/ | 245 | 1 | 0.41% | 6.5 | Not in any title test. |

Sample caveat: every one of these is ≤9 clicks. A one-click swing moves sade-sati by 0.09 points. These are candidates, not proven defects.

### Decay (W vs W′, pages with ≥50 impressions in W)

| Page | Impr. W | Impr. W′ | Pos W | Pos W′ | Read |
|---|--:|--:|--:|--:|---|
| / | 103 | 46 | 6.0 | 3.7 | 2.3 places worse; 5 clicks vs 3. Small base. |
| /rashifal | 89 | 32 | 10.3 | 6.6 | 3.7 places worse. Small base. |
| /festivals | 245 | 1,258 | 29.5 | 57.9 | Impressions −80.5% while position *improved*; both positions are far off page 1. Query-level cause not visible (8% view). Diwali is 2026-11-08, so seasonality is the first suspect — unconfirmed. |
| /learn/shukra-venus-in-vedic-astrology/ | 48 | 257 | 5.8 | 5.9 | Impressions −81% at an unchanged position: a demand drop, not a ranking loss. |
| /learn/mangal-mars-in-vedic-astrology/ | 121 | 251 | 7.8 | 7.0 | −52% impressions, 0.8 places worse. |

No page that earned clicks in W′ has lost ground at scale. The site roughly doubled in impressions.

### Traffic (GA4, window W, landings folded for query string and trailing slash: 68 distinct paths, 72 raw)

| Channel | Sessions | Share |
|---|--:|--:|
| Organic Search | 165 | 47% of the 350 session-rows |
| Direct | 154 | 44% |
| AI Assistant | 24 | 7% |
| Unassigned | 7 | 2% |

Total 348 sessions. Daily sessions ranged 5–42; the 42 on 2026-10-16 is about 2.5× the 17 sessions on each adjacent day and **cannot be assigned to a channel** (the daily export is site-level). Not attributed to any ship.
`/` takes 91 sessions (mostly Direct, 3.77 pages/session on its Direct row), and the best organic landing is the Rahu–Ketu article with 28.

## 2. Scores — issues closed in the last 28 days with a `thesis:` and a `metric:`

**25 of the 52 issues closed since 2026-09-24 carry both fields.** Four of them have a metric this data can read. None of the four is scoreable yet. **Not one traffic-thesis ship has a verdict.** That is the finding.

| Issue | Shipped (merge, UTC) | Predicted | Actual in W (post-deploy share) | Verdict |
|---|---|---|---|---|
| **#276** /dasha CTA on Rahu–Ketu article | PR #342, 2026-10-14 02:02 (live; the CTA is in the page today) | organic pages/session ≥ 1.20 over the next 28 days; inconclusive if < 20 sessions | 28 organic sessions, **1.04** pages/session *(post-deploy: ≤ 6 of 28 days)* | **INCONCLUSIVE — window not elapsed. No lift visible.** Rescore ≥ 2026-11-14 |
| **#311** title/meta on 4 band pages | PR #334, 2026-10-13 17:29 (live; the manglik title is the new one) | combined CTR ≥ 1.2% on ≥ 2,000 impressions, position within ±1 | 18 clicks / 2,880 impressions = **0.63%** *(arith)* *(≤ 6 of 28 days)*. W′: 10 / 1,211 = 0.83%. Baseline *(issue body)*: 0.71% | **INCONCLUSIVE — window not elapsed. No lift visible. Neither pass nor miss yet.** Rescore ≥ 2026-11-13 |
| **#329** manglik-check link | PR #344, 2026-10-14 16:07 (live; 4 `manglik-check` hits in the page) | organic pages/session ≥ 1.30 on ≥ 10 sessions; < 10 = inconclusive | **3 organic sessions**, 1.00 pages/session | **INCONCLUSIVE — below the issue's own sample floor.** See the structural note below |
| **#272** channel + page dimensions in the exports | PR #292, 2026-10-08 | organic sessions reported as a separate number; ranking URL beside each top-10 band query | `ga4.json` carries the channel (Organic Search = 165 of the 350 session-rows); `gsc-band.json` carries `page` | **PASS on shape. Query-level half not met** (query view = 8% coverage) |

### Why #276, #311 and #329 cannot be split, with the arithmetic

- **No per-page daily data.** The post-deploy days cannot be separated from the pre-deploy ones. At most 6 of the 28 days in W carry any of the three changes.
- **#276** *(arith)*: 28 sessions × 1.04 = 29.1 page-views, so **at most one onward page-view across all 28 days**. The `≥ 1.20` pass line needs ≥ 6 extra. W cannot show a pass. W also cannot show a *fail*: the CTA was live for a fifth of it.
- **#311** *(arith)*: two-thirds-plus of W's impressions were served under the old titles, so 0.63% is mostly the old-title rate. A 22-day pre / 6-day post mix could still hold a post rate above 1.2%. It does not show one, and it does not rule one out.
- **#329 is structurally unlikely to ever resolve.** The page earned 2 clicks from 469 impressions in W. The issue's own floor is 10 organic sessions in 28 days. At the current rate that is ~3.3× the traffic *(arith: 10 ÷ 3)*. The metric will read INCONCLUSIVE at the end of its window unless #311's title lift lands first. This is a design fault in the metric, not a verdict on the link.

### Tree-state metrics that this run could check (repo at `815091f`; these are shape checks, not outcomes)

| Issue | Metric clause checked | Before → now | Verdict |
|---|---|---|---|
| #397 Nadi claim | `grep -rn "Nadi has no cancelling" src/astro_ai/ \| wc -l` | 3 → **0** | PASS on the count. The `/ask` consistency clause was **not** checked. |
| #396 cache hits measured | `grep -rn "cached_tokens\|prompt_tokens_details" src/ \| wc -l` | 0 → **34** | PASS on the first clause. The `/admin/usage` ratio was **not** checked. |
| #373 feedback escaping | `grep -cniE 'html.escape\|escape\(\|…' routes/feedback.py` | 0 → **5** | PARTIAL: an escape is present. "Enforced by a test" was **not** checked. |

### Closed with `thesis:`/`metric:` and **not scored** (metric is repo or infra state, a run history, or a window not elapsed; I had no data for it)

#449, #446, #442, #409, #408, #405, #400, #374, #372, #369, #355, #349, #345, #338, #320, #316, #313, #286. These are not "passes".

## 3. Confounds — named before any delta

| Confound | Finding |
|---|---|
| **Concurrent ships** | Four PRs that touch `src/` merged inside W's post-deploy tail alongside the three above: #312 (sticky CTA lifted, 10-09), #319 (shloka serif, 7 learn templates, 10-10), #364 (12px floor on learn cards, 10-15), #352 (/about reword, 10-15). #276, #311 and #329 landed within 16 hours of each other on three different pages. A shared lift across the three would not be attributable to any one. **Limitation:** the checkout is shallow (1 commit), so `git log origin/main --since` is empty; the list above is from `gh pr list`, which misses any direct push. |
| **After W (not in it)** | #427 service-worker fix (10-20), #451 remedy-claim retirement (10-21, 28 src files), #412 Nadi (10-20), #480 (10-22). They cannot have affected W, but they will sit inside the next window and the rescore. |
| **Page reachable?** | Probed 2026-10-22 (not during W): `/health` 200, revision `bhagya-00493-9zh`, `build_sha` `380769fd…`; the Rahu–Ketu and manglik pages 200. The `/dasha` CTA and `manglik-check` link are in the served HTML; the manglik `<title>` is the #311 rewrite. **I cannot say the pages were healthy on each day of W.** |
| **#253 stale stylesheet** | Fixed 2026-10-20, so it was live for all of W. It affects returning visitors with an installed service worker. Organic first-time landers are the bulk of the pages above, so I rate the effect on these three as low, **but unmeasured**. |
| **#266 /kundli 413** | Closed 10-21 as "does not reproduce". Whether `/kundli` generated charts on each day of W is unknown. `/kundli` shows 17 sessions, 11 organic, 1.91 pages/session — it is **not** a signal that the form worked. |
| **Seasonality** | Diwali is 2026-11-08, so festival and muhurat demand will climb through the next window. The 2× impression rise W′→W is concentrated on `/learn` dasha and dosha pages (the largest risers), and its cause is **not determined**. A lift in the rescore window must be set against it. |
| **Sample size** | 117 clicks, 348 sessions in 28 days. Most per-page figures above are < 10 events. |

## 4. What I could not determine, and the one measurement that settles it

| Unknown | Settled by |
|---|---|
| Whether #276 / #311 / #329 moved anything | A per-page × per-day export for the 4 + 2 pages, or the plain wait to the rescore dates: #311 ≥ 2026-11-13, #276 ≥ 2026-11-14, #329 ≥ 2026-11-14 |
| Whether any session reached `/dasha` or `/manglik-check` from the CTA | A GA4 click event or a page-path-sequence dimension. The export has neither; pages/session is a proxy |
| Whether the new titles have been recrawled into the SERP | `site:`/URL-inspection of the four #311 pages — not available to me |
| Why impressions doubled W′→W | The query view is 8%; the other 92% is withheld |
| Channel of the 2026-10-16 spike (42 sessions) | GA4 daily × channel |
| Whether `/matching` position 4.3 / 0 clicks is real | One more window |
| Metrics for the 18 unscored issues | Outside GA4/GSC |

## 5. Findings I am deliberately not filing

| Finding | Why not |
|---|---|
| A second round of title rewrites for sade-sati, panch-mahapurush-yoga, marriage-mahadasha-timing | #311's thesis (title rewrites lift CTR) has no verdict. Filing the same bet on three more pages before the first resolves stacks an untested idea and adds a concurrent change to a window I am trying to read. Revisit at the #311 rescore. |
| `/matching` zero clicks at position 4.3 | One window, a position that moved 10 places, 3% chance under the band rate. |
| `/festivals` −80% impressions | No query-level view, plausible seasonality, position off page 1. |

## 6. Issue filed

| Issue | Why |
|---|---|
| [#490](https://github.com/mahAnuj/astro-ai/issues/490) — no per-page × per-day export, so no page-level ship can be scored before its 28-day window ends | Evidence Block attached. It is the reason #276, #311 and #329 have each been posted "unscored" for about a week. |

## 7. Score comments posted this run

| Issue | Verdict posted |
|---|---|
| #276 | INCONCLUSIVE — rescore ≥ 2026-11-14 |
| #311 | INCONCLUSIVE — rescore ≥ 2026-11-13 |
| #329 | INCONCLUSIVE — below its own sample floor; metric structurally unlikely to resolve |
| #272 | PASS on shape; query-level half not met |
| #397 | PASS on the countable clause; behaviour clause not checked |
| #396 | PASS on the first clause only |
| #373 | PARTIAL |
