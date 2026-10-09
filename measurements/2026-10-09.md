# Analyst report — 2026-10-09

**Window on every number: 2026-09-09 → 2026-10-06 (28 days, excludes the last 3 days).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API re-called.
Git history read from `origin/main` (unshallowed) for confounds. Production was **not** probed.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-09..10-06 | 101% of 8,790 impr. (rows sum 8,848); **band emitted 99 rows = 7,939 impr. = 90%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 133 rows | no | — |
| ga4 | landing × channel | same | 100% of 271 sessions; 99 rows, 67 landings (60 distinct paths after stripping query strings and folding trailing slashes) | no | bounce / pages-per-session are per channel; I weighted by sessions |

GSC total clicks 97; GA4 Organic Search sessions 130. They are different measures (GA4 includes non-Google engines); I do not equate them.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression **queries**."*
**This cannot be scored literally.** The export is by page; query-level data covers ~9% of impressions (per #272's measurement, not re-measured here). The band below is **pages**, and the objective's wording has not caught up (see §7).

### 1a. Band size (2026-09-09..10-06, `dimension: page`)

| measure | value |
|---|---:|
| pages with average position 6–20 | 99 |
| impressions in band | 7,939 (90% of 8,848 row impressions) |
| clicks in band | 85 (of 97 property clicks) |
| band CTR (clicks ÷ impressions) | 1.07% |
| pages with avg position < 6 (in `gsc-all`) | 502 impressions in total (`position < 6`); I printed only the first 10 rows, so I did not count the pages |
| pages with avg position > 20 | 4 pages, 407 impressions — `/festivals/` is 402 of them at position 31.2 |
| band pages with ≥ 100 impressions | 19 |
| band pages with < 10 impressions | 45 |

Reading: the band is not a long tail of equals. **The top 10 pages hold 5,447 impressions (69% of the band) and 65 clicks (76%)**; 45 of 99 pages have under 10 impressions and are noise.

### 1b. Top 10 band pages by `band_opportunity` (2026-09-09..10-06)

| # | page | impr. | clicks | CTR | avg pos | band_opp. |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,317 | 27 | 2.05% | 7.5 | 52.0 |
| 2 | /learn/rahu-mahadasha-career-problems/ | 810 | 6 | 0.74% | 7.5 | 42.6 |
| 3 | /learn/debilitated-sun-career/ | 773 | 5 | 0.65% | 6.0 | 41.4 |
| 4 | /learn/sade-sati/ | 629 | 7 | 1.11% | 6.4 | 30.7 |
| 5 | /learn/planets-in-7th-house-marriage/ | 469 | 5 | 1.07% | 6.4 | 23.1 |
| 6 | /learn/manglik-dosh/ | 363 | 3 | 0.83% | 7.9 | 18.8 |
| 7 | /learn/jupiter-in-10th-house-career/ | 305 | 2 | 0.66% | 6.8 | 16.3 |
| 8 | /learn/career-during-sade-sati/ | 338 | 5 | 1.48% | 7.4 | 15.3 |
| 9 | /learn/panch-mahapurush-yoga/ | 256 | 3 | 1.17% | 6.8 | 12.4 |
| 10 | /learn/marriage-mahadasha-timing/ | 187 | 2 | 1.07% | 6.8 | 9.2 |
| | **Top-10 total** | **5,447** | **65** | **1.19%** | | |

Note: `band_opportunity` is the script's ranking; I did not recompute its formula.

### 1c. Is the objective moving?

| question | answer |
|---|---|
| Did any top-10 band page enter the top 5 in this window? | **Not determinable.** I have one window only. Moving "into the top 5" needs a before and an after. |
| Baseline for the next cycle | Top-10 pages: avg position range 6.0–7.9, combined 5,447 impr., 65 clicks (2026-09-09..10-06). |
| Closest to the line | /learn/debilitated-sun-career/ at 6.0 (773 impr.); /learn/sade-sati/ 6.4; /learn/planets-in-7th-house-marriage/ 6.4 |

## 2. Post-ship scores — issues closed in the last 28 days

Searched: issues closed on/after 2026-09-09 (`gh issue list --state closed --search "closed:>=2026-09-09"`). **4 closed; 1 carried both `thesis:` and `metric:`.**

| issue | closed | thesis + metric? | scored? |
|---|---|---|---|
| #272 `[MEASURE]` north star and band cannot be measured | 2026-10-08 | **yes** | **yes — comment posted** (see below) |
| #285 `[INFRA]` agent-cycle engineer dispatch produces nothing | 2026-10-08 | no | n/a |
| #280 `[INFRA]` agent-infra has no GCP auth step | 2026-10-08 | no | n/a |
| #270 Hindi rashifal readings echo the English window description | 2026-10-08 | no | n/a |

### 2a. #272 — score

| | |
|---|---|
| Predicted (`metric:`) | organic sessions reported as a separate 28-day number; ranking URL beside each of the top-10 band **queries**; pass = both columns exist and are populated |
| Actual, organic sessions | **130 of 271 (48%)** — GA4 `channel` present, coverage 100% (2026-09-09..10-06) |
| Actual, ranking URL | present — the band is keyed by URL (99 pages, coverage 101%) |
| Not delivered | a per-**query** view; queries are ~9% of impressions, so "top-10 band queries" cannot be listed |
| **Verdict** | **PASS on the stated criterion; PARTIAL on the intent.** |

Posted: https://github.com/mahAnuj/astro-ai/issues/272#issuecomment-6072071543

**What the fix corrected — a miss in the premise, not in the ship.** #272 said the Rahu–Ketu landing had "at least 23 sessions" the export could not name. In this run's data: **27 GSC clicks vs 28 GA4 Organic Search sessions** on `/learn/rahu-mahadasha-ketu-antardasha/` (2026-09-09..10-06). The gap was a query-dimension artefact, and it is gone.

### 2b. The honest limit on scoring

There is **no traffic-affecting ship from the last 28 days that carried a `thesis:`/`metric:`** — nothing to score against sessions, CTR or position. All four closures are infra/measurement/localisation. That is a finding in itself: 48 commits landed on `origin/main` since 2026-09-09 (see §3), and none of the closed issues made a falsifiable traffic claim. The next scoreable work is #267 itself (open) and the new issue below.

## 3. Confounds — named before any delta

I report **no before/after delta** in this run (one window only, §6). These are the confounds that bind the *next* one.

| confound | finding |
|---|---|
| Concurrent ships in the window | 48 commits on `origin/main` since 2026-09-09. By content: **#124 Hindi surface** (`/hi/{path}`, 13 URLs, 2026-09-20 → 10-06; 2026-10-04 is the indexable-surface commit), **rashifal localisation** (#299, #270), and ~30 agent-loop / workflow / measurement commits (2026-10-07..09). Files touched under `src/`: `i18n.py` (10), `rashifal_grid.html` (5), `_lang_picker.html` (5), `rashifal_single.html` (4), `routes/*`, `main.py`, `base.html`, `app.css`, `chart.py` — **none is a `/learn` article template or a `/learn` title/meta**. The band pages' own content and titles did not change in this window per the file list, but I did not diff `learn_registry.py` line by line. |
| `/hi/` is too young to read | Zero `/hi` rows in GSC or GA4 in this window. The surface went indexable 2026-10-04; GSC lags ~3 days. **Not a miss — not yet measurable.** |
| Seasonality | **Not determined.** I did not source a 2026 festival calendar this run, and festival dates on this site have a record of being wrong (CLAUDE.md). `/learn/griha-pravesh-muhurat-2026-2027/` (9 sessions) and `/muhurat/griha-pravesh/` (5 sessions) are seasonal by nature; the band's biggest pages (Rahu/Ketu dasha, Sade Sati, debilitated Sun, 7th house) are evergreen topics. No seasonal explanation is asserted for any band movement. |
| Was the page reachable? | **Not probed.** The band is `/learn/*` — static Jinja templates, not Groq-dependent, so #266 (`/kundli` returns "high demand", **open**) does not apply to them. It does apply to `/kundli` (25 impr., pos 7.9, 0 clicks; 3 Organic sessions to `/kundli/`) — **traffic to a page that fails intermittently is not engagement**; read nothing into that landing's numbers. #253 (stale stylesheet for returning visitors) cannot be checked from GA4/GSC. |
| Sample size | Small. 271 sessions, 97 clicks in 28 days. 45 of 99 band pages have < 10 impressions. Most single-page CTR differences below ~5 clicks are noise. |
| Query-string / duplicate landings | GA4: 67 landings but 60 distinct paths. Four `/?fbclid=…` landings (1 session each, 100% bounce, channel "Organic Social") and `?_x_tr_*` Google-Translate variants. I folded these before ranking pages. |

## 4. CTR outliers (2026-09-09..10-06)

Comparison basis: band CTR **1.07%** (all 99 pages) and **a sibling at the same average position**, not an external table.

| page | impr. | clicks | CTR | pos | vs reference | note |
|---|--:|--:|--:|--:|---|---|
| /learn/rahu-mahadasha-career-problems/ | 810 | 6 | 0.74% | 7.5 | ref /learn/rahu-mahadasha-ketu-antardasha/ at **7.5: 2.05%** → 2.8× | at 2.05% expect 16.6 clicks, got 6 (Poisson P ≈ 0.003) |
| /learn/debilitated-sun-career/ | 773 | 5 | 0.65% | **6.0** | 0.32× the reference | expect 15.8, got 5 (P ≈ 0.002) |
| /learn/manglik-dosh/ | 363 | 3 | 0.83% | 7.9 | 0.40× | small |
| /learn/jupiter-in-10th-house-career/ | 305 | 2 | 0.66% | 6.8 | 0.32× | small |
| /learn/shukra-venus-in-vedic-astrology/ | 137 | 1 | 0.73% | 5.7 | (outside band) | position 5.7 — already top-5-ish with almost no clicks |
| /learn/ashwini-nakshatra/ | 94 | 1 | 1.06% | 5.5 | (outside band) | small |

Four band pages together: **2,251 impressions, 16 clicks, 0.71%**. At the reference's 2.05% that is ~46 clicks. Filed as **#311**.

**Counter-reading, stated:** the reference page is one page; query intent differs per page ("rahu mahadasha ketu antardasha" is a navigational-sounding long-tail), so 2.05% may be the outlier rather than the 0.7% group. That is why #311's thesis is a test with a metric, not a diagnosis.

## 5. Where visitors land and what they do (2026-09-09..10-06)

Sessions by channel (GA4, weighted bounce and pages/session):

| channel | sessions | bounce (weighted) | pages/session (weighted) |
|---|--:|--:|--:|
| Organic Search | 130 | 33.8% | 1.59 |
| Direct | 93 | 49.5% | 3.16 |
| AI Assistant | 35 | 45.7% | 3.31 |
| Unassigned | 9 | 33.3% | 1.00 |
| Organic Social | 4 | 100% | 1.00 |
| **Total** | **271** | | |

Sessions by landing type:

| landing type | sessions | bounce (weighted) | pages/session (weighted) |
|---|--:|--:|--:|
| `/learn/*` | 184 | 49.5% | 1.37 |
| `/` (incl. `/?fbclid=…`) | 62 | 21.0% | 4.99 |
| tools & other | 25 | 36.0% | 2.72 |

Top landings, query strings stripped, trailing slash folded (sessions, 2026-09-09..10-06):

| landing | sessions | of which Organic Search |
|---|--:|--:|
| `/` | 62 | 3 (47 are Direct, 8 AI Assistant, 4 Organic Social) |
| /learn/rahu-mahadasha-ketu-antardasha/ | 30 | 28 |
| /learn/rahu-mahadasha-career-problems/ | 12 | 6 |
| /learn/sade-sati/ | 11 | 9 |
| /learn/marriage-mahadasha-timing/ | 10 | 0 (7 Direct, 3 AI Assistant) |
| /learn/debilitated-sun-career/ | 9 | 6 |
| /learn/griha-pravesh-muhurat-2026-2027/ | 9 | 5 |
| /learn/kaal-sarp-dosh/ | 8 | 2 |

Observations:
- **Organic is the largest channel (48% of sessions) and the shallowest-reading one.** 130 organic sessions at 1.59 pages/session vs Direct 3.16. Together with #276 (open: the top landing sends 0 of 29 sessions onward), organic readers arrive, read one article, and leave.
- **The AI Assistant channel is real:** 35 sessions (13%), with 3.31 pages/session — the deepest-reading channel after Direct. 8 land on `/`, 3 on `/panchang/2026-09-17/`, 3 on `/learn/pitru-dosh-remedies/`. It is not measured by GSC. Window-only observation; no trend claim.
- **Bounce and pages/session disagree** on organic pages (e.g. the Rahu–Ketu page: bounce 21.4% yet 0.96 pages/session on 28 organic sessions). Pages/session below 1.0 is not possible as a plain pageview count; this GA4 export's definition is unclear to me. **I treat bounce and pages/session as unreliable for individual pages** and use them only in aggregate above.

## 6. Decay — what I could not determine

| item | status |
|---|---|
| Pages losing position month over month | **Not determinable.** I was given one window (2026-09-09..10-06). Decay needs the preceding 28 days (2026-08-12..09-08) at page level. |
| Funnel (landing → form → result → second page) | **Not determinable.** GA4 export has no event or path-sequence dimension (#272 comment 5 recorded the same). Pages/session is the only proxy and cannot name the second page. |
| Query-level band | Not determinable — ~9% coverage. |
| Seasonality | Not sourced (§3). |

**The single measurement that would settle decay:** run `fetch_gsc.py --by page` for 2026-08-12..2026-09-08 and diff against this run's `gsc-all.json` per page. One command; the page dimension already exists.

## 7. Actions taken and recommendations that are not mine to make

| action | where |
|---|---|
| Score posted | #272 comment (link in §2a) |
| Issue filed | **#311** — `[SEO]` four band pages at pos 6–8 with CTR 0.65–0.83% vs 2.05% sibling; Evidence Block complete; "Not claimed" section lists the reference-page counter-reading |
| No issue filed for | the pages/session < 1 anomaly (could be a GA4 definition, not a defect — see §5); the AI Assistant channel (an observation, not an action); `/festivals/` at position 31.2 with 402 impressions and 1 click (outside the band; noted, no thesis) |

For `chief` (analyst decides nothing): OBJECTIVE.md still reads "ten highest-impression **queries**". After #272 the measurable unit is the **page**. Either the objective is re-worded to pages, or a query-level export is built — the 9% coverage rules out query-level scoring as it stands. This is a wording ruling for `chief`, not an issue.

## 8. Not determined (summary)

1. Whether any band page moved into the top 5 — one window.
2. Decay and trend — no prior window.
3. Per-query position and the cause of the CTR gap in §4 — query coverage ~9%.
4. Seasonality of any page — no calendar sourced this run.
5. Reachability of any page — not probed; `/kundli` is known-intermittent (#266 open).
6. Whether the AI Assistant channel is growing — one window.
7. Whether the `learn_registry.py` titles changed in the window — I read the current `seo_title` values for four pages only, not their history. The reference page's `seo_title` was not located.
