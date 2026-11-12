# Analyst report — 2026-11-12 run

**Window W = 2026-10-13 → 2026-11-09** (28 days, last 3 days excluded). **Previous window P = 2026-09-15 → 2026-10-12.**
All numbers below were read from `/tmp/*.json` this run. Nothing is quoted from `BACKLOG.md` or memory.

## 0. Coverage (read before any number)

| export | dimension | coverage | truncated | note |
|---|---|---|---|---|
| gsc-band / gsc-all / gsc-daily | page / page / date | 100% of 22,965 impressions | no | band printed 104 rows = 18,755 impressions (82% of the page rows) |
| gsc-trend-page | page | 100% | n/a | 143 pages now, 126 in P |
| gsc-trend-query | query | **13%** of 22,965 impressions | n/a | partial view. Google withholds the rest. Query findings do not describe the site |
| ga4 | landing × channel | 100% of 646 sessions | no | 138 rows, 88 distinct landings (82 paths after folding query strings and trailing slashes) |
| ga4-daily | date | 28 of 28 days with traffic | n/a | no channel split by day |
| ga4-events | eventName | not stated as a % | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688), so it holds ~7 of 28 days |

## 1. The 6–20 position band vs the objective (W)

Objective: organic traction is real and unpromoted (#267). Optimise the band before publishing more.

| measure (GSC page, W) | value |
|---|---|
| site impressions / clicks / CTR | 22,965 / 285 / 1.24% |
| same, P (sum of page rows) | 10,371 / 108 / 1.04% |
| band pages (position 6–20) | 104 pages, 18,755 impressions, 203 clicks, **CTR 1.08%** |
| band CTR, pages with ≥100 impressions (25 pages) | 1.07% pooled, median 0.95% |
| site average position, daily range | 6.3 – 8.1, no trend |

**Growth is impression volume, not rank.** Daily average position stayed at 6.3–8.1 across W. The weekly step-up is in the table below.

| week (GSC daily) | impressions | clicks | GA4 sessions |
|---|---:|---:|---:|
| 10-13 → 10-19 | 2,845 | 35 | 125 |
| 10-20 → 10-26 | 4,667 | 47 | 139 |
| 10-27 → 11-02 | 7,522 | 90 | 152 |
| 11-03 → 11-09 | 7,931 | 113 | 231 |

Impressions rose about 2.8× from the first week to the last, and clicks about 3.2×. The rise flattened over the last two weeks. The last week's sessions include the 59-session day on 11-06.

### Band list, top 10 by opportunity (W, GSC page, avg position across the page's queries)

| page | impr | clicks | CTR | pos | clicks at band CTR (1.07%) | impr in P → W |
|---|---:|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,606 | 52 | 1.44% | 6.5 | 38.7 | 1,699 → 3,606 |
| /learn/debilitated-sun-career/ | 2,455 | 14 | **0.57%** | 6.7 | 26.3 | 962 → 2,455 |
| /learn/sade-sati/ | 1,942 | 12 | **0.62%** | 6.6 | 20.8 | 874 → 1,942 |
| /learn/jupiter-in-10th-house-career/ | 1,556 | 14 | 0.90% | 6.9 | 16.7 | 342 → 1,556 |
| /learn/7th-lord-placement-marriage-guide/ | 1,270 | 13 | 1.02% | 7.3 | 13.6 | 210 → 1,270 |
| /learn/gochar-2026-planetary-transits/ | 1,036 | 15 | 1.45% | 6.2 | 11.1 | 17 → 1,036 |
| /learn/planets-in-7th-house-marriage/ | 845 | 8 | 0.95% | 6.0 | 9.1 | 467 → 845 |
| /learn/panch-mahapurush-yoga/ | 790 | 9 | 1.14% | 6.9 | 8.5 | 361 → 790 |
| /learn/manglik-dosh/ | 505 | 3 | **0.59%** | 6.7 | 5.4 | 443 → 505 |
| /learn/10th-lord-in-6th-house-career/ | 577 | 16 | 2.77% | 6.5 | 6.2 | 184 → 577 |

- The top 10 band pages hold 14,582 impressions, 78% of the band's impressions.
- Pages just outside the band, at position 5.0–5.8 with ≥100 impressions: `/learn/career-during-sade-sati/` (978 impr, 13 clicks, pos 5.4), `/learn/marriage-mahadasha-timing/` (560, 6, 5.3), `/learn/chronic-health-issues-kundli/` (303, 5, 5.0), `/muhurat/griha-pravesh` (192, 13 clicks, 6.77% CTR, pos 5.8). The last is the site's best-converting page by CTR.
- The "clicks at band CTR" column is arithmetic on this window's pooled band rate. It is not a forecast.

### CTR outliers (below the band's own 1.07%, ≥500 impressions, position 6–7.3)

| page | impr | CTR | gap vs band rate (clicks) | already being worked? |
|---|---:|---:|---:|---|
| /learn/debilitated-sun-career/ | 2,455 | 0.57% | about 12 | #311 (title/meta, shipped 10-13); #835 (open, answer-first FAQ for the "which sign" queries) |
| /learn/sade-sati/ | 1,942 | 0.62% | about 9 | #685 (title, shipped 11-03, 9 of 28 days in W are post-deploy) |
| /learn/manglik-dosh/ | 505 | 0.59% | about 2 | #311 |

- Query evidence for debilitated-sun: `sun debilitated in which sign` (220 impr), `sun is debilitated in which sign` (107) and `sun debilitated sign` (70) are new in W (0 or 2 impressions in P). Query coverage is 13%.
- No new issue is needed. Each outlier already has an owner issue.

## 2. Post-ship scores (issues closed in the last 45 days with a `thesis:` and `metric:`)

**Window rule.** A window is clean when today − 31 (= 2026-10-12) is on or after the deploy date. No ship below is clean today.

| issue | deploy (PR merged) | clean window readable from | bar | state this run | action |
|---|---|---|---|---|---|
| #311 title/meta, 4 band pages | 2026-10-13 17:29Z (#334) | **2026-11-13** (tomorrow) | CTR ≥ 1.5% on ≥ 1,500 impr, pos ±1 | pending note already posted 11-08 | none. **Score at the next run** |
| #276 /dasha CTA, Rahu–Ketu article | 2026-10-14 02:02Z (#342) | 2026-11-14 | pages/session ≥ 1.20, ≥ 20 sessions | pending note already posted 11-08 | none |
| #329 Manglik checker link | 2026-10-14 16:07Z (#344) | 2026-11-14 | pages/session ≥ 1.30 on ≥ 10 sessions | pending, likely unscoreable (see below) | none |
| #508 /matching title/meta | 2026-11-03 20:59Z (#696) | 2026-12-04 | CTR ≥ 1.0% on ≥ 300 impr, pos 4.3 ±1.5 | pending note posted 11-07 | none, but see /matching below |
| #685 sade-sati title | 2026-11-03 10:58Z (#690) | 2026-12-04 | CTR ≥ 1.2% on ≥ 1,200 impr, pos within ±1 of 6.4 | pending note posted 11-08 | none |
| #426 sade-sati date correction (guard) | 2026-11-02 12:18Z (#673) | 2026-12-03 | position ±1 of 6.2, impressions not down >20% | pending note posted 11-08 | none |
| #518 learn → tool routing (5 slices) | 2026-10-25 → 2026-11-06 | 2026-12-07 | pages/session on /learn landings ≥ 2.0 | pending note posted 11-07 | none |
| #553 panch-mahapurush-yoga | 2026-10-31 02:26Z (#615) | 2026-12-01 | pages/session ≥ 1.30 on ≥ 10 sessions | pending note posted 11-07 | none |
| #570 `cta_click` event | 2026-11-03 04:42Z (#688) | 2026-12-04 | ≥ 1 event row per tool-linked article that received a click | pending note posted 11-08 | none |
| #528 /ask question out of the URL | 2026-11-09 00:53Z (#801) | 2026-12-10 | landings carrying a visitor `q=`: 1 → 0 | pending note posted 11-11 | none |
| #735 admin pages boot no GA4 | 2026-11-11 02:38Z (#877) | **2026-12-12** | `/admin*` landings 14 → 0 | **no note existed. One note posted this run** (comment 6812290654) | posted |
| #782 events export | n/a | n/a | the file exists after a run | closed 11-09 on a live run. A measurement-plumbing issue, not a traffic thesis | none |
| #843 per-word compounds on /numerology | 2026-11-10 (#850) | n/a | per-word compounds rendered. Not a traffic metric | issue itself says "likely unscoreable" at 14 sessions per 28d | **no comment**. The metric is deterministic and has no sample floor. GA4 shows 14 /numerology sessions in W, so a traffic read is meaningless |

Not scored because they are not traffic metrics: #896, #893, #885, #883, #871 and similar correctness issues.

### Reference readings for the pending issues (W, descriptive only, NOT scores)

| page | W impr / clicks / CTR / pos | GA4 organic sessions, pages/session, bounce (W) | what it can and cannot say |
|---|---|---|---|
| #311 set: career-problems | 996 / 21 / 2.11% / 6.0 (gsc-all; P: 828 / 6 clicks / pos 7.3) | 23, 2.13, 43% | missing from the band printout (position sits on the 6.0 edge); W holds the deploy day |
| #311 set: debilitated-sun | 2,455 / 14 / 0.57% / 6.7 | 16, 1.25, 62% | W holds the deploy day, so it mixes before and after |
| #311 set: manglik | 505 / 3 / 0.59% / 6.7 | **3**, 1.00 | below #329's floor of 10 sessions |
| #311 set: jupiter-10th | 1,556 / 14 / 0.90% / 6.9 | 16, 1.38, 56% | same |
| #276 Rahu–Ketu | 3,606 / 52 / 1.44% / 6.5 | 53, 1.38, 34% | bar ≥ 1.20 pages/session is met on the number, but #518 also edited this page and the cta_click ship overlaps (see confounds) |
| #685 sade-sati | 1,942 / 12 / 0.62% / 6.6 | 12, 2.58, 17% | 7 of 28 days are post-deploy. CTR bar of 1.2% is not near |
| #553 panch-mahapurush | 790 / 9 / 1.14% / 6.9 | **8**, 1.00 | below the floor of 10 |

**Do not read a verdict into this table.** The windows still contain pre-deploy days, which the issue-score rules forbid scoring on. #311 is the first to go clean (tomorrow). **#311 early read, not a score.** Four pages combined (career-problems, debilitated-sun, manglik, jupiter-10th), GSC page rows from `gsc-trend-page.json` / `gsc-all.json`:

| window | impressions | clicks | CTR |
|---|---:|---:|---:|
| P 2026-09-15 → 10-12 (pre-deploy) | 2,575 | 15 | 0.58% |
| W 2026-10-13 → 11-09 (starts on the deploy day) | 5,512 | 52 | 0.94% |
| bar | ≥ 1,500 | | ≥ 1.5%, position within ±1 |

On this reading the CTR bar (1.5%) is **not met** (0.94%). The impression floor is cleared, and positions moved from 7.3–6.0 to 6.0–6.9. Career-problems alone is at 2.11%; the other three are at 0.57–0.90%. #518 first-screen tool links landed on these same pages during W and the query mix more than doubled, so a CTR move cannot be put down to the title. The window rule makes tomorrow's run the scoring run. I expect a **MISS on the CTR bar** unless the numbers move, and will report it as one. (The issue's own 0.71% / 16 clicks / 2,251 impressions is an earlier window and does not match P exactly.)

**#329 is likely unscoreable.** Manglik got 3 organic sessions in W against a floor of 10, so expect one "unscoreable at this traffic: 3 vs 10" note when its window is clean on 11-14. #553's page is at 8 vs 10, which is near the floor but under it.

## 3. Confounds (named before any delta)

| confound | evidence | consequence |
|---|---|---|
| Many ships on the same pages in the same window | `gh pr list --state merged --since 2026-10-13`, content/SEO/UI ones: #521 (10-25), #615 (10-31), #658 (11-01), #680 (11-02), #673 (11-02), #690 (11-03), #696 (11-03), #754 (11-06), #830 (11-09), #796 (11-09; 7 learn seo_descriptions shortened), #737 (11-06; skip link + `<main>` on every page). The Rahu–Ketu page alone took #342, #521 and #830 | **No page-level movement in W can be attributed to a single ship.** The first-screen tool links of #518 landed on #311's pages while #311 was in flight |
| Seasonality | Diwali fell on 2026-11-08, inside W. `/learn/diwali-muhurat-2026/` went 2 → 74 impressions with position 7 → 11.1. `/learn/gochar-2026-planetary-transits/` went 17 → 1,036. Sade Sati / transit queries are timed to the 2026 transit calendar | festival and transit pages cannot be read as the work |
| Weekly traffic ramp is not explained | impressions per day went from ~400 (10-13 → 10-21) to ~1,050 (10-27 onward) while average position did not move | cause not determinable from these files. Candidates are query-mix growth and crawl/index growth. Not testable here |
| Page reachability | `/matching` sessions and impressions fell (below). `/festivals` position 28.7 → 32.1 (288 impr, 0 clicks) | traffic to a broken page is not engagement. No outage evidence in these files either way |
| Sample size | 285 clicks and 646 sessions in 28 days. Most per-page figures are under 20 clicks | pages with <10 sessions carry no conclusion |
| Owner/agent traffic in the sessions denominator | `/admin*` 21 sessions, `(not set)` 19 sessions in W. Together 40 of 646 (6.2%) | sessions and pages/session are slightly inflated by non-visitors until #735's clean window |
| Git history confound check | the clone is depth 1 (one commit), so `git log origin/main --since` cannot run (#666 open). Confounds above come from `gh pr list` merge dates instead | the PR list covers merges, not whether a merge touched a given page |

## 4. Decay (W vs P, GSC page)

| page | impr P → W | position P → W | clicks P → W | read |
|---|---|---|---|---|
| /matching | 317 → **98** (−69%) | 4.2 → **8.1** | 0 → 2 | real fall in top-10 visibility. See below |
| /learn/the-9-grahas-overview/ | 100 → 31 (−69%) | 8.0 → 9.2 | 0 → 0 | small |
| /learn/ashwini-nakshatra/ | 98 → 88 | 5.6 → 7.8 | 1 → 0 | position loss at similar impressions |
| /festivals | 293 → 288 | 28.7 → 32.1 | 1 → 0 | never ranked. Not decay |
| /learn/griha-pravesh-muhurat-2026-2027/ | 42 → **0 (gone)** | 7.5 → none | 1 → 0 | disappeared from GSC in W |
| /learn/career-not-progressing/ | 21 → 0 (gone) | | 0 → 0 | disappeared |
| /learn/marriage-delayed/ | 41 → 16 | 7.0 → 4.9 | 0 → 0 | better position, fewer impressions: query-mix |
| /learn/krittika-nakshatra/, /learn/shani-saturn/ | 5 → 59, 17 → 87 | 4.8 → 7.4, 8.3 → 10.2 | 0 | new pages entering at a worse average position. Not decay |

**/matching** is the only decay worth reading, and the arithmetic points the other way from the obvious story:

- P (09-15 → 10-12): 317 impressions at position 4.2.
- #508's own pending note quoted 2026-10-08 → 11-04: 351 impressions at 4.4.
- W (10-13 → 11-09): 98 impressions at 8.1.
- The 10-08 → 11-04 window and W share 10-13 → 11-04. So the **bulk of the /matching impressions were in 10-08 → 10-12 and are in neither W nor the post-deploy days**. That means the burst ended around mid-October, **before** #696 shipped on 11-03.
- The shortened title is therefore not the likely cause of the fall, and the title test's "before = 336 impressions" baseline is a burst that has gone.
- **Consequence for #508:** the clean window opens 11-04. At W's rate (98 per 28 days) it will not reach #508's floor of 300 impressions, so expect "unscoreable at this traffic" on 2026-12-04.
- Not determinable: the exact day of the drop, because there is no page × day export (#490, open). A single page × day pull for `/matching` would settle it.
- No new issue. The only action would be the page × day export, and #490 already asks for it.

Disappeared pages (`griha-pravesh-muhurat-2026-2027`, `career-not-progressing`): GA4 still shows `/learn/griha-pravesh-muhurat-2026-2027` with 16 sessions in W (69% bounce, 1.0 pages/session), so the page is reachable and is getting visits from other channels. The loss is in GSC impressions only. Cause not determinable from these files.

## 5. Traffic and channel mix (GA4, W)

| measure | value |
|---|---|
| sessions (landing × channel rows) | 646 (645 summed over rows) |
| Organic Search | 361 (56%) |
| Direct | 269 (42%) |
| AI Assistant | 10 (1.5%) |
| Unassigned | 5 |
| organic sessions landing on `/learn/*` | 283 (78% of organic), pages/session 1.51 (session-weighted) |
| organic sessions on non-learn landings | 78 |
| homepage `/` (all channels) | 87 sessions, 37% bounce, 3.99 pages/session |
| three outlier days | 10-16: 42 sessions, 10-23: 34, 11-06: 59 (typical day 12–37) |

- The channel for the three spike days is **not determinable**: the daily export has no channel split.
- `/learn/*` organic pages/session is **1.51 over W**. #518's pre-ship reading was 1.32. This is a W reading with partial post-ship days and many confounds, not a score.
- A 59-session day on 11-06 would be 9% of the window's sessions. Excluding the three spike days, W holds 512 sessions.

## 6. Funnel and events (GA4 events, W)

| event | count |
|---|---:|
| page_view | 1,137 |
| session_start | 643 |
| first_visit | 512 |
| user_identified | 671 |
| feature_view | 652 |
| form_start | 139 |
| ask_answered | 135 |
| **kundli_generated** | **52** |
| **cta_click** | **9** (coverage: from 2026-11-03, about 7 of the 28 days) |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |

- **`cta_click` split:** 8 of 9 events have `from_path` and `to_path` both `(not set)`. Only 1 carries a readable pair: `/learn/kaal-sarp-dosh/` → `/kaal-sarp-check`. So the split is **unreadable for 89% of events**. The total (9) stands. `split_available: true` in the file describes the export, not the data's content.
- **Why that matters:** #570's pass bar needs one event row per tool-linked article. With 8 of 9 events unattributed, that bar cannot be checked on this data. Whether the `(not set)` events come from the event firing without its parameters, or from a GA4 custom-dimension registration gap, is **not determinable from this file**. The single measurement that would settle it: GA4 Admin → Custom definitions, check whether `from_path` and `to_path` are registered as event-scoped dimensions.
- **Denominator, derived:** GA4 daily sessions 11-03 → 11-09 = 231 across all channels. 9 events / 231 sessions = 3.9% site-wide. That is not a learn-article click-through rate: the numerator is `cta_click` across all pages and the denominator includes all landings.
- `form_start` (139) and `kundli_generated` (52) cannot be put into a /kundli funnel: `form_start` is not split by form, so it also counts matching, numerology and ask. `form_submit` is 1 against `kundli_generated` 52 and `ask_answered` 135, so it is **not** the submit event for the main forms and should not be read as a funnel step.
- Landings for the calculators, GA4 organic, W: `/kundli` 24 sessions (67% bounce, 1.67 pages/session), `/matching` 13 (77%, 1.85), `/numerology` 14 (79%, 1.0). Bounce is high and sessions are small.

## 7. What could not be determined, and the single measurement that settles it

| gap | settle it with |
|---|---|
| exact day `/matching` lost its position, and whether #696 touched it | page × day GSC export for `/matching` (#490) |
| per-ship attribution on the four #311 pages, which also took #518 tool links | page × day export (#490) with each deploy timestamp, or one ship per page per window |
| channel of the 10-16 / 10-23 / 11-06 spikes | a date × channel GA4 export |
| why 8 of 9 `cta_click` events have no `from_path` / `to_path` | check the custom-dimension registration for both parameters in GA4 Admin |
| cause of the ~2.5× impression ramp 10-13 → 11-09 at flat position | none from these files |
| whether any ship touched a page's title between windows | `git log` is unusable at depth 1 (#666) |
| #311 attribution of the CTR move | page × day export (#490); the early read mixes the title change with #518 links on the same pages |

## 8. Actions this run

| action | where |
|---|---|
| posted "pending — scoreable from 2026-12-12" with baseline (21 `/admin*` sessions, 19 `(not set)`, W) | #735, comment 6812290654 |
| no other comment posted. Every other thesis issue already carries its one pending note, and none has a clean window yet | #311, #276, #329, #508, #685, #426, #518, #553, #570, #528 |
| no issue filed. The findings that need action (page × day export, `cta_click` parameter split) are either already covered by an open issue (#490) or a configuration check outside the repo that I cannot verify. See the note below | |

**One finding without an owner.** The `cta_click` parameter split being `(not set)` on 8 of 9 events is not covered by any open issue I found. I did not file one: I cannot tell from this file whether it is a registration gap in GA4 or a defect in the event code, and an issue needs a repro. **The next run should check whether `from_path` / `to_path` count is still 8 of 9 `(not set)` over a window that is wholly post-ship (from 2026-11-04), and file with an Evidence Block if so.**

## 9. Next runs

| date | what becomes scoreable | what to do |
|---|---|---|
| **2026-11-13** | #311 | score once: four-page combined CTR vs the 28 days before deploy (early read 0.94% vs bar 1.5%, so a MISS is likely), with the #518 overlap named |
| 2026-11-14 | #276, #329 | score once, or post "unscoreable at this traffic" for #329 (Manglik: 3 organic sessions in W vs a floor of 10) |
| 2026-12-03 → 12-12 | #426, #508 (expect unscoreable: ~98 vs 300 impressions), #685, #553, #518, #570, #528, #735 | per their pending notes |
