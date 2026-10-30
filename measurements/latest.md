# Analyst report — 2026-10-30

**Read-only run.** Every number below was read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`, plus the sibling exports in the same directory that the fetch step wrote (`/tmp/gsc-trend-page.json`, `/tmp/gsc-daily.json`, `/tmp/ga4-daily.json`). No API was re-called. Git facts are from `git log origin/main` (after unshallowing the clone) and `gh issue`.

**Windows used throughout**

| Label | Dates | Source |
|---|---|---|
| **W** | 2026-09-30 → 2026-10-27 (28 days, last 3 excluded) | all three required files |
| **P** | 2026-09-02 → 2026-09-29 (28 days, prior) | `gsc-trend-page.json` (`window_prev`) |

**Coverage (read before any figure)**

| Export | Dimension | Coverage | Truncated |
|---|---|---|---|
| `gsc-all.json` (W) | `page` | 100% of 13,916 impressions; 131 rows | no |
| `gsc-band.json` (W) | `page`, position 6–20 | whole fetch 100%; **emitted 101 rows = 12,318 impr. = 89%** | no |
| `ga4.json` (W) | `landing × channel` | 100% of 438 sessions; 110 rows, 75 landings (69 distinct paths after folding query strings and trailing slashes) | no |

**Everything here is page-level, not query-level.** `position` is a page's average across its queries. Nothing in the three files lets me name a query.

---

## 1. The band against OBJECTIVE.md

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**What I can and cannot say about that sentence.** I cannot evaluate it as written: the export has no query dimension. I can evaluate its page-level equivalent (the ten highest-impression pages), stated as such.

### 1a. The band, W = 2026-09-30 → 2026-10-27

| | W | P (2026-09-02 → 09-29) |
|---|--:|--:|
| Pages at position 6–20 | **101** | 102 |
| Band impressions | **12,318** (89% of 13,953 row-impressions) | 6,315 |
| Band clicks (W) | 134 | 69 |
| Band CTR | 1.09% | 1.09% |
| Site total (impr. / clicks / CTR) | 13,916 / 153 / 1.10% | 7,700 / 77 / 1.00% |
| Median CTR, 20 band pages with ≥100 impr. | 1.05% | not computed |

The band is a count that did not move (101 vs 102 pages). Its volume roughly doubled (12,318 vs 6,315 impressions) with CTR unchanged at 1.09%, so the doubling is demand, not better results. Concentration: the top three pages hold 5,772 of 12,318 band impressions (47%).

### 1b. Band list, ranked by the export's `band_opportunity` (top 12 of 101; window W)

| # | Page | Impr. | Clicks | CTR | Position | Opportunity |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,591 | 30 | 1.16% | 7.0 | 125.5 |
| 2 | /learn/debilitated-sun-career/ | 1,653 | 7 | **0.42%** | 6.4 | 92.2 |
| 3 | /learn/sade-sati/ | 1,528 | 11 | 0.72% | 6.4 | 80.7 |
| 4 | /learn/rahu-mahadasha-career-problems/ | 774 | 12 | 1.55% | 6.8 | 34.4 |
| 5 | /learn/panch-mahapurush-yoga/ | 537 | 5 | 0.93% | 6.9 | 27.2 |
| 6 | /learn/jupiter-in-10th-house-career/ | 472 | 2 | **0.42%** | 7.1 | 26.3 |
| 7 | /learn/manglik-dosh/ | 492 | 4 | 0.81% | 7.2 | 25.5 |
| 8 | /learn/career-during-sade-sati/ | 542 | 9 | 1.66% | 6.4 | 23.5 |
| 9 | /learn/marriage-mahadasha-timing/ | 262 | 1 | **0.38%** | 6.6 | 14.7 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 320 | 5 | 1.56% | 7.7 | 14.2 |
| 11 | /learn/kundali-matching-ashtakoot-guna-milan/ | 187 | 0 | **0%** | 8.0 | 11.2 |
| 12 | /learn/10th-lord-in-6th-house-career/ | 268 | 7 | 2.61% | 6.8 | 9.1 |

### 1c. The objective's own test, at page level (W)

Ten highest-impression pages in W: 9,319 impressions, **67% of all 13,953 row-impressions**.

| Page | Impr. W | Pos. W | Pos. P | In top 5 (≤ 5.0)? |
|---|--:|--:|--:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 2,591 | 7.0 | 7.5 | no |
| /learn/debilitated-sun-career/ | 1,653 | 6.4 | 6.3 | no |
| /learn/sade-sati/ | 1,528 | 6.4 | 6.9 | no |
| /learn/rahu-mahadasha-career-problems/ | 774 | 6.8 | 8.2 | no |
| /learn/career-during-sade-sati/ | 542 | 6.4 | 7.7 | no |
| /learn/panch-mahapurush-yoga/ | 537 | 6.9 | — | no |
| /learn/manglik-dosh/ | 492 | 7.2 | 8.9 | no |
| /learn/jupiter-in-10th-house-career/ | 472 | 7.1 | 6.7 | no |
| /learn/planets-in-7th-house-marriage/ | 387 | 5.8 | 6.6 | no (closest) |
| /matching | 343 | **4.4** | 6.2 | **yes** |

**Result: 1 of 10 at page level, up from 0 of the same pages in P (matching was 6.2).** Seven of the ten gained 0.5–1.8 places (matching, manglik-dosh [not top-10 in P], career-problems, career-during-sade-sati, planets-in-7th-house-marriage, sade-sati, rahu-mahadasha-ketu-antardasha); `debilitated-sun-career` and `jupiter-in-10th-house-career` did not. `panch-mahapurush-yoga` has no P position in the trend file, so I make no claim on it.

Pages that moved to position < 6 in W (impr. ≥ 30; still not top 5 by the ≤ 5.0 rule): `/learn/planets-in-7th-house-marriage/` 6.6 → 5.8, `/learn/gochar-2026-planetary-transits/` 6.6 → 5.8, `/learn/vimshottari-dasha-explained/` 8.8 → 5.6, `/learn/2nd-lord-placement-wealth-guide/` 7.6 → 5.6, `/learn/chronic-health-issues-kundli/` 6.1 → 5.9. Pages that fell from < 6 into the band: `kaal-sarp-dosh` 5.3 → 6.2, `shukra-venus-in-vedic-astrology` 5.5 → 6.2, `jupiter-remedies` 5.8 → 7.3, `ashwini-nakshatra` 5.3 → 7.0 (all tiny: 33–140 impressions).

### 1d. North star: organic sessions, W = 2026-09-30 → 2026-10-27 (GA4, coverage 100% of 438 sessions)

| Channel | Sessions | Bounce (session-weighted) | Pages/session (session-weighted) |
|---|--:|--:|--:|
| Organic Search | **210** | 46.2% | 1.56 |
| Direct | 203 | 65.0% | 2.14 |
| AI Assistant | 19 | 42.1% | 2.63 |
| Unassigned | 7 | 85.7% | 0.43 |
| **Sum of rows** | 439 | | |

(Rows sum to 439 against the export's stated 438; I did not resolve the one-session difference.)

GSC clicks in W are 153; GA4 Organic Search sessions are 210. These are different measures (GA4 organic includes non-Google engines; GSC withholds nothing at page level but only covers Google). I did not reconcile them.

---

## 2. Post-ship scores (issues closed 2026-10-02 → 2026-10-30 that carry both `thesis:` and `metric:`)

58 issues closed in the period; 28 carry both fields. **Only five have a metric a GA4/GSC export can measure.** Comments were posted on the three that changed; the other two were re-read and unchanged.

### 2a. Scored against GA4/GSC this run

| Issue | Predicted (`metric:`) | Actual, W | Verdict | Comment |
|---|---|---|---|---|
| **#311** SEO: title/meta rewrite on 4 band pages | combined CTR **≥ 1.5%** on ≥ 1,500 impr., position within ±1 | **0.737%** (25 clicks / 3,391 impr.), position 6.70. Before (P): 0.554% (10 / 1,805), position 7.55 | **MISS so far.** Bar not near. Only `rahu-mahadasha-career-problems` clears 1.5% (1.55%) and it also gained 1.4 places. `debilitated-sun-career` CTR **fell** 0.75% → 0.42% while impressions tripled | posted, #311 |
| **#276** CTA before 2nd heading, Rahu–Ketu antardasha | organic pages/session **≥ 1.20**; < 20 sessions = inconclusive | **1.16 on 31 organic sessions** (all channels 42, 1.12). Before (from the issue, **not fetched**): 1.0 | **INCONCLUSIVE, not a hit.** One view short of the bar (31 × 0.16 ≈ 5 extra views vs 6 needed). Half of W is pre-deploy and cannot be split | posted, #276 |
| **#329** Manglik checker link on manglik-dosh | organic pages/session ≥ 1.30 on **≥ 10** sessions | **1.00 on 5 organic sessions** (all channels 11, 1.00) | **INCONCLUSIVE** (below sample floor). At 4 clicks/28 days the floor may never be reached | posted, #329 |
| **#272** export organic sessions + ranking URL | columns exist and populated | `sessionDefaultChannelGroup` on all 110 rows; Organic Search = 210 of 438 sessions; `page` dimension populated, coverage 100% | **PASS on shape.** Query-level half still unmeasurable | no new comment (unchanged since 2026-10-29) |
| **#515** nightly rashifal | organic sessions to `/rashifal/*` up, 28 days post-deploy | **0 organic** `/rashifal*` landings (5 sessions: Direct 4, AI Assistant 1); GSC all `rashifal` pages: 174 impressions, 0 clicks, `/rashifal` 134 impr., position 10.0 | **NOT SCOREABLE** — deploy 2026-10-24, 3 post-deploy days in W. Baseline is zero, so any rescore must require a count, not a direction | no new comment (unchanged) |

The 31.0% → < 5% forbidden-planet share (#515's other metric) is a blob measurement; the email re-open rate is in neither export. I scored neither.

**Why #276/#329/#311 cannot be settled yet.** The deploys are 2026-10-13/14; W holds 14 pre- and 14 post-deploy days. There is no page × day export (#490), so W cannot be split. The 28-day post-deploy window ends **2026-11-10/11**; earliest honest rescore **2026-11-13/14**. #570 (no click event on in-article tool links) means #276 and #329 can only ever be scored through pages/session.

### 2b. Not scored: metric is not in GA4/GSC

These carry a `thesis:` and a `metric:` that are repo or ops measurements (gates, counts, workflow outcomes). They are outside this role's data. **Not scored, not passed:** #286, #313, #316, #320, #338, #345, #349, #355, #362, #369, #372, #373, #374, #396, #397, #400, #405, #408, #409, #442, #449, #493, #495.

I did not check any of these against the tree this run, so this report neither confirms nor contradicts them. Several (#442, #493, #495) name outcome counts over a future window that `loop-outcomes` is the right instrument for.

### 2c. Hits

None this cycle on the traffic theses. That is a result, stated plainly: of the three traffic-metric ships measurable at all (#311, #276, #329), **none has demonstrated its lift**, and one (#311) is a miss by a wide margin.

---

## 3. Confounds (named before any delta)

| Confound | Evidence this run |
|---|---|
| **Concurrent ships touching the same pages in W** | #342 (10-14, Rahu–Ketu CTA), #344 (10-14, Manglik link), #334 (10-13, four-page title/meta), **#451 (10-21: edits 25 `templates/learn/` pages, incl. manglik-dosh, rahu-mahadasha-career-problems, rahu-mahadasha-ketu-antardasha)**, #512 (10-24, `manglik-remedies` etc. — **not** manglik-dosh), #530 (10-26, `rahu-mahadasha-career-problems`), **#521 (10-25: adds a tool link to debilitated-sun-career, jupiter-in-10th-house-career, 7th-lord-placement-marriage-guide, marriage-mahadasha-timing, planets-in-7th-house-marriage)**, #364 (10-15, 12px floor on learn cards), #312 (10-09, sticky CTA lift). Attribution to any single ship is not possible. |
| **Seasonality / demand** | Site-wide daily impressions (`gsc-daily.json`): 310–517/day for 2026-09-30 → 10-22, then **640, 757, 927, 931, 1,053** for 10-23 → 10-27, at an unchanged position (6.8–7.1). 5,729 impressions in the first 14 days, 8,187 in the last 14. Diwali is 2026-11-08 (CLAUDE.md); consistent with the calendar but **not attributed to a cause here.** The page-level jump (e.g. Rahu–Ketu 876 → 2,591 impr. at 7.5 → 7.0) is demand, not rank. |
| **Page reachability** | #253 (stale stylesheet for returning visitors) was fixed by #427 on **2026-10-20**, i.e. inside W; it affected returning visitors, not first-time search arrivals. #266 (intermittent LLM "high demand") affects `/kundli`, not `/learn/*`; **I have no uptime data for it this run.** |
| **Sample size** | 25 clicks across the four #311 pages; 31 organic sessions on the #276 page; 5 on the #329 page. A few clicks move CTR by ~0.1 pp; a single session moves #329's pages/session by 0.2. |
| **Own traffic in the denominator** | `/admin/ops` has 12 sessions (Direct 11, Organic 1) in GA4 W, and Direct is 203 sessions (46%) at 65% bounce. I cannot tell owner, monitor or bot visits apart from visitors in these files. Treat Direct-channel figures as contaminated. |

---

## 4. CTR outliers (W; compared with the band's own median CTR of 1.05% on the 20 band pages with ≥ 100 impressions)

| Page | Impr. | Clicks | CTR | Position | Reading |
|---|--:|--:|--:|--:|---|
| /learn/debilitated-sun-career/ | 1,653 | 7 | **0.42%** | 6.4 | Position unchanged from P (6.3), CTR fell from 0.75% (4/534). Title/meta was rewritten by #311 and did not help. 12 GA4 sessions, pps 1.00 |
| /learn/jupiter-in-10th-house-career/ | 472 | 2 | 0.42% | 7.1 | Also in #311; P was 3 clicks/240 impr. |
| /learn/marriage-mahadasha-timing/ | 262 | 1 | 0.38% | 6.6 | Not in #311 |
| /learn/kundali-matching-ashtakoot-guna-milan/ | 187 | 0 | 0% | 8.0 | |
| /learn/guru-jupiter-in-vedic-astrology/ | 106 | 0 | 0% | 7.6 | |
| /learn/ (index) | 144 | 0 | 0% | 10.2 | |
| /rashifal | 134 | 0 | 0% | 10.0 | position fell from 6.8 (35 impr.) |
| **/matching** | 343 | 1 | **0.29%** | **4.4** | Page-one position, near-zero CTR. Already tracked as **#508** (open). Impressions 20 → 343 |
| /learn/chronic-health-issues-kundli/ | 139 | 0 | 0% | 5.9 | clicks 2 → 0 |

