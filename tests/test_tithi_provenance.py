"""#398 criterion 4: the tithi characters are labelled as what they are.

None of the four books this repo holds gives per-tithi characters
(`knowledge/vedic_reference.md` §29.10), and one shipped row actively
contradicted the corpus: Raman's *Muhurtha* Ch. II line 802 names the 4th
lunar day "unsuitable for undertaking any auspicious work", while both
`prompts/rashifal_single.txt` and `/panchang` told the reader it was a day to
"start small things". §29.8 called that "the sharpest tension §29 found
between shipped copy and the corpus" and recommended saying BOTH rather than
deleting either.

These tests pin that resolution on both surfaces. They are deliberately about
the CLAIM, not the wording: each asserts that a favourable-to-start phrasing
is absent and that the caution is present, so a rewrite that keeps the
substance passes and one that quietly restores the green light does not.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPT = ROOT / "src/astro_ai/prompts/rashifal_single.txt"
CHART = ROOT / "src/astro_ai/chart.py"

# Raman Ch. II line 802 lists the 4th, 8th, 12th and 14th. The rows that
# PRESCRIBE action are the ones that can contradict him; a character note that
# does not tell the reader to undertake anything cannot.
PANCHANG = ROOT / "src/astro_ai/templates/panchang.html"
QUALITY = ROOT / "src/astro_ai/rashifal_quality.py"


def _tithi_block() -> str:
    text = PROMPT.read_text()
    start = text.index("Tithi character")
    return text[start:text.index("Moon's nakshatra today", start)]


def test_the_prompt_does_not_present_the_table_as_classical():
    block = _tithi_block()
    assert "NOT A CLASSICAL RULE" in block, (
        "the tithi table must say it is not a classical rule — #398 criterion 4 "
        "allows sourced, removed or relabelled, and it is not sourceable"
    )
    assert "§29.10" in block, "the relabel must cite the section that found it unsourced"


def test_the_prompt_does_not_tell_the_reader_to_start_things_on_the_fourth():
    block = _tithi_block()
    line = next(l for l in block.splitlines() if "Chaturthi" in l)
    # the caution may wrap, so judge the row plus its continuation
    rows = block.split("- ")
    chaturthi = next(r for r in rows if r.startswith("Chaturthi"))
    assert "NOT a day to start things" in chaturthi, (
        f"Chaturthi must carry Raman's caution; got: {line!r}"
    )
    assert "start small things" not in chaturthi, (
        "the exact phrase §29.8 flagged is back in the prompt"
    )


def test_the_prompt_cautions_the_eighth_too():
    rows = _tithi_block().split("- ")
    ashtami = next(r for r in rows if r.startswith("Ashtami"))
    assert "NOT a day to launch or decide" in ashtami, (
        f"the 8th is on Ch. II line 802's list and must say so; got: {ashtami!r}"
    )
    assert "focused action" not in ashtami, (
        "the Ashtami row must not read as a licence to launch or decide"
    )


def test_panchang_says_both_on_the_fourth():
    src = CHART.read_text()
    block = src[src.index("_TITHI_SIGNIFICANCE"):]
    block = block[:block.index("\n}\n")]
    chaturthi = block[block.index('"Chaturthi"'):]
    chaturthi = chaturthi[:chaturthi.index('"Panchami"')]
    assert "Ganesh" in chaturthi, "the Ganesh association is real and must be kept"
    assert "Rikta" in chaturthi or "do not favour starting" in chaturthi, (
        "the /panchang row must carry the corpus caution — knowledge/ names this page"
    )
    assert "start small things" not in chaturthi, (
        "the exact phrase §29.8 flagged is back on /panchang"
    )


def test_panchang_drops_focused_action_on_the_eighth():
    src = CHART.read_text()
    block = src[src.index("_TITHI_SIGNIFICANCE"):]
    block = block[:block.index("\n}\n")]
    ashtami = block[block.index('"Ashtami"'):]
    ashtami = ashtami[:ashtami.index('"Navami"')]
    assert "focused action" not in ashtami, (
        "the 8th is on the avoid list; 'focused action' reads as a green light"
    )
    assert "avoid list" in ashtami or "inner resolve" in ashtami, (
        "the Ashtami row must state the caution or read inwardly"
    )


def test_the_knowledge_ledger_no_longer_says_flagged_not_corrected():
    ref = (ROOT / "src/astro_ai/knowledge/vedic_reference.md").read_text()
    where = ref[ref.index("sharpest tension"):]
    where = where[:where.index("### 29.9")]
    assert "**Flagged, not corrected**" not in where, (
        "the ledger still says this is uncorrected while the code is fixed — "
        "that is the drift CLAUDE.md warns about"
    )
    assert "CORRECTED 2026-10-30" in where, "the ledger must record when and how"


def test_the_panchang_explainer_does_not_call_the_characters_classical():
    """The fourth surface on the same page, found by QA on PR #606.

    The data cell at `panchang.html:103` was fixed and the explainer 158 lines
    below it still said "specific classical characters (… Chaturthi = Ganesh
    energy)" — the exact claim §29.10 found is in none of the four books, on
    the page `knowledge/` names by name. Fixing one artefact on a page and
    missing the other is the error this repo keeps hitting.
    """
    html = PANCHANG.read_text()
    assert "specific classical characters" not in html, (
        "the /panchang explainer calls the per-tithi characters classical; "
        "§29.10 is the finding that none of the four books gives them"
    )
    tithi_li = next(l for l in html.splitlines() if "Tithi (lunar day)" in l)
    assert "popular" in tithi_li.lower(), (
        f"the explainer must label the characters as association; got: {tithi_li[:160]!r}"
    )
    assert "unsuitable for starting" in tithi_li or "the other way" in tithi_li, (
        "the explainer names Chaturthi, so it must carry the caution the data "
        "cell carries"
    )


def test_the_eighth_is_attributed_rather_than_called_settled():
    """QA BUG-3a: `knowledge/` records the corpus as SPLIT on the 8th.

    Raman Ch. II line 802 places it on his avoid list; Rao's Table 79
    recommends it (Jaya -> 3, 8, 13). "the classical avoid list" asserted a
    settledness the corpus does not have.
    """
    src = CHART.read_text()
    block = src[src.index("_TITHI_SIGNIFICANCE"):]
    block = block[:block.index("\n}\n")]
    ashtami = block[block.index('"Ashtami"'):]
    ashtami = ashtami[:ashtami.index('"Navami"')]
    assert "the classical avoid list" not in ashtami, (
        "the 8th is contested in the corpus; naming 'the classical avoid list' "
        "asserts a settled position knowledge/ does not record"
    )
    assert "Raman" in ashtami, "the caution must say whose list it is"


def test_a_reading_that_leaks_an_internal_section_marker_is_caught():
    """QA BUG-4: the prompt now cites §29.10, and the contract requires it.

    CLAUDE.md: user-facing prose cites the tradition, never book-and-chapter.
    Nothing checked a generated reading for a leaked section marker before.
    """
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from astro_ai.rashifal_quality import check_reading
    leaked = check_reading("The texts say (\u00a729.10) this is not a day to start.",
                           tithi="Shukla Chaturthi")
    assert any("document section" in f for f in leaked["style"]), (
        f"a leaked section marker was not caught: {leaked}"
    )
    clean = check_reading("A quiet day to finish what is already open.",
                          tithi="Shukla Chaturthi")
    assert not any("document section" in f for f in clean["style"]), (
        f"a clean reading was flagged: {clean}"
    )
