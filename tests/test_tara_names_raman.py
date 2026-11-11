"""#879: the finder's nine Tara names are Raman's, and the page says so.

Source: B.V. Raman, *Muhurtha or Electional Astrology* (1948), lines 897-914 of the djvu text, quoted in
`knowledge/vedic_reference.md` 2A-ter: Janma, Sampat, Vipat, Kshema, Pratyak, Sadhana, Naidhana,
Mitra, Parama Mitra. Until #879 positions 5, 6, 7 and 9 were spelled Pratyari, Sadhaka, Vadha and
Ati-Mitra, and the page said the names had no held source.

The expected names are typed in here, not read back from muhurat.py. Grades are NOT touched by this
issue and are pinned in tests/test_janma_vivah_groom.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from astro_ai import muhurat
from astro_ai.muhurat import _tara_bala

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = (ROOT / "src" / "astro_ai" / "knowledge" / "vedic_reference.md").read_text(encoding="utf-8")
MUHURAT_SRC = (ROOT / "src" / "astro_ai" / "muhurat.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "src" / "astro_ai" / "templates" / "muhurat_finder.html").read_text(encoding="utf-8")
CORPUS = ROOT / "data" / "matching" / "raman-muhurtha-1948-electional-astrology_djvu.txt"

RAMAN_NAMES = ["Janma", "Sampat", "Vipat", "Kshema", "Pratyak", "Sadhana", "Naidhana", "Mitra",
               "Parama Mitra"]
RETIRED = ["Pratyari", "Sadhaka", "Vadha", "Ati-Mitra"]


def test_the_table_carries_ramans_nine_names_in_order():
    assert [muhurat._TARA_BALA_NAMES[i][0] for i in range(1, 10)] == RAMAN_NAMES


@pytest.mark.parametrize("name", RAMAN_NAMES)
def test_each_name_is_in_the_knowledge_file(name):
    assert name in KNOWLEDGE, name


def test_tara_bala_returns_ramans_names_for_the_four_renamed_positions():
    # Ashwini is nakshatra index 0; Bharani + k steps lands on position k+1 (mod 9).
    names = [_tara_bala("Ashwini", n)[1] for n in
             ("Rohini", "Mrigashira", "Ardra", "Ashlesha")]   # indices 3, 4, 5, 8 -> positions 4, 5, 6, 9
    assert names == ["Kshema", "Pratyak", "Sadhana", "Parama Mitra"]
    assert _tara_bala("Ashwini", "Punarvasu")[1:] == ("Naidhana", "avoid")   # index 6 -> position 7


def test_the_retired_spellings_are_gone_from_the_muhurat_module_and_the_finder():
    for old in RETIRED:
        assert old not in MUHURAT_SRC.split("_TARA_BALA_NAMES = {", 1)[1].split("}", 1)[0], old
        assert old not in TEMPLATE, old


def test_the_finder_no_longer_says_the_names_are_unsourced_and_lists_the_real_ones():
    assert "not sourced to a text this site holds" in TEMPLATE      # the good/excellent split only
    assert "(Pratyari, Sadhaka, Vadha, Ati-Mitra and the rest) are not sourced" not in TEMPLATE
    assert "The nine Tara names shown are Raman" in TEMPLATE
    assert "Sadhana, Mitra, Parama Mitra are auspicious; Vipat, Pratyak, Naidhana are avoided" in TEMPLATE


def test_the_module_comment_no_longer_says_the_source_is_not_held():
    head = MUHURAT_SRC.split("_TARA_BALA_NAMES = {", 1)[0]
    block = head[head.rindex("# Tara Bala (star strength)"):]
    assert "Source not held" not in block
    assert "Raman" in block


@pytest.mark.skipif(not CORPUS.exists(), reason="data/ is gitignored; Raman Muhurtha not on this checkout")
def test_the_names_are_in_the_djvu_text():
    text = "\n".join(CORPUS.read_text(encoding="utf-8", errors="replace").splitlines()[890:920])
    for name in ("Pratyak", "Sadhana", "Naidhana"):
        assert name in text, name
