"""#843: a multi-word name shows each word's own compound (Cheiro, knowledge/numerology.md §14.2).

The whole-name compound and every Bhagya score stay exactly as #581 pinned them."""

from __future__ import annotations

from pathlib import Path

import pytest

from astro_ai import numerology as n

SRC = Path(n.__file__).parent


def _wc(name):
    return n.compute(name, "1990-01-01", target_year=2026).word_compounds


def test_lloyd_george_words_are_18_and_25():
    # §14.2: "Lloyd" alone = 18, "George" alone = 25
    assert [(w, c) for w, c, _ in _wc("Lloyd George")] == [("Lloyd", 18), ("George", 25)]


def test_ramsay_macdonald_words_are_12_and_32():
    assert [(w, c) for w, c, _ in _wc("Ramsay MacDonald")] == [("Ramsay", 12), ("MacDonald", 32)]


def test_each_word_carries_its_compound_meaning():
    for _, c, meaning in _wc("Lloyd George"):
        assert meaning and meaning == n._COMPOUND_NUMBER_MEANING[c]


def test_one_word_name_has_no_word_panel():
    assert _wc("Baldwin") == ()


def test_word_outside_the_10_52_series_is_left_out():
    # "Al" = 1 + 3 = 4: no compound; "Lloyd" still shows
    assert [w for w, _, _ in _wc("Al Lloyd")] == ["Lloyd"]


def test_blank_and_punctuation_words_do_not_count_as_words():
    assert _wc("Lloyd  - ") == ()


def test_word_count_is_bounded():
    assert len(_wc(" ".join(["Lloyd"] * 20))) == n._MAX_WORD_COMPOUNDS


def test_whole_name_compound_and_scores_are_untouched():
    r = n.compute("Lloyd George", "1990-01-01", target_year=2026)
    assert r.name_compound == 43
    assert n.compute_numerology_bhagya_score(r).value == 53


def test_template_renders_the_panel_only_with_words():
    html = (SRC / "templates" / "numerology.html").read_text(encoding="utf-8")
    assert "{% if reading.word_compounds %}" in html
    assert "for word, compound, meaning in reading.word_compounds" in html


def _post(client, name):
    return client.post("/numerology", data={"name": name, "birth_date": "1990-01-01"})


def test_route_renders_each_word_for_a_two_word_name(client):
    r = _post(client, "Lloyd George")
    assert r.status_code == 200
    assert 'id="word-compounds"' in r.text
    assert "Lloyd &mdash; Compound 18" in r.text and "George &mdash; Compound 25" in r.text
    assert "Compound 43" in r.text  # the whole-name compound is still there


def test_route_has_no_word_panel_for_a_one_word_name(client):
    r = _post(client, "Baldwin")
    assert r.status_code == 200
    assert 'id="word-compounds"' not in r.text
