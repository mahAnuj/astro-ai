# In couple mode the muhurat finder ranks the combined verdict inside a tier, and the Top pick follows it

- **Date:** 2026-11-25
- **PR / issue:** #1344 (QA follow-up to #1341/#1342). Amends the sort key stated in
  `2026-11-21-muhurat-top-pick.md`, which said `rank_key = (tier, -score, date)`.

## Why, measured

In couple mode `top_pick` skipped a combined verdict of `avoid` and then ranked on
`(tier, -score, date)`, so `good-for-both` and `mixed` were indistinguishable. Measured on `a2ad420`,
vivah, Delhi, 365 days from 2026-11-22, six fixed couples (couple 0 is the issue's own: bride
1995-03-14 10:30, groom 1993-07-02 18:15). Couple 0 had 7 good-for-both auspicious days and a `mixed`
pick. "Better verdict, same tier" counted the eligible days of the pick's own grade with a better
verdict: 3, 0, 1, 8, 2, 0 for couples 0 to 5 (0 means nothing better existed).

| couple | pick before | pick with the new key |
|---|---|---|
| 0 | 2026-11-26 excellent/5, mixed | 2027-04-18 excellent/5, good-for-both (ties 2) |
| 1 | 2026-11-25 mixed | 2026-11-25 mixed (no good-for-both day exists in its 365 days; ties 16) |
| 2 | 2026-11-26 mixed | 2027-05-23 good-for-both (ties 0) |
| 3 | 2026-11-25 mixed | 2026-12-03 excellent-for-both (ties 3) |
| 4 | 2026-11-25 mixed | 2027-02-25 good-for-both (ties 1) |
| 5 | 2026-11-25 good-for-both | 2026-11-25 good-for-both (ties 1) |

## What was built

- `_VERDICT_ORDER = {"excellent-for-both": 0, "good-for-both": 1, "mixed": 2, "avoid": 3}` and
  `_verdict_rank(c)` in `muhurat.py`: 0 for a row with no couple, an unknown verdict counts as `mixed`.
- `rank_key = (tier, verdict_rank, -score, date)`. **Tier stays dominant**: a `good-for-both` day of a
  lower grade never outranks a `mixed` day of a higher one, so the order never contradicts the rating
  column. A non-couple search has verdict rank 0 on every row, so its order is unchanged.
- `top_pick` counts ties on `(rating, verdict rank, score)`, keeps its own couple-`avoid` filter (an
  `avoid` row in a higher tier still sorts ahead of a lower-tier row, so the key alone cannot replace
  it), and the table's first row stays the head the card names (one key, one source of truth). Inside
  a tier a couple-`avoid` row now sorts below `mixed` and `good-for-both` rows in the table.
- The card (couple mode only) says the order is verdict first and then points, calls both "this site's
  own convention", keeps the "not a classical endorsement" line, and its tie line reads "Tied on
  verdict and points". The non-couple sentence is byte-identical.

## Consequence, stated plainly

**The headline can now be months out.** Couple 0 moves from 2026-11-26 to 2027-04-18 while a
same-grade `mixed` day sits next week; couple 2 moves five months. It is the same shape as #1341's
"booster day wins on order". The card's disclosure is how the page says so. Nothing is re-weighted or
re-graded; the table still lists every date. Whether a pick that far out is acceptable product-wise
is not decided here: `chief` or `product-manager` can revisit it (for example by capping the
look-ahead the verdict can win across) with this table as the baseline.

## Sourcing (astro-auditor, 2026-11-25: CONSISTENT)

Not a classical claim. The combined verdict is this site's own both-partners rule (#885): the
classical rules fix which dates qualify, and the tradition this finder follows gives no ranking
between a date that suits both charts and one that does not clash. Tier dominance is the auditor's
ruling. `data/` was absent on the checkout this ran against, so no corpus claim is made and none is
needed. The card must never say good-for-both is classically better; the page's own text (a mixed day
can still be avoid for one partner) is unchanged.

## Rejected

- **Verdict above the tier.** A good-for-both `acceptable` day would beat a mixed `excellent` day and
  contradict the rating column.
- **Sort by verdict only inside `top_pick`.** The table's first row would stop being the head the card
  names, and the card and `find_candidates` could drift.
- **A score bonus for the verdict.** Invents a weight with no source; #1341 added none.
- **Filtering `mixed` out when a good-for-both day exists.** Hides valid dates; a mixed day is not an
  avoid (#885).
- **Disclose only, change no order.** Leaves a `mixed` headline above a day both charts favour.
- **A shared `_grade(c)` tuple for the key and the ties**, or a config knob or per-event order: one
  caller each, a four-line helper suffices.

## Not covered

Which vivah days exist is changing separately (#1357), so no test pins a real-finder couple pick date;
the tests pin synthetic rows and the property "the pick has the best verdict of its tier". Re-measure
the table above after #1357 lands.
