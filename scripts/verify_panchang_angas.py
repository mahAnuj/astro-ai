#!/usr/bin/env python3
"""Verify the computed Nitya Yoga and Karana — the 4th and 5th angas.

WHY THIS EXISTS
---------------
Issue #142: `/panchang`'s meta description and its `SoftwareApplication`
JSON-LD both advertised "yoga, karana" to searchers and to Google, while
`DailyPanchang` carried neither and the page only *explained what they are*.
Rendering them makes the claim true — but only if the values are right, and
both are shapes that fail silently:

  * **Nitya Yoga** is `(Sun + Moon)`, not `(Moon - Sun)`. Get the sign wrong
    and every value is still a plausible-looking yoga name. It is also the one
    anga that is NOT ayanamsa-invariant — the two shifts add rather than
    cancel — so a tropical slip moves it by ~2 places all year and never
    looks obviously broken.
  * **Karana** has a fixed/movable structure that an off-by-one destroys
    invisibly. Kimstughna is the FIRST half of Shukla Pratipada (index 0) and
    Shakuni / Chatushpada / Naga are the month's LAST three halves (57/58/59);
    indices 1..56 cycle the 7 movable karanas eight times. Shift that by one
    and Vishti (Bhadra) — the karana the whole muhurta tradition exists to
    avoid — lands on the wrong day, on a page that claims authority.

Neither error is visible in a diff, and neither is visible from inside the
implementation. So this gate checks the computation against a REAL PUBLISHED
ALMANAC and against arithmetic that owes the implementation nothing.

One command, zero judgment, PASS/FAIL, exit 0 or 1. Deliberately structured
like `scripts/verify_adhik_maas.py` and `scripts/verify_festivals.py`.

  Gate 1 - the verified almanac table.  Nine drikpanchang.com New Delhi day
      pages, each fetched and transcribed by hand, each with its source URL
      recorded next to the values. `compute_panchang()` must reproduce the
      yoga, the karana AND the tithi running at that day's sunrise. The nine
      are chosen to cover the structure, not to be convenient: all four fixed
      karanas (Kimstughna 2026-10-11, Shakuni 2026-11-08, Naga 2026-03-19 and
      2026-11-09), Vishti/Bhadra (2026-05-20), the first and last yoga of the
      27 (Vaidhriti 2026-10-11), and both pakshas.

      The computed sunrise is checked against Drik's printed sunrise too. The
      whole convention is "the anga running at LOCAL SUNRISE", so if the
      sunrise itself drifts the anga comparison stops meaning anything —
      2026-03-19 has Naga ending only 26 minutes after sunrise, and that day
      is in the table precisely because it is tight.

  Gate 2 - structural invariants over a two-year census.  Every day of
      2026-2027 at New Delhi sunrise. Yoga index in 0..26 and karana index in
      0..59; both names must equal what the index says they should be, where
      "should" is re-derived here from the classical rule rather than imported
      from `chart.py` — an independent second derivation, same reason
      `verify_adhik_maas.py` Gate 3 reads the JSON instead of the detector.
      Vishti must never appear at 0, 57, 58 or 59, and no fixed karana may
      appear anywhere else; `karana_index // 2 == tithi_index` must hold at
      every single sample, because a karana IS half a tithi and the two are
      computed from the same elongation.

  Gate 3 - rate and coverage.  Pure arithmetic against the synodic month,
      independent of both Drik and the implementation's naming. The Sun+Moon
      combined motion is 12.7-16.4 deg/day against a 13deg20' yoga, so the
      yoga index advances 0, 1 or 2 per day and averages ~1.06; the Moon-Sun
      elongation is 10.7-14.5 deg/day against a 6deg karana, so the karana
      index advances 1, 2 or 3 per day and averages ~2.03. A sign error, a
      wrong divisor or a wrong ayanamsa all break these bands. Coverage is
      asserted too: over two years every one of the 27 yogas and every one of
      the 60 karana indices must actually occur, which is what proves the
      fixed-karana branches are reachable at all rather than merely correct
      in principle.

HOW TO EXTEND THE ALMANAC TABLE
-------------------------------
Open the URL recorded next to any row, read the Yoga and Karana blocks, and
take the entry running at the printed sunrise (the FIRST entry of the day
unless its end time precedes sunrise). Record Drik's own spelling in
`drik_yoga` / `drik_karana` — the alias map below does the normalising in the
open, so nobody has to wonder whether a value was quietly massaged to fit.

**Do not derive an expected value from this codebase.** A gate whose expected
values came from the implementation it is testing proves only that the code
is self-consistent, which is exactly the blindness issue #142 was filed
about. If you cannot reach an almanac, leave the table alone.

Usage:  uv run python scripts/verify_panchang_angas.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai.chart import (  # noqa: E402
    compute_chart,
    compute_moon_rise_set,
    compute_panchang,
)

# The almanac's locale. Drik's day pages default to New Delhi, and every row in
# ALMANAC below was read off a New Delhi page, so the census uses the same city
# — a Mumbai sunrise is ~10 minutes later and would change boundary days.
CITY = "New Delhi, India"

# drikpanchang.com prints day pages at this URL with a DD/MM/YYYY date. Recorded
# as a template so each row below can carry its own exact source link without 9
# near-identical strings.
DRIK_URL = "https://www.drikpanchang.com/panchang/day-panchang.html?date={dd}/{mm}/{yyyy}"

# Drik's transliterations differ from ours in a handful of places. Mapping them
# here, in the open, is deliberate: the alternative is silently editing the
# transcribed values to match the code, which would hide a real disagreement.
DRIK_ALIASES: dict[str, str] = {
    "Ayushmana":  "Ayushman",
    "Garaja":     "Gara",
    "Vanija":     "Vanij",
    "Nagava":     "Naga",
    "Kinstughna": "Kimstughna",
    "Chatushpad": "Chatushpada",
    "Variyan":    "Variyana",
    "Aindra":     "Indra",
}

# Nine New Delhi day pages from drikpanchang.com, all fetched 2026-08-07.
# Fields: (iso date, drik sunrise HH:MM or None, drik yoga, drik karana,
#          drik tithi as "<Paksha> <Name>", why this date is in the table)
# The yoga/karana recorded is the one RUNNING AT SUNRISE, which is the first
# entry Drik lists for the day unless that entry's end time precedes sunrise.
ALMANAC: tuple[tuple[str, str | None, str, str, str, str], ...] = (
    # https://www.drikpanchang.com/panchang/day-panchang.html?date=15/01/2026
    #   Tithi  "Dwadashi upto 08:16 PM" (Krishna)
    #   Yoga   "Vriddhi upto 08:38 PM"
    #   Karana "Taitila upto 08:16 PM" then "Garaja"
    ("2026-01-15", None, "Vriddhi", "Taitila", "Krishna Dwadashi",
     "ordinary movable karana mid-Krishna-paksha; the baseline case"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=18/02/2026
    #   Sunrise 06:57 AM
    #   Tithi  "Pratipada upto 04:57 PM" (Shukla)
    #   Yoga   "Shiva upto 10:45 PM"
    #   Karana "Bava upto 04:57 PM" then "Balava upto 04:31 AM, Feb 19"
    ("2026-02-18", "06:57", "Shiva", "Bava", "Shukla Pratipada",
     "karana index 1 — the first MOVABLE karana, immediately after Kimstughna"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=19/03/2026
    #   Sunrise 06:26 AM
    #   Tithi  "Amavasya upto 06:52 AM"
    #   Yoga   "Shukla upto 01:17 AM, Mar 20" then "Brahma"
    #   Karana "Nagava upto 06:52 AM" then "Kinstughna upto 05:55 PM" then "Bava"
    ("2026-03-19", "06:26", "Shukla", "Naga", "Krishna Amavasya",
     "karana index 59 with only 26 min to spare — the tightest sunrise boundary here"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=20/05/2026
    #   Sunrise 05:28 AM
    #   Tithi  "Chaturthi upto 11:06 AM" (Shukla)
    #   Yoga   "Shula upto 02:10 PM" then "Ganda"
    #   Karana "Vishti upto 11:06 AM" then "Bava upto 09:42 PM" then "Balava"
    ("2026-05-20", "05:28", "Shula", "Vishti", "Shukla Chaturthi",
     "VISHTI / BHADRA — the karana the muhurta tradition exists to avoid"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=01/08/2026
    #   Sunrise 05:42 AM
    #   Tithi  "Tritiya upto 11:07 PM" (Krishna)
    #   Yoga   "Shobhana upto 11:23 PM" then "Atiganda"
    #   Karana "Vanija upto 10:52 AM" then "Vishti upto 11:07 PM"
    ("2026-08-01", "05:42", "Shobhana", "Vanij", "Krishna Tritiya",
     "movable karana in the 5th of the 8 cycles — catches a cycle-length slip"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=25/09/2026
    #   Sunrise 06:11 AM
    #   Tithi  "Chaturdashi upto 11:06 PM" (Shukla)
    #   Yoga   "Shula upto 02:51 PM"   (the listed "Ravi Yoga" is a booster, not a nitya yoga)
    #   Karana "Garaja upto 11:17 AM" then "Vanija upto 11:06 PM"
    ("2026-09-25", "06:11", "Shula", "Gara", "Shukla Chaturdashi",
     "first half of its tithi, where the other rows are mostly second halves"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=11/10/2026
    #   Sunrise 06:19 AM
    #   Tithi  "Pratipada upto 09:30 PM" (Shukla)
    #   Yoga   "Vaidhriti upto 09:05 PM" then "Vishkambha"
    #   Karana "Kinstughna upto 09:21 AM" then "Bava upto 09:30 PM"
    ("2026-10-11", "06:19", "Vaidhriti", "Kimstughna", "Shukla Pratipada",
     "KIMSTUGHNA at index 0 AND Vaidhriti, the 27th yoga — both list ends at once"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=08/11/2026
    #   Sunrise 06:38 AM
    #   Tithi  "Chaturdashi upto 11:27 AM" (Krishna)
    #   Yoga   "Ayushmana upto 03:03 AM, Nov 09" then "Saubhagya"
    #   Karana "Shakuni upto 11:27 AM" then "Chatushpada upto 11:56 PM" then "Nagava"
    ("2026-11-08", "06:38", "Ayushman", "Shakuni", "Krishna Chaturdashi",
     "SHAKUNI at index 57 — the first of the three closing fixed karanas"),

    # https://www.drikpanchang.com/panchang/day-panchang.html?date=09/11/2026
    #   Sunrise 06:39 AM
    #   Tithi  "Amavasya upto 12:31 PM"
    #   Yoga   "Saubhagya upto 02:57 AM, Nov 10" then "Shobhana"
    #   Karana "Nagava upto 12:31 PM" then "Kinstughna upto 01:12 AM, Nov 10"
    ("2026-11-09", "06:39", "Saubhagya", "Naga", "Krishna Amavasya",
     "NAGA at index 59, the last half-tithi of the lunar month"),
)

# Drik rounds to the minute and its rise convention need not match Swiss
# Ephemeris' defaults exactly. 4 minutes is generous enough for refraction and
# disc-edge differences and far tighter than any anga boundary in the table
# (the tightest, 2026-03-19, has 26 minutes of headroom).
SUNRISE_TOLERANCE_MIN = 4

# Gate 2/3 census. Two years is ~24.7 lunar months — enough for every one of
# the 60 karana indices to be sampled at some sunrise, which is what makes the
# coverage assertion in Gate 3 meaningful rather than aspirational.
CENSUS_START = date(2026, 1, 1)
CENSUS_END = date(2027, 12, 31)

# --- The classical rule, re-derived here so Gate 2 is a SECOND derivation ---
# Deliberately not imported from astro_ai.chart. If these are ever "shared" to
# remove the duplication, Gate 2 stops testing anything.
EXPECTED_YOGA_NAMES: tuple[str, ...] = (
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
    "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha",
    "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra",
    "Vaidhriti",
)
FIXED_KARANA_SLOTS: dict[int, str] = {
    0: "Kimstughna", 57: "Shakuni", 58: "Chatushpada", 59: "Naga",
}
MOVABLE_CYCLE: tuple[str, ...] = (
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanij", "Vishti",
)


def expected_karana_name(idx: int) -> str:
    """The 60-karana sequence, written out from the classical rule.

    Index 0 is Kimstughna (first half of Shukla Pratipada); 1..56 are the 7
    movable karanas repeated 8 times; 57/58/59 are Shakuni, Chatushpada and
    Naga, the last three half-tithis of the lunar month.
    """
    if idx in FIXED_KARANA_SLOTS:
        return FIXED_KARANA_SLOTS[idx]
    return MOVABLE_CYCLE[(idx - 1) % 7]


# Sidereal periods, days. The yoga is a SUM of two longitudes so it needs both
# separately; the karana is a DIFFERENCE, which is exactly what the synodic
# month already is. Getting these two compositions the right way round is the
# whole point of Gate 3 — the first draft of this file used the synodic month
# for the yoga as well and the gate caught it immediately.
SIDEREAL_MONTH_DAYS = 27.321662
SIDEREAL_YEAR_DAYS = 365.256363
SYNODIC_MONTH_DAYS = 29.530588

# Yoga: (Sun + Moon), so the rate is the SUM of the two sidereal rates,
# 0.986 + 13.176 = 14.162 deg/day, against a 360/27 = 13deg20' yoga -> ~1.062
# per day. Lunar anomaly swings the instantaneous rate over 12.7-16.4 deg/day,
# i.e. 0.95-1.23 yogas, so the daily index advance is 0, 1 or 2 and nothing else.
YOGA_STEPS = {0, 1, 2}
YOGA_MEAN_RATE = (
    (360.0 / SIDEREAL_MONTH_DAYS + 360.0 / SIDEREAL_YEAR_DAYS) / (360.0 / 27.0)
)

# Karana: (Moon - Sun), so the rate is the synodic rate, 12.191 deg/day, against
# a 6 deg karana -> ~2.032 per day. The elongation runs 10.7-14.5 deg/day with
# anomaly, i.e. 1.79-2.41, so the daily index advance is 1, 2 or 3.
KARANA_STEPS = {1, 2, 3}
KARANA_MEAN_RATE = (360.0 / SYNODIC_MONTH_DAYS) / 6.0

# Mean daily rates are averaged over 730 samples, so they converge tightly; 2%
# is loose enough for the finite window and far tighter than any real error
# (a wrong divisor or a sign flip moves these by tens of percent).
RATE_TOLERANCE = 0.02


def _panchang_for(chart, day: date):
    """DailyPanchang for `day` at CITY, anchored at local noon like the route does."""
    tz = ZoneInfo(chart.birth_tz)
    return compute_panchang(
        chart, when=datetime(day.year, day.month, day.day, 12, 0, tzinfo=tz)
    )


def _drik(name: str) -> str:
    """Drik's spelling normalised to ours, via the visible alias map."""
    return DRIK_ALIASES.get(name, name)


