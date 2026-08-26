#!/usr/bin/env python3
"""Verify the computed Chaturmas window and Abujha Muhurat days.

WHY THIS EXISTS
---------------
`muhurat.py` carried two hand-typed date tables that drove the live Muhurat
Finder — `_CHATURMAS_RANGES` (3 rows) and `_ABUJHA_MUHURATS` (9 rows). Every
single one of the twelve disagreed with the almanac (drikpanchang.com, New
Delhi, fetched 2026-08-07):

    Chaturmas 2026          shipped Jul 15 - Nov 11   real Jul 25 - Nov 20
    Chaturmas 2027          shipped Jul  5 - Nov  1   real Jul 14 - Nov 10
    Chaturmas 2028          shipped Jul 23 - Nov 19   real Jul  2 - Oct 28
    Akshaya Tritiya 2026    shipped 2026-04-30        real 2026-04-19
    Bhadli Navami 2026      shipped 2026-06-24        real ~2026-07-23
    Devuthani Ekadashi 2026 shipped 2026-11-19        real 2026-11-20
    Tulsi Vivah 2026        shipped 2026-11-20        real 2026-11-21
    Basant Panchami 2026    row MISSING              real 2026-01-23
    Basant Panchami 2027    shipped 2027-01-23        real 2027-02-11
    Akshaya Tritiya 2027    shipped 2027-05-19        real 2027-05-09
    Bhadli Navami 2027      shipped 2027-06-13        real ~2027-07-12
    Devuthani Ekadashi 2027 shipped 2027-10-31        real 2027-11-10
    Tulsi Vivah 2027        shipped 2027-11-01        real 2027-11-11

Two of those are worth naming individually. **Bhadli Navami was a whole lunar
month out** in both years — not a transcription slip but a wrong lunation. And
**the 2027 Basant Panchami row is the 2026 date filed under a 2027 key**, the
same mistyped-year signature as issue #141's Adhik Maas table.

Worse than any single row: the dicts ran out. `_CHATURMAS_RANGES` stopped at
2028 and fell through to a fixed `Jul 15 - Nov 15`, which is not a lunar window
in any year and structurally cannot express the ~147-day Chaturmas of a year
with an Adhik Maas inside it. `_ABUJHA_MUHURATS` stopped at 2027 and
`.get(d.year, [])` then returned `[]`, so from 2028 onward **every abujha day
silently ceased to exist** — a 2028 wedding scan showed no Akshaya Tritiya at
all, with no warning anywhere.

None of that was noticed for one reason, and it is the same reason as #141:
**there was no computation over the tables, so there was nothing for them to
disagree with.** `src/astro_ai/lunar_dates.py` is now that computation, and this
script is the gate over it.

One command, zero judgment, PASS/FAIL, exit 0 or 1. Deliberately structured like
`scripts/verify_adhik_maas.py`, `scripts/verify_festivals.py` and
`scripts/verify_lunar_observances.py`.

  Gate 1 - published dates.  Every date in `DRIK_MUHURAT` below must be
      reproduced **exactly**, with the reckoning the row calls for. Failures
      print a signed day offset, so "start +10" reads as "the window opened ten
      days late" rather than as a bare FAIL. This is the gate that catches a
      wrong row, and the gate a future "restoration" of the old numbers trips.

  Gate 2 - coverage census.  **This is the gate that catches the original
      defect.** For every year 2000-2100 the Chaturmas window must resolve and
      all five abujha days must be present. The old `.get(d.year, [])` fails
      this at 2028 and at every year after it. Row-level correctness was never
      the whole bug; running out of rows was.

  Gate 3 - structural invariants.  Source-independent of both the almanac and
      the computation's internals. Chaturmas is four lunar months, so it is
      117-119 civil days — or 146-149 when an Adhik Maas falls inside it, the
      case the old fixed fallback could not express at all and which must be
      exercised by a real census year or this gate FAILs for lack of coverage.
      Each abujha date drifts about -11 days a year against the Gregorian
      calendar and jumps ~+19 across an intervening leap month, which is proof
      owing nothing to any almanac that the right lunation was picked.

  Gate 4 - cross-module agreement.  `lunar_dates._pick_day` is a deliberate COPY
      of `lunar_observances._observances_for_year`'s vriddhi/kshaya day-pick
      (see that module's docstring for why it could not be a call). 4(a) holds
      the two in agreement: every computed Devshayani and Devuthani must appear
      as an `ekadashi-<iso>` slug from `lunar_observances` on the same day. That
      is the guard against the specific regression `lunar_observances` records
      in its own "HOW THAT WENT WRONG ONCE" section — widening the
      dashami-viddha second-day pick beyond Ekadashi, which moved three Purnimas
      and an Amavasya a day late while every count-based check stayed green.
      4(b) checks the three dates `festival_registry` independently
      hand-verified for 2026-2028.

  Gate 5 - bite test (`--self-test`).  A gate that cannot fail proves nothing.
      This corrupts `lunar_dates.shukla_tithi_date` to return result + 1 day,
      re-runs Gates 1-4, and requires that at least one goes red. Note that
      Gates 2 and 3 are deliberately shift-INVARIANT — coverage and drift do not
      change when every date moves by the same amount — so the reddening is
      expected to come from Gates 1 and 4, the two anchored to outside data.

-----------------------------------------------------------------------------
WHY THESE ARE NOT THE NUMBERS IN ISSUE #146 — read this before "fixing" them
-----------------------------------------------------------------------------
Issue #146's own body quotes `2027 = Jul 5 - Nov 1` and `2028 = Jul 23 - Nov 19`
as "the real Chaturmas windows". **They are not.** Those are `_CHATURMAS_RANGES`'
own 2027 and 2028 rows — the wrong table quoted back at itself. Drikpanchang's
New Delhi calendars give `2027 = Jul 14 - Nov 10` and `2028 = Jul 2 - Oct 28`,
and the 2028 row is 21 days out at both ends.

The issue was filed against the symptom (dates stale / missing) and reached for
the table for its numbers, which is exactly the trap a table with no computation
over it sets. A future reader who "restores" the issue's figures into
`DRIK_MUHURAT` below will trip Gate 1 immediately — which is the point of having
it. Verify against the almanac, not against the issue.

BHADLI NAVAMI IS NOT VERIFIED, AND THIS SCRIPT SAYS SO OUT LOUD
---------------------------------------------------------------
The rule (Ashadha Shukla Navami) is well attested, but **no published almanac
date was obtainable on 2026-08-07**: drikpanchang's New Delhi Hindu calendar
does not carry Bhadli / Bhadali / Kandarpa Navami in any year fetched (2015,
2026-2029) and its festival URLs 404. It is a regional Gujarati/Rajasthani
observance. No date was invented to fill the gap, so **Gate 1 carries no Bhadli
Navami row.** The only assertion made about it anywhere is Gate 2's structural
one: it falls in the same nija Ashadha as the verified Devshayani, 1-3 days
before it. If a citable source turns up, add it to `DRIK_MUHURAT` and say so.

HOW TO EXTEND
-------------
1. To add a year to `DRIK_MUHURAT`: open
   `drikpanchang.com/calendars/hindu/hinducalendar.html?year=YYYY&geoname-id=1261481`
   and read the rows off with their own lunar-month/tithi labels — Devshayani
   Ekadashi (`Ashadha, Shukla Ekadashi`), Devutthana / Prabodhini Ekadashi
   (`Kartika, Shukla Ekadashi`), Tulsi Vivah (`Kartika, Shukla Dwadashi`),
   Akshaya Tritiya (`Vaishakha, Shukla Tritiya`), Vasant Panchami (`Magha,
   Shukla Panchami`). The label matters more than the date: it is what proves
   the row is the lunation you think it is.
2. In an Adhik Maas year, check whether the `Adhika` prefix appears on the row.
   It must not — every abujha day falls in a NIJA month by construction. 2015 is
   in the table precisely because it has an Adhik Ashadha and so distinguishes
   the two Ashadha Shukla Ekadashis.
3. Run this script. **Do not tune the engine to silence a gate** — a failing
   gate means the dates are wrong, not that the gate is.

Usage:  uv run python scripts/verify_muhurat_tables.py
        uv run python scripts/verify_muhurat_tables.py --self-test
"""

