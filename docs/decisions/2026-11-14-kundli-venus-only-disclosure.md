# /kundli result page discloses the Venus-only grade drop, and describes the houses that qualify

- **Date:** 2026-11-14
- **PR / issue:** #777 (slice; the grades themselves stay an owner call)

## Why, measured

`compute_manglik_details` drops the severity one grade and caps the status at "mitigated" when
Mars qualifies only from Venus. Raman, *Muhurtha* (`vedic_reference.md` §1.6.3), ranks the Venus
frame the most powerful, so the drop is Bhagya's own convention. #579, #626 and #778 disclosed the
ladder on `/manglik-check`, the LLM line, `/matching` and `/learn`. `/kundli`'s result page said
nothing about the drop, and had a second defect: the paragraph under the badge was keyed on the
already-dropped grade. A chart with Mars 7th from Venus only (Mars 3rd from Lagna and Moon) was
graded moderate and told "Mars in the 1st, 4th or 12th house counts toward Manglik here", the
wrong houses (constructed chart, `tests/test_kundli_manglik_venus_only.py`).

Chosen: key the paragraph on the ladder's grade for the qualifying houses, keep the badge on the
shipped grade, and add one page-only note (`manglik_venus_only_note`, EN and HI) when
`venus_axis_only`. No prompt reads it, so the tokens cost is 0. Qualify, not regrade: chief's
standing ruling 3 allows this without the owner. Removing or regrading the ladder is still act #4.
Rejected: adding the "own weighting" sentence to the high tier, because 7th/8th most serious has
weak corroboration in the held sources and `test_the_high_tier_still_renders_and_keeps_its_sourced_claim`
pins that choice.
