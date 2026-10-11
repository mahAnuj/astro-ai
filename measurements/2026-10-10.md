# Analyst report — 2026-10-10

**Window on every number: 2026-09-10 → 2026-10-07 (28 days; the last 3 days are excluded by the exports).**
Sources read this run: `/tmp/gsc-band.json`, `/tmp/gsc-all.json`, `/tmp/ga4.json`. No API re-called. Production was not probed.
Git history read from `origin/main` (unshallowed this run) for confounds. Every figure below was computed from those three files this run; I did not take any number from `BACKLOG.md`, `measurements/` or earlier comments.

## 0. Coverage — read before any number

| export | dimension | window | coverage | truncated | caveat |
|---|---|---|---:|---|---|
| gsc-band | `page` | 2026-09-10..10-07 | 101% of 8,547 property impressions (rows sum 8,604). **Band emitted 101 rows = 7,790 impr. = 91%** | no | `position` is the page's **average** across its queries, not any one query's |
| gsc-all | `page` | same | 101%; 131 rows = 8,604 impr. | no | — |
| ga4 | landing × channel | same | 100% of 273 sessions (rows sum 274); 97 rows, 65 landings as exported, **62 after stripping query strings and folding trailing slashes** | no | bounce / pages-per-session are per channel; I weighted them by sessions |

GSC clicks (property total): **95**. GA4 Organic Search sessions: **135**. Different measures (GA4 includes non-Google engines, and counts differently); I do not equate them.

## 1. The 6–20 band against OBJECTIVE.md

OBJECTIVE.md: *"Move the 6–20 position band into the top 5 on the ten highest-impression **queries**."*
**Cannot be scored literally.** The exports are by page. This run has no query-level data, so I cannot say how much of the query space it would cover. The band below is **pages**. The objective's wording and the measurable unit disagree (#272 closed this only halfway — see §2).

### 1a. Band size (2026-09-10..10-07, `dimension: page`)

| measure | value |
|---|---:|
| pages with average position 6–20 | 101 |
| impressions in band | 7,790 (91% of 8,604 row impressions) |
| clicks in band | 84 (of 95 property clicks) |
| band CTR, impressions-weighted | 1.08% |
| band pages with ≥ 100 impressions | 18 (6,398 impr., 72 clicks) |
| band pages with < 10 impressions | 46 — noise |
| top-10 band pages by `band_opportunity` | 5,382 impr. (69% of the band), 64 clicks (76% of band clicks) |
| outside the band (30 pages) | 814 impr., 11 clicks |
| pages at position > 20 (≥ 1 impr.) | 4; `/festivals` is 360 of their impressions at 30.3 |
| pages already < 6 with ≥ 20 impr. | 5, led by `/learn/shukra-venus-in-vedic-astrology/` (126 impr., 5.8) |

Reading: the band is concentrated, not a long tail of equals. Ten pages hold 69% of its impressions. Fewer than a hundred clicks in 28 days means every per-page CTR below is small-number territory.

### 1b. Top 10 band pages by `band_opportunity` (2026-09-10..10-07)

| # | page | impr. | clicks | CTR | avg pos | band_opp. |
|--:|---|--:|--:|--:|--:|--:|
| 1 | /learn/rahu-mahadasha-ketu-antardasha/ | 1,313 | 27 | 2.06% | 7.5 | 51.8 |
| 2 | /learn/rahu-mahadasha-career-problems/ | 785 | 6 | 0.76% | 7.5 | 41.1 |
| 3 | /learn/debilitated-sun-career/ | 765 | 5 | 0.65% | 6.0 | 40.9 |
| 4 | /learn/sade-sati/ | 626 | 7 | 1.12% | 6.3 | 30.6 |
| 5 | /learn/planets-in-7th-house-marriage/ | 463 | 5 | 1.08% | 6.4 | 22.8 |
| 6 | /learn/manglik-dosh/ | 360 | 3 | 0.83% | 7.8 | 18.6 |
| 7 | /learn/jupiter-in-10th-house-career/ | 301 | 1 | 0.33% | 6.8 | 17.1 |
| 8 | /learn/career-during-sade-sati/ | 336 | 5 | 1.49% | 7.4 | 15.2 |
| 9 | /learn/panch-mahapurush-yoga/ | 253 | 3 | 1.19% | 6.8 | 12.2 |
| 10 | /learn/marriage-mahadasha-timing/ | 180 | 2 | 1.11% | 6.7 | 8.8 |

Every one of the ten is a `/learn/` article. The best-placed band page, `debilitated-sun-career`, sits at 6.0 — the objective's "top 5" is one position away for it and ~two for the next four.

### 1c. CTR outliers (2026-09-10..10-07; reference = impressions-weighted band CTR 1.08%)

Expected clicks = page impressions × 1.08%. Only pages with ≥ 100 impressions are shown.

