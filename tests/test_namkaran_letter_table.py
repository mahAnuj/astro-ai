"""#1062: the Namkaran first-letter table is compared against Raman's printed one, and the page says so.

Raman, Muhurtha (1948), Appendix "Nama Nakshatra, Finding" (data/matching/raman-muhurtha-1948-
electional-astrology_djvu.txt L6969-7110, printed pp. 105-106) prints 27 lines of four syllables,
one per pada. muhurat.py used to say "no book in the corpus carries this table", and the finder
page credited the syllable to Muhurta Chintamani, whose naming table is not held. Neither was true.

The 27 rows below are Raman's OCR text exactly as the djvu prints it, so this file does not need
the (gitignored) book to run. The verdicts are knowledge/vedic_reference.md 29.13's, and the test
reads that section so the two cannot drift apart. Nothing here edits a row of `_NAMKARAN_LETTERS`:
the OCR is not good enough to settle the rows 29.13 calls ambiguous.
"""

import re
from pathlib import Path

import pytest

from astro_ai import muhurat as m

SRC = Path(m.__file__).parent
MUHURAT_PY = (SRC / "muhurat.py").read_text(encoding="utf-8")
FINDER = (SRC / "templates" / "muhurat_finder.html").read_text(encoding="utf-8")
REFERENCE = (SRC / "knowledge" / "vedic_reference.md").read_text(encoding="utf-8")

# Raman's lines 1-27, in his nakshatra order (Aswini ... Revati; the list printed after the table
# at L7038-7089). Verbatim OCR from L6983-7035: the stray "." in row 3, the ";" in row 11, the
# "Dc"/"Ec" for De/Ee and the "Syatn" in row 26 are the book's text as the scan was read.
RAMAN_ROWS = {
    "Ashwini":           "Chu, Chay, Cho, La",
    "Bharani":           "Le, Lu, Lay, Lo",
    "Krittika":          "Aa, Ec. U, A",
    "Rohini":            "O, Va, Ve, Vu",
    "Mrigashira":        "Vay, Vo, Ka, Ki",
    "Ardra":             "Ku, Kham, Jna, Cha",
    "Punarvasu":         "Kay, Ko, Ha, Hi",
    "Pushya":            "Hu, Hay, Ho, Da",
    "Ashlesha":          "Dc, Du, Day, Do",
    "Magha":             "Ma, Me, Mu, May",
    "Purva Phalguni":    "Mo; Ta, Ti, Tu",
    "Uttara Phalguni":   "Tay, To, Pa, Pi",
    "Hasta":             "Pu, Shaw, Na, Dha",
    "Chitra":            "Pay, Po, Ra, Ri",
    "Swati":             "Ru, Ray, Ro, Tha",
    "Vishakha":          "Thi, Thu, Thay, Tho",
    "Anuradha":          "Na, Ni, Nu, Nay",
    "Jyeshtha":          "No, Ya, Ye, Yu",
    "Mula":              "Yay, Yo, Ba, Bi",
    "Purva Ashadha":     "Bu, Thha, Bha, Dha",
    "Uttara Ashadha":    "Bay, Bo, Ja, Ji",
    "Shravana":          "Ju, Jay, Jo, Gha",
    "Dhanishta":         "Ga, Gi, Gu, Gay",
    "Shatabhisha":       "Go, Sa, Si, Su ,",
    "Purva Bhadrapada":  "Say, So, Tha, Thi",
    "Uttara Bhadrapada": "Thu, Syatn, Cha, Tha",
    "Revati":            "Thay, Tho, Cha, Chi",
}

# 29.13's classification of those 27 rows (15 clear + 3 under Th=D / B=Bh + 1 + 2 + 6).
AGREES_PLAIN = (
    "Ashwini", "Bharani", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Chitra", "Anuradha", "Jyeshtha", "Dhanishta",
    "Shatabhisha",
)
# These match only if Raman's "Th" means D and his "B" means Bh. Kept as its own group because
# the same reading is exactly what cannot settle Vishakha and Mula, so it is a reading, not a rule.
AGREES_UNDER_TH_D_B_BH = ("Purva Bhadrapada", "Revati", "Uttara Ashadha")
DIFFERS = ("Shravana",)
DIFFERS_OR_UNREADABLE = ("Ardra", "Uttara Bhadrapada")
UNCLEAR = ("Krittika", "Hasta", "Swati", "Vishakha", "Mula", "Purva Ashadha")

