#!/usr/bin/env python3
"""Verify the computed lunar observances (Purnima / Amavasya / Ekadashi).

WHY THIS EXISTS
---------------
`lunar_observances.py` computes ~50 rows a year from the ephemeris instead of
tabulating them, so no human ever reads the list. That makes one specific bug
invisible: a **kshaya** tithi begins after one sunrise and ends before the next,
so no sunrise falls inside it, and a naive sunrise scan does not mislabel it —
it **drops it silently**. The output is one row short and looks entirely normal.
Nobody reviewing a wall of 50 dates notices that February has no Purnima.

The mirror-image case is **vriddhi**, a tithi spanning two sunrises and so
offering two candidate days; picking the wrong one shifts a fast by a day.

This script is the gate for both. One command, zero judgment, PASS/FAIL,
exit 0 or 1. It is deliberately structured like `scripts/verify_festivals.py`.

  Gate A - structural invariants.  Pure structure over the computed output:
      Purnima and Amavasya strictly alternate, same-kind gaps are one synodic
      month, P->A gaps are 13-17 days, every lunation carries exactly one
      Purnima, one Amavasya and exactly two Ekadashis (one Shukla before the
      Purnima, one Krishna after), dates are strictly monotonic per kind and no
      (kind, date) repeats.  The alternation + one-per-lunation checks are what
      catch a dropped kshaya day. Do not weaken them.

  Gate B - cross-check against the hand-verified registry.  Every festival in
      `festival_registry` whose classical rule is a Purnima or an Amavasya must
      land on a computed one. This is the gate that ties the computed engine to
      Drik-sourced, human-verified dates: those registry rows were verified
      against drikpanchang.com on 2026-08-06/07.

      The allowed offset comes from the festival's own `observance_window`,
      which the registry already declares, and which its module header (lines
      10-13) says each date was verified against "rather than against sunrise
      alone". A festival reckoned at *sunrise* must fall exactly on the computed
      day. A festival reckoned at any *later* window — pradosh, aparahna,
      nishita, moonrise — may fall one day EARLIER, never later: a tithi running
      at dusk on day X either was already running at sunrise on X (offset 0) or
      is still running at sunrise on X+1 (offset -1), and there is no third
      case. Diwali is the textbook instance (Kartika Amavasya at pradosh) but it
      is not special-cased; Sharad Purnima at moonrise and Mahalaya at aparahna
      behave identically. `holi` is the one rule-level exception: it is the day
      AFTER the pradosh-reckoned Phalguna Purnima, so the computed Purnima must
      be its date or its date minus one.

      The direction of the tolerance is the whole point — widening it both ways
      would let a genuinely wrong date pass. Every pairing prints its signed
      offset, computed MINUS festival: a later-window festival may be 0 or +1
      (it never falls after the computed sunrise day), a sunrise festival must
      be 0, and `holi` must be -1 or 0.

  Gate C - edge-case census.  Prints every vriddhi and kshaya occurrence in
      range, re-deriving them from the sunrise samples independently of the
      engine's own bookkeeping. Fails if either exceeds 8 per year — a spike
      means the algorithm broke, not that astronomy changed.

  Gate D - slug uniqueness and registry collisions.  Slugs are HTML ids and
      anchor targets on the /festivals hub, so a duplicate breaks anchors
      silently. Dates shared with a `festival_registry` festival are printed for
      information; they are expected (Guru Purnima IS a Purnima), not failures.

Note the counts printed by Gate A are OUTPUT, not targets. If a count disagrees
with what you expected, report the disagreement — do not tune the engine to hit
a number, and do not adjust the sunrise rule to make one date match.

Usage:  uv run python scripts/verify_lunar_observances.py
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import festival_registry  # noqa: E402
from astro_ai import lunar_observances as lo  # noqa: E402

YEARS = list(festival_registry.DATA_YEARS)
SPAN_START = date(min(YEARS), 1, 1)
SPAN_END = date(max(YEARS), 12, 31)


def _kind(slug: str) -> str:
    return slug.split("-", 1)[0]


def _rows() -> list[tuple[date, lo.Observance]]:
    return lo.observances_between(SPAN_START, SPAN_END)


# --------------------------------------------------------------------------
# Gate A - structural invariants
# --------------------------------------------------------------------------

def gate_a_structure(rows: list[tuple[date, lo.Observance]]) -> list[str]:
    failures: list[str] = []

    for year in YEARS:
        counts = Counter(_kind(o.slug) for d, o in rows if d.year == year)
        print(f"  {year}: {counts.get('purnima', 0)} Purnima, "
              f"{counts.get('amavasya', 0)} Amavasya, "
              f"{counts.get('ekadashi', 0)} Ekadashi")

    # Strictly monotonic per kind, no duplicate (kind, date).
    seen: set[tuple[str, date]] = set()
    last_by_kind: dict[str, date] = {}
    for d, o in rows:
        key = (_kind(o.slug), d)
        if key in seen:
            failures.append(f"duplicate (kind, date): {key[0]} on {d.isoformat()}")
        seen.add(key)
        prev = last_by_kind.get(key[0])
        if prev is not None and d <= prev:
            failures.append(
                f"{key[0]} dates not strictly increasing: {d.isoformat()} "
                f"follows {prev.isoformat()}"
            )
        last_by_kind[key[0]] = d

    pa = [(d, _kind(o.slug)) for d, o in rows if _kind(o.slug) in ("purnima", "amavasya")]
    pa.sort()

    # Strict alternation. Two of the same kind in a row is exactly what a
    # dropped kshaya day looks like.
    for (d0, k0), (d1, k1) in zip(pa, pa[1:]):
        if k0 == k1:
            failures.append(
                f"{k0} does not alternate: {d0.isoformat()} then {d1.isoformat()} "
                f"— a full/new moon between them was dropped (kshaya?)"
            )
        gap = (d1 - d0).days
        if not (13 <= gap <= 17):
            failures.append(
                f"{k0} {d0.isoformat()} -> {k1} {d1.isoformat()}: {gap} days apart, "
                f"expected 13-17 (half a synodic month)"
            )

    # Same-kind gap is one synodic month. Catches two adjacent drops, which
    # alternation alone would not see.
    for kind in ("purnima", "amavasya"):
        seq = [d for d, k in pa if k == kind]
        for d0, d1 in zip(seq, seq[1:]):
            gap = (d1 - d0).days
            if not (28 <= gap <= 32):
                failures.append(
                    f"{kind} {d0.isoformat()} -> {d1.isoformat()}: {gap} days apart, "
                    f"expected 28-32 (one synodic month) — a lunation is missing one"
                )

    # Every lunation contributes exactly one Purnima and exactly two Ekadashis,
    # ordered Amavasya < Shukla Ekadashi < Purnima < Krishna Ekadashi < Amavasya.
    amavasyas = [d for d, k in pa if k == "amavasya"]
    lunations = 0
    for a0, a1 in zip(amavasyas, amavasyas[1:]):
        inside = [(d, o) for d, o in rows if a0 < d < a1]
        purnimas = [d for d, o in inside if _kind(o.slug) == "purnima"]
        ekadashis = [(d, o) for d, o in inside if _kind(o.slug) == "ekadashi"]
        lunations += 1
        if len(purnimas) != 1:
            failures.append(
                f"lunation {a0.isoformat()}..{a1.isoformat()}: "
                f"{len(purnimas)} Purnima(s), expected exactly 1 "
                f"({[d.isoformat() for d in purnimas]})"
            )
        if len(ekadashis) != 2:
            failures.append(
                f"lunation {a0.isoformat()}..{a1.isoformat()}: "
                f"{len(ekadashis)} Ekadashi(s), expected exactly 2 "
                f"({[d.isoformat() for d, _ in ekadashis]})"
            )
            continue
        (d_first, o_first), (d_second, o_second) = ekadashis
        if "waxing" not in o_first.rule:
            failures.append(
                f"lunation {a0.isoformat()}..{a1.isoformat()}: first Ekadashi "
                f"{d_first.isoformat()} is not Shukla ({o_first.rule!r})"
            )
        if "waning" not in o_second.rule:
            failures.append(
                f"lunation {a0.isoformat()}..{a1.isoformat()}: second Ekadashi "
                f"{d_second.isoformat()} is not Krishna ({o_second.rule!r})"
            )
        if purnimas and not (d_first < purnimas[0] < d_second):
            failures.append(
                f"lunation {a0.isoformat()}..{a1.isoformat()}: order is not "
                f"Shukla Ekadashi < Purnima < Krishna Ekadashi "
                f"({d_first.isoformat()}, {purnimas[0].isoformat()}, "
                f"{d_second.isoformat()})"
            )

    print(f"  {len(rows)} observance(s) over {SPAN_START.isoformat()}.."
          f"{SPAN_END.isoformat()}, {lunations} complete lunation(s) checked")
    return failures


# --------------------------------------------------------------------------
# Gate B - cross-check against the hand-verified registry
# --------------------------------------------------------------------------

def _allowed_offsets(fest) -> tuple[tuple[int, ...], str]:
    """Which (computed_date - festival_date) offsets in days this rule allows.

    Derived from `observance_window`, not from what happens to pass. See the
    module docstring: a sunrise-reckoned festival is exact; a later-in-the-day
    window may sit one day before the computed sunrise day; `holi` is one day
    after the pradosh-reckoned Purnima and so allows both.
    """
    window = fest.observance_window
    if fest.slug == "holi":
        return (-1, 0), f"day after the pradosh Purnima; window {window!r}"
    if window.startswith("sunrise"):
        return (0,), f"sunrise-reckoned; window {window!r}"
    return (0, 1), f"reckoned after sunrise, may run a day earlier; window {window!r}"


def gate_b_registry_cross_check(rows: list[tuple[date, lo.Observance]]) -> list[str]:
    failures: list[str] = []
    by_kind: dict[str, set[date]] = {}
    for d, o in rows:
        by_kind.setdefault(_kind(o.slug), set()).add(d)

    checked = 0
    for fest in festival_registry.FESTIVALS:
        rule = fest.rule
        if "Purnima" in rule:
            kind, pool = "Purnima", by_kind.get("purnima", set())
        elif "Amavasya" in rule:
            kind, pool = "Amavasya", by_kind.get("amavasya", set())
        else:
            continue

        offsets, why = _allowed_offsets(fest)
        for year in YEARS:
            iso = fest.dates.get(year)
            if not iso:
                continue
            try:
                d = date.fromisoformat(iso)
            except ValueError:
                failures.append(f"{fest.slug} {year}: unparseable date {iso!r}")
                continue
            checked += 1

            nearest = min(pool, key=lambda c: abs((c - d).days), default=None)
            delta = (nearest - d).days if nearest else None
            ok = delta in offsets

            pairing = f"{kind} {nearest.isoformat() if nearest else '(none)'}"
            print(f"  {'ok  ' if ok else 'FAIL'} {fest.slug:<20} {iso} -> "
                  f"{pairing:<22} {delta:+d} day(s)  [{why}]"
                  if delta is not None else
                  f"  FAIL {fest.slug:<20} {iso} -> no computed {kind} at all")
            if not ok:
                failures.append(
                    f"{fest.slug} {year} ({iso}, rule {rule!r}): nearest computed "
                    f"{kind} is {nearest} ({delta:+d} days), allowed offsets "
                    f"{offsets} — {why}. Either the registry date or the sunrise "
                    "rule is wrong; check the tithi window against the almanac "
                    "before changing either."
                )

    print(f"  {checked} registry festival-year(s) cross-checked against the "
          "computed engine")
    return failures


# --------------------------------------------------------------------------
# Gate C - edge-case census (vriddhi / kshaya), re-derived independently
# --------------------------------------------------------------------------

def gate_c_edge_cases() -> tuple[list[str], list[tuple[date, str, str]]]:
    failures: list[str] = []
    samples: list[tuple[date, int]] = []
    day = SPAN_START - timedelta(days=1)
    end = SPAN_END + timedelta(days=1)
    while day <= end:
        samples.append((day, lo._tithi_index_at_sunrise(day)))
        day += timedelta(days=1)

    census: list[tuple[date, str, str]] = []

    for (d0, i0), (d1, i1) in zip(samples, samples[1:]):
        if i0 == i1 and i0 in lo._TARGETS:
            census.append((d0, lo._TARGETS[i0][1], "vriddhi"))
        skipped = (i1 - i0) % 30
        for step in range(1, skipped):
            missing = (i0 + step) % 30
            if missing in lo._TARGETS:
                census.append((d0, lo._TARGETS[missing][1], "kshaya"))

    census = [row for row in census if SPAN_START <= row[0] <= SPAN_END]
    census.sort()

    for d, name, kind in census:
        print(f"  {kind:<8} {d.isoformat()}  {name}")
    if not census:
        print("  no vriddhi or kshaya occurrences in range")

    if any(k == "vriddhi" and n == "Ekadashi" for _d, n, k in census):
        print("  NOTE: a vriddhi Ekadashi is emitted on the FIRST day, and the "
              "2026-08-07 Drik")
        print("        spot-check disagreed on both cases in range (dashami-viddha "
              "moves the")
        print("        fast to the second day). Open, deliberately unpatched — see "
              "the KNOWN")
        print("        DISAGREEMENT section of lunar_observances.py.")

    for year in YEARS:
        for kind in ("vriddhi", "kshaya"):
            n = sum(1 for d, _n, k in census if d.year == year and k == kind)
            print(f"  {year}: {n} {kind}")
            if n > 8:
                failures.append(
                    f"{year}: {n} {kind} occurrence(s), more than 8 — that is an "
                    "algorithm break, not an astronomical change"
                )
    return failures, census


# --------------------------------------------------------------------------
# Gate D - slug uniqueness and registry date collisions
# --------------------------------------------------------------------------

def gate_d_slugs(rows: list[tuple[date, lo.Observance]]) -> list[str]:
    failures: list[str] = []

    counts = Counter(o.slug for _d, o in rows)
    for slug, n in sorted(counts.items()):
        if n > 1:
            failures.append(
                f"slug {slug!r} emitted {n} times — slugs are HTML ids and anchor "
                "targets on the hub, so duplicates break anchors silently"
            )
    for d, o in rows:
        if not o.slug.endswith(d.isoformat()):
            failures.append(
                f"slug {o.slug!r} does not carry its own date {d.isoformat()} — "
                "it will not be unique per occurrence"
            )

    reg: dict[date, list[str]] = {}
    for fest in festival_registry.FESTIVALS:
        for year in YEARS:
            iso = fest.dates.get(year)
            if not iso:
                continue
            try:
                reg.setdefault(date.fromisoformat(iso), []).append(fest.slug)
            except ValueError:
                continue

    collisions = 0
    for d, o in rows:
        if d in reg:
            collisions += 1
            print(f"  shares {d.isoformat()}: {o.slug} + {', '.join(reg[d])} "
                  "(expected — a named festival IS its tithi)")
    print(f"  {len(counts)} unique slug(s) over {len(rows)} row(s), "
          f"{collisions} date(s) shared with the registry")
    return failures


# --------------------------------------------------------------------------

def main() -> int:
    print("Lunar observance verification")
    print("  engine   : src/astro_ai/lunar_observances.py")
    print("  registry : src/astro_ai/festival_registry.py "
          f"(DATA_YEARS {YEARS[0]}-{YEARS[-1]})")
    print(f"  span     : {SPAN_START.isoformat()}..{SPAN_END.isoformat()}, "
          "New Delhi sunrise / IST")
    print()

    rows = _rows()
    census_holder: list[tuple[date, str, str]] = []

    def _gate_c() -> list[str]:
        failures, census = gate_c_edge_cases()
        census_holder.extend(census)
        return failures

    gates = [
        ("Gate A - structural invariants", lambda: gate_a_structure(rows)),
        ("Gate B - cross-check against the hand-verified registry",
         lambda: gate_b_registry_cross_check(rows)),
        ("Gate C - edge-case census (vriddhi / kshaya)", _gate_c),
        ("Gate D - slug uniqueness and registry date collisions",
         lambda: gate_d_slugs(rows)),
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
              "silence a gate; check the tithi against an almanac first.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
