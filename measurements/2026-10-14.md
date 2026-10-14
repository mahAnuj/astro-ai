# Analyst report — 2026-10-14

**Window for every GSC/GA4 number: 2026-09-14 → 2026-10-11** (28 days; last 3 days excluded by the exporters).
Read this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. Nothing below comes from `BACKLOG.md` or an earlier comment except where a table says "source: issue comment".

## 0. Coverage — read before any number

| Export | Dimension | Property total | Rows account for | Truncated | Window |
|---|---|--:|--:|---|---|
| `gsc-all.json` | **page** (not query) | 10,081 impressions / 107 clicks | 101% (127 rows) | no | 2026-09-14 → 10-11 |
| `gsc-band.json` | page, position 6–20 only | 10,081 impressions | emitted 101 rows = **83%** (8,329 impr.) | no | 2026-09-14 → 10-11 |
| `ga4.json` | landing × channel | 281 sessions | 101% (283 in rows; 101 rows, 69 raw landings, **66 after folding `?query` and trailing `/`**) | no | 2026-09-14 → 10-11 |

- Everything is **page-level**. "Position" is a page's average across its queries. OBJECTIVE.md is written in *queries* ("ten highest-impression queries"); this export cannot say anything about individual queries. See §6.
- `debilitated-sun-career` (925 impr., position displayed 6.0) is **in `gsc-all.json` and missing from `gsc-band.json`** (the band filter apparently excludes it at the boundary). A band list built from the band file alone drops the page with the second-most impressions on the site.

## 1. The 6–20 band against OBJECTIVE.md

Objective: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

| Where pages sit (GSC, 2026-09-14 → 10-11, page mode) | pages | impressions | clicks | share of impr. |
|---|--:|--:|--:|--:|
| Position < 6 (already top 5) | 22 | 569 | 5 | 5.6% |
| **Position 6–20 (the band)** | **102** | **9,254** | **100** | **91.3%** |
| Position > 20 | 3 | 315 | 2 | 3.1% |
| Property total | – | 10,081 | 107 | – |

(Row-sum impressions are 10,138 vs property 10,081 — the 101% coverage; shares above use the 10,138 row total: 569+9,254+315.)

**The site's search traffic is the band.** 91% of impressions are at 6–20; only 569 impressions (5.6%) are in the top 5. Progress on the objective is not measurable yet: no earlier window is in this run's files, and the band is measured by page, not query.

### Top band pages, ranked by `impressions × achievable CTR gain` (GSC, 2026-09-14 → 10-11)

| # | Page | Impr. | Clicks | CTR | Avg pos | band_opportunity |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,635 | 28 | 1.71% | 7.5 | 70.1 |
| – | /learn/debilitated-sun-career/ *(missing from band file; from `gsc-all`)* | 925 | 6 | 0.65% | 6.0 | n/a |
| 2 | /learn/rahu-mahadasha-career-problems/ | 822 | 6 | 0.73% | 7.3 | 43.3 |
| 3 | /learn/sade-sati/ | 844 | 9 | 1.07% | 6.2 | 41.6 |
| 4 | /learn/manglik-dosh/ | 435 | 2 | 0.46% | 7.2 | 24.1 |
| 5 | /learn/planets-in-7th-house-marriage/ | 464 | 5 | 1.08% | 6.3 | 22.8 |
| 6 | /learn/jupiter-in-10th-house-career/ | 332 | 1 | 0.30% | 6.8 | 18.9 |
| 7 | /learn/panch-mahapurush-yoga/ | 345 | 3 | 0.87% | 6.7 | 17.7 |
| 8 | /learn/career-during-sade-sati/ | 391 | 6 | 1.53% | 7.3 | 17.5 |
| 9 | /learn/marriage-mahadasha-timing/ | 209 | 1 | 0.48% | 6.5 | 11.5 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 204 | 3 | 1.47% | 8.2 | 9.2 |

Not in the band but notable (same window): `/matching` 263 impr., 0 clicks, position 4.2 — top-5 position, zero clicks; `/festivals` 310 impr., 1 click, position 27.1.

### CTR outliers (GSC, 2026-09-14 → 10-11)

Comparator is the band's own median, not an external table: **0.80%** across the 19 band pages with ≥100 impressions (73 clicks / 6,809 impr. combined = 1.07%).

