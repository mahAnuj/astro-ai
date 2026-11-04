"""Chart-keyed lookup into `knowledge/remedies.md` (#399).

The natal prompt used to carry a nine-planet remedy list on EVERY call, whether
or not the chart had a planet that needed one. This module builds, instead, a
small `--- REMEDY RULES ---` block for only the planets the chart's own PLANET
DIGNITY block flags DEBILITATED or COMBUST — and nothing at all when there are
none. It is the first place runtime code reads `knowledge/`.

WHAT IS READ: remedies.md §5.1 (grain per planet) and §7.1 (deities per planet),
each a markdown table in a local file. No GCS, no dependency, parsed once.

WHAT NEVER REACHES THE MODEL: the book, the author, a chapter or a section mark.
The tables' cells carry them (the Venus grain cell names an author), and
natal.txt bans naming classical texts in prose, so the block is rendered from
the CELLS by `_render` below with every parenthetical stripped — never by
pasting a section. tests/test_knowledge_lookup.py holds a citation-ban regex
over every planet's block.

TWO KNOWN SIMPLIFICATIONS, both deliberate:
  * Keying remedies on DEBILITATED/COMBUST is a house convention. Nothing in
    remedies.md says a flagged planet is the one to remedy.
  * Deities are capped at three per planet, a token policy. The cell can hold
    five (Jupiter), so the block says "traditionally linked deities include",
    never "the deity" — the model is told these are options, not a prescription.

Sections are located by NUMBER PREFIX (`### 5.1`), never by full title: the §7.1
title contains an author's name, and a title match would break on a rename.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path

_log = logging.getLogger(__name__)

_REMEDIES_PATH = Path(__file__).parent / "knowledge" / "remedies.md"

#: Sun..Saturn, the order the old natal.txt remedy list used. The tie-break
#: within a tier — a house rule with no classical basis, but deterministic.
_PLANET_ORDER = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
MAX_PLANETS = 3
MAX_DEITIES = 3

#: §12.1 of remedies.md forbids resolving the Venus cell into a named grain —
#: the source names none. The parsed cell carries the author's name in a
#: parenthetical, so the rendering is fixed here rather than derived.
_VENUS_GRAIN = "a whitish grain"

# Defence in depth for the rule above: if a future edit puts a book, author or
# chapter mark into a table cell itself (not in a parenthetical), the planet's
# line is dropped rather than shipped. "Narasimha" alone is a deity, not a ban.
_CITATION_RE = re.compile(
    r"\b(?:Rao|P\.V\.R\.|Raman|Parashara|BPHS|Phaladeepika|Jataka|Mansagari|"
    r"Chintamani|Chapter)\b|Ch\.|§|\("
)
_PAREN_RE = re.compile(r"\s*\([^)]*\)")


class RemedyTablesError(Exception):
    """remedies.md is missing, empty, or no longer has the tables we read."""


def _read_remedies() -> str:
    """The file's text. Its own function so a test can count the reads."""
    return _REMEDIES_PATH.read_text(encoding="utf-8")


def _section_rows(text: str, number: str) -> dict[str, str]:
    """{planet: cell} for the first markdown table under the `### <number>` heading.

    The section ends at the next heading. `### 5.1` must not also match
    `### 5.10`, hence the trailing whitespace-or-end in the pattern.
    """
    heading = re.compile(rf"^###\s+{re.escape(number)}(?:\s|$)")
    in_section = False
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if heading.match(line):
            in_section = True
            continue
        if in_section and line.startswith("#"):
            break
        if not in_section or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "Planet" or set(cells[0]) <= {"-", ":", " "}:
            continue
        rows[cells[0]] = cells[1]
    return rows


