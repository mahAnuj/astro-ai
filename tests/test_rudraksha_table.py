"""The Rudraksha bead the page recommends must match knowledge/numerology.md §11.

WHY THIS EXISTS (#173)

`/numerology` shipped a different bead from §11 for Life Path 1 and Life Path 8,
and in both cases it *led* with the divergent bead and demoted §11's to a
footnote. Life Path 1 read "1-mukhi — rarest and most powerful", which points a
user at the scarcest and most-counterfeited bead on the market. This is a remedy
people act on with money, it was live, and nothing caught it: the twelve
`verify_*.py` gates cover almanac data, not this table.

Table data rots silently. The two documents drifted apart and stayed apart
through several release cycles because no executable check compared them.

THE TEST PARSES §11 OUT OF THE MARKDOWN. It does not restate the nine beads
inline. A test that hard-codes the expected values is testing itself: someone
"fixing" a divergence would edit both the code and the test, and the corpus
document — the thing that is supposed to be the authority — would drift away
unnoticed. Parsing means the markdown wins, always.

Note what this does NOT assert: that §11's beads are *correct*. That column is
unsourced and §11 says so in as many words. This gate only guarantees the app
and the knowledge file cannot disagree.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import numerology as _num

_KNOWLEDGE = (
    Path(__file__).resolve().parent.parent
    / "src" / "astro_ai" / "knowledge" / "numerology.md"
)


def _section_11_beads() -> dict[int, str]:
    """Parse the `# | Dosha | Rudraksha bead | ...` table out of §11."""
    text = _KNOWLEDGE.read_text(encoding="utf-8")
    start = text.index("## §11")
    end = text.index("## §12", start)
    beads: dict[int, str] = {}
    for line in text[start:end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        beads[int(cells[0])] = cells[2]
    return beads


def test_section_11_table_is_still_parseable():
    """Guard the parser itself — a silently-empty table would pass everything."""
    beads = _section_11_beads()
    assert sorted(beads) == list(range(1, 10)), beads
    assert all(re.fullmatch(r"\d+-mukhi", b) for b in beads.values()), beads


@pytest.mark.parametrize("number", range(1, 10))
def test_remedy_leads_with_the_bead_section_11_names(number: int):
    """All nine. The bead must be the FIRST thing said, not a demoted aside.

    Leading matters: #173's defect was not that 12-mukhi went unmentioned for
    Life Path 1 — it was mentioned, as the second-choice "acceptable
    alternative". What the user reads first is what the user buys.
    """
    expected = _section_11_beads()[number]
    text = _num._REMEDIES[number].rudraksha
    assert text.startswith(expected + " "), (
        f"Life Path {number}: knowledge/numerology.md §11 names {expected!r}, "
        f"but _REMEDIES[{number}].rudraksha leads with {text[:40]!r}"
    )


def test_master_numbers_still_inherit_their_base_bead():
    """11/22/33 have no row of their own; _get_remedy falls back to 2/4/6."""
    for master, base in ((11, 2), (22, 4), (33, 6)):
        assert _num._get_remedy(master) is _num._REMEDIES[base], master


def test_no_remedy_ranks_a_bead_as_rarest_or_most_powerful():
    """The unsourced-superlative guard.

    "rarest and most powerful" (Life Path 1, shipped) is a purchase
    recommendation dressed as tradition, on a column §11 marks UNSOURCED.
    Scarcity language on an untraceable mapping steers users toward the
    priciest and most-counterfeited grade, so it must not come back.
    """
    banned = ("rarest", "most powerful", "most potent", "most effective")
    for number, remedy in _num._REMEDIES.items():
        if remedy is None:
            continue
        low = remedy.rudraksha.lower()
        for phrase in banned:
            assert phrase not in low, f"Life Path {number} rudraksha says {phrase!r}"