# --------------------------------------------------------------------------
# Gate 1 - the verified almanac table
# --------------------------------------------------------------------------

def gate_1_almanac(chart) -> list[str]:
    failures: list[str] = []

    for iso, drik_sunrise, d_yoga, d_karana, d_tithi, why in ALMANAC:
        day = date.fromisoformat(iso)
        want_yoga = _drik(d_yoga)
        want_karana = _drik(d_karana)
        try:
            p = _panchang_for(chart, day)
        except Exception as exc:
            failures.append(
                f"{iso}: compute_panchang() raised {type(exc).__name__}: {exc} — "
                "this date is asserted by the almanac table, so the computation "
                "cannot be allowed to fail on it"
            )
            print(f"  FAIL {iso}  compute_panchang raised {type(exc).__name__}: {exc}")
            continue

        got_tithi = f"{p.tithi_paksha} {p.tithi_name}"
        ok_yoga = p.yoga_name == want_yoga
        ok_karana = p.karana_name == want_karana
        ok_tithi = got_tithi == d_tithi

        sunrise_note = ""
        ok_sunrise = True
        if drik_sunrise:
            want_h, want_m = (int(x) for x in drik_sunrise.split(":"))
            got_min = p.sunrise.hour * 60 + p.sunrise.minute
            off = got_min - (want_h * 60 + want_m)
            ok_sunrise = abs(off) <= SUNRISE_TOLERANCE_MIN
            sunrise_note = (f"  sunrise drik {drik_sunrise} got "
                            f"{p.sunrise.strftime('%H:%M')} ({off:+d}m)")

        ok = ok_yoga and ok_karana and ok_tithi and ok_sunrise
        print(f"  {'ok  ' if ok else 'FAIL'} {iso}  "
              f"yoga drik {want_yoga:<11} got {p.yoga_name:<11}(#{p.yoga_index:>2})  "
              f"karana drik {want_karana:<11} got {p.karana_name:<11}(#{p.karana_index:>2})  "
              f"tithi {got_tithi}{sunrise_note}")
        print(f"       {why}")

        if not ok_sunrise:
            failures.append(
                f"{iso}: computed sunrise {p.sunrise.strftime('%H:%M')} vs Drik's "
                f"{drik_sunrise} — more than {SUNRISE_TOLERANCE_MIN} min apart. Every "
                "anga in this table is the one running AT SUNRISE, so a sunrise that "
                "has moved makes the yoga and karana comparisons below meaningless. "
                "Fix the sunrise before reading anything else on this row."
            )
        if not ok_yoga:
            failures.append(
                f"{iso}: drikpanchang gives yoga {want_yoga}, we compute "
                f"{p.yoga_name} (index {p.yoga_index}). Nitya yoga is "
                "(Sun + Moon) sidereal / 13deg20' — check the SIGN (it is a sum, not "
                "the tithi's difference), the ayanamsa (this anga is NOT "
                "ayanamsa-invariant), and the order of _NITYA_YOGA_NAMES."
            )
        if not ok_karana:
            failures.append(
                f"{iso}: drikpanchang gives karana {want_karana}, we compute "
                f"{p.karana_name} (index {p.karana_index}). Index 0 is Kimstughna, "
                "1..56 cycle the 7 movable karanas, 57/58/59 are Shakuni / "
                "Chatushpada / Naga. An off-by-one in either branch puts Vishti "
                "(Bhadra) on the wrong day."
            )
        if not ok_tithi:
            failures.append(
                f"{iso}: drikpanchang gives tithi {d_tithi}, we compute {got_tithi}. "
                "The tithi is checked alongside the karana on purpose — a karana is "
                "half a tithi, so if the tithi has moved the karana was never going "
                "to be right, and this says which of the two broke."
            )

    print(f"  {len(ALMANAC)} day(s) checked against drikpanchang.com "
          f"({CITY}), each with its source URL recorded above the row")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - structural invariants over a two-year census
