# Analyst report — 2026-11-02 run

**Window for every number unless a row says otherwise: 2026-10-03 → 2026-10-30** (28 days; last 3 days excluded because GSC lags 2–3 days and GA4 24–48h). Prior comparison window where stated: **2026-09-05 → 2026-10-02**.

Read-only run. Numbers below were read from `/tmp/gsc-band.json`, `/tmp/gsc-all.json` and `/tmp/ga4.json`. Where I also used `/tmp/gsc-trend-page.json`, `/tmp/gsc-trend-query.json`, `/tmp/gsc-daily.json` and `/tmp/ga4-daily.json` (staged by the same run, not named in the task) the row says so. I did not call any API.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated |
|---|---|---|---|---|
| `gsc-band.json` | **page** | 2026-10-03 → 10-30 | 100% of 15,940 impressions; **emitted 98 rows = 83% (13,286 impr.)** | no |
| `gsc-all.json` | **page** | same | 100% of 15,940 impressions, 133 pages | no |
| `gsc-trend-page.json` | page | now vs 2026-09-05 → 10-02 | 100% | no |
| `gsc-trend-query.json` | **query** | same | **11%** (1,823 of 15,940 impr.) — partial; Google withholds the rest | no |
| `ga4.json` | landing × channel | same | 100% of 479 sessions (480 in rows); 112 rows, 74 landings (67 distinct paths after folding query strings and trailing slashes, by my fold) | no |

- **"Band" in this report means pages by average position, not queries.** A page's `position` is the average across its queries. Nothing below is a statement about any single query except §1b.
- `ga4-daily.json` sums to **481** sessions against 479 in `ga4.json`. A 2-session gap; I did not resolve it.
- `gsc-band.json` omits `/learn/career-during-sade-sati/` (666 impr., 9 clicks) though `gsc-trend-page.json` shows its position as 6.0 (previous window 7.7). I infer the unrounded value is just under 6; the 98 vs 99 band-page count between the two files is that one page.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression queries."*

### 1a. Band, by page (window 2026-10-03 → 10-30; coverage 100%, page average position)

| | now (10-03 → 10-30) | prior (09-05 → 10-02) | source |
|---|--:|--:|---|
| pages at position 6–20 (band file) | **98** pages, 13,286 impr., 137 clicks, CTR 1.03% | — | `gsc-band.json` |
| pages at position ≥ 6 and ≤ 20 (trend file, rounded) | 99 pages, 13,952 impr. | 103 pages, 7,089 impr. | `gsc-trend-page.json` |
| pages at position < 6 (top-5-ish) | **26** pages, 1,770 impr. | **33** pages, 518 impr. | `gsc-trend-page.json` |
| pages at position > 20 | 8 pages, 256 impr. | not computed | `gsc-all.json` |
| whole property | 15,940 impr., 173 clicks (1.09%) | 8,202 impr., 86 clicks (prior-window row sums) | `gsc-all.json`, `gsc-trend-page.json` |

| reading | finding |
|---|---|
| Band size | The band holds 83% of impressions. Its page count is flat (99 vs 103), its impressions are up 97% (13,952 vs 7,089). |
| Top-5 pages | **Fewer** pages sit under position 6 now (26 vs 33), though they carry 3.4× the impressions (1,770 vs 518). No sign the band is moving into the top 5. |
| Objective status | **Not measurable as written.** The objective names *queries*; the query view covers 11% of impressions (§1b). By page, the band did not move up — it grew in volume at the same positions. |

### 1b. The ten highest-impression queries (window 2026-10-03 → 10-30; **coverage 11%**, partial)

| query | impr. now | impr. prior | clicks now | position now | position prior |
|---|--:|--:|--:|--:|--:|
| rahu mahadasha ketu antardasha | 314 | 140 | 8 | 8.6 | 9.7 |
| sun debilitated in which sign | 113 | 0 | 0 | 7.6 | — |
| rahu ketu antardasha | 60 | 9 | 0 | 9.0 | 8.4 |
| rahu mahadasha and ketu antardasha | 53 | 23 | 0 | 8.8 | 9.3 |
| sun debilitated sign | 46 | 2 | 0 | 6.0 | 3.0 |
| sun is debilitated in which sign | 45 | 0 | 0 | 7.2 | — |
| rahu mahadasha ketu antardasha remedies | 42 | 25 | 0 | 8.8 | 8.4 |
| rahu dasha ketu antardasha | 36 | 11 | 0 | 9.5 | 10.6 |
| 10th lord in 6th house | 35 | 0 | 2 | 8.5 | — |
| ketu antardasha in rahu mahadasha | 34 | 20 | 1 | 8.1 | 9.8 |

