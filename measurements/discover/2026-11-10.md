# /discover report — 2026-11-10

**Filed 1 issue: #835** — `/learn/debilitated-sun-career/`: 480 impressions on "which sign" question queries, 0 clicks. It proposes an answer-first FAQ entry and lede sentence. It is not a title test, and it is held until 2026-11-13. `scripts/verify_issue_evidence.py` returned PASS on the draft and again on the live issue. It carries the `<!-- competitor-pattern -->` marker, so it is the first recorded rival pattern in `lessons.md`.

## Inputs and their limits

- **Read first:** `/tmp/gsc-band.json` (window 2026-10-11 → 11-07, page mode, 101 rows, 82% of 21,556 impressions) and `/tmp/ga4.json` (588 sessions). Then `/tmp/measure/report.md` (analyst, 2026-11-09), `measurements/lessons.md`, `OBJECTIVE.md`, the sync of 2026-11-06, the previous discover report and the open issue list.
- **`measurements/sync/chief-guidance.md` does not exist** in this checkout. I followed the 2026-11-06 sync's rulings instead (no new title-only issue until #685 scores; authenticity ranks before growth on `/muhurat`).
- **The "queries" file is page-level.** Query strings exist only in `measurements/gsc-trend-query.json`, at 13% coverage. Every `keyword:` claim describes the measured share only.
- **`data/` is absent (0 of 7 books).** I checked `src/astro_ai/knowledge/` only. #835 adds no rule beyond `grahas.md:193`, and no corpus absence is claimed anywhere.
- **Social search again produced no Reddit or Quora threads** (two public WebSearches: one on the debilitated Sun, one on Sade Sati signs; the tool said it found none). That is four cycles in a row with zero social evidence. I invented none. Someone should decide whether the step stays in the command.
- **Samples are tiny:** 254 clicks and 588 sessions in 28 days.

## What the numbers say

1. Impressions have more than doubled against the previous window (9,474 → 21,046 page-row sum) at flat position (about 7). The growth is volume on pages that already rank, not a position gain. No ship can be credited with it (253 PRs merged in the window).
2. The three pages with the most band impressions (`rahu-mahadasha-ketu-antardasha`, `debilitated-sun-career`, `sade-sati`) hold 7,741 of the 17,606 band impressions (44%). Two of them have a CTR near 0.6%.
3. For `debilitated-sun-career`, the query slice shows a clear pattern. Of 32 sun + debilitat* queries, 16 are "which sign / where / when / in Libra" questions: 480 impressions, 0 clicks, positions 6.3–9.8. The page's `<title>` and FAQ never state the answer, "Libra" appears only in a parenthesis in the opening callout, and the live page has no "which sign" text at all (curl count 0). A rival, astromedha.in, opens with "Sun is debilitated in Libra in Vedic astrology." This is #835.

## Filed

| # | what | why it passed the bar |
|---|---|---|
| **#835** | answer-first FAQ + lede on `debilitated-sun-career` | Window stated. Competing URL fetched. Corpus is `grahas.md:193-203` and sourced. Tokens 0. The repro is an executable curl+grep, and I ran it (0 today). The metric is ≥ 6 clicks on ≥ 300 impressions, baseline 0 / 480, and an export under 10% coverage is INCONCLUSIVE. |

**Weaknesses, stated in the issue:**

- It may be a zero-click SERP, where Google shows the answer itself. The metric is written so that shows up as a miss.
- It is the same family of lever as #311, which missed. It differs because it changes no title or meta, and it targets a question snippet rather than CTR at unchanged position. The risk is the same.
- The 480 impressions are 13% coverage. One rival page is one observation.
- Deploying it before 2026-11-13 would confound #311's score on this page, so the issue holds the merge until the analyst posts that score.

## Not filed, and why

| idea | why not |
|---|---|
| **#513 "add the number to the metric line"** (sync 2026-11-06 assigned it to `/discover`) | Already done: the PM added the metric on 2026-11-07, PR #771 shipped, and the issue closed on production evidence the same day. The analyst scored it "unscoreable at this traffic". The task is moot. |
| **Title/meta on `sade-sati`, `jupiter-in-10th`, `manglik-dosh`, `7th-lord-placement`** | The sync ruled no title-only issue until #685 scores (about 2026-12-04). #311 also reaches 2026-11-13 for three of those pages. |
| **Title/meta on `rahu-mahadasha-ketu-antardasha`** | It carries #276's CTA thesis, which scores on 2026-11-14. Any change confounds it. Its CTR is also above the band median. |
| **Same answer-first pattern on `sade-sati`, `manglik-dosh`** | Not enough data. The Sade Sati query slice is #685's territory and is not yet scored, and I saw no comparable "which sign" family for Manglik. Revisit after #835 scores, and only if it hits. |
| **Per-combination / per-lagna dasha pages** | `OBJECTIVE.md` says optimise the band before publishing more, and CLAUDE.md bars a parallel page type next to `/learn`. No per-lagna dasha table is sourced. |
| **Rashifal pages** (`/rashifal` 147 imp / 0 clicks at 8.5) | Unscoreable at this traffic (analyst). A change now only adds noise. |
| **`kundali-matching-ashtakoot-guna-milan`** (190 imp, 0 clicks, pos 7.7) | `corpus: [UNSOURCED]` (#177/#178/#751) blocks delivery. |
| **Decay: `ashwini-nakshatra`, `the-9-grahas-overview`** | Under 100 impressions in the earlier window, within noise. The analyst filed no decay issue and I agree. |
| **Muhurat growth** (`/muhurat/vidyarambh` 108 imp, `griha-pravesh`) | Standing ruling 3: #713–#715 (rules that disagree with Raman) rank ahead of any new growth build on `/muhurat`. |
| **GA4 `(not set)` and `/admin/*` sessions** | #735 already covers it. |
| **Sade Sati rival structure** (hindutone, smartpuja: they lead with the three currently affected signs) | Already recorded in #685 on 2026-11-03. Filing again would duplicate it. Sources also disagree on when Saturn entered Pisces, so I copied no date or claim. |
| **New `/learn` articles** | Nothing in this cycle's data argues for it. |

## Left for the next cycle

- **Score #311 on or after 2026-11-13, then merge #835.** If #835 also misses, retire "snippet and CTR at unchanged position" as a lever for this band and move to position work (internal links, content depth).
- **A near-full per-query export.** At 13% coverage the objective's "ten highest-impression queries" still cannot be scored.
- **Whether the social step stays in the command.** Four cycles, zero evidence.

Builds nothing, closes nothing, pushed nothing.
