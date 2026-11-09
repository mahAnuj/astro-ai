# Analyst report — 2026-11-09

All numbers read this run from `/tmp/*.json`. **Current window W = 2026-10-10 → 2026-11-06** (28 days, last 3 days excluded; GSC and GA4 both lag). **Previous window P = 2026-09-12 → 2026-10-09** (GSC trend files only; there is no GA4 previous window in this run).

Coverage, read first:

| export | window | dimension | coverage | truncated |
|---|---|---|---|---|
| `gsc-band.json` | W | page | 100% of 21,005 impressions; the band list prints 101 rows = 17,125 impressions (82%) | no |
| `gsc-all.json` | W | page | 100% (139 pages) | no |
| `gsc-daily.json` | W | date | 100% | no |
| `ga4.json` | W | landing × channel | 100% of 588 sessions (134 rows, 84 landings → 77 distinct paths after folding query strings and slashes) | no |
| `ga4-daily.json` | W | date | 28 of 28 days with traffic | no |
| `ga4-events.json` | W | eventName | 16 event names | no |
| `gsc-trend-page.json` | W vs P | page | 100% of W | no |
| `gsc-trend-query.json` | W vs P | query | **13%** of W impressions (partial view; Google withholds the rest) | no |

## 1. Headline vs OBJECTIVE.md (user base growth)

| metric | W (2026-10-10 → 11-06) | note |
|---|---|---|
| GSC impressions / clicks | **21,005 / 245** (CTR 1.17%) | `gsc-daily.json` |
| GSC, per-page rows summed, P → W | impressions 9,474 → 21,046 (**+122%**); clicks 102 → 245 (**+140%**) | `gsc-trend-page.json`; P is the sum of page rows, not a stated property total |
| GSC, first half vs second half of W | 10-10..10-23: 6,321 imp / 66 clicks → 10-24..11-06: 14,684 imp / 179 clicks | `gsc-daily.json`; the step is at 10-22 → 10-25 (517 → 927 impressions/day) |
| GA4 sessions | **588** (first half 233 → second half 357) | `ga4-daily.json` |
| GA4 channel mix | Organic Search 313 (53%), Direct 257 (44%), AI Assistant 13, Unassigned 5 | `ga4.json` |
| Organic sessions pages/session | 1.52 (sessions-weighted) | home 3.89 (86 sessions); `/learn/*` 1.33 (365 sessions) |
| Average GSC position | 6.3–8.1 daily, no trend | `gsc-daily.json` |

Reading: impressions and clicks more than doubled against P while position held at ~7. The growth is impression volume on already-ranking `/learn` pages, not a position gain.