from __future__ import annotations

import sys
import pathlib
import re
import time
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import adhik_maas as am  # noqa: E402
from astro_ai import festival_registry as fr  # noqa: E402
from astro_ai import lunar_dates as ld  # noqa: E402
from astro_ai import lunar_observances as lo  # noqa: E402
from astro_ai import muhurat as mu  # noqa: E402

ALMANAC = "drikpanchang.com"
ALMANAC_URL = (
    "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html"
    "?year=YYYY&geoname-id=1261481"
)
FETCHED = "2026-08-07"

# Read {FETCHED} from the New Delhi (NCT, geoname-id 1261481) Hindu year
# calendar, one page per year:
#
#   2015  …hinducalendar.html?year=2015&geoname-id=1261481
#   2026  …hinducalendar.html?year=2026&geoname-id=1261481
#   2027  …hinducalendar.html?year=2027&geoname-id=1261481
#   2028  …hinducalendar.html?year=2028&geoname-id=1261481
#   2029  …hinducalendar.html?year=2029&geoname-id=1261481
#
# Each date carries Drik's own lunar-month/tithi label, which is what proves the
# row is the intended lunation rather than a same-named neighbour:
#   devshayani  `Ashadha, Shukla Ekadashi`     devutthana  `Kartika, Shukla Ekadashi`
#   tulsi_vivah `Kartika, Shukla Dwadashi`     akshaya     `Vaishakha, Shukla Tritiya`
#   vasant      `Magha, Shukla Panchami`
#
# WHY 2015 AND 2029 ARE HERE and not just the DATA_YEARS span. Both are Adhik
# Maas years, and they test the leap-month correction in the two ways it can
# break:
#   2015  `Padmini Ekadashi / June 28, 2015 / Ashadha Adhika, Shukla Ekadashi`
#         — an adhik month with the SAME NAME as a target month. Without the
#         `kind == "nija"` filter in `lunar_dates.nija_month`, Devshayani 2015
#         resolves to 2015-06-28 (Padmini Ekadashi, an observance that exists
#         ONLY inside an Adhik Maas) instead of Drik's 2015-07-27.
#   2029  `Padmini Ekadashi / March 26, 2029 / Chaitra Adhika` — a leap month of
#         an unrelated name sitting between Vasant Panchami and Akshaya Tritiya,
#         which is what makes 2029's dates jump ~19 days later than 2028's.
#   2026  `Padmini Ekadashi / May 27, 2026 / Jyeshtha Adhika`
#   2027, 2028  no `Adhika` row anywhere in the year calendar.
#
# `chaturmas_days` is (devutthana - devshayani).days and is redundant with the
# two dates on purpose: it is the number a human can sanity-check at a glance
# against "four lunar months", and it is what makes a wrong lunation obvious.
DRIK_MUHURAT: dict[int, dict[str, str | int]] = {
    2015: {
        "devshayani": "2015-07-27",
        "devutthana": "2015-11-22",
        "tulsi_vivah": "2015-11-23",
        "akshaya_tritiya": "2015-04-21",
        "vasant_panchami": "2015-01-24",
        "chaturmas_days": 118,
    },
    2026: {
        "devshayani": "2026-07-25",
        "devutthana": "2026-11-20",
        "tulsi_vivah": "2026-11-21",
        "akshaya_tritiya": "2026-04-19",
        "vasant_panchami": "2026-01-23",
        "chaturmas_days": 118,
    },
    2027: {
        "devshayani": "2027-07-14",
        "devutthana": "2027-11-10",
        "tulsi_vivah": "2027-11-11",
        "akshaya_tritiya": "2027-05-09",
        "vasant_panchami": "2027-02-11",
        "chaturmas_days": 119,
    },
    2028: {
        "devshayani": "2028-07-02",
        "devutthana": "2028-10-28",
        "tulsi_vivah": "2028-10-29",
        "akshaya_tritiya": "2028-04-27",
        "vasant_panchami": "2028-01-31",
        "chaturmas_days": 118,
    },
    2029: {
        "devshayani": "2029-07-21",
        "devutthana": "2029-11-16",
        "tulsi_vivah": "2029-11-17",
        "akshaya_tritiya": "2029-05-16",
        "vasant_panchami": "2029-01-19",
        "chaturmas_days": 118,
    },
}

