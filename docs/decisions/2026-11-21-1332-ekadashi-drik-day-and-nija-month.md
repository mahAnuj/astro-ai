# A single-sunrise Ekadashi with Dwadashi skipped takes the day before, and shukla_tithi_date resolves a year-straddling month inside the year

- **Date:** 2026-11-21
- **PR / issue:** #1332

Lineage: found by `astro-auditor` while sourcing #1326
(`docs/decisions/2026-11-21-1326-late-year-festival-rows.md`), whose rows type their dates and
so never reached either defect. Related: #1330 (not part of this change).

## Why, measured

**1. The Ekadashi day.** Drik Panchang (New Delhi) prints an Ekadashi one day *earlier* than
the engine in exactly **3 of the 74** engine Ekadashis of 2026-2028 and agrees on the other 71:

| engine (sunrise scan) | Drik | Ekadashi |
| --- | --- | --- |
| 2027-01-19 | 2027-01-18 | Putrada |
| 2028-02-07 | 2028-02-06 | Jaya |
| 2028-11-13 | 2028-11-12 | Utpanna |

All three share one shape: the tithi index at the sunrises D-1, D, D+1 is t-1, t, t+2 (t = 10 or
25), D is a single-sunrise run and Dwadashi has no sunrise. The rule is therefore: such an
Ekadashi is emitted on D-1. Nothing else moves; the 2026-2028 list differs in exactly those
three dates and the total stays 149 (74 Ekadashis). The census gate re-derives the filter from
the sunrise indices alone and finds the same three, so it does not rest on the typed table.

**The rule is an UNSOURCED-IN-CORPUS Drik almanac convention.** It is 3 of 3 Drik readings, made by
`astro-auditor`; it is not read from `knowledge/`. The issue's `corpus:` line says
`knowledge/vedic_reference.md` §29.6 settles it — it does not: §29.6 is the sunrise rule for
assigning a tithi to a day, which is what the engine already did, and says nothing about a
skipped Dwadashi. No source in `knowledge/` is cited for the rule anywhere in the code. The
existing "second sunrise on vriddhi" rule is empirical in the same way (5 of 5 Drik readings),
and the old name *dashami-viddha* for it was a misnomer; the comments now say so. No
user-facing astrological sentence is added or changed — `_TARGETS`' `rule` strings are
untouched — only the computed date moves. `data/` is absent in this checkout, so no corpus
search was run.

**Not strict arunodaya.** A stricter reading (Dwadashi begins before sunrise) would also move
2027-10-25 and 2028-08-16, which Drik prints on the engine dates. Those two are kept in
`DRIK_SINGLE_SUNRISE` as negative controls, one per condition of the rule: 2027-10-25 has
indices 23, 25, 26 (fails t-1) and 2028-08-16 has 24, 25, 26 (fails t+2).

**Reach beyond 2026-2028, unverified.** Over 2000-2100 the same filter selects **97 of 2499**
Ekadashis (49 Shukla, 48 Krishna). I re-derived 97, the 49/48 split and the 2499 denominator;
I did **not** check any of them against Drik outside 2026-2028, so for those 94 dates the rule
is an extrapolation from three readings. Seven are Devshayani or Devuthani and move
`lunar_dates` with the engine: 2004-06-29, 2005-07-18, 2006-11-02, 2016-11-11, 2025-11-02,
2069-11-25 and 2078-11-16 (each now one day earlier). None falls in a year `DRIK_MUHURAT` pins
(2015, 2026-2029), so `verify_muhurat_tables.py` Gate 1 is unmoved. Widen `DRIK_SINGLE_SUNRISE`
with a Drik reading before trusting the rule further out.

**2. The month that straddles the year.** `nija_month(2027, "Margashirsha")` returns the first
overlapping month, 2026-12-09..2027-01-07, so `shukla_tithi_date(2027, "Margashirsha", 11)`
came back as the December 2026 date. `lunar_months(year)` can hold two months of one name when
the name straddles the boundary at both ends. Over 2000-2100 `shukla_tithi_date(y, month, 11)`
was wrong for **Margashirsha in 48 of 101 years** and for **Pausha in 15**; the other ten
month names are identical before and after in 101 of 101 years (diffed against the code before
this change). Now: every candidate month is picked, only dates with `d.year == year` are kept,
and the earliest is returned. Results: Margashirsha 2027 = 2027-12-09, Pausha 2027 = 2027-01-18,
Pausha 2026 = None (its Shukla Ekadashi is 2025-12-30), Pausha 2028 = 2028-01-08 of two
in-year candidates (2028-01-08 and 2028-12-27). Pausha has **0** in-year candidates in 15 of
101 years and **2** in 15. Returning None for the zero case is the module's degrade-don't-guess
rule; no current caller uses Margashirsha or Pausha, and a wrong-year date is worse than no date.

## Rejected

- **Strict arunodaya** — regresses 2027-10-25 and 2028-08-16 against Drik (above).
- **A "month that starts in the year" pick** — it would skip Pausha 2028's 2028-01-08
  Ekadashi, which belongs to the month that opens 2027-12-28, and return that month's
  successor's 2028-12-27 instead. The date's own year is what is asked for, so the filter is on
  the date.
- **None whenever two candidates land in the year** — throws away a valid in-year date for
  Pausha 2028; the earliest is kept instead.
- **A shared helper imported by both modules** — `lunar_dates._pick_day` is a documented copy
  of `lunar_observances` pass 1 and `verify_muhurat_tables.py` Gate 4(a) holds the pair in
  agreement; the same condition was added to both and `tests/test_lunar_ekadashi_drik.py`
  pins the pair together on Devuthani 2025.
- **Changing `nija_month` itself** — `verify_muhurat_tables.py` Gate 3(c) and Gate 1's Bhadli
  Navami check use it as a kshaya detector; its docstring now says it is not a year resolver.
- **Putting the three dates in `DRIK_VRIDDHI`** — `_emitted_for_run` there looks at offsets 0..+1
  and its failure text says dashami-viddha, the wrong diagnosis for a day-earlier shift.

## Gates

`scripts/verify_lunar_observances.py` (new `DRIK_SINGLE_SUNRISE` table and an independent
re-derivation in Gate C; red on the unfixed engine for exactly the three dates, green after),
`tests/test_lunar_ekadashi_drik.py`, and mutation rows in
`scripts/mutations/2026_11_21_1332_ekadashi_gauna.py`. Cost: date arithmetic only, 0 tokens.
