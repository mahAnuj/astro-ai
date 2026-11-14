"""#992: the planets-in-the-7th guide stops asserting functional-benefic/malefic verdicts by Ascendant.

`knowledge/*.md` holds the natural-vs-functional DISTINCTION (vedic_reference.md section 8.5.3) but no table of
functional benefics and malefics by Lagna (grep of houses.md, grahas.md, yogas.md, 2026-11-14). The per-Ascendant
list said Saturn "is not a functional malefic" for Cancer and Leo (Saturn rules the 7th and 8th from Cancer, the 6th
and 7th from Leo), that the Sun "becomes a functional malefic" for Capricorn and Aquarius, and that own-sign dignity
"significantly softens" Jupiter's late-marriage caveat. The registry's llm_summary ranked Venus-in-the-7th "BEST".

Now each bullet states what can be worked out (which sign the 7th is, which houses the planet rules) and says the
rest is practice or not ruled on. Phrase tests on the rendered route and the registry text: they catch the
wordings they name, not every possible rewording; they do not judge the astrology beyond the arithmetic.
"""
from __future__ import annotations

import re

SLUG = "planets-in-7th-house-marriage"


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _block(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    html = r.text
    seg = html[html.index("Per-Ascendant shifts"):html.index("Reading the 7th house honestly")]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg))


def test_no_functional_verdict_by_ascendant_is_asserted(client):
    t = _block(client)
    for phrase in (
        "is not a functional malefic",
        "becomes a functional malefic",
        "same beneficial shift",
        "significantly softened",
        "most widely praised",
    ):
        assert phrase not in t, phrase


def test_block_says_the_sources_give_no_table_by_ascendant(client):
    t = _block(client)
    assert "do not give a table of functional benefics and malefics by Ascendant" in t or \
        "give no table of functional benefics and malefics by Ascendant" in t
    # the three bullets that used to assert a verdict now each decline to rule
    assert t.count("does not rule on") + t.count("do not say how") + t.count("does not call the Sun") >= 3


def test_house_lordships_stated_are_the_true_ones(client):
    """Saturn: 8th from Cancer, 6th from Leo. Sun: 8th from Capricorn, 7th from Aquarius. Derived, not recalled."""
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
             "Capricorn", "Aquarius", "Pisces"]

    def house(lagna: str, sign: str) -> int:
        return (signs.index(sign) - signs.index(lagna)) % 12 + 1

    assert house("Cancer", "Aquarius") == 8 and house("Leo", "Capricorn") == 6
    assert house("Capricorn", "Leo") == 8 and house("Aquarius", "Leo") == 7
    t = _block(client)
    assert "rules the 8th house from a Cancer Ascendant" in t
    assert "rules the 6th house from a Leo Ascendant" in t
    assert "rules the 8th house from Capricorn and the 7th from Aquarius" in t


def test_jupiter_caveat_is_labelled_practice(client):
    t = _block(client)
    assert "Practitioners also say the late-marriage caveat for women is softened" in t
    assert "That is practice, not something the sources we hold state." in t


def test_venus_is_not_ranked_best_and_malavya_is_conditional():
    a = _article()
    assert "BEST" not in a.llm_summary
    line = next(ln for ln in a.llm_summary.split("\n") if ln.startswith("• Venus in 7th"))
    assert "only when Venus is in her own sign or exalted there" in line
    assert "kendra" in line


def test_llm_summary_does_not_assert_cancer_leo_shift():
    s = _article().llm_summary
    assert "reads very differently" not in s
    assert "no table by Ascendant" in s
