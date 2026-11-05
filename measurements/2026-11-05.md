# Analyst report — 2026-11-05 run

**Window for every number unless stated: W = 2026-10-06 → 2026-11-02** (28 days; the last 3 days are excluded because GSC and GA4 are not final).
Read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. Nothing was re-fetched.
Issue-body figures are labelled "(issue body)"; every other number was read from those three files.

## 0. Coverage — read before any number

| export | dimension | coverage | truncated | rows |
|---|---|---|---|---|
| `gsc-all.json` | `page` | 100% of 18,088 impressions (`rows_impressions` 18,118) | no | 137 pages |
| `gsc-band.json` | `page`, position 6–20 | whole fetch 100%; **emitted** 102 pages = 14,898 impressions = **82%** | no | 102 pages |
| `ga4.json` | `landingPagePlusQueryString` × `sessionDefaultChannelGroup` | 100% of 508 sessions (`rows_sessions` 510) | no | 118 landing × channel rows, 79 landings |

- **Everything GSC here is pages, not queries.** A page's `position` is its average across its queries, not any query's rank. OBJECTIVE.md is written in queries ("ten highest-impression queries"); this run cannot measure that wording, only its page analogue. No `--by query` export was read (that view covers ~9% of impressions per the analyst brief).
- **GA4 rows are landing × channel.** I summed sessions across channels per landing and weighted pages/session by sessions. `?hl=en-IN` is folded into its path.
- Totals in W: **18,088 impressions, 197 clicks (1.09% CTR)** in GSC; **508 sessions** in GA4.

## 1. The 6–20 band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page analogue below.

| measure (GSC `page`, W) | value |
|---|---|
| pages in the band (position 6.0–19) | **102**, 14,898 impressions (82% of 18,118), **157 clicks**, band CTR **1.05%** |
| the ten highest-impression pages | 12,161 impressions (67% of 18,118), 121 clicks |
| of those ten, at position ≤ 5.0 | **0 of 10** — best is 5.8 (`career-during-sade-sati`), then 5.9 (`gochar-2026-planetary-transits`) |
| of those ten, in the band (6.0–19) | 8 of 10, positions 6.4–7.3 |
| pages at position ≤ 5.0 at all | 15 pages, 446 impressions, 4 clicks |

**Reading: the objective is not met, and no page analogue of it moved in a measurable way this run.** I have only one window in these files, so I cannot say the band moved or stood still. See §5 for what would settle that.

### Band, ranked by `band_opportunity` (file's own score), top 12

| # | page | impressions | clicks | CTR | position | opportunity |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,091 | 36 | 1.16% | 6.8 | 149.5 |
| 2 | /learn/debilitated-sun-career/ | 2,063 | 12 | 0.58% | 6.6 | 111.8 |
| 3 | /learn/sade-sati/ | 1,852 | 12 | 0.65% | 6.5 | 99.1 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,049 | 6 | 0.57% | 7.0 | 56.9 |
| 5 | /learn/rahu-mahadasha-career-problems/ | 883 | 16 | 1.81% | 6.4 | 37.0 |
| 6 | /learn/7th-lord-placement-marriage-guide/ | 765 | 9 | 1.18% | 7.3 | 36.9 |
| 7 | /learn/panch-mahapurush-yoga/ | 560 | 7 | 1.25% | 6.8 | 26.6 |
| 8 | /learn/manglik-dosh/ | 494 | 4 | 0.81% | 7.1 | 25.6 |
| 9 | /learn/marriage-mahadasha-timing/ | 353 | 1 | 0.28% | 6.0 | 20.2 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 435 | 9 | 2.07% | 6.5 | 17.1 |
| 11 | /learn/mangal-mars-in-vedic-astrology/ | 288 | 2 | 0.69% | 7.3 | 15.3 |
| 12 | /learn/kundali-matching-ashtakoot-guna-milan/ | 202 | 0 | 0.00% | 7.6 | 12.1 |

The top five rows hold 8,938 impressions = 60% of the emitted band. Five pages carry the band; the other 97 are small.

## 2. Post-ship scores — issues closed in the last 28 days with a `thesis:` and a `metric:`

Comments were posted this run on #272, #276, #311, #329, #426, #685, #570, #514, #515.

**Misses first.**

