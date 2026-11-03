# Analyst report — run of 2026-11-03

**Window for every number below: W = 2026-10-04..2026-10-31** (28 days, last 3 excluded; GSC lags 2–3 days, GA4 24–48h). Prior window P = 2026-09-06..2026-10-03 where a delta is shown. All figures read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json`, `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json` (all fetched 2026-11-03 02:45Z). Closed-issue list, PR list and live-site probes were read this run via `gh`/`curl`.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated |
|---|---|---|---|---|
| gsc-band / gsc-all / gsc-daily | page / page / date | W | 100% of 16,606 impressions; band printed 101 rows = 84% (13,991 imp) | no |
| gsc-trend-page | page | W vs P | 100% of W impressions; **P total is the sum of P rows (8,323 imp, 88 clicks), P coverage is not stated by the export** | — |
| gsc-trend-query | query | W vs P | **12%** of W impressions — partial view, never used for whole-band claims | — |
| ga4 | landing × channel | W | 100% of 489 sessions (490 in rows); 117 rows, 79 raw landings, 72 after folding query strings and trailing slashes | no |
| ga4-daily | date | W | 28 of 28 days with traffic | — |

**The band file's grain is the PAGE, not the query.** `position` is each page's average across its queries. OBJECTIVE.md says *queries*; every 'query' sentence below is a page sentence. Query-level data covers 12% and cannot settle it.

## 1. The band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.* Measured at page grain, W = 2026-10-04..2026-10-31:

| measure | value (W) |
|---|---|
| pages at position ≤5 | 15 pages, 396 impressions (2.4% of 16,636) |
| pages at 5<pos≤20 | 111 pages, 15979 impressions (96.1%), 178 of 182 clicks |
| pages at position >20 | 8 pages, 261 impressions |
| band file (6.0–20.0) | 101 pages, 13,991 impressions, 149 clicks, CTR 1.06% |
| pages at 5.0<pos<6.0 (not in band file) | 10 pages, 1,988 impressions |

### The ten highest-impression pages (the objective's target set), W

| # | page | impressions | clicks | CTR % | position | in top 5? |
|---|---|---|---|---|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2916 | 33 | 1.13 | 6.8 | **no** |
| 2 | /learn/debilitated-sun-career/ | 1928 | 11 | 0.57 | 6.5 | **no** |
| 3 | /learn/sade-sati/ | 1754 | 11 | 0.63 | 6.4 | **no** |
| 4 | /learn/rahu-mahadasha-career-problems/ | 853 | 15 | 1.76 | 6.5 | **no** |
| 5 | /learn/jupiter-in-10th-house-career/ | 847 | 4 | 0.47 | 7.1 | **no** |
| 6 | /learn/career-during-sade-sati/ | 710 | 9 | 1.27 | 5.9 | **no** |
| 7 | /learn/7th-lord-placement-marriage-guide/ | 586 | 9 | 1.54 | 7.4 | **no** |
| 8 | /learn/panch-mahapurush-yoga/ | 564 | 6 | 1.06 | 6.9 | **no** |
| 9 | /learn/gochar-2026-planetary-transits/ | 508 | 7 | 1.38 | 5.9 | **no** |
| 10 | /learn/manglik-dosh/ | 493 | 4 | 0.81 | 6.9 | **no** |

**Top-5 count on the target set: 0 of 10. These ten hold 11159 of 16,636 impressions (67.1%) and 109 clicks (CTR 0.98%).** Two of them (career-during-sade-sati 5.9, gochar-2026-planetary-transits 5.9) are 0.9 positions from the line and are *not* in the band file, which starts at 6.0.

### Band list — top 15 by the script's `band_opportunity`, W

| # | page | impressions | clicks | CTR % | position | band_opportunity |
|---|---|---|---|---|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2916 | 33 | 1.13 | 6.8 | 142.0 |
| 2 | /learn/debilitated-sun-career/ | 1928 | 11 | 0.57 | 6.5 | 104.7 |
| 3 | /learn/sade-sati/ | 1754 | 11 | 0.63 | 6.4 | 94.2 |
| 4 | /learn/jupiter-in-10th-house-career/ | 847 | 4 | 0.47 | 7.1 | 46.8 |
| 5 | /learn/rahu-mahadasha-career-problems/ | 853 | 15 | 1.76 | 6.5 | 36.2 |
| 6 | /learn/panch-mahapurush-yoga/ | 564 | 6 | 1.06 | 6.9 | 27.8 |
| 7 | /learn/7th-lord-placement-marriage-guide/ | 586 | 9 | 1.54 | 7.4 | 26.2 |
| 8 | /learn/manglik-dosh/ | 493 | 4 | 0.81 | 6.9 | 25.6 |
| 9 | /learn/marriage-mahadasha-timing/ | 265 | 1 | 0.38 | 6.4 | 14.9 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 378 | 8 | 2.12 | 6.3 | 14.7 |
| 11 | /learn/mangal-mars-in-vedic-astrology/ | 252 | 3 | 1.19 | 7.6 | 12.1 |
| 12 | /learn/kundali-matching-ashtakoot-guna-milan/ | 202 | 0 | 0 | 7.7 | 12.1 |
| 13 | /learn/pushya-nakshatra/ | 184 | 2 | 1.09 | 7.4 | 9.0 |
| 14 | /rashifal | 150 | 0 | 0 | 8.7 | 9.0 |
| 15 | /learn/ | 142 | 0 | 0 | 11.3 | 8.5 |

## 2. Traffic level and shape (confound for everything in §3)

| measure | P (2026-09-06..2026-10-03) | W (2026-10-04..2026-10-31) |
|---|---|---|
| GSC impressions (page rows) | 8323 | 16636 |
| GSC clicks | 88 | 182 |
| GSC CTR % | 1.06 | 1.09 |
| GA4 sessions | **not fetched — no prior-window GA4 export this run** | 489 |

| sub-window (W split) | GSC impressions/day | GSC clicks | GSC CTR % | GA4 sessions/day |
|---|---|---|---|---|
| 2026-10-04..10-22 (19 d) | 430 (8,162 imp) | 85 | 1.04 | 14.7 (280) |
| 2026-10-23..10-31 (9 d) | 938 (8,444 imp) | 97 | 1.15 | 23.4 (211) |

Impressions per day ramp 517 (10-22) → 640 → 757 → 927 → 931 → 1,053 (10-27), then plateau 1,019–1,053. **Impressions more than doubled from 10-23 at essentially flat average position (daily average 6.6–7.1 over 10-23..10-31); GA4 sessions rose +59% per day.** The risers are a few pages (rahu-mahadasha-ketu-antardasha +1,809, sade-sati +1,267, debilitated-sun-career +1,264 = 4,340 of the +8,313 delta) and the query view (12% coverage) shows *new* queries at positions 6–9 (e.g. 'sun debilitated in which sign' 0→124 imp at 7.9, 'jupiter in 10th house' 0→41 at 10.2). **Cause not determined** — it is not attributable to any one ship (§4) and could be search demand, a Google re-ranking, or both. It is a rise in *reach*, not in rank: the objective's lever (position) did not move.

### GA4 by channel, W (landings aggregated, bounce and pages/session weighted by sessions)

| channel | sessions | bounce % | pages/session |
|---|---|---|---|
| Organic Search | 250 | 48.4 | 1.56 |
| Direct | 214 | 66.82 | 2.14 |
| AI Assistant | 19 | 36.84 | 3.16 |
| Unassigned | 7 | 85.71 | 0.29 |

North star (organic sessions) W: **250 of 489 (51%)**. GA4 Organic (250) exceeds GSC clicks (182) — GA4 counts every search engine; the two are not reconcilable from these files. **Direct (214, 44%) is not clean:** it includes `/admin/ops` landings and the `(not set)` landing (below), and the exports cannot separate owner/agent/bot traffic.

| internal / unattributable landing, W | channel | sessions |
|---|---|---|
| /admin/ops | Direct | 11 |
| (not set) | Organic Search | 10 |
| (not set) | Unassigned | 5 |
| /admin/activity | Organic Search | 1 |
| /admin/ops | Organic Search | 1 |
| /admin/ops?window=1 | Direct | 1 |

'AI Assistant' is a channel in its own right: **19 sessions, bounce 37%, 3.16 pages/session** — best-engaged channel on the site, at n=19.

### Top GA4 landings (folded), W

| landing | sessions | bounce % | pages/session |
|---|---|---|---|
| / | 92 | 34 | 3.83 |
| /learn/rahu-mahadasha-ketu-antardasha | 49 | 51 | 1.37 |
| /kundli | 22 | 77 | 1.45 |
| /learn/rahu-mahadasha-career-problems | 18 | 50 | 1.94 |
| /learn/debilitated-sun-career | 16 | 63 | 1.19 |
| /learn/sade-sati | 16 | 31 | 1.87 |
| (not set) | 15 | 93 | 0 |
| /learn/griha-pravesh-muhurat-2026-2027 | 15 | 73 | 1 |
| /admin/ops | 13 | 62 | 1.46 |
| /learn/gochar-2026-planetary-transits | 13 | 62 | 1.15 |
| /matching | 13 | 69 | 2.23 |
| /muhurat/griha-pravesh | 13 | 31 | 2.38 |

## 3. Scores — issues closed in the last 28 days with a `thesis:` and a `metric:`

43 closed issues (closed 2026-10-06 onward, read via `gh`) carry both fields. **8 have a metric a GA4/GSC reading can score; 35 have metrics that are repo, gate, test or loop-state assertions** (e.g. #607 '15 of 15 agent definitions carry the rule', #602 'a seventh test case') — a traffic export neither supports nor refutes them, so I do not score them and do **not** claim they pass.

| issue | closed | deploy (PR merged) | predicted | actual (W unless stated) | verdict |
|---|---|---|---|---|---|
| #311 title/meta, 4 band pages | 10-13 | #334, 2026-10-13 17:29Z; live titles confirmed on prod 2026-11-03 | combined CTR **≥1.5%** on ≥1,500 imp, position within ±1 | **34/4,121 = 0.83%**; P was 12/2,068 = 0.58%; issue's own baseline 16/2,251 = 0.71%. Positions 6.1→6.5, 6.7→7.1, 8.3→6.9, 7.9→6.5. **Three of four pages show no lift: debilitated-sun 11/1,928 = 0.57% (P 0.60%), jupiter-10th 4/847 = 0.47% (P 1.07%), manglik 4/493 = 0.81% (P 0.58%) — together 19/3,268 = 0.58% vs P 9/1,288 = 0.70%.** Only rahu-career-problems moved: 15/853 = 1.76% (P 3/780 = 0.38%) | **MISS so far.** 1.5% needs ~62 clicks on 4,121 imp; there are 34. W holds ~10 pre-deploy days. One page carries the whole gain, at n=15 clicks |
| #276 /dasha CTA, rahu-ketu antardasha | 10-14 | #342, 2026-10-14 02:02Z | pages/session **≥1.20** on ≥20 sessions | landing total **49 sessions, 1.37 pages/session** (Organic 36 sessions 1.50; Direct 13 sessions 1.00); bounce Organic 36% | **PROVISIONAL PASS on the pre-registered bar**, not attributed: W holds ~10 pre-deploy days (issue's baseline 1.0 on 29 sessions), Direct (n=13) shows no lift, and pages/session does not say the CTA was the click. `/dasha` onward-click data not in the exports |
| #329 Manglik checker link | 10-14 | #344, 2026-10-14 16:07Z | Organic pages/session **≥1.30 on ≥10 sessions**; <10 = inconclusive | Organic **4 sessions**, 1.00 pages/session (Direct 5 sessions, 1.00) | **INCONCLUSIVE by the issue's own floor** (n=4 <10). Confounded: #311 changed this page's title the day before, and 3 more PRs (#451, #556, #587) touched the template inside W |
| #426 sade-sati date correction (guard) | 11-02 | #673, 2026-11-02 12:18Z — **after W ended** | guard: position within ±1 of 6.2, impressions not down >20% in 28 days post-deploy; (a) greps return 0 | **Post-deploy GSC window does not exist yet.** Pre-deploy baseline in W: `/learn/sade-sati/` 1,754 imp, 11 clicks, position 6.4. (a) verified on prod 2026-11-03: both greps = **0**, `/health` build_sha 75a148b | **NOT SCOREABLE YET.** (a) PASS today; (b) first readable ~2026-12-03 (window 11-03..11-30 + 3-day lag) |
| #272 measurable north star | 10-08 | #292 | organic sessions as a separate number; ranking URL beside band entries | this run's `ga4.json` carries `channel` (Organic Search 250 sessions); `gsc-*.json` carries `page` | **PASS on shape** (as scored 2026-10-21). Query-level goal still unmet: query export is 12% |
| #514 rashifal computed fields | 11-01 | #516 (10-24), #524 (10-25) | organic + email re-open on `/rashifal/*`, 28 days post-deploy | GSC /rashifal pages: P 42 imp/1 click → W 210 imp/0 clicks (15 pages); GA4 /rashifal landings **5 sessions total**. Email re-open **not in GA4/GSC** | **NOT SCOREABLE YET** — 28-day window ends ≥2026-11-21 and one half of the metric is unreadable here |
| #515 nightly rashifal | 10-24 | #516, 2026-10-24 09:06Z | organic sessions to `/rashifal/*`, 28 days post-deploy | as above (5 sessions) | **NOT SCOREABLE YET** — same reason; n is far too small to carry a verdict even when matured |
| #345 trend on /admin/ops | 10-15 | #348 | band count + top-10 positions as a delta over a stated window | the delta data exists in this run's `gsc-trend-page.json` (impressions_prev / position_prev) | **NOT DETERMINED** — whether `/admin/ops` renders it needs an authenticated read I did not make |

**Misses are stated first on purpose.** #311 is the one ship that claimed to move the objective's own lever-adjacent metric (CTR in the band), and on this window it has not: 34 clicks against a bar of ~62, three of four pages flat or worse. It is not final — post-deploy days are ~18 of 28 and the 28-day post window closes 2026-11-10 — but nothing here supports the thesis yet. #329 and #276 are conversion changes, not band changes; #329 cannot be read at this traffic level.

## 4. Confounds, named

| confound | finding |
|---|---|
| **Concurrent ships** | `git log` is unusable (shallow clone: 1 commit visible), so read from `gh pr list --state merged`: **233 PRs merged since 2026-09-06; 68 touch `src/`, 57 of them merged inside W, 18 of those touching `learn/` templates or `learn_registry.py`.** Page-specific: rahu-career-problems #451 (10-21), #530 (10-26), #615 (10-31); debilitated-sun #480 (10-22), #521 (10-25); jupiter-10th #487 (10-23), #521 (10-25); manglik-dosh #344, #451, #556 (10-28), #587 (10-29); sade-sati #451, #572 (10-28); rahu-ketu #342, #451. **All four #311 pages were re-edited by at least one other PR inside W, so the CTR read cannot be attributed to the title change alone.** |
| **Query-mix shift** | Impressions doubled from 10-23 with new queries at positions 6–9. New low-intent impressions *lower* CTR for any page, so a flat CTR on a page whose impressions tripled (debilitated-sun 664→1,928) is weaker evidence of a failed title than it looks — and a rise is weaker evidence of a working one. Per-day, per-page data would separate it; not in the exports. |
| **Seasonality** | Not determinable from one 28-day window; no year-ago data (site is months old). `/festivals` fell 527→250 impressions at position 37.6→30.0 — outside the band and plausibly calendar. |
| **Was the page reachable?** | `/health` 200 on 2026-11-03, revision bhagya-00566-gh7, build_sha 75a148b (= latest main). `verify-production` concluded success on **all 40 runs returned** (query limit 40, so older runs not seen) since 2026-10-04. #253's stale-stylesheet fix (#427, SW stale-while-revalidate) merged 2026-10-20, so returning visitors in the first 16 days of W may have had stale CSS. #266 (Groq TPM) touches only `/rashifal/*`, which carries 5 GA4 sessions — it does not affect any band score above. GA4 had traffic on 28/28 days: no collection gap. |
| **Sample size** | Per-page clicks are single or low double digits (4, 4, 11, 15). #329 n=4, #276 Direct n=13, AI Assistant n=19. Treat per-page CTR differences below ~±0.5 pt as noise. |
| **Window mixing** | W starts 9–10 days before the #311/#276/#329 deploys. No per-page daily series is exported, so pre and post cannot be separated. This is why those scores say 'so far'. |

## 5. CTR outliers and decay

CTR outliers — band pages with ≥250 impressions and CTR below the band median of 0.84% (median of pages with ≥100 imp, n=23, from `gsc-band.json`). Gain = (band p75 CTR 1.69% − page CTR) × impressions, W:

| page | impressions | clicks | CTR % | position | clicks gained at p75 CTR |
|---|---|---|---|---|---|
| /learn/debilitated-sun-career/ | 1928 | 11 | 0.57 | 6.5 | ~21.6 |
| /learn/sade-sati/ | 1754 | 11 | 0.63 | 6.4 | ~18.6 |
| /learn/jupiter-in-10th-house-career/ | 847 | 4 | 0.47 | 7.1 | ~10.3 |
| /learn/manglik-dosh/ | 493 | 4 | 0.81 | 6.9 | ~4.3 |
| /learn/marriage-mahadasha-timing/ | 265 | 1 | 0.38 | 6.4 | ~3.5 |

- **debilitated-sun-career and jupiter-in-10th-house-career already had #311's title rewrite** and are still the 1st and 3rd largest CTR gaps: the rewrite did not close them (§3).
- **sade-sati is the second-largest gap (1,754 imp, 0.63%) and must not have its title/meta touched yet** — #426's guard metric measures it with title/meta held constant. A title test now would void that read.
- Zero-click pages with ≥100 impressions at positions 6–12 (all in W): kundali-matching-ashtakoot-guna-milan 202 imp @7.7; /rashifal 150 @8.7; /learn/ 142 @11.3; shukra-venus 137 @6.1; guru-jupiter 114 @7.5 — impressions with no clicks at n≥100 each.

Decay — pages with ≥100 impressions in **both** windows whose average position worsened by ≥1.0 (P→W): **none.** Small-n decay below that floor, P→W:

| page | position P→W | impressions P→W |
|---|---|---|
| /learn/ashwini-nakshatra/ | 5.3 → 7.6 | 88 → 57 |
| /learn/griha-pravesh-muhurat-2026-2027/ | 6.9 → 8.5 | 49 → 8 |
| /learn/the-9-grahas-overview/ | 7.4 → 9.1 | 104 → 53 |
| /learn/planets-in-7th-house-marriage/ | 6.5 → 5.8 (**improved**) | 448 → 342 (−24%) |

The last row is a position improvement with falling impressions — query-mix or demand, not decay. The three above it are under the 100-impression floor in at least one window; flagged, not concluded.

## 6. Funnel

| entry point (W) | sessions | bounce % | pages/session |
|---|---|---|---|
| /kundli | 22 | 77 | 1.45 |
| /matching | 13 | 69 | 2.23 |
| /numerology | 10 | 90 | 1.00 |

**Not determinable:** landing → form → result → second page. The GA4 export has landing × channel only, no event or step dimension, and every figure above is n ≤ 22. The settling measurement is a GA4 event export (form_start / result_view) for /kundli, /matching, /numerology over a trailing 28 days.

## 7. What I could not determine, and the one measurement that settles each

| unknown | settles it |
|---|---|
| Pre- vs post-deploy CTR/pages-per-session for #311/#276/#329 | per-page **daily** GSC and GA4 series (`--by page,date`), or wait for 2026-11-10 when a clean post-only window exists |
| Cause of the 10-23 impression doubling | query-level daily series for the 3 risers; the 12%-coverage query export cannot answer it |
| Whether #276's CTA drove the pages/session | GA4 click event on the CTA, or sessions landing on rahu-ketu with a `/dasha` second pageview |
| GA4 session delta vs prior window | a GA4 export for P (2026-09-06..2026-10-03) — not fetched this run |
| Owner/agent/bot share of Direct (214 sessions) | a GA4 internal-traffic filter, or a landing×hostname/IP-bucket export |
| #514/#515 email re-open | the email sender's own open-rate record — not in GA4/GSC |
| #345 /admin/ops rendering | an authenticated read of /admin/ops |

## 8. Issues filed

None. Considered and rejected: a sade-sati title/meta test (would void #426's guard); a new CTR-test issue for the other low-CTR band pages (#311 has not been scored final, and its first result is a miss — filing a repeat of the idea before it matures is the failure this role exists to prevent); an internal-traffic GA4 filter (a GA4 admin setting, not a repo change, and I could not size the inflation: 13 `/admin/ops` sessions plus an unmeasurable share of 214 Direct). Re-evaluate all three on 2026-11-10.

## 9. Comments posted this run

| issue | verdict posted | link |
|---|---|---|
| #311 | MISS so far | https://github.com/mahAnuj/astro-ai/issues/311#issuecomment-6594196069 |
| #276 | PROVISIONAL PASS, not attributed | https://github.com/mahAnuj/astro-ai/issues/276#issuecomment-6594196471 |
| #329 | INCONCLUSIVE (n=4 < 10) | https://github.com/mahAnuj/astro-ai/issues/329#issuecomment-6594196776 |
| #426 | NOT SCOREABLE YET (first score) | https://github.com/mahAnuj/astro-ai/issues/426#issuecomment-6594197041 |

**Not commented, deliberately:** #272 (PASS on shape already posted 2026-10-21 and still true), #514 and #515 (prior 'NOT SCOREABLE YET' comments stand; nothing new is readable), #345 (not determined — needs an authenticated read). The other 35 issues with a `thesis:`/`metric:` carry repo/gate/test metrics that GA4/GSC cannot score; no comment, and no claim that they pass.

**Re-posting note.** #311/#276/#329 were already scored daily by earlier runs; today's comments are one day's increment with unchanged verdicts. If these keep re-posting identical verdicts daily, the thread noise is a cost — consider scoring on change only. That is a process observation, not a finding I am filing.