# --------------------------------------------------------------------------

def gate_2_structure(census: list[tuple[date, object]]) -> list[str]:
    failures: list[str] = []
    yoga_seen: set[int] = set()
    karana_seen: set[int] = set()

    for day, p in census:
        yoga_seen.add(p.yoga_index)
        karana_seen.add(p.karana_index)

        if not 0 <= p.yoga_index <= 26:
            failures.append(
                f"{day}: yoga_index {p.yoga_index} outside 0..26 — there are exactly "
                "27 nitya yogas"
            )
            continue
        if not 0 <= p.karana_index <= 59:
            failures.append(
                f"{day}: karana_index {p.karana_index} outside 0..59 — there are "
                "exactly 60 karanas in a lunar month"
            )
            continue

        want_yoga = EXPECTED_YOGA_NAMES[p.yoga_index]
        if p.yoga_name != want_yoga:
            failures.append(
                f"{day}: yoga index {p.yoga_index} is named {p.yoga_name!r}, but the "
                f"classical order puts {want_yoga!r} there"
            )

        want_karana = expected_karana_name(p.karana_index)
        if p.karana_name != want_karana:
            failures.append(
                f"{day}: karana index {p.karana_index} is named {p.karana_name!r}, "
                f"but the classical order puts {want_karana!r} there"
            )

        if p.karana_index in FIXED_KARANA_SLOTS and p.karana_name == "Vishti":
            failures.append(
                f"{day}: Vishti at karana index {p.karana_index}, which belongs to the "
                f"FIXED karana {FIXED_KARANA_SLOTS[p.karana_index]}. This is the "
                "off-by-one issue #142 warned about, and it puts Bhadra — the one "
                "karana every muhurta rule avoids — on a day it does not fall on."
            )
        if p.karana_name in FIXED_KARANA_SLOTS.values():
            slot = next(i for i, n in FIXED_KARANA_SLOTS.items()
                        if n == p.karana_name)
            if p.karana_index != slot:
                failures.append(
                    f"{day}: fixed karana {p.karana_name} at index {p.karana_index}; "
                    f"it only ever sits at {slot}. Kimstughna is the first half of "
                    "Shukla Pratipada and the other three close the lunar month — "
                    "they cannot float."
                )

        if p.karana_index // 2 != p.tithi_index:
            failures.append(
                f"{day}: karana_index {p.karana_index} // 2 = {p.karana_index // 2} "
                f"but tithi_index is {p.tithi_index}. A karana IS half a tithi and "
                "both are read off the same Sun-Moon elongation at the same instant, "
                "so these can only disagree if one of them is computed from a "
                "different moment or a different formula."
            )

    print(f"  {len(census)} sunrise(s) sampled, {CENSUS_START}..{CENSUS_END} at {CITY}")
    print(f"  {len(yoga_seen)}/27 distinct yogas and {len(karana_seen)}/60 distinct "
          "karana indices observed  [coverage is asserted in Gate 3]")
    if not census:
        failures.append(
            "the census is empty — this gate proved nothing rather than passing"
        )
    return failures


