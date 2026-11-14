"""#998: the Saturn and Jupiter remedies guides stop asserting functional-benefic/malefic verdicts by Ascendant.

`knowledge/*.md` holds the rule (remedies.md 1.4: gemstones of functional malefics should be avoided, and telling
which is which needs the Ascendant AND the classification for that Ascendant) but no table of functional benefics
and malefics by Lagna (grep of houses.md, grahas.md, yogas.md, remedies.md, 2026-11-14; data/ was absent on the
runner, so this is a tree check, not a claim about the books). The pages listed Ascendants as "functional benefic"
or "functional malefic" next to gemstone advice, said "blue sapphire strongly recommended", and put the same lists in
two registry FAQs.

Now the pages state the sourced rule, say plainly that no table by Ascendant is held, give only house-lordship
arithmetic, and keep the consult-a-chart warning. Phrase tests on the rendered routes and the registry text: they
catch the wordings they name, not every possible rewording, and they do not judge the astrology beyond the arithmetic.
"""
from __future__ import annotations

import re

SATURN = "saturn-remedies"
JUPITER = "jupiter-remedies"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]


def _text(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    body = re.sub(r"<[^>]+>", " ", r.text)
    return re.sub(r"\s+", " ", body)


def _faq(slug: str, q_start: str) -> str:
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == slug)
    return next(f["a"] for f in art.faqs if f["q"].startswith(q_start))


def _house(lagna: str, sign: str) -> int:
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


# Phrases that were per-Ascendant verdicts. Each appeared verbatim (or nearly) before #998.
_REMOVED = (
    "is a functional malefic",
    "is a functional benefic",
    "is a functional benefic for",
    "functionally malefic",
    "strongly recommended",
    "Blue sapphire should be avoided",
    "yellow sapphire should be avoided",
    "Yellow sapphire should generally be avoided",
    "Yellow sapphire strengthens Jupiter's positive effects",
    "beneficial for most Ascendants",
    "Aries Ascendant: Saturn",
    "Cancer Ascendant: Saturn",
    "Leo Ascendant: Saturn",
    "Taurus and Libra Ascendants: Jupiter",
    "Capricorn Ascendant: Jupiter",
    "Jupiter's status is mixed",
)


def test_saturn_page_asserts_no_verdict_by_ascendant(client):
    t = _text(client, SATURN)
    for phrase in _REMOVED:
        assert phrase not in t, phrase


def test_jupiter_page_asserts_no_verdict_by_ascendant(client):
    t = _text(client, JUPITER)
    for phrase in _REMOVED:
        assert phrase not in t, phrase


def test_registry_faqs_assert_no_verdict_by_ascendant():
    for slug, q in ((JUPITER, "Is yellow sapphire safe"), (SATURN, "Should I wear blue sapphire")):
        a = _faq(slug, q)
        for phrase in ("is a functional malefic", "is a functional benefic", "yellow sapphire should be avoided",
                       "generally helps"):
            assert phrase not in a, (slug, phrase)
        assert "For Aries, Cancer, Leo" not in a
        assert "mainly for Taurus and Libra" not in a


def test_pages_say_the_sources_give_no_table_by_ascendant(client):
    for slug in (SATURN, JUPITER):
        t = _text(client, slug)
        assert "give no table of functional benefics and malefics by Ascendant" in t, slug
        assert "issues no verdict by Ascendant" in t, slug
    for slug, q in ((JUPITER, "Is yellow sapphire safe"), (SATURN, "Should I wear blue sapphire")):
        assert "no table of functional benefics and malefics by Ascendant" in _faq(slug, q), slug


def test_consult_a_chart_warning_survives(client):
    """The safety warning is the sourced part (remedies.md 1.4). Deleting it must turn this red."""
    s = _text(client, SATURN)
    assert "gemstones of functional malefics for your chart should be avoided" in s
    assert "needs your Ascendant and the classification of Saturn for that Ascendant" in s
    assert "Do not wear blue sapphire without a proper chart consultation" in s
    assert "Do not wear it without a chart consultation" in s
    assert "Never wear a planet's gemstone during that planet's maraka dasha" in s
    j = _text(client, JUPITER)
    assert "gemstones of functional malefics for your chart should be avoided" in j
    assert "needs your Ascendant and the classification of Jupiter for that Ascendant" in j
    assert "Do not skip yellow sapphire consultation" in j
    assert "Never wear a planet's gemstone during that planet's maraka dasha" in j
    assert "chart consultation" in _faq(JUPITER, "Is yellow sapphire safe")
    assert "have your chart read first" in _faq(SATURN, "Should I wear blue sapphire")


def test_house_lordships_stated_are_the_true_ones(client):
    """Derived from sign lordship (Saturn: Capricorn+Aquarius, Jupiter: Sagittarius+Pisces), not recalled."""
    sat = {lg: sorted(_house(lg, s) for s in ("Capricorn", "Aquarius")) for lg in SIGNS}
    jup = {lg: sorted(_house(lg, s) for s in ("Sagittarius", "Pisces")) for lg in SIGNS}
    # Taurus/Libra: a trikona plus a kendra, which is what "Yogakaraka" names
    assert sat["Taurus"] == [9, 10] and sat["Libra"] == [4, 5]
    assert sat["Aries"] == [10, 11] and sat["Cancer"] == [7, 8] and sat["Leo"] == [6, 7]
    assert sat["Capricorn"] == [1, 2] and sat["Aquarius"] == [1, 12]
    assert jup["Aries"] == [9, 12] and jup["Taurus"] == [8, 11] and jup["Gemini"] == [7, 10]
    assert jup["Capricorn"] == [3, 12]
    assert jup["Sagittarius"] == [1, 4] and jup["Pisces"] == [1, 10]

    s = _text(client, SATURN)
    assert "the 10th and 9th from Taurus, the 4th and 5th from Libra" in s
    assert "the 1st and 2nd houses from Capricorn, the 12th and 1st from Aquarius" in s
    assert "10th and 11th from Aries, the 7th and 8th from Cancer, and the 6th and 7th from Leo" in s
    j = _text(client, JUPITER)
    assert "the 1st and 4th houses from Sagittarius, the 10th and 1st from Pisces" in j
    assert "the 9th and 12th from Aries, the 8th and 11th from Taurus, the 7th and 10th from Gemini, " \
        "and the 12th and 3rd from Capricorn" in j
    assert "the 9th and 12th from Aries and the 1st and 4th from Sagittarius" in _faq(JUPITER, "Is yellow sapphire safe")
    assert "10th and 11th from Aries" in _faq(SATURN, "Should I wear blue sapphire")


def test_yogakaraka_and_lagna_lord_statement_is_the_sourced_one(client):
    """vedic_reference.md 2.7.2 (Rao Lesson 1 note 29): Saturn as lagna lord or yogakaraka hardly troubles even in Sade Sati."""
    s = _text(client, SATURN)
    assert "hardly going to trouble the person even in Sade Sati" in s
    assert "Yogakaraka" in s
