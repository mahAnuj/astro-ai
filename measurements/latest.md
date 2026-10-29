# Analyst report — 2026-10-29

**Window for every number unless stated: W = 2026-09-29 → 2026-10-26** (28 days, last 3 excluded).
Prior window P = 2026-09-01 → 2026-09-28 (from `/tmp/gsc-trend-page.json`, same coverage).
Files read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json`, `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json` (written alongside them by the same fetch).
Not read from any earlier comment or `BACKLOG.md`. "Issue baseline" figures are quoted from issue bodies and marked as such.

## 0. Coverage

| export | dimension | window | coverage | truncated |
|---|---|---|---|---|
| GSC band | page | W | 100% of 13,252 impressions; **emitted** 104 rows = 12,040 impr. (91% of 13,288 page-impr.) | no |
| GSC all | page | W | 100% (129 pages, 13,288 page-impr.) | no |
| GSC query (trend file) | query | W | **10%** of 13,252 — partial view, not used to conclude anything about the whole | — |
| GA4 | landing × channel | W | 100% of 424 sessions (110 rows, 76 raw landings → 70 after folding query strings) | no |

All "band" figures are **pages** at average position 6–20, not queries. The objective (OBJECTIVE.md) is worded in queries; the query view covers 10%, so the objective cannot be measured as written (known: #272, #291, #490).

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

| measure (W, pages, GSC) | value |
|---|---|
| pages in band (position 6–20) | 104 of 129 |
| band impressions / clicks | 12,040 / 122 → impressions-weighted CTR **1.01%** (median page CTR 0%) |
| top-10 pages by impressions (all positions) | 8 sit at 6–20; 1 is at 5.8 (`planets-in-7th-house-marriage`, 411 impr.); 1 is in the top 5 (`/matching`, position 4.4, 346 impr., 1 click) |
| same ten pages in P | 0 in the top 5 (`/matching` was at 6.0 on 17 impressions) |
| site total | 13,252 impr. / 139 clicks (W); page-sum 7,455 → 13,288 impr. and 76 → 139 clicks (P → W) |

**Reading:** the band is large and growing in impressions (+78% page-impressions, P → W) but nothing has crossed into the top 5 on a meaningful base. The one page that did (`/matching`) went 17 → 346 impressions and 0 → 1 click; that is too small to count as progress. Positions are page averages across queries, so a page can stay at 6–7 while individual queries sit anywhere in 1–20.

### Band, ranked by `band_opportunity` (top 12 of 104)

| page | impr. W | clicks W | CTR W | position W | impr. P → W | position P → W |
|---|--:|--:|--:|--:|--|--|
| /learn/rahu-mahadasha-ketu-antardasha/ | 2,460 | 31 | 1.26% | 7.1 | 808 → 2,460 | 7.5 → 7.1 |
| /learn/debilitated-sun-career/ | 1,585 | 7 | 0.44% | 6.4 | 491 → 1,585 | 6.3 → 6.4 |
| /learn/sade-sati/ | 1,470 | 9 | 0.61% | 6.4 | 338 → 1,470 | 6.9 → 6.4 |
| /learn/rahu-mahadasha-career-problems/ | 769 | 10 | 1.30% | 6.9 | 719 → 769 | 8.4 → 6.9 |
| /learn/panch-mahapurush-yoga/ | 527 | 4 | 0.76% | 6.9 | 157 → 527 | 7.3 → 6.9 |
| /learn/manglik-dosh/ | 488 | 4 | 0.82% | 7.2 | 287 → 488 | 9.0 → 7.2 |
| /learn/career-during-sade-sati/ | 506 | 8 | 1.58% | 6.6 | 231 → 506 | 7.9 → 6.6 |
| /learn/jupiter-in-10th-house-career/ | 372 | 1 | 0.27% | 7.0 | 227 → 372 | 6.7 → 7.0 |
| /learn/marriage-mahadasha-timing/ | 263 | 1 | 0.38% | 6.6 | 177 → 263 | 7.3 → 6.6 |
| /learn/7th-lord-placement-marriage-guide/ | 304 | 5 | 1.64% | 7.6 | 208 → 304 | 8.5 → 7.6 |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 179 | 0 | 0% | 8.0 | 17 → 179 | 6.5 → 8.0 |
| /learn/10th-lord-in-6th-house-career/ | 234 | 4 | 1.71% | 6.8 | 84 → 234 | 7.5 → 6.8 |

The top 10 of the band hold 8,744 impressions and 80 clicks (0.91%).

## 2. CTR outliers (comparison: the band's own weighted CTR, 1.01%, and its best page, 1.26% on a large base)

| page | impr. W | clicks W | CTR W | position W | finding |
|---|--:|--:|--:|--:|---|
| /learn/debilitated-sun-career/ | 1,585 | 7 | 0.44% | 6.4 | position unchanged from P, CTR under half the band; **title was rewritten by #311 (2026-10-13) and did not move it** |
| /learn/sade-sati/ | 1,470 | 9 | 0.61% | 6.4 | second-largest unexplained gap; not touched by #311 |
| /learn/jupiter-in-10th-house-career/ | 372 | 1 | 0.27% | 7.0 | #311 page; no lift |
| /learn/panch-mahapurush-yoga/ | 527 | 4 | 0.76% | 6.9 | below band |
| /learn/manglik-dosh/ | 488 | 4 | 0.82% | 7.2 | #311 page; below band |
| 6 band pages ≥ 100 impr. with **0 clicks** | 102–179 each | 0 | 0% | 6.1–10.2 | `kundali-matching-ashtakoot-guna-milan` (179), `/learn/` (146), `gochar-2026-planetary-transits` (140), `chronic-health-issues-kundli` (131), `/rashifal` (130), `guru-jupiter-in-vedic-astrology` (102) |

Size of the prize, not a recommendation: `debilitated-sun-career` + `sade-sati` are 3,055 impressions at 16 clicks (0.52%); at the band's best large-base page (1.26%) that would be ~38 clicks, i.e. **~+22 clicks in 28 days**. Small in absolute terms.

**Caveat on "achievable CTR":** the reference page used by #311 as the target (2.05% on 1,317 impr., issue baseline) is **1.26%** on 2,460 impr. in W. As impressions tripled, CTR fell. A CTR target taken from a smaller impression base should not be trusted.

## 3. Post-ship scoring (issues closed 2026-09-29 → 2026-10-29 carrying `thesis:` and `metric:`)

28 issues closed 2026-09-29 → 2026-10-29 carry a `thesis:` (27 also a `metric:`; #286 does not). **5 have a metric GA4/GSC can read; comments posted on each today.** The other 22 are infra, security, test, prompt-gate or tooling issues whose metrics are repo counts or loop outcomes — not scoreable from these exports (listed at the foot).

| issue | predicted (`metric:`) | actual (W) | verdict | posted |
|---|---|---|---|---|
| **#311** title/meta on 4 band pages | combined CTR ≥ 1.5% on ≥ 1,500 impr., position within ±1 | **0.685%** (22 / 3,214); position 6.71; P = 0.580% (10 / 1,724); issue baseline 0.71% (quoted) | **MISS so far** — impressions/position conditions hold, CTR is under half the bar. Post-deploy half cannot be isolated (no page×day export, #490); bound shows 1.5% is not plausible | yes |
| **#276** dasha CTA on Rahu–Ketu antardasha | organic pps ≥ 1.20, < 20 sessions = inconclusive | **1.16** on 32 organic sessions (all channels 43 sessions, 1.12) | **INCONCLUSIVE, below the bar on the whole window**; ~15 of 28 days are pre-deploy. Post-deploy would need ≈ 1.3 if the pre half sat at 1.0 (untested assumption) | yes |
| **#329** Manglik checker link | organic pps ≥ 1.30 on ≥ 10 sessions | **1.00** on **5** organic sessions (11 all channels) | **INCONCLUSIVE** (below sample floor). At ~5 organic sessions per 28 days the floor may never be met | yes |
| **#515** nightly rashifal (traffic metric only) | organic sessions to `/rashifal/*` improve | **0** organic; 5 `/rashifal*` landings (Direct 4, AI Assistant 1); GSC 165 impr., 0 clicks across all `rashifal` pages | **NOT SCOREABLE YET** (PR #516 merged 2026-10-24; 2 full post-deploy days). Baseline is zero. First check ≥ 2026-11-24 | yes |
| **#272** export dimensions | organic sessions as a separate number; ranking URL beside band entries | Organic Search = 199 of 424 sessions; `page` present, 104 band rows | **PASS on shape; query-level half still NOT MET** (query view covers 10%) | yes |

**The misses, plainly:** #311 is the only one with enough data to say anything, and what it says is *no lift*. Two of its four pages (`debilitated-sun-career`, `jupiter-in-10th-house-career`) are still at 0.27–0.44% CTR. #276 has not reached its bar on the whole window. #329 has too little traffic to be a test at all. No ship from this set can be called a hit.

Not scoreable from GA4/GSC (thesis present, metric is a repo/loop/security count): #313, #316, #320, #338, #345, #349, #355, #362, #369, #372, #373, #374, #396, #397, #400, #405, #408, #409, #442, #449, #493, #495. (#286 carries a `thesis:` but no `metric:` line.) #397 (Nadi wording) and #355 (miss latency) have user-facing effects but their metrics are string counts / latency, which I cannot read here.

## 4. Confounds (named before any delta above)

| confound | evidence | effect on the deltas |
|---|---|---|
| **Concurrent ships** | `git log origin/main --since` returns **1 commit**: the checkout is shallow (`git rev-parse --is-shallow-repository` = true). Used `gh pr list --state merged --search "merged:>=2026-09-29"` instead. 44 merged PRs touch `src/`. Template-affecting, with merge times: #334 (10-13, the #311 ship), #342 (10-14), #344 (10-14), **#451 (10-21, 26 files under `templates/learn/` incl. all four #311 pages, the antardasha page and `manglik-dosh`)**, #480 (10-22), #487 (10-23), #512 (10-24), #516 (10-24, rashifal), **#521 (10-25, `debilitated-sun-career`, `jupiter-in-10th-house-career`, 3 others)**, #530 (10-26), #556 (10-28, after W) | Three or more ships touched the same pages inside W. **No delta on #311, #276 or #329 can be attributed to one change.** I have not picked one |
| **Seasonality** | Site-wide GSC impressions: 417/day (2026-09-29..10-22) → **814/day (10-23..10-26)**, average position unchanged (6.92 in the last 4 days). GA4 sessions 13.6/day → 24.5/day over the same split. Diwali is 2026-11-08 (CLAUDE.md). Sessions also spike on single days: 42 on 2026-10-16, 34 on 2026-10-23 | The last 4 days carry ~25% of W's impressions (3,255 of 13,252). Pages gaining impressions late in W are not evidence of work. **I cannot say whether the doubling is the festival calendar, #451/#521, or something else** — no page×day export |
| **Page reachable?** | #253 (stale stylesheet) was fixed by #427 on 2026-10-20 — inside W. I have **no uptime or error-rate data** in the three files, so I cannot say whether #266 (intermittent Groq TPM failures) hit any ranking page in W | Traffic and CTR on `/learn/*` pages (static templates, no LLM call) are unlikely to be affected by #266; `/rashifal*` pages are. Not verified |
| **Sample size** | 424 sessions, 139 clicks in W. #311 rests on 22 clicks; #329 on 5 organic sessions; #276 on 32 | A 3-click swing moves #311's CTR by ~0.1 pp. Stated as "not near 1.5%", not as a precise delta |
| **Non-organic contamination** | `/` has 80 Direct sessions at pps 3.54; `/admin/ops` is a landing with 12 sessions (Direct 11); Direct = 199 of 424 sessions | The homepage "3.75 pps" benchmark in #518 is probably inflated by Direct traffic that may be the owner or agents. **Cannot be proved from these exports.** Does not affect organic sessions |

## 5. Decay (P → W, GSC page, pages with ≥ 100 impressions in either window)

| page | impr. P → W | position P → W | clicks P → W | read |
|---|---|---|---|---|
| /festivals | 759 → 240 | 40.1 → 26.4 | 1 → 0 | impressions down 68% but position **improved**; not in the band, not a ranking loss |
| /learn/shukra-venus-in-vedic-astrology/ | 210 → 63 | 5.5 → 6.3 | 2 → 0 | lost impressions; position moved from 5.5 (above the band) to 6.3 (inside it) |
| /learn/mangal-mars-in-vedic-astrology/ | 227 → 151 | 7.1 → 7.4 | 2 → 3 | −34% impressions |
| /learn/the-9-grahas-overview/ | 103 → 59 | 7.3 → 8.9 | 0 → 0 | down |
| /learn/kaal-sarp-dosh/ | 86 → 140 | 5.7 → 6.3 | 1 → 3 | moved from 5.7 (above the band) into it |
| /learn/guru-jupiter-in-vedic-astrology/ | 73 → 102 | 6.8 → 7.6 | 1 → 0 | slipped |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 17 → 179 | 6.5 → 8.0 | 0 → 0 | gained impressions, lost position |
| / | 58 → 123 | 4.3 → 6.0 | 2 → 9 | moved from 4.3 to 6.0 (brand/navigational mix, not a content page) |

Decay is mild and on small bases (largest real loss: `shukra-venus`, −147 impressions). Nothing here is a finding needing action; it is a watch list. Net: page-impressions rose 78% and clicks 83% (76 → 139) P → W.

## 6. Funnel (GA4, W, Organic Search unless stated)

| landing group | sessions | bounce | pages/session |
|---|--:|--:|--:|
| /learn/* (organic) | 150 | 44% | 1.45 |
| /learn/* (all channels) | 236 (55.7% of 424) | — | 1.34 |
| / (all channels; 80 of 90 Direct) | 90 | — | 3.62 |
| /kundli (organic) | 10 | 50% | 2.0 |
| /kundli (Direct) | 12 | 100% | 1.0 |
| /matching (organic) | 1 | 0% | 1.0 |
| /matching (Direct) | 10 | 90% | 1.0 |
| /dasha | 0 landings | — | — |
| organic, all landings | 199 | 45% | 1.61 |

Landing → form → result → second page is **not computable**: no event dimension in the export (#272 finding 5, #570). /learn is 56% of sessions and its pages-per-session is 1.34 against 3.62 for `/` — but `/` is mostly Direct and may include owner traffic (see §4), so that ratio overstates the gap by an unknown amount. Organic arrivals on tool pages are 11 sessions in total (`/kundli` 10, `/matching` 1).

## 7. Issues filed

**None.** Candidate findings and why each is not a new issue:

| candidate | disposition |
|---|---|
| Cannot split a ship's effect by date (page × day) | already open: **#490** |
| No click event on in-article tool links | already open: **#570** |
| Title rewrite on #311 did not move CTR | recorded as a miss on #311; a second title test on `debilitated-sun-career`/`sade-sati` would repeat a thesis that just missed, and the effect size (~+22 clicks / 28 days at best) is small |
| Direct traffic may include owner/agent visits | hypothesis, not evidence; no Evidence Block can be written from these exports |

## 8. What I could not determine, and the measurement that would settle it

| question | what is missing | the measurement |
|---|---|---|
| Did #311 / #276 / #329 move anything after deploy, alone? | no page × day cut; 3+ ships on the same pages in W | GSC `date × page` and GA4 `date × landing` for the four pages (#490). Or wait: a window with only post-deploy days is first available on a fetch ≥ **2026-11-13** (#311), **2026-11-14** (#276, #329), **2026-11-24** (#515) |
| Why did site impressions double on 10-23 → 10-26? | no per-page daily series | same `date × page` export; check which pages gained |
| Is `/` Direct traffic real visitors? | no internal-traffic filter visible in the export | GA4 `Direct` split by `hostname`/`deviceCategory`, or the owner's own count |
| Did #266 break any ranking page in W? | no uptime/error data in these files | `/admin/ops` error and fallback series for 2026-09-29 → 10-26 |
| Top-10 band *queries* | query dimension = 10% of impressions | not recoverable; page-level is the best available |
| #515's first metric (31.0% → < 5%) and email re-open rate | not in GA4/GSC | blob measurement and email-provider stats |