# Gate 1 rows -> the (month, tithi, reckoning) they must be reproduced from.
# The reckoning column is load-bearing: the two madhyahna rows come out a day
# wrong under sunrise reckoning in roughly one year in three. See
# `lunar_dates`' module docstring.
GATE1_RULES: tuple[tuple[str, str, int, str], ...] = (
    ("devshayani",      "Ashadha",   11, "sunrise"),
    ("devutthana",      "Kartika",   11, "sunrise"),
    ("akshaya_tritiya", "Vaishakha", 3,  "madhyahna"),
    ("vasant_panchami", "Magha",     5,  "madhyahna"),
)

# Census range. Measured: 2000-2100 costs 16.9s, or 29s with --self-test (which
# re-runs Gates 1-4 against a corrupted resolver, so it pays the census twice).
# Comfortably inside budget, so there is no reason to narrow it; `adhik_maas`
# supports 1900-2100 and `verify_adhik_maas.py` uses this same range.
#
# It was 37.4s before the `_intercalary` / `_nija` memos below, which is the
# only reason narrowing was ever considered. If this creeps back over ~40s,
# check those memos before shrinking the range — the census width is what makes
# Gate 3(a)'s adhik-inside branch reachable at all (17 of the 101 years).
CENSUS_YEARS = range(2000, 2101)

# The five names `_abujha_days` must produce every year. Four come from
# `_ABUJHA_RULES`; Tulsi Vivah is derived as Devuthani + 1 day.
EXPECTED_ABUJHA = ("Akshaya Tritiya", "Basant Panchami", "Bhadli Navami",
                     "Devuthani Ekadashi", "Tulsi Vivah")

# Chaturmas is Ashadha Shukla Ekadashi to Kartika Shukla Ekadashi: four synodic
# months = 118.1 days, so 117-119 whole days. An Adhik Maas inside the window
# inserts a fifth lunar month and makes it 146-149. There is no legal value
# between the two bands, which is what makes this a sharp check rather than a
# range: a 130-day Chaturmas is not a long year, it is a wrong lunation.
CHATURMAS_NORMAL = (117, 118, 119)
CHATURMAS_ADHIK = (146, 147, 148, 149)

# Year-over-year drift bands, same convention and same numbers as
# `verify_adhik_maas.py` Gate 2 / `tests/festival_dates_expected.json`. A lunar
# year is ~11 days shorter than a Gregorian one; a leap month adds ~30 back.
DRIFT_NORMAL = (-13, -9)
DRIFT_ADHIK = (17, 21)

# Bhadli Navami is Ashadha Shukla Navami and Devshayani is Ashadha Shukla
# Ekadashi, so Bhadli sits exactly two tithis earlier — 1 to 3 civil days,
# depending on whether either tithi is vriddhi or kshaya. This is the ONLY
# assertion this script makes about Bhadli Navami; see the module docstring.
BHADLI_LEAD_DAYS = (1, 3)


def _parse(iso: str) -> date:
    return date.fromisoformat(iso)


def _anniversary(d: date, year: int) -> date:
    """`d` moved to `year`, same month and day. 29 Feb clamps to 28 Feb."""
    try:
        return date(year, d.month, d.day)
    except ValueError:
        return date(year, 2, 28)


def _resolve(year: int, month: str, tithi: int, reckoning: str) -> date | None:
    """`shukla_tithi_date` looked up on the MODULE, not bound at import.

    Gate 5 monkeypatches `lunar_dates.shukla_tithi_date`, and `muhurat.py`
    reaches it the same way (`lunar_dates.shukla_tithi_date(...)`). Binding the
    function here with `from ... import` would make this script immune to the
    corruption it is supposed to detect — i.e. would make the bite test lie.
    """
    return ld.shukla_tithi_date(year, month, tithi, reckoning)


def _clear_caches() -> None:
    """Drop every year-granular cache between runs.

    `_chaturmas_window` and `_abujha_days` are `lru_cache`d for the live 365-day
    scan; Gate 5 must not be served a pre-corruption answer out of them.
    """
    mu._chaturmas_window.cache_clear()
    mu._abujha_days.cache_clear()
    ld.shukla_tithi_date.cache_clear()
    _nija.cache_clear()


# `adhik_maas.lunar_months` is lru_cached at maxsize=8, which is right for the
# live path (a 365-day scan touches at most two years) but thrashes here: the
# gates walk 101 years and then walk them again per observance, so an 8-entry
# cache turns every lookup back into a full year of new-moon enumeration and
# costs ~27s. Memoising over the whole census on THIS side keeps the census at
# 2000-2100 without changing a cache size that is tuned for production.
@lru_cache(maxsize=None)
def _intercalary(year: int) -> tuple[am.IntercalaryMonth, ...]:
    return am.intercalary_months(year)


@lru_cache(maxsize=None)
def _nija(year: int, name: str) -> am.LunarMonth | None:
    return ld.nija_month(year, name)


def _adhik_windows(year: int) -> list[am.IntercalaryMonth]:
    return [m for m in _intercalary(year) if m.kind == "adhik"]


def _adhik_overlapping(start: date, end: date) -> list[am.IntercalaryMonth]:
    """Adhik months intersecting the half-open civil interval [start, end)."""
    out: list[am.IntercalaryMonth] = []
    for year in range(start.year, end.year + 1):
        for m in _adhik_windows(year):
            if m.start < end and m.end >= start and m not in out:
                out.append(m)
    return out


def _adhik_starting_in(d0: date, d1: date) -> list[am.IntercalaryMonth]:
    """Adhik months the detector opens in (d0, d1]."""
    out: list[am.IntercalaryMonth] = []
    for year in range(d0.year, d1.year + 1):
        for m in _adhik_windows(year):
            if d0 < m.start <= d1 and m not in out:
                out.append(m)
    return out


# --------------------------------------------------------------------------
# Gate 1 - published dates
# --------------------------------------------------------------------------