# The one OCR repair the matching rows need: the scan reads Raman's "De" as "Dc" (L6999).
OCR_REPAIRS = {"Dc": "De"}


def raman_syllables(nakshatra: str) -> list[str]:
    return [s.strip(" ;.") for s in re.split(r"[,;.]\s*", RAMAN_ROWS[nakshatra]) if s.strip(" ;.")]


def to_finder_spelling(syllable: str, th_is_d_and_b_is_bh: bool = False) -> str:
    """Raman's spelling -> the finder's. Derived from rows that agree outright:
    "ay" is our "e" (Chay/Che, Day/De, Tay/Te, Kay/Ke), and a bare final "e" is our "i"
    (Le/Li, Ve/Vi, Me/Mi, Ye/Yi). With the flag, "Th" is read as D and a bare "B" as Bh.
    """
    syllable = OCR_REPAIRS.get(syllable, syllable)
    if th_is_d_and_b_is_bh:
        if syllable.startswith("Th"):
            syllable = "D" + syllable[2:]
        elif syllable.startswith("B") and not syllable.startswith("Bh"):
            syllable = "Bh" + syllable[1:]
    if syllable.endswith("ay"):
        return syllable[:-2] + "e"
    if syllable.endswith("e") and len(syllable) > 1:
        return syllable[:-1] + "i"
    return syllable


def _matches(nakshatra: str, th_d_b_bh: bool) -> bool:
    rows = [to_finder_spelling(s, th_d_b_bh) for s in raman_syllables(nakshatra)]
    return tuple(rows) == m._NAMKARAN_LETTERS[nakshatra]


def test_every_code_nakshatra_has_a_recorded_raman_row():
    assert len(m._NAMKARAN_LETTERS) == 27
    assert set(RAMAN_ROWS) == set(m._NAMKARAN_LETTERS), set(RAMAN_ROWS) ^ set(m._NAMKARAN_LETTERS)
    for name in RAMAN_ROWS:
        assert len(raman_syllables(name)) == 4, name


def test_every_row_has_exactly_one_verdict():
    groups = (AGREES_PLAIN, AGREES_UNDER_TH_D_B_BH, DIFFERS, DIFFERS_OR_UNREADABLE, UNCLEAR)
    flat = [n for g in groups for n in g]
    assert sorted(flat) == sorted(RAMAN_ROWS), "a nakshatra is unclassified or classified twice"
    assert len(flat) == 27


def test_the_verdict_counts_are_the_ones_the_reference_section_states():
    section = REFERENCE.split("#### The Namkaran first-letter table")[1].split("#### Business start")[0]
    assert "(18 of 27)" in section
    assert "15 clear, 3 more under that reading, 6 ambiguous, 3 different" in section
    assert len(AGREES_PLAIN) + len(AGREES_UNDER_TH_D_B_BH) == 18
    assert len(AGREES_PLAIN) == 15 and len(AGREES_UNDER_TH_D_B_BH) == 3
    assert len(UNCLEAR) == 6
    assert len(DIFFERS) + len(DIFFERS_OR_UNREADABLE) == 3
    for name in AGREES_PLAIN + AGREES_UNDER_TH_D_B_BH + DIFFERS + DIFFERS_OR_UNREADABLE + UNCLEAR:
        assert name in section, name


@pytest.mark.parametrize("name", AGREES_PLAIN)
def test_rows_that_agree_match_under_the_vowel_spellings_alone(name):
    assert _matches(name, th_d_b_bh=False), (name, RAMAN_ROWS[name], m._NAMKARAN_LETTERS[name])


@pytest.mark.parametrize("name", AGREES_UNDER_TH_D_B_BH)
def test_rows_that_need_th_as_d_and_b_as_bh_match_only_under_that_reading(name):
    assert _matches(name, th_d_b_bh=True), (name, RAMAN_ROWS[name], m._NAMKARAN_LETTERS[name])
    assert not _matches(name, th_d_b_bh=False), f"{name} matches plainly; move it to AGREES_PLAIN"