**Confounds, named before any delta.**
- **Concurrent ships.** `gh pr list` shows 253 PRs merged in W; those that touch indexed pages or on-page text: #334 (4 band titles, 10-13), #342/#344 (CTAs, 10-14), #521/#615/#658/#680/#754 (tool routing in /learn, 10-25 → 11-06), #690 (sade-sati title, 11-03), #696 (/matching title, 11-03), #737 (skip link and `<main>`, 11-06), #688 (cta_click event, 11-03). The local clone is shallow (`git log origin/main` returns 1 commit), so this list comes from `gh`, not git. With this many ships no impression delta can be credited to one of them.
- **Seasonality.** Impressions climbed through the Diwali week (Diwali 2026-11-08; Dhanteras and Karva Chauth fall in W). The pages that rose most are evergreen (`rahu-mahadasha-ketu-antardasha`, `debilitated-sun-career`, `sade-sati`) and are not festival pages, so a pure festival effect is unlikely, but it is not excluded. Not determinable from these files.
- **Reachability.** `curl https://shubhagya.com/health` returned HTTP 200 from the runner this run. Individual pages were not probed.
- **Internal traffic.** `/admin/ops` took 18 GA4 sessions and `(not set)` 16 (bounce 93.8%) of 588 (#735 is open on this). Roughly 6% of sessions are not visitors.
- **Spike days.** GA4 sessions 10-16 = 42, 10-23 = 34, 11-06 = 59 against a ~20/day baseline. The per-day export has no landing dimension, so the cause is not determinable.
- **Sample size.** 245 clicks and 588 sessions in 28 days. Any page-level CTR below ~300 impressions is noise.

## 2. The 6–20 position band (W)

Page mode: a band `position` is the page's **average** across its queries. 24 pages in the band carry ≥ 100 impressions (15,831 impressions, 177 clicks). Median CTR of those 24 = **1.03%**; the band as a whole (101 pages) = 193 clicks / 17,125 impressions = 1.13%.

Top 12 by `band_opportunity` (the script's own ranking):

| page | impressions | clicks | CTR | avg position | P impressions → W | CTR vs band median |
|---|---|---|---|---|---|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,395 | 46 | 1.35% | 6.6 | 1,516 → 3,395 | 1.3× |
| /learn/debilitated-sun-career/ | 2,301 | 13 | **0.56%** | 6.6 | 871 → 2,301 | **0.55×** |
| /learn/sade-sati/ | 1,901 | 11 | **0.58%** | 6.5 | 755 → 1,901 | **0.56×** |
| /learn/jupiter-in-10th-house-career/ | 1,358 | 10 | 0.74% | 6.9 | 321 → 1,358 | 0.72× |
| /learn/7th-lord-placement-marriage-guide/ | 1,071 | 12 | 1.12% | 7.3 | 190 → 1,071 | 1.1× |
| /learn/gochar-2026-planetary-transits/ | 838 | 12 | 1.43% | 6.1 | 17 → 838 | 1.4× |
| /learn/rahu-mahadasha-career-problems/ | 964 | 20 | 2.07% | 6.2 | n/a | 2.0× |
| /learn/panch-mahapurush-yoga/ | 659 | 10 | 1.52% | 6.8 | 312 → 659 | 1.5× |
| /learn/manglik-dosh/ | 507 | 3 | **0.59%** | 6.9 | n/a | 0.57× |
| /learn/mangal-mars-in-vedic-astrology/ | 344 | 2 | 0.58% | 7.4 | n/a | 0.56× |
| /learn/10th-lord-in-6th-house-career/ | 517 | 13 | 2.51% | 6.6 | 170 → 517 | 2.4× |
| /learn/vimshottari-dasha-explained/ | 234 | 1 | 0.43% | 7.1 | 3 → 234 | 0.4× (n small) |

Also in the band: `/rashifal` 154 imp / 0 clicks at 8.4; `/learn/kundali-matching-ashtakoot-guna-milan/` 193 imp / 0 clicks at 7.8; `/learn/` 129 imp / 0 clicks at 11.2; `/kundli` 67 imp / 5 clicks at 8.9 (CTR 7.5%).

**CTR outliers (the title/meta fix, not content).** Low: `debilitated-sun-career`, `sade-sati`, `manglik-dosh`, `jupiter-in-10th-house-career` sit at 0.56–0.74% against the band median of 1.03%. All four are already under a test (see §3): #311 (debilitated-sun-career, manglik-dosh, jupiter-in-10th) and #685 (sade-sati). **No new issue filed**, because filing one would duplicate a pending test. Query-level signal for the debilitated-sun page, measured on the 13% query slice: `sun debilitated in which sign` 202 impressions / 0 clicks at 8.2, `sun is debilitated in which sign` 99 / 0, `sun debilitated sign` 68 / 0 — all new since P (0 impressions). That is a question a snippet can answer in the SERP. The 13% coverage means this describes the measured share only.

## 3. Post-ship scores (W; clean-window rule)

A window is clean only when it starts on or after the deploy date. Today minus 31 days = 2026-10-09, so **no shipped thesis has a clean window yet.** That is a finding, not a gap in the work.

| issue | thesis / metric | deploy | scoreable from | action this run |
|---|---|---|---|---|
| #311 | 4 band titles → combined CTR ≥ 1.5% on ≥ 1,500 impressions | PR #334, 2026-10-13 17:29Z | 2026-11-13 | pending note already posted 2026-11-08; nothing posted |
| #276 | /dasha CTA on rahu-mahadasha-ketu-antardasha | PR #342, 2026-10-14 | 2026-11-14 | pending note already posted; nothing posted |
| #329 | Manglik checker link | PR #344, 2026-10-14 | 2026-11-14, likely unscoreable | pending note already posted; nothing posted |
| #685 | sade-sati title names Moon signs | PR #690, 2026-11-03 | 2026-12-04 | pending note already posted; nothing posted |
| #508 | /matching title/meta | PR #696, 2026-11-03 | 2026-12-04 | pending note already posted; nothing posted |
| #518 | tool routing across /learn | slices 10-25 → #754 on 2026-11-06 | 2026-12-07 | pending note already posted; nothing posted |
| #515, #514, #523, #513 | organic + email re-open on `/rashifal/*` | 10-24 / not determined / 10-25 / 11-07 | **never at this traffic** | **posted once: "unscoreable at this traffic"** (1 organic `/rashifal*` session of 11 in W; 228 impressions / 0 clicks; email re-open is in neither export). Scoring stops. |
| #782 | cta_click export | n/a | n/a | commented once with live-run evidence (see §6) |

**Misses and partial results, stated plainly.**
- **#311 is a MISS on the data it can be read against.** The thesis predicted ≥ 1.5% combined CTR on ≥ 1,500 impressions; the earlier mixed-window reads were 0.85% on 4,489 impressions. This run's per-page CTRs for its pages: debilitated-sun-career 0.56% (2,301 imp), jupiter-in-10th 0.74% (1,358), manglik-dosh 0.59% (507), rahu-mahadasha-career-problems 2.07% (964). These are *mixed-window* numbers and are **not a score**. On this window the title rewrite did not move CTR on three of the four pages, while impressions on them rose 2–4× at flat position. Neither the earlier comments nor this report can call it final before 2026-11-13.
- **#276 and #329 are likely unscoreable.** The rahu-ketu page had 58 GA4 sessions in W (bounce 46.6%, 1.31 pages/session). `/learn/manglik-dosh` had 9 sessions (bounce 77.8%, 1.0 pages/session). `/kundli` took 26 landing sessions and `/matching` 13.
- **Learn pages/session = 1.33 in W** (365 sessions), against the target ≥ 2.0 set in #518 and 3.89 on the homepage. #518's last slice merged 2026-11-06, so this window holds almost none of it; the reading is a baseline, not a miss.
- Four rashifal theses (#513, #514, #515, #523) will never be scored with GA4 and GSC alone — the loop shipped them with a metric the analyst cannot read.

## 4. Decay (W vs P, page mode)

Pages with a position worse by ≥ 1.0 and ≥ 30 impressions in P:

| page | P imp → W | P pos → W pos | P clicks → W | reading |
|---|---|---|---|---|
| /learn/ashwini-nakshatra/ | 95 → 78 | 5.5 → 8.0 | 1 → 0 | **lost 2.5 positions**; small sample |
| /learn/the-9-grahas-overview/ | 98 → 38 | 7.9 → 9.2 | 0 → 0 | imp −61% |
| /learn/financial-struggles/ | 45 → 12 | 6.2 → 7.2 | 0 → 0 | imp −73% |
| /learn/vivah-muhurat-2027/ | 47 → 50 | 8.4 → 9.5 | 0 → 0 | flat volume, −1.1 pos |
| /learn/saturn-in-10th-house-career/ | 110 → 154 | 7.4 → 8.8 | 0 → 2 | clicks up despite position |
| /kundli | 31 → 67 | 7.5 → 8.9 | 1 → 5 | volume and clicks up |
| /festivals | 344 → 274 | 27.5 → 32.7 | 1 → 0 | outside the band, not recoverable by title work |

Largest impression falls: `sun-in-10th-house-career` 141 → 77 (position 7.2 → 7.0, clicks 1 → 3), `ketu-in-vedic-astrology` 61 → 10, `griha-pravesh-muhurat-2026-2027` 44 → 1 (position 7.7 → 6.0; a muhurat page whose 2026 season is ending), `career-not-progressing` 23 → 0 (gone).

None of these is a material decay on a page that carries traffic: the largest absolute loss is 70 impressions on one page. **No decay issue filed.** All of the above are < 100 impressions in P, so each is within noise.

## 5. Funnel (GA4, W, events file present this run)

| event | count (W) | note |
|---|---|---|
| page_view | 1,026 | |
| session_start | 586 | |
| feature_view | 592 | |
| form_start | 130 | |
| kundli_generated | 52 | 40% of `form_start`; **event ratio, not a user funnel** — `form_start` covers every form |
| ask_answered | 137 | |
| form_submit | 1 | looks unwired (130 starts, 52 kundlis, 1 submit); not determinable what it is attached to |
| subscribe_completed | 1 | |
| cta_click | 4 | exists only from 2026-11-03 04:42Z; partial history; split unavailable |

Landing sessions by tool (GA4, W): `/kundli` 26 (bounce 65.4%), `/matching` 13 (76.9%), `/numerology` 13 (84.6%), `/muhurat/griha-pravesh` 14 (21.4%). Tool-route landings = 85 of 588 sessions (14%).

## 6. What could not be determined, and the one measurement that settles each

| gap | settled by |
|---|---|
| Whether any title or CTA ship moved anything | the 2026-11-13 run for #311, 11-14 for #276 and #329 — their windows become clean then. A per-page × per-day GSC export (#490) would remove the wait. |
| `cta_click` from/to split | `split_available` is false this run; the two custom dimensions were registered 2026-11-08 and GA4 is not retroactive. Re-read in a run dated ≥ 2026-11-12. Comment posted on #782. |
| What caused the 10-16, 10-23 and 11-06 session spikes | a date × landing GA4 export |
| Whether the impression growth is seasonal | a year-over-year view; the property is too young, so not determinable |
| Rashifal thesis scoring (#513, #514, #515, #523) | an email-open count in `measurements/` and ≥ 30 organic `/rashifal*` sessions per 28 days |
| The whole band by query | not available; the query export covers 13% and Google withholds the rest |
| `form_submit` meaning | the event's wiring in the templates |

## 7. Issues and comments posted this run

| target | what | why |
|---|---|---|
| #515, #514, #523, #513 | one "unscoreable at this traffic" note each | the metric cannot be read from GA4/GSC; this closes the repeat-scoring loop |
| #782 | one comment: events file present, split still `(not set)`, re-check ≥ 2026-11-12 | first live run of AC3 |
| new issues | **none** | every material finding is already covered by an open or pending issue (#311, #685, #735, #782) |
