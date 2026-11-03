# /discover report — 2026-11-03

**Filed 1 issue: #685** (`/learn/sade-sati/` title/meta names no Moon sign). It passes `scripts/verify_issue_evidence.py` (PASS, 0 problems), run on the draft before filing and again on the live issue. Everything else I considered is under "Not filed".

## Inputs and their limits

- **Read first:** `/tmp/gsc-band.json` and `/tmp/ga4.json` (window 2026-10-04 → 10-31), then `OBJECTIVE.md`, the analyst's 2026-11-02 report, the previous `/discover` report (2026-10-26) and the open issue list.
- **`/tmp/measure/report.md` does not exist.** I used `measurements/2026-11-02.md` (window 10-03 → 10-30). It overlaps this window by 27 of 28 days, so I read no movement into the one-day difference. I did not contradict any of its findings.
- **The "queries" file is page-level.** `gsc-band.json` is `dimension: page`: 101 rows, 13,991 impressions (84% of the property's 16,606). Query strings exist only in `measurements/gsc-trend-query.json`, which covers **8%** of impressions at 1–9 impressions per query. So every `keyword:` claim is an intent signal, not a volume. The objective's "ten highest-impression queries" still cannot be scored. This is already tracked in #272 and #291.
- **Tiny samples.** 182 clicks and 489 sessions in 28 days. Most per-page GA4 figures are 1–12 sessions.
- **Social search returned nothing again.** I ran one public WebSearch for r/vedicastrology on the Rahu–Ketu combination. It returned astrology sites and blogs, and the tool said it found no Reddit threads. That is three cycles running with no Reddit or Quora evidence. I invented none. The step is not producing evidence in this environment, and someone should decide whether it stays in the command.
- **Skills not invoked:** `seo-auditor`, `keyword-researcher` and `competitor-scout` are not in this session's skill list. Rivals came from WebSearch and WebFetch.
- **Corpus:** `data/` is absent from this checkout (0 of 7 books). I checked `src/astro_ai/knowledge/` only. #685 adds no astrological claim, so no book-level check was needed.

## What the numbers say

1. **Impressions are 16,606 against 15,940 last week.** Clicks are 182 against 173. CTR is flat at about 1.1%. Position has not moved into the top 5. The band is still the same pages: rahu-mahadasha-ketu-antardasha (2,916 impr, 33 clicks, pos 6.8), debilitated-sun-career (1,928, 11, 6.5) and sade-sati (1,754, 11, 6.4) carry 6,598 of the 13,991 band impressions (47%).
2. **Channels:** Organic 250, Direct 214, AI Assistant 19, Unassigned 7. AI Assistant is the best-engaged channel (19 sessions, 3.16 pages/session in the analyst's table) but far too small to specify on.
3. **`/learn/sade-sati/` is the largest untested CTR outlier.** The analyst named it and did not inspect its title. I did. The live `<title>` is `Sade Sati: Saturn's 7.5-Year Lesson (Without the Fear)`. It names no sign, while two rivals lead with the three signs currently affected. The page's own GA4 behaviour is good (organic bounce 36%, 2.18 pages/session). The gap is arriving, not staying. That became #685.

## Filed

| # | title | why it passed the bar |
|---|---|---|
| **#685** | `/learn/sade-sati/` title names no Moon sign — 1,754 impressions at 0.63% CTR | Window stated. Two rival URLs fetched on 2026-11-03: hindutone.com and smartpuja.com. Corpus cited as `vedic_reference.md:218-232`, and the issue says plainly that `data/` was absent. Tokens are 0. The repro is an executable grep, and I ran it (count 1 today). The metric is CTR ≥ 1.2% on ≥ 1,200 impressions at position within ±1 of 6.4, and anything below that is INCONCLUSIVE. |

**Weaknesses, stated in the issue and repeated here:**

- It is the same shape of thesis as #311, which missed (0.81% against a 1.5% bar). I filed it because #311's rewrites were generic and this one targets observed query wording, and because it is the only top-3 page with no title test. If it misses too, the loop should stop filing title tests for this band.
- The query evidence is five strings at 1–9 impressions each.
- Seasonality is not ruled out: impressions on this page went from 451 to 1,685, and Diwali is 2026-11-08.
- At 11 baseline clicks, a doubling is about 2 standard deviations, so a pass would be suggestive, not conclusive.
- The title goes stale on 2027-06-03, when Saturn enters Aries. Acceptance criterion 5 requires a dated comment.
- I could not see the rivals' `<title>` tags. The claim is about their H1/headline.
- The FAQ phase labels on the page (Aquarius setting, Pisces peak, Aries rising) are my reading of the page's own FAQ #1, not new data.

## Not filed, and why

| idea | why not |
|---|---|
| **Title/meta changes on `rahu-mahadasha-ketu-antardasha`** (2,916 impr, CTR 1.13%) | The analyst's reference page. CTR fell from 2.05% in #311's window to 1.13% here, but the volume doubled over the same period and position improved. It carries #276's CTA. Another change would confound that score. |
| **Title/meta on `debilitated-sun-career`, `jupiter-in-10th-house-career`, `manglik-dosh`** | #311 rewrote these on 2026-10-13, and #521 and the Manglik series touched them. Its rescore window runs to about 2026-11-13. |
| **`/matching` title/meta** (pos 4.4, 0 clicks) | Already #508. |
| **GA4 `(not set)` landing: 15 sessions, 10 organic, bounce 93%, 0 pages/session** | About 3% of sessions with no page view recorded. I have no repro and no cause (consent timing, an error page, an in-app browser?). A hypothesis is not an Evidence Block. It needs a per-event export, and #570 is the nearest owner. |
| **Direct deep-link landings on `/learn/*`** (e.g. rahu-ketu Direct 12 sessions, bounce 100%; `?hl=`, `?_x_tr_` translate parameters) | Likely dark-social or in-app traffic. Nothing in the exports says what it is, and I won't specify a share feature on a guess. |
| **Per-lagna / per-combination dasha pages** (ajmerastro.com has `/dasha/rahu-mahadasha/ketu-antardasha/aquarius-lagna`; astromedha.in and jagannathhora.com have per-combination pages) | `OBJECTIVE.md`: optimise the band before publishing more. CLAUDE.md warns against a parallel page type next to `/learn`. The rule content would need sourcing first, and the corpus has no per-lagna dasha table that I checked. |
| **Tool CTA on `rahu-mahadasha-career-problems`** | #276 is PROVISIONAL and #329 INCONCLUSIVE. #518 owns the family. Adding a third CTA thesis before either scores is activity, not progress. |
| **`/festivals`** (impressions down 58.5%, pos 28) | Outside the band, 245 impressions and 0 clicks, and the festival-date sourcing problem is unresolved. |
| **`kundali-matching-ashtakoot-guna-milan`** (202 impr, 0 clicks, pos 7.7) | Its `corpus:` would be `[UNSOURCED]` (#177/#178), which blocks delivery. Those issues are the unblocker. |
| **`/rashifal` and `/rashifal/*`** | #515/#514 are not scoreable yet. A change now contaminates the baseline. |
| **`/panchang/YYYY-MM-DD` pages** (about 40 rows, under 5 impressions each) | Too small to carry a metric. |
| **New `/learn` articles** | `OBJECTIVE.md`. Nothing in this cycle's data argues otherwise. |
| **Sitewide `seo_title` backfill** | #311 has not shown that title rewrites move CTR. |
| **`/admin/ops` and `/admin/activity` in GA4** (about 13 sessions) | Owner traffic in the property totals. It is a measurement hygiene point, not a growth issue. |
| **Arambha/Madhya/Uttara on the Sade Sati page** | SOURCES.md:530 marks them UNSOURCED, and #430 is closed. I only constrained #685 not to use them. |

## Left open for the next cycle

- **Rescore #311 on or after 2026-11-13, and #685 about 28 days after it deploys.** If both miss, retire title tests as a lever for this band.
- **A per-query export at near-full coverage.** Without it the objective stays unscoreable as written.
- **Whether the Reddit/Quora step should stay in the command.** Three cycles, zero evidence.
- **The `(not set)` GA4 landings.** Revisit once #570's event exists.

Builds nothing, closes nothing, pushed nothing. The only repo-side write was a line appended to `AGENT_STATUS.md`, which is gitignored.