def gate_1_published_dates() -> list[str]:
    failures: list[str] = []
    checked = 0

    for year in sorted(DRIK_MUHURAT):
        row = DRIK_MUHURAT[year]

        for key, month, tithi, reckoning in GATE1_RULES:
            want = _parse(str(row[key]))
            try:
                got = _resolve(year, month, tithi, reckoning)
            except Exception as exc:
                failures.append(
                    f"{year} {key}: shukla_tithi_date({month}, {tithi}, {reckoning!r}) "
                    f"raised {type(exc).__name__}: {exc} — this date is asserted by the "
                    f"{ALMANAC} table, so it cannot be allowed to fail"
                )
                print(f"  FAIL {year} {key:<16} raised {type(exc).__name__}: {exc}")
                continue

            if got is None:
                failures.append(
                    f"{year} {key}: shukla_tithi_date returned None, but {ALMANAC} gives "
                    f"{want}. None means the nija {month} was not found for this year — "
                    "check whether lunar_months() has lost a month or mislabelled one."
                )
                print(f"  FAIL {year} {key:<16} drik {want}  got None")
                continue

            off = (got - want).days
            checked += 1
            print(f"  {'ok  ' if off == 0 else 'FAIL'} {year} {key:<16} "
                  f"drik {want}  got {got}  {off:+d}d  "
                  f"({month} Shukla {tithi}, {reckoning})")
            if off:
                failures.append(
                    f"{year} {key}: computed {got}, {ALMANAC} gives {want} ({off:+d} "
                    f"days). Rule is nija {month} Shukla {tithi}, {reckoning} reckoning. "
                    "An offset of exactly +/-1 usually means the wrong reckoning "
                    "(sunrise vs madhyahna) or a vriddhi/kshaya day-pick; an offset near "
                    "+/-30 means the wrong lunation, i.e. an adhik month was taken for a "
                    "nija one. Verify against the almanac before changing the engine."
                )

        # The rows above resolve `shukla_tithi_date` directly from GATE1_RULES,
        # which restates (month, tithi, reckoning) INDEPENDENTLY of
        # `muhurat._ABUJHA_RULES` — that independence is deliberate, but on its
        # own it leaves a hole: a wrong month in `_ABUJHA_RULES` would sail past
        # Gate 1 and only be caught by Gate 4(b)'s three DATA_YEARS. So the same
        # published dates are ALSO read back out of `_abujha_days`, which is the
        # dict the live `_abujha_for` actually serves. Tulsi Vivah can only be
        # checked this way in any case: it is not a rule but a derivation
        # (Devuthani + 1 day) that exists nowhere else.
        try:
            days = mu._abujha_days(year)
        except Exception as exc:
            failures.append(
                f"{year}: _abujha_days raised {type(exc).__name__}: {exc}"
            )
            print(f"  FAIL {year} _abujha_days     raised {type(exc).__name__}: {exc}")
            days = {}
        by_name: dict[str, date] = {}
        for d, entries in days.items():
            for name, _types in entries:
                by_name.setdefault(name, d)

        for key, name, note in (
            ("akshaya_tritiya", "Akshaya Tritiya",    "_ABUJHA_RULES"),
            ("vasant_panchami", "Basant Panchami",    "_ABUJHA_RULES"),
            ("devutthana",      "Devuthani Ekadashi", "_ABUJHA_RULES"),
            ("tulsi_vivah",     "Tulsi Vivah",        "derived: Devuthani + 1 day"),
        ):
            want = _parse(str(row[key]))
            got = by_name.get(name)
            label = f"abujha:{key}"
            if got is None:
                failures.append(
                    f"{year} {label}: _abujha_days produced no {name!r} at all, but "
                    f"{ALMANAC} gives {want}. The live _abujha_for reads this dict, so "
                    "an absent day is a day that does not exist for users."
                )
                print(f"  FAIL {year} {label:<16} drik {want}  got (absent)")
                continue
            off = (got - want).days
            checked += 1
            print(f"  {'ok  ' if off == 0 else 'FAIL'} {year} {label:<16} "
                  f"drik {want}  got {got}  {off:+d}d  ({note})")
            if off:
                failures.append(
                    f"{year} {label}: _abujha_days places {name!r} on {got}, {ALMANAC} "
                    f"gives {want} ({off:+d} days)"
                    + (
                        ". Tulsi Vivah is derived as Devuthani Ekadashi + 1 day, so "
                        "check Devuthani's own row above first."
                        if name == "Tulsi Vivah" else
                        ". Note the plain row for this date above may still be green: "
                        "that one resolves GATE1_RULES, this one goes through "
                        "muhurat._ABUJHA_RULES. A disagreement between the two means the "
                        "month/tithi/reckoning columns in _ABUJHA_RULES are wrong, which "
                        "is what the live finder actually uses. An offset near +/-30 is "
                        "a wrong month name."
                    )
                )

        # The window must be exactly the two published Ekadashis, no fudge.
        want_window = (_parse(str(row["devshayani"])), _parse(str(row["devutthana"])))
        got_window = mu._chaturmas_window(year)
        checked += 1
        if got_window is None:
            failures.append(
                f"{year} chaturmas: _chaturmas_window returned None, but both boundary "
                f"Ekadashis are published ({want_window[0]} .. {want_window[1]})"
            )
            print(f"  FAIL {year} chaturmas        drik {want_window[0]}..{want_window[1]}"
                  f"  got None")
        else:
            d_start = (got_window[0] - want_window[0]).days
            d_end = (got_window[1] - want_window[1]).days
            span = (got_window[1] - got_window[0]).days
            want_span = int(row["chaturmas_days"])
            ok = d_start == 0 and d_end == 0 and span == want_span
            print(f"  {'ok  ' if ok else 'FAIL'} {year} {'chaturmas':<16} "
                  f"drik {want_window[0]}..{want_window[1]} ({want_span}d)  "
                  f"got {got_window[0]}..{got_window[1]} ({span}d)  "
                  f"start {d_start:+d}, end {d_end:+d}")
            if d_start or d_end:
                failures.append(
                    f"{year} chaturmas: computed {got_window[0]}..{got_window[1]}, "
                    f"{ALMANAC} gives {want_window[0]}..{want_window[1]} — "
                    f"start {d_start:+d}, end {d_end:+d}. NOTE: issue #146's body quotes "
                    "the OLD WRONG table's 2027/2028 windows as if they were almanac "
                    "values. Do not restore them here; see the module docstring."
                )
            elif span != want_span:
                failures.append(
                    f"{year} chaturmas: both edges match {ALMANAC} but the span is "
                    f"{span} days against the recorded {want_span} — arithmetic is "
                    "broken, not the dates"
                )

    print(f"  {checked} published date(s)/window(s) checked against {ALMANAC} "
          f"({min(DRIK_MUHURAT)}, {min(y for y in DRIK_MUHURAT if y > 2015)}-"
          f"{max(DRIK_MUHURAT)}), fetched {FETCHED}")
    print("  NOTE: no Bhadli Navami row exists here — no published date was obtainable; "
          "see Gate 2")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - coverage census
