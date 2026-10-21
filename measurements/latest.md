# Analyst report — run of 2026-10-21

**Window W** = 2026-09-21 → 2026-10-18 (28 days; GSC and GA4 both exclude the last 3 days). Every number below is for W unless its row names another window. Files read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. Nothing was re-fetched.

Two other kinds of number appear, each labelled where it occurs:
- **baseline(issue)** — the "before" figure written in an issue body. It is quoted as a claim the issue made, not as something fetched this run.
- **live probe** — `curl` against shubhagya.com on 2026-10-21.

## 0. Coverage, read before any number

| export | dimension | coverage | rows | truncated | note |
|---|---|---|---|---|---|
| GSC band (`gsc-band.json`) | page | `coverage_pct` 100% of 11,481 impressions; **emitted** 87% (10,037 impr) | 107 pages at pos 6–20 | false | position = the page's **average** across its queries, not any query's |
| GSC all (`gsc-all.json`) | page | 100% (11,518 rows vs 11,481 total) | 124 pages | false | 110 clicks in total |
| GA4 (`ga4.json`) | landing × channel | 101% of 341 sessions | 100 rows, 71 landings | false | 71 landings include query-string and trailing-slash variants; folded to 67 paths below |

**The objective cannot be measured as written.** OBJECTIVE.md says *"ten highest-impression queries"*. These exports are by page, and query-level GSC covers only ~9% of impressions (`fetch_gsc.py` docs). Every "band" figure below is a **page** average. A page at 6.0 can rank 1 for one query and 15 for another.

## 1. The band against OBJECTIVE.md (W)

| measure | value (W) |
|---|---|
| Site impressions / clicks (all pages) | 11,481 / 110 (CTR 0.96%) |
| Pages at avg position 6–20 | 107 pages, 10,037 impr (87% of impressions), 98 clicks, pooled CTR 0.98% |
| Pages at avg position < 6 | 15 pages, 1,237 impr, 12 clicks, pooled CTR 0.97% |
| Pages at avg position > 20 | 2 pages, 244 impr |
| Organic Search sessions (GA4) | 159 of 341 (47%). Direct 154, AI Assistant 23, Unassigned 7 (sum 343 vs 341 reported: the coverage note says 101%) |

