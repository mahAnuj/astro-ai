# Analyst report — run of 2026-10-27

**Window W for every number below: 2026-09-27 → 2026-10-24** (28 days; the exports exclude the last 3 days).
Files read this run, and only these: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`.

| Export | Dimension | Coverage | Truncated |
|---|---|---|---|
| GSC (`gsc-all`) | `page` | rows = 12,284 impressions vs property total 12,251 (100%); 125 pages | no |
| GSC (`gsc-band`) | `page`, position 6–20 | prints 102 pages, 11,109 impressions = 91% of the fetch (`emitted_coverage_pct`); 120 of 128 clicks | no |
| GA4 | `landingPagePlusQueryString` × `sessionDefaultChannelGroup` | 397 of 397 sessions (100%); 111 rows, 74 raw landings → 69 distinct paths after folding query strings/trailing slashes | no |

**Read this first.** The GSC exports are `--by page`. A "position" below is a page's **average across its queries**, not any one query's. The objective is stated in *queries*. **I cannot measure it as written** — no query-level data was provided this run.

---

## 1. The band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Page-level proxy: the ten highest-impression **pages** and their average position, W.

| # | Page | Impressions | Clicks | CTR | Avg position | Gap to ≤5.0 |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,244 | 29 | 1.29% | 7.2 | 2.2 |
| 2 | /learn/debilitated-sun-career/ | 1,409 | 7 | 0.50% | 6.2 | 1.2 |
| 3 | /learn/sade-sati/ | 1,277 | 8 | 0.63% | 6.3 | 1.3 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 782 | 10 | 1.28% | 6.8 | 1.8 |
| 5 | /learn/planets-in-7th-house-marriage/ | 495 | 6 | 1.21% | 5.8 | 0.8 |
| 6 | /learn/panch-mahapurush-yoga/ | 493 | 3 | 0.61% | 6.9 | 1.9 |
| 7 | /learn/manglik-dosh/ | 461 | 2 | 0.43% | 7.6 | 2.6 |
| 8 | /learn/career-during-sade-sati/ | 414 | 4 | 0.97% | 6.8 | 1.8 |
| 9 | /learn/jupiter-in-10th-house-career/ | 357 | 1 | 0.28% | 6.9 | 1.9 |
| 10 | /matching | 347 | 1 | 0.29% | **4.4** | already in |
| | **Top-10 total** | **8,279** | **71** | **0.86%** | | |

| Measure (W) | Value |
|---|---|
| Top-10 pages already averaging ≤ 5.0 | **1 of 10** (`/matching`, 4.4) |
| Top-10 share of all impressions (8,279 / 12,284 rows) | 67.4% |
| Band pages (6–20) | 102 pages, 11,109 impressions, 120 clicks, impressions-weighted CTR 1.08% |
| Band pages with ≥100 impressions | 23 pages = 9,640 impressions; median CTR 0.83% |
| Top 4 band pages' share of band impressions | 5,712 / 11,109 = 51% |
| Band pages with <10 impressions | 41 of 102 (noise; ignore for ranking) |
| Band positions | 98 of 102 pages sit at 6–11; the band is "one to two places off" for nearly everything |

**Movement against the objective: not determinable from these three files.** They hold one window, so there is no earlier band to compare with. The daily and trend exports exist in `/tmp` (`gsc-trend-page.json`, `gsc-daily.json`, `ga4-daily.json`) but were outside the files I was told to read, and I did not use them.

### Band — ranked by the script's `band_opportunity`

| Rank | Page | Impr. | Clicks | CTR | Pos. | `band_opportunity` |
|--:|---|--:|--:|--:|--:|--:|
| 1 | rahu-mahadasha-ketu-antardasha | 2,244 | 29 | 1.29% | 7.2 | 105.6 |
| 2 | debilitated-sun-career | 1,409 | 7 | 0.50% | 6.2 | 77.5 |
| 3 | sade-sati | 1,277 | 8 | 0.63% | 6.3 | 68.6 |
| 4 | rahu-mahadasha-career-problems | 782 | 10 | 1.28% | 6.8 | 36.9 |
| 5 | panch-mahapurush-yoga | 493 | 3 | 0.61% | 6.9 | 26.6 |
| 6 | manglik-dosh | 461 | 2 | 0.43% | 7.6 | 25.7 |
| 7 | career-during-sade-sati | 414 | 4 | 0.97% | 6.8 | 20.8 |
| 8 | jupiter-in-10th-house-career | 357 | 1 | 0.28% | 6.9 | 20.4 |
| 9 | marriage-mahadasha-timing | 250 | 1 | 0.40% | 6.6 | 14.0 |
| 10 | 7th-lord-placement-marriage-guide | 301 | 6 | 1.99% | 7.7 | 12.1 |

`band_opportunity` is the script's figure. I did not recompute it.

### CTR outliers (compared with the band's own median, 0.83% on pages with ≥100 impressions)

| Page | Impr. | Clicks | CTR | Pos. | Why it is a finding |
|---|--:|--:|--:|--:|---|
| /matching | 347 | 1 | 0.29% | 4.4 | Best position in the top 10 and a CTR a third of the band median. Already tracked in **#508** (open, no comments). Not re-filed. |
| debilitated-sun-career | 1,409 | 7 | 0.50% | 6.2 | Second-largest band page; CTR 0.6× the band median. Title was rewritten in #311, so this is the live test. |
| sade-sati | 1,277 | 8 | 0.63% | 6.3 | Third-largest, CTR 0.76× median, **not** covered by #311 (see §4). |
| panch-mahapurush-yoga | 493 | 3 | 0.61% | 6.9 | Not covered by #311. |
| kundali-matching-ashtakoot-guna-milan | 164 | 0 | 0% | 7.9 | Zero clicks on 164 impressions. |
| /learn/, /rashifal, guru-jupiter, sun-in-10th-house | 145 / 124 / 103 / 100 | 0 | 0% | 10.1 / 10.1 / 7.3 / 6.9 | Each has ≥100 impressions and no clicks. |
| `/` | 115 | 8 | 6.96% | 6.0 | Positive outlier. Almost certainly branded queries, but I cannot confirm that without query data. |
| 7th-lord-placement-marriage-guide | 301 | 6 | 1.99% | 7.7 | The in-band reference sibling: it holds ≈2% at a worse position than the weak pages. |

### Outside the band

| Page | Impr. | Clicks | Pos. | Note |
|---|--:|--:|--:|---|
| /festivals | 236 | 0 | 25.7 | Beyond position 20. Diwali is 2026-11-08 per CLAUDE.md (a repo statement, not verified by me). I have no earlier window, so I cannot say whether this is rising. |

### Decay

**Not determinable.** Decay needs at least two windows and these files hold one. Single measurement that would settle it: `gsc-trend-page.json` (previous window) read alongside this window.

---

## 2. Scores — closed in the last 28 days (since 2026-09-29) with `thesis:` and `metric:`

55 issues were closed in the period. 27 carry both a `thesis:` and a `metric:` in the body. **Three of the 27 can be scored with GA4/GSC**, plus #272 (whose metric is about the export itself). The other 23 have metrics measured in the tree, in CI or in ops data, which GA4 and GSC cannot score. I did not score them and did not post comments on them (list below).

| Issue | Predicted (`metric:`) | Actual, window W | Verdict |
|---|---|---|---|
| **#311** title/meta on 4 pages | Combined CTR ≥ 1.5% on ≥ 1,500 impressions, position within ±1, over the 28 days after deploy | 20 clicks / 3,009 impr = **0.665%**; impr-weighted position 6.65. Mixed window (see below) | **INCONCLUSIVE, leaning MISS** |
| **#276** /dasha CTA on Rahu–Ketu article | Organic `pages_per_session` ≥ 1.20 (≥ 6 extra views); < 20 sessions = inconclusive | **1.17** on **30** organic sessions (≈ 5 extra views); all channels 40 sessions, 1.13 | **INCONCLUSIVE — not a hit** |
| **#329** Manglik checker link | Organic `pages_per_session` ≥ 1.30 on ≥ 10 sessions; < 10 = inconclusive, not a pass | **1.00** on **3** organic sessions (9 all channels, 6 Direct) | **INCONCLUSIVE — below the issue's own floor** |
| **#272** export dimensions | Channel and per-URL columns exist and are populated | `ga4.json` carries a channel on every row (Organic Search = 177 of 397 sessions); `gsc-*.json` are keyed by `page` | **PASS on shape.** The "top-10 *queries*" half is still not met, because the exports are page-level |

### What the window can and cannot say about #311, #276 and #329

| | #311 | #276 | #329 |
|---|---|---|---|
| Deploy (merge time) | 2026-10-13 17:29Z (PR #334) | 2026-10-14 02:02Z (PR #342) | 2026-10-14 16:07Z (PR #344) |
| Full post-deploy days inside W | 11 (10-14 → 10-24), plus a partial 10-13 | 11 (10-14 → 10-24) | 10 (10-15 → 10-24) |
| Metric's own 28-day window ends | 2026-11-10 | 2026-11-11 | 2026-11-11 |
| Earliest fair rescore | 2026-11-13 | 2026-11-14 | 2026-11-14 |
| "Before" figure | 0.71% (16/2,251), issue's window 09-09..10-06. **Quoted from the issue, not fetched this run.** | 1.0 pages/session on 29 sessions. **Quoted from the issue, not fetched.** | 1.00 on 3 sessions. **Quoted from the issue, not fetched.** |

**#311 — leaning MISS.**
- W is 17 pre-deploy days and 11 post-deploy days. If the post-deploy CTR were the 1.5% bar, the blended W figure would have to be about 0.71% × 17/28 + 1.5% × 11/28 ≈ 1.02%. We see 0.665%.
- For post-deploy ≥ 1.5% to be true, the pre-deploy part of W would need to be ≈ 0.13%, against the issue's own 0.71% baseline. That is implausible but not excluded.
- That arithmetic assumes equal impressions per day. A per-day split is the only way to remove the assumption.
- Position held: impressions-weighted 6.65 (6.2 / 6.8 / 6.9 / 7.6 on the four), inside the ±1 band.
- The four pages' current CTRs: career-problems 1.28% (10/782), debilitated-sun 0.50% (7/1,409), manglik-dosh 0.43% (2/461), jupiter-in-10th 0.28% (1/357).
- Impressions on the four are 3,009 against the 2,251 baseline, so the sample bar is met. **The CTR bar is not, and no lift is visible.**

**#276 — not a hit, not a miss.**
- 1.17 is under the 1.20 bar. 30 sessions is above the < 20 floor, so the sample rule does not excuse it.
- The gap to the bar is about one page-view. 30 × 0.17 ≈ 5 extra views against ≥ 6 needed. That is a handful of sessions and cannot be told apart from noise.
- If the 17 pre-deploy days sat at ~1.0, the post-deploy days would average ~1.4. The pre-deploy value inside W is unknown, so this is an upper-bound reading, not a result.
- GA4 here is landing-level and cannot show whether any onward view went to `/dasha`. Even a pass would not prove the CTA caused it.
- Bounce is 33% on organic, which fits "most sessions are engaged by time, not by onward clicks".

**#329 — the metric cannot resolve at this traffic.**
- It needs ≥ 10 organic sessions in 28 days. W has 3 (and GSC shows 2 clicks on 461 impressions at position 7.6).
- **Direct confound with #311.** `manglik-dosh` is one of #311's four pages, and its title/meta landed 15 hours before the checker link. A change in this page's traffic is not attributable to either.
- Flagged in the finding at the end: unless #311 lifts CTR, #329's metric is unlikely ever to read above INCONCLUSIVE.

### The other 23 issues with a thesis and metric — not scored by me

None has a GA4/GSC metric. #397 and #515 touch user-facing content but are measured on the tree and on stored readings, which I do not have.

| Issues | Metric kind |
|---|---|
| #286, #313, #316, #320, #338, #345, #349, #362, #374, #442, #449, #493 | Loop / CI / repo state |
| #355, #372, #396, #400 | Token and latency accounting (ops data) |
| #369 | CSS rules on `/admin/ops` |
| #373, #408, #409 | Security / error-path assertions |
| #397 | Occurrences of an absolute claim in the tree |
| #405 | Merge-conflict churn in git history |
| #515 | Share of readings naming a forbidden planet (GCS blobs) |

---

## 3. Confounds

| Confound | State | Effect on the scores |
|---|---|---|
| **Concurrent ships** | `git log origin/main` since the deploys: **33 commits touching `src/`/`pyproject.toml`/`uv.lock`** after #311's deploy (10-13 17:29Z) through 10-24; 32 after #276's; 31 after #329's. 57 since 09-27. | Most are admin, token-accounting, prompt and loop work with no learn-page effect. Several touch the learn templates (next row). Attribution to one ship is not possible. |
| **Same-page edits** | `c59c750` (10-21) edited remedy text on manglik-dosh, rahu-ketu-antardasha and career-problems. `126abc1` (10-22) edited debilitated-sun. `db86556` (10-23) edited jupiter-in-10th. I read the manglik and rahu-ketu diffs: remedy-line edits, no change to the CTA or the link. | Does not touch CTR or the onward path. Content change, so a small ranking effect cannot be excluded. |
| **Ships after W ends** | `a9fc25f` (#521, 10-25) adds routes to a tool on debilitated-sun and jupiter-in-10th, two of #311's four. | Outside W, but it will contaminate the next windows' pages-per-session on those two. |
| **#311 vs #329 on one page** | manglik-dosh changed by both within 15 hours. | See §2. |
| **Prerequisite for #276** | The sticky Kundli CTA was lifted above the mobile tab bar on 10-09 (#312), before the #276 deploy. | Visible during the whole post-deploy period, so it does not confuse the #276 read. It does sit inside W's pre-deploy part. |
| **Page reachability** | #253's service-worker fix shipped 10-20 (`0824996`). Before that, returning visitors could be served a stale stylesheet. #266 is about the Groq-backed natal request, not the static `/learn/*` articles. | Engagement before 10-20 may be understated for returning visitors. I cannot check HTTP health of the pages from these files. I did not fetch production. |
| **Google re-crawl lag** | GSC shows impressions, not the title Google displayed. I confirmed the new `seo_title` strings are in `learn_registry.py` at `origin/main` for manglik-dosh and career-problems. I did not check what Google shows. | A title change may not have been displayed for all of W's post-deploy days. This favours "wait", not "miss". |
| **Seasonality** | These are evergreen dasha/manglik/career topics. Diwali is 2026-11-08 (repo statement; I did not verify the festival calendar for W). I have no earlier year or window to compare. | Cannot be ruled in or out. |
| **Sample size** | Organic sessions: 177 across the site, 30 on the top page, 3 on manglik-dosh. | Every per-page pages/session figure here is a handful of sessions. |
| **Internal traffic** | `/admin/ops` landed 7 sessions (6 Direct) in W, 1.8% of 397. I cannot tell whether other Direct traffic is owner or agent traffic. | Direct bounce on tool pages may be inflated. Does not touch organic. |

---

## 4. Funnel and traffic mix (GA4, W)

| Channel | Sessions | Share | Weighted bounce | Weighted pages/session |
|---|--:|--:|--:|--:|
| Direct | 188 | 47.4% | 62.8% | 2.23 |
| Organic Search | 177 | 44.6% | 44.1% | 1.66 |
| AI Assistant | 24 | 6.0% | 41.7% | 2.50 |
| Unassigned | 8 | 2.0% | 75.0% | 0.50 |
| **Total** | **397** | | | |

| Landing (all channels) | Sessions | Organic | Bounce | Pages/session | Note |
|---|--:|--:|--:|--:|---|
| `/` | 92 | 10 | 30% | 3.80 | The only landing with real onward traffic |
| /learn/rahu-mahadasha-ketu-antardasha | 40 | 30 | 47% | 1.13 | Top organic landing |
| /kundli | 22 | 10 | 77% | 1.45 | Direct 12 sessions, **100% bounce** |
| /learn/griha-pravesh-muhurat-2026-2027 | 14 | 8 | 64% | 1.00 | |
| /learn/sade-sati | 13 | 9 | 31% | 1.15 | |
| /matching | 12 | 0 | 75% | 2.33 | Direct 10, AI Assistant 2, **no organic** despite 347 GSC impressions |
| /learn/marriage-mahadasha-timing | 12 | 1 | 83% | 1.17 | Direct 8, AI 3 |
| /numerology | 9 | 0 | 100% | 1.00 | All Direct |
| /learn/manglik-dosh | 9 | 3 | 100% | 1.00 | |

- Learn articles that earn organic sessions mostly show pages/session 1.0–1.4.
- The organic top page converts to nothing onward on this measure.
- This is what #518 (open) is about. It shipped partially on 10-25, after W, so this window is the pre-#521 baseline for those pages.
- Landings with a query string: 4 rows, 6 sessions in total, folded into their paths above.

---

## 5. Issues filed

**None.** Candidates considered, and why not:

| Candidate | Why not |
|---|---|
| `/matching` position 4.4, CTR 0.29% | Already open as **#508** ("0 clicks on 336 impressions", window 09-23..10-20). Still reproduces in W (347 impr, 1 click). No comments on #508 yet. I did not add a duplicate. |
| Rewrite sade-sati / panch-mahapurush titles (CTR 0.63% / 0.61%) | It is the same idea as #311, which is unscored. Filing it would repeat the bet before the first result is in. Revisit after the 2026-11-13 rescore. |
| `/festivals` at position 25.7 | One window, 0 clicks, and no trend. No action justified yet. |
| Direct traffic with 100% bounce on /kundli and /numerology | Cannot tell internal, bot or real from these files. |

---

## 6. What I could not determine, and the measurement that settles it

| Unknown | Measurement that settles it |
|---|---|
| Whether #311, #276 or #329 moved anything | Per-day, per-page series (GSC `page × date`, GA4 landing × date) split at each deploy timestamp. `/tmp/gsc-daily.json` and `/tmp/ga4-daily.json` exist, but I was not given them for this run. Otherwise wait for the full 28 post-deploy days (rescore from 2026-11-13). |
| Query-level movement against the objective | A `--by query` export joined to page. It is a partial view (~9% coverage per the analyst definition), so it cannot settle the whole band. |
| Band movement and decay | The previous window's `--band` export beside this one. |
| Whether Google shows the new #311 titles | A live SERP check for those four URLs. Not attempted. |
| Whether the #276 CTA is clicked | A GA4 event on the CTA link or a next-page report. The landing-level export cannot show it. |
| Whether the /learn pages were serving correctly through W | A production health sweep. `verify-production` asserts invariants, not page-level availability over time. |

## Bottom line

| | |
|---|---|
| Hits | 1 on shape: #272 (and its query-level half is still unmet) |
| Misses | 0 proven; **#311 leans MISS** — CTR 0.665% against a 1.5% bar, with 11 of 28 days post-deploy |
| Inconclusive | #276 (1.17 vs 1.20, ~5 views, noise), #329 (3 organic sessions vs a 10-session floor) |
| Not scoreable by me | 23 infra/tree-measured theses |
| Objective | 1 of the top-10 pages is at ≤ 5.0; the other 9 sit 0.8–2.6 positions off. Movement cannot be measured from one window |

## Comments posted this run

| Issue | Comment |
|---|---|
| #311 | https://github.com/mahAnuj/astro-ai/issues/311#issuecomment-6430478245 |
| #276 | https://github.com/mahAnuj/astro-ai/issues/276#issuecomment-6430479300 |
| #329 | https://github.com/mahAnuj/astro-ai/issues/329#issuecomment-6430479546 |
| #272 | https://github.com/mahAnuj/astro-ai/issues/272#issuecomment-6430479800 |

The first attempt to post all four ran in a loop with `| tail -1` and printed nothing. I checked afterwards and none had posted, then re-ran each one and checked the exit codes. One comment per issue, no duplicates.