# Mula (Yay, Yo, Ba, Bi) is the one row 29.13 leaves ambiguous that DOES equal the finder's
# (Ye, Yo, Bha, Bhi) under the same B=Bh reading that rescues Uttara Ashadha. It stays in UNCLEAR
# because that reading is the thing in doubt (Raman's "Ba, Bi" may be plain Ba, Bi), so counting
# it would build the 18 on the assumption it is testing. Recorded here so the test is not hiding it.
UNCLEAR_BUT_MATCHES_UNDER_THE_READING = ("Mula",)


@pytest.mark.parametrize("name", DIFFERS + DIFFERS_OR_UNREADABLE + UNCLEAR)
def test_rows_the_reference_does_not_call_agreeing_match_under_neither_reading(name):
    # If the spelling rules ever start matching one of these, the verdict is stale: promote it
    # deliberately rather than let a mapping tweak do it.
    assert not _matches(name, False), name
    if name in UNCLEAR_BUT_MATCHES_UNDER_THE_READING:
        assert _matches(name, True), f"{name} no longer matches under Th=D / B=Bh; drop the exception"
    else:
        assert not _matches(name, True), name


def test_shravana_is_a_different_set_not_a_different_spelling():
    assert m._NAMKARAN_LETTERS["Shravana"] == ("Khi", "Khu", "Khe", "Kho")
    assert tuple(to_finder_spelling(s) for s in raman_syllables("Shravana")) == \
        m._NAMKARAN_ALTERNATE_LETTERS["Shravana"] == ("Ju", "Je", "Jo", "Gha")
    assert not set(m._NAMKARAN_ALTERNATE_LETTERS["Shravana"]) & set(m._NAMKARAN_LETTERS["Shravana"])


def test_only_shravana_has_an_alternate_set():
    assert set(m._NAMKARAN_ALTERNATE_LETTERS) == {"Shravana"}
    assert m._namkaran_alternate_letters("Shravana") == ("Ju", "Je", "Jo", "Gha")
    assert m._namkaran_alternate_letters("Bharani") == ()
    assert m._namkaran_alternate_letters("") == ()


def test_the_not_held_comment_is_gone_and_the_raman_citation_is_there():
    assert "no book in the corpus carries this table" not in MUHURAT_PY
    block = MUHURAT_PY.split("_NAMKARAN_LETTERS: dict")[0][-1800:]
    assert "Nama" in block and "Nakshatra, Finding" in block
    assert "L6969-7110" in block and "18 of 27" in block
    assert "vedic_reference.md 29.13" in block


def test_the_template_no_longer_credits_muhurta_chintamani():
    assert "Chintamani" not in FINDER
    assert "Per Muhurta" not in FINDER


# 2026-01-20 06:00 Delhi: Moon in Shravana pada 3. 2026-01-27 06:00 Delhi: Moon in Bharani pada 4.
# Measured with compute_chart; both are real charts, not stubs.
def _namkaran_page(dob: str) -> str:
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    r = TestClient(app).post("/muhurat", data={
        "event_type": "namkaran", "city": "Delhi", "start_date": "2026-12-01", "days": "3",
        "child_dob": dob, "child_time": "06:00", "child_place": "Delhi, India",
    })
    assert r.status_code == 200, r.status_code
    return r.text


def _visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_a_shravana_child_is_shown_both_sets_and_the_convention():
    html = _namkaran_page("2026-01-20")
    text = _visible(html)
    assert "Shravana" in text and "Khe" in text  # the finder's primary, pada 3
    assert "Two sets of syllables circulate for Shravana" in text
    assert "Ju · Je · Jo · Gha" in text
    assert "Khi · Khu · Khe · Kho" in text
    assert "Chintamani" not in html


def test_a_child_in_another_nakshatra_is_not_shown_an_alternate_set():
    html = _namkaran_page("2026-01-27")
    text = _visible(html)
    assert "Bharani" in text and "Lo" in text
    assert "Two sets of syllables circulate" not in text
    assert "Ju · Je" not in text
    assert "Chintamani" not in html
    # the honest attribution is still there
    assert "commonly circulated" in text and "Raman" in text
