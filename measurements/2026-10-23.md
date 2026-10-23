# Analyst report — run of 2026-10-23

**Windows.** Current **W = 2026-09-23 → 2026-10-20** (28 days, last 3 excluded). Previous **P = 2026-08-26 → 2026-09-22**, from `/tmp/gsc-trend-page.json`. GA4 has no previous-window file this run.
All numbers below were read from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, and the same-run siblings `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json`, `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json`. Exceptions are labelled (issue-body baselines, live probes, git).

## 0. Headline

| | |
|---|---|
| Verdicts posted this run | 0 hits, 0 misses, **3 INCONCLUSIVE** (#276, #311, #329), 1 PASS-on-shape (#272), 1 UNSCORED (#493) |
| Nothing is a hit yet | None of the three traffic theses can show a lift. No ship is 28 days old; the earliest, #311, is 10 days post-deploy. |
| Nothing is a miss yet, **but none of the three shows any sign of lift** | #276 pages/session 1.03 (target 1.20). #311 CTR 0.66% (target ≥ 1.2–1.5%). #329 has 3 organic sessions against a floor of 10. |
| Issue filed | **#508**, `/matching` ranks 4.3 on 336 impressions and got 0 clicks |
| Window caveat on everything | The objective is worded on **queries**; the only view with full coverage is **pages** (100%). The query view covers **8%** of impressions. |

## 1. The 6–20 band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**Coverage first.** GSC `dimension: page`, W, 11,749 impressions, 116 clicks, coverage 100%, not truncated. `--band` printed 109 pages at position 6–20 = 10,424 impressions, **emitted coverage 89%**. `position` is a page's average across its queries, not any query's. I cannot evaluate the objective on queries: `gsc-trend-query.json` covers **8%** of impressions (W).

| Band, pages at avg position 6–20, W | value |
|---|--:|
| pages | 109 |
| impressions | 10,424 |
| clicks | 109 |
| CTR | 1.05% |
| pages with 0 clicks | 77 of 109 |
| top-10 pages by opportunity: impressions / clicks | 7,336 / 66 (0.90%) |
| pages already at position < 6 (all GSC rows) | 13 pages, 1,075 impressions |

Ten largest band items, ranked by the export's `band_opportunity`. Window W, GSC page:

| # | page | impr | clicks | CTR | avg pos | impr in P → W | pos in P → W |
|--:|---|--:|--:|--:|--:|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,010 | 25 | 1.24% | 7.5 | 413 → 2,010 | 7.6 → 7.5 |
| 2 | /learn/debilitated-sun-career/ | 1,237 | 8 | 0.65% | 6.1 | 267 → 1,237 | 7.1 → 6.1 |
| 3 | /learn/sade-sati/ | 1,092 | 9 | 0.82% | 6.2 | 209 → 1,092 | 15.1 → 6.2 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 806 | 8 | 0.99% | 6.9 | 644 → 806 | 8.6 → 6.9 |
| 5 | /learn/manglik-dosh/ | 471 | 2 | 0.42% | 7.5 | 184 → 471 | 14.9 → 7.5 |
| 6 | /learn/panch-mahapurush-yoga/ | 451 | 3 | 0.67% | 7.0 | 99 → 451 | 9.6 → 7.0 |
| 7 | /learn/jupiter-in-10th-house-career/ | 376 | 1 | 0.27% | 6.8 | 170 → 376 | 7.1 → 6.8 |
| 8 | /learn/career-during-sade-sati/ | 384 | 4 | 1.04% | 7.0 | 174 → 384 | 8.8 → 7.0 |
| 9 | /learn/marriage-mahadasha-timing/ | 242 | 1 | 0.41% | 6.4 | 151 → 242 | 8.0 → 6.4 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 267 | 5 | 1.87% | 7.8 | 221 → 267 | 8.8 → 7.8 |

**What the numbers say about the objective:**

| Finding | Number (window) |
|---|---|
| No band page reached the top 5 on its own *average* | Closest are `planets-in-7th-house-marriage` (557 impr, pos 5.8, 6 clicks), `ashwini-nakshatra` (99, pos 5.4) and `matching` (336, pos 4.3, 0 clicks), each already outside the band (W) |
| Band is concentrated | Top 4 pages = 5,145 of 10,424 band impressions (49%) (W) |
| One page carries the site | `/learn/rahu-mahadasha-ketu-antardasha/` = 2,010 of 11,749 impressions (17%) and 25 of 116 clicks (22%) (W); 8 of the 10 largest query rows are variants of one Rahu–Ketu phrase (query view, 8% coverage) |
| Impressions grew faster than clicks | Page-level totals: 6,022 → 11,788 impressions (+96%), 63 → 116 clicks (+84%) (P → W, trend file rows sum) |
| Position mostly unchanged where it matters | `rahu-mahadasha-ketu-antardasha` 7.6 → 7.5 despite 4.9× impressions |

## 2. Post-ship scores (issues closed in the last 28 days with `thesis:` and `metric:`)

25 closed issues since 2026-09-25 carry both fields. Only **3** have a metric that GA4/GSC can answer. Comments posted on each issue this run.

| Issue | Shipped (UTC) | Predicted | Actual in W | Verdict |
|---|---|---|---|---|
| **#276** /dasha CTA on Rahu–Ketu antardasha article | PR #342, 2026-10-14 02:02 | pages/session ≥ 1.20 (≥ 20 sessions) | **1.03** on 29 organic sessions; ≤ ~1 extra onward view in all of W | **INCONCLUSIVE** (7 of 28 days post-deploy). No lift visible. Rescore ≥ 2026-11-14 |
| **#311** title/meta on four band pages | PR #334, 2026-10-13 17:29 | CTR ≥ 1.2–1.5% on ≥ 1,500 impr, position within ±1 | **0.66%** (19 / 2,890), position 6.1–7.5. Previous window 0.79% (10 / 1,265). Body baseline 0.71% | **INCONCLUSIVE.** CTR is *below* the baseline and not above the old rate. Rescore ≥ 2026-11-13 |
| **#329** Manglik checker link | PR #344, 2026-10-14 16:07 | pages/session ≥ 1.30 on ≥ 10 sessions | **1.00** on **3** organic sessions (8 all channels) | **INCONCLUSIVE** by the issue's own rule. Rescore ≥ 2026-11-14 |
| #272 channel dimension + page dimension | PR #292, 2026-10-08 | organic sessions separate; ranking URL beside top-10 band items | Organic Search 167 of 357 sessions; page-level band present at 89% emitted coverage; **query-level 8%** | **PASS on shape; query-level half NOT MET** (a GSC ceiling) |
| #493 prioritise/discover dispatch | closed 2026-10-23 | next `agent-prioritise` run writes a non-empty file, or goes red | no run since the close (last run 2026-10-18, success; latest `measurements/prioritise/` file is dated 2026-10-08 on `origin/main`) | **UNSCORED**: event not happened |

**Misses, stated plainly.** There are no confirmed misses and no hits. But:
- **#311**: the four pages' W CTR (0.66%) is **lower** than their pre-ship CTR in the issue body (0.71%) and in P (0.79%). 7 of 28 days carry the new titles, so this is mostly the old-title rate; it is not evidence the titles failed, and it is not evidence they worked.
- **#276**: 29 organic sessions at 1.03 pages/session. If the CTA converted at even 20% the metric would be near 1.2. It has not, in the 7 post-deploy days. Cannot be separated from the pre-ship days without a per-page daily export (#490, open).
- **#329**: the metric cannot answer. The page earned **2 clicks** in W. A floor of 10 organic sessions is ~3.3× today's traffic. Unless #311 lifts clicks, this metric will read INCONCLUSIVE again in November and never say whether the link works.

Site-wide split at the deploy day (GSC `dimension: date`, not these pages): 2026-09-23 → 10-13 (21 days) 80 clicks / 8,806 impressions = 0.91%; 2026-10-14 → 10-20 (7 days) 36 / 2,943 = 1.22%. Clicks/day 3.81 → 5.14. 36 observed against ~27 expected is **under 2σ**, and the whole site moved, not the shipped pages. Not attributable to any of the three.

**The other 20 issues** (#286, #313, #316, #320, #338, #345, #349, #355, #369, #372, #373, #374, #396, #397, #400, #405, #408, #409, #442, #449) carry code/ops metrics (gate counts, run outcomes, grep counts). **Not scored this run:** the three input files cannot answer them and I did not execute their repro commands. Absence from this table is not a pass.

## 3. Confounds, named before any delta

| Confound | Evidence this run |
|---|---|
| **Concurrent ships** | `git log origin/main --since=2026-10-13` (shallow clone fetched to 2026-09-10): the set of commits touching `src/` includes #342 and #344 on 10-14, the `/learn` 12px floor (#307/#364, 10-15), `/about` rewording (#209, 10-15), service-worker stale-while-revalidate (#253, 10-20), a remedy-claim sweep touching 26 `learn/templates/routes` files (c59c750, 10-21), Surya Namaskar retirement (126abc1, 10-22). **146 commits since 2026-09-20.** Three theses landed within 15 hours of each other (#311 10-13, #276 and #329 10-14). I cannot attribute any movement to one ship. |
| **Per-page daily data absent** | GSC/GA4 daily exports are site-wide only (`dimension: date`). W cannot be split at the deploy for any shipped page (#490 open). |
| **Seasonality** | Not determined. Only 2 windows of history. `/festivals` fell 1,166 → 254 impressions with position 56.6 → 29.4 (P → W): festival-season traffic is calendar-driven here. |
| **Was the page working?** | Probed 2026-10-23: `/health` 200 (revision `bhagya-00495-7ww`, build_sha `f8696b5…`); `/learn/manglik-dosh/` 200 with new title and checker link; `/learn/rahu-mahadasha-ketu-antardasha/` 200 with `/dasha` link; `/kundli` 200; `/matching` 200. Probes show *now*, not each day of W. #253 (stale stylesheet) closed 10-20 and #266 (`/kundli` "high demand") closed 10-21, both **inside W**: `/kundli` organic sessions (10) and the rashifal pages cannot be treated as a clean read. |
| **Sample size** | 357 sessions, 116 clicks in W. Per-page counts are 3–30. Most per-page deltas are noise. Organic sessions on the scored pages (GA4, W): Rahu–Ketu 29; the four #311 pages 20 combined (8 / 7 / 3 / 2); `manglik-dosh` 3. |
| **Audience changing** | Impressions on the scored pages rose 2.3×–4.9× (P → W) with position unchanged or improved, so before/after pages/session and CTR are not like-for-like. |
| **Direct traffic quality unknown** | Direct = 159 of 357 sessions (45%). Direct landings on `/learn/*` bounce at 100% with 1.0 pages/session (`/learn/marriage-mahadasha-timing/` 7 Direct sessions at 90% bounce overall). `/` Direct = 79 sessions at 3.97 pages/session. I cannot tell owner / agent / bot traffic from visitors in this export. |

## 4. CTR outliers

Band median CTR is **0%** (77 of 109 pages have 0 clicks), so a median comparison is vacuous. Band aggregate CTR is 1.05% (W).

| Page | impr | clicks | CTR | pos | Why it is a finding (W) |
|---|--:|--:|--:|--:|---|
| **/matching** | 336 | **0** | 0% | **4.3** | 0 clicks at top-5 position; at the band's 1.05% expect ~3.5, P(0) ≈ 0.03. Page jumped from 9 impressions (P). **Filed as #508** |
| /learn/jupiter-in-10th-house-career/ | 376 | 1 | 0.27% | 6.8 | Lowest CTR among the 10 largest band pages. Covered by #311 |
| /learn/manglik-dosh/ | 471 | 2 | 0.42% | 7.5 | Covered by #311 / #329 |
| /learn/marriage-mahadasha-timing/ | 242 | 1 | 0.41% | 6.4 | Not covered by any open ship. 6 Direct, 3 AI-Assistant sessions, **0 organic** (GA4, W) |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 128 | 0 | 0% | 7.9 | Position 5.5 → 7.9, impressions 11 → 128 (P → W). Too small to act on alone |
| reference: /learn/7th-lord-placement-marriage-guide/ | 267 | 5 | 1.87% | 7.8 | Best CTR among large band pages |

## 5. Decay

Pages with ≥ 50 impressions in P. Window P → W, GSC page.

| Page | impr P → W | pos P → W | clicks P → W | Reading |
|---|---|---|---|---|
| /learn/shukra-venus-in-vedic-astrology/ | 249 → 45 (−82%) | 6.0 → 5.8 | 3 → 0 | **Real decay.** Position held at 5.8 but impressions fell by four fifths. Cause not determined from this data (demand, a SERP feature, or query mix). Too small a count to file |
| /festivals | 1,166 → 254 (−78%) | 56.6 → 29.4 | 1 → 0 | Seasonality / out of band; position better but impressions down |
| /learn/mangal-mars-in-vedic-astrology/ | 242 → 123 (−49%) | 7.1 → 7.7 | 2 → 2 | Mild |
| `/` | 52 → 100 | **3.7 → 6.1** | 3 → 6 | Position worsened by 2.4 on more impressions: likely a wider query mix, not a loss |
| /muhurat/vidyarambh | 4 → 83 | 3.8 → 7.3 | | New impressions, not decay |
| /rashifal | 35 → 91 | 7.0 → 10.1 | 0 → 0 | Position worsened by 3.1, small counts |
| 17 `/panchang/<date>` pages listed as gone / negligible | | | | Noise at 1–16 impressions each |

No ranking page lost ≥ 2 positions with ≥ 100 impressions in both windows. `/learn/kundali-matching-ashtakoot-guna-milan/` moved 5.5 → 7.9 but from 11 impressions.

## 6. Funnel

GA4, W, 357 sessions, coverage 101%, 66 distinct paths after folding query strings and trailing slashes.

| Channel | sessions |
|---|--:|
| Organic Search | 167 |
| Direct | 159 |
| AI Assistant | 25 |
| Unassigned | 8 |

| Landing (all channels) | sessions | bounce (weighted) | pages/session (weighted) |
|---|--:|--:|--:|
| `/` | 91 | 30% | 3.97 |
| /learn/rahu-mahadasha-ketu-antardasha | 34 | 44% | 1.03 |
| /kundli | 16 | 69% | 1.62 |
| /learn/griha-pravesh-muhurat-2026-2027 | 14 | 64% | 1.00 |
| /learn/sade-sati | 13 | 31% | 1.15 |
| /muhurat/griha-pravesh | 9 | 44% | 2.11 |
| /learn/planets-in-7th-house-marriage | 7 | 57% | 3.43 |

- Organic landings on `/learn/*` average ~1.0 pages/session: readers read one article and leave. The only organic landings with > 2 pages/session are `/muhurat/griha-pravesh` (9 sessions, 2.11) and `/learn/planets-in-7th-house-marriage` (5 organic of 7, 3.43) and `/learn/kaal-sarp-dosh` (5 sessions, 4.8): small samples.
- `/kundli` as a landing has 16 sessions with 69% bounce. Whether visitors submit the form is **not determinable**: this export has no event data (#272, #490 context). Form→result→second-page steps cannot be measured from these files.
- **Anomaly:** 2026-10-16 = 42 sessions / 38 users, against a W daily median ~11 (GA4 daily). Which channel or landing caused it cannot be determined from these files. It inflates the post-deploy 7-day average: 18.4 sessions/day (129 / 7) against 11.0 in the 21 days before (230 / 21); excluding 10-16 it is 14.5 (87 / 6). A site-wide "traffic rose after the ships" read is mostly one day plus a smaller rise.

## 7. What I could not determine, and the measurement that would settle it

| Question | Why not | The one measurement |
|---|---|---|
| Whether #276 / #311 / #329 worked | Window not elapsed; no per-page daily | Per-page × per-day GSC and GA4 export (#490), or wait until 2026-11-13/14 |
| Whether the band moved on *queries* | Query view = 8% of impressions; top-10 are mostly one phrase | Not recoverable from GSC. Use pages as the unit and say so in OBJECTIVE.md (chief's call, not mine) |
| What caused 2026-10-16's 42 sessions | No date × channel or date × landing | GA4 `date × sessionDefaultChannelGroup` |
| Whether Direct `/learn/*` traffic is human | No bot/internal-traffic filter visible | GA4 internal-traffic filter status, or hostname/user-agent breakdown |
| Whether `/matching`'s 0 clicks is a snippet problem | No SERP access, no query for that page | GSC query × page for `/matching` (not exportable at the volume Google reports) |
| The 20 code/ops-metric issues | Outside these files | Run each issue's own `repro:` |

## 8. Filed and posted

| Action | Reference |
|---|---|
| Issue filed, Evidence Block validated (`verify_issue_evidence.py 508` → PASS) | #508 `/matching` CTR outlier |
| Score comments posted | #276, #311, #329, #272, #493 |
| Not filed | Shukra/Venus decay (45 impressions, cannot support a hypothesis); Direct `/learn/*` bounce (cannot distinguish bots); 2026-10-16 spike (cause unknowable from these files) |

*analyst, read-only. No code, template, content or BACKLOG.md edited.*
