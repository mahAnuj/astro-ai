# Analyst report — 2026-10-11

**Window on every number: 2026-09-11 → 2026-10-08 (28 days; the exports exclude the last 3 days).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API re-called. Every figure below was computed from those three files this run, except where a row says otherwise (git history, GitHub issue state, one production probe). Nothing was taken from `BACKLOG.md`, `measurements/`, or earlier comments as a number.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-11..10-08 | 101% of 8,376 property impressions (rows sum 8,433). **Band emitted 97 rows = 6,852 impr. = 82%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 129 rows = 8,433 impr. | no | — |
| ga4 | landing × channel | same | 101% of 280 sessions (rows sum 282); 101 rows, 69 landings as exported, **66 paths after stripping query strings and folding trailing slashes** | no | bounce / pages-per-session are per channel; I weighted them by sessions |

- Property clicks (GSC): **95**. GA4 Organic Search sessions: **139**. Different measures (GA4 counts other engines and counts differently); I do not equate them.
- **Band boundary.** `fetch_gsc.py:79` filters `6 <= pos <= 20` on the *unrounded* position. `/learn/debilitated-sun-career/` (759 impr.) prints as 6.0 in `gsc-all.json` but is **absent from `gsc-band.json`**, so its unrounded position is below 6. It is the third-highest-impression page on the site and the closest to the objective's top-5 line, and a band-only reading drops it. I list it separately in §1b. A second page, `/learn/santan-prapti-children-in-kundli/` (35 impr.), is in the same situation.
- **Sample size.** 95 clicks in 28 days. Every per-page CTR below is small-number territory; I give a binomial tail where I make a claim.
- **Production reachable** at the time of this run: `GET /health` → 200, `GET /learn/rahu-mahadasha-ketu-antardasha/` → 200 (155,470 B, 0.64 s). One probe each, not a sweep. I did not check `/rashifal/*` (#266 intermittency) — see §5.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression **queries**."*
**Cannot be scored literally.** These exports are by page; this run has no query-level data. The unit below is **pages**. (Still the open wording question #272 left behind; it is `chief`'s ruling, not a defect.)

### 1a. Band size (2026-09-11..10-08, `dimension: page`)

| measure | value |
|---|---:|
| pages with average position 6–20 (as emitted) | 97 |
| impressions in band | 6,852 (82% of 8,433 row impressions) |
| clicks in band | 79 (of 95 property clicks) |
| band CTR, impressions-weighted | 1.15% |
| band CTR excluding the one reference page (Rahu–Ketu antardasha) | 0.94% (52 clicks / 5,542 impr.) |
| pages by average position, `gsc-all`: 6–20 / 5–6 / ≤5 / >20 | 99 pages, 7,646 impr., 84 clicks / 10 pages, 418 impr., 9 clicks / 16 pages, **28 impr.**, 0 clicks / 4 pages, 341 impr., 2 clicks |
| pages already ≤ 5 | 16 pages, 28 impressions total, 0 clicks — **nothing high-volume is in the top 5** |
| top-10 band pages by `band_opportunity` | 4,701 impr. (69% of band), 60 clicks (76% of band clicks) — see 1b |

### 1b. Top 10 band pages by `band_opportunity`, plus the page that fell just out of the band (2026-09-11..10-08)

| # | page | impr. | clicks | CTR | avg pos | band_opp. |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,310 | 27 | 2.06% | 7.5 | 51.6 |
| 2 | /learn/rahu-mahadasha-career-problems/ | 761 | 6 | 0.79% | 7.4 | 39.7 |
| — | /learn/debilitated-sun-career/ *(not in band file; prints 6.0, unrounded < 6)* | 759 | 5 | 0.66% | 6.0 | n/a |
| 3 | /learn/sade-sati/ | 625 | 7 | 1.12% | 6.3 | 30.5 |
| 4 | /learn/planets-in-7th-house-marriage/ | 451 | 5 | 1.11% | 6.4 | 22.1 |
| 5 | /learn/manglik-dosh/ | 351 | 3 | 0.85% | 7.3 | 18.1 |
| 6 | /learn/jupiter-in-10th-house-career/ | 295 | 1 | 0.34% | 6.8 | 16.7 |
| 7 | /learn/career-during-sade-sati/ | 334 | 5 | 1.50% | 7.4 | 15.0 |
| 8 | /learn/panch-mahapurush-yoga/ | 252 | 3 | 1.19% | 6.8 | 12.1 |
| 9 | /learn/marriage-mahadasha-timing/ | 179 | 2 | 1.12% | 6.7 | 8.7 |
| 10 | /learn/10th-lord-in-6th-house-career/ | 143 | 1 | 0.70% | 7.1 | 7.6 |

- Top-10 band pages above (excluding the unlisted Sun page): impressions 1,310+761+625+451+351+295+334+252+179+143 = **4,701 = 69% of the 6,852 band impressions**; clicks 27+6+7+5+3+1+5+3+2+1 = **60 of 79 (76%)**.
- All ten are `/learn/` articles.
- **Objective status, page-level proxy: 0 of the 11 pages in §1b (the ten band pages plus `debilitated-sun-career`) are at position ≤ 5.** The nearest is `debilitated-sun-career` (under 6.0); the next five sit at 6.3–7.4. No movement can be claimed from this run — it is a single window.

### 1c. Non-`/learn` pages worth naming (2026-09-11..10-08)

| page | impr. | clicks | CTR | avg pos | read |
|---|--:|--:|--:|--:|---|
| /festivals | 336 | 1 | 0.30% | **28.6** | 7th-highest-impression page on the site, ranking on page 3. Not in the band. |
| / | 82 | 3 | 3.66% | 5.3 | best CTR of any page with >50 impr. |
| /rashifal | 53 | 1 | 1.89% | 10.1 | in band |
| /matching | 42 | 0 | 0% | 6.5 | in band, tool page |
| /kundli | 25 | 0 | 0% | 7.9 | in band, tool page |
| /muhurat/griha-pravesh | 16 | 4 | 25.0% | 5.9 | 16 impressions; too small to read |

## 2. Post-ship scores — issues closed 2026-09-13 → 2026-10-11

Seven issues closed in the window (`gh issue list --state closed`, closed ≥ 2026-09-13). I read the body and every comment of each for a `thesis:` and a `metric:`.

| issue | closed | carries `thesis:` + `metric:` | scored? |
|---|---|---|---|
| #272 [MEASURE] export dimensions | 2026-10-08 | **yes** | yes — see below |
| #304 [UI] mobile sticky CTA under tab bar | 2026-10-09 | no | no — see note |
| #268 pre-warm rashifal cache | 2026-10-09 | no | no |
| #260 learn-article shlokas font | 2026-10-10 | no | no |
| #270 Hindi rashifal English echo | 2026-10-08 | no | no |
| #285, #280 infra | 2026-10-08 | no | no |

### 2a. #272 — **PARTIAL** (unchanged from the two earlier scores; not re-posted)

| | predicted (`metric:`) | actual (2026-09-11..10-08) | verdict |
|---|---|---|---|
| Organic sessions reported as a separate number | yes | **yes** — GA4 export carries a channel column; Organic Search = **139 of 280** sessions (rows sum 282, coverage 101%) | PASS |
| Ranking URL beside the band | "beside each of the top-10 band **queries**" | **pages, not queries** — GSC `dimension: page`, 97 band rows = 6,852 impr. | PARTIAL |

- Two analyst scores already sit on #272 (2026-10-09, 2026-10-10), both **PARTIAL** on the same grounds. The verdict does not change on this window's data, so **I did not post a third copy** — a daily identical comment buries the one that matters. If you wanted it re-posted anyway, say so.
- Still **not determined**: whether a query→URL join is obtainable at all. The single measurement that settles it: `fetch_gsc.py --by query` with `page` as a second dimension, and its `coverage_pct`. The issue's own measurement put the `query` dimension at 9% of impressions; I did not re-measure it this run.
- Confounds: measurement tooling, not a site change; nothing about traffic depends on it. Nothing else in the window could change whether the column exists.

### 2b. The other six closed issues — a gap, not a miss

None carries a `thesis:` or `metric:`, so by this role's rule none can be scored. Two of them shipped to users:

| issue | shipped (commit, date) | why it cannot be scored here |
|---|---|---|
| #304 sticky Kundli CTA lifted above the mobile tab bar | `2f5f49f`, 2026-10-09 | **After the window.** The data ends 2026-10-08, so no number in these files can include it. Also no `metric:`. Earliest honest read: a window that starts after 2026-10-09 and has a non-overlapping before-window — about 2026-11-09 onward for a full 28 days. |
| #268 rashifal cache pre-warm | `8857fd2`, 2026-10-09 | After the window; and its effect is token spend / latency, not GA4/GSC. |

#260 (`0a3ccf8`, 2026-10-10) and #270 (`347473b` / `a2f7f02`) are likewise after or near the window end and carry no metric. **No ship in this period has an outcome I can report as a hit or a miss.** That is the finding, not an omission.

## 3. Confounds

| confound | what I found (2026-09-11..10-08) |
|---|---|
| Concurrent ships to the app (`git log origin/main --since=2026-09-11 -- src/`, history unshallowed this run) | The only user-facing shipping in the window is the **#124 Hindi `/hi/` surface** (commits 2026-09-20 sitemap + 13 Hindi twins; 2026-10-04..06 routes/templates/i18n) and rashifal localisation (`a2f7f02`, 2026-10-08). No commit in the window touched a `/learn/` article body or `seo_title` — the diff set is `learn_article_base.html`/remedies templates on 2026-10-10 (after the window) and `app.css`/`_tab_bar.html` on 2026-10-09 (after). **No `/hi/` URL appears in `gsc-all.json` (0 rows) or `ga4.json` (0 landings)** — the Hindi surface has no measurable footprint in this window. |
| Workflow / agent-infra churn | `git log origin/main --since=2026-09-11`: 65 commits, 20 touch `src/`; inside the window itself (to 2026-10-08) 47 commits, 17 touch `src/`. The rest are `.github/`, `scripts/`, `.claude/`, `measurements/` or root docs and do not ship to the site. |
| Seasonality | **Not determined.** One window; no prior-year or non-overlapping prior window in the files. The page-level ranks here are mostly evergreen `/learn/` articles (`/festivals` has 1 click), which argues against a festival spike, but I cannot size a seasonal effect. |
| Page reachable? | `/health` 200 and the top band page 200 at probe time. #253 (stale stylesheet) and #266 (TPM-ceiling failures on LLM pages) are not tested by this probe; neither affects the static `/learn/` pages that dominate the band. |
| Sample size | 95 clicks / 280 sessions in 28 days. Most per-page deltas are noise. |
| **Overlapping windows** | This window (09-11..10-08) overlaps the previous run's by 27 of 28 days. Any "change since last run" computed across the two is mostly the same data counted twice; I make none. |

## 4. CTR outliers (2026-09-11..10-08; reference = impressions-weighted band CTR 1.15%; pages ≥ 100 impr.)

Expected clicks = impressions × 1.15%. `P(≤k)` = binomial probability of seeing that few clicks or fewer at the band rate.

| page | impr. | clicks | expected | pos | P(≤k) | read |
|---|--:|--:|--:|--:|--:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,310 | 27 | 15.1 | 7.5 | 0.998 | **the high outlier.** Upper-tail P ≈ 0.0002 against the band's rate excluding it (0.94%). |
| /learn/rahu-mahadasha-career-problems/ | 761 | 6 | 8.8 | 7.4 | 0.23 | within noise of the band rate |
| /learn/debilitated-sun-career/ | 759 | 5 | 8.8 | 6.0 | 0.13 | within noise |
| /learn/jupiter-in-10th-house-career/ | 295 | 1 | 3.4 | 6.8 | 0.15 | within noise |
| /festivals | 336 | 1 | 3.9 | 28.6 | 0.10 | position, not CTR, is the issue |
| /learn/shukra-venus-in-vedic-astrology/ | 115 | 0 | 1.3 | 5.9 | 0.26 | 0 clicks at position 5.9; too few impressions to read |

**Reading for #311** (open: title/meta test on four pages at 6.0–7.5 vs. a 2.05% sibling): the four pages (`career-problems`, `debilitated-sun`, `manglik-dosh`, `jupiter-in-10th`) total **2,166 impr. / 15 clicks = 0.69%** this window. Against the **band's own rate excluding the reference page (0.94%)** they'd expect 20.3 clicks; seeing ≤ 15 has probability **0.14 — not distinguishable from noise**. Against the reference page's 2.05% it is overwhelming (expected 44), but the evidence says **the reference page is the outlier, not the four** (§ table above). So #311's target of "≥ 1.5%" is a bet that the reference page's rate is reproducible by a title change, not a gap-to-baseline. I will post this on #311.

## 5. Funnel and traffic mix (2026-09-11..10-08, GA4, 280 sessions; bounce and pages/session weighted by sessions)

| landing group | sessions | bounce | pages/session | note |
|---|--:|--:|--:|---|
| `/` (home) | 61 | 18% | 5.10 | **49 of 61 are `Direct`** (8 AI Assistant, 4 Organic) |
| `/learn/*` | 193 | 51% | 1.36 | **118 of 193 sessions (61%) have pages/session exactly 1.00** |
| everything else (tools, panchang, muhurat) | 28 | 36% | 2.46 | too few to rank |

| channel (all landings) | sessions | share | bounce | pages/session |
|---|--:|--:|--:|--:|
| Organic Search | 139 | 49% | 36% | 1.57 |
| Direct | 100 | 35% | 52% | 3.03 |
| AI Assistant | 35 | 12% | 40% | 3.23 |
| Unassigned | 8 | 3% | 38% | 0.88 |

(Shares are of the 282 row-sessions.)

- `/learn/*` Organic Search only: **121 sessions, 37% bounce, 1.45 pages/session.** The organic reader finds the article and, almost always, stops. `/learn/rahu-mahadasha-ketu-antardasha` alone: 32 sessions, **1.03 pages/session**, 30 of them Organic. This is #276's finding and this window agrees with it (still open). I cannot see *why* — the export has no CTA-click event.
- **Home page is not an organic story**: 49 Direct sessions at 5.1 pages/session on `/`. Possible causes include the owner, testers, or automated browser checks running through GA. **I cannot determine which** from the export; the measurement that would settle it is the same export with `hostName`/`deviceCategory`/a known-internal-traffic filter, or `newVsReturning`.
- **AI Assistant is a real channel**: 35 sessions (12%), 3.23 pages/session — the best engagement of any channel. 8 land on `/`; the rest are spread over ~17 `/learn/`, tool, and panchang URLs. **Not a finding needing action** — it is new visibility the channel dimension from #272 provides. Sample is small.
- GA4 Organic Search (139) vs GSC clicks (95): they should not match. Per-page, `rahu-mahadasha-ketu-antardasha` has 27 GSC clicks vs 30 GA4 organic sessions — close.

## 6. Decay

**Not determinable this run.** The only prior-window data is the previous run's export, which overlaps this window by 27 of 28 days (§3). A decay claim needs a non-overlapping before-window (e.g. `--days 28` ending 28 days earlier). The fetch scripts take `--days` only (`fetch_gsc.py:42`, `fetch_ga4.py:25`) — no `--end`/`--offset` — so **the single change that would settle it is an offset flag on both scripts**, or a stored export from ≥ 28 days ago to diff against. I am not filing it: whether the stored exports under `measurements/` already hold a usable non-overlapping window is something I did not check, and the fix is a small flag, not a finding.

## 7. Issues filed / comments posted this run

| action | target | why |
|---|---|---|
| comment | #311 | adds the band-rate-excluding-reference comparison (§4): the four pages are within noise of the band; the reference page is the outlier. Changes how the issue's "Pass" threshold should be read. |
| none filed | — | No finding in this run is new, evidenced, and not already tracked (#311 CTR, #276 learn→tool, #267 band). `/festivals` at position 28.6 with 336 impressions is the one unfiled observation: it is a page-3 ranking with no ship and no metric proposed — a `product-manager` question, not a defect, and I do not propose features. |

## 8. What I could not determine

| question | the one measurement that settles it |
|---|---|
| Whether the objective ("ten highest-impression **queries**") can be scored at all | `fetch_gsc.py --by query` with `page` as a second dimension, and its `coverage_pct` |
| Whether any page decayed | a non-overlapping prior 28-day export (§6) |
| Effect of #304 / #268 / #260 / #270 | none carry a metric; #304 would need a window starting after 2026-10-09 |
| Who the 49 Direct sessions on `/` are | internal-traffic filter or `newVsReturning` / `hostName` in the GA4 request |
| Whether `/rashifal/*` was reachable (#266) | a production sweep; not done — and the CLAUDE.md sweep deliberately no longer touches those pages |
| Seasonality | a prior-year window; the property has none in these files |
