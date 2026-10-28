# Analyst report — 2026-10-28

**Window for every number unless stated: W = 2026-09-28 → 2026-10-25** (28 days, last 3 days excluded).
Prior window P = 2026-08-31 → 2026-09-27 (from `/tmp/gsc-trend-page.json`).
All figures were read from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus the sibling exports `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json`, `/tmp/gsc-daily.json` and `/tmp/ga4-daily.json` in the same directory (fetched before this run; no API was called). Where a number comes from an issue body or an earlier comment, it is labelled "quoted".

## Coverage (read before any number)

| Export | Dimension | Window | Coverage | Truncated |
|---|---|---|---|---|
| `gsc-band.json` | page | W | 100% of 12,769 impressions fetched; band printed 106 rows = 91% (11,577 impr.) | no |
| `gsc-all.json` | page | W | 100% (128 rows, 12,802 row-impressions) | no |
| `gsc-trend-query.json` | **query** | W vs P | **10%** of 12,769 impressions — partial view | — |
| `ga4.json` | landing × channel | W | 100% of 405 sessions (111 rows, 75 landings = 69 distinct paths after folding query strings and trailing slashes) | no |

The objective names the ten highest-impression **queries**. The exports are by page and query coverage is 10%, so the objective is **not directly measurable** as written; everything below is page level.

## 1. The 6–20 band against OBJECTIVE.md (W)

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