| issue | shipped | predicted (`metric:`) | actual, W | verdict |
|---|---|---|---|---|
| **#311** title/meta rewrite on 4 band pages | PR #334, 2026-10-13 17:29Z | combined CTR **≥ 1.5%** on ≥ 1,500 impressions, position within ±1 | **38 / 4,489 = 0.85%**; weighted position 6.71 vs 6.95 (issue body) | **MISS so far.** 3 of 4 pages show no lift: 22 / 3,606 = 0.61% vs 10 / 1,441 = 0.69% before (issue body). One page (`rahu-mahadasha-career-problems`, 16 clicks) carries all the movement |
| **#329** link to `/kundli` in Manglik "How to check" | PR #344, 2026-10-14 16:07Z | pages/session ≥ 1.30 on ≥ 10 Organic sessions | 1.00 on **4** Organic sessions | **INCONCLUSIVE** — below the issue's own floor, and the sample cannot reach 10 at 4 per 28 days. pages/session cannot score this issue |

**Provisional.**

| issue | shipped | predicted | actual, W | verdict |
|---|---|---|---|---|
| **#276** "find your Ketu antardasha dates" CTA | PR #342, 2026-10-14 02:02Z | pages/session ≥ 1.20 for this landing, ≥ 20 sessions | **1.34** on 52 sessions (Organic 39 sessions at 1.46; Direct 12 at 1.00) | **PROVISIONAL, not attributable.** Bar met on W, but ~8 of W's days are pre-deploy, the mix is 75% Organic (which reads higher than Direct), and W cannot be split by day. Not claimed as a hit |

**Not scoreable yet / not determinable.**

| issue | why | earliest clean read |
|---|---|---|
| #426 (Sade Sati/Gochar date correction, PR #673, 2026-11-02 12:18Z) | deploy on the last day of W; guard baseline in W: 1,852 impressions, position 6.5 | post-only window closes 2026-11-30, readable ~12-03 |
| #685 (Sade Sati title naming Moon signs, PR #690, 2026-11-03 10:58Z) | after W. W reproduces the issue's baseline: 12 / 1,852 = 0.65% vs 0.63% (issue body) | window 2026-11-04 → 12-01, readable ~12-04 |
| #570 (`cta_click` event, PR #688, 2026-11-03 04:42Z) | `ga4.json` carries no event dimension; nothing to read | needs a GA4 export with `eventName` + `from_path`/`to_path`, from 2026-11-04 |
| #514 (rashifal fields, closed 2026-11-01), #515 (nightly rashifal, 2026-10-24) | email re-open rate is not in the exports; organic half reads **0 Organic sessions** to `/rashifal*` in W (4 sessions total: Direct 3, AI Assistant 1); GSC 213 impressions, 0 clicks across 15 rashifal pages | #515 window closes 2026-11-21 |
| #272 (channel + page dimensions) | **PASS on shape** (organic is a separate number: 262 of 508 sessions, 51.6%). The query-level half is **not met** this run | n/a |

**Not scored by me — the `metric:` is not a GA4/GSC quantity:** #313, #316, #320, #338, #345, #349, #355, #357, #358, #362, #369, #372, #373, #374, #396, #397, #398, #400, #405, #406, #407, #408, #409, #431, #432, #442, #449, #450, #493, #495, #510, #543, #602, #604, #607, #621. Their metrics are repo counts, test results or `/admin/ops` readings. Reading them was not asked of this run and the data was not in the three files. (#286 carries a `thesis:` fragment and a `metric:` fragment too; neither is a traffic quantity.)

## 3. Confounds

| confound | finding |
|---|---|
| Concurrent ships (`git log` is a 1-commit shallow clone here, so I used merged PRs from `gh pr list --search "merged:>=2026-10-06"`; titles only, **file lists not diffed**) | Learn/topic edits inside W: #512, #530 (remedy pages), #556, #579, #587, #590 (Manglik), #572 (Sade Sati phases), #658 (2026-11-01) and #680 (2026-11-02) (route learn articles to tools), #673 (Sade Sati/Gochar dates). Also #427 (service-worker stale-while-revalidate for `/static/`, 2026-10-20) and #516/#519 (rashifal, 2026-10-24). **No title-only change can be attributed to #311, #276 or #329 alone** |
| Seasonality | **Not determined for the band pages.** W is the run-up to Diwali (2026-11-08 per CLAUDE.md), which lifts festival/muhurat pages (e.g. `/muhurat/griha-pravesh`, `/learn/griha-pravesh-muhurat-2026-2027`), not obviously the career/dasha pages that dominate the band. No prior-year data exists in the files |
| Page working? | **Production reachability NOT checked:** `curl https://shubhagya.com/health` from the runner timed out with no HTTP response (exit 28, code 000). That is a runner limitation or an outage — I cannot tell which. #253 (stale stylesheet) was addressed by #427 on 2026-10-20 and is inside W only partly. #266 (Groq TPM) affects LLM pages, not the `/learn` pages scored here |
| Sample size | Band pages have 4–36 clicks each in W. Differences under ~0.5 CTR points on a page are noise. GA4 organic landings: 52 distinct, the largest 39 sessions |
| Window overlap | Every score window W overlaps both its before and after periods for #276, #311, #329 (7–8 pre-deploy days in W). No per-landing × per-day export exists, so I cannot cut W at the deploy |
| Measurement hygiene | **14 of 508 GA4 sessions land on `/admin/*`** (11 + 1 + 1 `/admin/ops`, 1 `/admin/activity`) and **17 on `(not set)`** (11 labelled Organic, pps 0.0). `/` has 79 Direct sessions on 35 users at 3.59 pages/session. Internal and unattributed traffic is in the 262 "Organic" and 222 "Direct" figures; I cannot size it further from these files |

