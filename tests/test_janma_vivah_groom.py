"""#714, last slice: a Vivah GROOM on his own Janma day is no longer counted as a Tara pass.

Source: Raman, *Muhurtha or Electional Astrology* (1948), quoted with line numbers in
`knowledge/vedic_reference.md` 2A-ter. The book calls the day ruled by one's Janma star
"ordinarily held to be unfavourable for an election", groups the 1st star with the 3rd, 5th and
7th as days to avoid, lists marriage among the events it is inauspicious for, and says "For a
woman, Janma Nakshatra would be quite favourable for marriage". So `_couple_verdict` reads a
groom on Janma as avoid for the Tara test and leaves the bride's Janma a pass. The "nuptials ...
favourable without exception" sentence contradicts the same passage and is NOT used.

Expected values are typed from that reading, not read back from `muhurat.py`; every check calls
the real function the route calls. What is deliberately NOT changed is pinned too: the Tara table's
grades, `_tara_bala`, and the verdict for every non-Janma groom position.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from astro_ai import chart, muhurat
from astro_ai.muhurat import PartnerFactors, _couple_verdict, _tara_bala

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "src" / "astro_ai" / "knowledge" / "vedic_reference.md"
TEMPLATE = ROOT / "src" / "astro_ai" / "templates" / "muhurat_finder.html"
CORPUS = ROOT / "data" / "matching" / "raman-muhurtha-1948-electional-astrology_djvu.txt"

# The nine Tara grades as the code held them before #714; the NAMES of 5, 6, 7, 9 are Raman's since #879. Typed in.
TARA_TABLE = {
    1: ("Janma", "ok"), 2: ("Sampat", "good"), 3: ("Vipat", "avoid"), 4: ("Kshema", "good"),
    5: ("Pratyak", "avoid"), 6: ("Sadhana", "good"), 7: ("Naidhana", "avoid"),
    8: ("Mitra", "good"), 9: ("Parama Mitra", "excellent"),
}


def _p(position: int, chandra: str = "strong") -> PartnerFactors:
    name, grade = TARA_TABLE[position]
    return PartnerFactors(grade, name, chandra, "none", "", "")


def test_the_tara_table_is_unchanged():
    assert muhurat._TARA_BALA_NAMES == TARA_TABLE


def test_the_groom_rule_keys_on_the_tables_own_janma_name():
    assert muhurat._JANMA_TARA_NAME == TARA_TABLE[1][0] == "Janma"


def test_tara_bala_still_grades_own_star_ok():
    # The single-user personal match calls this and is unchanged.
    assert _tara_bala("Ashwini", "Ashwini") == (1, "Janma", "ok")
    # Position 1 recurs at the 10th and 19th star (mod 9), and the page says so.
    assert _tara_bala("Ashwini", "Magha")[1] == "Janma"        # the 10th star from Ashwini
    assert _tara_bala("Ashwini", "Bharani")[1] == "Sampat"     # sanity: not everything is Janma


@pytest.mark.parametrize("bride_position", [2, 4, 6, 8, 9])
def test_groom_janma_with_a_passing_bride_is_mixed_never_good_for_both(bride_position):
    assert _couple_verdict(_p(bride_position), _p(1)) == "mixed"


def test_groom_janma_with_a_janma_bride_is_mixed():
    assert _couple_verdict(_p(1), _p(1)) == "mixed"


@pytest.mark.parametrize("bride_position", [3, 5, 7])
def test_groom_janma_with_an_avoid_bride_is_avoid(bride_position):
    assert _couple_verdict(_p(bride_position), _p(1)) == "avoid"


def test_groom_janma_is_never_excellent_even_with_an_excellent_bride():
    assert _couple_verdict(_p(9), _p(1)) == "mixed"


def test_bride_janma_with_a_good_groom_is_unchanged_good_for_both():
    assert _couple_verdict(_p(1), _p(2)) == "good-for-both"
    assert _couple_verdict(_p(1), _p(4)) == "good-for-both"


def test_bride_janma_with_an_excellent_groom_is_unchanged_good_for_both():
    # Bride Janma is "ok", not "excellent", so the day was never excellent-for-both.
    assert _couple_verdict(_p(1), _p(9)) == "good-for-both"


def test_bride_janma_with_an_avoid_groom_is_unchanged_mixed():
    assert _couple_verdict(_p(1), _p(3)) == "mixed"


# Verdicts for every (bride position, groom position 2..9), both Chandra strong, typed in from the
# pre-#714 rule: avoid only when both avoid; excellent only when both excellent; good-for-both when
# both pass; mixed otherwise. Groom positions 2..9 are not Janma, so none of them may move.
_NON_JANMA_GROOM = {
    #  groom: bride 1..9
    2: ["good-for-both", "good-for-both", "mixed", "good-for-both", "mixed",
        "good-for-both", "mixed", "good-for-both", "good-for-both"],
    3: ["mixed", "mixed", "avoid", "mixed", "avoid", "mixed", "avoid", "mixed", "mixed"],
    4: ["good-for-both", "good-for-both", "mixed", "good-for-both", "mixed",
        "good-for-both", "mixed", "good-for-both", "good-for-both"],
    5: ["mixed", "mixed", "avoid", "mixed", "avoid", "mixed", "avoid", "mixed", "mixed"],
    6: ["good-for-both", "good-for-both", "mixed", "good-for-both", "mixed",
        "good-for-both", "mixed", "good-for-both", "good-for-both"],
    7: ["mixed", "mixed", "avoid", "mixed", "avoid", "mixed", "avoid", "mixed", "mixed"],
    8: ["good-for-both", "good-for-both", "mixed", "good-for-both", "mixed",
        "good-for-both", "mixed", "good-for-both", "good-for-both"],
    9: ["good-for-both", "good-for-both", "mixed", "good-for-both", "mixed",
        "good-for-both", "mixed", "good-for-both", "excellent-for-both"],
}


@pytest.mark.parametrize("groom_position", sorted(_NON_JANMA_GROOM))
def test_every_non_janma_groom_position_keeps_its_verdict(groom_position):
    got = [_couple_verdict(_p(b), _p(groom_position)) for b in range(1, 10)]
    assert got == _NON_JANMA_GROOM[groom_position]


def test_the_groom_rule_does_not_depend_on_chandra_bala():
    # A weak Chandra already made the day mixed; groom Janma with a bride avoid stays avoid.
    assert _couple_verdict(_p(3, "weak"), _p(1, "weak")) == "avoid"
    assert _couple_verdict(_p(2, "weak"), _p(1, "strong")) == "mixed"


def test_the_real_search_marks_a_groom_janma_day_mixed_not_good_for_both(monkeypatch):
    # End to end through find_candidates with two real charts. Groom: Moon in Uttara Phalguni
    # (1992-08-02 06:30 Delhi). 2026-12-30 is an Uttara Phalguni day; the bride (Moon in
    # Ashlesha) is Kshema, good, with both Chandra strong, so BEFORE #714 this day read
    # good-for-both (measured against main d384c9a: good-for-both -> mixed).
    monkeypatch.setattr(chart, "geocode_place", lambda place: (28.61, 77.21, "Asia/Kolkata"))
    bride = chart.compute_chart("1995-03-14", "12:00", "Delhi")
    groom = chart.compute_chart("1992-08-02", "06:30", "Delhi")
    assert next(p for p in groom.planets if p.name == "Moon").nakshatra == "Uttara Phalguni", "fixture"
    cands = muhurat.find_candidates("vivah", "Delhi", date(2026, 12, 29), days=3,
                                    personal_chart=bride, bride_chart=bride, groom_chart=groom)
    day = next(c for c in cands if c.d == date(2026, 12, 30))
    assert day.nakshatra == "Uttara Phalguni"
    assert day.couple.groom.tara_bala_name == "Janma"
    assert day.couple.groom.tara_bala == "ok"           # the chip is unchanged
    assert (day.couple.bride.tara_bala, day.couple.bride.chandra_bala) == ("good", "strong")
    assert day.couple.groom.chandra_bala == "strong"
    assert day.couple.combined_verdict == "mixed"
    # The single-user path is untouched: the bride's own personal match is not a groom reading.
    assert day.personal.tara_bala != "avoid"


def test_the_finder_paragraph_states_the_groom_bride_split_and_the_ghati_caveat():
    html = TEMPLATE.read_text()
    para = html[html.index("<strong>Tara Bala, Janma:</strong>"):].split("</p>", 1)[0]
    assert "a groom on the day ruled by his own birth star is no longer counted as a pass" in para
    assert "a bride on her own birth-star day still passes" in para
    assert "does not apply the exception Raman allows only in urgent cases" in para
    assert "ghatis" in para
    assert 'unclear on "nuptials", so that sentence is not used' in para
    assert "personal match still shows" in para


def _norm(text: str) -> str:
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)      # blockquote markers
    return re.sub(r"\s+", " ", text).strip()


# Sentences quoted in 2A-ter: (phrase, the range 2A-ter gives for its passage, the corpus lines the
# phrase itself sits on). The scan prints `5tli` for `5th` and a stray quote at line 1081; phrases
# are cut before those.
_QUOTES = [
    ("advisable to avoid a day that is ruled by the 1st, 3rd,", "1063-1066", 1063, 1065),
    ("ordinarily held to be unfavourable for an election", "1081-1082", 1081, 1082),
    ("inauspicious for war, sexual union, shaving, taking medical treatment, travel and marriage",
     "1083-1088", 1087, 1088),
    ("quite favourable for marriage", "1098-1099", 1098, 1099),
]


def _section() -> str:
    text = KNOWLEDGE.read_text()
    start = text.index("#### 2A-ter.")
    return text[start:text.index("\n---\n", start)]


def test_the_knowledge_section_exists_and_quotes_what_the_book_says():
    sec = _section()
    assert "2A-ter" in sec and "(#714)" in sec.split("\n", 1)[0]
    flat = _norm(sec)
    for phrase, section_range, _lo, _hi in _QUOTES:
        assert phrase in flat, phrase
        assert section_range in flat, section_range
    # The contradictory sentence is quoted only to be refused, and the section says so.
    assert "cannot be cited for the Vivah" in flat
    assert "For a woman, Janma Nakshatra would be quite favourable for marriage" in flat


def test_the_quoted_lines_are_where_the_section_says_when_the_corpus_is_present():
    # data/ is gitignored, so a fresh checkout may not hold it, and a skip fails verify_behaviour:
    # the knowledge-file checks above always run; this one adds the corpus check when it can.
    if not CORPUS.exists():
        return
    lines = CORPUS.read_text(errors="replace").splitlines()
    for phrase, _range, lo, hi in _QUOTES:
        assert _norm(phrase) in _norm(" ".join(lines[lo - 1:hi])), (phrase, lo, hi)