| page | impr. | clicks | expected | pos | read |
|---|--:|--:|--:|--:|---|
| /learn/rahu-mahadasha-ketu-antardasha/ | 1,313 | 27 | 14.2 | 7.5 | **over** by ~13 — the one clear signal |
| /learn/rahu-mahadasha-career-problems/ | 785 | 6 | 8.5 | 7.5 | under by ~2.5 |
| /learn/debilitated-sun-career/ | 765 | 5 | 8.2 | 6.0 | under by ~3 — best position in the top 10, 0.65% CTR |
| /learn/jupiter-in-10th-house-career/ | 301 | 1 | 3.2 | 6.8 | under by ~2 |
| /learn/saturn-in-10th-house-career/ | 108 | 0 | 1.2 | 7.2 | 0 clicks |
| /learn/the-9-grahas-overview/ | 100 | 0 | 1.1 | 7.9 | 0 clicks |
| /learn/ (index) | 103 | 0 | 1.1 | 15.0 | 0 clicks |

**Verdict on outliers: only #1 is a finding.** The "under" rows differ from expectation by 2–3 clicks; at these counts that is not distinguishable from noise, and I am not filing a title/meta issue on it. The one thing worth a human look: `debilitated-sun-career` at position 6.0 earns the second-lowest CTR of the top 10 — it is cheap to read its SERP snippet, but a count of 5 clicks cannot justify a conclusion.

## 2. Post-ship scoring — issues closed 2026-09-12 → 2026-10-09 carrying `thesis:` AND `metric:`

Closed-issue list read via `gh` (`closed:>=2026-09-12`): **6 issues**. Only one carried both fields.

| issue | closed | thesis / metric present | predicted | actual (window 2026-09-10..10-07) | verdict | posted |
|---|---|---|---|---|---|---|
| **#272** measurement dimensions | 2026-10-08 (c9c0f2b) | both | organic sessions as a separate number; ranking URL beside each of the top-10 band **queries** | Organic Search = **135 of 273** sessions, populated. URL column is **pages**, 101 rows / 7,790 impr.; no query is paired with a URL | **PARTIAL** | yes — [comment](https://github.com/mahAnuj/astro-ai/issues/272#issuecomment-6091629813) |
| #304 learn sticky CTA | 2026-10-09 | `Metric.` only, **no `thesis:`** | pages/session on `/learn` landings, issue's own baseline 1.38 | **not scoreable** — merged 2f5f49f on 2026-10-09, window ends 10-07, zero post-ship days. Baseline re-measured below | **NOT YET** | no comment (excluded: no thesis; nothing post-ship to score) |
| #285, #280, #270, #268 | 2026-10-08/09 | neither field | — | — | not scorable by this protocol | no |

**The miss, stated plainly:** #272 shipped half of what it promised. The north star is now measurable; the band's *query* column is not. The objective in `OBJECTIVE.md` is still unscoreable as worded, and nothing closed this cycle changes that.

**Baseline for #304, so the next analyst can score it** (this run's window, `/learn*` landings, all channels, session-weighted):

| measure | value |
|---|---:|
| `/learn` sessions | 187 |
| pages/session | 1.36 (issue says 1.38 on 2026-09-08..10-05 — consistent) |
| bounce rate | 0.50 |
| sessions in rows at exactly 1.00 pages/session | 146 = **78%** (issue says 71% on its window) |
| Organic Search only: sessions / pages-per-session / share at exactly 1.00 | 118 / 1.45 / 77% |

With ~187 sessions per 28 days this will not reach significance in a single window. Score it on 2–3 post-ship windows, as #304 itself says.

## 3. Confounds — named before any delta

| confound | state (2026-09-10..10-07) |
|---|---|
| **Concurrent ships** | `git log origin/main --since=2026-09-10`: **58 commits**. Those that change what ships to users: #124 Hindi surface (`/hi/` serving 13 URLs, 2026-10-04; sitemap twins 2026-09-20), #268/#303 rashifal cache serving (2026-10-09), #304/#312 sticky CTA (2026-10-09), #270/#299 Hindi rashifal fixes (2026-10-08). The rest is `.github/`, `scripts/`, `.claude/`, `measurements/` and docs. **The window ends 10-07, so #268, #270, #299, #304 land after it** — none of them can explain anything in these numbers. |
| **Hindi surface** | Despite #124, **no `/hi/` URL appears in either GSC (131 pages) or GA4 (62 landings)** this window. It has not yet produced a measurable effect; it also cannot be a confound for the band. |
| **Seasonality** | Not checked. `src/astro_ai/festivals.py` was grepped for Sept/Oct 2026 entries and the pattern matched nothing usable, so I have no repo-sourced festival dates for this window. The band's top pages are evergreen dasha/dosha/house articles, not festival pages, which lowers — but does not eliminate — the exposure. I did not verify festival dates from an outside source. |
| **Page reachable?** | #253 (stale stylesheet via service worker) and #266 (`/kundli` "high demand" under the Groq ceiling) are both **still OPEN** as of this run. #253 affects returning visitors only; #266 affects `/kundli`, which is not in the band. Traffic to `/learn` pages is therefore not obviously traffic to a broken page — but I did not probe production, so I cannot confirm either way. |
| **Sample size** | 95 clicks / 273 sessions in 28 days. Most per-page deltas here are noise; the top-1 page (27 clicks) is the only one big enough to carry a conclusion. |
| **Single window** | I hold one 28-day window. **A decay or trend claim needs a prior window; I cannot make one.** |

