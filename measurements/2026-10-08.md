# Analyst report — run of 2026-10-08

**Window on every number below: 2026-09-08 → 2026-10-05 (28 days).** Taken from the `window` field in all three files (`/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`). It excludes the last 3 days; GSC is not final before that and GA4 lags 24–48h. Every figure was computed this run from those files. Nothing is carried over from `BACKLOG.md`, earlier comments or memory.

## Headline

| Finding | Value (2026-09-08 → 2026-10-05) |
|---|---|
| Ten highest-impression band queries already in the top 5 | **0 of 10** |
| Those ten: impressions / clicks / impression-weighted position | 349 / 6 / 9.33 |
| Issues scored against a thesis | **0** — no issue closed in the last 28 days (see §2) |
| New issues filed | **0** — every finding that needs action is already open (see §4) |

Nothing can be said about movement. This is a single-window baseline, with no prior window fetched and no scorable ship (§2, §3, §6). The sample is also thin: one query has more than 100 impressions, and 26 of the 56 band rows have exactly 1 impression.

---

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *move the 6–20 band into the top 5 on the ten highest-impression queries.*

### 1a. Band totals

| Measure | Value | Window |
|---|---:|---|
| Band queries (position 6–20) in `gsc-band.json` | 56 | 2026-09-08 → 2026-10-05 |
| Band impressions | 469 | same |
| Band clicks | 6 | same |
| Band CTR | 1.28% | same |
| Impression-weighted band position | 9.37 | same |
| Band rows with exactly 1 impression | 26 of 56 | same |
| Band rows with ≤ 2 impressions | 33 of 56 | same |
| Band rows with ≥ 10 impressions | 10 of 56 (349 impressions, 74% of the band) | same |

`gsc-all.json` holds 100 rows (620 impressions, 9 clicks) and is truncated by the fetch script. 19 of the 56 band rows are absent from it, so any total taken from `gsc-all.json` is a lower bound. The band totals above come from `gsc-band.json`, which is the complete band.

### 1b. The ten highest-impression band queries (the objective's target set)

| # | Query | Impr. | Clicks | CTR | Avg pos | In top 5? |
|--:|---|--:|--:|--:|--:|:-:|
| 1 | rahu mahadasha ketu antardasha | 157 | 4 | 2.55% | 9.6 | no |
| 2 | rahu dasha with sun mahadasha and job | 32 | 0 | 0% | 9.3 | no |
| 3 | rahu mahadasha ketu antardasha remedies | 29 | 0 | 0% | 8.6 | no |
| 4 | rahu mahadasha and ketu antardasha | 26 | 0 | 0% | 9.1 | no |
| 5 | ketu antardasha in rahu mahadasha | 23 | 0 | 0% | 9.9 | no |
| 6 | what is manglik dosh | 23 | 0 | 0% | 9.5 | no |
| 7 | rahu dasha ketu antardasha | 19 | 1 | 5.26% | 9.8 | no |
| 8 | rahu ketu antardasha | 15 | 0 | 0% | 9.1 | no |
| 9 | manglik dosh in english | 13 | 0 | 0% | 6.8 | no |
| 10 | rahu mahadasha with ketu antardasha | 12 | 1 | 8.33% | 9.1 | no |
| | **Top-10 total** | **349** | **6** | 1.72% | 9.33 (weighted), 9.2 (median) | **0 / 10** |

Nine of the ten sit at positions 8.6–9.9, which is the bottom of page one. Only "manglik dosh in english" (6.8) is clearly higher.

### 1c. Query families in the band

The family is the set of band queries containing the stated words.

| Family | Band rows | Impr. | Clicks | Window |
|---|--:|--:|--:|---|
| Contains `rahu` or `ketu` (dasha/antardasha) | 21 | 344 | 6 | 2026-09-08 → 2026-10-05 |
| Contains `manglik` / `mangalik` | 12 | 66 | 0 | same |
| Contains `bhagya` (brand-ish) | 6 | 28 | 0 | same |
| Contains `sade sati` / `saturn` / `shani` | 7 | 17 | 0 | same |

- The Rahu–Ketu family is **73% of band impressions (344 of 469) and all 6 of the band's clicks.**
- The objective is, in practice, one topic. Moving that family is moving the objective.
- Manglik is the second cluster: 66 impressions, 0 clicks.

### 1d. CTR outliers

| Observation | Value | Verdict |
|---|---|---|
| Band rows with ≥ 10 impressions and 0 clicks | 7 of 10 | The band's own median CTR for these rows is **0%**, so "poor CTR vs the band median" cannot be computed. The comparison degenerates. |
| Best row: "rahu mahadasha ketu antardasha" | 157 impr, 4 clicks, 2.55% at pos 9.6 | Not an outlier. Four clicks cannot be told apart from noise. |
| Sibling Rahu–Ketu queries, same position range (rows 2–5 and 8 in 1b) | 0 clicks on 32+29+26+23+15 = 125 impressions | Too small to call a title/meta problem. At ~2.5% CTR the expectation would be ~3 clicks, and zero is not distinguishable from that. |