# --------------------------------------------------------------------------
# Gate 3 - rate and coverage (arithmetic, independent of Drik and of naming)
# --------------------------------------------------------------------------

def gate_3_rate_and_coverage(census: list[tuple[date, object]]) -> list[str]:
    failures: list[str] = []

    yoga_steps: list[int] = []
    karana_steps: list[int] = []
    for (d0, p0), (d1, p1) in zip(census, census[1:]):
        if (d1 - d0).days != 1:
            continue
        y_step = (p1.yoga_index - p0.yoga_index) % 27
        k_step = (p1.karana_index - p0.karana_index) % 60
        yoga_steps.append(y_step)
        karana_steps.append(k_step)
        if y_step not in YOGA_STEPS:
            failures.append(
                f"{d0} -> {d1}: yoga index jumped {y_step} in one day "
                f"({p0.yoga_index} -> {p1.yoga_index}); Sun+Moon combined motion "
                f"allows only {sorted(YOGA_STEPS)}. A jump outside that band is a "
                "formula error, not astronomy."
            )
        if k_step not in KARANA_STEPS:
            failures.append(
                f"{d0} -> {d1}: karana index jumped {k_step} in one day "
                f"({p0.karana_index} -> {p1.karana_index}); the Moon-Sun elongation "
                f"allows only {sorted(KARANA_STEPS)}."
            )

    for label, steps, want, tol in (
        ("yoga", yoga_steps, YOGA_MEAN_RATE, RATE_TOLERANCE),
        ("karana", karana_steps, KARANA_MEAN_RATE, RATE_TOLERANCE),
    ):
        if not steps:
            failures.append(f"{label}: no consecutive-day pairs to measure a rate over")
            continue
        got = sum(steps) / len(steps)
        ok = abs(got - want) <= tol
        print(f"  {'ok  ' if ok else 'FAIL'} {label:<7} mean {got:.4f}/day, "
              f"synodic arithmetic says {want:.4f} (tolerance {tol}), "
              f"steps observed {sorted(set(steps))}")
        if not ok:
            failures.append(
                f"{label} advances {got:.4f} indices/day over {len(steps)} days; the "
                f"synodic month gives {want:.4f}. This gate owes nothing to Drik or to "
                "the naming tables — a wrong divisor, a sign flip or a tropical/"
                "sidereal mix-up all land here."
            )

    yoga_seen = {p.yoga_index for _, p in census}
    karana_seen = {p.karana_index for _, p in census}
    missing_yoga = sorted(set(range(27)) - yoga_seen)
    missing_karana = sorted(set(range(60)) - karana_seen)
    print(f"  {'ok  ' if not missing_yoga else 'FAIL'} coverage yoga   "
          f"{len(yoga_seen)}/27")
    print(f"  {'ok  ' if not missing_karana else 'FAIL'} coverage karana "
          f"{len(karana_seen)}/60")
    if missing_yoga:
        failures.append(
            f"yogas never observed over {CENSUS_START}..{CENSUS_END}: "
            f"{[EXPECTED_YOGA_NAMES[i] for i in missing_yoga]}. All 27 occur roughly "
            "monthly, so an unreachable one means the index is not spanning its range."
        )
    if missing_karana:
        failures.append(
            f"karana indices never observed over {CENSUS_START}..{CENSUS_END}: "
            f"{missing_karana}. Every index is reached at some sunrise within two "
            "years; an unreachable one means a branch — most likely one of the four "
            "fixed karanas — is dead code that Gate 2 can never exercise."
        )
    return failures


# --------------------------------------------------------------------------

