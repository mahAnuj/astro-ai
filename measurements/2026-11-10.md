# Analyst report — 2026-11-10 run

**Windows, stated once and used throughout.** Current **W = 2026-10-11 → 2026-11-07** (28 days; the last 3 days are excluded because GSC and GA4 lag). Prior **P = 2026-09-13 → 2026-10-10** (`/tmp/gsc-trend-page.json` `window_prev`). Every number below was read from `/tmp/*.json` this run.

**Coverage, read before any number**

| Export | Dimension | Coverage of W | Truncated | Note |
|---|---|---|---|---|
| `gsc-all.json` / `gsc-band.json` | page | 100% of 21,556 impressions (rows sum to 21,598) | no | Band prints 101 rows = 82% (17,606 impr) of the fetch |
| `gsc-trend-page.json` | page | 100% | no | 139 pages now, 126 in P |
| `gsc-trend-query.json` | query | **13%** (Google withholds anonymised queries) | n/a | Partial view. Never read it as the whole band |
| `ga4.json` | landing × channel | 100% of 603 sessions | no | 136 rows, 86 raw landings (80 after folding query strings and trailing slashes) |
| `ga4-events.json` | eventName | 4,101 events | no | `cta_click` exists only from 2026-11-03 04:42Z |
| `gsc-daily.json`, `ga4-daily.json` | date | 100%, 28/28 days with traffic | no | |

---

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

**The objective's literal unit is a query, and it cannot be measured here.** The query export covers 13% of impressions. The band below is by **page**, where `position` is a page's *average* across its queries, not any one query's.

| Whole site, GSC page, W vs P | W | P | Change |
|---|---|---|---|
| Impressions | 21,598 | 9,821 | +120% |
| Clicks | 254 | 103 | +147% |
| Site CTR | 1.18% | 1.05% | +0.13 pt |
| Pages with any impression | 139 | 126 | +13 |
| Pages new in W (`is_new`) | 47 | n/a | 316 impressions in total, so the new pages explain little of the rise |

| Band summary, GSC page, W | Value |
|---|---|
| Pages at average position 6–20 | 101 |
| Their impressions / clicks | 17,606 / 194 |
| Band share of site impressions | 82% |
| Band CTR (weighted) | 1.10% |
| Pages at position ≤ 5.0 | 15, with 623 impressions in total (2.9% of site impressions) |
| **Top-10 pages by impressions that are at position ≤ 5.0** | **0 of 10** |

The ten highest-impression pages in W sit at position 5.5–7.3. None is in the top 5, so the objective is not yet met.

| # | Page (top 10 by impressions, W) | Impr | Clicks | CTR | Pos | Pos in P | Impr in P |
|---|---|---|---|---|---|---|---|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 3,475 | 47 | 1.35% | 6.6 | 7.6 | 1,561 |
| 2 | /learn/debilitated-sun-career/ | 2,359 | 13 | 0.55% | 6.7 | 6.0 | 902 |
| 3 | /learn/sade-sati/ | 1,907 | 12 | 0.63% | 6.5 | 6.3 | 800 |
| 4 | /learn/jupiter-in-10th-house-career/ | 1,429 | 11 | 0.77% | 6.9 | 6.8 | 321 |
| 5 | /learn/7th-lord-placement-marriage-guide/ | 1,138 | 12 | 1.05% | 7.3 | 8.4 | 192 |
| 6 | /learn/rahu-mahadasha-career-problems/ | 958 | 20 | 2.09% | 6.1 | 7.3 | 835 |
| 7 | /learn/career-during-sade-sati/ | 943 | 14 | 1.48% | 5.5 | 7.3 | 380 |
| 8 | /learn/gochar-2026-planetary-transits/ | 886 | 12 | 1.35% | 6.1 | 7.1 | 17 |
| 9 | /learn/planets-in-7th-house-marriage/ | 703 | 7 | 1.00% | 5.8 | n/r | n/r |
| 10 | /learn/panch-mahapurush-yoga/ | 684 | 10 | 1.46% | 6.7 | n/r | n/r |

