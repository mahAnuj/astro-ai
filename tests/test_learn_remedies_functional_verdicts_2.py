"""#1003: the Mars, Mercury, Venus, Moon and Sun remedies guides stop asserting functional-benefic/malefic
verdicts by Ascendant (follow-up to #998, which did the same for Saturn and Jupiter).

`knowledge/*.md` holds the rule (remedies.md 4.1 / vedic_reference.md 7A.2: wear only the gemstone of a functional
benefic, avoid those of functional malefics and of marakas in maraka dasha; telling which is which needs the
Ascendant AND the classification for that Ascendant) but no table of functional benefics and malefics by Lagna
(tree grep of knowledge/*.md, 2026-11-14; data/ was absent on the runner, so this is a tree check, not a claim about
the books). The one sourced Ascendant-specific classification for these five planets is Mars as Yogakaraka for
Cancer and Leo (vedic_reference.md Manglik table rows 12-13, aspects.md). The pages listed Ascendants as functional
benefic/malefic next to gemstone advice, called Venus a Yogakaraka for Capricorn/Aquarius (no source in the tree) and
listed "compatible" Ascendants for pearl, and the registry FAQs repeated all of it.

Phrase tests on the rendered routes and the registry text: they catch the wordings they name, not every possible
rewording, and they do not judge the astrology beyond the arithmetic.
"""
from __future__ import annotations

import re

MARS = "mars-remedies"
MERCURY = "mercury-remedies"
VENUS = "venus-remedies"
MOON = "chandra-moon-remedies"
SUN = "surya-sun-remedies"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]

# (slug, FAQ question prefix) for every registry FAQ that carried the per-Ascendant lists.
_FAQS = (
    (MARS, "Is red coral safe"),
    (MERCURY, "Is emerald safe"),
    (VENUS, "Is diamond safe"),
    (MOON, "Can I wear Pearl"),
    (SUN, "Can I wear Ruby"),
)


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


# Per-Ascendant verdict wordings, each present on one of the pages before #1003.
_COMMON_REMOVED = (
    "is functionally benefic",
    "becomes functionally malefic",
    "is a mild functional malefic",
    "is a Yogakaraka",
    "most auspicious functional benefic",
    "generally supports",
    "strongly supports",
    "is often recommended",
    "classically recommended",
    "generally recommended",
    "Best consulted case-by-case",
    "mixed houses",
    "Best avoided without careful consultation",
    "(Aquarius, Pisces)",
    "Compatible:",
    "Avoid Scorpio Ascendant",
    "generally helps",
)

_PAGE_REMOVED = {
    MARS: ("Cancer, Leo, Scorpio, Sagittarius, Pisces Ascendants",
           "Taurus, Gemini, Virgo Ascendants",
           "Red coral generally supports",
           "Red coral can worsen anger"),
    MERCURY: ("Taurus, Cancer, and Libra Ascendants",
              "Capricorn and Aquarius Ascendants: Mercury",
              "Aries and Scorpio Ascendants: Mercury",
              "Mercury rules dusthanas",
              "Emerald can worsen nervous-system",
              "Leo Ascendant: Mercury"),
    VENUS: ("Capricorn and Aquarius Ascendants: Venus",
            "Aries and Scorpio Ascendants: Venus",
            "Cancer and Leo Ascendants: Venus",
            "Venus rules dusthanas",
            "(Aries, Scorpio, mixed for Sagittarius / Pisces, mild-malefic for Cancer / Leo)",
            "Virgo Ascendant: Venus rules the 2nd and 9th (both good)"),
    MOON: ("Cancer</strong> (Moon's own sign)",
           "Pisces</strong> (friendly)",
           "Pearl can amplify weakness"),
    SUN: ("functional malefic for your Ascendant (Aquarius, Pisces)",
          "Sun is combust in the natal chart"),
}


def _assert_clean(t: str, slug: str) -> None:
    for phrase in _COMMON_REMOVED + _PAGE_REMOVED[slug]:
        assert phrase not in t, (slug, phrase)


def test_mars_page_asserts_no_verdict_by_ascendant(client):
    _assert_clean(_text(client, MARS), MARS)


def test_mercury_page_asserts_no_verdict_by_ascendant(client):
    _assert_clean(_text(client, MERCURY), MERCURY)


def test_venus_page_asserts_no_verdict_by_ascendant(client):
    _assert_clean(_text(client, VENUS), VENUS)