At position 4.4 a 0.29% CTR is the strongest outlier on the site and is the one with the clearest ceiling; it is #508's, not a new finding.

## 5. Decay

| Page | Impr. P → W | Position P → W | Clicks P → W | Reading |
|---|--:|--:|--:|---|
| /festivals | 753 → 238 | 39.5 → 26.5 | 1 → 0 | Impressions down 68% while position improved; page is far outside the band. Cause not determined |
| /learn/the-9-grahas-overview/ | 105 → 57 | 7.3 → 9.0 | 0 → 0 | lost 1.7 places |
| /learn/ashwini-nakshatra/ | 87 → 49 | 5.3 → 7.0 | 1 → 0 | lost 1.7 places |
| /learn/shukra-venus-in-vedic-astrology/ | 202 → 79 | 5.5 → 6.2 | 2 → 0 | impressions −61% |
| / (homepage) | 59 → 129 | 4.3 → 5.9 | 2 → 9 | lost 1.6 places but clicks 4.5× |

All decay is on pages with ≤ 253 impressions P-window; none involves a page carrying meaningful clicks. **Not a finding that needs action; recorded because a decay report that omits decay is not a report.** Only four pages lost ≥ 1.0 place with ≥ 40 impressions in both windows (the-9-grahas-overview, ashwini-nakshatra, vivah-muhurat-2027 7.4 → 9.7, homepage), and none is a top-10 page.

