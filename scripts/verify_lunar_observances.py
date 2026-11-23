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

  Gate C - edge-case census, and the vriddhi day-choice rule.  Prints every
      vriddhi and kshaya occurrence in range, re-deriving them from the sunrise
      samples independently of the engine's own bookkeeping. Fails if either
      exceeds 8 per year — a spike means the algorithm broke, not that astronomy
      changed.

      It then asserts which day of a vriddhi run the engine picks, because that
      choice is a rule and not an accident, and getting it wrong shifts a fast
      by a day while leaving every count and every structural invariant in Gate
      A perfectly intact — i.e. it is invisible to every other gate here.

      A vriddhi **Ekadashi** must be emitted on the SECOND day of the run
      (an empirical Drik almanac convention, 5 of 5 Drik readings, UNSOURCED in
      the corpus — the old name *dashami-viddha* is kept below only as a label,
      because no Dashami test exists in the engine: the tithi sampled at the
      first sunrise is already Ekadashi). A vriddhi **Purnima or Amavasya** must
      be emitted on the FIRST — the second-day pick is specific to the Ekadashi
      fast and must not leak. Both directions are
      checked, against `DRIK_VRIDDHI` below: every vriddhi run over 2024-2032,
      with the day drikpanchang.com actually prints, read off the year calendar
      on 2026-08-07. The table reaches outside DATA_YEARS on purpose — the
      2026-2028 span contains only two vriddhi Ekadashis, and two dates are not
      enough to settle a rule on.

  Gate D - slug uniqueness and registry collisions.  Slugs are HTML ids and
      anchor targets on the /festivals hub, so a duplicate breaks anchors
      silently. Dates shared with a `festival_registry` festival are printed for
      information; they are expected (Guru Purnima IS a Purnima), not failures.

  Gate E - independent per-row tithi check at each row's own window (#1330).
      The five late-year rows #1326 added (kartika-purnima, kalabhairav-jayanti,
      vivah-panchami, gita-jayanti, dattatreya-jayanti) were each shifted one day,
      in the registry AND the expected table together, and the rest of the gates
      stayed green: 19 of 30 shifted entries (15 entries x -1/+1) shipped. Gate 1
      of `verify_festivals.py` compares two hand transcriptions with each other,
      Gates 2/3 there are arithmetic on dates with no ephemeris, and Gate B above
      reads only rules containing "Purnima" or "Amavasya" (so an Ekadashi row is
      never looked at) and deliberately lets a later-window row sit one day EARLY
      (so a dattatreya -1 passes). None of them can see the tithi.

      This gate computes the tithi for each of the five rows at the row's own
      `observance_window` and requires the computed day list to EQUAL the registry
      date: exact, no +-1 band, no tie-break. The four shukla rows call
      `lunar_dates.shukla_tithi_date`; dattatreya-jayanti is pinned to the sunrise
      engine although its window is pradosh, because that holds 3 of 3 years today
      and is what closes the Gate B -1 survivors - a future year where pradosh
      legitimately picks the day before must fail loud and be adjudicated against
      the almanac, not widened.

      Kalabhairav Jayanti (Krishna Ashtami of purnimanta Margashirsha, i.e. amanta
      Kartika) is the one row `lunar_dates` does not cover, so it is computed here.
      "Evening" is read as SUNSET TO CIVIL MIDNIGHT of the day. THAT BOUND IS AN
      UNSOURCED READING OF DRIK, NOT A RULE: knowledge/*.md does not rule on it
      (consistent with #1331), and it is tuned only by 3 of 3 years agreeing with
      the shipped dates. It is exact, and three cases pin it (pyswisseph, Lahiri,
      New Delhi, 1-minute scan):
        2026: Ashtami 12-01 00:13 -> 12-01 23:15. If "after sunset" ran to the next
              sunrise, 2026-11-30 would qualify too (13 minutes inside that night).
        2027: Ashtami 11-20 19:18 -> 11-21 17:21; sunset 11-21 17:25 - Ashtami ends
              4 minutes BEFORE it, so 11-21 does not qualify.
        2028: Ashtami 11-09 15:41 -> 11-10 14:04.
      Two candidate evenings (a vriddhi Ashtami spanning two evenings, or a future
      year) is a FAIL that prints both days: the registry rule does not pick between
      them, read the almanac. A 4-minute margin is not flakiness if it flips: it is
      the registry's own claim sitting on a knife edge.

      If pyswisseph is absent the import above raises and the script exits non-zero.
      Do not add an ImportError skip - a silent pass is the failure this guards.

Note the counts printed by Gate A are OUTPUT, not targets. If a count disagrees
with what you expected, report the disagreement — do not tune the engine to hit
a number, and do not adjust the sunrise rule to make one date match.

Usage:  uv run python scripts/verify_lunar_observances.py
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "src"))

# Gate E needs the ephemeris directly. A missing pyswisseph must raise here and
# exit non-zero; never wrap this in a try/except ImportError.
import swisseph as swe  # noqa: E402

from astro_ai import festival_registry  # noqa: E402
from astro_ai import lunar_dates as ld  # noqa: E402
from astro_ai import lunar_observances as lo  # noqa: E402
from astro_ai.chart import _sunrise_sunset, _tithi_at  # noqa: E402

YEARS = list(festival_registry.DATA_YEARS)
SPAN_START = date(min(YEARS), 1, 1)
SPAN_END = date(max(YEARS), 12, 31)

# Every vriddhi run the engine finds over 2024-2032, with the day
# drikpanchang.com prints for it — read off …/calendars/hindu/hinducalendar.html
# ?year=YYYY on 2026-08-07. Entries are (first day of the run, kind, Drik's day,
# the name Drik gives it).
#
# All five vriddhi Ekadashis land on the SECOND day of the run, and every
# reachable vriddhi Purnima and Amavasya on the FIRST. That asymmetry is the
# second-day rule (labelled dashami-viddha for history only — a misnomer) and
# this table is the evidence for it, 5 of 5 Drik readings and unsourced in the
# corpus; see the RESOLVED DISAGREEMENT section of lunar_observances.py.
#
# One run is missing here and its absence is not an oversight: the vriddhi
# Amavasya of 2025-12-19 carries no festival name, and Drik's year calendar
# lists only named observances, so there was nothing to read. It is left out
# rather than guessed at.
DRIK_VRIDDHI: tuple[tuple[str, str, str, str], ...] = (
    ("2024-06-17", "ekadashi", "2024-06-18", "Nirjala Ekadashi"),
    ("2024-09-02", "amavasya", "2024-09-02", "Somavati Amavasya"),
    ("2024-10-27", "ekadashi", "2024-10-28", "Rama Ekadashi"),
    ("2026-05-26", "ekadashi", "2026-05-27", "Padmini Ekadashi"),
    ("2026-06-29", "purnima", "2026-06-29", "Jyeshtha Purnima"),
    ("2027-03-03", "ekadashi", "2027-03-04", "Vijaya Ekadashi"),
    ("2027-06-18", "purnima", "2027-06-18", "Jyeshtha Purnima"),
    ("2028-12-01", "purnima", "2028-12-01", "Margashirsha Purnima"),
    ("2029-10-17", "ekadashi", "2029-10-18", "Papankusha Ekadashi"),
)

# Single-sunrise Ekadashis where Drik Panchang (New Delhi) prints the day BEFORE
# the one a plain sunrise scan lands on (#1332). Entries are (the day a sunrise
# scan lands on, Drik's day, the name Drik gives it, is_shifted).
#
# Read from drikpanchang.com (New Delhi) in the #1332 cycle by astro-auditor: of
# the 74 Ekadashis the engine emitted over 2026-2028, exactly 3 differ from Drik,
# and each is a day EARLIER. In all three the sunrise indices at D-1, D, D+1 are
# t-1, t, t+2 (t = 10 or 25): Dwadashi is skipped, no sunrise falls inside it.
# That is the rule; it is an UNSOURCED-IN-CORPUS Drik almanac convention (3 of 3 Drik readings, the other 71 unchanged) — knowledge/
# vedic_reference.md §29.6 does not decide it and is not cited as support. The
# vriddhi "second sunrise" rule above is empirical in the same way.
#
# The two is_shifted=False rows are negative controls, one per condition of the
# rule (tithi indices at the sunrises D-1, D, D+1; Ekadashi is 10 or 25):
#   2027-10-25  23, 25, 26 - Dashami was skipped at D-1, so the t-1 test fails.
#   2028-08-16  24, 25, 26 - Dwadashi is running at D+1, so the t+2 test fails.
# Drik prints both on the sunrise day. They are also why the rule is NOT strict
# arunodaya, which would regress both. Do not put these rows in DRIK_VRIDDHI:
# `_emitted_for_run` there only looks at offsets 0..+1 and its failure text says
# dashami-viddha, which is the wrong diagnosis for a day-earlier shift.
DRIK_SINGLE_SUNRISE: tuple[tuple[str, str, str, bool], ...] = (
    ("2027-01-19", "2027-01-18", "Putrada Ekadashi", True),
    ("2028-02-07", "2028-02-06", "Jaya Ekadashi", True),
    ("2028-11-13", "2028-11-12", "Utpanna Ekadashi", True),
    ("2027-10-25", "2027-10-25", "negative control: t-1 test", False),
    ("2028-08-16", "2028-08-16", "negative control: t+2 test", False),
)


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

def _emitted_for_run(
    first: date, kind: str, lo_off: int = 0, hi_off: int = 1
) -> date | None:
    """Which day of the run starting `first` the engine emitted `kind` on.

    A vriddhi run offers exactly two candidate days, `first` and `first + 1`
    (the default offsets 0..+1), and two observances of the same kind are never
    less than 13 days apart, so a hit on either day is unambiguously this run's.
    The single-sunrise day-earlier rule (#1332) looks at -1..0 instead.
    """
    window = lo.observances_between(
        first + timedelta(days=lo_off - 1), first + timedelta(days=hi_off + 1)
    )
    hits = [
        d for d, o in window
        if _kind(o.slug) == kind and lo_off <= (d - first).days <= hi_off
    ]
    return hits[0] if len(hits) == 1 else None


def gate_c_drik_single_sunrise() -> list[str]:
    """Assert the day-earlier single-sunrise rule against Drik, both directions."""
    failures: list[str] = []
    for engine_iso, drik_iso, label, shifted in DRIK_SINGLE_SUNRISE:
        engine_day = date.fromisoformat(engine_iso)
        expected = date.fromisoformat(drik_iso)
        got = _emitted_for_run(engine_day, "ekadashi", lo_off=-1, hi_off=0)
        what = "day-earlier rule" if shifted else "stays on the sunrise day"
        if got is None:
            failures.append(
                f"single-sunrise Ekadashi {engine_iso} ({label}): the engine emits "
                f"no Ekadashi on {engine_iso} or the day before"
            )
            print(f"  FAIL ekadashi sunrise {engine_iso} -> (nothing emitted)   "
                  f"Drik {drik_iso}  {label}")
            continue
        ok = got == expected
        print(f"  {'ok  ' if ok else 'FAIL'} ekadashi sunrise {engine_iso} -> "
              f"{got.isoformat()}   Drik {drik_iso}  {label} [{what}]")
        if not ok:
            failures.append(
                f"Ekadashi whose sunrise scan lands on {engine_iso} ({label}) emitted "
                f"on {got.isoformat()}, Drik prints {drik_iso} "
                + ("(single sunrise, Dwadashi skipped at D+1 - Drik prints the day "
                   "BEFORE; unsourced-in-corpus Drik convention, #1332)"
                   if shifted else
                   "(negative control - the day-earlier rule must not fire here)")
            )
    print(f"  {len(DRIK_SINGLE_SUNRISE)} single-sunrise Ekadashi(s) checked against "
          "drikpanchang.com (3 shifted, 2 negative controls)")
    return failures


def gate_c_drik_vriddhi() -> list[str]:
    """Assert the day-of-run choice against the Drik table, both directions."""
    failures: list[str] = []
    for first_iso, kind, drik_iso, label in DRIK_VRIDDHI:
        first = date.fromisoformat(first_iso)
        expected = date.fromisoformat(drik_iso)
        want_second = kind == "ekadashi"
        rule = "dashami-viddha, SECOND day" if want_second else "FIRST day, no viddha test"
        got = _emitted_for_run(first, kind)

        if got is None:
            failures.append(
                f"vriddhi {kind} run starting {first_iso} ({label}): the engine emits "
                f"no {kind} on {first_iso} or the day after, so the run itself is gone "
                "— this is not a day-choice problem, check the sunrise scan first"
            )
            print(f"  FAIL {kind:<9} run {first_iso}  -> (nothing emitted)   "
                  f"Drik {drik_iso}  {label}")
            continue

        ok = got == expected
        print(f"  {'ok  ' if ok else 'FAIL'} {kind:<9} run {first_iso}  -> "
              f"{got.isoformat()}   Drik {drik_iso}  {label} [{rule}]")
        if ok:
            continue
        if want_second:
            failures.append(
                f"dashami-viddha REGRESSION: vriddhi Ekadashi run starting {first_iso} "
                f"({label}) emitted on {got.isoformat()}, Drik prints {drik_iso}. A "
                "vriddhi Ekadashi takes the SECOND day of the run (a Drik almanac "
                "convention, 5 of 5 readings, unsourced in the corpus)."
            )
        else:
            failures.append(
                f"dashami-viddha LEAKED into {kind}: vriddhi run starting {first_iso} "
                f"({label}) emitted on {got.isoformat()}, Drik prints {drik_iso}. The "
                "second-day pick is specific to the Ekadashi fast; Purnima and Amavasya "
                "are reckoned at sunrise and take the FIRST day of the run."
            )
    print(f"  {len(DRIK_VRIDDHI)} vriddhi run(s) checked against drikpanchang.com "
          "(2024-2032, wider than DATA_YEARS on purpose)")
    return failures


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

    # Day-of-run choice for every vriddhi in span, whether or not the Drik table
    # below happens to cover it. Ekadashi second, everything else first.
    for d0, name, kind in census:
        if kind != "vriddhi":
            continue
        obs_kind = name.lower()
        want = d0 + timedelta(days=1) if obs_kind == "ekadashi" else d0
        got = _emitted_for_run(d0, obs_kind)
        if got != want:
            failures.append(
                f"vriddhi {name} run starting {d0.isoformat()}: engine emits "
                f"{got.isoformat() if got else '(nothing)'}, rule says "
                f"{want.isoformat()} "
                + ("(dashami-viddha — a vriddhi Ekadashi takes the SECOND day)"
                   if obs_kind == "ekadashi"
                   else "(FIRST day — the viddha test does not apply outside Ekadashi)")
            )

    # Single-sunrise Ekadashis (#1332): re-derive the day-earlier filter from the
    # sample indices alone, for EVERY sunrise-sampled Ekadashi in span, so the
    # Drik table above is not the only thing holding the rule. Index at D-1 is
    # t-1 (not a vriddhi run), D is t, D+1 is >= t+2 (Dwadashi skipped), with
    # t = 10 or 25; the engine must emit D-1. Everything else emits D.
    shifted_days: list[date] = []
    checked_ekadashi = 0
    for i in range(1, len(samples) - 1):
        d, idx = samples[i]
        if idx not in (10, 25) or not (SPAN_START <= d <= SPAN_END):
            continue
        prev_idx, next_idx = samples[i - 1][1], samples[i + 1][1]
        if prev_idx == idx or next_idx == idx:
            continue  # vriddhi run - the second-day rule above owns it
        checked_ekadashi += 1
        shift = prev_idx == idx - 1 and (next_idx - idx) % 30 >= 2
        want = d - timedelta(days=1) if shift else d
        got = _emitted_for_run(d, "ekadashi", lo_off=-1, hi_off=0)
        if shift:
            shifted_days.append(d)
        if got != want:
            failures.append(
                f"single-sunrise Ekadashi on sunrise day {d.isoformat()} "
                f"(indices {prev_idx},{idx},{next_idx}): engine emits "
                f"{got.isoformat() if got else '(nothing)'}, rule says "
                f"{want.isoformat()}"
            )
    print(f"  {checked_ekadashi} single-sunrise Ekadashi(s) re-derived; "
          f"{len(shifted_days)} take the day before: "
          f"{[x.isoformat() for x in shifted_days]}")

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
# Gate E - independent per-row tithi check at each row's own window (#1330)
# --------------------------------------------------------------------------

class IndependentRow(NamedTuple):
    slug: str
    window_prefix: str   # the registry's observance_window must still start with this
    kind: str            # "shukla" (lunar_dates) or "krishna_evening" (computed below)
    month: str           # nija month name, AMANTA (Kartika, not purnimanta Margashirsha)
    tithi: int           # 1..15 within the paksha
    reckoning: str       # "sunrise" / "madhyahna" for shukla; "evening" for krishna_evening


# Tithi index 22 is Krishna Ashtami, 0-based as `chart._tithi_at` returns it
# (0 = Shukla Pratipada .. 14 = Purnima, 15 + 7 = Krishna Ashtami).
_KRISHNA_ASHTAMI = 22

INDEPENDENT_ROWS: tuple[IndependentRow, ...] = (
    IndependentRow("vivah-panchami", "madhyahna", "shukla", "Margashirsha", 5, "madhyahna"),
    IndependentRow("gita-jayanti", "sunrise", "shukla", "Margashirsha", 11, "sunrise"),
    IndependentRow("kartika-purnima", "sunrise", "shukla", "Kartika", 15, "sunrise"),
    # Pinned to the sunrise engine although the window is pradosh: 3 of 3 years
    # agree (2026 is the kshaya gap rule's begin-day = the registry's pradosh day).
    # It closes the Gate B -1 survivors. A year where pradosh legitimately takes
    # the day before must fail loud and go to the almanac, not widen this.
    IndependentRow("dattatreya-jayanti", "pradosh", "shukla", "Margashirsha", 15, "sunrise"),
    # Purnimanta Margashirsha = amanta Kartika; the rule text says so.
    IndependentRow("kalabhairav-jayanti", "evening", "krishna_evening", "Kartika", 8, "evening"),
)


def _tithi_idx_at(instant: datetime) -> int:
    ut = instant.astimezone(ld._UTC)
    jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60 + ut.second / 3600)
    return _tithi_at(jd)[0]


def _evening_samples(day: date) -> tuple[int, int]:
    """Tithi index at sunset of `day`, and at 23:59 IST of `day`.

    The evening is sunset to civil midnight (an UNSOURCED reading of Drik, see the
    module docstring). Two end-point samples are exact, not an approximation: the
    shortest tithi (~19 h) is longer than the evening window (< 8 h), so a tithi
    running at any instant of the window is running at one of its two ends.
    """
    _sunrise, sunset = _sunrise_sunset(day, ld._DELHI_LAT, ld._DELHI_LON, ld._DELHI_TZ)
    midnight = datetime.combine(day, time(23, 59), tzinfo=ld._DELHI_TZ)
    return _tithi_idx_at(sunset), _tithi_idx_at(midnight)


def _krishna_ashtami_in_evening(day: date) -> bool:
    return _KRISHNA_ASHTAMI in _evening_samples(day)


def _evening_ashtami_days(year: int, month: str) -> list[date]:
    """Days of `year` whose evening carries Krishna Ashtami of nija amanta `month`.

    Krishna Ashtami falls about 22 days into an amanta month, so the scan starts at
    start + 13 and runs to the month's end. `lunar_dates` is not generalised to
    Krishna (its docstring forbids it without a purnimanta/amanta argument).
    """
    days: list[date] = []
    for m in ld._nija_months(year, month):
        day = m.start + timedelta(days=13)
        while day <= m.end:
            if day.year == year and _krishna_ashtami_in_evening(day):
                days.append(day)
            day += timedelta(days=1)
    return sorted(days)


def _independent_days(row: IndependentRow, year: int) -> list[date]:
    if row.kind == "krishna_evening":
        return _evening_ashtami_days(year, row.month)
    picked = ld.shukla_tithi_date(year, row.month, row.tithi, row.reckoning)
    return [] if picked is None else [picked]


def gate_e_independent_window_check() -> list[str]:
    failures: list[str] = []
    by_slug = {f.slug: f for f in festival_registry.FESTIVALS}

    checked = 0
    for row in INDEPENDENT_ROWS:
        row_fest = by_slug.get(row.slug)
        if row_fest is None:
            # A renamed slug must fail, not silently stop being checked.
            failures.append(f"{row.slug}: no such row in festival_registry")
            continue
        if not row_fest.observance_window.startswith(row.window_prefix):
            failures.append(
                f"{row.slug}: observance_window is now {row_fest.observance_window!r}, "
                f"this gate recorded it as starting {row.window_prefix!r}. Re-derive "
                "what the row is reckoned at before editing INDEPENDENT_ROWS."
            )
            continue
        for year in YEARS:
            iso = row_fest.dates.get(year)
            if not iso:
                failures.append(f"{row.slug} {year}: no date in the registry")
                continue
            try:
                shipped = date.fromisoformat(iso)
            except ValueError:
                failures.append(f"{row.slug} {year}: unparseable date {iso!r}")
                continue
            checked += 1

            computed = _independent_days(row, year)
            ok = computed == [shipped]
            shown = ", ".join(d.isoformat() for d in computed) or "(none)"
            print(f"  {'ok  ' if ok else 'FAIL'} {row.slug:<20} {iso} -> computed "
                  f"{shown}  [{row.reckoning}]")
            if ok:
                continue
            if not computed:
                failures.append(
                    f"{row.slug} {year} ({iso}): the computation found no day "
                    f"({row.month} tithi {row.tithi} at {row.reckoning}) - a kshaya "
                    "month or tithi is a FAIL here, never a skip; read the almanac."
                )
            elif len(computed) > 1:
                failures.append(
                    f"{row.slug} {year} ({iso}): {len(computed)} candidate days "
                    f"({shown}). The registry rule does not pick between them; read "
                    "the almanac."
                )
            else:
                failures.append(
                    f"{row.slug} {year}: registry says {iso}, the tithi at the row's "
                    f"own window ({row.reckoning}) lands on {shown}. Exact equality, "
                    "no +-1 band; check the almanac before changing either."
                )

    print(f"  {checked} row-year(s) checked "
          f"({len(INDEPENDENT_ROWS)} rows x {len(YEARS)} year(s))")
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
        failures.extend(gate_c_drik_vriddhi())
        failures.extend(gate_c_drik_single_sunrise())
        return failures

    gates = [
        ("Gate A - structural invariants", lambda: gate_a_structure(rows)),
        ("Gate B - cross-check against the hand-verified registry",
         lambda: gate_b_registry_cross_check(rows)),
        ("Gate C - edge-case census (vriddhi / kshaya) and the vriddhi day-choice rule",
         _gate_c),
        ("Gate D - slug uniqueness and registry date collisions",
         lambda: gate_d_slugs(rows)),
        ("Gate E - independent per-row tithi check at each row's own window",
         gate_e_independent_window_check),
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