## 4. CTR outliers (against the band's own distribution)

Band reference: aggregate CTR 157 / 14,898 = **1.05%**; median page CTR (pages with ≥ 100 impressions) **0.81%**.

| page (W) | impressions | clicks | CTR | position | status |
|---|---:|---:|---:|---:|---|
| /learn/debilitated-sun-career/ | 2,063 | 12 | 0.58% | 6.6 | **#311 shipped a title change; no lift read** |
| /learn/sade-sati/ | 1,852 | 12 | 0.65% | 6.5 | #685 shipped 2026-11-03, after W |
| /learn/jupiter-in-10th-house-career/ | 1,049 | 6 | 0.57% | 7.0 | **#311 shipped; no lift read** |
| /learn/marriage-mahadasha-timing/ | 353 | 1 | 0.28% | 6.0 | noise: at 0.81% the expected clicks are 2.9, observed 1, P(≤1) ≈ 0.2 |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 202 | 0 | 0.00% | 7.6 | noise: expected 1.6, observed 0, P ≈ 0.2 |
| /rashifal | 151 | 0 | 0.00% | 8.7 | noise at this size |
| /matching | 346 | 2 | 0.58% | **4.3** | already top-5 and a poor CTR; #696 shortened its title/meta on 2026-11-03, after W — nothing to read yet |

Two pages (`debilitated-sun-career`, `jupiter-in-10th-house-career`) were the headline of #311 and **are still the two worst large CTR outliers in the band after the ship**. That is the plainest fact in this report: the title rewrite did not close their gap, and 3,112 impressions sit on the two of them (a 1.5% CTR would be ~47 clicks; they got 18).

## 5. What I could not determine, and the single measurement that settles each

| gap | measurement |
|---|---|
| **Decay / movement of the band.** One window in the files, so no page can be shown to have gained or lost position | `fetch_gsc.py --by page` over the prior 28 days (2026-09-08 → 2026-10-05) beside this window — or the archived per-window exports under `measurements/` |
| **Objective in query terms** | `fetch_gsc.py --by query` over W, joined to the top-10 queries; covers ~9% of impressions, so it can rank at most a partial list |
| **Whether #276 / #329 links get used** | `cta_click` events from 2026-11-04 → 2026-12-01, by `from_path` / `to_path` (#570 shipped the event; no export reads it yet) |
| **Clean pre/post for #311, #276, #329** | post-only window from 2026-10-14, closes 2026-11-10, readable ~2026-11-13; needs a per-landing × per-day export (#490) to cut W at the deploy |
| **Reachability of production** | `/health` returned no response from the runner. A run from a network that can reach it |
| **Size of internal / unattributed traffic** | a GA4 export with `hostName` or an internal-traffic filter; today 14 `/admin/*` + 17 `(not set)` sessions are visible out of 508 |
| **Funnel (landing → form → result → second page)** | cannot be computed: no event or path-sequence dimension. Only pages/session by landing is available (Organic `/kundli` 12 sessions, pps 2.33, bounce 41.7%; Direct `/kundli` 13 sessions, pps 1.15, bounce 92.3%; Direct `/matching` 10 sessions, 90% bounce; Direct `/numerology` 9 sessions, 100% bounce) — samples of 9–13 sessions, directional only |

## 6. Issues filed

**None.** No finding this run is both new and actionable:

- The band's outliers with enough impressions to matter (#311's pages, `sade-sati`) already have an issue or a shipped fix being scored; the small-sample outliers are inside Poisson noise.
- #311 is a miss so far, but its clean post-only window is not readable until ~2026-11-13; filing a reversal now would be acting on a window that mixes 7 pre-deploy days. Re-score then. If it still reads below 1.5% on the three non-career pages, the finding is that **title/meta rewrites are not the lever for those pages**, and that is the one to file.
- Reachability, internal traffic and the missing per-day export are measurement gaps owned by existing issues (#490) or by the runner's network; no new evidence block could be completed for them from these files.