# --------------------------------------------------------------------------

def gate_2_coverage() -> tuple[list[str], dict[int, dict[str, date]]]:
    """Every census year must produce a Chaturmas window and all five abujha days.

    THIS IS THE GATE THAT CATCHES THE ORIGINAL DEFECT. `_ABUJHA_MUHURATS` had
    rows for 2026-2027 and nothing after, so `.get(d.year, [])` returned an empty
    list from 2028 onward and every abujha day vanished with no error. Likewise
    `_CHATURMAS_RANGES` ran out at 2028. Correct rows were never the whole
    problem; a finite table was.

    Returns the per-year resolved dates so Gates 3 and 4 do not re-derive them.
    """
    failures: list[str] = []
    resolved: dict[int, dict[str, date]] = {}
    missing_window: list[int] = []
    missing_names: dict[str, list[int]] = {}
    bhadli_checked = 0

    for year in CENSUS_YEARS:
        row: dict[str, date] = {}

        try:
            window = mu._chaturmas_window(year)
        except Exception as exc:
            failures.append(
                f"{year}: _chaturmas_window raised {type(exc).__name__}: {exc} — the "
                "window must resolve for every year in the census, and there is no "
                "tolerated exception here"
            )
            window = None
        if window is None:
            missing_window.append(year)
        else:
            row["devshayani"], row["devutthana"] = window

        try:
            days = mu._abujha_days(year)
        except Exception as exc:
            failures.append(
                f"{year}: _abujha_days raised {type(exc).__name__}: {exc}"
            )
            days = {}

        by_name: dict[str, date] = {}
        for d, entries in days.items():
            for name, _types in entries:
                by_name.setdefault(name, d)
        for name in EXPECTED_ABUJHA:
            if name in by_name:
                row[name] = by_name[name]
            else:
                missing_names.setdefault(name, []).append(year)

        resolved[year] = row

        # The only assertion made anywhere about Bhadli Navami.
        bhadli = by_name.get("Bhadli Navami")
        devshayani = row.get("devshayani")
        if bhadli is not None and devshayani is not None:
            lead = (devshayani - bhadli).days
            lo_lead, hi_lead = BHADLI_LEAD_DAYS
            bhadli_checked += 1
            if not (lo_lead <= lead <= hi_lead):
                failures.append(
                    f"{year} Bhadli Navami {bhadli} is {lead} days before Devshayani "
                    f"{devshayani}, expected {lo_lead}-{hi_lead}. Both are Ashadha Shukla "
                    "(Navami and Ekadashi), two tithis apart, so a larger gap means they "
                    "are not in the same lunation."
                )
            month = _nija(year, "Ashadha")
            if month is None:
                failures.append(
                    f"{year}: Bhadli Navami resolved to {bhadli} but nija_month('Ashadha') "
                    "is None — inconsistent"
                )
            elif not (month.start <= bhadli <= month.end):
                failures.append(
                    f"{year} Bhadli Navami {bhadli} falls outside nija Ashadha "
                    f"{month.start}..{month.end} — this is the shape of the original bug, "
                    "where the shipped 2026 date (2026-06-24) sat a whole lunar month "
                    "before the real one"
                )

    n = len(CENSUS_YEARS)
    print(f"  census {CENSUS_YEARS.start}-{CENSUS_YEARS.stop - 1} ({n} years)")
    print(f"  chaturmas window resolved : {n - len(missing_window)}/{n}")
    for name in EXPECTED_ABUJHA:
        gaps = missing_names.get(name, [])
        print(f"  {name:<19} resolved : {n - len(gaps)}/{n}")

    if missing_window:
        failures.append(
            f"_chaturmas_window returned None for {len(missing_window)} census year(s): "
            + ", ".join(str(y) for y in missing_window[:12])
            + (" …" if len(missing_window) > 12 else "")
            + ". Every year must resolve; a year with no window is a year in which "
            "_in_chaturmas silently answers False for all 365 days."
        )
    for name, gaps in sorted(missing_names.items()):
        failures.append(
            f"{name} missing in {len(gaps)} census year(s): "
            + ", ".join(str(y) for y in gaps[:12])
            + (" …" if len(gaps) > 12 else "")
            + ". This is EXACTLY the original defect: the old table had no rows past "
            "2027, so _abujha_for returned '' for every date from 2028 on and the day "
            "simply did not exist for users."
        )

    print(f"  {bhadli_checked} Bhadli Navami year(s) checked STRUCTURALLY ONLY "
          f"(same nija Ashadha as Devshayani, {BHADLI_LEAD_DAYS[0]}-"
          f"{BHADLI_LEAD_DAYS[1]} days earlier)")
    print("  ^ that is the ONLY assertion this script makes about Bhadli Navami: no "
          f"published date was obtainable from {ALMANAC} on {FETCHED} for any year, so "
          "it is NOT checked against an almanac anywhere")
    return failures, resolved


# --------------------------------------------------------------------------
# Gate 3 - structural invariants
# --------------------------------------------------------------------------