- **0 of these 10 sit at position ≤ 5.** Best is 6.0.
- These 10 are the top 10 *of the 11% the API returns*, not the site's top 10. They carry 10.8% of the property's impressions (sum 778 of 15,940; I summed the table). Do not read them as the objective's "ten highest-impression queries".
- `sun debilitated sign` fell from 3.0 to 6.0 on 46 vs 2 impressions; the prior position rests on 2 impressions and is not a measurement.

### 1c. Band list by opportunity (window 2026-10-03 → 10-30; `gsc-band.json`, page mode, top 15 of 98 of 83% coverage)

| # | page | impr. | clicks | CTR | pos | `band_opportunity` |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 2,829 | 35 | 1.24% | 6.8 | 134.7 |
| 2 | /learn/debilitated-sun-career/ | 1,878 | 11 | 0.59% | 6.5 | 101.7 |
| 3 | /learn/sade-sati/ | 1,685 | 10 | 0.59% | 6.4 | 91.1 |
| 4 | /learn/jupiter-in-10th-house-career/ | 738 | 3 | 0.41% | 7.1 | 41.3 |
| 5 | /learn/rahu-mahadasha-career-problems/ | 826 | 14 | 1.69% | 6.6 | 35.6 |
| 6 | /learn/panch-mahapurush-yoga/ | 564 | 5 | 0.89% | 6.8 | 28.8 |
| 7 | /learn/manglik-dosh/ | 500 | 4 | 0.80% | 6.9 | 26.0 |
| 8 | /learn/7th-lord-placement-marriage-guide/ | 523 | 8 | 1.53% | 7.5 | 23.4 |
| 9 | /learn/marriage-mahadasha-timing/ | 269 | 1 | 0.37% | 6.4 | 15.1 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 351 | 8 | 2.28% | 6.4 | 13.1 |
| 11 | /learn/kundali-matching-ashtakoot-guna-milan/ | 200 | 0 | 0% | 7.6 | 12.0 |
| 12 | /learn/mangal-mars-in-vedic-astrology/ | 225 | 3 | 1.33% | 7.7 | 10.5 |
| 13 | /learn/ | 146 | 0 | 0% | 11.1 | 8.8 |
| 14 | /rashifal | 145 | 0 | 0% | 8.8 | 8.7 |
| 15 | /learn/pushya-nakshatra/ | 177 | 2 | 1.13% | 7.3 | 8.6 |

- The top 3 pages are 6,392 of 13,286 band impressions (48%; summed from the table rows above).
- Not in the band file but worth naming: `/learn/career-during-sade-sati/` 666 impr., 9 clicks, position 6.0 (see §0).

## 2. Post-ship scores

Scored: issues closed since 2026-10-05 whose body carries both a `thesis:` and a `metric:` line. **That is 40 issues; only 6 have a metric GA4 or GSC can read.** Comments posted on those 6, each with its window, predicted and actual.

| issue | thesis (short) | predicted | actual (window 2026-10-03 → 10-30) | verdict | comment |
|---|---|---|---|---|---|
| **#311** title/meta on 4 band pages | rewriting title/meta lifts CTR toward the 2.05% sibling | combined CTR **≥ 1.5%** on ≥ 1,500 impr. | **0.81%** (32 / 3,942); prior window 0.60% (12 / 2,016); position 6.68 vs 7.33 | **MISS so far.** Not a pass; 0.81% is half the bar. Only `rahu-mahadasha-career-problems` clears it (1.69%, but its position also improved 7.9 → 6.6) | posted |
| **#276** /dasha CTA on Rahu–Ketu article | a CTA before the second heading lifts onward visits | organic pages/session **≥ 1.20**, ≥ 20 sessions | **1.47** on **38** organic sessions; folded all-channel 1.35 on 51 | **PROVISIONAL, not a pass.** Crossed the bar since the 10-31 score (1.17 on 30), but W is 11 pre-deploy days of 28 and cannot be split; the move came with new days, not new evidence about the CTA | posted |
| **#329** link Manglik checker | a link at "How to check" lifts onward visits | organic pages/session **≥ 1.30** on ≥ 10 sessions | **1.00** on **5** organic sessions (all channels 10, all 1.00) | **INCONCLUSIVE** — below the issue's own floor. The floor may never be reached at ~4 clicks / 28 days | posted |
| **#272** export channel + page dimensions | exports make organic and per-page band measurable | two columns exist and are populated | organic sessions **243** reported separately; ranking URL present **by page**; query-level coverage **11%** | **PASS on shape; query half NOT MET** | posted |
| **#515** rashifal nightly generation | removes the TPM ceiling and improves the prose | organic sessions to `/rashifal/*` + email re-open, 28 days post-deploy | **0** organic sessions to `/rashifal*`; 5 landings (Direct 4, AI Assistant 1); 15 pages, 202 impr., 0 clicks | **NOT SCOREABLE YET** — 6 full post-deploy days. Baseline is zero; rescore on a count | posted |
| **#514** rashifal layout fields | a per-rashi daily field gives visible variation | organic + email re-open, 28 days post-deploy | same as #515 (shared metric) | **NOT SCOREABLE YET.** The shipping PR is not stated on the issue | posted |