## 4. GA4 — where sessions come from and where they stop (2026-09-10..10-07)

### 4a. Channels (all landings; bounce and pages/session weighted by sessions)

| channel | sessions | share | bounce | pages/session |
|---|--:|--:|--:|--:|
| Organic Search | 135 | 49% | 0.35 | 1.57 |
| Direct | 96 | 35% | 0.50 | 3.12 |
| AI Assistant | 35 | 13% | 0.46 | 3.23 |
| Unassigned | 8 | 3% | 0.38 | 0.88 |
| **Total** | **274** (property 273) | | | |

North star (organic sessions): **135 in 2026-09-10..10-07.** No prior window held, so no direction.

### 4b. Top landings, folded (query strings stripped, trailing slashes merged), all channels

| landing | sessions | of which organic | bounce | pages/session |
|---|--:|--:|--:|--:|
| / | 60 | 3 | 0.17 | 5.15 |
| /learn/rahu-mahadasha-ketu-antardasha | 30 | 28 | 0.27 | 1.00 |
| /learn/rahu-mahadasha-career-problems | 12 | 6 | 0.58 | 1.25 |
| /learn/sade-sati | 11 | 9 | 0.27 | 1.00 |
| /learn/marriage-mahadasha-timing | 11 | 0 | 0.91 | 1.00 |
| /learn/debilitated-sun-career | 9 | 6 | 0.22 | 1.22 |
| /learn/griha-pravesh-muhurat-2026-2027 | 9 | 5 | 0.67 | 1.00 |
| /learn/kaal-sarp-dosh | 8 | 2 | 0.63 | 2.25 |

Notes that change how to read it:

- **`/` is not an organic page**: 3 of its 60 sessions are organic; the rest are Direct (49 in one row) and AI Assistant (8). Its pages/session of 5.15 is a returning-user number.
- **`/learn` is where organic lands (118 of 135 organic sessions) and where it stops**: organic `/learn` sessions average 1.45 pages, 77% never view a second page. Non-`/learn` landings (87 sessions) average 4.33.
- The top organic landing, `rahu-mahadasha-ketu-antardasha`, has 28 organic sessions at **exactly 1.00 pages/session** — i.e. every one of them left from the article. This is the page #304 was written about.
- `/learn/marriage-mahadasha-timing`: 11 sessions, **0 organic**; 4 of the 35 AI-Assistant sessions land there. Bounce 0.91. Its GSC row says 180 impressions / 2 clicks. The traffic is real but is not coming from Google.
- GSC clicks vs GA4 organic sessions agree closely on the top page (27 vs 28) and loosely elsewhere (e.g. `jupiter-in-10th-house-career` 1 click vs 5 sessions); I do not rely on the join below the top page.
- One landing arrives with a Google Translate query string (`?_x_tr_sl=en&_x_tr_tl=ta…`) — a separate "landing" for the same page; folded above.

## 5. Decay

**Not determinable this run.** I hold one window. The correct measurement: run the exports for 2026-08-13..09-09 (the 28 days immediately before) and diff `position` per page for the 18 band pages with ≥ 100 impressions. Comparing against the committed `measurements/` files from earlier runs would be comparing ~27 of 28 overlapping days, which shows nothing.

## 6. Issues filed

**None.** Candidates considered and why each was not filed:

| candidate | reason |
|---|---|
| Objective wording vs page-level measurement | Already the open consequence of #272's PARTIAL; the #272 comment states the gap and the measurement that would settle it. A new issue would duplicate it. |
| `/learn` organic sessions leave after one page (77%) | Already the subject of #304 (closed, post-ship window not yet available). Re-filing before that window exists would be guessing. |
| Title/meta for `debilitated-sun-career` etc. | 5–6 clicks versus 8 expected is not evidence. Re-check when the window holds more than ~100 impressions of difference. |
| `/festivals` at position 30.3 (360 impr.) | Outside the band, 1 click; no evidence it is winnable. |

## 7. What I could not determine, and the one measurement that settles each

| unknown | settled by |
|---|---|
| Whether the band moved | The same exports for 2026-08-13..09-09, diffed per page |
| Which *queries* the band consists of, and their coverage | A `--by query` run (with the ranking page as a second dimension if the script allows) and its `coverage_pct` |
| Whether `/learn` pages and `/kundli` were healthy during the window | A probe of production: `/health` revision plus 5 samples of a band page and `/kundli` (not done — this run is read-only against the three files) |
| Seasonality for this window | A sourced festival/Pitru-Paksha date list for 2026-09-10..10-07; none held |
| Whether #304 moved pages/session | `/learn` landings, 2026-10-10 → 2026-11-06 (and the one after), against the 1.36 baseline in §2 |