| Page | Impr. | CTR | vs band median 0.80% | Reading |
|---|--:|--:|---|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,635 | 1.71% | +0.91 pt | The only high outlier. Already addressed by #276 (CTA), unrelated to CTR. |
| /learn/debilitated-sun-career/ | 925 | 0.65% | −0.15 pt | #311 title test target, shipped 2026-10-13 |
| /learn/rahu-mahadasha-career-problems/ | 822 | 0.73% | −0.07 pt | #311 |
| /learn/manglik-dosh/ | 435 | 0.46% | −0.34 pt | #311 (and #329, see §2 confound) |
| /learn/jupiter-in-10th-house-career/ | 332 | 0.30% | −0.50 pt | #311 |
| /learn/marriage-mahadasha-timing/ | 209 | 0.48% | −0.32 pt | **not touched by any ship** |

Small-number caveat: 1 click is 0.30% on 332 impressions; none of the low rows is distinguishable from the band median at this size. The #311 4-page baseline (above) is 15 clicks / 2,514 impr. = **0.60%**, vs the band median 0.80%: below, but not by a margin these counts can carry.

### Organic traffic (GA4, 2026-09-14 → 10-11) — the north star

| Channel | Sessions | Share | Weighted bounce | Weighted pages/session |
|---|--:|--:|--:|--:|
| Organic Search | 138 | 49% | 35.5% | 1.65 |
| Direct | 107 | 38% | 54.2% | 2.83 |
| AI Assistant | 30 | 11% | 43.3% | 2.83 |
| Unassigned | 8 | 3% | 37.5% | 0.88 |
| **Total** | **281** | 100% | – | – |

- Organic sessions per GA4 = **138**; GSC clicks = **107**. They are different instruments and should not match (GA4 organic also includes non-Google engines); I do not treat the 31 gap as a finding.
- **"AI Assistant" is 30 sessions (11%) at 2.83 pages/session — better engagement than Organic (1.65).** It is the third-largest channel and appears in no objective, thesis or issue I could see. I cannot say which assistant or which pages from this export.
- Top landings, folded (GA4, 2026-09-14 → 10-11): `/` 63 sessions (3 organic, 4.56 pages/session); Rahu–Ketu antardasha 32 (30 organic, **1.03 pages/session**); rahu-mahadasha-career-problems 12; sade-sati 12; debilitated-sun-career 10.
- The Rahu–Ketu page alone is 30 of 138 organic sessions (22%).

## 2. Post-ship scoring — issues closed in the last 28 days with a `thesis:` and a `metric:`

Closed since 2026-09-16 with both fields: #338, #329, #320, #316, #313, #311, #286, #276, #272 (nine). Source for the list: `gh issue list --state closed`. #286's body has no thesis/metric of its own — the string appears only as a requirement bullet inside the issue text, so it carries **no score** (the validator it asked for shipped as #332/#333/#336).

**Headline: no traffic-thesis ship can be scored today. Three of four conversion/SEO ships deployed after the data ends, and the fourth is an instrumentation change that already passed.** This is a finding, not a gap in effort: the loop ships faster than the 28-day metrics mature.