## 6. Funnel

The three files give landing, bounce and pages/session only. They contain no event for form submission or result view, so **I cannot measure landing → form → result → second page.**

What is visible (W, GA4, session-weighted, query strings folded):

| Landing | Sessions | Bounce | Pages/session | Note |
|---|--:|--:|--:|---|
| / | 90 | 32% | 3.75 | Direct 79, Organic 9, AI 2 |
| /learn/rahu-mahadasha-ketu-antardasha | 42 | 50% | 1.12 | top non-home landing |
| /kundli | 22 | 77% | 1.45 | Direct 12 (bounce 100%), Organic 10 |
| /learn/sade-sati | 15 | 27% | 1.93 | best-engaged big organic landing |
| /matching | 13 | 69% | 2.23 | Direct 10 |
| /numerology | 9 | **100%** | 1.00 | all Direct |
| (not set) | 13 | 92% | 0.00 | Organic 9, Unassigned 4 |

Learn-article landings are the dominant organic entry and are almost all at 1.0 pages/session: `debilitated-sun-career` 12 sessions at 1.00, `7th-lord-placement-marriage-guide` 10 at 1.00, `manglik-dosh` 11 at 1.00. That is the same dead-end shape #518 describes. I do not restate #518's own 1.32 vs 3.75 figures because I did not recompute them.

