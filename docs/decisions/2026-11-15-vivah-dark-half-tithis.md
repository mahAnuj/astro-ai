# Vivah excludes the waning-half 11th-13th and gives the bright-half 12th no credit

- **Date:** 2026-11-15
- **PR / issue:** #1022 (parent #1017)

## Why, measured

`EVENT_RULES["vivah"]["good_tithis"]` is keyed on the tithi name alone, so Krishna (dark-half)
Ekadashi, Dwadashi and Trayodashi earned the same +2 as their bright-half namesakes. Raman,
*Muhurtha*, marriage chapter, as `knowledge/vedic_reference.md` section 29.9 paraphrases it,
rejects the dark-half 11th through New Moon and calls the bright-half 2nd, 3rd, 5th, 7th,
10th, 11th and 13th best. Rao's Table 79 Wedding row (`knowledge/grahas.md`) lists the 12th
with no paksha, so the 12th is contested between the two held books. `data/` was absent when
this was ruled (astro-auditor, 2026-11-15); everything is from the knowledge files.

Chosen, Vivah only: a new per-event key `avoid_krishna_tithis` (Ekadashi, Dwadashi,
Trayodashi) read with `.get()` in `score_event`, in the hard-exclusion block after
`avoid_tithis`, flag `avoid_krishna_tithi`; and Dwadashi leaves `good_tithis` and stays
neutral (the smallest claim under a contested source). Shashti stays unscored, Purnima stays
avoided. The page says whose rule each is (Raman for the exclusion; Rao versus Raman for the
12th) and does not call either "classical" (#1024). The waning-half 2nd-10th keep the
finder's own credit: the held sources say nothing about them for marriage, and the page says so.

The other four events have no event-specific tithi rule in the knowledge files, so they are
untouched (recorded as contested on the issue, not wrong). Measured, New Delhi, 365 days from
2026-11-14: griha_pravesh, business, vidyarambh and namkaran ratings, reasons and flags are
byte-identical before and after.

Vivah, same window: waning-half 11th-13th days rated acceptable or better 6 -> 0 (4 of them
excellent; the issue's 9 predates #1021 and #1023 merging, which already removed three);
days whose rating changed 9; bright-half Dwadashi days rated acceptable or better 4 -> 3.
Tokens: 0, no LLM call or prompt touched.

Rejected: reusing `avoid_tithis` with a paksha tuple (it is shared by five events and keyed on
name; changing its type touches all of them), and excluding the bright-half Dwadashi (Rao lists
it, so an exclusion would assert more than the sources agree on).