| Issue | Closed (UTC) | Deployed (per issue comment) | Predicted (`metric:`) | Actual in this window | Post-deploy days in data | Verdict | Comment posted this run? |
|---|---|---|---|---|--:|---|---|
| #311 title/meta on 4 band pages | 2026-10-13 17:35 | PR #334, `686fe3a` | combined CTR ≥1.5% on ≥1,500 impr., position ±1 | baseline 15 clicks / 2,514 impr. = 0.60% | **0** | **NOT SCOREABLE** — earliest read ~2026-11-13 | no — already posted 2026-10-14 00:09Z with the same window; re-posting adds nothing |
| #276 dasha CTA on Rahu–Ketu page | 2026-10-14 02:08 | PR #342, `f1d7b6c` | pages/session ≥ 1.20, inconclusive if <20 sessions | baseline 1.03 (organic 30 sessions; all channels 32 sessions) | **0** | **NOT SCOREABLE** — earliest read ~2026-11-14 | yes — baseline comment |
| #329 Manglik checker link | 2026-10-14 16:13 | PR #344, `bc83d3d` | pages/session ≥1.30 on ≥10 sessions, else inconclusive | baseline 1.00 on 6 sessions (3 organic + 3 direct) | **0** | **NOT SCOREABLE** — and the sample bar may never be met (see below) | yes — baseline comment |
| #272 measurement dimensions | 2026-10-08 | `c9c0f2b` | two columns exist and are populated | channel column present; GSC `page` dimension present; 101% coverage | n/a | **PASS** (already scored 2026-10-09 and 2026-10-10; unchanged) | no |
| #338 loop outcomes + cost as data | 2026-10-14 18:39 | `491bbcb` serving (see §4) | `measurements/loop.json` on `main`, refreshed ≤24h of each scheduled run, ≥20 cycles; stale >48h or <20 = not a pass | file on `main`: yes. **23 rows**, 2026-10-08 → 2026-10-13. `generated_at` 2026-10-13T18:29:34Z | n/a | **PARTIAL** — 2 of 3 criteria met; "refreshed within 24h of each scheduled run" cannot be judged until the first scheduled `agent-measure` run after the merge finishes (run 38655194421, in progress at read time) | yes |
| #320 PDF out of history | 2026-10-13 | – | repo state | already scored 2026-10-14 00:09Z: HIT, residual disclosed | n/a | unchanged | no |
| #316 loop outcome report | 2026-10-11 | – | would-have-flagged 4 rows | already scored 2026-10-12 | n/a | unchanged | no |
| #313 workflow static gate | 2026-10-11 | – | reintroduced defects are caught | already scored 2026-10-12 | n/a | unchanged | no |
| #286 evidence validator | 2026-10-13 | – | no own thesis/metric | not scored | n/a | – | no |

### #338 detail (the only newly scoreable one) — file `measurements/loop.json`, read this run

| Fact | Value |
|---|---|
| Rows | 23 (≥20 required) |
| Date span | 2026-10-08 → 2026-10-13 |
| Outcomes | shipped 11, nothing 5, failed 4, **unknown 3** |
| Attribution | 18 from the run log, **5 `unattributed`** |
| `generated_at` | 2026-10-13T18:29:34Z — ~29 h before this read (2026-10-14 23:39Z). Under the 48 h staleness limit, but it predates the merge (2026-10-14 18:39Z), so no post-merge scheduled run has refreshed it yet |

- 3 of 23 rows have outcome `unknown` and 5 are unattributed: 8/23 = 35% of cycle rows cannot say what the cycle produced. The issue's metric only asks for ≥20 rows, so this does not fail it, but a page built on this data will inherit the gap.
- `cost.json`: the only dollar figure it holds is the flat $100/month Claude Max subscription; Google Cloud and OpenAI are `null` ("no figure readable"). Per-cycle cost is not separable. The "what does it cost" question in #338 is therefore answered for one line item out of five.

### #276 / #329 baselines recorded now (GA4, 2026-09-14 → 10-11)

| Page | Channel | Sessions | Pages/session | Bounce |
|---|---|--:|--:|--:|
| /learn/rahu-mahadasha-ketu-antardasha/ | Organic Search | 30 | 1.03 | 23.3% |
| /learn/rahu-mahadasha-ketu-antardasha/ | Direct | 2 | 1.00 | 100% |
| /learn/manglik-dosh/ | Organic Search | 3 | 1.00 | 100% |
| /learn/manglik-dosh/ | Direct | 3 | 1.00 | 100% |

- **#329's metric will most likely come back "inconclusive".** It needs ≥10 sessions in 28 days; the page had 6 sessions (3 organic) in the 28 days just measured. Absent a rise in impressions, the pass/fail bar is not reachable and the test as specified cannot succeed or fail. That is a design finding about the metric, not about the ship.
- #276's own bar (≥20 sessions) is met on organic alone (30).

## 3. Confounds — named before any delta

