# /discover report — 2026-11-24

Window for all numbers: GSC and GA4, 2026-10-25..2026-11-21 (band file: 97 pages, 74% of 30,711 impressions, 409 clicks; GA4 799 sessions). Analyst report: /tmp/measure/report.md (2026-11-23). Both dispatches ran in the foreground, `seo-growth` first, then `product-manager`.

## Filed
- **#1430** (`growth`, filed by `seo-growth`): the 7th-house pair.
  - `planets-in-7th-house-marriage` has 1,448 impressions, 11 clicks, position 6.8.
  - `7th-lord-placement-marriage-guide` has 1,560 impressions, 16 clicks, position 7.2.
  - The first page has no section for an empty 7th house, or for "which planet is best". A grep for `empty|vacant|unoccupied|no planet` returns 0.
  - It is a body edit plus cross-links, not a title test, because #311 MISSED.
  - Corpus: `houses.md` L211-236 and `vedic_reference.md` L808. Any claim about outcomes of an empty 7th house is `[UNSOURCED]`.
  - Tokens: 0. Metric: combined clicks against 27, engaged share against 33%, pages per session against 1.14.
  - I confirmed with `gh` that it exists, is open and carries the `growth` label. `product-manager` reports checking its corpus citations. I did not read the issue body or re-check them myself.
- No `<!-- competitor-pattern -->` issues were filed. See Rivals below.

## Deliberately not filed, so it isn't re-raised
- **Four top band pages** (`debilitated-sun-career`, `rahu-mahadasha-ketu-antardasha`, `jupiter-in-10th-house-career`, `sade-sati`) each already have a shipped change waiting to be scored. Another edit would confound the score. The pending items and their earliest scoring dates are #685 (12-04), #835 (12-14), #1073 and #1075 (12-17). Revisit after those dates.
  - This follows chief's "file band-page issues for the top pages" row only partly. Filing for pages with an unscored ship would break the analyst's measurement.
- **Title or meta rewrites:** #311 MISSED, and the titles already carry the query words.
- **Sade-sati per-sign start and end dates:** wait until after #685 scores. Dates must come from `chart.py`. The phase names arambha, madhya and uttara are not in the corpus, so the page must not call them classical.
- **Panch-mahapurush** (1,074 impressions, position 7.2, 1.49% CTR): the visible queries are 1 to 8 impressions each. The "best" and "rare" claims they ask for are `[UNSOURCED]` in `vedic_reference.md` §4.1 and `yogas.md` §5. There is no verified rival URL.
- **Mangal-mars, shukra-venus, manglik and gochar:** no query-level signal that ties to a page gap. Manglik overlaps open #777, #1369 and #1396. Revisit once the page-by-day export (#953) exists.
- **Per-festival pages** (Kartika Purnima, Kalabhairav Jayanti, Vivah Panchami, Gita Jayanti, Dattatreya Jayanti, Makar Sankranti/Pongal):
  - CLAUDE.md forbids a parallel page type for festival queries.
  - No visible query matches any of the six.
  - `/festivals` ranks 38.1 with 0 clicks.
  - Kartika Purnima is today.
  - If wanted later, the route is a `/learn` article, with every date sourced.
  - I did not check the festival dates against an almanac.
- **gochar-2027 not indexed:** tracked by #1065.
- **Funnel step-loss findings:** the event instrumentation is unfinished (#1070). A finding without a measured step would be an opinion.
- **`muhurat_searched` absent from `ga4-events.json`:** per the analyst, to be filed after #1336's window opens on 2026-12-22.

## Gaps in this run
- **Social research was not done.** `product-manager` had WebFetch but no WebSearch, and Reddit blocks WebFetch. Nothing was invented. The next run should give that dispatch WebSearch, or run the social step from the coordinator.
- **Rival research is thin.** A Google search returned nothing and a guessed AstroSage URL returned 404. The only rival URLs recorded are astrosight.ai and jagannathhora.com, and they are already in #1430. No new rival pattern was filed.
- **`data/` is absent in this checkout.** Corpus checks covered `src/astro_ai/knowledge/*.md` only, not the source books. A zero is a term check, not proof the concept is absent.
- **Growth split:** 0.12 against a 0.40 target. Filing was not forced to lift it, because the evidence bar and the unscored ships block more filings. The levers are chief's open picks, #1076, #1107 and #1065, and the page-by-day export (#953).
- **Chief guidance followed and not followed:** followed on `lessons.md` (MISS #311) and on picking growth. The "file band-page issues" instruction was applied only to pages with no unscored ship, which gave #1430.
- No token-budget conflicts: nothing proposed uses an LLM call.
- `AGENT_STATUS.md` has one heartbeat line from `product-manager`, which is local only.
