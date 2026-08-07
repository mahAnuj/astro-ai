#!/usr/bin/env python3
"""Verify the shipped festival dates against the checked-in expected table.

WHY THIS EXISTS
---------------
`festivals.py` once shipped 9 of 17 dates for 2026 wrong — by up to 21 days —
under a module header that claimed a source provenance the dates did not
actually have. The worst pair: Karva Chauth on 2026-11-05 and Diwali on
2026-11-08, three days apart, when the tithi count between them (Kartika
Krishna Chaturthi to Kartika Amavasya, 11 tithis) makes 10-11 days the only
possible answer. Nothing in the codebase could have noticed.

This script is that missing check: one command, zero judgment, PASS/FAIL,
exit 0 or 1. It runs five independent gates.

  Gate 1 - exact date match.  Every festival in `festival_registry.FESTIVALS`
      must appear in tests/festival_dates_expected.json with byte-identical
      ISO dates for every shipped year. The JSON is a machine copy of the
      verified dataset; the registry is a hand transcription of the same
      data, so the diff catches transcription slips. Primary gate.

  Gate 2 - tithi-interval consistency.  Pure arithmetic on the dates: pairs
      of festivals whose classical rules fix the tithi count between them
      must fall the corresponding number of days apart. Deliberately no
      ephemeris dependency — a QA machine with no ephemeris library installed
      must still run this gate rather than silently skip it. This gate catches
      the 2026 bug on its own.

  Gate 3 - year-over-year lunar drift.  After normalising for Gregorian year
      length, a tithi-based festival moves -13..-9 days per year, or +17..+21
      in a year an adhik maas (intercalary month) intervenes. Anything else
      is a whole-month error. Gate 1 cannot see such an error if the expected
      table and the registry share the same typo; Gate 3 can, because it
      checks each source against astronomy rather than against the other.
      Gates 2 and 3 therefore run over BOTH sources independently.

  Gate 4 - lookup reachability.  Every festival in the registry must come back
      out of `festivals.festivals_for_date()` on its own date, for every
      shipped year. The by-date index used to map one date to ONE festival, so
      a second festival on the same day was silently dropped — Pongal behind
      Makar Sankranti, Hartalika Teej behind Ganesh Chaturthi, Narak
      Chaturdashi behind Diwali. The date was right in the registry and wrong
      on the site, which no date gate can see. This gate proves the round trip.
      Shared dates are printed for information; they are legitimate, not a
      failure. Only an unreachable festival fails.

  Gate 5 - ordering primacy on a shared date.  Gate 4 proves both festivals on
      a shared date are reachable; it does not care which of them comes first.
      Which one comes first is what the daily rashifal email, the welcome email
      and the rashifal LLM prompt actually print, because they call
      `festival_for_date()` and it returns entry zero. That choice used to rest
      entirely on where a row sat in the `FESTIVALS` tuple — invisible in a
      diff and destroyed by any re-sort or a row inserted in the wrong place,
      with no test anywhere that would go red. `Festival.priority` now carries
      it, and this gate holds it to a hard-coded table of expected winners
      below: every shared date must be in the table, every table entry must
      still be a shared date, the winner must have a strictly lower priority
      than everything else on that date, and `festival_for_date()` must
      actually return it. A new collision nobody has adjudicated fails here by
      name rather than shipping a silent default.

HOW TO ADD A YEAR
-----------------
1. Verify the new year's dates against drikpanchang.com (New Delhi / IST,
   purnimanta reckoning) AND a computed tithi checked against each festival's
   own observance window — moonrise for Karva Chauth, pradosh for Diwali,
   nishita for Shivratri and Janmashtami, madhyahna for Ram Navami and Ganesh
   Chaturthi, aparahna for Dussehra and Bhai Dooj. Not sunrise for all.
2. In tests/festival_dates_expected.json: add the year to `_meta.years`, its
   source URL to `_meta.source_urls`, its adhik maas windows to
   `_meta.adhik_maas` (empty list if none — 2029 has Adhik Chaitra), and the
   date to every festival's `dates` block.
3. In src/astro_ai/festival_registry.py: add the year to `DATA_YEARS`, to
   `SOURCE_URL_BY_YEAR`, and to every `Festival.dates`.
4. Run this script. Do not adjust a date to make a gate pass — a failing gate
   means the date is wrong, not that the gate is.

Usage:  .venv/bin/python scripts/verify_festivals.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PATH = REPO_ROOT / "tests" / "festival_dates_expected.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import festival_registry  # noqa: E402
from astro_ai import festivals  # noqa: E402


def _parse(iso: str) -> date:
    return date.fromisoformat(iso)


def _anniversary(d: date, year: int) -> date:
    """`d` moved to `year`, same month and day. 29 Feb clamps to 28 Feb."""
    try:
        return date(year, d.month, d.day)
    except ValueError:
        return date(year, 2, 28)


# --------------------------------------------------------------------------
# Gate 1 - exact date match between registry and expected table
# --------------------------------------------------------------------------

def gate_1_exact_dates(expected: dict) -> list[str]:
    failures: list[str] = []

    exp_years = [int(y) for y in expected["_meta"]["years"]]
    reg_years = list(festival_registry.DATA_YEARS)
    if sorted(exp_years) != sorted(reg_years):
        failures.append(
            f"year coverage differs: expected table has {sorted(exp_years)}, "
            f"registry DATA_YEARS has {sorted(reg_years)}"
        )

    exp_fests = expected["festivals"]
    reg_slugs = [f.slug for f in festival_registry.FESTIVALS]

    for slug in reg_slugs:
        if slug not in exp_fests:
            failures.append(f"{slug}: in registry but missing from expected table")
    for slug in exp_fests:
        if slug not in reg_slugs:
            failures.append(f"{slug}: in expected table but missing from registry")

    checked = 0
    for fest in festival_registry.FESTIVALS:
        row = exp_fests.get(fest.slug)
        if row is None:
            continue
        for year in reg_years:
            got = fest.dates.get(year)
            want = row["dates"].get(str(year))
            if want is None:
                failures.append(f"{fest.slug}: no expected date for {year}")
                continue
            if got is None:
                failures.append(f"{fest.slug}: registry has no date for {year} (expected {want})")
                continue
            checked += 1
            if got != want:
                delta = (_parse(got) - _parse(want)).days
                failures.append(
                    f"{fest.slug} {year}: registry has {got}, expected {want} "
                    f"({delta:+d} days off)"
                )

    print(f"  {checked} date(s) compared across {len(reg_slugs)} festival(s) "
          f"x {len(reg_years)} year(s)")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - tithi-interval consistency (arithmetic only, no ephemeris)
# --------------------------------------------------------------------------

def _adhik_windows(expected: dict) -> list[tuple[date, date, str]]:
    out: list[tuple[date, date, str]] = []
    for year, windows in expected["_meta"]["adhik_maas"].items():
        if year.startswith("_"):
            continue
        for start, end, name in windows:
            out.append((_parse(start), _parse(end), name))
    return out


def gate_2_tithi_intervals(
    expected: dict,
    dates_by_source: dict[str, dict[str, dict[int, str]]],
) -> list[str]:
    failures: list[str] = []
    invariants = expected["tithi_interval_invariants"]
    adhik = _adhik_windows(expected)
    years = [int(y) for y in expected["_meta"]["years"]]

    for source, table in dates_by_source.items():
        checked = skipped = 0
        for inv in invariants:
            a, b = inv["a"], inv["b"]
            if a not in table or b not in table:
                skipped += 1
                continue
            for year in years:
                iso_a, iso_b = table[a].get(year), table[b].get(year)
                if not iso_a or not iso_b:
                    skipped += 1
                    continue
                d_a, d_b = _parse(iso_a), _parse(iso_b)
                gap = (d_b - d_a).days
                if not inv["same_lunar_month"]:
                    intervening = [
                        name for start, end, name in adhik
                        if start <= d_b and end >= d_a
                    ]
                    if intervening:
                        skipped += 1
                        continue
                checked += 1
                if not (inv["min_days"] <= gap <= inv["max_days"]):
                    failures.append(
                        f"[{source}] {a} ({iso_a}) -> {b} ({iso_b}) in {year}: "
                        f"{gap} days apart, expected {inv['min_days']}-{inv['max_days']} "
                        f"({inv['tithis']} tithis). {inv['why']}"
                    )
        print(f"  {source}: {checked} interval(s) checked, {skipped} skipped "
              f"(adhik maas / absent festival)")
    return failures


# --------------------------------------------------------------------------
# Gate 3 - year-over-year lunar drift
# --------------------------------------------------------------------------

def gate_3_lunar_drift(
    expected: dict,
    dates_by_source: dict[str, dict[str, dict[int, str]]],
) -> list[str]:
    failures: list[str] = []
    bands = expected["drift_bands"]
    normal_lo, normal_hi = bands["normal"]
    adhik_lo, adhik_hi = bands["adhik_maas"]
    years = sorted(int(y) for y in expected["_meta"]["years"])
    tithi_based = {
        slug for slug, row in expected["festivals"].items() if row["tithi_based"]
    }

    for source, table in dates_by_source.items():
        checked = 0
        for y0, y1 in zip(years, years[1:]):
            observed: list[tuple[date, str, int, str]] = []
            for slug in table:
                if slug not in tithi_based:
                    continue
                iso0, iso1 = table[slug].get(y0), table[slug].get(y1)
                if not iso0 or not iso1:
                    continue
                d0, d1 = _parse(iso0), _parse(iso1)
                drift = (d1 - _anniversary(d0, y1)).days
                checked += 1
                if normal_lo <= drift <= normal_hi:
                    band = "normal"
                elif adhik_lo <= drift <= adhik_hi:
                    band = "adhik"
                else:
                    failures.append(
                        f"[{source}] {slug} {y0}->{y1}: {iso0} -> {iso1} is a "
                        f"{drift:+d} day shift, outside both bands "
                        f"({normal_lo}..{normal_hi} normal, {adhik_lo}..{adhik_hi} "
                        f"adhik maas) — looks like a whole-month error"
                    )
                    band = "out-of-band"
                observed.append((d0, slug, drift, band))

            observed.sort(key=lambda row: (row[0], row[1]))
            sequence = [row[3] for row in observed if row[3] != "out-of-band"]
            changeovers = [
                i for i in range(1, len(sequence)) if sequence[i] != sequence[i - 1]
            ]
            if len(changeovers) > 1:
                failures.append(
                    f"[{source}] {y0}->{y1}: drift bands are not contiguous — "
                    f"{len(changeovers)} changeovers in date order, expected at most 1. "
                    f"An adhik maas falls at one point in the year, so every festival "
                    f"before it shifts one way and every festival after it the other. "
                    "Order: "
                    + ", ".join(f"{s}={b}" for _d, s, _dr, b in observed)
                )
            elif changeovers and sequence[0] != "adhik":
                failures.append(
                    f"[{source}] {y0}->{y1}: drift band changeover runs "
                    f"normal -> adhik in date order; an intervening adhik maas "
                    f"pushes the festivals BEFORE it, so the adhik band must come "
                    "first. Order: "
                    + ", ".join(f"{s}={b}" for _d, s, _dr, b in observed)
                )
            n_adhik = sequence.count("adhik")
            label = (
                f"{y0}->{y1}: {n_adhik} adhik-band, {sequence.count('normal')} normal-band"
                + (", one changeover" if changeovers else ", no changeover")
            )
            print(f"  {source}: {label}")
        print(f"  {source}: {checked} festival-year drift comparison(s) checked")
    return failures


# --------------------------------------------------------------------------
# Gate 4 - lookup reachability (nothing dropped on a shared date)
# --------------------------------------------------------------------------

def gate_4_lookup_reachability() -> list[str]:
    failures: list[str] = []
    years = list(festival_registry.DATA_YEARS)

    shared: dict[date, list[str]] = {}
    checked = 0
    for fest in festival_registry.FESTIVALS:
        for year in years:
            iso = fest.dates.get(year)
            if not iso:
                failures.append(f"{fest.slug}: registry has no date for {year}")
                continue
            try:
                d = _parse(iso)
            except ValueError:
                failures.append(f"{fest.slug} {year}: unparseable date {iso!r}")
                continue
            checked += 1
            entries = festivals.festivals_for_date(d)
            slugs = [e["slug"] for e in entries]
            if fest.slug not in slugs:
                failures.append(
                    f"{fest.slug} {year} ({iso}): registry has this date but "
                    f"festivals_for_date() returns {slugs or '[]'} — the festival is "
                    "silently dropped from the emails and the hub"
                )
            if len(entries) > 1:
                shared[d] = slugs

    for d in sorted(shared):
        print(f"  shared date {d.isoformat()}: {', '.join(shared[d])} "
              f"(festival_for_date -> {shared[d][0]})")
    if not shared:
        print("  no shared dates in the current dataset")

    # The single-slot accessor must agree with the list accessor's first entry,
    # or the email would show a festival the hub does not lead with.
    for fest in festival_registry.FESTIVALS:
        for year in years:
            iso = fest.dates.get(year)
            if not iso:
                continue
            d = _parse(iso)
            entries = festivals.festivals_for_date(d)
            one = festivals.festival_for_date(d)
            if not entries:
                continue
            if one is None or one["slug"] != entries[0]["slug"]:
                failures.append(
                    f"{iso}: festival_for_date() returns "
                    f"{one and one['slug']!r}, festivals_for_date()[0] is "
                    f"{entries[0]['slug']!r} — the two accessors disagree"
                )

    print(f"  {checked} festival-year lookup(s) round-tripped, "
          f"{len(shared)} shared date(s)")
    return failures


# --------------------------------------------------------------------------
# Gate 5 - ordering primacy on a shared date
# --------------------------------------------------------------------------

# Every Gregorian date in the shipped years that carries more than one
# festival, with the winner named explicitly. Written out by hand, not derived
# from the registry, so that a future edit which flips one of these resolutions
# fails here with the pair named instead of quietly changing what the daily
# email says. Adding a festival that lands on an occupied date will also fail
# this gate until the collision is adjudicated and recorded here — which is the
# point: a new shared date is a decision, not a detail.
#
# date -> (winning slug, every slug on that date, why the winner leads)
EXPECTED_SHARED_DATES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "2026-01-14": (
        "makar-sankranti", ("makar-sankranti", "pongal"),
        "same solar moment under two names; the pan-Indian name leads",
    ),
    "2026-09-14": (
        "ganesh-chaturthi", ("ganesh-chaturthi", "hartalika-teej"),
        "Shukla Tritiya and Chaturthi share a sunrise in 2026; Ganesh Chaturthi "
        "is pan-Indian, Hartalika Teej north and central",
    ),
    "2026-11-08": (
        "diwali", ("diwali", "narak-chaturdashi"),
        "pre-dawn Chaturdashi and pradosh Amavasya on one Gregorian day; "
        "Diwali leads any night it falls on",
    ),
    "2027-01-15": (
        "makar-sankranti", ("makar-sankranti", "pongal"),
        "same solar moment under two names; the pan-Indian name leads",
    ),
    "2027-09-04": (
        "ganesh-chaturthi", ("ganesh-chaturthi", "rishi-panchami"),
        "Shukla Panchami begins at 12:30 IST, inside the same madhyahna that "
        "Shukla Chaturthi still holds; Ganesh Chaturthi is pan-Indian and the "
        "larger day by far, Rishi Panchami the vrat kept alongside it",
    ),
    "2028-01-15": (
        "makar-sankranti", ("makar-sankranti", "pongal"),
        "same solar moment under two names; the pan-Indian name leads",
    ),
    "2028-10-17": (
        "diwali", ("diwali", "narak-chaturdashi"),
        "pre-dawn Chaturdashi and pradosh Amavasya on one Gregorian day; "
        "Diwali leads any night it falls on",
    ),
}


def gate_5_ordering_primacy() -> list[str]:
    failures: list[str] = []
    years = list(festival_registry.DATA_YEARS)
    priority_of = {
        f.slug: getattr(f, "priority", 100) for f in festival_registry.FESTIVALS
    }

    actual: dict[str, list[str]] = {}
    for fest in festival_registry.FESTIVALS:
        for year in years:
            iso = fest.dates.get(year)
            if iso:
                actual.setdefault(iso, []).append(fest.slug)
    actual = {iso: slugs for iso, slugs in actual.items() if len(slugs) > 1}

    for iso in sorted(actual):
        if iso not in EXPECTED_SHARED_DATES:
            failures.append(
                f"{iso}: {', '.join(actual[iso])} share this date, but it is not "
                "in EXPECTED_SHARED_DATES — a new collision has appeared and "
                "nobody has said which festival the daily email should lead with. "
                "Set `priority` on both rows and add the date to the table."
            )
    for iso in sorted(EXPECTED_SHARED_DATES):
        if iso not in actual:
            failures.append(
                f"{iso}: EXPECTED_SHARED_DATES names this a shared date but the "
                "registry no longer has two festivals on it — a date moved. "
                "Re-verify against the almanac before touching this table."
            )

    checked = 0
    for iso in sorted(EXPECTED_SHARED_DATES):
        want_winner, want_slugs, why = EXPECTED_SHARED_DATES[iso]
        got_slugs = actual.get(iso)
        if got_slugs is None:
            continue
        checked += 1

        if sorted(got_slugs) != sorted(want_slugs):
            failures.append(
                f"{iso}: expected {sorted(want_slugs)} on this date, registry has "
                f"{sorted(got_slugs)} — the pair itself changed, so the recorded "
                "resolution no longer applies"
            )
            continue

        # The winner must win on `priority`, strictly. A tie means the outcome is
        # still being decided by tuple position, which is the thing this gate exists
        # to stop being load-bearing.
        winner_priority = priority_of[want_winner]
        ties = [
            s for s in got_slugs
            if s != want_winner and priority_of[s] <= winner_priority
        ]
        if ties:
            failures.append(
                f"{iso}: {want_winner} (priority {winner_priority}) does not "
                f"strictly outrank "
                + ", ".join(f"{s} (priority {priority_of[s]})" for s in ties)
                + " — the shared date is being resolved by declaration order "
                "again, not by priority. Expected winner: "
                f"{want_winner} — {why}"
            )

        entries = festivals.festivals_for_date(_parse(iso))
        got_order = [e["slug"] for e in entries]
        if not got_order:
            failures.append(f"{iso}: festivals_for_date() returned nothing")
            continue
        if got_order[0] != want_winner:
            failures.append(
                f"{iso}: festivals_for_date() leads with {got_order[0]!r}, expected "
                f"{want_winner!r} — the daily email, the welcome email and the "
                f"rashifal prompt would all announce the wrong festival. {why}"
            )
        one = festivals.festival_for_date(_parse(iso))
        if one is None or one["slug"] != want_winner:
            failures.append(
                f"{iso}: festival_for_date() returns {one and one['slug']!r}, "
                f"expected {want_winner!r} — this is the exact value that goes "
                "into the daily rashifal email"
            )
        print(f"  {iso}: {' > '.join(got_order)} "
              f"(priorities {', '.join(str(priority_of[s]) for s in got_order)})")

    print(f"  {checked} shared date(s) checked against a table of "
          f"{len(EXPECTED_SHARED_DATES)}")
    return failures


# --------------------------------------------------------------------------

def _registry_dates() -> dict[str, dict[int, str]]:
    return {f.slug: dict(f.dates) for f in festival_registry.FESTIVALS}


def _expected_dates(expected: dict) -> dict[str, dict[int, str]]:
    return {
        slug: {int(y): iso for y, iso in row["dates"].items()}
        for slug, row in expected["festivals"].items()
    }


def main() -> int:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    meta = expected["_meta"]

    print("Festival date verification")
    print(f"  expected table : {EXPECTED_PATH.relative_to(REPO_ROOT)}")
    print("  registry       : src/astro_ai/festival_registry.py")
    print(f"  source         : {meta['source_name']}, {meta['source_locale']}, "
          f"verified {meta['verified_on']}")
    print()

    dates_by_source = {
        "registry": _registry_dates(),
        "expected": _expected_dates(expected),
    }

    gates = [
        ("Gate 1 - exact date match (registry vs expected table)",
         lambda: gate_1_exact_dates(expected)),
        ("Gate 2 - tithi-interval consistency (arithmetic, no ephemeris)",
         lambda: gate_2_tithi_intervals(expected, dates_by_source)),
        ("Gate 3 - year-over-year lunar drift",
         lambda: gate_3_lunar_drift(expected, dates_by_source)),
        ("Gate 4 - lookup reachability (nothing dropped on a shared date)",
         gate_4_lookup_reachability),
        ("Gate 5 - ordering primacy (the right festival leads a shared date)",
         gate_5_ordering_primacy),
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
        print(f"FAIL — {len(all_failures)} problem(s). Do not adjust a date to silence "
              "a gate; verify against the almanac first.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