def test_moon_page_asserts_no_verdict_by_ascendant(client):
    _assert_clean(_text(client, MOON), MOON)


def test_sun_page_asserts_no_verdict_by_ascendant(client):
    _assert_clean(_text(client, SUN), SUN)


def test_registry_faqs_assert_no_verdict_by_ascendant():
    for slug, q in _FAQS:
        a = _faq(slug, q)
        for phrase in _COMMON_REMOVED:
            assert phrase not in a, (slug, phrase)
        for phrase in ("Cancer, Leo, Scorpio, Sagittarius, and Pisces Ascendants",
                       "For Taurus, Gemini, and Virgo Ascendants",
                       "For Gemini and Virgo Ascendants (Mercury is the Ascendant lord), and for Taurus",
                       "For Aries and Scorpio Ascendants, Venus rules dusthanas",
                       "For Aries and Scorpio Ascendants, Mercury rules dusthanas",
                       "Cancer, Scorpio, Pisces most compatible",
                       "(Aquarius, Pisces)"):
            assert phrase not in a, (slug, phrase)


def test_pages_say_the_sources_give_no_table_by_ascendant(client):
    for slug in (MARS, MERCURY, VENUS):
        t = _text(client, slug)
        assert "give no table of functional benefics and malefics by Ascendant" in t, slug
        assert "issues no verdict by Ascendant" in t, slug
    m = _text(client, MOON)
    assert "give no table of functional benefics and malefics by Ascendant" in m
    assert "issues no verdict by Ascendant" in m
    s = _text(client, SUN)
    assert "give no table of functional benefics and malefics by Ascendant" in s
    for slug, q in _FAQS:
        assert "no table of functional benefics and malefics by Ascendant" in _faq(slug, q), slug


def test_consult_a_chart_warning_survives(client):
    """The safety warning is the sourced part (remedies.md 4.1, vedic_reference.md 7A.2). Deleting it must turn this red."""
    for slug, planet, stone in ((MARS, "Mars", "red coral"), (MERCURY, "Mercury", "emerald"),
                                (VENUS, "Venus", "diamond")):
        t = _text(client, slug)
        assert "gemstones of functional malefics for your chart should be avoided" in t, slug
        assert f"needs your Ascendant and the classification of {planet} for that Ascendant" in t, slug
        assert f"Do not wear {stone} on the strength of a house count or a web list; have your chart read first" in t, slug
        assert "Never wear a planet's gemstone during that planet's maraka dasha" in t, slug
    assert "Do not buy emerald without consultation" in _text(client, MERCURY)
    assert "Do not buy diamond without consultation" in _text(client, VENUS)
    m = _text(client, MOON)
    assert "gemstones of functional malefics for your chart should be avoided" in m
    assert "needs your Ascendant and the classification of the Moon for that Ascendant" in m
    assert "it still needs a chart review before you wear it" in m
    s = _text(client, SUN)
    assert "gemstones of functional malefics for your chart should be avoided" in s
    assert "STILL requires chart analysis before wearing" in s
    assert "Never wear ruby when the Sun is a functional malefic for your chart" in s
    for slug, q in _FAQS:
        a = _faq(slug, q)
        assert "gemstones of functional malefics for your chart should be avoided" in a, slug
    assert "Have your chart read first" in _faq(MARS, "Is red coral safe")
    assert "have your chart read first" in _faq(MERCURY, "Is emerald safe")
    assert "have your chart read first" in _faq(VENUS, "Is diamond safe")