def gate_4_muhurat_agrees(chart) -> list[str]:
    """The Muhurat Finder must read the same angas /panchang renders (#148).

    `muhurat.py` used to carry its own nitya-yoga and karana implementations —
    a second copy of the same astrology, with its own spellings
    ("Variyan"/"Aindra"/"Chatushpad" against chart.py's
    "Variyana"/"Indra"/"Chatushpada"), and nothing computing over both. They
    agreed only because the sequence order happened to match. That is the same
    shape as #141 and #146: an authoritative-looking value, consumed by a
    shipped feature, with no computation that would disagree if it drifted.

    #148 collapsed muhurat onto chart.py. This gate is what stops it forking
    again — it fails the moment the Muhurat Finder's blocker path stops
    matching the almanac users read.

    Checks both blocker inputs, since those are what actually gate a muhurat:
    the nitya-yoga NAME (Vyatipata/Vaidhriti block) and Bhadra detection
    (Vishti). A spelling drift in either would silently stop a blocker firing.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from astro_ai import muhurat as _m
    from astro_ai.chart import _nitya_yoga_at, _karana_at, julian_day_utc

    failures: list[str] = []
    base = datetime(2026, 1, 1, 6, 0, tzinfo=ZoneInfo("UTC"))
    yoga_seen: set[str] = set()
    karana_seen: set[str] = set()

    for i in range(400):
        when = base + timedelta(hours=i * 7)
        jd = julian_day_utc(when)
        _yi, chart_yoga, _ = _nitya_yoga_at(jd)
        _ki, chart_karana, _ = _karana_at(jd)
        muhurat_yoga, blocks = _m._nitya_yoga_flag(chart, when)
        muhurat_bhadra = _m._bhadra_active_at(chart, when)
        yoga_seen.add(chart_yoga)
        karana_seen.add(chart_karana)

        if muhurat_yoga != chart_yoga:
            failures.append(
                f"{when:%Y-%m-%d %H:%M}Z nitya yoga: muhurat says "
                f"{muhurat_yoga!r}, chart.py says {chart_yoga!r}"
            )
        if blocks != (chart_yoga in {"Vyatipata", "Vaidhriti"}):
            failures.append(
                f"{when:%Y-%m-%d %H:%M}Z blocking flag disagrees with the "
                f"name it was derived from ({chart_yoga!r} -> {blocks})"
            )
        if muhurat_bhadra != (chart_karana == "Vishti"):
            failures.append(
                f"{when:%Y-%m-%d %H:%M}Z Bhadra: muhurat says {muhurat_bhadra}, "
                f"chart.py karana is {chart_karana!r}"
            )

    # A gate that never sees a blocker fire proves nothing about blockers.
    if not {"Vyatipata", "Vaidhriti"} & yoga_seen:
        failures.append(
            "sample window contained no blocking nitya yoga — the blocker "
            "comparison above was never exercised; widen the window"
        )
    if "Vishti" not in karana_seen:
        failures.append(
            "sample window contained no Vishti — Bhadra detection was never "
            "exercised; widen the window"
        )
    return failures


def gate_5_single_pada_impl() -> list[str]:
    """One pada implementation, and nobody recomputes it (#209 QA follow-up).

    Three copies of this arithmetic existed — `chart._pada_of`,
    `matching._moon_pada` and `muhurat._child_moon_pada`. They agreed on every
    real chart, which is exactly why the fork survived: agreement by luck
    reads identical to agreement by design.

    It was not harmless. All three used
    `int((abs_long % (360/27)) / (360/108)) + 1`, which is wrong at every exact
    10-degree multiple (20.0 gives pada 2 where 3 is correct). When #209 fixed
    the boundary it fixed ONE copy. muhurat's copy additionally carried a
    `min(pada, 4)` clamp that hid the out-of-range symptom while still
    shipping the wrong pada.

    This gate fails if a caller reintroduces its own arithmetic, and if the
    three ever disagree on a real chart.
    """
    import ast
    import inspect
    import textwrap
    from datetime import date, timedelta
    from astro_ai import matching as _m, muhurat as _mu
    from astro_ai.chart import compute_chart, _pada_of

    failures: list[str] = []

    # 1. no caller may recompute the pada itself
    # Inspect the EXECUTABLE body only. A first version string-matched the
    # whole source and failed on the docstrings, which quote the old formula
    # in order to explain why it was removed — a gate that punishes
    # documenting the bug it guards would get the documentation deleted.
    for label, fn in (("matching._moon_pada", _m._moon_pada),
                      ("muhurat._child_moon_pada", _mu._child_moon_pada)):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        func = tree.body[0]
        stmts = list(func.body)
        if (stmts and isinstance(stmts[0], ast.Expr)
                and isinstance(stmts[0].value, ast.Constant)
                and isinstance(stmts[0].value.value, str)):
            stmts = stmts[1:]          # drop the docstring
        # Assert the INVARIANT, not a list of spellings. A first version
        # string-matched markers like "360 / 27" and was defeated by a
        # bite-test that wrote "360.0 / 27.0" — the very form the original
        # fork used. These functions are field reads; any arithmetic in them
        # is a recomputation by definition, whatever it looks like.
        arithmetic = [
            ast.unparse(node) for node in ast.walk(ast.Module(body=stmts, type_ignores=[]))
            if isinstance(node, ast.BinOp)
            and isinstance(node.op, (ast.Div, ast.Mult, ast.Mod, ast.FloorDiv))
        ]
        for expr in arithmetic:
            failures.append(
                f"{label} recomputes the pada — arithmetic {expr!r} in its "
                f"body. Read PlanetPosition.pada instead."
            )
        reads_field = any(
            isinstance(node, ast.Attribute) and node.attr == "pada"
            for node in ast.walk(ast.Module(body=stmts, type_ignores=[]))
        )
        if not reads_field:
            failures.append(f"{label} never reads .pada — is it still delegating?")

    # 2. the boundary the fork got wrong
    for deg, want in ((10.0, 4), (20.0, 3), (30.0, 2), (40.0, 1)):
        got = _pada_of(deg)
        if got != want:
            failures.append(f"_pada_of({deg}) = {got}, expected {want}")

    # 3. all three agree on real charts, and stay in range
    d = date(1970, 1, 1)
    checked = 0
    while d < date(2005, 1, 1):
        try:
            c = compute_chart(d.isoformat(), "10:30", CITY)
            moon = next(p for p in c.planets if p.name == "Moon")
            a = _m._moon_pada(moon)
            _nak, b = _mu._child_moon_pada(c)
            checked += 1
            if not (a == b == moon.pada):
                failures.append(
                    f"{d}: pada disagrees — matching={a} muhurat={b} "
                    f"PlanetPosition={moon.pada}"
                )
            if not 1 <= moon.pada <= 4:
                failures.append(f"{d}: pada {moon.pada} out of range 1-4")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{d}: {type(exc).__name__}: {exc}")
        d += timedelta(days=97)
    if checked < 50:
        failures.append(f"only {checked} charts exercised — gate is too thin to trust")
    return failures


# --------------------------------------------------------------------------
# Gate 6 - a date with no daylight span must be flagged, not divided (#227)
# --------------------------------------------------------------------------

# Tromso, as OpenStreetMap/Nominatim resolves the bare string "Tromso". The
# exact point is not the claim — what matters is that it is north of the
# Arctic Circle (66.56N), so some dates hold no ordinary sunrise-to-sunset
# span at all. Coordinates are pinned here rather than geocoded because this
# gate must run with no network: outbound geocoding is blocked in most
# sandboxes, and a gate that cannot run is a gate that never fails.
POLAR_CITY = "Tromso"
POLAR_LAT, POLAR_LON, POLAR_TZ = 69.6492, 18.9553, "Europe/Oslo"
POLAR_YEAR = 2026

# Sub-second slack: the window bounds are float-second timedeltas off sunrise,
# so the last Rahu Kaal segment can end a few microseconds past sunset.
_SLACK = timedelta(seconds=1)


def _stubbed_chart(place: str, lat: float, lon: float, tz: str):
    """A chart at pinned coordinates with `geocode_place` stubbed.

    No network, by design: outbound geocoding is blocked in most sandboxes, and
    a gate that cannot run is a gate that never fails.
    """
    from astro_ai import chart as _chart_module
    real = _chart_module.geocode_place
    _chart_module.geocode_place = lambda _place: (lat, lon, tz)
    try:
        return compute_chart("2000-01-01", "12:00", place)
    finally:
        _chart_module.geocode_place = real


def _polar_chart():
    """A chart at Tromso with `geocode_place` stubbed — no network, by design."""
    return _stubbed_chart(POLAR_CITY, POLAR_LAT, POLAR_LON, POLAR_TZ)


def _windows_are_wellformed(day: date, p) -> list[str]:
    """Complaints about `p`'s daylight-derived windows, ignoring the flag.

    Deliberately says nothing about how `daylight_ordinary` is DEFINED — it
    checks the consequence instead. Restating the flag's own condition here
    would make the gate a tautology that passes forever, which is the failure
    `scripts/mutate_behaviour_suite.py` was written to catch.
    """
    bad: list[str] = []
    if p.sunset <= p.sunrise:
        bad.append(f"sunset {p.sunset:%d %H:%M:%S} is not after sunrise {p.sunrise:%d %H:%M:%S}")
    if p.sunrise.date() != day or p.sunset.date() != day:
        bad.append(f"sunrise/sunset fall outside {day} ({p.sunrise.date()} / {p.sunset.date()})")
    for label, start, end in (
        ("rahu kaal", p.rahu_kaal_start, p.rahu_kaal_end),
        ("abhijit", p.abhijit_start, p.abhijit_end),
    ):
        if end <= start:
            bad.append(f"{label} {start:%H:%M:%S}..{end:%H:%M:%S} ends before it starts")
        if start < p.sunrise - _SLACK or end > p.sunset + _SLACK:
            bad.append(f"{label} {start:%H:%M:%S}..{end:%H:%M:%S} escapes daylight")
    return bad


def gate_6_polar_daylight(census: list[tuple[date, object]]) -> list[str]:
    """A date with no sunrise-to-sunset span must be FLAGGED, never divided (#227).

    Rahu Kaal is a weekday-indexed eighth of daylight and Abhijit a fifteenth
    of it (`knowledge/vedic_reference.md` §28); Choghadiya divides the same
    span into eight. North of the Arctic Circle a calendar date can hold no
    such span — `_rise_or_set` anchors at local midnight, so the first set it
    finds can be the tail of the previous solar day and land BEFORE the rise.
    The eighths and fifteenths are then negative and every window ends before
    it starts.

    That did not raise and did not degrade. `/panchang` took `?city=` as free
    text and rendered it at 200 OK: Tromso 2026-05-17 showed "Sunrise/Sunset
    01:14 — 00:06", "Rahu Kaal 00:14 — 00:06" and a choghadiya counting
    downwards, with nothing on the page to say it was wrong. Measured
    2026-08-26 over the 365 days of 2026 at Tromso: 117 raise before reaching
    here (no rise or no set at all — a separate, LOUD path the route degrades),
    5 reach here without an ordinary span (2026-05-16, 05-17, 07-26, 07-27,
    07-28) and 243 are ordinary.

    Those five dates are recorded as history, not as the assertion — an
    ephemeris update may legitimately move them. What is asserted is the tie
    between the flag and its consequence, in both directions:

      * every day the flag calls ordinary must have well-formed windows, and
      * every day it does not must have at least one malformed one.

    So the gate goes red if the flag is dropped, inverted, hardcoded, or
    narrowed to only half the shapes. The New Delhi census is included as the
    control: a guard that flags a shipping locale is as broken as one that
    misses Tromso.
    """
    failures: list[str] = []
    try:
        chart = _polar_chart()
    except Exception as exc:  # noqa: BLE001
        return [f"could not build the stubbed {POLAR_CITY} chart: "
                f"{type(exc).__name__}: {exc}"]

    flagged: list[date] = []
    ordinary = 0
    raised = 0
    day = date(POLAR_YEAR, 1, 1)
    while day.year == POLAR_YEAR:
        try:
            p = _panchang_for(chart, day)
        except Exception:  # noqa: BLE001  — the loud path; #227 is the quiet one
            raised += 1
            day += timedelta(days=1)
            continue
        bad = _windows_are_wellformed(day, p)
        if p.daylight_ordinary:
            ordinary += 1
            for line in bad:
                failures.append(
                    f"{POLAR_CITY} {day}: daylight_ordinary=True but {line} — "
                    "the page will render this window as if it were real"
                )
        else:
            flagged.append(day)
            if not bad:
                failures.append(
                    f"{POLAR_CITY} {day}: daylight_ordinary=False on an ordinary "
                    "day (sunrise..sunset and every window is well-formed) — "
                    "the page will withhold windows it could have shown"
                )
        day += timedelta(days=1)

    # A gate that never sees the defect proves nothing about the defect.
    if not flagged:
        failures.append(
            f"no day in {POLAR_YEAR} at {POLAR_CITY} was flagged — either the "
            "flag is hardcoded True or the coordinates stopped being polar; "
            "either way the check above never ran"
        )
    if not ordinary:
        failures.append(
            f"every computable day in {POLAR_YEAR} at {POLAR_CITY} was flagged — "
            "the flag is hardcoded False and disclosure would swallow the "
            "243 days that are perfectly ordinary"
        )

    # Control: the shipping locale must be untouched by all of this.
    for day, p in census:
        bad = _windows_are_wellformed(day, p)
        if bad:
            failures.append(f"{CITY} {day}: {bad[0]}")
        if not p.daylight_ordinary:
            failures.append(
                f"{CITY} {day}: daylight_ordinary=False at an Indian latitude — "
                "the disclosure is firing where there is nothing to disclose"
            )

    print(f"  {POLAR_CITY} {POLAR_YEAR}: {raised} raised, {len(flagged)} flagged "
          f"({', '.join(str(d) for d in flagged) or 'none'}), {ordinary} ordinary")
    print(f"  {CITY}: {len(census)} census day(s), all ordinary and well-formed"
          if not failures else f"  {CITY}: control had problems, see above")
    return failures


# --------------------------------------------------------------------------
# Gate 7 - moonrise/moonset are computable, bounded, and absent where they
#          should be (#150)
# --------------------------------------------------------------------------

# Reykjavik, at 64.15N — SOUTH of the Arctic Circle, which is the point. The
# Sun has an ordinary rise and set on most of its days, and the Moon does not:
# the Moon's path is inclined ~5.1deg to the ecliptic, so it goes circumpolar
# at latitudes where the Sun never does. Pinned, not geocoded, for the same
# reason as POLAR_* above.
SUBPOLAR_CITY = "Reykjavik"
SUBPOLAR_LAT, SUBPOLAR_LON, SUBPOLAR_TZ = 64.1466, -21.9426, "Atlantic/Reykjavik"


def _moon_for(chart, day: date):
    """(moonrise, moonset) for `day`, anchored at local noon like the route."""
    tz = ZoneInfo(chart.birth_tz)
    return compute_moon_rise_set(
        chart, when=datetime(day.year, day.month, day.day, 12, 0, tzinfo=tz)
    )


def _moon_census(chart, year: int) -> dict:
    """Every day of `year`: what `compute_moon_rise_set` gave and where it fell."""
    tz = ZoneInfo(chart.birth_tz)
    out = {"raised": [], "outside": [], "moonless": [], "partial": [],
           "next_day": [], "both_today": 0, "max_hours": 0.0, "max_at": None}
    day = date(year, 1, 1)
    while day.year == year:
        try:
            rise, set_ = _moon_for(chart, day)
        except Exception as exc:  # noqa: BLE001
            out["raised"].append((day, f"{type(exc).__name__}: {exc}"))
            day += timedelta(days=1)
            continue
        if rise is None and set_ is None:
            out["moonless"].append(day)
        elif rise is None or set_ is None:
            out["partial"].append(day)
        midnight = datetime(day.year, day.month, day.day, tzinfo=tz)
        for label, instant in (("moonrise", rise), ("moonset", set_)):
            if instant is None:
                continue
            hours = (instant - midnight).total_seconds() / 3600.0
            if hours > out["max_hours"]:
                out["max_hours"], out["max_at"] = hours, (day, label, instant)
            if not 0.0 <= hours < 48.0:
                out["outside"].append((day, label, instant, hours))
            elif instant.date() != day:
                out["next_day"].append((day, label, instant))
        if rise is not None and set_ is not None \
                and rise.date() == day and set_.date() == day:
            out["both_today"] += 1
        day += timedelta(days=1)
    return out


def gate_7_moon_rise_set() -> list[str]:
    """`compute_moon_rise_set` is REACHED, and every shape it returns is one
    the page can render honestly (#150).

    This function shipped with two comments about it and zero callers — the
    #140 shape, where the code exists and nothing reaches it. `/panchang` calls
    it now, and the three shapes it returns are all irregular by the standards
    of the sunrise card next to it:

      * a next-day instant. Successive moonrises are ~24h50m apart, so a
        calendar date can hold none of its own and the first one after midnight
        is on D+1 — 13 of 365 New Delhi days in 2026. The page prints the DATE
        on those, and that is only sound if an instant is never further out
        than D+1, which is what this gate pins.
      * `None` for one of the two.
      * `None` for both — the Moon's own polar case. It is NOT
        `daylight_ordinary`, which is about the Sun (see its comment in
        `chart.py`), and it fires far more often and far further south.

    Asserted, in both directions, so a hardcoded answer goes red either way:

      * nothing raises anywhere, at any of the three latitudes;
      * every instant returned lies in [local midnight D, local midnight D+2),
        because "not this date" must mean "tomorrow" for the label to be true;
      * at New Delhi the Moon always rises AND always sets — absence must never
        fire at an Indian latitude, the same control Gate 6 uses;
      * at New Delhi the next-day case DOES occur, or the date-labelling branch
        is dead code that nothing exercises;
      * at both northern cities the moonless case DOES occur, or the disclosure
        branch is unreachable and untested;
      * the Moon's absence and the Sun's flag are INDEPENDENT — there is a date
        with no ordinary daylight span and a real moonrise (Tromso 2026-05-16,
        moonrise 00:36), and dates with ordinary daylight and no moon at all.
        Deriving one flag from the other would collapse one of the two.

    Counts measured 2026-08-27 over the 365 days of 2026 and printed below, not
    asserted — an ephemeris update may legitimately move them: New Delhi 340
    days with both instants inside the date and 25 instants on D+1 (13
    moonrises, 12 moonsets), 0 moonless; Reykjavik 88 moonless; Tromso 166.
    What is asserted is the shape.
    """
    failures: list[str] = []
    try:
        delhi = _stubbed_chart(CITY, 28.6139, 77.2090, "Asia/Kolkata")
        tromso = _polar_chart()
        reykjavik = _stubbed_chart(
            SUBPOLAR_CITY, SUBPOLAR_LAT, SUBPOLAR_LON, SUBPOLAR_TZ)
    except Exception as exc:  # noqa: BLE001
        return [f"could not build the stubbed charts: {type(exc).__name__}: {exc}"]

    censuses = {CITY: _moon_census(delhi, POLAR_YEAR),
                POLAR_CITY: _moon_census(tromso, POLAR_YEAR),
                SUBPOLAR_CITY: _moon_census(reykjavik, POLAR_YEAR)}

    for name, c in censuses.items():
        for day, exc in c["raised"][:5]:
            failures.append(
                f"{name} {day}: compute_moon_rise_set raised {exc} — absence is "
                "signalled by None, so a raise means the return flag stopped "
                "being checked and JD 0.0 reached datetime"
            )
        for day, label, instant, hours in c["outside"][:5]:
            failures.append(
                f"{name} {day}: {label} {instant:%Y-%m-%d %H:%M} is {hours:.2f}h "
                "past local midnight — the page labels anything not on the page's "
                "own date as the NEXT day, which that is not"
            )

    delhi_c = censuses[CITY]
    for day in delhi_c["moonless"][:3]:
        failures.append(
            f"{CITY} {day}: no moonrise AND no moonset at an Indian latitude — "
            "the page will show its polar disclosure where there is nothing to "
            "disclose"
        )
    for day in delhi_c["partial"][:3]:
        failures.append(
            f"{CITY} {day}: only one of moonrise/moonset — not expected at this "
            "latitude; the page will say the other does not happen"
        )
    if not delhi_c["next_day"]:
        failures.append(
            f"no day in {POLAR_YEAR} at {CITY} had an instant on D+1 — either the "
            "midnight anchor was changed or the census stopped running; either "
            "way the date-labelling branch on the page is now untested"
        )

    for name in (POLAR_CITY, SUBPOLAR_CITY):
        if not censuses[name]["moonless"]:
            failures.append(
                f"no day in {POLAR_YEAR} at {name} was moonless — either "
                "the coordinates stopped being northern or absence stopped being "
                "reported, and the page's disclosure branch never runs"
            )

    # Independence from #227's SUN flag, both ways.
    sun_flagged_with_a_moon = 0
    ordinary_sun_no_moon = 0
    day = date(POLAR_YEAR, 1, 1)
    while day.year == POLAR_YEAR:
        try:
            p = _panchang_for(tromso, day)
            rise, set_ = _moon_for(tromso, day)
        except Exception:  # noqa: BLE001 — the loud path Gate 6 already counts
            day += timedelta(days=1)
            continue
        if not p.daylight_ordinary and (rise is not None or set_ is not None):
            sun_flagged_with_a_moon += 1
        if p.daylight_ordinary and rise is None and set_ is None:
            ordinary_sun_no_moon += 1
        day += timedelta(days=1)
    if not sun_flagged_with_a_moon:
        failures.append(
            f"{POLAR_CITY} {POLAR_YEAR}: every date with no ordinary daylight span "
            "also had no moonrise and no moonset — the two flags have been tied "
            "together, and the page will withhold a moonrise that exists "
            "(2026-05-16 has one at 00:36)"
        )
    if not ordinary_sun_no_moon:
        failures.append(
            f"{POLAR_CITY} {POLAR_YEAR}: no date had ordinary daylight and no moon "
            "at all — the Moon's absence has been made a consequence of the Sun's, "
            "and the disclosure will never fire on the days that need it"
        )

    for name, c in censuses.items():
        at = c["max_at"]
        print(f"  {name} {POLAR_YEAR}: {c['both_today']} day(s) with both instants "
              f"inside the date, {len(c['next_day'])} on D+1, "
              f"{len(c['partial'])} with one absent, {len(c['moonless'])} with "
              f"neither, {len(c['raised'])} raised; furthest instant "
              f"{c['max_hours']:.2f}h past local midnight"
              + (f" ({at[0]} {at[1]} {at[2]:%d %b %H:%M})" if at else ""))
    print(f"  {POLAR_CITY}: {sun_flagged_with_a_moon} date(s) with no daylight span "
          f"but a real moon instant, {ordinary_sun_no_moon} with ordinary daylight "
          "and no moon — the two flags are independent")
    return failures


def main() -> int:
    print("Panchang anga verification — Nitya Yoga + Karana (issue #142)")
    print("  computation : src/astro_ai/chart.py compute_panchang()")
    print(f"  locale      : {CITY}, values taken at LOCAL SUNRISE")
    print(f"  almanac     : drikpanchang.com day pages, fetched 2026-08-07, "
          f"{len(ALMANAC)} dates (URLs in ALMANAC)")
    print(f"  census      : {CENSUS_START}..{CENSUS_END}")
    print()

    try:
        chart = compute_chart("2000-01-01", "12:00", CITY)
    except Exception as exc:
        print(f"FAIL — could not build a chart for {CITY}: "
              f"{type(exc).__name__}: {exc}")
        return 1

    census: list[tuple[date, object]] = []
    day = CENSUS_START
    census_errors: list[str] = []
    while day <= CENSUS_END:
        try:
            census.append((day, _panchang_for(chart, day)))
        except Exception as exc:
            census_errors.append(f"{day}: {type(exc).__name__}: {exc}")
        day += timedelta(days=1)

    gates = [
        ("Gate 1 - the verified almanac table (drikpanchang.com, New Delhi)",
         lambda: gate_1_almanac(chart)),
        ("Gate 2 - structural invariants over a two-year census",
         lambda: gate_2_structure(census)),
        ("Gate 3 - rate and coverage (synodic arithmetic, no almanac)",
         lambda: gate_3_rate_and_coverage(census)),
        ("Gate 4 - the Muhurat Finder reads the same angas (#148)",
         lambda: gate_4_muhurat_agrees(chart)),
        ("Gate 5 - one pada implementation, no recomputation (#209)",
         gate_5_single_pada_impl),
        ("Gate 6 - polar dates are flagged, not divided (#227)",
         lambda: gate_6_polar_daylight(census)),
        ("Gate 7 - moonrise/moonset: reached, bounded, absent where it should be (#150)",
         gate_7_moon_rise_set),
    ]

    all_failures: list[str] = list(census_errors)
    if census_errors:
        print(f"Census build raised on {len(census_errors)} day(s) — every day in "
              "range must compute:")
        for line in census_errors[:10]:
            print(f"  FAIL: {line}")
        print()

    results: list[tuple[str, int]] = []
    for title, run in gates:
        print(title)
        failures = run()
        for line in failures[:20]:
            print(f"  FAIL: {line}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
        print()
        results.append((title, len(failures)))
        all_failures.extend(failures)

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s). Do not adjust the computation "
              "to silence a gate, and never re-derive an expected value from this "
              "codebase — read the almanac page whose URL is recorded next to the row.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
