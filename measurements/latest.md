# Analyst report — run of 2026-11-14

**Window for every number: 2026-10-15 → 2026-11-11** (28 days, last 3 days excluded; GSC lags 2–3 days, GA4 24–48h) unless a row states another. **Previous window** for deltas: 2026-09-17 → 2026-10-14. All figures read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json`, `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json`, `/tmp/ga4-events.json`.

## 0. Coverage — read before any number

| export | dimension | coverage of property total | truncated | note |
|---|---|---|---|---|
| gsc-all / gsc-band / gsc-trend-page | page | 100% of 23,440 impressions (293 clicks) | no | band printed 102 rows = 82% of impressions (19,260) |
| gsc-trend-query | query | **14%** of 23,440 | no | partial view: Google withholds rare queries; never read as the whole site |
| ga4 | landing × channel | 100% of 703 sessions (151 rows, 97 landings) | no | 89 distinct paths after folding query strings and trailing slashes |
| ga4-daily | date | 28 of 28 days with traffic | n/a | |
| ga4-events | event | 4,725 events | no | `cta_click` exists only from 2026-11-03 04:42Z (PR #688): partial history |

## 1. The 6–20 band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* The page-mode export measures **pages**, whose position is an average across their queries. The query export covers 14%, so "ten highest-impression queries" cannot be read for the whole site; the ten highest-impression **pages** are read instead.

| measure (2026-10-15 → 11-11, GSC page mode) | value |
|---|---|
| pages at average position 6–20 | 102 pages, 19,260 impressions, 220 clicks |
| of those, pages at position ≤ 10 | 81 pages, 18,888 impressions |
| ten highest-impression pages with average position ≤ 5.0 | **0 of 10** (objective target: 10 of 10) |
| ten highest-impression pages, position range | 5.3 – 7.4 |
| band CTR median, 25 pages with ≥ 100 impressions | 0.87% |
| site-wide, this window vs previous | 23,518 vs 10,748 impressions (+119%); 293 vs 107 clicks (+174%) |

Ten highest-impression pages (window above):

| # | page | impressions | clicks | CTR | avg position | impressions prev | position prev |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,612 | 53 | 1.47% | 6.5 | 1,821 | 7.5 |
| 2 | /learn/debilitated-sun-career/ | 2,469 | 14 | 0.57% | 6.6 | 1,013 | 6.1 |
| 3 | /learn/sade-sati/ | 1,923 | 13 | 0.68% | 6.6 | 945 | 6.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,609 | 14 | 0.87% | 6.9 | 358 | 6.8 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,305 | 13 | 1.00% | 7.3 | 222 | 8.0 |
| 6 | /learn/gochar-2026-planetary-transits/ | 1,147 | 16 | 1.39% | 6.2 | 16 | 6.9 |
| 7 | /learn/career-during-sade-sati/ | 1,008 | 15 | 1.49% | 5.4 | 407 | 7.3 |
| 8 | /learn/rahu-mahadasha-career-problems/ | 991 | 22 | 2.22% | 5.9 | 837 | 7.2 |
| 9 | /learn/planets-in-7th-house-marriage/ | 882 | 7 | 0.79% | 6.2 | 512 | 6.1 |
| 10 | /learn/panch-mahapurush-yoga/ | 800 | 10 | 1.25% | 6.9 | 379 | 6.8 |

Band opportunity ranking (the export's `band_opportunity`, impressions × achievable CTR gain), top 8:

| page | impressions | CTR | position | band_opportunity |
|---|---:|---:|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,612 | 1.47% | 6.5 | 163.7 |
| /learn/debilitated-sun-career/ | 2,469 | 0.57% | 6.6 | 134.1 |
| /learn/sade-sati/ | 1,923 | 0.68% | 6.6 | 102.4 |
| /learn/jupiter-in-10th-house-career/ | 1,609 | 0.87% | 6.9 | 82.5 |
| /learn/7th-lord-placement-marriage-guide/ | 1,305 | 1.00% | 7.3 | 65.3 |
| /learn/gochar-2026-planetary-transits/ | 1,147 | 1.39% | 6.2 | 52.8 |
| /learn/planets-in-7th-house-marriage/ | 882 | 0.79% | 6.2 | 45.9 |
| /learn/panch-mahapurush-yoga/ | 800 | 1.25% | 6.9 | 38.0 |

Reading: the band grew in width (impressions more than doubled) but not in height. The site-wide average position is flat (daily 6.5–8.1 across the window) and no top-10 page is at ≤ 5.0. The two nearest are `/learn/career-during-sade-sati/` (5.4) and `/learn/rahu-mahadasha-career-problems/` (5.9). Page-level position rose by 1 or more on `rahu-mahadasha-ketu-antardasha` (7.5 → 6.5) and `career-during-sade-sati` (7.3 → 5.4).

## 2. Site-level trend

| period (2026-10-15 → 11-11) | GSC impressions | GSC clicks | CTR | GA4 sessions |
|---|---:|---:|---:|---:|
| first 7 days (10-15 → 10-21) | 2,959 | 38 | 1.28% | 138 |
| middle 14 days (10-22 → 11-04) | 13,686 | 155 | 1.13% | not split |
| last 7 days (11-05 → 11-11) | 8,035 | 114 | 1.42% | 252 |
| whole window | 23,440 | 293 | 1.25% | 704 (703 per property total) |

Impressions step up from about 400/day (10-15 → 10-22) to about 1,000/day from 10-26 and stay there. GA4 sessions per day ranged 11–59 with one-day spikes on 2026-10-16 (42), 10-23 (34), 11-06 (59) and 11-10 (43). **Not determinable:** what produced those spikes; `ga4-daily.json` has no channel split, so organic cannot be separated from direct on a given day. Single-day spikes are not trends.

### GA4 sessions by channel (2026-10-15 → 11-11, landing × channel rows summed; bounce and pages/session weighted by sessions)

| channel | sessions | bounce rate | pages/session |
|---|---:|---:|---:|
| Organic Search | 390 | 45.4% | 1.63 |
| Direct | 296 | 75.0% | 1.80 |
| AI Assistant | 11 | 36.4% | 4.09 |
| Unassigned | 5 | 80.0% | 0.40 |
| all | 702 | 58.0% | 1.73 |

North-star read: organic sessions = **390 of 702 (56%)**. The 296 Direct sessions carry 75% bounce, which is the shape of non-human or internal traffic; this cannot be settled from these exports.

**Measurement noise in the denominator (#735, deployed 2026-11-11):** 20 sessions (2.8% of 702) landed on `/admin/ops/` (19 Direct, 1 Organic Search; 60% bounce), and 20 more sit on landing `(not set)` (15 Organic Search, 95% bounce, 0.0 pages/session). The #735 fix merged 2026-11-11 02:38Z, so this window still contains the admin traffic; the 28-day effect is pending (scoreable from 2026-12-12, already posted on #735).

## 3. Scores — issues closed in the last 45 days that carried a `thesis:` and a `metric:`

Rule applied: a window is clean when it starts on or after the deploy date. This window starts 2026-10-15.

### Posted this run (once each)

| issue | deploy | verdict | predicted | actual (2026-10-15 → 11-11) | where |
|---|---|---|---|---|---|
| **#276** Rahu–Ketu antardasha `/dasha` CTA | PR #342, 2026-10-14 02:02Z | **BAR MET, not attributable** | ≥ 1.20 pages/session on ≥ 20 organic sessions | **1.42 on 55 organic sessions** (all channels 1.33 on 69) | comment on #276 |
| **#329** Manglik checker link | PR #344, 2026-10-14 16:07Z | **UNSCOREABLE at this traffic: 3 vs 10** | ≥ 1.30 pages/session on ≥ 10 organic sessions | 3 organic sessions at 1.00; 7 all channels | comment on #329 |

Caveat on the #276 hit, stated as plainly as the pass: the page's 1.42 pages/session is **below** the 1.58 of all other `/learn/*` organic landings combined (251 sessions), so the data does not show this CTA outperforming the routes #518 added elsewhere. A second tool route landed on the same article on 2026-11-02 (PR #680) and the link text changed on 2026-11-09 (PR #830). The one direct `cta_click` read for the page (from `/tmp/ga4-events.json`, partial history from 2026-11-03) is **1** event to `/dasha`.

### Already posted on an earlier run — NOT re-posted

| issue | state | earlier verdict (posted once) | does this run's number move it? |
|---|---|---|---|
| **#311** four-page title/meta rewrite | clean since 2026-10-14 | **MISS** (posted 2026-11-13, window 2026-10-14 → 11-10): 0.937% vs bar ≥ 1.5% | No. This window (10-15 → 11-11): 53 clicks / 5,558 impressions = **0.954%**, position 6.58 impressions-weighted. Bar still not met; change 0.017 points, not material. Nothing posted. |

#311 pages, this window (GSC page mode): career-problems 991 impr / 22 clicks / 2.22% / pos 5.9; debilitated-sun 2,469 / 14 / 0.57% / 6.6; manglik-dosh 489 / 3 / 0.61% / 6.8; jupiter-in-10th 1,609 / 14 / 0.87% / 6.9. Three of four are under 0.9% CTR at 6.6–6.9; the one page above 2% also moved to position 5.9 (bar's "unchanged position" condition not held).

### Pending — pending notes already posted, nothing posted this run

| issue | deploy | scoreable from | note on this run's data |
|---|---|---|---|
| #685 sade-sati title | PR #690, 2026-11-03 | 2026-12-04 | window contains the deploy; not a score. `/learn/sade-sati/` now 1,923 impr / 13 clicks / 0.68% / 6.6 (previous 945 / 9 / 6.2). The bar (≥ 1.2% on ≥ 1,200 impressions, position within ±1 of 6.4) is not met on this mixed window. |
| #508 /matching title/meta | PR #696, 2026-11-03 | 2026-12-04 | see decay finding below |
| #553 panch-mahapurush CTA | PR #615, 2026-10-31 | 2026-12-01 | 9 organic sessions at 1.00 pages/session in this mixed window; floor is 10. |
| #426 sade-sati date correction (guard) | PR #673, 2026-11-02 | 2026-12-03 | window mixed; position 6.2 → 6.6 (within ±1), impressions up, not down. |
| #518 learn tool routes (five slices) | last slice PR #754, 2026-11-06 | 2026-12-07 | `/learn/*` organic landings: 306 sessions, 1.55 pages/session, bounce 45.4% (window mixes pre and post). Issue's secondary target was ≥ 2.0. |
| #835 debilitated-sun answer-first lede | PR #940, 2026-11-13 | 2026-12-14 | deployed after the end of this window; the numbers here are its **baseline** (see query table). |
| #528 /ask question out of URL | PR #801, 2026-11-09 | 2026-12-10 | window mixed. |
| #735 admin pages off GA4 | PR #877, 2026-11-11 | 2026-12-12 | 20 `/admin/ops/` sessions in this window (above). |
| #570 / #782 cta_click event and export | PR #688 (2026-11-03) | partial history until 2026-12-01 | see event table. |

Closed with a thesis but a correctness metric rather than a traffic one (not scoreable from GSC/GA4, reported only): #959, #896, #885, #843 (self-described unscoreable at 14 sessions in 28 days), #978, #980, #966, #972, #397.

## 4. Confounds, named before any delta

| confound | detail |
|---|---|
| Concurrent ships on ranking pages | Merged PRs touching `/learn/*` or templates inside the window (from `gh pr list`): #521 (2026-10-25), #615 (10-31), #658 (11-01), #680 (11-02), #690 (11-03), #696 (11-03), #754 (11-06), #796 (11-09, seven learn meta descriptions shortened), #830 (11-09), #839 and #857 (11-10, Manglik copy), plus a mobile text-floor sweep across 14 templates on 11-12. Several pages took two or three changes, so no per-page delta here is attributable to one change. |
| Seasonality | Diwali was 2026-11-08 and the window contains it. Impressions also stepped up around 2026-10-23 → 10-26, before Diwali. Seasonality is not determined for any page; the exports hold no prior-year data. |
| Window mixing | The fetch reads one trailing window and cannot split a page at its deploy date (#490; `--page-daily` follow-up is #953, open). Every delta above is window vs window. |
| Page reachability | The window ends 2026-11-11. This run did not probe production; no check that any page was broken during the window. #266 (intermittent Groq failures) affects LLM routes, not the `/learn` pages ranked here. |
| Git history | The checkout is depth 1 (one commit visible), so `git log origin/main --since` cannot be used (#666, #974 open). The confound list is built from `gh pr list --state merged` instead. |
| Sample size | 703 sessions and 293 clicks in 28 days. Per-page GA4 rows of 3–25 sessions cannot carry a conclusion. |

## 5. Decay and CTR outliers

Decay (pages with ≥ 100 impressions in the previous window; position worse by ≥ 1.5 or impressions down ≥ 30%):

| page | impressions prev → now | position prev → now | clicks prev → now | confound |
|---|---|---|---|---|
| **/matching** | 320 → **97** (−69.7%) | **4.2 → 8.2** | 0 → 2 | title and meta rewritten 2026-11-03 under #508 (PR #696); `/matching` also changed by #750, #871/#888, #889/#892 chart changes. Page earned its rank only recently (the #508 issue records impressions 9 → 336, position 14.7 → 4.3), so 4.2 may have been a spike. The window cannot split at the deploy. **Not attributable.** |
| /learn/the-9-grahas-overview/ | 100 → 30 (−70%) | 7.9 → 9.4 | 0 → 0 | small base (100 impressions) |
| /learn/ashwini-nakshatra/ | 100 → 92 (−8%) | 5.7 → 7.7 | 1 → 1 | small base |
| /festivals | 239 → 290 | 29.8 → 32.5 | 0 → 0 | position 30+, not in the band |

