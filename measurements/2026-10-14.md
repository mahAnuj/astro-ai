# Analyst report — 2026-10-14

**Window on every traffic number: 2026-09-14 → 2026-10-11 (28 days; the exports exclude the last 3 days).**
Traffic figures were computed this run from `/tmp/gsc-band.json`, `/tmp/gsc-all.json` and `/tmp/ga4.json`. No API was re-called.
Git, issue and production facts come from `git log origin/main`, `gh issue` and one `curl` run this session.
Nothing is carried from `BACKLOG.md`, `measurements/` or earlier comments, except where a row says "prior score".

**I make no "change since last run" claim.** The previous run's window (2026-09-13..10-10) overlaps this one by 27 of 28 days. No earlier, non-overlapping window was in this run's files, so the **decay** check (§4) is not determinable.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-14..10-11 | 101% of 10,081 property impressions (rows sum 10,138). **Band printed 101 rows = 8,329 impr. = 83%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 127 rows = 10,138 impr. | no | same |
| ga4 | landing × channel | same | 101% of 281 property sessions (rows sum 283); 101 rows; `landing_count` 69 as exported, **66 paths** after I stripped query strings and folded trailing slashes | no | bounce and pages/session are per channel; weighted by sessions below |

| fact | value | window |
|---|---:|---|
| GSC property clicks | 107 | 2026-09-14..10-11 |
| GSC property impressions | 10,081 (rows 10,138) | same |
| GA4 sessions, property total | 281 (rows 283) | same |
| GA4 Organic Search sessions (sum of rows) | 138 of 283 (49%) | same |
| GA4 Direct / AI Assistant / Unassigned (sum of rows) | 107 / 30 / 8 | same |

