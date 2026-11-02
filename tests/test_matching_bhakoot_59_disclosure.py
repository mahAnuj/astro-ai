"""The /matching Bhakoot 5/9 zero is disclosed as Bhagya's own convention (#177).

`matching.py:_BHAKOOT_DOSHA_NAMES` scores three Moon-sign distances 0/7: 6/8,
5/9 and 2/12. knowledge/matching.md (Muhurta Chintamani v.31, the text we hold)
gives only the 6/8 and 2/12 afflictions; 5/9 is in none of it, and astro-auditor's
2026-10-17 F4 found "nava panchama" absent from all 13 corpus books. The page
nonetheless called the 5/9 zero "classically an obstacle", cited "the classical
tradition" for its cancellation, and the explainer said 5-9 "traditionally"
scores zero.

DISCLOSURE ONLY. We do not know what value, if any, a tradition gives 5/9, so the
zero, the total and the verdict must not move; the owner decides whether it should.
Pinned, and kept apart on purpose:

  * the 5/9 result page says the zero is Bhagya's own convention and not from the
    text we hold, in English and in Hindi (the 6/8 and 2/12 pages must NOT say it
    -- those two ARE in the text, and their wording is unchanged byte for byte);
  * the 5/9 koota still awards 0.0/7 and the total/grade did not move;
  * no surface calls 5/9 classical or traditional.

Pairs: groom 1990-01-01 10:00 Mumbai (Moon in Aquarius) against a bride born on the
date below, 10:00 Mumbai. Totals were computed on origin/main (098db6e) BEFORE the
change and are hard-coded here, so a drift in the computation is also caught.
Driven through the real POST /matching route and template; the LLM is stubbed (#449).
"""
from __future__ import annotations

import html as _html
import re

import pytest

# bride birth date -> (Moon sign distance, total, verdict) as computed on origin/main.
FIVE_NINE = "1990-01-10"            # Gemini, 5/9, Vashya + Tara hold -> cancelled
FIVE_NINE_NADI = "1990-02-15"       # 5/9 with an afflicted Nadi
SIX_EIGHT = "1990-01-13"            # Cancer, 6/8
TWO_TWELVE = "1990-01-27"           # Capricorn, 2/12
_EXPECT = {
    FIVE_NINE: (20.0, "Avara"),
    FIVE_NINE_NADI: (19.0, "Avara"),
    SIX_EIGHT: (19.5, "Avara"),
    TWO_TWELVE: (19.0, "Avara"),
}

_EN_MARK = "not drawn from the classical text we hold"
_HI_MARK = "हमारे पास उपलब्ध शास्त्रीय ग्रंथ से नहीं लिया गया है"

# The koota notes for the two sourced distances, byte for byte as on origin/main.
_OLD_NOTE = ("Bhakoot dosha — the {dosha} distance between the Moon signs is "
             "classically an obstacle. Any cancellation is reported separately "
             "and does not change this score.")


def _charts(bride_date):
    from astro_ai.chart import compute_chart

    return (compute_chart("1990-01-01", "10:00", "Mumbai"),
            compute_chart(bride_date, "10:00", "Mumbai"))


def _guna(bride_date):
    from astro_ai.matching import compute_guna_milan

    return compute_guna_milan(*_charts(bride_date))


def _koota(guna):
    return next(k for k in guna.kootas if k.name == "Bhakoot")