`n/r` means I did not read that figure this run.

Band, ranked by `band_opportunity` (the export's own score), first 8 only. The full 101-row list is in `/tmp/gsc-band.json`.

| Page | Impr | Clicks | CTR | Pos | band_opportunity |
|---|---|---|---|---|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 3,475 | 47 | 1.35% | 6.6 | 161.5 |
| /learn/debilitated-sun-career/ | 2,359 | 13 | 0.55% | 6.7 | not re-read (rank 2 in the file) |
| /learn/sade-sati/ | 1,907 | 12 | 0.63% | 6.5 | not re-read (rank 3) |
| /learn/jupiter-in-10th-house-career/ | 1,429 | 11 | 0.77% | 6.9 | not re-read (rank 4) |
| /learn/7th-lord-placement-marriage-guide/ | 1,138 | 12 | 1.05% | 7.3 | not re-read (rank 5) |
| /learn/gochar-2026-planetary-transits/ | 886 | 12 | 1.35% | 6.1 | not re-read (rank 6) |
| /learn/rahu-mahadasha-career-problems/ | 958 | 20 | 2.09% | 6.1 | not re-read (rank 7) |
| /learn/panch-mahapurush-yoga/ | 684 | 10 | 1.46% | 6.7 | not re-read (rank 8) |

**The step-change is in the daily series, and its cause is not determinable from these files.**

| Daily GSC / GA4, W | Impressions | Clicks | Sessions (GA4) | Avg position |
|---|---|---|---|---|
| 2026-10-11 → 10-24 (first 14 days) | 6,580 | 70 | 241 | 6.3–8.1 |
| 2026-10-25 → 11-07 (last 14 days) | 14,976 | 184 | 364 | 6.5–7.4 |

- Daily impressions ran at about 375–517 through 10-22, then 640 on 10-23 and 927 by 10-25, and about 1,050 from 10-27.
- Average position did not move (6.9–7.5 before, 6.5–7.4 after).
- The rise is therefore more impressions at the same average rank, not a better rank.
- Distinct queries seen rose from 192 to 581 (`keys_now` / `keys_prev`). That fits Google showing the pages for more queries. It is not proof.

---

## 2. Scores — closed issues that carried `thesis:` and `metric:`

A window is clean only if it starts on or after the deploy. W starts 2026-10-11, so any ship from 2026-10-12 onward cannot be scored this run.

**Nothing was scoreable and nothing was posted this run.** Every issue below already carries its one "pending — scoreable from …" note, written 2026-11-07/08. Re-posting would repeat the failure the 2026-11-06 rule exists to stop.

| Issue | Thesis (short) | Deploy (merge) | W clean? | First clean window readable | State |
|---|---|---|---|---|---|
| #311 | Title/meta rewrite on 4 band pages lifts CTR toward 2.05% | PR #334, 2026-10-13 | no (W starts 10-11, 2 pre-deploy days) | **2026-11-13** | pending note already posted |
| #276 | /dasha CTA on Rahu–Ketu article: pages/session ≥ 1.20 | PR #342, 2026-10-14 | no | **2026-11-14** | pending note posted |
| #329 | Manglik checker link: pages/session ≥ 1.30 on ≥ 10 sessions | PR #344, 2026-10-14 | no | **2026-11-14**, likely unscoreable (3 organic sessions in W) | pending note posted |
| #426 | Truth fix, guard: sade-sati position within ±1 of 6.2, impressions not down >20% | PR #673, 2026-11-02 | no | 2026-12-03 | pending note posted |
| #553 | /kundli link plus false claim removed: pages/session ≥ 1.30 on ≥ 10 sessions | PR #615, 2026-10-31 | no | 2026-12-01 | pending note posted |
| #685 | Sade Sati title names 3 Moon signs: CTR ≥ 1.2% on ≥ 1,200 impr | PR #690, 2026-11-03 | no | 2026-12-04 | pending note posted |
| #508 | /matching title shortened: CTR ≥ 1.0% on ≥ 300 impr | PR #696, 2026-11-03 | no | 2026-12-04 | pending note posted |
| #570 | `cta_click` events by from/to path exist | PR #688, 2026-11-03 | no | 2026-12-04 | see the `cta_click` row below |
| #518 | Route every learn article to a tool: share of articles with no route → 0; pages/session ≥ 2.0 | 5 slices, final PR #754, 2026-11-06 | no | 2026-12-07 | pending note posted |
| #782 | `ga4-events.json` exists after an `agent-measure` run | PR #785/#788, 2026-11-08 | n/a, deterministic | done | **HIT.** Scored on the issue 2026-11-09, closed. `/tmp/ga4-events.json` is present again this run |
| #272 | Organic channel and per-page band measurable | 2026-10-08 | yes | scored | Shape: PASS. Query-level half: **NOT MET**. Verdict unchanged across 5 earlier comments, so nothing posted |

**Observations I may report but must not score.** These are context only; W mixes pre- and post-deploy days.

| Item | What W shows | Why it is not a score |
|---|---|---|
| #311's four pages, W (debilitated-sun, jupiter-in-10th, manglik-dosh, rahu-career-problems) | 5,247 impressions, 47 clicks, 0.90% CTR. The issue's "before" was 16 / 2,251 = 0.71%. Average position moved 6.0→6.7, 6.8→6.9, 7.1→6.9, 7.3→6.1 | Two pre-deploy days in W. Impressions rose 2.3× for reasons I cannot isolate. The pass bar also needs position within ±1 of "today's", and debilitated-sun moved 0.7 and rahu-career-problems 1.2 |
| `cta_click`, W | **8** events (count only). `split_available: false`: every row reports `(not set)` for `from_path` and `to_path` | The two custom dimensions were registered 2026-11-08, and GA4 applies a dimension only to events collected after registration. #782's 2026-11-09 comment said the split can first appear in a run dated ≥ 2026-11-12. **I am not posting; re-check then** |
| #276 landing, W | `/learn/rahu-mahadasha-ketu-antardasha/`: 47 Organic sessions at 1.38 pages/session; Direct 13 at 1.00 | Window contains 3 pre-deploy days. Organic is above the 1.20 bar on 47 sessions (≥ 20, so the sample floor is met), but the bar cannot be attributed until the window is clean |
| #329 / #553 landings, W | manglik-dosh: 3 Organic sessions, pages/session 1.0. panch-mahapurush-yoga: 9 Organic sessions, pages/session 1.0 | Both are below the issues' own 10-session floor. #553's baseline was 4 sessions. Neither can be scored on traffic at this volume |

**Scoring scope.** The `thesis:`/`metric:` filter matched about 80 issues closed since 2026-09-26. Most are infra, security or ops issues whose metric is not a GA4/GSC number, and I did not score them. The traffic-metric ones are in the table above.

---

## 3. Confounds, named before any delta

1. **Concurrent ships.** 51 merged PRs in W touched `src/astro_ai/{templates,learn_registry,static,routes,main,i18n}`. Learn-page changes alone:
   - **10-24:** #512 (8 learn templates re-grounded), #516
   - **10-25:** #521 (5 articles routed to tools)
   - **10-26:** #530 (11 learn templates)
   - **10-28:** #556, #572
   - **10-31:** #615
   - **11-01:** #658
   - **11-02:** #673, #680
   - **11-03:** #690 (sade-sati title), #696 (/matching title)
   - **11-06:** #754 (31 learn templates)

   Ranking and CTR movement cannot be attributed to any one of them. The impression step-up (10-23 → 10-27) coincides with the first run of these edits, but it began *before* #512 and #521 landed, and position stayed flat.
2. **Seasonality.** I have no prior-year series. The window covers Navratri/Diwali-season search (Diwali is 2026-11-08, after W), so a seasonal contribution to the impression rise cannot be excluded. `/festivals` and the muhurat pages are the likeliest to carry it. The top pages are evergreen dasha, Sade Sati and career pages.
3. **Page reachability.** I did not probe production this run, so I cannot state it. Learn pages are static templates. Rashifal is the LLM-backed page that #266 showed failing under the Groq TPM ceiling, and it is not in the band.
4. **Sample size.**
   - 603 sessions and 254 clicks in 28 days.
   - Most per-page figures rest on 1–20 clicks. CTR on 2 clicks of 511 impressions is not distinguishable from noise.
   - Daily sessions run 5–59; the spikes of 42 (10-16), 34 (10-23) and 59 (11-07) are single days and not a trend.
5. **Internal traffic in GA4.** `/admin/ops` has 18 sessions (16 Direct, 1 Organic, 1 `?window=1`), 3.0% of all sessions. Direct includes them. Organic Search is not affected apart from the 1 row.

---

## 4. Decay and CTR outliers

**Pages losing ground, GSC page, W vs P, with both windows ≥ 50 impressions**

| Page | Pos W | Pos P | Impr W | Impr P | Clicks W / P | Reading |
|---|---|---|---|---|---|---|
| /festivals | 33.9 | 26.6 | 269 | 333 | 0 / 1 | Real decay, −64 impressions, the only large drop. Seasonal and date-keyed, so I treat it as watch, not an action |
| /learn/ashwini-nakshatra/ | 8.0 | 5.5 | 83 | 95 | 0 / not read | 2.5 places lost, small sample |
| /learn/ (index) | 11.0 | 13.5 | 125 | 122 | 0 / not read | Improved by 2.5, still outside the band |

**Pages that dropped out entirely (`is_gone`): 34 in all. Largest by prior impressions:**

| Page | Impr in P | Clicks in P | W |
|---|---|---|---|
| /learn/griha-pravesh-muhurat-2026-2027/ | 42 | 1 | **0 impressions** |
| /learn/career-not-progressing/ | 22 | 0 | 0 |
| /panchang/2026-09-21, 09-25, 10-07 | 8, 7, 6 | 0 | 0 (dated URLs expiring, expected) |

- **Unexplained:** `griha-pravesh-muhurat-2026-2027` shows zero GSC impressions in W. The same landing has 15 GA4 sessions in W (10 Organic, 4 Direct, 1 AI Assistant).
- A page cannot have organic sessions and zero impressions across one window unless the visits came very early or Google attributes the impressions to another URL. I cannot tell which from these files.
- A seasonal muhurat page losing its window is also plausible.
- Not filed as an issue, because the evidence is inconclusive. The measurement that settles it is a GSC URL-Inspection check for that URL and the per-day GSC series for that page, which no current export provides.

**Top 10 by impressions, ranked CTR (outliers against the band's own 1.10% weighted CTR)**

| Page | Impr | CTR | Pos | vs band 1.10% | Open or closed work |
|---|---|---|---|---|---|
| /learn/marriage-mahadasha-timing/ | 511 | **0.39%** (2 clicks) | **5.5** | 3.5× below, at a *better* position than the band | **none found** (issue search by slug returned nothing live) |
| /learn/debilitated-sun-career/ | 2,359 | 0.55% | 6.7 | 2× below | #835 open |
| /learn/mangal-mars-in-vedic-astrology/ | 360 | 0.56% | 7.5 | 2× below | none open |
| /learn/manglik-dosh/ | 501 | 0.60% | 6.9 | 1.8× below | #311 pending (this page is one of its four) |
| /learn/sade-sati/ | 1,907 | 0.63% | 6.5 | 1.7× below | #685 pending |
| /learn/jupiter-in-10th-house-career/ | 1,429 | 0.77% | 6.9 | 1.4× below | #311 pending |

- **No issue filed.** The standing items above already have an owner, either pending a score or open.
- `marriage-mahadasha-timing` is the only unowned one. Two clicks against about 5.6 expected at the band's rate is weak evidence, with a Poisson tail of roughly 8% (P(X≤2) at λ=5.6). I would re-check it in the next run, and file only if it is still under 0.6% on ≥ 500 impressions.
- **Query-level evidence for #835**, from the 13% partial query view: "sun debilitated in which sign" had 209 impressions and 0 clicks at position 8.2. "Sun is debilitated in which sign" had 102 impressions and 0 clicks at position 7.8. That is consistent with #835's thesis, but it is not new evidence.

---

## 5. Funnel and engagement

**GA4 by channel, W (landings folded; bounce and pages/session weighted by sessions)**

| Channel | Sessions | Bounce | Pages/session |
|---|---|---|---|
| Organic Search | 325 | 45% | 1.53 |
| Direct | 261 | 71% | 1.92 |
| AI Assistant | 12 | 33% | 4.00 |
| Unassigned | 5 | 80% | 0.40 |
| Total | 603 | n/r | n/r |

- Learn landings carry **258 of 325** Organic sessions (79%).
- The homepage `/` has 89 sessions (35% bounce, 3.94 pages/session), more than any article.
- Top Organic learn landing: Rahu–Ketu antardasha, 47 sessions at 34% bounce.
- **Weakest engagement:** `/learn/7th-lord-placement-marriage-guide` (18 Organic sessions, 1.11 pages/session), `/learn/10th-lord-in-6th-house-career` (14, 1.07) and `/learn/debilitated-sun-career` (16, 1.25).
- `/learn/7th-lord-placement-marriage-guide` was routed to a tool in PR #521 (merged 2026-10-25, the file list names that template). So 10 of W's 28 days are pre-routing, and its 1.11 pages/session mixes before and after. I did not check the other two pages against the five slices.

**GA4 events, W (2026-10-11 → 11-07, 4,101 events)**

| Event | Count |
|---|---|
| page_view | 1,049 |
| feature_view | 599 |
| ask_answered | 134 |
| form_start | 131 |
| kundli_generated | 53 |
| cta_click | 8 (partial history from 11-03) |
| form_submit | 1 |
| subscribe_completed | 1 |
| feedback_sent | 2 |

- 131 `form_start` against 53 `kundli_generated`: a 40% ratio. That is a loose proxy, because `form_start` is not specific to the kundli form, so I do not read it as a kundli-form completion rate.
- 1 `subscribe_completed` in 28 days.
- **I could not compute a per-funnel drop-off** (landing → form → result → second page). No export joins sessions across steps.

---

## 6. What I could not determine, and the one measurement that would settle each

| Unknown | The measurement |
|---|---|
| Whether any band **query** is moving into the top 5 (the objective's actual unit) | A query export with more than 13% coverage. Not recoverable from GSC; the achievable substitute is a fixed tracked-query list checked by position each week |
| What caused the 2.2× impression step-up from 10-23 | A per-page, per-day GSC series (`--by page --by date`). The current exports split by page or by date, never both |
| Whether `cta_click` fires on the intended links | GA4 `cta_click` split by `from_path` / `to_path`. First possible in a run dated ≥ 2026-11-12 |
| Why `griha-pravesh-muhurat-2026-2027` has 0 impressions with 15 GA4 sessions | GSC URL-Inspection for that URL, plus that page's per-day impressions |
| Whether #311, #276, #329, #426, #553, #685, #508, #518 worked | Clean windows. Earliest readable: #311 2026-11-13, #276/#329 2026-11-14, #553 2026-12-01, #426 2026-12-03, #685/#508/#570 2026-12-04, #518 2026-12-07 |
| Whether pages were reachable throughout W | A production probe sweep across W. This run did none |

**Posted to issues this run: none. Issues filed this run: none.** Every scoreable-or-pending issue already carries its single note, and the one new unowned outlier (`marriage-mahadasha-timing`) is below the evidence bar to file.
