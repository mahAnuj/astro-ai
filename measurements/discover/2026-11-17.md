# /discover report — 2026-11-17

**Issues filed: 0.** Every candidate either already has an issue, already has a page, or lacked demand evidence. Reasons are below so the same ideas are not re-raised next week.

## Inputs read, in order

1. `/tmp/measure/report.md` (analyst, run 2026-11-16, window 10-17 → 11-13), `/tmp/gsc-band.json` (window 10-18 → 11-14), `/tmp/ga4.json`, and `measurements/gsc-trend-query.json` for query rows.
2. `measurements/lessons.md` and `measurements/sync/chief-guidance.md`.
3. Rivals and social: two public `WebSearch` calls. The social search returned no Reddit threads. Rival pages seen are search results only; I did not WebFetch them.
4. Corpus: **`data/` is absent in this checkout, so zero of the seven books were present.** `knowledge/*.md` was greppable. Any "unsourced" statement below is therefore unmeasured against the books.

## What the numbers say (not re-derived)

- Impressions are up 140% and clicks up 228% over the prior window. `/learn` articles are 93% of impressions.
- The objective is unmet. None of the top-10 band pages is at position ≤ 5.0, and all ten sit at 6.4–7.7.
- #311 is a MISS (a title/meta rewrite did not reach the bar). I am not proposing another title-only test. The pages that need work are CTR-gapped, so any change has to be content or answer-first structure, as #835 was.

## Analyst inbox — one line per item

### Search demand (analyst §8)

| item | decision |
|---|---|
| "sun debilitated in which sign" family (524 impr, 0 clicks) | **Not filed.** #835 shipped 2026-11-13 and is scoreable from 2026-12-14. Filing again would stack a second change on an unmeasured one. |
| "jupiter in 10th house" / "guru in 10th house" | **Not filed.** #1073 (closed 2026-11-16) covers it. Re-measure before more work. |
| "10th lord in 6th house" | **Not filed.** It converts at 2.85%, so no action is needed. |
| "rahu mahadasha ketu antardasha" family | **Not filed.** #1075 (closed 2026-11-16) covers it. The head query went from position 9.6 to 7.0. |
| `/matching` decay (position 4.2 → 9.3) | **Not filed.** #1076 and #508 own it, and the onset cannot be dated until #953 lands. |
| `gochar-2026` (1,863 impr, 28s engagement) | **Not filed.** The cause is unknown and #1079 rewrote the page after the window. Re-measure first. #1071 covers the 2027 sibling. |
| `yes` query | **Not filed.** A one-word query that nobody targets. |

### Content opportunities (analyst §9)

| item | decision |
|---|---|
| Devuthani Ekadashi, 2026-11-20 (3 days) and Tulsi Vivah, 2026-11-21 | **Not filed.** Both already have dated entries in `festival_registry.py` with significance and observance text. They are covered by `/festivals`. A new `/learn` page would not be indexed in 3 days. CLAUDE.md also bars a parallel page type for queries an existing page serves, and `/festivals` is at position 34, so there is no ranking page to protect either way. The Ekadashi fast and Chaturmas rules are UNSOURCED in the corpus: `vedic_reference.md` lists `chaturmas` as UNSOURCED, and the corpus holds no Ekadashi-as-fasting source. |
| Makar Sankranti / Pongal, 2027-01-15 | **Not filed this cycle.** The date is outside any window I could justify from this cycle's data. Revisit about 2026-12-15 with the index-status measurement (#1065). |
| `gochar-2027`, `vivah-muhurat-2027` | Already exist or are filed (#1071). |

## Rival patterns observed

Two public searches only; no rival page was fetched.

- **Dasha × antardasha pair pages.** `astromedha.in/insights/vedic/rahu-mahadasha-ketu-antardasha`, its mirror `ketu-mahadasha-rahu-antardasha`, and `ajmerastro.com/.../dasha/ketu-mahadasha/rahu-antardasha` each publish one page per pair.
- **Sign × house placement pages.** `vedicbirth.com/placement/sun/libra/10` publishes one page per placement.

**Not filed as `<!-- competitor-pattern -->` issues.** I measured the demand from `gsc-trend-query.json`, the 14% query view. Pair-keyed queries concentrate on one pair:
- Rahu/Ketu variants add up to roughly 800 impressions.
- The mirror pair "ketu mahadasha rahu antardasha" has 6 impressions plus about 10 more across variants.
- Every other pair seen is 1–2 impressions, for example "jupiter mahadasha and venus antardasha" at 2.

The 81-page pattern has no measured demand, so a thesis for it would be an opinion. The one pair with demand is already served by the top page, now at position 6.4. The owner's rule asks for one issue per rival pattern. The discover bar asks for nothing that cannot be justified from this cycle's data. I followed the second and am recording the pattern here instead. A reason to revisit: a pair other than Rahu/Ketu reaching 20 or more impressions in a window.

Pages built as programmatic combinations also carry grounding risk. "grounding" is the largest QA-fail theme in `lessons.md` (27 FAILs), and per-combination interpretation text is exactly the claim shape those FAILs name. I copied no astrological claim from a rival.

## Lessons applied

- #311 MISS: no title/meta-only issue filed.
- Chief guidance (analyst row: state the traffic needed before filing a thesis). At about 711 sessions per 28 days, a new page's thesis would need roughly 300 impressions to score. None of the candidates met that.
- Chief guidance (start list): the three unowned band pages have since been covered by #1073 and #1075. `7th-lord-placement-marriage-guide` (1,512 impr, CTR 0.99%, position 7.2) and `planets-in-7th-house-marriage` (1,149 impr, CTR 0.96%, position 6.6) have no *open* ranking issue. Their prior issues (#978, #1085, #988, #990, #992) were all corpus-grounding fixes, not answer-first work. **I did not file for them.** I have no query-level data for either page, so I could not write the `keyword:` field. The 14% view does not surface their queries, and a filed issue would guess at the intent. The next run should use a per-page query export if one exists; a fix would be one query export for those two pages. That is a measurement gap, not an issue.

## Gaps this run could not close

- `data/` absent, so every corpus check was against `knowledge/*.md` only.
- `/tmp/gsc-band.json` has no query dimension.
- No rival page was fetched, only search-result summaries.
- GA4 has no prior-window export (#1115 is open).
