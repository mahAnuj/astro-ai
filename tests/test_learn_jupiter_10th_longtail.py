"""#1073: the Jupiter-in-10th guide answers its own long-tail queries (Pisces, Sagittarius, aspects, marriage age).

Held: `knowledge/aspects.md` (Jupiter aspects the 5th, 7th, 9th from itself; Raman); `knowledge/houses.md` (Rao's house
significations); `knowledge/vedic_reference.md` 5.5 (marriage-timing indicators: dashas of Venus, Jupiter, the 7th lord, a
planet occupying or aspecting the 7th, Jupiter's transit through the 7th or over the natal Moon). Nothing held gives a
marriage AGE for Jupiter in the 10th, so the page must give none.

Every test reads the real rendered route.
"""
from __future__ import annotations

import re

SLUG = "jupiter-in-10th-house-career"

PISCES_H3 = "Jupiter in Pisces in the 10th house (Gemini ascendant)"
SAGITTARIUS_H3 = "Jupiter in Sagittarius in the 10th house (Pisces ascendant)"
ASPECT_H2 = "Which houses does Jupiter in the 10th aspect?"

# an age or an age window stated for marriage
_AGE = re.compile(r"\bage\s*\d|\bages\s*\d|\bby\s+\d\d\b|\byears?\s+old\b|\b\d\d\s*[-–]\s*\d\d\b", re.I)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def _html(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    # the article body only: the page chrome carries a CSS comment that mentions h3 in angle brackets
    return r.text.split('<div class="callout callout-insight">', 1)[1]


def _headings(html: str) -> list[tuple[str, str]]:
    return [(m.group(1), _plain(m.group(2))) for m in re.finditer(r"<(h[23])>(.*?)</\1>", html, re.S)]


def _section(html: str, heading: str) -> str:
    """HTML from the named heading to the next h2 (h3s inside stay in the section)."""
    start = html.index(heading)
    nxt = re.search(r"<h2", html[start:])
    return html[start : start + nxt.start()] if nxt else html[start:]


def test_the_two_own_sign_placements_have_their_own_h3(client):
    hs = _headings(_html(client))
    assert ("h3", PISCES_H3) in hs, hs
    assert ("h3", SAGITTARIUS_H3) in hs, hs


def test_the_aspect_h2_exists_and_names_the_2nd_4th_6th(client):
    html = _html(client)
    assert ("h2", ASPECT_H2) in _headings(html)
    body = _plain(_section(html, ASPECT_H2))
    for house in ("2nd", "4th", "6th"):
        assert house in body, house
    assert "5th, 7th and 9th" in body
    # the 7th and 10th are NOT aspected from the 10th
    assert "does not aspect the 7th house" in body


def test_the_sign_sections_keep_the_ascendant_arithmetic_right(client):
    html = _html(client)
    gemini = _plain(_section(html, PISCES_H3).split(SAGITTARIUS_H3)[0])
    pisces = _plain(_section(html, SAGITTARIUS_H3))
    # Pisces is the 10th from Gemini; its 5th/7th/9th from Pisces are Cancer/Virgo/Scorpio
    assert "Pisces is the 10th sign counting on from Gemini" in gemini
    assert "Cancer, Virgo and Scorpio" in gemini
    # Sagittarius is the 10th from Pisces; its 5th/7th/9th from Sagittarius are Aries/Gemini/Leo
    assert "Sagittarius is the 10th sign counting on from Pisces" in pisces
    assert "Aries, Gemini and Leo" in pisces


def test_the_hamsa_condition_is_unchanged_and_not_restated_differently(client):
    t = _plain(_html(client))
    # the page's one statement of the rule, as before #1073
    assert t.count("Jupiter must sit in Sagittarius, Pisces, or Cancer") == 1
    assert "be in a kendra (1st, 4th, 7th, or 10th house) from the Lagna" in t
    # the new sections point back to it rather than adding or dropping a condition
    assert "Jupiter in Sagittarius, Pisces, or Cancer, and in a kendra from the Lagna" in t


def test_the_marriage_section_exists_gives_the_held_indicators_and_no_age(client):
    html = _html(client)
    hs = [h for lvl, h in _headings(html) if "marriage" in h.lower()]
    assert hs, "no heading names marriage"
    sec = _section(html, hs[0])
    body = _plain(sec)
    assert "10th house" in body and "not on the marriage-timing list" in body
    for indicator in ("Venus", "Jupiter", "7th lord", "occupying or aspecting the 7th house", "natal Moon"):
        assert indicator in body, indicator
    assert not _AGE.search(body), _AGE.search(body).group(0)


def test_the_marriage_section_links_the_timing_guide(client):
    html = _html(client)
    hs = [h for lvl, h in _headings(html) if "marriage" in h.lower()]
    assert 'href="/learn/marriage-mahadasha-timing/"' in _section(html, hs[0])


def test_the_age_scan_is_red_on_the_shapes_it_exists_for():
    for bad in ("Marriage usually happens at age 28.", "Marriage by 27 is likely.", "married by age 30",
                "people marry between 25-30.", "a 26 years old native"):
        assert _AGE.search(bad), bad
    assert not _AGE.search("The 10th house does not set the timing of marriage.")


def test_every_page_link_in_the_new_sections_resolves(client):
    from astro_ai.learn_registry import ARTICLES

    slugs = {a.slug for a in ARTICLES}
    html = _html(client)
    new = _section(html, "Jupiter in Pisces or Sagittarius in the 10th house, sign by sign") + _section(
        html, "Does Jupiter in the 10th decide the age of marriage?"
    )
    for href in re.findall(r'href="/learn/([^/"]+)/"', new):
        assert href in slugs, href