def gate_3_structure(resolved: dict[int, dict[str, date]]) -> list[str]:
    failures: list[str] = []

    # --- (a) Chaturmas length, split by whether a leap month falls inside it.
    normal_checked = adhik_checked = 0
    for year in CENSUS_YEARS:
        row = resolved.get(year, {})
        start, end = row.get("devshayani"), row.get("devutthana")
        if start is None or end is None:
            continue  # already a Gate 2 failure
        span = (end - start).days
        inside = _adhik_overlapping(start, end)
        if inside:
            band, adhik_checked = CHATURMAS_ADHIK, adhik_checked + 1
        else:
            band, normal_checked = CHATURMAS_NORMAL, normal_checked + 1
        if span not in band:
            failures.append(
                f"{year} chaturmas {start}..{end} is {span} days; expected one of "
                f"{band} given "
                + (", ".join(f"Adhik {m.name} {m.start}..{m.end}" for m in inside)
                     if inside else "no adhik month inside the window")
                + ". Chaturmas is four lunar months (118.1 days) or five when a leap "
                "month falls inside (147.6). A value between the bands means the wrong "
                "lunation was picked at one end."
            )
        if inside:
            print(f"  adhik-inside {year}  {start}..{end}  {span}d  "
                  + ", ".join(f"Adhik {m.name} {m.start}..{m.end}" for m in inside))

    print(f"  chaturmas length: {normal_checked} normal year(s) in {CHATURMAS_NORMAL}, "
          f"{adhik_checked} adhik-inside year(s) in {CHATURMAS_ADHIK}")
    if adhik_checked == 0:
        failures.append(
            "NO census year has an adhik month inside its Chaturmas window, so the "
            f"{CHATURMAS_ADHIK} band was never exercised and this gate proved nothing "
            "about the case that matters most. The old fixed Jul 15 - Nov 15 fallback "
            "structurally could not express a ~147-day Chaturmas at all, which is why "
            "this branch has to be covered. Widen CENSUS_YEARS until it is — 2031's "
            "Adhik Bhadrapada is one such year."
        )

    # --- (b) Year-over-year drift of each abujha date.
    drift_checked = drift_adhik = 0
    for name in EXPECTED_ABUJHA:
        series = [(y, resolved[y][name]) for y in CENSUS_YEARS
                    if name in resolved.get(y, {})]
        for (y0, d0), (y1, d1) in zip(series, series[1:]):
            if y1 != y0 + 1:
                continue  # a gap is a Gate 2 failure, not a drift failure
            drift = (d1 - _anniversary(d0, y1)).days
            intervening = _adhik_starting_in(d0, d1)
            if intervening:
                band, drift_adhik = DRIFT_ADHIK, drift_adhik + 1
            else:
                band = DRIFT_NORMAL
            drift_checked += 1
            if not (band[0] <= drift <= band[1]):
                says = (", ".join(f"Adhik {m.name} {m.start}..{m.end}"
                                    for m in intervening)
                        if intervening else "no leap month")
                failures.append(
                    f"[{name}] {y0}->{y1}: {d0} -> {d1} is {drift:+d} days, outside the "
                    f"{'adhik' if intervening else 'normal'} band {band[0]}..{band[1]}; "
                    f"detector says {says}. A lunar date drifts ~-11 days a Gregorian "
                    "year and jumps ~+19 across a leap month. This is pure arithmetic on "
                    "civil dates and owes nothing to any almanac, so a failure here means "
                    "the wrong lunation was picked in one of the two years."
                )

    print(f"  drift: {drift_checked} year-over-year step(s) across "
          f"{len(EXPECTED_ABUJHA)} observance(s), {drift_adhik} of them across an "
          f"intervening adhik month (band {DRIFT_ADHIK})")

    # --- (c) Month resolution vs kshaya months, proved rather than allowlisted.
    target_months = sorted({rule[1] for rule in mu._ABUJHA_RULES} | {"Ashadha", "Kartika"})
    unresolved: set[tuple[int, str]] = set()
    kshaya_expected: set[tuple[int, str]] = set()
    for year in CENSUS_YEARS:
        for m in _intercalary(year):
            if m.kind == "kshaya" and m.name in target_months:
                kshaya_expected.add((year, m.name))
        for month in target_months:
            if _nija(year, month) is None:
                unresolved.add((year, month))

    print(f"  month resolution: {len(target_months) * len(CENSUS_YEARS)} "
          f"(year, month) pair(s) over {target_months}")
    print(f"    unresolved      : {len(unresolved)}")
    print(f"    kshaya expected : {len(kshaya_expected)}")
    if unresolved != kshaya_expected:
        only_unresolved = sorted(unresolved - kshaya_expected)
        only_kshaya = sorted(kshaya_expected - unresolved)
        failures.append(
            "the set of (year, month) pairs that fail to resolve is not exactly the set "
            "that intercalary_months() reports as kshaya. "
            + (f"Unresolved with no kshaya to explain it: {only_unresolved[:12]}. "
                 if only_unresolved else "")
            + (f"Kshaya month that nevertheless resolved: {only_kshaya[:12]}. "
                 if only_kshaya else "")
            + "A kshaya month is the ONLY legitimate reason for a target month to be "
            "absent from a year, and stating that as an equality rather than an "
            "allowlist of years is what stops a genuine gap being papered over."
        )
    return failures


# --------------------------------------------------------------------------
# Gate 4 - cross-module agreement
# --------------------------------------------------------------------------

