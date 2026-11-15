# Eclipse days are computed from Swiss Ephemeris, not typed

- **Date:** 2026-11-15
- **PR / issue:** #1018

## Why, measured

`muhurat._ECLIPSE_DATES` was typed by hand. Its 2028 row held two lunar eclipses that do not
exist (Feb 12, Aug 6: the real Jan 12 and Jul 6 shifted a month, the #141/#146 signature) and
omitted four real ones (2027-08-17, 2028-01-12, 2028-07-06, 2028-12-31); from 2029 the dict was
empty, so every eclipse silently stopped blocking. Checked against NASA GSFC Lunar and Solar
Eclipses 2021-2030.

Now `_eclipses_in_year(year)` calls `swe.sol_eclipse_when_glob` and `swe.lun_eclipse_when`,
memoised per year, so no year can be mistyped and none runs out. Inclusion set unchanged: every
global eclipse of either kind, any type, visible in India or not. The date is the IST calendar
date of the maximum; NASA lists UT, so the 2027 penumbral lunar of "Feb 20" is 2027-02-21 here
(04:42 IST). The +/-1-day blocking rule and the reason strings are unchanged.

The blocking rule itself remains UNSOURCED: `knowledge/*.md` holds no eclipse muhurta rule, and
whether a penumbral or not-visible eclipse should block is equally unsourced. Not decided here.

Cost: first call for a fresh year ~20 ms, free afterwards; no LLM call, 0 tokens.