---

## 7. Issues filed

**None.** Reasons, so the absence is auditable:

| Candidate | Why not filed |
|---|---|
| /matching at 0.29% CTR, position 4.4 | Already open as #508 |
| #311 title/meta did not lift CTR | Recorded on #311 itself; the next move (a different title for `debilitated-sun-career`) is a product-manager spec, and I cannot complete an Evidence Block's `competing:` field without fetching rival pages, which this role does not do unprompted |
| In-article tool-link click event missing | Already open as #570 |
| No page × day export | Already open as #490 |
| `loop` workflow labels GSC pages as "queries" | Already open as #291 |

## 8. What I could not determine, and the single measurement that settles each

| Unknown | Measurement |
|---|---|
| Whether #311/#276/#329 worked | A page × day GA4 and GSC export (#490), or simply a fetch on/after **2026-11-13** when W holds only post-deploy days |
| Which queries make up the objective's "ten highest-impression queries" | A `--by query` export; the three files are page-level, and the query view is a partial sample |
| Whether the Direct channel (203 sessions) is real | A GA4 internal-traffic filter or a bot/hostname breakdown; nothing in these files splits it |
| Why impressions doubled from 2026-10-23 | A per-query breakdown by day. Calendar (Diwali 2026-11-08) is consistent but unproven |
| Why `/festivals` lost 68% of impressions | Query-level data for that page; position moved the other way |
| Whether the GA4 vs GSC click gap (210 organic sessions vs 153 clicks) is non-Google traffic or measurement | GA4 `sessionSource` split |
| Funnel drop-off in kundli/matching/numerology | Event-level GA4 export (form submit, result view) |
| 23 issues in §2b | The owner's own instruments; not this role's data |

## 9. Corrections made during this run

Two statements in my first draft of the #311 and #329 comments were wrong and were **edited in place** before the run ended: a date range mislabelled in #311 (`10-09..10-13` → `2026-09-30..10-13`), and a claim that #512 edited `manglik-dosh` (it edited only the sibling `manglik-remedies`; #451 is the one that touched `manglik-dosh`). Both checked against `git show --name-only`.

*analyst, read-only. No code, template, content or BACKLOG.md was edited.*