def gate_4_cross_module(resolved: dict[int, dict[str, date]]) -> list[str]:
    failures: list[str] = []

    # --- (a) vs lunar_observances. The day-pick in lunar_dates._pick_day is a
    # COPY of lunar_observances'; this is what stops the copy drifting. It is
    # also the specific guard against widening _VIDDHA_TITHIS beyond Ekadashi —
    # see lunar_observances' "HOW THAT WENT WRONG ONCE".
    ek_checked = 0
    for year in CENSUS_YEARS:
        row = resolved.get(year, {})
        wanted = [(k, row[k]) for k in ("devshayani", "devutthana") if k in row]
        if not wanted:
            continue
        rows = lo.observances_between(date(year, 1, 1), date(year, 12, 31))
        ekadashi_days = {d for d, o in rows if o.slug == f"ekadashi-{d.isoformat()}"}
        for key, d in wanted:
            ek_checked += 1
            if d in ekadashi_days:
                continue
            near = sorted(ekadashi_days, key=lambda c: abs((c - d).days))[:1]
            off = f"{(near[0] - d).days:+d}d away at {near[0]}" if near else "none in year"
            failures.append(
                f"{year} {key} = {d} is not an Ekadashi according to "
                f"lunar_observances (nearest: {off}). lunar_dates._pick_day is a copy of "
                "lunar_observances' vriddhi/kshaya day-pick and the two must agree. A "
                "systematic one-day drift here is the signature of the regression "
                "lunar_observances records in its own docstring: widening the "
                "dashami-viddha second-day pick past Ekadashi moved three Purnimas and "
                "an Amavasya a day late while every count-based check stayed green."
            )
    print(f"  (a) {ek_checked} computed Devshayani/Devuthani cross-checked against "
          f"lunar_observances Ekadashi slugs over the full census")

    # --- (b) vs festival_registry's independently hand-verified 2026-2028 rows.
    registry_map = {
        "akshaya-tritiya": "Akshaya Tritiya",
        "vasant-panchami": "Basant Panchami",
        "tulsi-vivah": "Tulsi Vivah",
    }
    reg_checked = 0
    for slug, name in registry_map.items():
        fest = fr.get_festival(slug)
        if fest is None:
            failures.append(
                f"festival_registry has no festival with slug {slug!r} — it was renamed "
                "or removed, and this cross-check has silently stopped checking anything"
            )
            continue
        for year in fr.DATA_YEARS:
            want_iso = fest.dates.get(year)
            if want_iso is None:
                failures.append(
                    f"festival_registry {slug} has no date for {year}, which is in "
                    "DATA_YEARS"
                )
                continue
            want = _parse(want_iso)
            got = resolved.get(year, {}).get(name)
            reg_checked += 1
            off = (got - want).days if got else None
            ok = got == want
            print(f"  {'ok  ' if ok else 'FAIL'} (b) {year} {slug:<16} registry {want}  "
                  f"computed {got}  "
                  + (f"{off:+d}d" if off is not None else "(absent)"))
            if not ok:
                failures.append(
                    f"{year} {slug}: festival_registry has {want}, this computes {got}. "
                    "The registry rows are a SEPARATE hand verification against the same "
                    "almanac, so a disagreement is a real finding — report it and re-read "
                    "the almanac. Do not edit either side to match the other."
                )
    print(f"  (b) {reg_checked} row(s) cross-checked against festival_registry "
          f"DATA_YEARS {fr.DATA_YEARS}")

    # --- (c) the live predicate, at the boundary that matters to a user: the
    # restriction must lift ON Devuthani, not the day after.
    edge_checked = 0
    for year in CENSUS_YEARS:
        d = resolved.get(year, {}).get("devutthana")
        if d is None:
            continue
        edge_checked += 1
        before = d - timedelta(days=1)
        if not mu._in_chaturmas(before):
            failures.append(
                f"{year}: _in_chaturmas({before}) is False, but that is the day before "
                f"Devuthani Ekadashi {d} and so the last restricted day of Chaturmas"
            )
        if mu._in_chaturmas(d):
            failures.append(
                f"{year}: _in_chaturmas({d}) is True on Devuthani Ekadashi itself. "
                "Devuthani is when Vishnu wakes and the restriction LIFTS — it is also "
                "an abujha day, so marking it restricted contradicts the same module's "
                "own override. The window is end-exclusive on purpose."
            )
    print(f"  (c) {edge_checked} Devuthani boundary/boundaries checked through the live "
          "_in_chaturmas predicate (end-exclusive)")
    return failures


# --------------------------------------------------------------------------

GATE_TITLES = (
    f"Gate 1 - published dates ({ALMANAC}, New Delhi)",
    "Gate 2 - coverage census (the gate that catches the original defect)",
    "Gate 3 - structural invariants (arithmetic, source-independent)",
    "Gate 4 - cross-module agreement (lunar_observances, festival_registry)",
    "Gate 6 - combustion orbs match Raman Muhurtha p.197, footnote included",
)


def gate_6_combustion_orbs() -> list[str]:
    """The combustion orbs must match the page they cite, footnote included.

    Nothing guarded this table until 2026-08-23, which is how it carried
    invented retrograde values (Mercury 10, Venus 8) for weeks under a "per
    BPHS" attribution to a book that is not in `data/` and never has been.
    The real source states them in a FOOTNOTE rather than in the table body,
    and the footnote is exactly what a hurried transcription drops.

    So this checks three things a wrong value has to survive all of:
      1. code == knowledge/grahas.md §12, orb by orb
      2. the cited source file still contains the table AND the footnote
      3. the retrograde orbs are exactly one degree less than direct, for
         Mercury and Venus only — which is what "one degree less" means and
         what an invented number will not accidentally satisfy
    """
    failures: list[str] = []
    root = pathlib.Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    from astro_ai.chart import COMBUSTION_ORBS

    # 1. Code vs the knowledge file.
    full = (root / "src/astro_ai/knowledge/grahas.md").read_text()
    # Scope to the combustion table. grahas.md has many tables keyed by planet
    # name, and an unscoped row regex matched 44 of them.
    # Anchor on the TABLE HEADER, not on prose around it. This gate went red
    # when 701ff75 restructured §12 and dropped the sentence
    # "**Classical combustion orbs:**" it used to key on — the orb table itself
    # was untouched and still correct, but the gate reported "nothing to read".
    # A gate that breaks when a heading is reworded is a gate people learn to
    # ignore. The column header IS the table, so it cannot drift away from the
    # data while the data still exists.
    marker = "| Planet | Combust when within |"
    if marker not in full:
        return [f"grahas.md: {marker!r} not found — this gate has nothing to read. "
                "The combustion orb table moved or changed shape; re-point this "
                "anchor at it rather than deleting the check."]
    doc = full[full.index(marker):]
    doc = doc[:doc.index("\n\n", doc.index("|"))] if "\n\n" in doc[doc.index("|"):] else doc
    # Capture the whole cell and parse it, rather than pattern-matching the
    # retrograde clause inline: an optional group followed by a greedy tail
    # silently matches EMPTY and swallows the value it was meant to capture,
    # which is how the first version of this gate reported a false failure.
    rows = re.findall(r"\|\s*(Moon|Mars|Mercury|Jupiter|Venus|Saturn)\s*\|([^|]*)\|", doc)
    if len(rows) != 6:
        failures.append(f"grahas.md §12: parsed {len(rows)} orb rows, expected 6 — "
                        "table shape changed, this gate is not reading it")
    for planet, cell in rows:
        nums = re.findall(r"(\d+(?:\.\d+)?)\s*°", cell)
        if not nums:
            failures.append(f"grahas.md §12: no orb found in the {planet} row ({cell.strip()!r})")
            continue
        retro = nums[1] if "retrograde" in cell and len(nums) > 1 else nums[0]
        want = (float(nums[0]), float(retro))
        got = COMBUSTION_ORBS.get(planet)
        if got != want:
            failures.append(f"{planet}: code {got}, grahas.md {want}")

    # 2. The cited source must still say what we claim it says.
    src = root / "data/matching/raman-muhurtha-1948-electional-astrology_djvu.txt"
    if not src.exists():
        print(f"  SKIP source check: {src.name} not present (data/ is gitignored)")
    else:
        text = src.read_text(errors="ignore")
        if "Planets, Combustion of" not in text:
            failures.append("Raman Muhurtha: combustion table heading not found — "
                            "the citation in grahas.md §12 points at nothing")
        # OCR renders "are" as "ere"; match either rather than pinning the typo.
        if not re.search(r"When Mercury and Venus\s+(?:are|ere)\s+retrograde the angle "
                         r"will be\s+one degree less", text):
            failures.append("Raman Muhurtha: the 'one degree less' footnote is gone — "
                            "the retrograde orbs below rest entirely on it")

    # 3. The footnote's arithmetic, stated as a rule.
    for planet in ("Mercury", "Venus"):
        direct, retro = COMBUSTION_ORBS[planet]
        if abs((direct - retro) - 1.0) > 1e-9:
            failures.append(f"{planet}: retrograde orb is {direct - retro:g}° less than "
                            f"direct; the source says ONE degree less (expect {direct - 1:g})")
    for planet in ("Moon", "Mars", "Jupiter", "Saturn"):
        direct, retro = COMBUSTION_ORBS[planet]
        if direct != retro:
            failures.append(f"{planet}: has a retrograde variant ({retro}) but the "
                            "footnote names only Mercury and Venus")

    print(f"  checked {len(COMBUSTION_ORBS)} planets against grahas.md §12 and "
          "Raman Muhurtha p.197")
    return failures


