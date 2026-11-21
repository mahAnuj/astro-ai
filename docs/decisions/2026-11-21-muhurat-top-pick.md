# The muhurat finder ranks within a tier by soft-scoring points, and names one top pick

- **Date:** 2026-11-21
- **PR / issue:** #1341 (slice 7 of #1017; R1), also closes #1339 (the Range select shows the searched days)

## Why, measured

`find_candidates` sorted on `(tier, date)` and `score_event` threw the points away once it had a
rating, so among `excellent` days the earliest won whatever it scored. Measured 2026-11-21, Delhi,
from 2026-11-22: for vidyarambh the first excellent day by date (2026-11-25, score 5) is only
excellent because Sarvartha Siddhi lifted it; 2026-11-26 and 2026-12-03 reach 6 from the soft
factors alone and sat below it.

## What was built

- `MuhuratCandidate.score` (last field, default 0): the soft-scoring points behind the rating.
  `score_event` keeps its signature and 3-tuple return; the points arithmetic moved verbatim into
  `_soft_scoring` (reasons and flags byte-identical) and `_soft_points` returns the number.
- `_RATING_MIN_SCORE = {"excellent": 5, "good": 4, "acceptable": 3}`, best first, now the single
  table both the cut-off chain and the lifted-day floor read. The chain it replaced
  (`>=5`, `==4`, `==3`, else caution) is exactly equivalent.
- `rank_key = (tier, -score, date)` is the one sort key; `top_pick` returns the minimum of the
  eligible rows under it plus how many OTHER eligible rows tie on (rating, score). Eligible means an
  excellent/good/acceptable row (`AUSPICIOUS_RATINGS`, the finder's own definition) that is not, in
  couple mode, a combined verdict of `avoid`. Those rows stay in the list; only the headline skips
  them.
- `_finder_response` passes `top_pick`, `top_pick_ties` and `prefill_days` (the clamped
  `len(candidates)` on a result, the requested `days` on the four error re-renders). The template is
  the frontend's half.

## The booster floor

A day a booster (Amrit/Sarvartha Siddhi, Ravi Yoga) or an Abujha date lifts carries its tier's floor
as its score: `max(soft points, floor of the rating it was lifted to)`; an avoid day scores 0.
**The floor adds no weight and moves no rating**: the rating is what `score_event` already returned.
It only decides where the lifted day sorts inside its tier.

**Consequence, stated plainly.** A booster day lifted from below ties with the plain 5s of its tier
and the tie breaks on date, earliest first; a plain 6 beats it. Measured over 365 days from
2026-11-22 (Delhi): excellent days are mostly lifted ones (vivah 17 of 23, griha_pravesh 14 of 19,
vidyarambh 27 of 45, namkaran 23 of 47, business 16 of 26). Only vidyarambh (10 days at 6) and
business (2 at 6) have any excellent day above 5, so for vivah, griha_pravesh and namkaran the
"best" day is the earliest excellent one and `top_pick_ties` is 22, 18 and 46. The page must say the
pick won on order, which is why the count is returned. For business the pick over a full year is
2027-06-02 (a 6) while a 5 exists on 2026-12-03; a shorter window picks within itself.

## Rejected

- **Boosters sort first.** It would promote a day the soft factors rate lower over days they rate
  higher, on the strength of a rule this finder has no source ranking above them. It is also
  invisible in the points the page shows.
- **Keep the literal soft score as the key and only disclose it.** A booster-lifted day would then
  sort at the bottom of the tier it was lifted into (a score-3 acceptable day lifted to excellent
  would rank below every plain 5), so the list would contradict its own rating column.
- **Re-weighting anything.** No weight, cut-off, exclusion or booster rule changed.

## Sourcing (astro-auditor, 2026-11-21)

The weights (+2 tithi, +2 nakshatra, +1 weekday, +1 peak day, -1 avoid weekday) and the tier cut-offs
are **this site's own convention**. `knowledge/vedic_reference.md` §29.11 and §29.13 name the factors
a muhurta weighs; they give no weights. The `peak_day` Thursday for Vidyarambh is **contested**. So
in-grade order is a point count, never a classical ranking, and the page says so. `data/` was absent
on the checkout the audit ran against; the auditor worked from extractions.

## Not covered

R3, R4, R6, R9 and F1/F2 of #1017. One small side effect of the plan's formula, left as specified:
a caution day's score is `max(soft points, 0)`, so a Saturday caution (soft -1) scores 0 and ties
with a neutral caution. Caution days are never the pick.