| Metric (W) | Value |
|---|---|
| Pages at average position 6–20 | 106 pages, 11,577 impressions (91% of all), 122 clicks (95% of 129 total) |
| …of which position 6–8 | 62 pages, 10,749 impressions, 117 clicks |
| …position 8–11 / 11–15 / 15–20 | 36 pages 802 impr. / 6 pages 22 impr. / 2 pages 4 impr. |
| Pages already at position < 6 | 16 pages, 908 impressions, 7 clicks |
| Site total | 12,769 impressions, 129 clicks (CTR 1.01%) |
| Site total, P | 7,205 impressions, 74 clicks (from the trend file's page rows) |
| Band pages ≥ 100 impressions | 21 pages; impressions-weighted CTR 0.97%; 0.89% excluding the reference page |

Band count in P: 103 pages at position 6–20 (5,799 impressions, by `position_prev`). The band got bigger (impressions ×2.0), not smaller: impressions are arriving at positions 6–8 and are not crossing into the top 5. **Pages entering the top 5 this window that were in the band in P: not determined** (needs a per-page join I did not run; the only top-5 pages ≥ 100 impressions are `/matching` 4.4 and `/learn/planets-in-7th-house-marriage/` 5.8, both already there or near in P: 5.4 and 6.9).

Top of the band by `impressions × achievable CTR gain` (`band_opportunity`, W):

| # | Page | Impr. | Clicks | CTR | Position (P) | Opportunity |
|---|---|--:|--:|--:|---|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,358 | 29 | 1.23% | 7.1 (7.5) | 112.5 |
| 2 | /learn/debilitated-sun-career/ | 1,504 | 7 | 0.47% | 6.3 (6.4) | 83.2 |
| 3 | /learn/sade-sati/ | 1,376 | 8 | 0.58% | 6.4 (7.1) | 74.6 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 779 | 10 | 1.28% | 6.8 (8.5) | 36.7 |
| 5 | /learn/panch-mahapurush-yoga/ | 507 | 3 | 0.59% | 6.9 (7.3) | 27.4 |
| 6 | /learn/manglik-dosh/ | 476 | 3 | 0.63% | 7.3 (10.2) | 25.6 |
| 7 | /learn/career-during-sade-sati/ | 456 | 5 | 1.10% | 6.7 (8.0) | 22.4 |
| 8 | /learn/jupiter-in-10th-house-career/ | 362 | 1 | 0.28% | 7.0 (6.7) | 20.7 |
| 9 | /learn/marriage-mahadasha-timing/ | 257 | 1 | 0.39% | 6.6 | 14.4 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 307 | 6 | 1.95% | 7.6 | 12.4 |

The top three pages carry 45% of band impressions.

Top queries (query dimension, **10% coverage — not the whole band**), W: "rahu mahadasha ketu antardasha" 279 impr., position 9.4 (P 9.3); "rahu ketu antardasha" 59, 9.4 (P 5.5); "sun debilitated in which sign" 44, 7.7 (new); "bhagya kundali astrology" 22, 6.4. The leading query's position did not move (9.3 → 9.4) while its impressions rose 88 → 279.

## 2. Post-ship scores (issues closed 2026-09-30 → 2026-10-27 carrying `thesis:` and `metric:`)

Twenty-eight closed issues carry both fields. Five have a metric GA4 or GSC can read. The rest are measured on the tree, CI or ops data and are listed in §2b as **not scored**.

### 2a. Traffic-facing ships — comments posted this run

| Issue | Shipped | Predicted | Actual (W) | Verdict | Comment |
|---|---|---|---|---|---|
| **#311** title/meta on 4 band pages | 2026-10-13 17:29Z (PR #334); 12 of 28 days post-deploy | combined CTR ≥ 1.5% (refreshed block ≥ 1.2%) on ≥ 1,500 impr., position within ±1 | **0.673%** (21 / 3,121), position 6.66; P: 0.610% (10 / 1,639), position 7.98 | **INCONCLUSIVE, leaning MISS** | posted |
| **#276** /dasha CTA on Rahu–Ketu article | 2026-10-14 02:02Z (PR #342); 12 of 28 days | organic pages/session ≥ 1.20 (< 20 sessions = inconclusive) | **1.16** on 32 organic sessions, bounce 31.3% | **INCONCLUSIVE, not a hit** (~1 page-view short) | posted |
| **#329** Manglik checker link | 2026-10-14 16:07Z (PR #344); 11 of 28 days | pages/session ≥ 1.30 on ≥ 10 organic sessions | **1.00 on 3** organic sessions | **INCONCLUSIVE** — below the sample floor | posted |
| **#515** nightly rashifal generation | 2026-10-24 (PR #516); ≤ 2 days | organic sessions to `/rashifal/*` improve; email re-open rate | **0** organic sessions; 5 `/rashifal*` landings (Direct 4, AI Assistant 1); re-open rate not in either export | **NOT SCOREABLE** — re-score on/after 2026-11-24 | posted |
| **#272** export dimensions | 2026-10-08 | organic sessions as a separate number; ranking URL beside band entries | Organic Search = 185 of 405 sessions; GSC `dimension: page` populated | **PASS on shape** (already scored 2026-10-09 and 2026-10-21; no new comment) | not re-posted |

**The misses and near-misses, plainly:**

- **#311 is on track to miss.** Combined CTR is 0.673% against a 1.2–1.5% bar. If the post-deploy CTR had been 1.2%, W would blend to about 0.86% using P's 0.61% as the pre rate (0.92% with the issue's quoted 0.71%). Solving for the post-deploy share gives about 0.76% (0.62% against the issue's baseline). Assumes equal impressions per day; the last 14 days carry 55% of W's impressions, which would pull the implied post-deploy rate lower, not higher. Not final: the metric window ends 2026-11-10, rescore on/after 2026-11-13.
- **The one page that rose, rose with its rank.** `career-problems` went 2 → 10 clicks and 0.29% → 1.28%, but its average position moved 8.5 → 6.8 in the same window. That page supplies 10 of the 21 clicks; the metric's own "unchanged position" premise fails for it (weighted position moved 1.3 places against P). Its CTR gain cannot be credited to the title.
- **#276 did not reach its bar and cannot be said to have caused anything.** 1.16 against 1.20 is five extra page-views against six needed. This page is also the one the site's demand is moving on (impressions 757 → 2,358 at flat position), so its session volume moves with or without the CTA.
- **#329 cannot be scored as written.** 3 organic sessions against a floor of 10, and 0 of 9 all-channel sessions went past the landing. Not evidence the link fails; not evidence of anything. The metric is unresolvable at this traffic.
- A **fourth** reading is missing for all of these: nothing records a click on the CTA. Filed as #570.

### 2b. Closed with `thesis:`/`metric:`, not scorable from GA4 or GSC (not scored — I did not measure these)

Metrics are tree, CI, workflow or ops measures, outside the exports I was given: #286, #313, #316, #320, #338, #345, #349, #355, #362, #369, #372, #373, #374, #396, #397, #400, #405, #408, #409, #442, #449, #493, #495. Their numbers were not read this run, so no verdict is given and no comment was posted. #345 and #349 describe `/admin/ops` movement panels; whether those render correctly is a separate check, not a traffic measure.

## 3. Confounds (named before any delta)

| Confound | Detail (W unless stated) | Effect |
|---|---|---|
| Concurrent ships on the scored pages | 29 merged PRs since 2026-10-13 touched `src/` (listed from `gh pr list`, not all are `/learn`). On `/learn` pages: #451 (10-21, 28 files), #480 (10-22), #487 (10-23), #501 (10-23), #512 (10-24), #521 (10-25; its file list includes two of #311's pages, debilitated-sun and jupiter-in-10th), #530 (10-26). Content and CTA links, not titles | #311's pages were edited after the deploy (#521 touches two of them per its file list; the earlier 10-27 score comment, quoted, says remedy-text edits reached all four 10-21..10-23); #329's template also took remedy text. Attribution to one ship is not possible for CTR or pages/session |
| #311 × #329 on one URL | `/learn/manglik-dosh/` took the title rewrite 10-13 and the checker link 10-14 | Not separable |
| Position moved under the test | #311 pages weighted position 7.98 → 6.66; `career-problems` 8.5 → 6.8; `manglik-dosh` 10.2 → 7.3 | CTR change is partly a ranking effect |
| Demand / seasonality | Site impressions 5,752 (09-28..10-11) → 7,017 (10-12..10-25). Daily impressions ran ~380–520 then **640, 757, 927 on 10-23, 10-24, 10-25**; clicks 7, 7, 9. Diwali 2026-11-08 (CLAUDE.md) is 14 days after W ends, so festival-adjacent demand is plausible; which pages carried the jump is **not in the data** | Absolute impressions and clicks are not comparable with P |
| Post-deploy share of W | 12 of 28 days (43%) for #311 and #276, 11 for #329. No per-page daily series exists (#490) | Every §2 figure blends pre and post days |
| Page reachable | 2026-10-28: `/health` ok (revision `bhagya-00518-8zz`, build_sha `fcd2e09…`); `/learn/rahu-mahadasha-ketu-antardasha/` 200 in 0.58s, `/learn/manglik-dosh/` 200 in 0.70s, `/learn/sade-sati/` 200 in 0.60s, `/kundli` 200 in 0.58s, `/rashifal/aries` 200 in **6.58s** (n = 1, likely an uncached reading, not a rate) | The pages are not broken now; whether #253 (stale stylesheet) or #266 (Groq 413) affected W was not re-measured, both are closed (10-20, 10-21) |
| Sample size | 129 clicks site-wide in W; #311 rests on 21 clicks; #329 on 3 organic sessions; #276 on 32 | Most deltas here are noise at this size |
| Hindi surface | `/hi/*` URLs appear in GSC (e.g. `/hi/rashifal` 4 impr.) | negligible volume in W |

## 4. Decay, outliers and funnel (W vs P)

| Finding | Evidence | Read |
|---|---|---|
| **/festivals impressions −70%** | 807 → 240 impr., position 42.8 → 25.8, clicks 1 → 0 | Fewer impressions while rank improved; on a page whose demand should rise toward Diwali. Cause not determined (query dimension is 10% coverage). Not filed: 0 clicks either side |
| **/rashifal position decay** | 7.2 → 10.1; impressions 36 → 128; 0 clicks | Tiny volume; #515 and #524 reshaped the page in this window |
| **Matching ashtakoot article** | /learn/kundali-matching-ashtakoot-guna-milan/: 17 → 173 impr., position 6.5 → 8.0, 0 clicks | New impressions, no clicks; edited by #480 and #501. Watch, not an action |
| **Shukra article** | /learn/shukra-venus-in-vedic-astrology/ 212 → 53 impr., 2 → 0 clicks | One-off; cause not determined |
| **CTR outliers (band median, pages ≥ 100 impr. = 0.97% weighted)** | Below: debilitated-sun 0.47% (1,504 impr.), sade-sati 0.58% (1,376), panch-mahapurush 0.59% (507), jupiter-in-10th 0.28% (362), marriage-mahadasha 0.39% (257), kundali-matching 0% (173), /learn/ 0% (147), /rashifal 0% (128), chronic-health 0% (119). Above: 7th-lord 1.95%, mangal-mars 2.48%, kaal-sarp 2.21% | `debilitated-sun-career` and `sade-sati` are the two largest below-median pages: 2,880 impr., 15 clicks. At the band's own 0.89% ex-reference rate they would take ~26 |
| **Homepage and /matching** | `/` at position 6.0, 120 impr., 8 clicks (6.7% CTR); `/matching` 348 impr., 1 click, position 4.4 | `/matching` is already tracked by #508 |
| **Funnel: top landings (GA4, W, folded)** | `/` 90 sessions, pages/session 3.68, bounce 31.1%; Rahu–Ketu article 42 sessions, 1.12, bounce 45.2%; `/kundli` 22 sessions, 1.45, bounce 77.3%; `/matching` 13 sessions, 2.23, bounce 69.2% | Learn landings stay at ~1.0–1.3 pages/session; the homepage is the only landing that carries visitors onward. Organic Search = 185 of 405 sessions (46%) |

## 5. Issues filed this run

| # | Title | Why it needed action |
|---|---|---|
| #570 | [MEASURE] No event records a click on an in-article tool link, so #276, #329 and #521 can only be scored through pages/session | `static/analytics.js` has no link-click event; four ships' thesis is "the reader follows the link" and the only proxy cannot resolve at this traffic. Evidence Block included |

Not filed, because already open: per-page × per-day export (#490), `/matching` title test (#508), learn dead-end articles (#518), the 6–20 band itself (#267), mislabelled workflow prompts (#291).

## 6. What I could not determine

| Question | Why not | Measurement that settles it |
|---|---|---|
| Whether #311's titles changed CTR | W is 57% pre-deploy; position moved; no per-page daily series | A page × date export for the four pages (#490). Rescore on/after 2026-11-13 |
| Whether anyone clicks the #276/#329/#521 links | No click event exists | `cta_click` event (#570) |
| Whether the band is moving toward the top 5 on the ten highest-impression **queries** | Query dimension covers 10% of impressions; the band is measured per page | Not recoverable (Google withholds the rest). Define the objective at page level, or accept the 10% |
| What caused the 10-23..10-25 impressions jump (640/757/927/day vs ~420) | No page × date series | #490 again |
| Email re-open rate for #515 | Not in GA4 or GSC | The email provider's reports; outside what I was given |
| Pre-deploy-only vs post-deploy-only CTR/pages-per-session | Exports are 28-day aggregates | #490 |
| Seasonality | Only two windows of data; the festival calendar suggests Diwali (2026-11-08) will lift festival and muhurat pages but I did not quantify it | A third window, or last year's series (site is too young) |

*analyst, read-only. No code, template, content or `BACKLOG.md` edited. Comments posted on #311, #276, #329, #515; issue #570 filed.*
