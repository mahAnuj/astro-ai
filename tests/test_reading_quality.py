"""The natal reading verdict (#327 slice 1, #966): every fixture is a rule natal.txt states.

`reading_quality` only measures, so what needs pinning is WHAT it measures: that a
planet name, a sign name, a house number, a decimal, a classical-text name and a
banned word each fail a reading, that the seeker's own name does not, and that the
terms it checks have not drifted from the prompt that states them. The drift tests
parse `prompts/natal.txt` itself -- a ban added to the prompt without the linter fails
here, instead of the rate quietly reading better than the output is."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import reading_quality as rq
from astro_ai.chart import RASHIS

NATAL = (Path(rq.__file__).parent / "prompts" / "natal.txt").read_text()

_FILLER = ("The years ahead ask for steady effort and plain honesty with yourself. "
           "Small habits kept daily matter more than big plans made once. ")


def _clean(n: int = 7, extra: str = "", name_in_prose: str = "") -> str:
    """A reading with `n` sections and nothing the prompt bans, ~1,000 words."""
    body = _FILLER * 8
    sections = [f"## Section {i}\n{body}" for i in range(1, n + 1)]
    sections[0] += f"\n{extra} {name_in_prose}"
    return "\n\n".join(sections)


def _kinds(verdict: dict) -> set[str]:
    return {h["kind"] for h in verdict["banned"]}


def test_a_clean_seven_section_english_reading_passes():
    v = rq.check_natal_reading(_clean(), n_sections=7)
    assert v["ok"] is True and v["banned"] == [], v
    assert v["sections"] == 7
    assert 920 <= v["words"] <= 1380, f"fixture left the prompt's band: {v['words']}"


def test_ok_requires_exactly_seven_sections():
    clean = _clean()
    assert rq.check_natal_reading(clean, n_sections=7)["ok"] is True
    for n in (1, 6, 8):
        v = rq.check_natal_reading(clean, n_sections=n)
        assert v["ok"] is False and v["banned"] == [], (n, v)


def test_a_planet_name_fails_the_verdict():
    v = rq.check_natal_reading(_clean(extra="Saturn presses on your career."), n_sections=7)
    assert v["ok"] is False
    assert {"kind": "planet", "term": "Saturn"} in v["banned"], v


def test_every_planet_natal_txt_bans_is_caught():
    line = next(l for l in NATAL.splitlines() if "DO NOT name specific planets:" in l)
    names = [n.strip(" .") for n in line.split(":", 1)[1].split(",")]
    assert len(names) == 9, f"natal.txt's planet line no longer lists nine names: {names}"
    for name in names:
        v = rq.check_natal_reading(_clean(extra=f"Your {name} is strong."), n_sections=7)
        assert "planet" in _kinds(v), f"natal.txt bans {name!r} and the checker lets it through"


def test_every_sign_name_english_and_sanskrit_is_caught():
    parts = [p for label in RASHIS for p in re.findall(r"[A-Za-z]+", label)]
    assert len(parts) == 24
    for part in parts:
        v = rq.check_natal_reading(_clean(extra=f"A {part} nature shows."), n_sections=7)
        assert "sign" in _kinds(v), f"{part!r} is not caught as a sign"


def test_a_seeker_named_sunil_is_not_a_planet_hit():
    # `Sunil` merely contains `Sun`; the word boundary alone clears it.
    v = rq.check_natal_reading(_clean(name_in_prose="Sunil, you tend to carry others."),
                               n_sections=7)
    assert v["ok"] is True, v


def test_a_seeker_named_meena_is_not_flagged_as_a_sign_but_a_stranger_is():
    # Meena is Pisces. The prompt tells the model to use the name naturally.
    text = _clean(name_in_prose="Meena, you tend to carry others.")
    assert rq.check_natal_reading(text, n_sections=7, name="Meena Rao")["ok"] is True
    assert "sign" in _kinds(rq.check_natal_reading(text, n_sections=7, name=""))
    # ...and only the NAME is excused, not the rest of the reading.
    other = _clean(extra="Saturn.", name_in_prose="Meena")
    assert "planet" in _kinds(rq.check_natal_reading(other, n_sections=7, name="Meena"))


def test_house_numbers_are_flagged_but_house_of_service_is_not():
    for bad in ("your 10th house", "your 2nd house", "the second house", "house 7"):
        v = rq.check_natal_reading(_clean(extra=f"It sits in {bad}."), n_sections=7)
        assert "house_number" in _kinds(v), f"{bad!r} not flagged"
    ok = rq.check_natal_reading(
        _clean(extra="The ruler of your career house sits in the house of service."),
        n_sections=7)
    assert ok["ok"] is True, ok


def test_a_decimal_age_is_flagged_but_an_iso_date_is_not():
    bad = rq.check_natal_reading(_clean(extra="from 34.5 to 51"), n_sections=7)
    assert {"kind": "decimal_age", "term": "34.5"} in bad["banned"], bad
    ok = rq.check_natal_reading(
        _clean(extra="over the coming months until 2027-03-15, from 34 to 51"), n_sections=7)
    assert ok["ok"] is True, ok


def test_a_classical_text_name_or_chapter_citation_is_flagged():
    for bad in ("Jataka Parijata", "BPHS", "Phaladeepika", "Parashara", "Mansagari",
                "Rao Ch.11", "see chapter 4"):
        v = rq.check_natal_reading(_clean(extra=f"As {bad} says."), n_sections=7)
        assert "classical_text" in _kinds(v), f"{bad!r} not flagged"


def test_the_classical_texts_in_natal_txt_are_all_caught():
    line = next(l for l in NATAL.splitlines() if "DO NOT name classical texts" in l)
    inner = re.search(r"\((.*?)\)", line).group(1)
    names = [n.strip(' "') for n in inner.split(",")]
    assert len(names) == 6, f"natal.txt's text list changed: {names}"
    for name in names:
        v = rq.check_natal_reading(_clean(extra=f"As {name} says."), n_sections=7)
        assert "classical_text" in _kinds(v), f"natal.txt bans {name!r}; not caught"


def test_a_banned_word_is_flagged_in_any_form():
    for bad in ("Moreover", "this will amplify", "you navigate", "navigating life",
                "her propensity", "manifests", "unlocking", "intricacies"):
        v = rq.check_natal_reading(_clean(extra=f"{bad} here."), n_sections=7)
        assert "banned_word" in _kinds(v), f"{bad!r} not flagged"
    # `favourable` is a different word from the banned `favourability`.
    assert rq.check_natal_reading(_clean(extra="A favourable year."), n_sections=7)["ok"]


def test_every_banned_word_natal_txt_lists_is_caught():
    para = next(p for p in NATAL.split("\n\n") if p.startswith("BANNED WORDS"))
    terms = re.findall(r'"([a-z]+)"\s*→', para)
    assert len(terms) == 17, f"natal.txt's BANNED WORDS list changed size: {terms}"
    for term in terms:
        v = rq.check_natal_reading(_clean(extra=f"It will {term} the way."), n_sections=7)
        assert "banned_word" in _kinds(v), f"natal.txt bans {term!r}; not caught"


def test_hindi_reading_with_six_sections_fails_and_has_no_word_count():
    v = rq.check_natal_reading(_clean(n=6), n_sections=6, lang="hi")
    assert v["ok"] is False
    assert v["words"] is None, "the 920-1380 band is an English count"
    seven = rq.check_natal_reading(_clean(n=7), n_sections=7, lang="hi")
    assert seven["ok"] is True and seven["words"] is None


def test_banned_by_kind_reports_counts_and_never_terms():
    v = rq.check_natal_reading(_clean(extra="Saturn and Mars, moreover 34.5"), n_sections=7)
    counts = rq.banned_by_kind(v)
    assert counts == {"planet": 2, "decimal_age": 1, "banned_word": 1}, counts
    assert rq.banned_by_kind(rq.check_natal_reading(_clean(), n_sections=7)) == {}


# natal.txt line 54 lists six phrases; "natal Moon" is caught by the planet rule (`Moon`),
# so it is deliberately not a `forbidden_phrase` and is excluded from the per-phrase set.
_PHRASE_FIXTURES = {
    "transit": "A long transit is ending.",
    "gochar": "The gochar of the year helps.",
    "natal Lagna": "Your natal Lagna shapes this.",
    "Bhava": "Each Bhava carries a theme.",
    "lord of the": "The lord of the home matters.",
}


def test_each_jargon_phrase_fails_the_verdict_as_a_forbidden_phrase():
    for phrase, sentence in _PHRASE_FIXTURES.items():
        v = rq.check_natal_reading(_clean(extra=sentence), n_sections=7)
        assert v["ok"] is False, f"{phrase!r} passes"
        assert "forbidden_phrase" in _kinds(v), f"{phrase!r} not a forbidden_phrase: {v}"


def test_every_phrase_natal_txt_line_54_bans_is_caught():
    line = next(l for l in NATAL.splitlines() if l.startswith("- DO NOT use the words"))
    phrases = re.findall(r'"([^"]+)"', line)
    assert len(phrases) == 6, f"natal.txt's phrase line changed size: {phrases}"
    for phrase in phrases:
        v = rq.check_natal_reading(_clean(extra=f"Here the {phrase} appears."), n_sections=7)
        assert v["ok"] is False and v["banned"], f"natal.txt bans {phrase!r}; not caught"
    # `natal Moon` is caught once, by the planet rule, never twice.
    moon = rq.check_natal_reading(_clean(extra="Your natal Moon is calm."), n_sections=7)
    assert rq.banned_by_kind(moon) == {"planet": 1}, moon


def test_phrases_match_case_insensitively_and_across_a_line_wrap():
    for bad in ("Transit", "GOCHAR", "natal\nLagna", "bhava", "Lord  of\nthe"):
        v = rq.check_natal_reading(_clean(extra=f"See {bad} here."), n_sections=7)
        assert "forbidden_phrase" in _kinds(v), f"{bad!r} not flagged"


def test_ordinary_prose_is_not_a_forbidden_phrase():
    # Only the listed words: a longer word, a name, or "lord" / "of the" apart is clean,
    # and so is the prompt's own "house of service" phrasing.
    for ok_text in ("A transitory phase passes.", "Your friend Bhavana helps.",
                    "The house of service calls.", "A lord, and the owner of the shop.",
                    "Your rising sign shapes first impressions.",
                    "The ruler of your career house sits in the house of service."):
        v = rq.check_natal_reading(_clean(extra=ok_text), n_sections=7)
        assert v["ok"] is True, f"{ok_text!r} wrongly flagged: {v['banned']}"
    assert rq.check_natal_reading(_clean(), n_sections=7)["ok"] is True


def test_a_seeker_named_bhava_is_not_a_phrase_hit_but_a_stranger_is():
    text = _clean(name_in_prose="Bhava, you tend to carry others.")
    assert rq.check_natal_reading(text, n_sections=7, name="Bhava Rao")["ok"] is True
    assert "forbidden_phrase" in _kinds(rq.check_natal_reading(text, n_sections=7, name=""))
    # ...and the name excuses only itself, not a different phrase elsewhere.
    sep = _clean(extra="Your gochar is kind.", name_in_prose="Bhava")
    assert "forbidden_phrase" in _kinds(rq.check_natal_reading(sep, n_sections=7, name="Bhava"))
