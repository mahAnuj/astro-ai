"""/matching names its school, and the narrative prompt stops calling 5/9 classical (#177).

Two owner-sweep items (2026-11-06), pinned together because both are about what
the page and the narrative claim the tradition says:

  * `matching.txt` told the model, for a Bhakoot zero, to "mention the classical
    concern about marital harmony". A 5/9 zero is Bhagya's own convention
    (`matching.py:_bhakoot_convention_only`; the text we hold names only 6/8 and
    2/12 -- #656), so the narrative could re-assert in prose the claim the result
    page had just retracted. The prompt now defers to the Bhakoot row's note,
    which already carries the right wording for each distance.
  * the result page never said which system it scores by. knowledge/matching.md
    records the choice (North Indian 36-guna Ashtakoota; "Do not blend
    traditions"). One sentence, en and hi, no book named. And
    `matching_bands_note` called "the eight koota scores and their weights" the
    classical part, which is inexact next to the 5/9 zero.

DISCLOSURE ONLY: no score, threshold or verdict moves. Driven through the real
POST /matching route and template; the LLM is stubbed (#449).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_PROMPT = Path(__file__).resolve().parents[1] / "src/astro_ai/prompts/matching.txt"

_EN_SCHOOL = "North Indian 36-guna Ashtakoota system"
_HI_SCHOOL = "उत्तर भारतीय 36 गुणों वाली अष्टकूट पद्धति"
_BOOKS = ("Muhurta", "Muhurtha", "Chintamani", "Jataka", "Parashara", "Raman",
          "मुहूर्त", "चिन्तामणि", "चिंतामणि", "पराशर")


def _post(client, stub_llm, lang="en"):
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    r = client.post(f"/matching?lang={lang}", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00",
        "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": "1990-01-10", "b_birth_time": "10:00",
        "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


# --- the page names its school -----------------------------------------------------

@pytest.mark.parametrize("lang,mark", [("en", _EN_SCHOOL), ("hi", _HI_SCHOOL)])
def test_result_page_names_the_school(client, stub_llm, lang, mark):
    html = _post(client, stub_llm, lang)
    assert mark in html, f"{lang}: the school sentence is not rendered"
    # It sits with the scale legend and the band disclosure, not somewhere else.
    assert 0 < html.index(mark) - html.index("Madhyam</span>") < 1500


def test_school_sentence_has_both_languages_and_no_latin_prose_in_hindi():
    from astro_ai.i18n import translate as t

    en, hi = t("en", "matching_school_note"), t("hi", "matching_school_note")
    assert en != "matching_school_note" and hi != "matching_school_note"
    assert en != hi
    # Hindi may carry the digits "36", never a Latin-script word.
    assert not re.search(r"[A-Za-z]", hi), hi
    for text in (en, hi):
        for book in _BOOKS:
            assert book not in text, text


# --- the bands note no longer calls the whole of the scoring classical ------------

@pytest.mark.parametrize("lang", ["en", "hi"])
def test_bands_note_admits_the_convention_exception(lang):
    from astro_ai.i18n import translate as t

    text = t(lang, "matching_bands_note")
    assert "are the classical part" not in text
    assert "शास्त्र-आधारित भाग है" not in text
    assert ("except where a note says Bhagya counts a score by its own rule" in text
            if lang == "en" else "सिवाय वहाँ जहाँ" in text), text


# --- the prompt no longer tells the model a Bhakoot zero is classical -------------

def _marriage_foundation_line():
    lines = [l for l in _PROMPT.read_text(encoding="utf-8").splitlines()
             if "If Bhakoot Dosha is present" in l]
    assert len(lines) == 1, "the Bhakoot instruction is not on exactly one line"
    return lines[0]


def test_prompt_does_not_call_the_bhakoot_concern_classical_unconditionally():
    line = _marriage_foundation_line()
    assert "mention the classical concern about marital harmony" not in line
    assert not re.search(r"Bhakoot[^.]*\bmention the classical concern", line)
    # The Nadi sentence is a different (sourced) claim and is left alone.
    assert "classical concern about health and progeny" in line


def test_prompt_defers_to_the_bhakoot_row_note_for_a_convention_zero():
    line = _marriage_foundation_line()
    assert "Follow the Bhakoot row's note" in line
    assert "Bhagya's own convention" in line
    assert "do not attribute it to the tradition" in line


def test_prompt_wording_matches_what_the_note_actually_says():
    # The prompt tells the model to look for "Bhagya's own convention" in the note;
    # that must be the phrase the 5/9 koota note really carries, and the 6/8 note
    # (which IS in the text we hold) must not carry it.
    from astro_ai.chart import compute_chart
    from astro_ai.matching import compute_guna_milan

    def note(bride):
        g = compute_guna_milan(compute_chart("1990-01-01", "10:00", "Mumbai"),
                               compute_chart(bride, "10:00", "Mumbai"))
        return next(k for k in g.kootas if k.name == "Bhakoot").note

    assert "Bhagya's own convention" in note("1990-01-10")          # 5/9
    assert "Bhagya's own convention" not in note("1990-01-13")      # 6/8
    assert "classically an obstacle" in note("1990-01-13")


def test_the_bhakoot_note_reaches_the_model_in_the_user_message():
    # The prompt's "follow the note" instruction is only meaningful if the note is
    # in the message the model reads.
    from astro_ai.chart import compute_chart
    from astro_ai.llm import _format_matching_message
    from astro_ai.matching import compute_guna_milan

    g, b = (compute_chart("1990-01-01", "10:00", "Mumbai"),
            compute_chart("1990-01-10", "10:00", "Mumbai"))
    msg = _format_matching_message("A", "B", g, b, compute_guna_milan(g, b))
    assert "Bhakoot: 0.0/7 — Bhakoot dosha" in msg
    assert "Bhagya's own convention" in msg


def test_the_edited_prompt_changes_the_matching_cache_key():
    # Cached readings are keyed on the prompt file's hash (cache.fingerprint_prompt),
    # so the old, "classical"-saying readings are not served after this edit.
    import hashlib
    from astro_ai import cache

    fp = cache.fingerprint_prompt(_PROMPT)
    assert fp.endswith(hashlib.sha256(_PROMPT.read_bytes()).hexdigest()[:8])


def test_i18n_symmetry_for_the_new_key():
    from astro_ai import i18n

    tables = [v for k, v in vars(i18n).items()
              if isinstance(v, dict) and "matching_bands_note" in v]
    assert len(tables) >= 2
    assert all("matching_school_note" in t for t in tables)