def _post(client, stub_llm, bride_date, lang="en"):
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    r = client.post(f"/matching?lang={lang}", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00",
        "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": bride_date, "b_birth_time": "10:00",
        "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


# --- the disclosure is on the 5/9 page, and only there ---------------------------

@pytest.mark.parametrize("bride", [FIVE_NINE, FIVE_NINE_NADI])
@pytest.mark.parametrize("lang,mark", [("en", _EN_MARK), ("hi", _HI_MARK)])
def test_five_nine_page_discloses_the_zero_is_bhagyas_convention(
        client, stub_llm, bride, lang, mark):
    html = _post(client, stub_llm, bride, lang)
    assert mark in html, f"{lang}: the 5/9 convention disclosure is not rendered"
    # It sits inside the Bhakoot strip, after the dosha name, not elsewhere.
    assert html.index("Nava-panchama (5/9)") < html.index(mark)


@pytest.mark.parametrize("bride", [SIX_EIGHT, TWO_TWELVE])
@pytest.mark.parametrize("lang,mark", [("en", _EN_MARK), ("hi", _HI_MARK)])
def test_six_eight_and_two_twelve_pages_do_not_carry_it(client, stub_llm, bride, lang, mark):
    # Those two distances ARE in the text we hold; telling the reader their zero is
    # "our own convention" would be the same unsourced claim, inverted.
    html = _post(client, stub_llm, bride, lang)
    assert mark not in html
    assert "own convention" not in html


@pytest.mark.parametrize("bride,dosha", [
    (SIX_EIGHT, "Shadashtaka (6/8)"), (TWO_TWELVE, "Dwirdwadasha (2/12)")])
def test_sourced_distances_keep_their_note_byte_for_byte(bride, dosha):
    g = _guna(bride)
    assert _koota(g).note == _OLD_NOTE.format(dosha=dosha)
    assert g.bhakoot_dosha.name == dosha
    assert g.bhakoot_dosha.convention_only is False
    assert g.bhakoot_dosha.note.startswith(
        f"{dosha} Bhakoot dosha is present, but the classical tradition cancels it "
        "when any one of five conditions holds.")


# --- nothing that scores moved ----------------------------------------------------

@pytest.mark.parametrize("bride", list(_EXPECT))
def test_the_disclosure_moves_no_score_total_or_grade(client, stub_llm, bride):
    total, verdict = _EXPECT[bride]
    g = _guna(bride)
    assert _koota(g).awarded == 0.0 and _koota(g).max_points == 7
    assert (g.total_awarded, g.overall_verdict) == (total, verdict)
    html = _post(client, stub_llm, bride)
    assert g.overall_verdict_label in html


def test_five_nine_flag_is_set_only_for_five_nine():
    assert _guna(FIVE_NINE).bhakoot_dosha.convention_only is True
    assert _guna(FIVE_NINE_NADI).bhakoot_dosha.convention_only is True
    # A pair with no dosha at all.
    assert _guna("1990-01-05").bhakoot_dosha.convention_only is False
    assert _guna("1990-01-05").bhakoot_dosha.present is False


# --- no surface calls 5/9 classical -----------------------------------------------

_CLAIMS_CLASSICAL = re.compile(
    r"classically|classical tradition|classical cancelling|traditionally|"
    r"considered a dosha|are considered", re.I)


def test_five_nine_notes_do_not_call_it_classical():
    from astro_ai.matching import (_bhakoot_dosha, KootaScore)

    for bride in (FIVE_NINE, FIVE_NINE_NADI):
        g = _guna(bride)
        for note in (_koota(g).note, g.bhakoot_dosha.note):
            assert not _CLAIMS_CLASSICAL.search(note), note
            assert "own convention" in note, note
            assert "does not name" in note or "names only the 6/8 and 2/12" in note, note

    # The branch no birth chart in the scan reaches: dosha present, nothing cancels.
    def ks(name, awarded):
        return KootaScore(name=name, sanskrit="", max_points=8, awarded=awarded, note="")

    kootas = (ks("Vashya", 0.0), ks("Tara", 0.0), ks("Nadi", 8.0))
    d = _bhakoot_dosha(2, 10, kootas)           # Gemini/Aquarius: Mercury, Saturn
    assert d.present and not d.cancelled and d.convention_only
    assert not _CLAIMS_CLASSICAL.search(d.note), d.note
    assert "own convention" in d.note


def _sentences_mentioning(html, needle):
    html = re.sub(r"(?s)<(script|style)\b.*?</\1>|<!--.*?-->", " ", html)
    text = _html.unescape(re.sub(r"<[^>]+>", " ", html))
    text = re.sub(r"\s+", " ", text)
    return [s for s in re.split(r"(?<=[.!?;])\s+", text) if needle in s]


@pytest.mark.parametrize("path,needle", [
    ("/matching", "5-9"),
    ("/learn/kundali-matching-ashtakoot-guna-milan", "5th-9th"),
])
def test_explainers_do_not_call_five_nine_traditional(client, path, needle):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    hits = _sentences_mentioning(r.text, needle)
    assert hits, f"{path}: no sentence mentions {needle}; the guard would pass vacuously"
    for s in hits:
        assert "convention" in s, s
        # "6-8 and 2-12 traditionally score zero; Bhagya also scores 5-9 zero..." is
        # the one legal shape: the claim about tradition must not be what carries 5-9.
        assert not re.search(r"5-9[^;.]*\btraditional", s) and "(6-8, 5-9, 2-12)" not in s, s


def test_checker_catches_the_old_wording():
    # The guard must be able to go red: the exact sentences this change replaced.
    assert _CLAIMS_CLASSICAL.search(_OLD_NOTE.format(dosha="Nava-panchama (5/9)"))
    old = "Certain distances (6-8, 5-9, 2-12) traditionally score zero."
    assert "(6-8, 5-9, 2-12)" in old and "convention" not in old


def test_the_convention_text_names_no_book():
    from astro_ai.i18n import translate as t

    for lang in ("en", "hi"):
        text = t(lang, "matching_bhakoot_convention")
        assert text != "matching_bhakoot_convention", f"{lang}: key is missing"
        for book in ("Muhurta", "Muhurtha", "Chintamani", "Jataka", "Parashara", "Raman",
                     "मुहूर्त", "चिन्तामणि", "चिंतामणि", "पराशर"):
            assert book not in text, (lang, text)


# --- the "How this total was reached" row must not call a 5/9 cancellation classical ---
#
# QA round 1 on #656 (2d5114b): the strip and the koota note were fixed, but
# matching_result.html's totals footnote still said "cancelled by the classical
# conditions" for a cancelled 5/9 pair, on the same page as the strip saying the
# opposite. The claim checks above only read the two note strings, so nothing saw it.

def _flat(html):
    return re.sub(r"\s+", " ", _html.unescape(html))


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_totals_footnote_does_not_call_a_five_nine_cancellation_classical(
        client, stub_llm, lang):
    assert _guna(FIVE_NINE).bhakoot_dosha.cancelled is True   # the footnote renders
    page = _flat(_post(client, stub_llm, FIVE_NINE, lang))
    assert "cancelled by the classical conditions" not in page
    assert "cancelled by the conditions Bhagya applies to it" in page


def test_totals_footnote_keeps_its_wording_for_a_sourced_distance(client, stub_llm):
    # 6/8 is in the text we hold, so its cancellation stays "classical" -- exactly
    # when it is cancelled, as on origin/main.
    cancelled = _guna(SIX_EIGHT).bhakoot_dosha.cancelled
    page = _flat(_post(client, stub_llm, SIX_EIGHT))
    assert ("cancelled by the classical conditions" in page) is cancelled
    assert "conditions Bhagya applies to it" not in page