def test_house_lordships_stated_are_the_true_ones(client):
    """Derived from sign lordship (Mars: Aries+Scorpio, Mercury: Gemini+Virgo, Venus: Taurus+Libra, Moon: Cancer,
    Sun: Leo), not recalled."""
    mars = {lg: [_house(lg, s) for s in ("Aries", "Scorpio")] for lg in SIGNS}
    mer = {lg: [_house(lg, s) for s in ("Gemini", "Virgo")] for lg in SIGNS}
    ven = {lg: [_house(lg, s) for s in ("Taurus", "Libra")] for lg in SIGNS}
    moon = {lg: _house(lg, "Cancer") for lg in SIGNS}
    sun = {lg: _house(lg, "Leo") for lg in SIGNS}

    # Mars Yogakaraka for Cancer and Leo = a kendra and a trikona (vedic_reference.md Manglik table rows 12-13)
    kendra, trikona = {1, 4, 7, 10}, {1, 5, 9}
    for lg in ("Cancer", "Leo"):
        h = set(mars[lg])
        assert h & kendra and h & trikona and 1 not in h, lg
    assert mars["Cancer"] == [10, 5] and mars["Leo"] == [9, 4]
    assert mars["Aries"] == [1, 8] and mars["Scorpio"] == [6, 1]
    assert mars["Taurus"] == [12, 7] and mars["Gemini"] == [11, 6] and mars["Virgo"] == [8, 3]
    assert mer["Gemini"] == [1, 4] and mer["Virgo"] == [10, 1]
    assert mer["Aries"] == [3, 6] and mer["Taurus"] == [2, 5] and mer["Scorpio"] == [8, 11]
    assert mer["Capricorn"] == [6, 9]
    assert ven["Taurus"] == [1, 6] and ven["Libra"] == [8, 1]
    assert ven["Capricorn"] == [5, 10] and ven["Aquarius"] == [4, 9]
    assert ven["Aries"] == [2, 7] and ven["Scorpio"] == [7, 12] and ven["Virgo"] == [9, 2]
    assert moon["Cancer"] == 1 and moon["Gemini"] == 2 and moon["Leo"] == 12 and moon["Libra"] == 10
    assert sun["Leo"] == 1 and sun["Aries"] == 5 and sun["Virgo"] == 12 and sun["Aquarius"] == 7

    t = _text(client, MARS)
    assert "the 1st and 8th houses from Aries, the 6th and 1st from Scorpio" in t
    assert "the 10th and 5th from Cancer, the 4th and 9th from Leo" in t
    assert "the 12th and 7th from Taurus, the 11th and 6th from Gemini, and the 8th and 3rd from Virgo" in t
    t = _text(client, MERCURY)
    assert "the 1st and 4th houses from Gemini, the 10th and 1st from Virgo" in t
    assert ("the 3rd and 6th from Aries, the 2nd and 5th from Taurus, the 8th and 11th from Scorpio, "
            "and the 6th and 9th from Capricorn") in t
    t = _text(client, VENUS)
    assert "the 1st and 6th houses from Taurus, the 8th and 1st from Libra" in t
    assert ("the 5th and 10th from Capricorn, the 4th and 9th from Aquarius, the 2nd and 7th from Aries, "
            "and the 7th and 12th from Scorpio") in t
    assert "he rules the 9th and 2nd houses" in t
    t = _text(client, MOON)
    assert "the 2nd from Gemini, the 12th from Leo and the 10th from Libra" in t
    t = _text(client, SUN)
    assert "the 5th from Aries, the 12th from Virgo, the 7th from Aquarius" in t

    assert "the 1st and 8th from Aries and the 6th and 1st from Scorpio" in _faq(MARS, "Is red coral safe")
    assert "the 10th and 5th from Cancer, the 4th and 9th from Leo" in _faq(MARS, "Is red coral safe")
    assert "the 1st and 4th from Gemini, the 10th and 1st from Virgo" in _faq(MERCURY, "Is emerald safe")
    assert "the 1st and 6th from Taurus, the 8th and 1st from Libra" in _faq(VENUS, "Is diamond safe")
    assert "the 5th and 10th from Capricorn, the 4th and 9th from Aquarius" in _faq(VENUS, "Is diamond safe")
    assert "the 2nd from Gemini and the 12th from Leo" in _faq(MOON, "Can I wear Pearl")


def test_mars_yogakaraka_statement_is_the_sourced_one(client):
    """Mars as Yogakaraka for Cancer and Leo is sourced (vedic_reference.md Manglik table rows 12-13; aspects.md).
    Venus as Yogakaraka for Capricorn/Aquarius has no source in the tree and must not be asserted."""
    t = _text(client, MARS)
    assert "name Mars the Yogakaraka here" in t
    v = _text(client, VENUS)
    assert "Yogakaraka" not in v
    assert "Yogakaraka" not in _faq(VENUS, "Is diamond safe")


def test_moon_dignities_are_the_sourced_ones(client):
    """grahas.md 191-200: Moon owns Cancer, exalted Taurus, debilitated Scorpio; Mars debilitated Cancer; Mercury
    Pisces; Venus Virgo."""
    assert "the Moon is debilitated in Scorpio and exalted in Taurus" in _text(client, MOON)
    assert "Mars is debilitated in Cancer" in _text(client, MARS)
    assert "Mercury is debilitated in Pisces" in _text(client, MERCURY)
    assert "Venus is debilitated in Virgo" in _text(client, VENUS)
