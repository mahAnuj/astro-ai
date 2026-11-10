# The numerology Bhagya score carries no compound-number term, and both numerology pages say the 0-100 is editorial

- **Date:** 2026-11-10
- **PR / issue:** #584

## Why, measured

`compute_numerology_bhagya_score` gave +2 when the whole-name compound was in
(10, 19, 23, 27, 28, 37, 46, 49) and -2 when it was in (13, 14, 16, 26, 43), and the
driver text called the first group "one of the most-fortunate name compounds in this
tradition". No held source assigns a score to a compound: `knowledge/numerology.md` §13
records that Johari's compounds are birth-day 10-31 only (37, 43, 46 and 49 are outside
that range), and §13.2 records "no numeric scoring formula in either book". The code
comment itself recorded that the lists contradicted Cheiro: 28 "not a fortunate number"
(layout 3668-3669), 31, which 49 aliases to, "not a fortunate number from a worldly or
material standpoint" (3695-3696), 13 "not unfortunate as is generally supposed"
(3501-3502), 14 "fortunate for dealings with money" (3516-3518). `data/` was absent in
this checkout, so Cheiro was **not re-read**; those quotes are taken from the old code
comment and are not independently re-verified.

**Ruling (chief, Option B, #584):** disclose that the 0-100 is Bhagya's own editorial
weighting on `/numerology` and `/numerology/compatibility`, and delete the compound tier
from the Bhagya score. The Cheiro compound meaning text still renders. The 50/30/20
weights, the +15/-25 marriage adjustments, the Personal Year branches and the 25/50/75
bands are untouched (they are `[UNSOURCED]` too, and the disclosure now says so in
effect).

**Rejected.** A, keep the tier and add only the disclosure: leaves a silently wrong
claim standing ("most-fortunate ... in this tradition" against held Cheiro quotes for 28
and 49). C, re-tier from Cheiro: invents a new +/-2 weight and would rest on four quoted
comment lines, because the full Cheiro good/bad list could not be obtained.

**This reverses** the earlier deferral in the code comment ("Values deliberately LEFT
AS-IS: retiering moves every user's headline 0-100 score ... Filed as a follow-up"). That
reasoning was about re-tiering; removing the term is a different act and the claim it
carried could not be made honest.

**Effect.** A name whose compound is in either old list moves by 2 points: +2 names
lose 2, -2 names gain 2. Measured with `birth_date=1990-01-01`, target year 2026:
Amit (compound 10) 65 -> 63, Anuj (13) 53 -> 55, Lloyd George (43) 53 -> 55, Sita Devi
(25, in neither list) 58 -> 58. A score at a band edge can change label (25/50/75). The
page text deliberately does **not** announce the 2-point change: it would read as noise to
a visitor who never saw the old number. It is recorded here and in the PR.

0 new tokens: no LLM call is on this path.
