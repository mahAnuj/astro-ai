# Analyst report — 2026-10-25

**Window for every number unless stated: 2026-09-25 → 2026-10-22** (28 days, last 3 days excluded; GSC/GA4 lag).
**Previous window (GSC trend only): 2026-08-28 → 2026-09-24.**
Sources, all read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json`, `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json` (all already fetched; no API called).

## 0. Coverage — read before any figure

| Export | Dimension | Window | Coverage | Truncated |
|---|---|---|---|---|
| gsc-all.json | page | 2026-09-25 → 10-22 | 100% of 11,895 impressions (rows sum to 11,934) | no |
| gsc-band.json | page, position 6–20 | same | whole fetch 100%; **emitted 111 rows = 10,612 impressions = 89%** | no |
| gsc-trend-query.json | query | same | **8%** of 11,895 (983 impressions) — partial view, 91% unrecoverable | no |
| ga4.json | landing × channel | same | 100% of 364 sessions (rows sum to 365); 107 rows, 71 landings (67 after folding query strings/trailing slashes) | no |

## 1. The band against OBJECTIVE.md (window 2026-09-25 → 10-22)

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**The objective as written cannot be measured.** It names *queries*; the only query view covers 8% of impressions (983 of 11,895), and 8 of the 10 largest query rows are variants of one query ("rahu mahadasha ketu antardasha"). This is the same conclusion as the #272 re-scores. The measurement below is **per page** (page's average position across its queries).

| Measure | Value | Window |
|---|---|---|
| Site impressions / clicks / CTR | 11,895 / 121 / 1.02% | 09-25 → 10-22 |
| Site impressions / clicks, previous window (sum of trend rows) | 6,428 / 63 | 08-28 → 09-24 |
| Pages at position 6–20 | 111 pages, 10,612 impressions (89% of site), 113 clicks, CTR 1.06% | 09-25 → 10-22 |
| Median CTR, band pages with ≥100 impressions (n=24) | 0.81% | 09-25 → 10-22 |
| Pages at position ≤5 with ≥100 impressions | **1**: `/matching` — 341 impressions, **0 clicks**, pos 4.4 | 09-25 → 10-22 |
| Pages at position >20 with ≥100 impressions | 1: `/festivals` — 243 impressions, pos 26.4 | 09-25 → 10-22 |

Top of the band, ranked by `band_opportunity` (impressions × CTR gap; pos = page-average):

| # | Page | Impr | Clicks | CTR | Pos | Impr prev window | Pos prev |
|---|---|--:|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,055 | 26 | 1.27% | 7.4 | 555 | 7.7 |
| 2 | /learn/debilitated-sun-career/ | 1,246 | 7 | 0.56% | 6.1 | 346 | 6.7 |
| 3 | /learn/sade-sati/ | 1,123 | 9 | 0.80% | 6.2 | 254 | 11.4 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 796 | 9 | 1.13% | 6.9 | 656 | 8.6 |
| 5 | /learn/manglik-dosh/ | 480 | 2 | 0.42% | 7.4 | 210 | 13.3 |
| 6 | /learn/panch-mahapurush-yoga/ | 489 | 3 | 0.61% | 7.0 | 109 | 7.5 |
| 7 | /learn/jupiter-in-10th-house-career/ | 374 | 1 | 0.27% | 6.9 | 186 | 6.7 |
| 8 | /learn/career-during-sade-sati/ | 387 | 4 | 1.03% | 7.0 | 192 | 8.6 |
| 9 | /learn/marriage-mahadasha-timing/ | 245 | 1 | 0.41% | 6.5 | n/r | n/r |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 288 | 6 | 2.08% | 7.7 | n/r | n/r |

(n/r = not in the top rows I read for the previous window.)

**What the band shows:** site impressions are up ~85% on the previous window (11,895 vs 6,428 summed trend rows) but clicks went 63 → 121 and the band's CTR is ~1%. **Nothing has crossed into the top 5 on a page with meaningful volume.** The band is filling with impressions faster than it converts them; the lever is CTR at position 6–8, not rank. Only one page is at ≤5 (`/matching`, zero clicks).

## 2. Post-ship scores (issues closed in the last 28 days with `thesis:` + `metric:`)

25 closed issues since 2026-09-27 carry both lines. **5 have a metric GA4/GSC can read**; the rest are code/ops metrics I cannot read from these files and are listed under §2b. Comments posted on the five issues (see §6).

| Issue | Deploy (PR) | Predicted | Actual (this run's window) | Verdict |
|---|---|---|---|---|
| **#311** title/meta on 4 pages | 2026-10-13 17:29Z (#334) | Combined CTR ≥1.5% on ≥1,500 impr, position within ±1, over 28d after deploy | 4 pages: **2,896 impr, 19 clicks, 0.66% CTR**; avg positions 6.9 / 6.1 / 7.4 / 6.9. Previous window: 1,398 impr, 10 clicks, 0.72%. Issue baseline 0.71% | **INCONCLUSIVE — leaning MISS.** Impressions bar met, position bar met, CTR bar not met and not moving. Only ~9 of 28 days are post-deploy and the export cannot be split by date per page. CTR was 0.71% → 0.66%. Metric window ends ~2026-11-10; rescore then. |
| **#276** dasha CTA on Rahu–Ketu antardasha page | 2026-10-14 02:02Z (#342) | Organic pages/session ≥1.20; inconclusive if <20 sessions | Organic: **28 sessions, pps 1.04**, bounce 35.7%; all channels 34 sessions, pps 1.03. Page now gets 2,055 impr / 26 clicks | **INCONCLUSIVE — leaning NO EFFECT.** 28 sessions clears the floor, but ≤9 days are post-deploy. Arithmetic: 28 × 1.04 ≈ 29 page-views, so at most ~1 onward view in the whole window versus ≥6 predicted. Rescore ≥ 2026-11-11. |
| **#329** link in Manglik "how to check" | 2026-10-14 16:07Z (#344) | Organic pps ≥1.30 on ≥10 sessions | Organic: **3 sessions, pps 1.00**; all channels 8 sessions, pps 1.00 | **INCONCLUSIVE** — 3 sessions, below the issue's own floor of 10. Not a pass. Rescore ≥ 2026-11-14. |
| **#272** export organic sessions + page dimension | 2026-10-08 | Column exists and populated | Organic Search = 169 of 365 session-rows (total 364); `page` populated in band (111 rows) | **PASS on shape; query-level half NOT MET** (8% query coverage) |
| **#515** nightly rashifal on Claude Code | 2026-10-24 | Organic sessions to `/rashifal/*` and email re-open rate, 28d post-deploy | Baseline only: `/rashifal*` landings = **5 sessions, 0 organic** (Direct 4, AI Assistant 1); GSC `/rashifal` 105 impr, 0 clicks, pos 10.4 (prev 32 impr, pos 7.2) | **NOT SCOREABLE** — deployed one day ago; the window opens 10-24. Baseline recorded. Email re-open rate is not in my data. |

### Misses and near-misses, plainly

| Finding | Evidence | Window |
|---|---|---|
| #311's CTR thesis has not shown up. CTR 0.71% → 0.66% on the four pages despite new titles | 19 clicks / 2,896 impr. Per page: career-problems 9/796, debilitated-sun 7/1,246, manglik 2/480, jupiter-10th 1/374 | 09-25 → 10-22 |
| #276's CTA: ~0 onward views | 1.04 pps on 28 organic sessions | 09-25 → 10-22 |
| Meanwhile the *reference* page that #311 used (Rahu–Ketu antardasha) has CTR 1.27%, down from the issue's 2.05%, as impressions grew 1.6× (1,317 → 2,055) | 26/2,055 vs 27/1,317 | 09-25 → 10-22 vs issue window |

Read together: the issue's 2.05% reference rate has itself fallen to 1.27% as impressions rose, which weakens the premise that 2% is an attainable CTR at position 7 here. Treat the "benchmark" in #311 as unreliable.

### 2b. Closed with thesis + metric but not scoreable from GA4/GSC

Not a miss and not a hit; I read no number for these. #313, #316, #320, #338, #345, #349, #355, #362, #369, #372, #373, #374, #396, #397, #400, #405, #408, #409, #442, #449, #493 (metrics are test/gate/ops counts). #286 has no parseable metric line. #397 (Nadi copy) has a user-facing effect but its metric is an occurrence count.

### 2c. Shipped inside the window but still pending

| Item | Merged | Metric | Status |
|---|---|---|---|
| PR #521 (for #518, issue OPEN) — routing 5 dead-end articles to tools | 2026-10-25 | sessions reaching /kundli, /matching, /dasha from a `/learn/*` landing | Baseline from this run: `/learn/*` landings **206 sessions (128 organic), pps 1.35 (organic 1.46)**; homepage 91 sessions, pps 3.76. Nothing to score yet. |

## 3. Confounds (named before any delta)

| Confound | Finding |
|---|---|
| **Concurrent ships** | Local clone is shallow (`git rev-parse --is-shallow-repository` = true), so `git log origin/main --since` returns 1 commit and cannot be used. I used `gh pr list --state merged` instead: from 2026-10-13 on, merged PRs touching `src/` include #334 (titles), #342 and #344 (CTAs), #427 (service-worker SWR), #451 (28 files in learn/templates), #480/#487/#501/#512 (content claim corrections, 7–10 files each), #516 (rashifal, 15 files), #521 (5 learn templates, 10-25). **#451, #480, #487, #512 and #516 touched `/learn` templates in the same weeks as #311/#276/#329, so no CTR or pps delta can be attributed to one change.** |
| **Pre/post split** | The page-level exports cannot be split by date; `gsc-daily` and `ga4-daily` are site-wide only. Every page-level "actual" above mixes pre- and post-deploy days (about 19 pre / 9 post for #311, #276, #329). |
| **Seasonality** | `gsc-daily` shows 310–540 impressions/day throughout the window with no spike, so a festival surge is not visible in the daily series. Window includes the run-up to Diwali (2026-11-08): `/festivals` and festival pages are the pages most likely to be seasonal. Not determined for the learn pages. |
| **Page reachable?** | #253 (stale stylesheet) closed 2026-10-20 and #427 (SWR for /static/) merged 10-20, so returning visitors before 10-20 may have seen the stale stylesheet. #266 (/kundli "high demand") closed 2026-10-21 (`/kundli` is the 3rd-largest landing: 16 sessions). **I did not probe production and cannot say whether /kundli and rashifal were failing in the window.** Treat /kundli and /rashifal engagement before 10-21 as suspect. |
| **Sample size** | 364 sessions in 28 days. Most per-page figures are 3–12 sessions: too small to carry a conclusion. Single-day spike: GA4 **42 sessions on 2026-10-16** against a 5–20 range (cause not determinable from the files). |
| **Impressions rose ~85%** | A rise in impressions with unchanged position means the query mix changed, which alone moves CTR. CTR comparisons between windows are therefore weak. |

## 4. Decay (current window vs 08-28 → 09-24, `dimension: page`)

| Page | Impr now | Impr prev | Clicks now / prev | Pos now / prev | Reading |
|---|--:|--:|--:|--:|---|
| /festivals | 243 | 1,066 | 0 / 1 | 26.4 / 54.0 | Impressions −77% while average position *improved*; the average mixes queries, cause not determinable. Seasonal reading unsupported (Diwali is ahead). |
| /learn/shukra-venus-in-vedic-astrology/ | 35 | 220 | 0 / 2 | 5.8 / 5.6 | Impressions −84% at unchanged position: query-demand loss or a SERP feature, not rank. |
| /learn/mangal-mars-in-vedic-astrology/ | 121 | 236 | 2 / 2 | 7.4 / 7.2 | −49% impr at same position. |
| / (homepage) | 109 | 53 | 8 / 3 | **6.0 / 3.8** | Position lost 2.2 on 109 impr; small sample. |
| /rashifal | 105 | 32 | 0 / 1 | 10.4 / 7.2 | Lost 3.2 positions; 0 clicks. |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 146 | 10 | 0 / 0 | 7.8 / 5.0 | New impressions at 7.8, 0 clicks. |

Biggest gainers (for scale): rahu-mahadasha-ketu-antardasha 555 → 2,055; debilitated-sun-career 346 → 1,246; sade-sati 254 → 1,123 (pos 11.4 → 6.2); planets-in-7th-house-marriage 210 → 545 (pos 5.8); `/matching` 10 → 341 (pos 13.7 → 4.4).

## 5. CTR outliers (band pages ≥200 impr and CTR <0.7%, vs band median 0.81% for ≥100 impr)

| Page | Impr | Clicks | CTR | Pos |
|---|--:|--:|--:|--:|
| /matching | 341 | 0 | 0% | 4.4 |
| /learn/debilitated-sun-career/ | 1,246 | 7 | 0.56% | 6.1 |
| /learn/panch-mahapurush-yoga/ | 489 | 3 | 0.61% | 7.0 |
| /learn/manglik-dosh/ | 480 | 2 | 0.42% | 7.4 |
| /learn/jupiter-in-10th-house-career/ | 374 | 1 | 0.27% | 6.9 |
| /learn/marriage-mahadasha-timing/ | 245 | 1 | 0.41% | 6.5 |

Three of these (debilitated-sun, manglik, jupiter-10th) are pages whose titles #311 already rewrote on 2026-10-13 and are still at the bottom. **`/matching`** is the strongest outlier and already has an open issue (#508, filed for 09-23 → 10-20); this run confirms it at 341 impr / 0 clicks / pos 4.4 on 09-25 → 10-22. No new issue filed.

## 6. Actions taken

| Action | Detail |
|---|---|
| Comments posted | #311, #276, #329, #272, #515 — predicted / actual / verdict, with this run's window |
| Issues filed | **None.** The one actionable CTR finding (`/matching`) already exists as #508; the other findings are waiting on a window to elapse or are too small to carry a conclusion. |

## 7. What I could not determine, and the measurement that would settle it

| Unknown | Single measurement that settles it |
|---|---|
| Whether #311/#276/#329 moved anything | A per-page, per-date GSC/GA4 export (`dimension: page,date`) so the 9 post-deploy days can be split from the 19 before. Otherwise wait for the windows to close: #311 ≈ 2026-11-10, #276 ≈ 2026-11-11, #329 ≈ 2026-11-11 and needs ≥10 organic sessions. |
| The objective's "ten highest-impression queries" | Not measurable at 8% query coverage. `chief` should restate the objective in page terms, or accept it as unmeasurable. |
| Whether the pages were failing during the window | A production probe of `/kundli` and `/rashifal/*` (I did not call production). |
| Cause of the 42-session day on 2026-10-16 | GA4 `date × sessionDefaultChannelGroup` or `date × landing`. |
| Cause of the 85% impression growth | GSC `query × date`; at 8% coverage this may be unrecoverable. |
| Whether the 2.05% "reference CTR" in #311 was ever representative | It is now 1.27% on 1.6× the impressions; the benchmark is one page. |
| Email re-open rate (#515 metric) | Not in GA4/GSC. |
| Real list of what merged when | Clone is shallow; unshallow `origin/main` (`git fetch --unshallow`) so `git log --since` works. |

*analyst, read-only. No code, template, content or BACKLOG.md was edited.*