- GSC clicks and GA4 sessions measure different things. I do not equate them.
- **Unit is pages, not queries.** OBJECTIVE.md says "ten highest-impression **queries**". These exports are `dimension: page`, so the objective can only be scored by a page-level proxy (§1b). Not a new finding (#272 scored PARTIAL for the same reason; #291 tracks the stale labels).
- **Sample size.** 107 clicks in 28 days. Every per-page CTR below is small-number territory.
- **Production reachability, checked this run.**
  - `GET /health` → `{"ok":true,"revision":"bhagya-00440-bvw","build_sha":"ee1949a8…"}`.
  - `686fe3a` (#311) is an ancestor of `ee1949a`, so the #311 change is in the serving revision.
  - The four #311 pages return HTTP 200 and carry the new `<title>` (§2).
  - **Not checked:** `/kundli` (#266 open) and `/rashifal/*` (LLM-backed). Traffic to them is not evidence that they worked.

## 1. The 6–20 band against OBJECTIVE.md (2026-09-14..10-11, `dimension: page`)

### 1a. Band size

| measure | value | window |
|---|---:|---|
| pages at average position 6–20 (printed) | 101 | 2026-09-14..10-11 |
| impressions in the printed band | 8,329 (83% of 10,138 row impressions) | same |
| clicks in the printed band | 94 of 107 property clicks | same |
| band CTR, impressions-weighted | 1.13% (94 / 8,329) | same |
| band CTR excluding the reference page | 0.99% (66 / 6,694) | same |
| median CTR, all 101 band pages | 0.00% (70 of 101 have zero clicks) | same |
| median CTR, the 19 band pages with ≥100 impressions | 0.80% | same |

### 1b. Objective proxy: are the ten highest-impression pages in the top 5?

| measure | value | window |
|---|---:|---|
| ten highest-impression pages (gsc-all) | 6,503 impr. = 64% of 10,138 | 2026-09-14..10-11 |
| of those, at average position ≤ 5 | **0 of 10** | same |
| pages at average position < 6, all of gsc-all | 22 pages, 569 impr. (6%) | same |
| pages at average position > 20 | 3 pages, 315 impr. | same |

The pages with the volume are one to three places short of the top 5. The pages already in the top 5 are low-volume.
Zero of ten is the same reading as the previous run, from an overlapping window.

### 1c. Band list, ranked by the file's `band_opportunity` (top 15, 2026-09-14..10-11)

| # | page | impr. | clicks | CTR | avg pos |
|--:|---|---:|---:|---:|---:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,635 | 28 | 1.71% | 7.5 |
| 2 | /learn/rahu-mahadasha-career-problems/ | 822 | 6 | 0.73% | 7.3 |
| 3 | /learn/sade-sati/ | 844 | 9 | 1.07% | 6.2 |
| 4 | /learn/manglik-dosh/ | 435 | 2 | 0.46% | 7.2 |
| 5 | /learn/planets-in-7th-house-marriage/ | 464 | 5 | 1.08% | 6.3 |
| 6 | /learn/jupiter-in-10th-house-career/ | 332 | 1 | 0.30% | 6.8 |
| 7 | /learn/panch-mahapurush-yoga/ | 345 | 3 | 0.87% | 6.7 |
| 8 | /learn/career-during-sade-sati/ | 391 | 6 | 1.53% | 7.3 |
| 9 | /learn/marriage-mahadasha-timing/ | 209 | 1 | 0.48% | 6.5 |
| 10 | /learn/7th-lord-placement-marriage-guide/ | 204 | 3 | 1.47% | 8.2 |
| 11 | /learn/10th-lord-in-6th-house-career/ | 177 | 2 | 1.13% | 7.1 |
| 12 | /learn/sun-in-10th-house-career/ | 145 | 1 | 0.69% | 7.1 |
| 13 | /learn/ | 121 | 0 | 0.00% | 13.3 |
| 14 | /learn/chronic-health-issues-kundli/ | 134 | 1 | 0.75% | 6.2 |
| 15 | /learn/mangal-mars-in-vedic-astrology/ | 125 | 1 | 0.80% | 7.5 |

- **Gap in the band file.** `/learn/debilitated-sun-career/` has 925 impressions, 6 clicks, 0.65% CTR and a displayed position of 6.0. It is the **second-highest-impression page on the property**, and it is absent from `gsc-band.json`.
  - The band filter probably drops it because its true average is just under 6.0. I cannot confirm that: the files carry one decimal.
  - **Consequence:** ranking by the band file alone omits the #2 page by volume. #311 already includes it.
  - Not filed: it is an inference from rounding, not a measured defect. Settling measurement: print `position` to 3 decimals for this page.
- **Concentration.** The top 3 band pages hold 3,301 of 8,329 printed band impressions (40%).
- The reference page (/learn/rahu-mahadasha-ketu-antardasha/) alone is 28 of 107 property clicks (26%).

### 1d. CTR outliers (2026-09-14..10-11)

Comparison base is the band's own rate, **not** a blog table: 0.87% (73 clicks − 28 reference-page clicks = 45 clicks over 5,174 impressions, for the 18 band pages with ≥100 impressions excluding the reference page). Probabilities are exact binomial at that rate.

| page | impr. | clicks | expected at 0.87% | P(this low or lower) | P(this high or higher) | reading |
|---|---:|---:|---:|---:|---:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,635 | 28 | 14.2 | – | 0.0008 | **the only real outlier, and it is a high one** |
| /learn/jupiter-in-10th-house-career/ | 332 | 1 | 2.9 | 0.22 | – | not distinguishable from the base |
| /learn/manglik-dosh/ | 435 | 2 | 3.8 | 0.27 | – | not distinguishable |
| /learn/rahu-mahadasha-career-problems/ | 822 | 6 | 7.1 | 0.43 | – | not distinguishable |
| /learn/career-during-sade-sati/ | 391 | 6 | 3.4 | – | 0.13 | not distinguishable |
| /learn/mars-remedies/ | 106 | 3 | 0.9 | – | 0.07 | n too small |

**No low-CTR outlier can be called.** The #311 premise ("four pages with CTR 0.65–0.83% vs 2.05% for a sibling") is mostly the reference page being unusually good, not the four being unusually bad. The reference page is the outlier.

## 2. Post-ship scores — issues closed in the last 28 days (2026-09-16 → 2026-10-14) that carry a `thesis:` and a `metric:`

`gh issue list --state closed --search "closed:>=2026-09-16"` returned 16 issues. Six mention both words in the body. **Five carry a real `thesis:`/`metric:`**: #320, #316, #313, #311, #272. **#286 does not** — its body quotes the words as validator rules ("`thesis:` and `metric:` both present"), so it is not a scoreable ship and I did not score it.

| issue | closed | kind of metric | verdict | comment |
|---|---|---|---|---|
| #311 title/meta CTR test | 2026-10-13 | **traffic (GSC CTR)** | **NOT SCOREABLE YET — 0 post-deploy days in the data** | posted this run |
| #320 rewrite textbook out of history | 2026-10-13 | repo state | **HIT on the stated metric; one named gap** | posted this run |
| #316 weekly loop-outcome report | 2026-10-11 | loop effect | PARTIAL (prior score 2026-10-12) | not re-posted; see below |
| #313 workflow gate | 2026-10-11 | mutation catch | HIT (prior score 2026-10-12) | not re-posted |
| #272 measurement dimensions | 2026-10-08 | structural | PASS on stated pass/fail, PARTIAL on intent (scored 2026-10-09 and 2026-10-10) | not re-posted |

**The only traffic ship in the 28 days is #311, and it cannot be scored.** There is no traffic evidence yet for any shipped change. That is a finding in itself: the objective's lever (the band) has had **one** title/meta change shipped against it, 1 day before this report.

### 2a. #311 — baseline for the future score, and why there is no score today

| item | value |
|---|---|
| deployed | `686fe3a` merged 2026-10-13 17:29 UTC; `/health` build_sha `ee1949a` (a descendant) is serving |
| live check this run | all four pages HTTP 200, new `<title>` present (e.g. "Confused About Career in Rahu Mahadasha? Why It Happens", "Manglik Dosh: Is It Real? Cancellation Rules Most Skip") |
| GSC data available | ends 2026-10-11, i.e. **before the deploy**. Post-deploy days in this run's files: **0** |
| earliest honest score | an after-window of 2026-10-14 → 2026-11-10, readable once GSC finalises, about 2026-11-13 |

Pre-ship baseline, same four pages, window 2026-09-14..10-11:

| page | impr. | clicks | CTR | avg pos |
|---|---:|---:|---:|---:|
| /learn/debilitated-sun-career/ | 925 | 6 | 0.65% | 6.0 |
| /learn/rahu-mahadasha-career-problems/ | 822 | 6 | 0.73% | 7.3 |
| /learn/manglik-dosh/ | 435 | 2 | 0.46% | 7.2 |
| /learn/jupiter-in-10th-house-career/ | 332 | 1 | 0.30% | 6.8 |
| **combined** | **2,514** | **15** | **0.60%** | – |

- The issue's pass bar is ≥1.5% on ≥1,500 impressions at average position within ±1 of today's. On 2,514 impressions that is ≥ 38 clicks against a baseline of 15. At the band's own base rate (0.87%) the expectation is about 22.
- The baseline has drifted down across overlapping windows: 0.71% (issue body) → 0.69% (2026-09-11..10-08, per prior note) → 0.60% (here). These windows overlap heavily, so it is one measurement viewed three times, not a trend.
- **Predicted (issue):** ≥1.5% combined CTR on ≥1,500 impressions, position within ±1.
- **Actual:** none yet.
- **Confounds already visible for the after-window:**
  - The title change is not the only SEO-relevant thing in motion. #124 (Hindi `/hi/` URLs plus hreflang, 13 URLs) landed 2026-10-04..06 and may still be changing impressions inside the baseline.
  - The reference page is not being changed, so it is a natural control.
  - Four pages × 28 days is about 15–40 clicks. The binomial noise on 15 clicks is wide, so a pass or a miss will each be arguable.

### 2b. #320 — scored by execution this run

| | |
|---|---|
| **Predicted (`metric:`)** | `git log --all -- data/vedic_astro_textbook.pdf` is empty; the gate sweep is unchanged; the three corpus gates still exit 0 |
| **Actual — history** | `git log origin/main --oneline -- data/vedic_astro_textbook.pdf` → 0 commits. `origin/main` is 757 commits. `gh api repos/mahAnuj/astro-ai` → `private: false` |
| **Not checked** | The gate sweep and the three corpus gates. `data/` is gitignored and this checkout holds none of the books, so a corpus gate result would be against an empty corpus and worthless. The closing comment's "identical tree hash" is the evidence for "unchanged", and I did not re-derive it |
| **Scope of the `--all` check** | My clone holds `origin/main` only, so "empty" is verified for `main`'s history, not for every ref. The closing comment itself says the blob is still reachable through 33 `refs/pull/N/head` refs (a GitHub Support purge is outstanding) |
| **Verdict** | **HIT on `main`'s history. Thesis (unblocks going public) confirmed: the repository is public.** The residual (PR refs) was disclosed by the closer and is tracked outside the metric |

### 2c. Issues scored previously — status only

| issue | prior verdict | anything new this run |
|---|---|---|
| #272 | PASS / PARTIAL | Re-confirmed from this run's files: `ga4.json` carries `channel` (Organic Search 138 of 283); `gsc-*.json` is `dimension: page`. Unchanged |
| #313 | HIT | Nothing new; no re-run |
| #316 | PARTIAL ("hit on fixtures, not shown on live data") | **New evidence:** `loop-outcomes.yml` has since run live. Issue #326's comment of 2026-10-13T10:54Z carries a real report for 2026-10-06..10-13, "6 BROKEN, 2 UNKNOWN, 7 OK". The workflow's own run `38386421622` is `conclusion: failure`, step "Report on loop outcomes". I did not determine whether that failure is the deliberate non-zero exit on BROKEN or a crash. That is the single measurement that would move #316 from PARTIAL to PASS or FAIL |

I did not re-post #272, #313 or #316. Nothing in their metrics moved, and a daily duplicate comment buries the original. This is a deliberate departure from "post on every issue" and I'm stating it rather than hiding it.

## 3. Confounds

### 3a. What shipped to the app in the window (`git log origin/main`, paths `src/`, `pyproject.toml`, `uv.lock`, `README.md`; 2026-09-14..10-11)

| date | commit | what | SEO or traffic relevance |
|---|---|---|---|
| 09-20 | `ad5995d`, `5ccbf27`, `a8a5939`, `ef4198f` | #124 Hindi allow-list, sitemap lastmod, 13 Hindi twins | **High.** New indexable URLs and a sitemap change |
| 10-04..06 | `4a7c276` … `571c8c5` (12 commits) | #124 `/hi/{path}` serving 13 URLs, with hreflang | **High.** Same epic |
| 10-08 | `9ccb2c9` | #299 rashifal day-windows localisation | Low |
| 10-09 | `b5e1266`, `27c2d0f` | #268 rashifal served from the cached combined reading; #304 sticky CTA lift | Medium. #268 changes rashifal reachability |
| 10-10 | `d5912e7` | #260 mantra fonts on /learn | Low |
| 10-11 | `8805b23`, `69c533b` | #306 kundli autofocus removal, snapshot tile wrap | Low |

The 84 commits on `main` from 2026-09-14 to 10-13 are mostly `.github/`, `.claude/`, `scripts/` and `measurements/`, which do not ship. Rows above are the ones that do.
**Anything that moved in the band inside this window cannot be attributed to a single ship.** #124 is the only one with a plausible effect on search, and it is not an article change.
After the window, 10-13: #311 (`686fe3a`) and #255 privacy (`783b597`) shipped. Neither is in the traffic data.

### 3b. Other confounds

| confound | state |
|---|---|
| Seasonality | **Not determined.** `festivals.py` carries no date inside 2026-09-14..10-11 that I could find (grep returned nothing). I have no 28-day-earlier window to compare against |
| Page reachability | `/health` OK and the four #311 pages serve. **`/kundli` (#266, open) and `/rashifal/*` not probed.** GA4 shows only 5 organic sessions on `/kundli` and 1 on `/rashifal/pisces`, so a #266 outage would not show here |
| #253 stale stylesheet (open) | Not probed. Affects returning visitors' rendering, not impressions |
| Actions availability | #339 (open): GitHub refused to start 6 Actions jobs on 2026-10-12 for a payment failure. That affects the loop, not the site |
| Sample size | 107 clicks / 281 sessions. Most per-page figures are noise |

## 4. Decay and funnel

**Decay: not determinable.** I have one window. The only earlier window on disk is the previous run's, which overlaps 27 of 28 days. The single measurement that settles it is a non-overlapping window (2026-08-17..09-13) through the same `fetch_gsc.py --by page`.

### 4a. Channel mix (GA4, 2026-09-14..10-11)

| channel | sessions | share | bounce (session-weighted) | pages/session (weighted) |
|---|---:|---:|---:|---:|
| Organic Search | 138 | 49% | 35.5% | 1.65 |
| Direct | 107 | 38% | 54.2% | 2.83 |
| AI Assistant | 30 | 11% | 43.3% | 2.83 |
| Unassigned | 8 | 3% | 37.5% | 0.88 |

- `/` is 63 sessions (54 Direct, 6 AI Assistant, 3 Organic Search). Direct to `/` at 24% bounce and 4.3 pages/session looks like returning or known visitors, not strangers. I cannot tell from this export; it should not be read as acquisition.
- **AI Assistant is 30 sessions at 2.83 pages/session, the same depth as Direct and 1.7× organic.** It is a channel the OBJECTIVE does not name. I report it, I do not recommend on it.

### 4b. Where organic lands (GA4, folded by path, 2026-09-14..10-11)

| landing | organic sessions | all-channel sessions |
|---|---:|---:|
| /learn/rahu-mahadasha-ketu-antardasha | 30 | 32 |
| /learn/sade-sati | 9 | 12 |
| /learn/debilitated-sun-career | 7 | 10 |
| /muhurat/griha-pravesh | 7 | 7 |
| /learn/rahu-mahadasha-career-problems | 6 | 12 |
| /kundli | 5 | 5 |

- Organic sessions on `/learn/*`: 118 of 138 (86%). Weighted pages/session there is 1.48. On non-`/learn` organic landings (20 sessions) it is 2.65.
- On `/learn` organic landings with pages/session ≤1.05, 90 of 118 sessions never leave the page. That is the funnel finding, and it **is already filed as #276** (top /learn landing sends 0 of 29 sessions onward). In this window the same landing has 30 organic sessions at 1.03 pages/session, so it persists. I did not file a duplicate.
- The reference page is 30 organic sessions here against 28 GSC clicks. The two are close, which supports reading GA4 organic as GSC clicks for this page.

## 5. Issues filed

**None.** Every finding that needs action is already open:
- #276, the funnel on the top /learn landing (still reproduces, see §4b)
- #329, manglik-dosh never links the site's own checker
- #291, the stale "queries" and "landing pages" wording
- #267, the band

The `debilitated-sun-career` band-file gap (§1c) is an inference from rounding, not a measured defect, so it fails the Evidence Block bar and is reported here instead.

## 6. What I could not determine

| gap | the single measurement that settles it |
|---|---|
| Whether #311 moved CTR | GSC `--by page` for 2026-10-14..11-10, read after about 2026-11-13 |
| Whether any band movement is from #124 | the same window split by `/hi/` vs non-`/hi/` URLs |
| Decay on any page | a non-overlapping prior window, 2026-08-17..09-13 |
| True average position of `/learn/debilitated-sun-career/` | position to 3 decimals |
| Whether `loop-outcomes` run `38386421622` failed by design or by crash | `gh run view 38386421622 --log`. This token's earlier attempt got HTTP 403 on run logs, and I did not retry it |
| Whether `/kundli` and `/rashifal/*` were serving readings in the window | a prose-container probe per CLAUDE.md's `.speakable-body` rule, or Cloud Run logs for 2026-09-14..10-11 |
| Seasonality | the same 28 days one year earlier, which is impossible on a site this young. Treat every delta as unadjusted |
| The "ten highest-impression queries" objective, literally | `--by query` is a partial view (about 9% of impressions per earlier measurement, not re-measured here) |
