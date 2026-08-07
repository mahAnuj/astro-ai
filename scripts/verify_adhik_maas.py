#!/usr/bin/env python3
"""Verify the computed Adhik Maas (intercalary month) detector.

WHY THIS EXISTS
---------------
`muhurat._ADHIK_MAAS_RANGES` was a hand-typed table of six years that drove the
live Muhurat Finder, and it shipped wrong in three separate ways at once:

  * its **2028** row was the real **2026** window with the year mistyped — same
    month name (`Adhik Jyeshtha`), near-identical dates. Every valid muhurat in
    May-June 2028 was suppressed as malamas;
  * its **2029** window was **missing entirely**, so the genuine Adhik Chaitra of
    March-April 2029 raised no warning at all;
  * its **2031** window was ~15 days off.

None of that was noticed for one reason: **there was no computation over the
table, so there was nothing for it to disagree with.** A table nobody re-derives
is a table nobody can check. `src/astro_ai/adhik_maas.py` is now that
computation, and this script is the gate over both of them.

One command, zero judgment, PASS/FAIL, exit 0 or 1. It is deliberately
structured like `scripts/verify_festivals.py` and
`scripts/verify_lunar_observances.py`.

  Gate 1 - the verified table.  Every window in `DRIK_ADHIK` below must be
      reproduced **exactly** by `intercalary_months()`, and every year the table
      asserts leap-free must produce nothing. Both edges print a signed day
      offset, so a future failure reads "start +1, end -1" rather than a bare
      FAIL — the difference between "the boundary convention slipped" and "the
      wrong lunation was picked" is visible in those two numbers alone. This is
      the gate that would have caught issue #141 on the day it shipped.

  Gate 2 - Diwali-drift structural cross-check.  Pure arithmetic on civil dates,
      source-independent of BOTH drikpanchang.com and the detector's internals —
      same spirit as `verify_festivals.py` Gate 3. Diwali is Kartika Amavasya, so
      it drifts about -11 days a year against the Gregorian calendar; an adhik
      maas inserts a whole lunar month and turns that into a ~+19 day jump. The
      gate classifies each year-over-year drift into the "normal" or "adhik maas"
      band and then asks the detector whether a leap month actually intervened.
      The two must agree. Crucially this is a check of the detector against
      *arithmetic*, not against itself: the -12 day drift from Diwali 2027 to
      Diwali 2028 is proof, owing nothing to any almanac, that **no leap month
      falls between them** — i.e. that the old 2028 row was spurious.

  Gate 3 - cross-check against the independent hand-verified JSON.
      `tests/festival_dates_expected.json` `_meta.adhik_maas` is a **second,
      independent derivation** of the same fact: a human transcription off Drik,
      versus this ephemeris computation. Two derivations that agree are worth far
      more than one, which is why the JSON is read here rather than being
      replaced by the detector.

      `scripts/verify_festivals.py` must **NOT** be made to import the detector to
      "share" this data. Its Gate 2 docstring is an explicit promise that a QA
      machine with no ephemeris library installed still runs that gate rather
      than silently skipping it, and importing `adhik_maas` (and so `swisseph`)
      would break that promise. The duplication is the design.

  Gate 4 - structural invariants over the supported range.  Census over
      2000-2100, printed as OUTPUT rather than as a pass target. Asserts that
      every window is 29 or 30 days inclusive; that consecutive adhik months sit
      856-1064 days apart; that every month name is a real one; that adhik months
      fall only in the Mar-Oct band and never straddle a Gregorian year; and that
      there are no kshaya months in range.

      The 29-or-30-day check is the load-bearing one. **A 31-day window is the
      signature of one specific mistake** — taking the two bounding new moons'
      *civil dates* inclusive — and a 31-day lunar month cannot exist, because
      the synodic month is 29.53 days. That is exactly how issue #141's own table
      went wrong; see DRIK_ADHIK below.

  Gate 5 - consistency with `lunar_observances`.  For every adhik window,
      `start - 1 day` and `end` must both be Amavasya days as computed by
      `lunar_observances.observances_between()`. A lunar month runs amavasya to
      amavasya, so this ties the new detector's sunrise reckoning to the one
      already shipped on /festivals. Divergence means one of the two modules
      quietly changed its convention, which no other gate here would see.

      On a **vriddhi** Amavasya the two legitimately differ by exactly one day,
      in one direction only. That is a rule, not a tolerance, and the gate proves
      the vriddhi before allowing it — see the function's own docstring.

NO DEFECT TOLERANCE — DO NOT RE-ADD ONE
---------------------------------------
While issue #141 was in flight, `chart._jd_to_utc_datetime` failed to carry a
60th minute into hours and raised a `ValueError` on certain sunrises, so Gates 4
and 5 whitelisted that one exception text and counted the years it cost instead
of failing. Issue #147 fixed the carry, and the tolerance was then deliberately
deleted: **every exception out of `intercalary_months()` is now a FAIL naming
the year and the exception.** Do not reintroduce a whitelist — absorbing that
class of break silently is precisely the blindness issue #141 existed to remove.

HOW TO EXTEND
-------------
1. To add a year to `DRIK_ADHIK`: open
   `drikpanchang.com/calendars/hindu/hinducalendar.html?year=YYYY&geoname-id=1261481`
   and look for `Adhika` in any month-name column. **Padmini Ekadashi and Parama
   Ekadashi occur only inside an Adhik Maas**, so their presence is a positive
   leap-month marker and their absence from a whole year calendar is a negative
   one — that binary is how the 2028-absent and 2029-present rows below were
   settled. Record a year with no leap month as an empty tuple; asserting an
   absence is as load-bearing as asserting a window, and the 2028 row is the
   proof.
2. Derive the window edges from named observances, never from the new-moon civil
   dates (see DRIK_ADHIK's note). Sanity-check the result: it must be 29 or 30
   days inclusive.
3. Run this script. If a gate goes red, the table or the almanac reading is
   wrong. **Do not tune the engine to silence a gate** — a failing gate means the
   dates are wrong, not that the gate is.

Usage:  uv run python scripts/verify_adhik_maas.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PATH = REPO_ROOT / "tests" / "festival_dates_expected.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

import swisseph as swe  # noqa: E402

from astro_ai import adhik_maas as am  # noqa: E402
from astro_ai import lunar_observances as lo  # noqa: E402

# Every adhik maas drikpanchang.com's New Delhi year calendars show over
# 2026-2031, and every year in that span it shows none. Fetched 2026-08-07 from
# `…/calendars/hindu/hinducalendar.html?year=YYYY&geoname-id=1261481`. Entries are
# year -> tuple of (start, end, nija month name); an EMPTY tuple is a positive
# assertion that the year has no leap month, not a gap in the research.
#
#   2026  `Vat Savitri / May 16, 2026 / Jyeshtha, Krishna Amavasya`
#         `Padmini Ekadashi / May 27, 2026 / Jyeshtha Adhika, Shukla Ekadashi`
#         `Parama Ekadashi / June 11, 2026 / Jyeshtha Adhika, Krishna Ekadashi`
#   2027  no `Adhika` row anywhere in the year calendar
#   2028  no `Adhika` row anywhere in the year calendar — and this is the row
#         `muhurat._ADHIK_MAAS_RANGES` used to get wrong, by carrying a copy of
#         the 2026 window under a mistyped year
#   2029  `Padmini Ekadashi / March 26, 2029 / Chaitra Adhika, Shukla Ekadashi`
#         `Ugadi / Gudi Padwa / April 14, 2029 / Chaitra, Shukla Pratipada`
#         (nija Chaitra opens Apr 14, so Adhika Chaitra ends Apr 13)
#   2030  no `Adhika` row anywhere in the year calendar
#   2031  `Somavati Amavasya / August 18, 2031 / Bhadrapada, Krishna Amavasya`
#         (so Adhika opens Aug 19)
#         `Hartalika Teej / September 19, 2031 / Bhadrapada, Shukla Tritiya`
#         (Shukla Tritiya on Sep 19 puts nija Bhadrapada Pratipada at Sep 17, so
#         Adhika ends Sep 16)
#
# Padmini and Parama Ekadashi occur ONLY in an Adhik Maas, so the 2028 calendar's
# silence about both is evidence rather than merely an absence of evidence.
#
# ---------------------------------------------------------------------------
# WHY THESE ARE NOT THE NUMBERS IN ISSUE #141 — read this before "fixing" them
# ---------------------------------------------------------------------------
# Issue #141's own table gives `Mar 15 - Apr 14` for 2029 and `Aug 18 - Sep 17`
# for 2031. Those are the two **bounding new-moon civil dates, taken inclusive**.
# Doing that adds a day at each edge and yields a **31-day lunar month**, which
# cannot exist: the synodic month is 29.53 days, so an amavasya-to-amavasya
# window is 29 or 30 whole days and never more.
#
# The rows below are the corrected ones — 2029-03-16..2029-04-13 (29 days) and
# 2031-08-19..2031-09-16 (29 days). A lunar day belongs to the month running at
# its local sunrise, so the window opens on the first day whose sunrise follows
# the opening new moon and closes on the day before the first whose sunrise
# follows the closing one. Drik agrees independently on both edges via the named
# observances quoted above.
#
# If a future reader "restores" the issue's numbers here, Gate 4's 29-or-30-day
# invariant will go red immediately — which is the point of having it.
DRIK_ADHIK: dict[int, tuple[tuple[str, str, str], ...]] = {
    2026: (("2026-05-17", "2026-06-15", "Jyeshtha"),),
    2027: (),
    2028: (),
    2029: (("2029-03-16", "2029-04-13", "Chaitra"),),
    2030: (),
    2031: (("2031-08-19", "2031-09-16", "Bhadrapada"),),
}

# Gate 4 census range. 1900-2100 is supported by the detector but costs ~9s;
# 2000-2100 costs ~3.5s and covers every year anyone will plan a muhurat in.
CENSUS_YEARS = range(2000, 2101)

# Consecutive adhik months, in days between their start dates. 856 days is 29
# synodic months and 1064 is 36 — the two spacings the Metonic-ish 19-year cycle
# of 7 leap months actually produces. Anything outside that is not astronomy.
ADHIK_SPACING_DAYS = (856, 1064)

# Adhik months cluster hard in the northern summer half of the year because the
# Sun moves slowest (Earth at aphelion in July), so a solar month is longest and
# a lunar month is likeliest to fit inside one without a sankranti. Mar-Oct is a
# structural consequence, not a coincidence — a window outside it is an algorithm
# break, so it FAILs rather than being reported.
ADHIK_MONTH_BAND = (3, 10)

# Diwali is the Kartika Amavasya, i.e. the new moon while the Sun is in sidereal
# Tula (rashi 6) — the month is named for the rashi the Sun enters during it, and
# Tula is followed by Vrischika, which opens Kartika. Gate 2 uses this to pick
# Diwali's lunation out of `lunar_observances` without a typed date.
_TULA = 6


def _parse(iso: str) -> date:
    return date.fromisoformat(iso)


def _anniversary(d: date, year: int) -> date:
    """`d` moved to `year`, same month and day. 29 Feb clamps to 28 Feb.

    Copied deliberately from `verify_festivals.py` rather than imported: these
    two scripts are meant to be independently runnable, and that one must stay
    importable on a machine with no ephemeris library.
    """
    try:
        return date(year, d.month, d.day)
    except ValueError:
        return date(year, 2, 28)


def _adhik_windows(year: int) -> list[am.IntercalaryMonth]:
    """Adhik (never kshaya) months overlapping `year`, per the detector."""
    return [m for m in am.intercalary_months(year) if m.kind == "adhik"]


# --------------------------------------------------------------------------
# Gate 1 - the verified table
# --------------------------------------------------------------------------

def gate_1_verified_table() -> list[str]:
    failures: list[str] = []
    checked = 0

    for year in sorted(DRIK_ADHIK):
        want = [(_parse(s), _parse(e), n) for s, e, n in DRIK_ADHIK[year]]
        try:
            got = _adhik_windows(year)
        except Exception as exc:
            failures.append(
                f"{year}: intercalary_months() raised {type(exc).__name__}: {exc} — "
                "this year is asserted by the Drik table, so the detector cannot be "
                "allowed to fail on it"
            )
            print(f"  FAIL {year}  detector raised {type(exc).__name__}: {exc}")
            continue

        if len(want) != len(got):
            names = ", ".join(f"Adhik {m.name} {m.start}..{m.end}" for m in got) or "(none)"
            wanted = ", ".join(f"Adhik {n} {s}..{e}" for s, e, n in want) or "(none)"
            failures.append(
                f"{year}: Drik gives {len(want)} adhik maas ({wanted}), the detector "
                f"gives {len(got)} ({names})"
                + (
                    " — a leap month appearing where the almanac has none is exactly "
                    "the shape of the spurious 2028 row in issue #141"
                    if got and not want else
                    " — a leap month the almanac has is missing, which is the shape of "
                    "the absent 2029 row in issue #141"
                    if want and not got else ""
                )
            )
            print(f"  FAIL {year}  drik {wanted:<44} got {names}")
            continue

        if not want:
            print(f"  ok   {year}  drik (no Adhika row in the year calendar)      "
                  "got (none)")
            checked += 1
            continue

        for (w_start, w_end, w_name), m in zip(want, got):
            d_start = (m.start - w_start).days
            d_end = (m.end - w_end).days
            ok = d_start == 0 and d_end == 0 and m.name == w_name
            checked += 1
            print(f"  {'ok  ' if ok else 'FAIL'} {year}  "
                  f"drik {w_start}..{w_end} {w_name:<11} "
                  f"got {m.start}..{m.end} {m.name:<11} "
                  f"start {d_start:+d}, end {d_end:+d}, "
                  f"{(m.end - m.start).days + 1}d")
            if m.name != w_name:
                failures.append(
                    f"{year}: Drik names this Adhik {w_name}, the detector says "
                    f"Adhik {m.name} — the month takes the name of the FOLLOWING nija "
                    "month, so an off-by-one here means the rashi index is being read "
                    "at the wrong new moon"
                )
            if d_start or d_end:
                failures.append(
                    f"{year} Adhik {w_name}: detector gives {m.start}..{m.end} "
                    f"({(m.end - m.start).days + 1} days), Drik gives {w_start}..{w_end} "
                    f"({(w_end - w_start).days + 1} days) — start {d_start:+d}, "
                    f"end {d_end:+d}. Equal-and-opposite offsets mean the wrong lunation; "
                    "offsets of the same sign mean the sunrise boundary convention moved. "
                    "Verify against the almanac before changing either side."
                )

    print(f"  {checked} year(s) checked against drikpanchang.com "
          f"({min(DRIK_ADHIK)}-{max(DRIK_ADHIK)}, wider than DATA_YEARS on purpose)")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - Diwali-drift structural cross-check
# --------------------------------------------------------------------------

def _sun_rashi_at_ist_noon(d: date) -> int:
    """Sidereal rashi of the Sun at 12:00 IST on `d`.

    Independent of `adhik_maas` — this calls the ephemeris directly, so Gate 2
    never asks the detector where a month boundary is. (The Lahiri sidereal mode
    it needs is process-global and is set by importing `astro_ai.chart`, which
    importing `adhik_maas` above already did.) Noon is far enough from a
    sankranti instant for every case in range; the gate fails loudly rather than
    guessing if a year does not yield exactly one candidate.
    """
    jd = swe.julday(d.year, d.month, d.day, 12.0 - 5.5)  # IST noon -> UT hours
    return int(swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0] // 30)


def _kartika_amavasya(year: int) -> tuple[date | None, str]:
    """Diwali's lunation for `year`, from `lunar_observances` alone.

    `festival_registry.DATA_YEARS` only runs 2026-2028, so the Diwali series has
    to be extended past it somehow. It is extended by **computing** the Kartika
    Amavasya rather than by typing four more dates in: a typed date is precisely
    the kind of datum issue #141 was about, and a gate whose evidence is typed
    dates cannot catch a typo in a table of typed dates.
    """
    rows = lo.observances_between(date(year, 1, 1), date(year, 12, 31))
    amavasyas = [d for d, o in rows if o.slug.startswith("amavasya")]
    if not amavasyas:
        return None, f"{year}: lunar_observances returned no Amavasya at all"
    hits = [d for d in amavasyas if _sun_rashi_at_ist_noon(d) == _TULA]
    if len(hits) != 1:
        return None, (
            f"{year}: {len(hits)} Amavasya with the Sun in Tula "
            f"({[d.isoformat() for d in hits]}), expected exactly 1 — a new moon has "
            "landed within a day of a sankranti and noon sampling can no longer "
            "resolve it. Do not widen the window; bisect for the sankranti instant."
        )
    return hits[0], ""


def _adhik_between(d0: date, d1: date) -> list[am.IntercalaryMonth]:
    """Adhik months the DETECTOR places in (d0, d1]. The thing under test."""
    out: list[am.IntercalaryMonth] = []
    for year in range(d0.year, d1.year + 1):
        for m in _adhik_windows(year):
            if d0 < m.start <= d1 and m not in out:
                out.append(m)
    return out


def _check_drift_series(
    label: str,
    series: list[tuple[int, date]],
    bands: dict,
) -> list[str]:
    """Band-classify each year-over-year drift and cross-check it against the detector."""
    failures: list[str] = []
    normal_lo, normal_hi = bands["normal"]
    adhik_lo, adhik_hi = bands["adhik_maas"]

    for (y0, d0), (y1, d1) in zip(series, series[1:]):
        drift = (d1 - _anniversary(d0, y1)).days
        intervening = _adhik_between(d0, d1)
        says = (", ".join(f"Adhik {m.name} {m.start}..{m.end}" for m in intervening)
                if intervening else "no leap month")

        if intervening:
            band, lo_, hi_ = "adhik", adhik_lo, adhik_hi
        else:
            band, lo_, hi_ = "normal", normal_lo, normal_hi
        ok = lo_ <= drift <= hi_

        print(f"  {'ok  ' if ok else 'FAIL'} [{label}] {y0}->{y1}  {d0} -> {d1}  "
              f"{drift:+3d}d  expected {band} band {lo_}..{hi_}  detector: {says}")
        if ok:
            continue

        if intervening:
            failures.append(
                f"[{label}] {y0}->{y1}: {d0} -> {d1} is {drift:+d} days, outside the "
                f"adhik band {adhik_lo}..{adhik_hi}, yet the detector places "
                f"{says} between them. Arithmetic says no whole lunar month was "
                "inserted here — the detector is claiming a leap month that the "
                "calendar does not show, which is exactly the failure mode of the "
                "spurious 2028 row in issue #141."
            )
        else:
            failures.append(
                f"[{label}] {y0}->{y1}: {d0} -> {d1} is {drift:+d} days, outside the "
                f"normal band {normal_lo}..{normal_hi}, and the detector places no "
                "leap month between them. A drift near +19 with no leap month means a "
                "whole lunar month was inserted that the detector cannot see — which "
                "is the failure mode of the MISSING 2029 row in issue #141."
            )
    return failures


def gate_2_diwali_drift(expected: dict) -> list[str]:
    failures: list[str] = []

    # Reused from tests/festival_dates_expected.json rather than redefined, so
    # this gate and verify_festivals.py Gate 3 cannot drift apart.
    bands = expected["drift_bands"]
    print(f"  bands (from {EXPECTED_PATH.name}): normal {bands['normal']}, "
          f"adhik maas {bands['adhik_maas']}")

    # --- Series A: Diwali's own civil dates, exactly as issue #141 argues them.
    # 2026-2028 come from the hand-verified JSON, not from anything computed.
    # 2029 is the issue's own figure; it is the one typed date in this gate, and
    # it is held in place by the pradosh assertion below rather than trusted.
    diwali = expected["festivals"]["diwali"]["dates"]
    series_a: list[tuple[int, date]] = [
        (int(y), _parse(diwali[str(y)])) for y in sorted(int(k) for k in diwali)
    ]
    DIWALI_2029 = date(2029, 11, 5)
    series_a.append((2029, DIWALI_2029))

    # --- Series B: computed Kartika Amavasyas, 2026-2032. Sunrise-reckoned and
    # therefore uniform, where Diwali is pradosh-reckoned and so may sit a day
    # before its own Amavasya. Extending past DATA_YEARS is the whole point: the
    # 2029 AND 2031 leap months both have to show up as +19 day jumps.
    series_b: list[tuple[int, date]] = []
    for year in range(2026, 2033):
        d, why = _kartika_amavasya(year)
        if d is None:
            failures.append(why)
            continue
        series_b.append((year, d))

    # The pradosh rule, from verify_lunar_observances.py Gate B: a festival
    # reckoned after sunrise falls on its computed tithi day or the day before,
    # never after. Asserting it here is what stops Series A's dates and Series B's
    # selector from silently describing two different lunations.
    by_year = dict(series_b)
    for year, d_fest in series_a:
        d_comp = by_year.get(year)
        if d_comp is None:
            continue
        off = (d_comp - d_fest).days
        ok = off in (0, 1)
        print(f"  {'ok  ' if ok else 'FAIL'} Diwali {year} {d_fest} vs computed "
              f"Kartika Amavasya {d_comp}: {off:+d}d (pradosh allows 0 or +1)")
        if not ok:
            failures.append(
                f"Diwali {year} ({d_fest}) is {off:+d} days from the computed Kartika "
                f"Amavasya ({d_comp}); pradosh reckoning allows 0 or +1 only. Either "
                "the date is wrong or _kartika_amavasya() has picked the wrong "
                "lunation, and until that is settled the drift arithmetic below is "
                "describing two different months."
            )

    failures.extend(_check_drift_series("diwali", series_a, bands))
    failures.extend(_check_drift_series("kartika amavasya", series_b, bands))
    print(f"  {len(series_a) - 1} + {len(series_b) - 1} year-over-year drift(s) "
          "cross-checked against the detector")
    return failures


# --------------------------------------------------------------------------
# Gate 3 - cross-check against the independent hand-verified JSON
# --------------------------------------------------------------------------

def gate_3_expected_json(expected: dict) -> list[str]:
    """Second, independent derivation: hand Drik transcription vs the ephemeris.

    Do NOT edit tests/festival_dates_expected.json or verify_festivals.py to make
    this agree. If the two disagree, that disagreement is the finding — report it
    and re-read the almanac. Silencing either side destroys the independence that
    makes this gate worth running at all.
    """
    failures: list[str] = []
    checked = 0

    for key, windows in sorted(expected["_meta"]["adhik_maas"].items()):
        if key.startswith("_"):  # `_note`
            continue
        year = int(key)
        # The JSON writes the display name ("Adhik Jyeshtha"); IntercalaryMonth
        # carries the bare nija name ("Jyeshtha") and leaves the prefix to callers.
        want = [(_parse(s), _parse(e), n.removeprefix("Adhik ").strip())
                for s, e, n in windows]
        try:
            got = _adhik_windows(year)
        except Exception as exc:
            failures.append(
                f"{year}: intercalary_months() raised {type(exc).__name__}: {exc}, but "
                "the expected-dates JSON makes an assertion about this year"
            )
            continue

        if len(want) != len(got):
            failures.append(
                f"{year}: {EXPECTED_PATH.name} declares {len(want)} adhik maas, the "
                f"detector finds {len(got)} "
                f"({', '.join(f'{m.start}..{m.end} {m.name}' for m in got) or 'none'}) "
                "— two independent derivations disagree; re-read the almanac, do not "
                "edit either side to match the other"
            )
            print(f"  FAIL {year}  json {len(want)} window(s), detector {len(got)}")
            continue

        if not want:
            print(f"  ok   {year}  json (none)                     detector (none)")
            checked += 1
            continue

        for (w_start, w_end, w_name), m in zip(want, got):
            checked += 1
            ok = (m.start, m.end, m.name) == (w_start, w_end, w_name)
            print(f"  {'ok  ' if ok else 'FAIL'} {year}  "
                  f"json {w_start}..{w_end} {w_name:<11} "
                  f"detector {m.start}..{m.end} {m.name:<11} "
                  f"start {(m.start - w_start).days:+d}, end {(m.end - w_end).days:+d}")
            if not ok:
                failures.append(
                    f"{year}: {EXPECTED_PATH.name} has {w_start}..{w_end} Adhik {w_name}, "
                    f"the detector computes {m.start}..{m.end} Adhik {m.name}. The JSON "
                    "is a hand transcription off Drik and the detector is an ephemeris "
                    "computation — they were meant to be independent, so a disagreement "
                    "is a real finding. Report it; do not 'fix' either side."
                )

    print(f"  {checked} year(s) cross-checked against {EXPECTED_PATH.name} "
          "_meta.adhik_maas (independent hand transcription)")
    return failures


# --------------------------------------------------------------------------
# Gate 4 - structural invariants over the supported range
# --------------------------------------------------------------------------

def gate_4_structure() -> tuple[list[str], list[am.IntercalaryMonth]]:
    failures: list[str] = []
    windows: set[tuple[date, date, str, str]] = set()

    for year in CENSUS_YEARS:
        try:
            months = am.intercalary_months(year)
        except Exception as exc:
            failures.append(
                f"{year}: intercalary_months() raised {type(exc).__name__}: {exc} — "
                "the detector must answer for every year in the supported range. There "
                "is no tolerated exception here; see the module docstring."
            )
            print(f"  FAIL {year}  detector raised {type(exc).__name__}: {exc}")
            continue
        # A window overlapping two Gregorian years is returned by both, so the
        # census is a set, not a list.
        for m in months:
            windows.add((m.start, m.end, m.name, m.kind))

    census = [am.IntercalaryMonth(*w) for w in sorted(windows)]
    adhik = [m for m in census if m.kind == "adhik"]
    kshaya = [m for m in census if m.kind == "kshaya"]

    for m in adhik:
        print(f"  adhik   {m.start} .. {m.end}  {(m.end - m.start).days + 1:>2}d  "
              f"Adhik {m.name}")
    for m in kshaya:
        print(f"  kshaya  {m.start} .. {m.end}  {(m.end - m.start).days + 1:>2}d  "
              f"{m.name}")
    print(f"  {len(adhik)} adhik, {len(kshaya)} kshaya over "
          f"{CENSUS_YEARS.start}-{CENSUS_YEARS.stop - 1}  [census is OUTPUT, not a target]")

    if kshaya:
        failures.append(
            f"{len(kshaya)} kshaya month(s) in {CENSUS_YEARS.start}-"
            f"{CENSUS_YEARS.stop - 1}: "
            + ", ".join(f"{m.start}..{m.end} {m.name}" for m in kshaya)
            + ". There are none in this range astronomically, so a kshaya here means "
            "the two-sankranti branch is firing on an ordinary month. This matters "
            "live: adhik_maas_for_date() deliberately ignores kshaya, so such a month "
            "would silently stop blocking muhurats."
        )

    for m in adhik:
        span = (m.end - m.start).days + 1
        if span not in (29, 30):
            failures.append(
                f"{m.start}..{m.end} (Adhik {m.name}) is {span} days inclusive, "
                "expected 29 or 30. A 31-day window is the signature of taking the two "
                "bounding new moons' CIVIL DATES inclusive — a synodic month is 29.53 "
                "days, so a 31-day lunar month cannot exist. This is exactly how issue "
                "#141's table went wrong for 2029 and 2031."
            )
        if m.name not in am._MONTH_NAMES:
            failures.append(
                f"{m.start}..{m.end}: month name {m.name!r} is not one of the twelve "
                f"in adhik_maas._MONTH_NAMES — the rashi index has run off the end"
            )
        lo_month, hi_month = ADHIK_MONTH_BAND
        if not (lo_month <= m.start.month <= hi_month and lo_month <= m.end.month <= hi_month):
            failures.append(
                f"{m.start}..{m.end} (Adhik {m.name}) falls outside the Mar-Oct band. "
                "Adhik months cluster there because the solar month is longest around "
                "aphelion; one outside it is an algorithm break, not an astronomical "
                "surprise."
            )
        if m.start.year != m.end.year:
            failures.append(
                f"{m.start}..{m.end} (Adhik {m.name}) straddles a Gregorian year. That "
                "is possible in principle and intercalary_months() filters on overlap "
                "precisely so it stays visible from both years — but it has never "
                "happened in range, so treat it as an algorithm break until an almanac "
                "says otherwise."
            )

    lo_gap, hi_gap = ADHIK_SPACING_DAYS
    spacing_checked = 0
    for m0, m1 in zip(adhik, adhik[1:]):
        gap = (m1.start - m0.start).days
        spacing_checked += 1
        if not (lo_gap <= gap <= hi_gap):
            failures.append(
                f"{m0.start} -> {m1.start}: {gap} days between consecutive adhik "
                f"months, expected {lo_gap}-{hi_gap} (29-36 synodic months). Too small "
                "means a month was double-counted; too large means one was missed."
            )
    print(f"  {spacing_checked} consecutive-spacing check(s)")
    return failures, adhik


# --------------------------------------------------------------------------
# Gate 5 - consistency with lunar_observances
# --------------------------------------------------------------------------

# Tithi index of Amavasya, derived from lunar_observances' own table rather than
# written as 29, so the two cannot disagree about which tithi this is.
_AMAVASYA_IDX = next(i for i, row in lo._TARGETS.items() if row[0] == "amavasya")


def _is_vriddhi_amavasya(first: date) -> bool:
    """True if Amavasya is still running at the NEXT sunrise after `first` too."""
    return (
        lo._tithi_index_at_sunrise(first) == _AMAVASYA_IDX
        and lo._tithi_index_at_sunrise(first + timedelta(days=1)) == _AMAVASYA_IDX
    )


def gate_5_amavasya_alignment(adhik: list[am.IntercalaryMonth]) -> list[str]:
    """A lunar month runs amavasya to amavasya, under one sunrise convention.

    `start` is the first day whose sunrise follows the opening new moon, so the
    day BEFORE it is the one whose sunrise still had Amavasya running. `end` is
    the day before the first sunrise after the closing new moon, so `end` is
    itself such a day. Both must line up with `lunar_observances`, which reckons
    its tithis at the same New Delhi sunrise. If they stop lining up, one of the
    two modules has changed its convention and only this gate would notice.

    THE ONE PERMITTED OFFSET, AND WHY IT IS A RULE RATHER THAN A TOLERANCE
    ---------------------------------------------------------------------
    The two modules answer subtly different questions about a **vriddhi**
    Amavasya — one long enough to be running at two consecutive sunrises.
    `lunar_observances` emits the observance on the FIRST day of that run (its
    dashami-viddha second-day pick is deliberately restricted to Ekadashi; see
    its Gate C). `adhik_maas` needs the LAST day whose sunrise still precedes the
    new-moon instant, which is the SECOND. So on a vriddhi Amavasya the detector's
    edge is legitimately one day after the emitted observance.

    The offset is therefore allowed to be -1 ONLY where the run is proved vriddhi
    from the sunrise samples, and is NEVER allowed to be +1: for an ordinary
    Amavasya the two days are the same day, and the detector's edge can never
    precede the emitted observance. Widening this to a symmetric +/-1 tolerance
    would let a genuine boundary slip through — the direction is the whole check.

    Real instance in range: Adhik Shravana 2004-07-18..2004-08-16 ends on
    2004-08-16, while the observance sits on 2004-08-15; tithi 29 holds at both
    sunrises. Both modules are correct. It is the only one over 2000-2100.
    """
    failures: list[str] = []
    checked = vriddhi = 0

    for m in adhik:
        for want, label in (
            (m.start - timedelta(days=1), "start-1"),
            (m.end, "end"),
        ):
            rows = lo.observances_between(want - timedelta(days=3), want + timedelta(days=3))
            amavasyas = [d for d, o in rows if o.slug.startswith("amavasya")]
            checked += 1
            if want in amavasyas:
                continue

            nearest = min(amavasyas, key=lambda c: abs((c - want).days), default=None)
            if nearest is None:
                failures.append(
                    f"Adhik {m.name} {m.start}..{m.end}: {label} = {want} has no "
                    "computed Amavasya within 3 days at all — the two modules are no "
                    "longer describing the same lunation"
                )
                print(f"  FAIL Adhik {m.name:<11} {label:<7} {want} -> none within 3 days")
                continue

            off = (nearest - want).days
            if off == -1 and _is_vriddhi_amavasya(nearest):
                vriddhi += 1
                print(f"  ok   Adhik {m.name:<11} {label:<7} {want} -> observance "
                      f"{nearest} ({off:+d}d, vriddhi Amavasya: tithi "
                      f"{_AMAVASYA_IDX} holds at both sunrises, so the observance takes "
                      "the first day and the month boundary the second)")
                continue

            failures.append(
                f"Adhik {m.name} {m.start}..{m.end}: {label} = {want}, but the nearest "
                f"computed Amavasya is {nearest} ({off:+d} days)"
                + (
                    " — a +1 offset is impossible under either module's rule: for an "
                    "ordinary Amavasya both pick the same day, and for a vriddhi one "
                    "the detector's edge comes LATER, not earlier"
                    if off > 0 else
                    " and that run is not vriddhi, so there is no rule under which the "
                    "two may differ. One of adhik_maas and lunar_observances has "
                    "changed its sunrise convention; check which before touching either."
                )
            )
            print(f"  FAIL Adhik {m.name:<11} {label:<7} {want} -> nearest computed "
                  f"Amavasya {nearest} ({off:+d}d)")

    print(f"  {checked} window edge(s) tied to a computed Amavasya "
          f"({vriddhi} via the vriddhi rule)")
    if checked == 0:
        failures.append(
            "no window edge could be checked at all — lunar_observances returned "
            "nothing everywhere, so this gate proved nothing rather than passing"
        )
    return failures


# --------------------------------------------------------------------------

def main() -> int:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))

    print("Adhik Maas verification")
    print("  detector : src/astro_ai/adhik_maas.py")
    print("  sunrise  : src/astro_ai/lunar_observances.py (same New Delhi / IST "
          "convention)")
    print(f"  expected : {EXPECTED_PATH.relative_to(REPO_ROOT)} _meta.adhik_maas")
    print(f"  almanac  : drikpanchang.com New Delhi year calendars, fetched "
          f"2026-08-07, {min(DRIK_ADHIK)}-{max(DRIK_ADHIK)}")
    print(f"  census   : {CENSUS_YEARS.start}-{CENSUS_YEARS.stop - 1} "
          f"(detector supports {am.SUPPORTED_YEARS.start}-"
          f"{am.SUPPORTED_YEARS.stop - 1})")
    print()

    state: dict[str, object] = {}

    def _gate_4() -> list[str]:
        failures, adhik = gate_4_structure()
        state["adhik"] = adhik
        return failures

    def _gate_5() -> list[str]:
        return gate_5_amavasya_alignment(state.get("adhik") or [])  # type: ignore[arg-type]

    gates = [
        ("Gate 1 - the verified table (drikpanchang.com, New Delhi)",
         gate_1_verified_table),
        ("Gate 2 - Diwali-drift structural cross-check (arithmetic vs the detector)",
         lambda: gate_2_diwali_drift(expected)),
        ("Gate 3 - cross-check against the independent hand-verified JSON",
         lambda: gate_3_expected_json(expected)),
        ("Gate 4 - structural invariants over the supported range", _gate_4),
        ("Gate 5 - consistency with lunar_observances (amavasya to amavasya)",
         _gate_5),
    ]

    all_failures: list[str] = []
    results: list[tuple[str, int]] = []
    for title, run in gates:
        print(title)
        failures = run()
        for line in failures:
            print(f"  FAIL: {line}")
        print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
        print()
        results.append((title, len(failures)))
        all_failures.extend(failures)

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s). Do not tune the engine to "
              "silence a gate; check the window against an almanac first, and check "
              "that it is 29 or 30 days long before you believe it.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
