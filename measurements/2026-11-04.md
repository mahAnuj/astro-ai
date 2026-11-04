# Analyst report — 2026-11-04

**Windows used everywhere below** (all read this run from `/tmp/*.json`, last 3 days excluded):

- **W** = 2026-10-05 → 2026-11-01 (28 days). **P** = 2026-09-07 → 2026-10-04 (28 days, from `gsc-trend-page.json` / `gsc-trend-query.json`).
- GSC: `sc-domain:shubhagya.com`, `dimension: page`, coverage **100%** of 17,416 impressions, `truncated: false`. Query view: coverage **12%** (2,092 of 17,416 impressions) — partial, never read as the whole band.
- GA4: property 543505751, landing × channel, coverage **100%** of 500 sessions, `truncated: false`. GA4 has no prior-window export, so GA4 figures are W-only.
- Production reachability: **not checked.** `curl https://shubhagya.com/health` from the runner returned no HTTP response (status `000`). No page in this report was confirmed rendering today.

**Headline.** Impressions doubled P → W (8,468 → 17,446 on the trend rows) with clicks 90 → 190, and almost all of it is the 6–20 band. The band is large and **no query in it reached the top 5.** The one lever tested on CTR (#311 title/meta) did not work on 3 of 4 pages. No ship in the last 28 days can yet be scored a hit.

---

## 1. The 6–20 band vs OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression queries."* The primary export is by **page** (position = the page's average over its queries), so the objective's literal unit — a query — is only measurable on the 12% query view.

### Whole-site position distribution (GSC page view, W, coverage 100%)

| bucket | pages | impressions | clicks | CTR |
|---|---|---|---|---|
| position ≤ 5 | 28 | 2,770 | 38 | 1.37% |
| **position 6–20 (the band)** | **98** | **14,416** (83% of rows' impressions) | **152** | **1.05%** |
| position > 20 | 9 | 260 | 0 | 0% |
| all | 135 | 17,446 | 190 | 1.09% |

Of the band's 98 pages, 80 sit at 6.0–9.99 (14,156 impressions, 151 clicks) and only 18 at 10–20 (260 impressions, 1 click). The band is almost entirely **positions 6–9** — bottom of page one or top of page two, not deep.

### Top of the band, ranked by `impressions × achievable CTR gain` (`band_opportunity` from the export) — W

| # | page | impr | clicks | CTR | avg pos | impr P | pos P |
|---|---|---|---|---|---|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,040 | 35 | 1.15% | 6.8 | 1,167 | 7.6 |
| 2 | /learn/debilitated-sun-career/ | 1,996 | 10 | 0.50% | 6.6 | 710 | 6.1 |
| 3 | /learn/sade-sati/ | 1,808 | 12 | 0.66% | 6.4 | 544 | 6.6 |
| 4 | /learn/jupiter-in-10th-house-career/ | 954 | 6 | 0.63% | 7.0 | 301 | 6.8 |
| 5 | /learn/rahu-mahadasha-career-problems/ | 882 | 15 | 1.70% | 6.5 | 788 | 7.8 |
| 6 | /learn/7th-lord-placement-marriage-guide/ | 670 | 9 | 1.34% | 7.3 | 204 | 8.6 |
| 7 | /learn/panch-mahapurush-yoga/ | 552 | 6 | 1.09% | 6.9 | 228 | 6.8 |
| 8 | /learn/manglik-dosh/ | 495 | 4 | 0.81% | 7.0 | 350 | 8.1 |
| 9 | /learn/marriage-mahadasha-timing/ | 311 | 1 | 0.32% | 6.3 | — | — |
| 10 | /learn/10th-lord-in-6th-house-career/ | 402 | 8 | 1.99% | 6.5 | 136 | 7.0 |

The 10 highest-impression band pages hold **11,110 of the band's 14,416 impressions (77%)** and 106 of its 152 clicks. Not in the band but adjacent: `/learn/career-during-sade-sati/` 744 impressions at 5.8 and `/learn/gochar-2026-planetary-transits/` 565 at 5.9 — both just inside the top 6 on average.

### Objective check on the query view (PARTIAL: 12% of impressions, W)

| measure | value |
|---|---|
| ten highest-impression queries observed (sum 874 impressions) | **0 at position ≤ 5; 10 of 10 at 6.3–10.1** |
| queries at 6–20 | 223 queries, 1,726 impressions |
| queries at ≤ 5 | 153 queries, 239 impressions |
| queries at > 20 | 58 queries, 90 impressions |
| top query: "rahu mahadasha ketu antardasha" | 334 impr, 7 clicks, pos 8.5 (P: 149 impr, pos 9.6) |

**Objective status: not met, and not close.** Impressions are rising into the band faster than position is improving; the one measurable position improvement on the top query is 9.6 → 8.5 (P → W). Query-level data cannot say whether the 91% of impressions Google withholds are better or worse placed.

**Metric caveat.** The page view's `position` is an average; a page can rank 1 for one query and 15 for another. "Pages at 6–20" and "queries at 6–20" are not the same count. Treat the table above as the page-level band, and the query table as an unrepresentative 12% sample.

---

## 2. Scores — issues closed 2026-10-07 → 2026-11-04 carrying `thesis:` and `metric:`

92 issues closed in this span; **46** carry both strings in their body. **8 were scored on an issue comment this run** (links below); 1 was already scored (#272, 2026-10-09); the other **37 are not scoreable from GA4/GSC** (see bottom of this section).

| issue | closed | thesis / predicted | actual (window) | verdict |
|---|---|---|---|---|
| **#311** SEO: title/meta on 4 band pages | 2026-10-13 | combined CTR ≥ **1.5%** on ≥ 1,500 impr, position within ±1 | **0.81%** (35 / 4,327), W; P 0.65% (14 / 2,149). 3 of 4 pages flat or down (20 / 3,445 = 0.58% vs P 0.66%); the whole gain is one page, 15 clicks | **MISS so far** — not final, post-only window closes 2026-11-10 |
| **#276** CONVERSION: early-dasha CTA on top landing | 2026-10-14 | pages/session ≥ **1.20** on ≥ 20 sessions | **1.36** on 50 sessions, W (Organic 1.49 on 37; Direct 1.00 on 12) | **PROVISIONAL — not attributable.** Above the bar, but organic share rose and organic always reads higher than direct; ~9 pre-deploy days in W |
| **#329** CONVERSION: Manglik checker link | 2026-10-14 | pages/session ≥ **1.30** on ≥ 10 organic sessions | **1.00** on **4** organic sessions (9 total), W | **INCONCLUSIVE** (below the issue's own 10-session floor) |
| **#685** SEO: sade-sati title names Moon signs | 2026-11-03 | CTR ≥ 1.2% on ≥ 1,200 impr, position ±1 of 6.4 | deployed after W ends — W is the **baseline**: 12 / 1,808 = 0.66%, pos 6.4 | **NOT SCOREABLE YET** (earliest ~2026-12-04) |
| **#426** CONTENT: Saturn exit dates | 2026-11-02 | guard: position ±1 of 6.2, impressions not down > 20% | deployed after W ends; baseline 1,808 impr, pos 6.4 | **NOT SCOREABLE YET** |
| **#570** MEASURE: `cta_click` event | 2026-11-03 | `cta_click` rows by `from_path` / `to_path` | exports carry no event dimension; deployed after W | **NOT SCOREABLE** — data not in this run's inputs |
| **#514** Rashifal: computed fields | 2026-11-01 | organic + email re-open on `/rashifal/*` | GA4 organic sessions **0**; GSC 213 impr / 0 clicks (P 43 / 1); no re-open data | **NOT SCOREABLE YET** |
| **#515** Rashifal: nightly generation | 2026-10-24 | organic sessions + re-open, 28d post-deploy | same as #514; ~19 pre-deploy days in W | **NOT SCOREABLE YET** (closes ~2026-11-21) |

Comments posted: #311 `…/issues/311#issuecomment-6619667903`, #276 `…6619668182`, #329 `…6619668464`, #685 `…6619668721`, #426 `…6619669000`, #570 `…6619669282`, #514 `…6619669535`, #515 `…6619669811`.

### The misses, stated as plainly as the hits

| finding | evidence (W) |
|---|---|
| **The title/meta lever has not moved CTR.** #311 predicted ≥ 1.5%; the four pages read 0.81%. | 35 / 4,327. Needs ~65 clicks at W's impressions; got 35. |
| **Three of the four rewritten pages are flat or worse.** | debilitated-sun 0.70% → 0.50%; jupiter-in-10th 0.66% → 0.63%; manglik 0.57% → 0.81% (4 clicks). |
| **The one page that moved may not be the title.** | career-problems 0.63% → 1.70% (5 → 15 clicks) also moved position 7.8 → 6.5, and was edited by #530 and #615 inside W. |
| **Both conversion theses (#276, #329) have no direct evidence yet.** | `cta_click` shipped 2026-11-03, after W. #329 is under its own sample floor. |
| **No ship in the 28 days can be called a hit.** | 0 of 8 scored. 1 miss-so-far, 1 provisional, 6 not yet measurable. |

### Not scored by the analyst — 37 issues whose `metric:` is a repo or loop count, not GA4 / GSC

#286, #313, #316, #320, #338, #345, #349, #355, #357, #358, #362, #369, #372, #373, #374, #396, #397, #398, #400, #405, #406, #407, #408, #409, #431, #432, #442, #449, #450, #493, #495, #510, #543, #602, #604, #607, #621.

Their metrics are things like grep counts, test counts, workflow outcomes and CSS rule sizes. I did not measure any of them and make no claim about whether they passed — that belongs to `qa` and the loop-outcome report. Two read production behaviour (#349 error rate, #355 miss latency); neither is in the exports I read. The selection used the string match `thesis:` AND `metric:` in the issue **body** only; an issue that carries them only in a comment would not appear.

---

## 3. Confounds — named before any delta

| confound | what the files show |
|---|---|
| **Site-wide impression step from 2026-10-23** | GSC daily: 7,743 impressions / 79 clicks over 10-05..10-22 (18 days, ~430/day) vs 9,673 / 111 over 10-23..11-01 (10 days, ~967/day), at flat average position (6.5–7.6 daily). New low-intent queries dilute CTR on every page. |
| **Concurrent ships on the same pages** | Learn-page PRs merged in or near W: #342, #344 (10-14); #451 (10-21), #480 (10-22), #487 (10-23), #521 (10-25), #530 (10-26), #556 (10-28), #587 (10-29), #615 (10-31), #658 (11-01), #673/#680 (11-02), #690 (11-03). Every one of #311's four pages was touched by at least one other PR in W, so **no per-page CTR delta is attributable to a single ship.** |
| **Pre/post split impossible inside W** | Deploys for #311/#276/#329 fell 2026-10-13/14, so W holds ~9 pre-deploy and ~19 post-deploy days that GA4/GSC exports here cannot separate (no per-page × per-day export — **#490**, open). |
| **Seasonality** | Not determined. The two biggest risers are astrological-event queries (`gochar-2026-planetary-transits` 39 → 565 impr; `sade-sati` 544 → 1,808) in a month with a Saturn transit date correction; whether that is search interest or ranking is not separable here. |
| **Was the page reachable?** | Not verified today (no response from `/health` on the runner). #253 (stale CSS) is closed; #266 (Groq 413 on `/kundli`) is closed. Rashifal pages call the LLM path — the 0 organic rashifal sessions in W is read as "too small", not as "broken". |
| **Direct traffic is large and not clean** | GA4 W: Direct **218 of 500 sessions (43.6%)**, bounce 67%, 2.11 pages/session; `/` alone holds 82 Direct sessions at 34% bounce and 3.78 pages/session. `/admin/ops` is 13 sessions (12 Direct). Internal or automated traffic cannot be separated from visitors with these exports. **Organic Search (257 sessions, 47% bounce, 1.56 pages/session) is the clean north-star series; any all-channel pages/session figure mixes in Direct.** |
| **Single-day GA4 spikes** | 2026-10-16 = 42 sessions and 2026-10-23 = 34 sessions vs ~15/day typical. No matching GSC spike on 10-16, so the 10-16 spike is not search. Channel for those days not determined (the daily export has no channel). |
| **Shallow checkout** | `git rev-parse --is-shallow-repository` → true, 1 commit visible; the required `git log origin/main --since` check was **not available** (open issue **#666**). I used `gh pr list --state merged` and `gh pr view --json files` instead; the PR-level lists above are not exhaustive. |
| **Sample size** | Per-page clicks in the band are 1–35. Page-level CTR differences under ~0.5 pt are noise on this site. |

---

## 4. Decay and CTR outliers

### CTR outliers, band pages with ≥ 150 impressions, W

The band's own median CTR is **0.0%** (more than half of its 98 pages got no click), so the comparison is the band's aggregate rate, **1.05%** (152 / 14,416).

| page | impr | clicks | CTR | pos | reading |
|---|---|---|---|---|---|
| /learn/debilitated-sun-career/ | 1,996 | 10 | 0.50% | 6.6 | below band aggregate; #311 title test did not fix it |
| /learn/sade-sati/ | 1,808 | 12 | 0.66% | 6.4 | title just changed (#690) — baseline |
| /learn/jupiter-in-10th-house-career/ | 954 | 6 | 0.63% | 7.0 | #311 title test did not fix it |
| /learn/marriage-mahadasha-timing/ | 311 | 1 | 0.32% | 6.3 | lowest CTR of any band page ≥ 300 impr |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 204 | 0 | 0% | 7.6 | zero clicks; P 22 impr at pos 9.7 — new ranking. Edited by #680 on 11-02 (after W) |
| /rashifal | 151 | 0 | 0% | 8.7 | zero clicks |
| /learn/vimshottari-dasha-explained/ | 158 | 1 | 0.63% | 7.0 | P: 4 impr — new ranking |

### Zero clicks on ≥ 100 impressions (all pages, W)

`/festivals` 245 impr (pos 29.7), `/learn/kundali-matching-ashtakoot-guna-milan/` 204, `/learn/shukra-venus-in-vedic-astrology/` 157 (pos 5.9), `/rashifal` 151, `/learn/` 140 (pos 11.0), `/learn/guru-jupiter-in-vedic-astrology/` 119.

### Decay (position worse by ≥ 1.5, P impressions ≥ 40) — W vs P

| page | impr P → W | position P → W | clicks P → W |
|---|---|---|---|
| /learn/the-9-grahas-overview/ | 101 → 51 | 7.4 → 9.2 | 0 → 0 |
| /learn/ashwini-nakshatra/ | 93 → 55 | 5.5 → 7.4 | 1 → 0 |
| /learn/vivah-muhurat-2027/ | 46 → 53 | 7.6 → 9.6 | 0 → 0 |

Three pages, none above 101 impressions in P; none large enough to be a ranking-loss finding. Also down on impressions without a position change worth naming: `/festivals` 468 → 245, `/learn/planets-in-7th-house-marriage/` 454 → 348 (position improved 6.4 → 5.7), `/learn/sun-in-10th-house-career/` 116 → 56. **No decay was found on a page carrying meaningful traffic.**

---

## 5. Funnel and engagement (GA4, W, landing × channel, folded by path, sessions-weighted)

| channel | sessions | bounce | pages/session |
|---|---|---|---|
| Organic Search | 257 | 46.7% | 1.56 |
| Direct | 218 | 67.0% | 2.11 |
| AI Assistant | 19 | 36.8% | 3.16 |
| Unassigned | 7 | 85.7% | 0.29 |
| total | 501 (export: 500) | | |

| landing (path-folded, W) | sessions | bounce | pages/session | mix |
|---|---|---|---|---|
| / | 93 | 34% | 3.78 | Direct 82, Organic 9, AI 2 |
| /learn/rahu-mahadasha-ketu-antardasha | 50 | 48% | 1.36 | Organic 37, Direct 13 |
| /kundli | 23 | 74% | 1.69 | Direct 12, Organic 11 |
| /learn/rahu-mahadasha-career-problems | 19 | 47% | 1.89 | Organic 18 |
| /learn/gochar-2026-planetary-transits | 16 | 56% | 1.19 | Organic 12 |
| /learn/debilitated-sun-career | 15 | 67% | 1.20 | Organic 14 |
| /learn/sade-sati | 15 | 33% | 1.93 | Organic 11 |
| /matching | 13 | 69% | 2.23 | Direct 10, AI 2 |
| /numerology | 11 | 82% | 1.00 | Direct 9 |

- GA4 daily: 219 sessions in the first 14 days (10-05..10-18) vs 283 in the last 14 (10-19..11-01), **+29%**; GSC impressions on the same split 5,922 → 11,494 (+94%), clicks 57 → 133 (+133%). Search clicks grew far faster than organic sessions — GSC clicks 190 in W vs GA4 organic sessions 257, so the two do not reconcile and I cannot say why (GA4 channel grouping vs GSC click counts differ by design; not investigated).
- **Funnel by tool (kundli → result → second page) cannot be read from these files.** The export is landing → sessions → pages/session; there is no step-through event. `/kundli` has 23 landing sessions at 74% bounce — higher than the 47% organic-learn rate — but it is a mixed Direct / Organic landing and has no result-page event to measure against.
- Learn pages with high bounce and ≥ 10 sessions: `/learn/10th-lord-in-6th-house-career` 83% (12), `/learn/marriage-mahadasha-timing` 83% (12), `/learn/griha-pravesh-muhurat-2026-2027` 73% (15), `/learn/manglik-dosh` 78% (9). Each is below the sample at which a page-level bounce is a finding.

---

## 6. Issues filed

**None.** Every finding that would justify one is already tracked, or is a measurement the data cannot support:

| candidate finding | why not filed |
|---|---|
| Per-page × per-day export is missing, so the 28-day post-deploy windows cannot be scored cleanly | already open: **#490** |
| `git log origin/main --since` unavailable (shallow checkout) | already open: **#666** |
| `/matching` title/meta (ranks 4.3, 342 impr, 2 clicks in W) | already open: **#508**; a title shortening landed as #696 on 2026-11-03 |
| Workflow prompts label GSC pages as "queries" | already open: **#291** (I confirmed the exports are page-level; the labels remain wrong) |
| More title/meta rewrites of band pages | the analyst does not propose features, and the one tested lever is a miss-so-far (#311); the PM should read §2 before specifying another |
| Direct/internal traffic pollution (43.6% Direct; `/admin/ops` 13 sessions; two unexplained single-day spikes) | real, but no export here carries the channel × day or hostname split that would let an issue name a fix with an Evidence Block; a candidate for the next GA4 export, not for an issue today |

---

## 7. What I could not determine, and the one measurement that settles it

| unknown | the single measurement |
|---|---|
| Effect of #311 / #276 / #329 on their own pages, separated from the 2026-10-23 impression step and neighbouring edits | A per-page × per-day GSC export (#490) cut at each deploy timestamp — `2026-10-14..2026-11-10` vs `2026-09-16..2026-10-13` for the three 2026-10-13/14 ships |
| Whether #276's CTA is used | `cta_click` `from_path=/learn/rahu-mahadasha-ketu-antardasha/` → `to_path=/dasha`, 2026-11-04 → 2026-12-01 (#570 shipped 2026-11-03) |
| Whether #685 / #426 helped or hurt `/learn/sade-sati/` | GSC page rows for it over 2026-11-04 → 2026-12-01, readable ~2026-12-04; three edits landed within 23 hours of each other on 11-02..11-03 |
| Whether production was rendering correctly for these pages in W | HTTP + body checks of the top 10 band pages, run from a host that can reach `shubhagya.com` — the runner got no response from `/health` |
| Whether the 91% of impressions hidden from the query view are better or worse than the visible 9% | cannot be recovered; only the page-level band is whole |
| What the 218 Direct sessions are | GA4 hostname / internal-traffic filter, or a channel × day export, to split owner and automated traffic from visitors |
| Rashifal organic traffic | 28 days of `/rashifal/*` GA4 sessions after the 2026-10-24 and 2026-11-01 ships (≥ 2026-11-24); re-open rate needs the email provider's data, which is in no export here |
| Per-issue score for the 37 non-GA4/GSC thesis issues | not an analyst measurement; `qa` or the loop-outcome report |

---

*Read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus `/tmp/ga4-daily.json`, `/tmp/gsc-daily.json`, `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json` (same 2026-11-04 01:00 fetch). Issue bodies and PR file lists via `gh`. No number above is carried from BACKLOG.md or an earlier comment; the pass thresholds quoted per issue are each issue's own `metric:`.*
