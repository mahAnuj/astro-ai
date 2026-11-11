# The Vivah "avoid only when BOTH partners avoid" Tara rule stays, and the finder says it is its own convention

- **Date:** 2026-11-11
- **PR / issue:** #885 (split from #879)

## Why, measured

`_couple_verdict` (`src/astro_ai/muhurat.py`) grades a Vivah day `avoid` on the Tara test only
when bride and groom are both on an avoid Tara, and `mixed` when exactly one is. The question was
whether one partner's avoid should make the couple's day avoid.

`astro-auditor` (2026-11-11, `data/` absent on the runner, 0 of 7 books, so `knowledge/*.md`
only): the rule is UNSOURCED. Raman, *Muhurtha or Electional Astrology*, L1063-1066, advises
avoiding a day ruled by the 1st, 3rd, 5th and 7th stars and names no person; his marriage chapter
(L3789-3790) says only that "the usual Tarabala, Panchaka, etc., should be looked into"
(`knowledge/vedic_reference.md` 2A-ter). Nothing in `knowledge/*.md` says how two partners' Taras
combine for a wedding day, so neither "both" nor "either" is sourced. `matching.md` L373-379 (the
Guna Milap Tara kuta, a different test) grades one-sided affliction as partial, which points away
from "either".

Counted over the 81 bride x groom Tara-position pairs (positions 3, 5, 7 avoid for the bride, 1,
3, 5, 7 for the groom, uniform and independent, not weighted by real days): `avoid` is 12 pairs
today and would be 51 under "either" (14.8% to 63.0%). 39 pairs would move `mixed` to `avoid`.

`chief` ruled **Option A** (Standing ruling 3, 2026-11-11, comment on #885): keep the verdicts and
disclose the convention. Rejected: **B** (one avoid makes the day avoid) swaps one unsourced rule
for a stronger one that more than quadruples `avoid` on a reading no held text states, on one
organic session a month of evidence; **C** (close with no change) would leave the silence standing.

The finder now says the "both" rule is its own convention, that Raman gives no combining rule, and
that a `mixed` day can still carry one partner's avoid. Pinned in
`tests/test_vivah_both_tara_disclosure.py`, with six rows in
`scripts/mutations/2026_11_11_885_both_tara.py`.

**What would overturn it:** a passage in `knowledge/*.md` (or a book in `data/`) stating how the two
partners' Taras combine for a wedding day. Not checked against the books themselves: none were
present.