@lru_cache(maxsize=1)
def _tables() -> tuple[dict[str, str], dict[str, str]]:
    """(grain cells, deity cells), parsed once. Raises RemedyTablesError.

    lru_cache does not cache an exception, so a failure is retried — and
    re-logged — on the next call rather than sticking until a restart.
    """
    try:
        text = _read_remedies()
    except (OSError, ValueError) as exc:  # ValueError: UnicodeDecodeError on non-UTF-8 bytes
        raise RemedyTablesError(f"cannot read {_REMEDIES_PATH.name}: {exc}") from exc
    grains = _section_rows(text, "5.1")
    deities = _section_rows(text, "7.1")
    if not grains or not deities:
        raise RemedyTablesError(
            f"{_REMEDIES_PATH.name} parsed to {len(grains)} grain rows (§5.1) and "
            f"{len(deities)} deity rows (§7.1); the layout this reads has changed"
        )
    return grains, deities


def _strip(cell: str) -> str:
    return _PAREN_RE.sub("", cell).strip()


def grain_for(planet: str) -> str | None:
    """The grain to name for `planet`, or None (Ketu has no §5.1 row)."""
    cell = _tables()[0].get(planet)
    if cell is None:
        return None
    if planet == "Venus":
        return _VENUS_GRAIN
    grain = _strip(cell)
    # Lower-cased: it is rendered mid-sentence, and the prompt tells the model
    # to name it exactly as the block gives it.
    return grain[:1].lower() + grain[1:] if grain else None


def deities_for(planet: str) -> list[str]:
    """Up to MAX_DEITIES deities for `planet`, in table order."""
    cell = _tables()[1].get(planet, "")
    names = [_strip(n) for n in cell.split(",")]
    return [n for n in names if n][:MAX_DEITIES]


def _is_weak(tags: Sequence[str]) -> str | None:
    """"DEBILITATED", "COMBUST" or None, testing by TOKEN.

    The COMBUST tag is "COMBUST (7.3° from Sun)" and a planet can carry both
    (they are joined with " — "), so neither equality nor a single `in` on the
    joined string is right. Debilitated wins when both are present: the planet
    is counted once, in the stronger tier.
    """
    tokens = {t.split(" (")[0].strip() for t in tags}
    if "DEBILITATED" in tokens:
        return "DEBILITATED"
    if "COMBUST" in tokens:
        return "COMBUST"
    return None


def select_planets(dignities: Iterable[tuple[str, Sequence[str]]]) -> list[str]:
    """The planets to give a remedy line, at most MAX_PLANETS.

    Debilitated first, then combust, then Sun..Saturn inside each tier. 7 of
    300 seeded charts have four weak planets, so the cap does bite, rarely.
    """
    tier = {"DEBILITATED": 0, "COMBUST": 1}
    weak = []
    for name, tags in dignities:
        kind = _is_weak(tags)
        if kind is not None and name in _PLANET_ORDER:
            weak.append((tier[kind], _PLANET_ORDER.index(name), name))
    return [name for _, _, name in sorted(weak)][:MAX_PLANETS]


def _render(planet: str) -> str:
    parts = []
    grain = grain_for(planet)
    if grain:
        parts.append(f"grain: {grain}")
    deities = deities_for(planet)
    if deities:
        parts.append("traditionally linked deities include " + ", ".join(deities))
    line = f"- {planet}: " + "; ".join(parts) if parts else ""
    if _CITATION_RE.search(line):
        _log.error("remedy line for %s carries a citation mark, dropped: %r", planet, line)
        return ""
    return line


def remedy_rules_for(dignities: Iterable[tuple[str, Sequence[str]]]) -> str:
    """The `--- REMEDY RULES ---` block for this chart, or "".

    `dignities` is (planet name, dignity tags) for the chart, as
    chart.planet_dignities yields them. "" means "no block": no planet is
    flagged, or remedies.md could not be read. The second is logged at ERROR
    and never raised — this is on the /kundli request path, and a reading
    with no remedy line is better than no reading.
    """
    planets = select_planets(dignities)
    if not planets:
        return ""
    try:
        _tables()
    except RemedyTablesError as exc:
        _log.error("remedy rules unavailable, natal reading goes out without them: %s", exc)
        return ""
    lines = [line for line in (_render(p) for p in planets) if line]
    if not lines:
        return ""
    return "--- REMEDY RULES ---\n" + "\n".join(lines)
