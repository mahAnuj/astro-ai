#!/usr/bin/env python3
"""Gate: the gochar table in code must match the sourced table in knowledge/.

Why this exists. `_GOCHAR_FAVOURABILITY` used to list 3-5 houses per planet
and default every other house to "neutral" — a category B.V. Raman does not
use; he classifies all twelve. Two of the listed values were also simply
wrong against him (`("Jupiter", 1)` and `("Ketu", 9)` were marked favourable
where he calls both malefic), and the lookup was keyed on the house from the
LAGNA while Gochara is by definition measured from the natal Moon.

None of that was catchable by reading the diff, because nothing in the repo
tied the constant to its source. This does: it parses the table out of
knowledge/vedic_reference.md §2A — which carries the citation — and asserts
the code agrees, house by house.

Gate 3 is the one that matters most. It re-derives, from the chart engine
itself, that the favourability attached to a transit is the one for its house
FROM THE MOON and not from the Lagna. A table can be perfectly correct and
still be looked up with the wrong key; that was the actual bug.
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai.chart import (  # noqa: E402
    _GOCHAR_FAVOURABILITY,
    compute_chart,
    compute_gochar_impacts,
)

DOC = Path(__file__).resolve().parent.parent / "src/astro_ai/knowledge/vedic_reference.md"
PLANETS_IN_CODE = ("Jupiter", "Saturn", "Rahu", "Ketu")


def parse_doc_table() -> dict[str, tuple[set[int], set[int]]]:
    """Pull §2A's benefic/malefic table out of the knowledge file."""
    text = DOC.read_text()
    start = text.index("## 2A. Gochara")
    body = text[start:text.index("\n## ", start + 10)]
    out: dict[str, tuple[set[int], set[int]]] = {}
    for line in body.splitlines():
        if not line.startswith("|") or "---" in line or "Benefic" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        nums = lambda c: {int(n) for n in re.findall(r"\d+", c)}
        for name in cells[0].split("/"):
            out[name.strip()] = (nums(cells[1]), nums(cells[2]))
    return out


def gate_1_doc_table_is_complete(doc) -> list[str]:
    """Every planet's two lists must partition 1..12 exactly."""
    fails = []
    for planet, (ben, mal) in doc.items():
        if ben & mal:
            fails.append(f"{planet}: house(s) {sorted(ben & mal)} listed as BOTH benefic and malefic")
        if ben | mal != set(range(1, 13)):
            missing = set(range(1, 13)) - (ben | mal)
            fails.append(f"{planet}: houses {sorted(missing)} classified as neither — Raman classifies all twelve")
    print(f"  parsed {len(doc)} planets from vedic_reference.md §2A")
    return fails


def gate_2_code_matches_doc(doc) -> list[str]:
    fails = []
    for planet in PLANETS_IN_CODE:
        if planet not in doc:
            fails.append(f"{planet}: absent from the knowledge table")
            continue
        ben, _ = doc[planet]
        for house in range(1, 13):
            want = "favorable" if house in ben else "challenging"
            got = _GOCHAR_FAVOURABILITY.get((planet, house))
            if got is None:
                fails.append(f"{planet} house {house}: missing from code (would default to neutral)")
            elif got != want:
                fails.append(f"{planet} house {house}: code says {got!r}, Raman says {want!r}")
    print(f"  compared {len(PLANETS_IN_CODE) * 12} (planet, house) pairs against the source")
    return fails


def gate_3_lookup_is_keyed_from_the_moon(doc) -> list[str]:
    """The bug was the KEY, not the table. Prove the verdict follows the Moon."""
    fails = []
    random.seed(11)
    cities = ["Mumbai, India", "Delhi, India", "Chennai, India", "Kolkata, India"]
    checked = differs = 0
    for _ in range(40):
        y, m, d = random.randint(1960, 2005), random.randint(1, 12), random.randint(1, 28)
        try:
            chart = compute_chart(f"{y:04d}-{m:02d}-{d:02d}",
                                  f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
                                  random.choice(cities))
            impacts = compute_gochar_impacts(chart)
        except Exception:
            continue
        for g in impacts:
            ben, _ = doc[g.planet]
            from_moon = "favorable" if g.house_from_moon in ben else "challenging"
            from_lagna = "favorable" if g.house_from_lagna in ben else "challenging"
            checked += 1
            if from_moon != from_lagna:
                differs += 1
            if g.favorability != from_moon:
                fails.append(
                    f"{g.planet} in {g.sign}: house {g.house_from_moon} from Moon "
                    f"(={from_moon}) but favourability is {g.favorability!r}"
                )
    print(f"  {checked} live gochar lines checked; {differs} would differ if keyed from the Lagna "
          f"({100 * differs / max(checked, 1):.1f}%)")
    if checked and differs == 0:
        fails.append("no sampled line distinguishes Moon from Lagna — this gate proves nothing; widen the sample")
    return fails


def main() -> int:
    doc = parse_doc_table()
    gates = [
        ("Gate 1 - knowledge table partitions all 12 houses", gate_1_doc_table_is_complete),
        ("Gate 2 - code table matches the sourced table", gate_2_code_matches_doc),
        ("Gate 3 - favourability is keyed from the Moon, not the Lagna", gate_3_lookup_is_keyed_from_the_moon),
    ]
    results = []
    for name, fn in gates:
        print(name)
        fails = fn(doc)
        for f in fails:
            print(f"  FAIL: {f}")
        print(f"  -> {'PASS' if not fails else f'FAIL ({len(fails)} problem(s))'}\n")
        results.append((name, fails))

    print("Summary")
    for name, fails in results:
        print(f"  {'PASS     ' if not fails else f'FAIL ({len(fails)})'} {name}")
    total = sum(len(f) for _, f in results)
    print(f"\n{'PASS' if not total else f'FAIL — {total} problem(s)'}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