### The misses, stated plainly

- **#311 did not move CTR to its bar.** Four title/meta rewrites, one deploy (2026-10-13 17:29Z), and the pooled CTR is 0.81% against ≥ 1.5%. Two of four pages sit below the band's own CTR of 1.03%: `debilitated-sun-career` 0.59% on 1,878 impressions and `jupiter-in-10th-house-career` 0.41% on 738. Arithmetic bound: with ≥ 54% of the four pages' impressions post-deploy, a post-deploy-only rate of 1.5% would pool above 0.81%, and site-wide 71% of impressions were post-deploy. That assumes the four pages split like the site; it is an inference, not a per-page split. The loop should not file "rewrite more titles" on the strength of this idea.
- **#329's tool link shows no onward visits in the data we have** — pages/session is exactly 1.00 on all 10 sessions. 5 organic sessions cannot confirm or refute it. The metric as written is probably unscoreable; the thing to fix is the metric (#570 is open for the click event).
- **#276 is the only one trending toward a hit, and it is the one I trust least.** It flipped from 1.17 to 1.47 in two days on +8 sessions. I would not report it as a hit until the post-deploy half is read alone.

### Issues closed in the window with a `thesis:`/`metric:` that GA4/GSC cannot score (34; no comment posted)

| group | issues | why not scored |
|---|---|---|
| process / loop plumbing | #621, #607, #604, #602, #543, #495, #493, #450, #449, #442, #406, #405, #374, #358, #357, #338, #316, #313 (18) | metric is a gate, a test, a label or a workflow behaviour |
| security / correctness | #409, #408, #407, #373, #320, #398, #397 (7) | metric is occurrences in code or copy |
| observability / admin pages | #510, #396, #372, #369, #362, #355, #349, #345, #400 (9) | metric is a page's content or a token count |

I did not read each issue's whole body beyond its `thesis:`/`metric:` lines. #397 (`/matching` Nadi copy) has an on-site effect, but its metric is an occurrence count, not a traffic number.

## 3. Confounds

| confound | what I found (window 2026-10-03 → 10-30) | effect on the scores |
|---|---|---|
| **Impression surge, not explained** | GSC impressions averaged 426/day for 10-03..10-22 and ~1,003/day for 10-25..10-30 (daily file); 10-23 640, 10-24 757, 10-25 927. Clicks 4.5/day → 12/day. GA4 sessions 14.6/day (10-03..10-22) → 23.8/day (10-23..10-30). Position stayed 6.6–7.5 throughout. | Moves every page-level number in W. CTR was **flat across it** (1.04% before 10-23, 1.13% from), so the surge is volume at an unchanged click rate, not a rank change. |
| **The surge is concentrated** | Three pages carry +4,250 of the +7,776 net impression change vs the prior window: rahu-ketu (+1,769), debilitated-sun (+1,247), sade-sati (+1,234). | #311 and #276 are scored on exactly these pages. |
| **Concurrent ships on the same pages** | #451 (28 files, 10-21), #480 (10-22), #487 (10-23), #521 (10-25: debilitated-sun, jupiter-10th, 7th-lord, marriage-mahadasha, planets-in-7th), #530 (10-26), #556, #572, #579, #587, #590 (10-28..10-30, Manglik), #615 (10-31, after the window; career-problems among five files). Read from `gh pr list`; I did not diff each against these pages except #334, #342, #344 and #521. | #311's four pages: debilitated-sun and jupiter-10th were touched by #521; manglik-dosh by the Manglik series. **Cannot attribute any movement to one ship.** |
| **Seasonality** | Diwali is **2026-11-08** per the repo's own docs. Not sized: no prior-year data in the exports. The 10-23 onset sits 16 days before it. | Cannot be ruled in or out. Rises on `/learn/gochar-2026-planetary-transits/` (47 → 438) and `/learn/sade-sati/` (451 → 1,685) fit a calendar effect or a ranking change; I cannot tell which. |
| **Window straddles the deploys** | #334 deployed 2026-10-13 17:29Z, #342 2026-10-14 02:02Z, #344 2026-10-14 16:07Z. W holds 10–11 pre-deploy days and 16–17 post-deploy days. No page × day export exists (#490). | **No page-level score can use post-deploy days alone.** Every verdict above is a mixed-window read. |
| **Page reachability** | I did not test whether the pages served correctly during W. #253's stale stylesheet was fixed by #427 (2026-10-20 merge); #266 (Groq TPM) affects `/rashifal/*`, which has 0 organic sessions anyway. | Traffic to a broken page is not engagement; I have no evidence either way for the four scored learn pages. |
| **Sample size** | #329: 5 organic sessions. #276: 38. #311: 32 clicks over four pages (the Poisson noise on 32 is about ±6). | #329 is below its own floor; the others carry a verdict only at the stated confidence. |
| **Git history** | The checkout is shallow (`git rev-list --count HEAD` = 1); `git log origin/main --since=2026-09-05` returned one commit. | I substituted `gh pr list --state merged`. Filed as **#666**. |