**Objective status.** Of the ten highest-impression pages in W, 8 sit in 6–20. Only `/matching` (avg 4.3) is inside the top 5. `/learn/planets-in-7th-house-marriage/` is at 5.8, not top-5 by the literal test. I have no prior-window figure fetched this run, so I **cannot say whether the band moved**. Baseline(issue #311) was 99 pages / 7,939 impr / 85 clicks / 1.07% CTR for 2026-09-09→10-06. That window **overlaps W by 16 of 28 days**, so the two are not independent and I report no delta.

### Top of the band, ranked by `band_opportunity` (W)

| # | page | impr | clicks | CTR | avg pos | opp. |
|---|---|---:|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,977 | 25 | 1.26% | 7.5 | 93.6 |
| 2 | /learn/debilitated-sun-career/ | 1,187 | 5 | 0.42% | 6.0 | 66.2 |
| 3 | /learn/sade-sati/ | 1,046 | 10 | 0.96% | 6.2 | 52.8 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 845 | 8 | 0.95% | 7.1 | 42.7 |
| 5 | /learn/manglik-dosh/ | 469 | 2 | 0.43% | 7.5 | 26.1 |
| 6 | /learn/panch-mahapurush-yoga/ | 418 | 2 | 0.48% | 6.9 | 23.1 |
| 7 | /learn/jupiter-in-10th-house-career/ | 361 | 0 | 0.00% | 6.8 | 21.7 |
| 8 | /learn/career-during-sade-sati/ | 399 | 5 | 1.25% | 7.0 | 18.9 |
| 9 | /learn/marriage-mahadasha-timing/ | 242 | 1 | 0.41% | 6.5 | 13.5 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 259 | 5 | 1.93% | 7.9 | 10.5 |

The first 10 pages carry 7,203 impressions, 63% of all site impressions.

## 2. Post-ship scoring (issues closed 2026-09-23 → 2026-10-21 with `thesis:` and `metric:`)

**None of the three user-facing ships can be scored yet.** Their 28-day post-deploy windows have not elapsed, and W holds only 4–6 post-deploy days. This is "not enough data yet". It is **not** a pass.

Deploy time is assumed to equal merge time. I did not verify the build.

| issue | shipped (merge, UTC) | post-deploy days inside W | metric's own window ends | verdict |
|---|---|---:|---|---|
| #311 title/meta rewrite, 4 band pages | 2026-10-13 17:29 (PR #334) | ≤ 6 of 28 | 2026-11-10; add the 3-day lag → rescore ≥ 2026-11-13 | **INCONCLUSIVE — no sign of lift, direction negative but inside noise** |
| #276 `/dasha` CTA on Rahu–Ketu article | 2026-10-14 02:02 (PR #342) | ≤ 5 | 2026-11-11; rescore ≥ 2026-11-14 | **INCONCLUSIVE — no sign of lift** |
| #329 `/manglik-check` link on Manglik article | 2026-10-14 16:07 (PR #344) | ≤ 5 | 2026-11-11; rescore ≥ 2026-11-14 | **INCONCLUSIVE — 3 organic sessions, below the issue's own floor of 10** |

### #311 — predicted vs actual

| page | baseline(issue) 2026-09-09→10-06: impr / clicks / CTR / pos | W: impr / clicks / CTR / pos |
|---|---|---|
| rahu-mahadasha-career-problems | 810 / 6 / 0.74% / 7.5 | 845 / 8 / 0.95% / 7.1 |
| debilitated-sun-career | 773 / 5 / 0.65% / 6.0 | 1,187 / 5 / 0.42% / 6.0 |
| manglik-dosh | 363 / 3 / 0.83% / 7.9 | 469 / 2 / 0.43% / 7.5 |
| jupiter-in-10th-house-career | 305 / 2 / 0.66% / 6.8 | 361 / 0 / 0.00% / 6.8 |
| **combined** | **2,251 / 16 / 0.71% / —** | **2,862 / 15 / 0.52% / —** |

| | predicted | actual (W) |
|---|---|---|
| combined CTR | ≥ 1.5% on ≥ 1,500 impr, avg pos within ±1 (the issue's metric) | 0.52% on 2,862 impr. Position stayed within ±1 on all four, and the impressions floor is met |
| | the PR #334 body states a *different* bar: ≥ 1.2% on ≥ 2,000 impr | still missed under either bar |

- **Direction.** CTR is lower than baseline(issue), 0.52% vs 0.71%. Against the baseline rate, 2,862 impr would give ~20.3 clicks and W shows 15 (Poisson P(≤15) ≈ 0.14). That is **not significant**, and I do not call it a regression.
- **Dilution.** At most 6 of the 28 days are post-deploy, so W is ≥ 78% old titles. Impressions rose 27%, but the windows overlap, so I cannot say whether that rise is new reach or the same pages seen again.
- **Live probe.** All four new titles are serving (HTTP 200). For example, `/learn/debilitated-sun-career/` → "Debilitated Sun: Why Authority at Work Feels Borrowed", and `/learn/jupiter-in-10th-house-career/` → "Jupiter in 10th House: Hamsa Yoga or a Stalled Career?". The change reached production, so a miss would not be an artefact of an undeployed change.
- **The premise looks weaker than it did.** #311 rested on a reference page at 2.05% CTR, pos 7.5 (baseline(issue)). In W that same page, `/learn/rahu-mahadasha-ketu-antardasha/`, is **1.26% at pos 7.5**. Its title was not changed by #311, and its CTA was added at ≤ 5 days of W. The benchmark that made the four pages look broken fell by 39% with no change to its title. The "gap to 2.05%" was largely one page's good fortnight. The issue's own "Not claimed" section flagged the reference as possibly the outlier, and W supports that.
- **Metric ambiguity.** The issue and the PR body state different pass bars, so whichever bar the rescore uses must be stated first. I used the issue's, as it is the record of the thesis.

### #276 — Rahu–Ketu article, `/dasha` CTA

| | predicted | actual (W) |
|---|---|---|
| `pages_per_session`, Organic Search, landing `/learn/rahu-mahadasha-ketu-antardasha/` | ≥ 1.20 (pass); still 1.0 → thesis false; inconclusive if sessions < 20 | **1.04 on 28 sessions** (bounce 28.6%). Direct on the same landing: 5 sessions, pps 1.00 |

- baseline(issue) was 1.0 on 29 sessions. Sessions clear the issue's floor of 20, but the CTA existed for ≤ 5 of the 28 days, so 1.04 is mostly the *pre*-CTA population. I cannot attribute it.
- Live probe: `/dasha` links are present on the page (3 hrefs). I did not confirm which one is the new CTA or its position.
- Pass is ≥ 1.20 on the 28 days *after* deploy. If the post-deploy days alone ran at 1.2 against 23 days at 1.0, W would read ≈ 1.04 — **W cannot distinguish pass from fail.**

### #329 — Manglik article, checker link

| | predicted | actual (W) |
|---|---|---|
| `pages_per_session`, Organic Search, landing `/learn/manglik-dosh/` | ≥ 1.30 on ≥ 10 sessions = pass; < 10 = inconclusive, not a pass | **1.00 on 3 organic sessions**, bounce 100%. Direct: 5 sessions, pps 1.00 |

- Below the issue's own floor: inconclusive by its own terms. This page also has 469 impr at avg pos 7.5 and 2 clicks. Traffic is too thin for a pages-per-session thesis to be scoreable in any 28-day window at the current rate.
- Live probe: `/manglik-check` links are on the page (4 hrefs). Placement not confirmed.

### #272 — measurement export shape

| | predicted | actual |
|---|---|---|
| organic sessions reported as a separate 28-day number | a separate column | **PASS.** `ga4.json` carries `sessionDefaultChannelGroup`: Organic Search 159 sessions (W) |
| ranking URL listed beside band entries | `page` populated | **PASS.** `gsc-band.json` has `dimension: page`, 107 rows |

- The thesis asked for ranking URLs beside the top-10 band *queries*. The exports are by page and the query view is ~9% coverage. The shape is met and the query-level goal is not.

### Closed issues carrying `thesis:`/`metric:` that GA4/GSC cannot score

I listed them and did not comment on each. None has a metric that these exports can measure. Posting 20 "not scoreable" comments would add noise. These need their own checks, which I did not run this cycle.

| issue | closed | metric is about | scoreable from GA4/GSC? |
|---|---|---|---|
| #449, #446, #442, #405, #400, #396, #374, #373, #372, #369, #355, #349, #345, #338, #316, #313, #286, #320 | 2026-10-14 → 2026-10-21 | gates, repo hygiene, workflow behaviour, admin pages, token telemetry | no |
| #408, #409 | 2026-10-18, 2026-10-20 | server-error and autoescape code paths | no |
| #397 | 2026-10-20 | copy on `/matching` (Nadi panel strings 3 → 0) | no — a grep/render check, not a traffic metric |

## 3. Confounds

| confound | state | consequence |
|---|---|---|
| Other ships in W | **Not enumerable here.** The clone is shallow (`git rev-parse --is-shallow-repository` = true; `git log origin/main` shows 1 commit). `gh pr list` shows 62 PRs merged 2026-09-21→10-18. Most are infra, loops, gates and admin pages. User-visible ones that could touch these pages' traffic: PR #334 (4 titles; its `chart.py` change is a comment only), #342, #344 (the CTAs), #303 (rashifal serving), #299 (Hindi rashifal), #427 (service-worker `/static/` SWR, 2026-10-20), #451 (remedy claims retired from reader-facing pages, 32 files, 2026-10-21) | #451 merged after W ended, and #427 on its last day, so neither can have moved W. #334/#342/#344 are the treatments themselves. **Concurrent *content* ships in W that I could not rule out** — I did not read each of the other merged PRs' diffs |
| #253 — stale stylesheet to returning visitors | Open from 2026-09-02, closed 2026-10-20 — covers all of W | Returning-visitor engagement in W (pps, bounce) was measured on pages that may have rendered unstyled or mis-styled. Any engagement delta, #276 and #329 included, inherits this |
| #266 — `/kundli` "high demand" (Groq 413) | Reported 2026-09-05. A 2026-10-13 capacity comment put the worst natal request at 85% of the 8,000 TPM bucket. Closed 2026-10-21 as "does not reproduce". W-state uncertain | `/kundli` landings (16 sessions: 10 organic at pps 2.0, 6 direct at pps 1.0) may have hit failures. **I did not measure the failure rate in W.** Do not read `/kundli` engagement as the funnel's real rate |
| Page reachable now | Live probes 2026-10-21: five `/learn` pages and `/matching` all HTTP 200; `/health` → revision `bhagya-00489-w8x`, `build_sha` `d29c224…` | That's *now*, not W. `build_sha` does not equal local HEAD (71b44fe), but HEAD is a measurements-only commit that does not deploy, so this is not by itself a discrepancy. I cannot confirm which commit `d29c224` is (shallow clone) |
| Seasonality | **Not determined.** I did not verify festival dates against a source, so I assert nothing about Navratri/Dussehra or Pitru Paksha. `/learn/griha-pravesh-muhurat-2026-2027` (14 sessions) and `/muhurat/griha-pravesh` (9) are muhurat-season pages | Muhurat landings are likely seasonal. The four #311 pages and the two CTA pages are evergreen, so seasonality is probably a smaller driver for them. "Probably" is an inference, not a measurement |
| Sample size | 341 sessions and 110 clicks in W. The largest organic landing has 28 sessions. Eighteen of the top 25 landings have ≤ 8 sessions | Most per-page deltas here are noise. Pages-per-session on a landing with under ~20 sessions is not reportable |
| Direct traffic on deep pages | 154 of 341 sessions are Direct. Deep `/learn` pages show Direct sessions at bounce 100% (manglik-dosh 5, ketu-antardasha 5) | The 'Direct' label on deep content pages is suspicious — possibly untagged referrals or bots. Cause **not determined**; it affects any "organic share" read |

## 4. CTR outliers and decay

**Reference rate.** Pooled CTR for the 6–20 band is 0.98% (98 / 10,037) and the median of the band pages with ≥ 100 impressions is 0.82%. Site-wide CTR at position < 6 is 0.97% — **no better than the band.** That is odd: page-average position probably hides wide spread, so position is a weak predictor on this site.

| page (W) | impr | clicks | CTR | avg pos | read |
|---|---:|---:|---:|---:|---|
| /matching | 325 | 0 | 0% | 4.3 | Top-5 average, zero clicks. At 0.97%, P(0 clicks) ≈ 4%. Weak evidence. Live title is long: "Free Kundli Matching (Ashtakoot Guna Milan) — 8 Kootas + Manglik + Nadi Cancellation Rules". GA4 shows 0 organic sessions (5 Direct, 2 AI Assistant) |
| /learn/jupiter-in-10th-house-career/ | 361 | 0 | 0% | 6.8 | At 0.98%, P(0) ≈ 3%. Title changed by #311 within the window |
| /learn/debilitated-sun-career/ | 1,187 | 5 | 0.42% | 6.0 | Expected ≈ 11.6 clicks at the pooled rate; P(≤5) ≈ 2.6%. Largest unexplained shortfall on the site. Only ≤ 6 days carry the new title |
| /learn/kaal-sarp-dosh/ | 121 | 3 | 2.48% | 6.2 | Best CTR among band pages with ≥ 100 impr. Small count, so not a template to copy |
| /learn/7th-lord-placement-marriage-guide/ | 259 | 5 | 1.93% | 7.9 | Above band rate at a *worse* position |

**Decay: not determinable this run.** No prior-window per-page GSC file exists in the inputs. `fetch_gsc.py` has `--by date` and `--trend`, and `fetch_ga4.py` has `--daily`, so the one measurement that settles #311 and the CTAs is a day-split re-fetch. I was told not to call the APIs.

**Funnel: not determinable.** The exports carry landing, bounce and pages per session, but no step events. These are the only form-adjacent landings, with the usual small-sample caveat:

| landing (W) | channel | sessions | bounce | pps |
|---|---|---:|---:|---:|
| /kundli | Organic Search | 10 | 50.0% | 2.00 |
| /kundli | Direct | 6 | 100% | 1.00 |
| /matching | Direct | 5 | 100% | 1.00 |
| /matching | AI Assistant | 2 | 0% | 4.00 |

## 5. Issues filed

**None.** No finding both needs an action and meets the Evidence Block bar:
- #311 / #276 / #329 need *time*, not a new issue; the rescore dates are below.
- The `/matching` and Jupiter zero-click readings are 3–4% tail probabilities on ~300–360 impressions. Filing "fix the title" on that would be the activity-not-progress the objective warns against.
- The Direct-traffic oddity and the seasonality gap are things I could not determine, and I would not file an issue that asserts a cause I did not measure.

## 6. What I could not determine, and the measurement that settles it

| unknown | single measurement that settles it |
|---|---|
| Did #311's titles move CTR? | After 2026-11-13: `fetch_gsc.py --by date` over 2026-10-14→2026-11-10, filtered to the four pages, versus the same-length window before 2026-10-13 |
| Did the #276 / #329 CTAs lift onward visits? | After 2026-11-14: `fetch_ga4.py --daily`, the two landings, Organic Search, post-deploy days only. Also needs ≥ 20 / ≥ 10 sessions to count |
| Did the band move this quarter? | A stored prior-window page-level export to diff against W. `measurements/` holds daily files, but I did not read them (a number I did not fetch this run is not reportable) |
| Was `/kundli` failing during W? | `events.py` error/fallback counts for 2026-09-21→10-18. Event retention is 30 days, so the start of W (2026-09-21) is already at or past the edge as of this run, and the rest ages out daily |
| What else shipped to these pages' content in W? | A full-depth clone (`git fetch --unshallow`) and `git log --since=2026-09-21 -- src/astro_ai/templates/learn src/astro_ai/learn_registry.py` |
| Why do deep `/learn` pages show Direct sessions at 100% bounce? | GA4 session-source/medium split and a bot-filter check on those landings |
| The objective as written (ten highest-impression *queries*) | Query-level GSC has ~9% coverage; Google withholds the rest and it cannot be recovered. The objective is measurable only at page level unless it is rewritten, which is `chief`'s call, not mine |

## 7. Summary

| | |
|---|---|
| Scored | 3 user-facing ships + 1 measurement ship |
| Hits | 1 — #272 (export shape) |
| **Misses** | **0 confirmed.** #311's CTR is 0.52% against a 1.5% bar. The window is ≥ 78% pre-deploy, so this is neither a miss nor a hit |
| Inconclusive | 3 — #311, #276, #329 |
| Not scoreable from GA4/GSC | 21 infra/gate/security/copy issues |
| Rescore due | #311 ≥ 2026-11-13; #276 and #329 ≥ 2026-11-14 |
| Biggest fact in the file | The reference page that justified #311 fell from 2.05% (baseline(issue)) to 1.26% in W with an unchanged title. The CTR gap that motivated the experiment may be mostly regression to the mean |
