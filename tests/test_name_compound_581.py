"""#581: `name_compound` is the ALL-LETTER whole-name total, and the page says so.

WHAT WAS WRONG
--------------
The issue found that the code sums every letter of the whole name and that its own
comment, and the page caption ("the unreduced total of a name"), presented that as
Cheiro's method. knowledge/numerology.md §14.2 records that Cheiro uses two
reductions: word SINGLES for Lloyd George (9 + 7 = 16, the code shows 43) and word
COMPOUNDS for Ramsay MacDonald (12 + 32 = 44, which is what the code computes).

chief's ruling (2026-11-10, Standing ruling 4 clause 3) was to keep the computation
and make the comment and caption truthful. Switching to word singles would move every
user's Bhagya score and rests on a per-word 11 -> 2 reduction that no held text
sources. These tests make a change to the value DELIBERATE: whoever moves it must
change these numbers in the same commit and say why.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from astro_ai import numerology as n

SRC = Path(n.__file__).parent


@pytest.mark.parametrize(
    "name, compound",
    [
        ("Lloyd George", 43),   # Cheiro's word-single reading says 16; see #581
        ("John Smith", 35),     # word singles say 17
        ("Ramsay MacDonald", 44),  # the example that agrees with the all-letter total
        ("Baldwin", 22),        # single word: no ambiguity
    ],
)
def test_name_compound_is_the_all_letter_total(name, compound):
    assert n.compute(name, "1990-01-01", target_year=2026).name_compound == compound


def test_bhagya_score_for_fixed_names_is_unchanged():
    """The caption fix must not move a headline score (chief ruling, item 4).

    Lloyd George moved 53 -> 55 on 2026-11-10 under #584, which removed the
    -2 for compound 43 (it sat in the old challenged tier); the other two
    carry no compound term either way.
    """
    expected = {"Lloyd George": 55, "John Smith": 58, "Baldwin": 58}
    for name, value in expected.items():
        r = n.compute(name, "1990-01-01", target_year=2026)
        assert n.compute_numerology_bhagya_score(r).value == value


def test_caption_does_not_claim_an_unreduced_whole_name_total_is_the_tradition():
    html = (SRC / "templates" / "numerology.html").read_text(encoding="utf-8")
    assert "unreduced total of a name" not in html
    # both branches of the caption say the total is over the whole name and that
    # the tradition also reads words separately
    assert html.count("also reads each word of a name on its own") == 2


def test_code_comment_names_both_of_cheiros_reductions():
    text = (SRC / "numerology.py").read_text(encoding="utf-8")
    block = text[text.index("# Compound name number (before reduction)"):text.index("name_raw = sum(")]
    assert "ALL-LETTER" in block
    assert "word SINGLES" in block and "word COMPOUNDS" in block