def run_gates(verbose: bool = True) -> list[tuple[str, int]]:
    """Run Gates 1-4 and return (title, failure count) per gate."""
    _clear_caches()
    results: list[tuple[str, int]] = []
    state: dict[str, object] = {}

    def _g1() -> list[str]:
        return gate_1_published_dates()

    def _g2() -> list[str]:
        failures, resolved = gate_2_coverage()
        state["resolved"] = resolved
        return failures

    def _g3() -> list[str]:
        return gate_3_structure(state.get("resolved") or {})  # type: ignore[arg-type]

    def _g4() -> list[str]:
        return gate_4_cross_module(state.get("resolved") or {})  # type: ignore[arg-type]

    def _g6() -> list[str]:
        return gate_6_combustion_orbs()

    for title, run in zip(GATE_TITLES, (_g1, _g2, _g3, _g4, _g6)):
        if verbose:
            print(title)
        failures = run()
        if verbose:
            for line in failures:
                print(f"  FAIL: {line}")
            print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
            print()
        results.append((title, len(failures)))
    return results


def gate_5_self_test() -> int:
    """Bite test: corrupt the resolver by one day and require the gates to notice.

    A gate that cannot fail proves nothing. This shifts every date
    `lunar_dates.shukla_tithi_date` returns forward by one day and re-runs Gates
    1-4; if they all still pass, this script is decoration and exits 1.

    Gates 2 and 3 are expected to survive, and that is by design rather than a
    weakness: coverage does not change when a date moves, and a uniform +1 shift
    leaves both the Chaturmas span and every year-over-year drift exactly as they
    were. The detection has to come from Gates 1 and 4 — the two anchored to data
    computed elsewhere (the almanac table, `lunar_observances`,
    `festival_registry`). That is precisely why a purely structural gate set is
    not enough, and why Gate 1 exists.
    """
    print("Gate 5 - bite test (--self-test)")
    print("  corrupting lunar_dates.shukla_tithi_date to return result + 1 day, "
          "then re-running Gates 1-4 with every cache cleared")
    print()

    original = ld.shukla_tithi_date

    def corrupted(year: int, month: str, tithi: int, reckoning: str = "sunrise"):
        d = original(year, month, tithi, reckoning)
        return None if d is None else d + timedelta(days=1)

    corrupted.cache_clear = original.cache_clear  # type: ignore[attr-defined]
    ld.shukla_tithi_date = corrupted  # type: ignore[assignment]
    try:
        results = run_gates(verbose=False)
    finally:
        ld.shukla_tithi_date = original  # type: ignore[assignment]
        _clear_caches()

    reddened = [t for t, n in results if n]
    total = sum(n for _t, n in results)
    for title, n in results:
        print(f"  {'RED  ' if n else 'green'}  {title}"
              + (f"  ({n} failure(s))" if n else ""))
    print()
    print(f"  {len(reddened)} of {len(results)} gate(s) reddened, "
          f"{total} failure(s) total")

    if total == 0:
        print()
        print("  FAIL: a resolver corrupted by a full day passed every gate. This "
              "script detects nothing and must not be trusted as evidence.")
        return 1
    print("  -> PASS (the gates bite)")
    return 0


def main(argv: list[str]) -> int:
    self_test = "--self-test" in argv[1:]

    print("Muhurat table verification (Chaturmas + Abujha days)")
    print("  computation : src/astro_ai/lunar_dates.py, src/astro_ai/muhurat.py")
    print("  months      : src/astro_ai/adhik_maas.py (amanta, nija/adhik/kshaya)")
    print("  sunrise     : src/astro_ai/lunar_observances.py (same New Delhi / IST "
          "convention)")
    print(f"  almanac     : {ALMANAC}, New Delhi (NCT, geoname-id 1261481)")
    print(f"                {ALMANAC_URL}")
    print(f"  fetched     : {FETCHED}  "
          f"(years {', '.join(str(y) for y in sorted(DRIK_MUHURAT))})")
    print(f"  census      : {CENSUS_YEARS.start}-{CENSUS_YEARS.stop - 1} "
          f"(adhik_maas supports {am.SUPPORTED_YEARS.start}-"
          f"{am.SUPPORTED_YEARS.stop - 1})")
    print()

    t0 = time.time()
    results = run_gates(verbose=True)
    elapsed = time.time() - t0

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print(f"  census wall time: {elapsed:.1f}s")
    print()

    total = sum(n for _t, n in results)
    if total:
        print(f"FAIL — {total} problem(s). Do not tune the engine to silence a gate. "
              "Check the date against the almanac first — and note that issue #146's "
              "own body quotes the OLD WRONG Chaturmas windows as if they were "
              "almanac values.")
        return 1

    if self_test:
        print()
        rc = gate_5_self_test()
        if rc:
            return rc
        print()

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