**Not determinable:** whether any CTR gap is a title/meta problem. GSC is exported without a `page` dimension (#272), so a query cannot be tied to the URL that ranks, or to that URL's title.

### 1e. Off-band context (not in the objective, reported so it is not mistaken for the band)

| Group | Rows (in `gsc-all`) | Impr. | Clicks | Position range | Window |
|---|--:|--:|--:|---|---|
| Festival / puja queries ("hindu festivals", "puja calendar", "today festival" …) | 36 | 84 | 0 | 8 → 103 (mostly 63–103) | 2026-09-08 → 2026-10-05 |
| Top-5 rows with ≥ 3 impressions | 8 | 40 | 0 | 2.1 → 3.8 | same |

- Festival queries are far outside the 6–20 band. That is #267's P4 and not a band item.
- Most top-5 rows are brand-ish or off-topic: "shubhagya", "bhagya.com", "yes", "om angarakaya namah", "jupiter in tamil".
- Only "rahu mahadasha" (6 impr, pos 2.8) and "rahu mahadasha effects" (3 impr, pos 3) are real head terms already in the top 5, and both are tiny.

---

## 2. Post-ship scoring

| Check | Result |
|---|---|
| Issues closed in the last 28 days (2026-09-10 → 2026-10-08) | **0.** The most recent closed issue is #229 / #261, closed 2026-09-04. |
| Closed issues whose body contains "thesis" or "metric:" | 3: #235, #210, #189. Each match is incidental prose, not a `thesis:` / `metric:` field, and all three closed before 2026-09-10 (2026-09-04, 2026-08-16, 2026-08-09). |
| Issues scored | **0** |
| Comments posted on issues | **0** |

- **No score was fabricated.**
- The five PRs merged in the window were #269, #271, #273, #274 and #275, all closed 2026-10-07 → 2026-10-08. By file list they touch only `.claude/`, `.github/workflows/`, `scripts/fetch_*`, `OBJECTIVE.md`, `TEAMS.md`, `CLAUDE.md` and `measurements/`.
- None touches `src/`, templates or CSS, so none can have moved a site metric.

Where the redesign epic sits (the biggest site change in recent weeks):

| Item | Status |
|---|---|
| Redesign sub-issues (#235–#261 range) | Closed 2026-09-04 11:07–11:16 UTC, **4 days before** this window opens |
| Carried a `thesis:` / `metric:` | No |
| Scorable here | No. A pre-redesign 28-day window (before 2026-09-04) was not fetched, and this window has no pre-ship comparison. |

---

## 3. Confounds

| Confound | Finding |
|---|---|
| Concurrent ships in the window | `git log origin/main --since` returned **1 commit** (`a2c41af`, discover report, 2026-10-08) because the clone is shallow (`git rev-parse --is-shallow-repository` → true). **Cannot be used to enumerate ships.** From `gh pr list --state merged`: 5 PRs, all agent/CI infrastructure, none touching `src/` (§2). |
| Redesign (#233 epic) landing | Sub-issues closed 2026-09-04, **4 days before the window starts.** Any ranking or engagement change in this window may carry the redesign's effect. Not separable with one window. |
| Seasonality | Not tested. The window sits in the autumn festival run-up, and festival traffic is violently seasonal on this site. No year-ago window exists because the site is too young. Treat the festival and muhurat rows (`/festivals`, `griha-pravesh-muhurat-2026-2027`, `/panchang/*`) as calendar-driven. |
| Was the page reachable? | Probed 2026-10-08, from the runner: `/` 200, `/learn/rahu-mahadasha-ketu-antardasha/` 200, `/learn/manglik-dosh/` 200, `/festivals` 200, `/kundli` 200, `/health` 200 (revision `bhagya-00391-bmt`, `build_sha` null). Each answered in 0.55–0.92s. These probes are a spot check **today** and do not prove the pages worked throughout the window. |
| #253 stale stylesheet | Still open, with the stylesheet half marked fixed on 2026-09-04 (`app.css?v=` content-hashed). Fixed before this window opens. Not re-verified this run. |
| #266 `/kundli` "high demand" (Groq 413) | Still **open**. Its last comment, 2026-09-05, is a QA pass on a prompt-budget fix. I did **not** submit a chart this run, so I cannot say whether chart generation worked during the window. GA4 shows 1 session landing on `/kundli`, so funnel conclusions about kundli are not supportable either way. |
| Non-search traffic in GA4 | 4 sessions landed on `/?fbclid=…` (Meta click ids), all with 100% bounce. The export has no channel dimension, so GA4 totals mix organic, direct and social. **GA4 session counts below are not "organic sessions".** |
| Sample size | 254 GA4 sessions in 28 days. 469 band impressions. Most per-page and per-query deltas are noise. |

---

## 4. Issues filed

**None.** Every finding that needs action is already filed.

| Finding in this run | Already tracked by | Why not refiled |
|---|---|---|
| Organic sessions not computable (no channel dimension) | #272 | Same gap. |
| Band query cannot be mapped to its ranking page (no `page` dimension) | #272 | Same gap. |
| `gsc-all` truncated to 100 rows; 19 of 56 band rows missing from it | #272 (finding 3) | Reconfirmed this run, nothing new. |
| Funnel (landing → form → result) not measurable | #272 (fifth gap) | Same gap. |
| Top landing page sends 0 of its sessions onward (see §5) | #276 | Filed 2026-10-08, 0 comments. |
| 6–20 band optimisation | #267 | The standing objective issue. |
| Non-canonical URLs split into separate GA4 rows | #272 (finding 4) | Checked live: `/learn/marriage-mahadasha-timing` and `/learn/rahu-mahadasha-career-problems` return **307** to the trailing-slash URL, and the canonical tag matches. Not a serving defect, only a reporting artefact. |

---

## 5. GA4 landing pages

Window 2026-09-08 → 2026-10-05, from `/tmp/ga4.json`. 65 landing rows, 254 sessions. **Not organic-only** (no channel dimension).

| Segment | Rows | Sessions | Pages/session (session-weighted) | Bounce (session-weighted) |
|---|--:|--:|--:|--:|
| `/` (homepage) | 1 | 56 (22% of all) | 5.39 | 14.3% |
| `/learn/*` articles | 49 | 176 | 1.38 | 48.9% |
| Tool and other landings (`/festivals`, `/muhurat/*`, `/panchang/*`, `/rashifal*`, `/ask`, `/kundli`, `/matching`, `/terms`) | 11 | 18 | not computed (too few) | not computed |
| `/?fbclid=…` | 4 | 4 | 1.0 | 100% |

| Observation | Value | Window |
|---|---|---|
| `/learn/` landings with pages/session exactly 1.00 | 35 of 49 rows, 125 of 176 sessions (71%) | 2026-09-08 → 2026-10-05 |
| Top `/learn` landing, `/learn/rahu-mahadasha-ketu-antardasha/` | 29 sessions, bounce 27.6%, **pages/session 1.00** | same |
| Same page: sessions that viewed a second page | none (mean of exactly 1.00) | same |
| Weakest repeat landings | `/learn/marriage-mahadasha-timing/` 7 sessions, 100% bounce; `/learn/manglik-dosh/` 5 sessions, 100% bounce; `/learn/rahu-mahadasha-career-problems/` 10 sessions, 60% bounce | same |

- The Rahu–Ketu page is the biggest `/learn` landing and the one the 21-row band family points at. All 29 sessions read it and stopped.
- Whether that is a missing call-to-action or the natural end of a visit **cannot be determined from this export.** #276 owns it.
- Per-page bounce rates on fewer than ~10 sessions are not conclusions.

---

## 6. What I could not determine

| Question | Why not | The single measurement that settles it |
|---|---|---|
| Did any ship move the band or sessions? | No closed issue carries a `thesis:` / `metric:` in the window. No prior-window data was fetched. | Fetch `fetch_gsc.py` / `fetch_ga4.py` for the 28 days ending 2026-09-07. This is a call I was told not to make. |
| Which queries lost ground (decay)? | One window only. | Same prior-window GSC export, joined on query. |
| Organic sessions (the north star) | GA4 export has no channel or source dimension. | Add `sessionDefaultChannelGroup` to `fetch_ga4.py` (#272). |
| Which URL ranks for each band query | GSC export has no `page` dimension. | Add `page` to `fetch_gsc.py` (#272). |
| Whether the CTR of the Rahu–Ketu family is a title/meta problem | Zero-click rows are too few to distinguish from noise, and no page mapping. | A page-level GSC export for `/learn/rahu-mahadasha-ketu-antardasha/` over a longer window. |
| Whether `/kundli` chart generation worked during the window | I did not submit a chart. #266 is still open. | A POST to `/kundli` with a chart, or the Cloud Run logs for `413` / "high demand" in the window. |
| Funnel step-through for kundli, matching and numerology | Landings: `/kundli` 1, `/matching` 1 session. No event dimension in the export. | `eventName` or `pagePath` + `previousPagePath` in the GA4 export (#272). |
| Which commits shipped in the window | Shallow clone, 1 commit visible. | `git fetch --unshallow`, or `gh api repos/mahAnuj/astro-ai/commits?since=2026-09-08T00:00:00Z`. |

---

*analyst, read-only. No code, template, content or BACKLOG.md edited. No issue comments or new issues posted this run, because there was nothing to score or file.*