Only `/matching` is a decay worth watching: a page that held 4.2 and now sits at 8.2 after its title was changed is exactly the shape #508 was written to test. **No new issue filed:** the verdict on #508 arrives 2026-12-04 from a clean window, and a title-only issue is held by the 2026-11-06 sync ruling quoted in #835 ("no new title-only issue until #685 is scored").

CTR outliers (compared with the band's own median of 0.87% on pages with ≥ 100 impressions):

| page | impressions | CTR | position | read |
|---|---:|---:|---:|---|
| /learn/debilitated-sun-career/ | 2,469 | 0.57% | 6.6 | below band median; #835 deployed after this window, so this is its baseline |
| /learn/sade-sati/ | 1,923 | 0.68% | 6.6 | below band median; #685 pending |
| /learn/manglik-dosh/ | 489 | 0.61% | 6.8 | below band median; part of #311 |
| /learn/planets-in-7th-house-marriage/ | 882 | 0.79% | 6.2 | below band median; no open scoring issue |
| /learn/jupiter-in-10th-house-career/ | 1,609 | 0.87% | 6.9 | at band median |
| /learn/rahu-mahadasha-career-problems/ | 991 | 2.22% | 5.9 | above median; also the one position-5.9 page in the top 10 |
| /learn/10th-lord-in-6th-house-career/ | 632 | 2.53% | 6.6 | above median at unchanged-looking position |
| /learn/mercury-remedies/, /learn/saturn-remedies/ | 176, 183 | 2.84%, 2.73% | 6.2, 7.1 | above median |

Risers worth stating: `/learn/gochar-2026-planetary-transits/` 16 → 1,147 impressions (position 6.9 → 6.2), `/learn/jupiter-in-10th-house-career/` 358 → 1,609, `/learn/7th-lord-placement-marriage-guide/` 222 → 1,305. These are queries and impressions growth, not clicks: 16, 14 and 13 clicks respectively.

## 6. Query view (partial: 14% of impressions)

| query (2026-10-15 → 11-11) | impressions | impressions prev | clicks | position | position prev |
|---|---:|---:|---:|---:|---:|
| rahu mahadasha ketu antardasha | 383 | 248 | 11 | 7.3 | 9.6 |
| sun debilitated in which sign | 231 | 0 | 0 | 8.3 | none |
| sun is debilitated in which sign | 109 | 0 | 0 | 7.6 | none |
| jupiter in 10th house | 90 | 0 | 0 | 10.1 | none |
| 10th lord in 6th house | 85 | 0 | 2 | 8.4 | none |
| sun debilitated sign | 72 | 2 | 0 | 6.3 | 3.0 |
| rahu mahadasha and ketu antardasha | 65 | 42 | 0 | 7.5 | 9.5 |

The two "which sign" queries total 340 impressions and 0 clicks in this window; that is the baseline for #835. `sun debilitated sign` moved from position 3.0 to 6.3, but on a base of 2 previous impressions, which cannot carry a conclusion.

## 7. Funnel and events (2026-10-15 → 11-11, `/tmp/ga4-events.json`, 4,725 events, 703 sessions)

| event | count | note |
|---|---:|---|
| page_view | 1,215 | 1.73 per session in the channel table |
| session_start | 700 | |
| feature_view | 698 | |
| form_start | 140 | |
| ask_answered | 133 | |
| kundli_generated | 55 | 39% of `form_start`; `form_start` is not split by form, so this ratio mixes /kundli, /matching and /numerology |
| cta_click | 12 | from 2026-11-03 only; 8 of 12 have `(not set)` for both from and to path |
| subscribe_completed | 1 | |
| form_submit | 1 | |
| feedback_sent | 2 | |

`cta_click` rows with a path (window, partial history): `/learn/career-during-sade-sati/` → `/` 1; `/learn/kaal-sarp-dosh/` → `/kaal-sarp-check` 1; `/learn/name-numerology-explained/` → `/numerology` 1; `/learn/rahu-mahadasha-ketu-antardasha/` → `/dasha` 1. **Eight clicks carry no path**, so the split is unreadable for two thirds of the event; the total of 12 stands.

Funnel step by landing (organic, GA4): `/muhurat/griha-pravesh/` 23 sessions at 9% bounce and 2.26 pages/session is the strongest landing for onward use; `/learn/*` as a whole is 430 of 703 sessions and the 1.55 pages/session figure above. Not determinable: where kundli, matching and numerology users drop between landing, form and result, because `form_start` and `kundli_generated` are not split by feature in the export. The single measurement that would settle it is `fetch_ga4.py --events` broken down by the `feature` parameter on `form_start`.

## 8. Actions taken this run

| action | target |
|---|---|
| comment posted (score, once) | #276 |
| comment posted (unscoreable, once), then corrected in place for one misplaced PR number | #329 |
| comments not posted (unchanged verdict) | #311 (MISS stands, 0.954% vs 0.937%) |
| comments not posted (pending note already exists) | #685, #508, #553, #426, #518, #835, #528, #735, #570 |
| issues filed | none: no finding needs action that is not already owned by an open issue or held by the sync ruling on title-only tests |

## 9. What I could not determine, and the one measurement that would settle each

| question | why not | settling measurement |
|---|---|---|
| Whether the page-level lifts after a ship are the ship | the fetch cannot split at the deploy date | `fetch_gsc.py --page-daily` committed per night (#953) |
| Why `/matching` fell from 4.2 to 8.2 | window mixes the #508 title change with other changes and a recent rank spike | `/matching` daily position from #953 across 2026-11-03 |
| What drove the 11-06 (59) and 11-10 (43) session spikes | daily export has no channel | `ga4-daily` split by `sessionDefaultChannelGroup` |
| Whether Direct (296 sessions, 75% bounce) is people | exports show no source or hostname | GA4 `sessionSource` and `hostname` split for Direct |
| Whether any top-10 page can reach position ≤ 5 | position is a page average across queries; query view is 14% of impressions | per-query positions for the top-10 pages (needs `--by query` with a page filter) |
| Seasonal effect of Diwali on the 10-26 → 11-11 plateau | no prior-year window in the exports | the same window one year on (not available before 2027-11) |
