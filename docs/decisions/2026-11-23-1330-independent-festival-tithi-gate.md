# Gate E of verify_lunar_observances.py checks the five #1326 festival rows against the ephemeris

- **Date:** 2026-11-23
- **PR / issue:** #1330 (rows added by #1326; Kalabhairav copy in #1331)

## Why, measured

The five late-year rows #1326 added (kartika-purnima, kalabhairav-jayanti, vivah-panchami,
gita-jayanti, dattatreya-jayanti) have 15 date entries. Each was shifted by one day, in
`festival_registry.py` AND `tests/festival_dates_expected.json` together, in a scratch copy
under `/tmp`, and `verify_festivals.py` plus `verify_lunar_observances.py` were run:

| row | +1 survives | -1 survives |
|---|---|---|
| kalabhairav-jayanti | 3/3 | 3/3 |
| vivah-panchami | 3/3 | 3/3 |
| gita-jayanti | 2/3 (2027, 2028) | 3/3 |
| dattatreya-jayanti | 0/3 | 2/3 (2027, 2028) |
| kartika-purnima | 0/3 | 0/3 |

**19 of 30 shifted entries shipped green** (re-measured on the base commit by the engineer,
same 19). For the issue's own +1-only metric it is 8 of 15, across three rows, not two:
gita-jayanti is a third row the issue did not name. After Gate E the same matrix is 0 of 30.

Why the existing gates miss them: Gate 1 of `verify_festivals.py` compares two hand
transcriptions with each other, so a coordinated typo agrees with itself. Its Gates 2 and 3
are arithmetic on dates with no ephemeris. `verify_lunar_observances.py` Gate B reads only
rules containing "Purnima" or "Amavasya", so an Ekadashi row (gita-jayanti) is never looked
at, and its `_allowed_offsets` deliberately lets a later-window row sit one day EARLY, which
is exactly the dattatreya -1 survivor.

## What was decided

**Gate E, in `scripts/verify_lunar_observances.py`, not in `verify_festivals.py`.** The latter
promises "no ephemeris" in Gates 2 and 3, and `verify_adhik_maas.py` says it must not import
the detector. `verify_lunar_observances.py` already imports `swisseph`, already holds the
registry cross-check, and already runs in `pr-gates` and `pre_qa_check`, so no new
`verify_*.py` and no change to `FAST_GATES`, its partition test or the workflows.

For each of the five rows the gate computes the day at the row's own window and requires the
computed day list to EQUAL the registry date: exact, no +-1 band. The four shukla rows call
`lunar_dates.shukla_tithi_date` (vivah-panchami Margashirsha/5/madhyahna, gita-jayanti
Margashirsha/11/sunrise, kartika-purnima Kartika/15/sunrise, dattatreya-jayanti
Margashirsha/15/sunrise); 12 of 12 already agreed. Input is the registry only, since Gate 1
already forces the JSON to equal it. A missing slug, a missing year, an edited window, a
`None` from the engine and two candidate days are each a FAIL naming the row. If pyswisseph is
missing the import raises and the script exits non-zero; there is no `ImportError` skip.

dattatreya-jayanti is pinned to the sunrise engine although its window is pradosh. That holds
3 of 3 years (2026 is the kshaya gap rule's begin-day, equal to the registry's pradosh day)
and is what closes the Gate B -1 survivors. A future year where pradosh legitimately takes
the day before must fail loud and be adjudicated against the almanac, not widened.

## The Kalabhairav "evening" bound is an UNSOURCED reading, not a rule

Krishna Ashtami (tithi index 22) is the only row needing new code. "Evening" is read as
**sunset to civil midnight** of the day, sampled at sunset and at 23:59 IST (two end-point
samples are exact because the shortest tithi, about 19 h, is longer than the window). This is
an unsourced-in-corpus reading of Drik Panchang: `knowledge/*.md` does not rule on it
(consistent with #1331), and it is tuned only by 3 of 3 years agreeing with the shipped dates.
pyswisseph, Lahiri, New Delhi, 1-minute scan:

- 2026: Ashtami 12-01 00:13 to 12-01 23:15. If "after sunset" ran to the next sunrise,
  2026-11-30 would qualify too (13 minutes into that night) and the registry's "not on the
  adjacent evening" would be false for 2026. With the midnight bound exactly one day qualifies.
- 2027: Ashtami 11-20 19:18 to 11-21 17:21; sunset 11-21 is 17:25. Ashtami ends **4 minutes
  before** sunset, so 11-21 does not qualify. A pyswisseph or sunset-definition change that
  flips this turns Gate E red for 2027: that is the registry's own claim sitting on a knife
  edge, not flakiness.
- 2028: Ashtami 11-09 15:41 to 11-10 14:04.

Two candidate evenings (a vriddhi Ashtami spanning two evenings, or a future year) fails and
prints both days; there is no tie-break (YAGNI, no year in 2026-2028 needs one). If chief
prefers sunset to sunrise, 2026 has two candidates and the registry comment must change, which
is a `src/` edit outside this change. No festival date, registry row, expected-table value or
astrological rule was edited here.

## Rejected

- Extending `lunar_observances` / `lunar_dates` to Panchami and Ashtami: shipped engine
  surface for a verification need; `lunar_dates` forbids Krishna without a reckoning argument.
- A gate in `verify_festivals.py`: breaks its written no-ephemeris promise.
- A pinned table of tithi-at-instant facts: a third hand transcription that would pass the
  same coordinated typo.
- Widening or per-row tightening Gate 2/3 bands: they cannot see the tithi.
- A +-1 tolerance on Kalabhairav "to be safe": that is the defect.
- A new `verify_festival_tithis.py`: touches `pre_qa_check`, its partition test and gate-count
  rows for no gain.
- A blanket sweep of all tithi_based rows: `shukla_tithi_date(..., "madhyahna")` disagrees
  with the shipped, Drik-verified date for ram-navami (2026, 2028), rishi-panchami (2027) and
  ganga-dussehra (2026, deliberately the Adhik-Jyeshtha date). Those would false-red on rows
  nothing is wrong with.

## Follow-up, not done here

23 of 37 tithi_based rows have at least one +1 that `verify_festivals` and
`verify_lunar_observances` accept (measured by the architect; includes rows
`verify_muhurat_tables` covers separately, not measured per row). Clean candidates, one
`INDEPENDENT_ROWS` line each because the window maps to a reckoning and 3 of 3 years
reproduce: ugadi-gudi-padwa, nag-panchami, navratri, govardhan-puja, devshayani-ekadashi
(sunrise); ganesh-chaturthi, anant-chaturdashi (madhyahna).

Cost: 0 LLM tokens, 0 network, 0 GCS. `verify_lunar_observances.py` about 0.8 s to about 1.3 s.