## 4. CTR outliers (window 2026-10-03 → 10-30; `gsc-all.json`, page mode, position ≤ 8 and ≥ 200 impr.)

Compared against the band's own CTR (1.03%, 137 / 13,286), not a published table.

| page | impr. | clicks | CTR | pos | reading |
|---|--:|--:|--:|--:|---|
| /learn/kundali-matching-ashtakoot-guna-milan/ | 200 | 0 | 0% | 7.6 | 0 clicks on 200 impr.; expected ≈ 2 at the band rate |
| /matching | 343 | 1 | 0.29% | **4.4** | best-ranked page on this list, CTR a third of the band's; already filed as **#508** |
| /learn/marriage-mahadasha-timing/ | 269 | 1 | 0.37% | 6.4 | expected ≈ 2.8 |
| /learn/jupiter-in-10th-house-career/ | 738 | 3 | 0.41% | 7.1 | #311 page, title rewritten 10-13 |
| /learn/debilitated-sun-career/ | 1,878 | 11 | 0.59% | 6.5 | #311 page; expected ≈ 19 at the band rate |
| /learn/sade-sati/ | 1,685 | 10 | 0.59% | 6.4 | **not a #311 page** and has had no title test; expected ≈ 17 |

- `sade-sati` is the largest untested outlier: 1,685 impressions, 3rd on the band list, 0.59% CTR. Its impressions rose 451 → 1,685 between windows. I did not inspect its title.
- Page-mode caveat: a page averaging 6.4 may rank 1 for one query and 15 for another. Query data (11%) cannot say which.

## 5. Decay (page mode, window 2026-10-03 → 10-30 vs 2026-09-05 → 10-02)

No page with ≥ 100 impressions now lost more than 1 position. Biggest slips:

| page | impr. now / prior | position now / prior | Δ pos |
|---|--:|--:|--:|
| /learn/guru-jupiter-in-vedic-astrology/ | 113 / 77 | 7.5 / 6.6 | +0.9 (worse) |
| / | 144 / 73 | 5.9 / 5.1 | +0.8 (worse) |
| /learn/mangal-mars-in-vedic-astrology/ | 225 / 189 | 7.7 / 6.9 | +0.8 (worse) |
| /learn/debilitated-sun-career/ | 1,878 / 631 | 6.5 / 6.1 | +0.4 (worse; #311 page) |
| /learn/jupiter-in-10th-house-career/ | 738 / 272 | 7.1 / 6.7 | +0.4 (worse; #311 page) |

Largest impression losses:

| page | impr. now / prior | clicks now / prior | position now / prior |
|---|--:|--:|--:|
| /festivals | 245 / 590 (**-58.5%**) | 0 / 1 | 28.4 / 38.1 |
| /learn/shukra-venus-in-vedic-astrology/ | 122 / 177 | 0 / 2 | 6.0 / 5.6 |
| /learn/griha-pravesh-muhurat-2026-2027/ | 8 / 54 | 0 / 1 | 8.5 / 7.0 |
| /learn/planets-in-7th-house-marriage/ | 369 / 414 | 4 / 4 | 5.8 / 6.6 |

- **Not decay in the sense that matters:** the position slips are under 1 place, on pages of 113–225 impressions, in a window where site volume doubled. I would not file on them.
- **`/festivals` is the finding worth watching.** It lost 58.5% of impressions while its position *improved* 38.1 → 28.4; at position 28 it is outside the band and clicks are ~0, so the dollar value is small. But a festival calendar page with Diwali on 2026-11-08 should rise, not fall. Not filed: 245 impressions and 0 clicks is below what an issue needs, and I cannot tell seasonality from a ranking change.
- **The `griha-pravesh-muhurat-2026-2027` article** fell 54 → 8 impressions while GA4 shows it as the 4th-largest landing (18 sessions, 12 organic, bounce 72%, 1.0 pages/session) and `/muhurat/griha-pravesh` 14 sessions. The GSC drop and the GA4 sessions disagree in direction; I cannot reconcile them from page-mode data.

## 6. Funnel and engagement (GA4, window 2026-10-03 → 10-30; coverage 100% of 479 sessions)

| channel | sessions | bounce (session-weighted) | pages/session (session-weighted) |
|---|--:|--:|--:|
| Organic Search | 243 | 49% | 1.53 |
| Direct | 211 | 66% | 2.09 |
| AI Assistant | 19 | 37% | 3.16 |
| Unassigned | 7 | 86% | 0.29 |

| landing (folded) | sessions | of which organic | bounce | pages/session |
|---|--:|--:|--:|--:|
| / | 90 | 9 | 32% | 3.74 |
| /learn/rahu-mahadasha-ketu-antardasha | 51 | 38 | 51% | 1.35 |
| /kundli | 22 | 10 | 77% | 1.45 |
| /learn/griha-pravesh-muhurat-2026-2027 | 18 | 12 | 72% | 1.00 |
| /learn/rahu-mahadasha-career-problems | 17 | 16 | 53% | 2.00 |
| (not set) | 15 | 10 | 93% | 0.00 |
| /learn/sade-sati | 15 | 11 | 27% | 1.93 |
| /learn/debilitated-sun-career | 14 | 13 | 71% | 1.21 |
| /muhurat/griha-pravesh | 14 | 14 | 29% | 2.36 |
| /admin/ops | 13 | 1 | 62% | 1.46 |
| /matching | 13 | 1 | 69% | 2.23 |

- `/learn/*` landings: 284 sessions (59% of 479; 188 organic), pages/session **1.33** — against the homepage's 3.74. The learn pages are where organic traffic lands and where it stops.
- `/admin/ops` is 13 sessions in the property — owner traffic mixed into the totals; I cannot separate it. It is 2.7% of sessions.
- `/numerology` 10 sessions (1 organic) at 90% bounce, `/kundli` 22 at 77%: the tool pages bounce more than the articles that feed them. I did not break the funnel into landing → form → result → second page; the exports do not carry events (#570).
- Funnel steps cannot be read from these files at all; the single measurement that would settle it is a per-step event (see §7).

## 7. What I could not determine, and the one measurement that would settle each

| unknown | settles it |
|---|---|
| Whether the top-10 *queries* moved into the top 5 (the objective as written) | A query-level export with coverage near 100% — not available; Google withholds ~89% of impressions. Best available proxy: the page-level band, with the weakness in §1a. |
| What caused the impression surge from 2026-10-23 | A page × day GSC export (#490) to see which pages carry it, and a prior-year comparison for the festival-season explanation. |
| Whether #311, #276, #329 moved anything on post-deploy days only | The same export, read on or after 2026-11-13 (#311), 2026-11-14 (#276, #329). |
| Whether #276's CTA and #329's link were *used* | A click event on in-article tool links (#570). pages/session cannot show it. |
| What else shipped per path per day | Deeper git history in the analyst job (**#666**). |
| #515/#514's email re-open rate and the forbidden-planet share | Neither is in a GA4/GSC export; the latter is a blob measurement. |
| Whether the learn pages served correctly during W | A response-code and render check per page per day; I have none. |

## 8. Actions taken this run

| action | where |
|---|---|
| Posted scores | #311, #276, #329, #272, #515, #514 |
| Filed | **#666** — analyst job checks out at depth 1, so the required `git log origin/main --since` cannot run |
| Not filed, already covered | #490 (page × day export), #570 (click event), #508 (`/matching` CTR) |
| Not filed, below the bar for an issue | `/festivals` impression drop; position slips under 1 place |
| Changed code, content, templates or BACKLOG.md | none |

## 9. Corrections to my own work

- The #329 comment lists #579 and #590 among the PRs that "edited this page or its checker". I took that from their titles; I did not diff those two against `manglik-dosh.html`. #344 itself I did diff (it touched `manglik-dosh.html`).
- §2: 40 issues carry both a `thesis:` and a `metric:` line (checked by regex over 83 issues closed since 2026-10-05); 6 scored, 34 not (18 + 7 + 9 in the grouping table). The grouping is by title, not by reading each body.