| Confound | State | Effect on scoring |
|---|---|---|
| **Concurrent ships** | `git log` is unavailable: the checkout is shallow (1 commit, `491bbcb`). Substituted `gh pr list --state merged` (merged ≥2026-09-14). PRs that change what a visitor sees on `/learn`, `/kundli` or `/rashifal`: #312 sticky CTA lifted above the tab bar (2026-10-09), #319 shloka serif on learn articles (10-10), #324/#321 `/kundli` autofocus and tile fixes (10-11), #303 `/rashifal` served from cache (10-09), #299 Hindi rashifal (10-08), #334 title/meta (10-13), #342 dasha CTA (10-14), #344 Manglik link (10-14). Source from a prior comment on #311: #124 Hindi `/hi/` URLs landed 2026-10-04..06 (not re-verified this run). | **#311 and #329 share `/learn/manglik-dosh/`.** #334 (title) deployed 10-13 and #344 (checker link) 10-14, a day apart. The two theses cannot be separated on that page, which #329 explicitly said not to do. #312 touched the learn-page CTA that #276 and #329 also act on. Neither effect can be attributed to one change. |
| **Seasonality** | Not determined. One window is available; no year-ago or prior-window file this run. The griha-pravesh muhurat pages (`/learn/griha-pravesh-muhurat-2026-2027` 10 sessions, `/muhurat/griha-pravesh` 7) show festival-season demand. Whether the window is festival-inflated is not determined. | Any traffic rise in the after-window may be the calendar. |
| **Was the page reachable?** | Checked live this run (2026-10-14 ~23:39Z): `/health` → `ok:true`, `revision` `bhagya-00443-7zn`, `build_sha` `491bbcb933f52f857f044209bb8258a0fdd2b0d2`. The six top band pages above all return HTTP 200 at 155–173 KB. The `manglik-check` string appears 4 times in the live Manglik article (was 2, nav and footer only, per #329's pre-fix measurement). New #311 titles are live on the four pages. | Pages are serving the shipped revision now. Whether they were working throughout the *measured* window (2026-09-14 → 10-11) is **not determined**: this run has no uptime history, and #266's intermittent Groq-TPM failures affect LLM pages, not these static `/learn` pages. |
| **Sample size** | Organic = 138 sessions in 28 days; beyond the top four folded landings (63, 32, 12, 12), no landing has more than 10 sessions. Page-level GSC CTR on <500 impressions moves by ±1 click = ±0.2–0.3 pt. | Most per-page deltas this size are noise. State "not enough data" rather than a verdict. |

## 4. Decay

**Cannot be determined from this run's inputs.** Decay needs two windows; the three files carry one window (2026-09-14 → 10-11), the checkout has no history (1 commit), and I am forbidden from quoting earlier windows' figures from `measurements/*.md` or comments as if fetched now. The single measurement that would settle it: run `fetch_gsc.py --by page --days 28` for the window 2026-08-17 → 2026-09-13 and diff per page against `gsc-all.json`.

## 5. Funnel (GA4, 2026-09-14 → 10-11)

| Step | Sessions | Pages/session | Note |
|---|--:|--:|---|
| Landing on /learn/rahu-mahadasha-ketu-antardasha | 32 | 1.03 | Zero onward visits in practice — what #276 targets |
| Landing on /kundli | 5 | 2.80 | Too small to read |
| Landing on /muhurat/griha-pravesh | 7 | 2.43 | – |
| `/` (Direct 54 + others; 63 folded) | 63 | 4.56 | 3 organic. The home page is mostly a direct/returning surface, not a search landing |

This export has no event or path-sequence dimension (as #272 comment 2026-10-07 notes). **Kundli / matching / numerology step-through (landing → form → result → second page) cannot be measured.** The single measurement that would settle it: GA4 `eventName` by `pagePath`, or custom events on form submit and result render.

## 6. What I could not determine

| Question | Why not | What would settle it |
|---|---|---|
| Whether the **ten highest-impression queries** moved toward the top 5 | Exports are page-level; GSC `--by query` covers ~9% of impressions | The objective should be restated in pages, or a query-level GSC export taken as a separate measure |
| Any decay | One window | Prior-window GSC export (§4) |
| Effect of #311, #276, #329 | 0 post-deploy days in the data | Re-run with window ending ≥ 2026-11-13 (#311), 2026-11-14 (#276), 2026-11-15 (#329) |
| Effect of the "AI Assistant" channel (30 sessions, 2.83 pages/session) | Export does not name the assistant or landing set | GA4 `sessionSource` × landing |
| Whether `loop.json` meets "refreshed within 24h" | First post-merge scheduled run was still in progress | Read `generated_at` after run 38655194421 commits |
| Seasonality | One window, no year-ago | Prior-year same-window GSC |

## 7. Issues filed this run

None. Nothing above reaches the bar for an Evidence Block that needs action today: #311/#276/#329 are waiting on time, not work. Two observations are recorded here rather than filed because their evidence is a single window: (a) `debilitated-sun-career` missing from `gsc-band.json` at position 6.0 — the band filter boundary; (b) the 30-session AI Assistant channel.

*analyst, read-only. Scores posted as comments on #276, #329 and #338.*
