# Shashti and Dwadashi join the avoided tithis for Griha Pravesh, and Shashti for Vivah

- **Date:** 2026-11-27
- **PR / issue:** #1504

## Why, measured

Raman's general avoid list is the 4th, 6th, 8th, 12th, 14th, full and new moon (Panchanga Suddhi,
L1329; Ch. II L802 gives the shorter form without the 6th). `knowledge/vedic_reference.md` section
29.13, Griha Pravesh row, records that his general rule governs house entry, and section 29.9
records the same list and the marriage chapter's rejection of "the 8th, 12th and 6th" (L3728-3732).
The finder's `avoid_tithis` for `griha_pravesh` held only 4, 8, 9, 14, Amavasya and Purnima, so a
Shashti or Dwadashi house entry was graded "good" and a Sarvartha Siddhi day lifted it further. For
`vivah` the 6th was missing the same way.

**Ruling (astro-auditor, #1504, binding):**

| Event | Shashti | Dwadashi |
|---|---|---|
| Griha Pravesh | added to `avoid_tithis` | added to `avoid_tithis` |
| Vivah | added to `avoid_tithis` | CONTESTED (#1022); stays neutral in the bright half, already excluded in the dark half by `avoid_krishna_tithis` |

Vivah's Dwadashi is contested because Rao's Table 79 Wedding row lists the 12th while Raman's
marriage chapter rejects it. Shashti is not contested for a wedding: Raman rejects it and Rao's row
does not list it. Navami stays in both sets as this finder's own addition (neither table rejects it
for house entry). `corpus:` sources: `knowledge/vedic_reference.md` 29.9 and 29.13, `knowledge/grahas.md`
Table 79.

**`data/` was absent on the runner.** The books were not re-read; the change rests on the repo's own
paraphrase in the sections above and on the auditor's ruling.

**Before and after** (`find_candidates`, New Delhi, 365 days from 2026-11-27, 730 rows across both
events; per-date diff of rating and flags):

| Event | Rating changes | Detail |
|---|---|---|
| vivah | 5 | 2027-01-27 excellent to avoid (Krishna Shashti, Sarvartha Siddhi); 2027-02-12 good to avoid (Shukla Shashti, Sarvartha Siddhi); 3 caution to avoid |
| griha_pravesh | 13 | 2026-12-05 good, 2027-01-27 good, 2027-02-12 good, 2027-02-18 good (all four Sarvartha Siddhi lifts); 2027-03-04, 2027-05-17, 2027-07-09 acceptable; 6 caution; all to avoid |
| griha_pravesh | 0 (reason only) | 2027-01-19 and 2027-06-15 were already avoid as a Tuesday; the flag is now `avoid_tithi` because the tithi check precedes the weekday check |

No other row changed. Vivah's Shukla Dwadashi rows (for example 2027-02-18, good) are unchanged.

**Abujha.** The Abujha override (`find_candidates`) skips every exclusion, so 2027-11-10, a Shukla
Dwadashi, stays "excellent" for Griha Pravesh and Vivah. That is today's behaviour, and #1357 changes
it; it is not counted in the table above.

Cost: 0 Groq tokens (rule sets and page copy only; no prompt changed).

## Rejected

- **Also adding Dwadashi to vivah's `avoid_tithis`** -- would settle a contested row (#1022) by choosing
  Raman over Rao. The auditor ruled it stays neutral.
- **Leaving Shashti out of vivah** -- Raman's marriage chapter names it and Rao's row does not
  contradict it; nothing contests it.
- **A paksha-aware Griha Pravesh rule** -- Raman's general list names the 12th and 6th "both in the
  bright and the dark half" (L802), so no paksha split is supported.

## Known limits

Residual asymmetry, flagged and left: Vivah avoids Purnima (Raman's general list; Rao's table lists
it as good) but not the bright-half Dwadashi (Raman's marriage chapter; Rao's table lists it). Both
are the same kind of disagreement and they are graded differently; the Purnima entry predates this
change and the auditor's ruling did not reopen it.
