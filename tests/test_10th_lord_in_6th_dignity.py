"""#1083: /learn/10th-lord-in-6th-house-career names, for each of the 12 ascendants, the 10th lord and the 6th
sign it sits in, and sometimes that planet's dignity there. The Gemini row said 'Jupiter debilitated in Scorpio';
Jupiter is debilitated in Capricorn (knowledge/grahas.md dignity table, Rao Table 6). Every row's lord, sign and
dignity claim is recomputed from the engine's own rashi-lord table, so a wrong row cannot return.
"""
from __future__ import annotations

import re

from astro_ai.chart import RASHI_LORDS

SLUG = "10th-lord-in-6th-house-career"
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
         "Aquarius", "Pisces"]
# knowledge/grahas.md dignity table (Rao Table 6)
EXALTED = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo", "Jupiter": "Cancer",
           "Venus": "Pisces", "Saturn": "Libra"}
DEBILITATED = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces", "Jupiter": "Capricorn",
               "Venus": "Virgo", "Saturn": "Aries"}


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _rows(client) -> list[tuple[str, str]]:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    html = r.text
    section = html[html.index("How the placement flavours by ascendant"):html.index("When it hurts")]
    items = re.findall(r"<li><strong>(\w+) ascendant:</strong>(.*?)</li>", section, re.S)
    assert [a for a, _ in items] == SIGNS, items
    return [(a, _plain(body)) for a, body in items]


def test_each_row_names_the_right_10th_lord_and_6th_sign(client):
    for asc, body in _rows(client):
        i = SIGNS.index(asc)
        tenth, sixth = SIGNS[(i + 9) % 12], SIGNS[(i + 5) % 12]
        m = re.match(rf"\s*(\w+) \(10th lord of {tenth}\) in the 6th sign {sixth}\.", body)
        assert m, (asc, body[:120])
        assert m.group(1) == RASHI_LORDS[SIGNS.index(tenth)], (asc, m.group(1))


def test_every_dignity_claim_matches_the_dignity_table(client):
    claims = 0
    for asc, body in _rows(client):
        planet = re.match(r"\s*(\w+) \(10th lord", body).group(1)
        sixth = SIGNS[(SIGNS.index(asc) + 5) % 12]
        for kind, table in (("exalted", EXALTED), ("debilitated", DEBILITATED)):
            for m in re.finditer(rf"\b(\w+) {kind} in (\w+)", body):
                if m.group(1) != planet:  # e.g. 'Jupiter is debilitated in Capricorn' states the table itself
                    continue
                claims += 1
                assert table[planet] == m.group(2) == sixth, (asc, m.group(0))
        for m in re.finditer(r"Jupiter is debilitated in (\w+)", body):
            assert m.group(1) == DEBILITATED["Jupiter"]
    assert claims >= 3  # Taurus (Saturn), Scorpio (Sun), Aquarius (Mars)


def test_jupiter_in_scorpio_is_not_called_debilitated(client):
    gem = dict(_rows(client))["Gemini"]
    assert "Jupiter debilitated in Scorpio" not in gem
    assert "not a debilitation" in gem and "debilitated in Capricorn" in gem


def test_unsourced_classical_attributions_are_labelled_as_practice(client):
    t = _plain(client.get(f"/learn/{SLUG}/").text)
    for gone in ("the classical \"successful doctor", "Classical texts consistently recommend",
                 "is classical Vedic remedy", "Classical Vedic tradition frames this as",
                 "Classical Vedic tradition and centuries of practical readings"):
        assert gone not in t, gone
    assert "not a profession list from the classical texts" in t
    assert "not a remedy the classical texts prescribe for a house" in t


def test_registry_no_longer_calls_the_remedies_classical():
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == SLUG)
    blob = art.summary + " " + art.llm_summary + " " + " ".join(f["a"] for f in art.faqs)
    assert "honest classical remedies" not in blob
    assert "Safe universal classical practices" not in blob
    assert "classical Vedic signature for careers" not in blob


def _all_prose(client) -> str:
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == SLUG)
    page = _plain(client.get(f"/learn/{SLUG}/").text)
    return page + " " + art.summary + " " + " ".join(f["a"] for f in art.faqs) + " " + art.llm_summary


def test_no_planet_in_a_friends_sign_is_called_own_sign_or_exalted(client):
    """QA round 1 on #1121: 'Mars in Sagittarius' was listed under 'exalted or in own sign' (FAQ) and 'well-placed in
    itself' (page). Mars rules Aries/Scorpio and is exalted in Capricorn (grahas.md L197); Sagittarius is Jupiter's."""
    prose = _all_prose(client)
    assert "well-placed in itself" not in prose
    own = {p: {SIGNS[i] for i, lord in enumerate(RASHI_LORDS) if lord == p} for p in EXALTED}
    checked = 0
    for sentence in re.split(r"(?<=[.;])\s", prose):
        if not re.search(r"\bown[- ]sign\b|\bexalted or in own\b|\bin itself\b", sentence):
            continue
        for m in re.finditer(r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn) in (" + "|".join(SIGNS) + r")\b", sentence):
            checked += 1
            planet, sign = m.groups()
            assert sign in own[planet] or sign == EXALTED[planet], (planet, sign, sentence[:200])
    assert "Mars in Sagittarius" in prose
    for m in re.finditer(r"[^.]*Mars in (?:a friend's sign \()?Sagittarius[^.]*\.", prose):
        assert "friend" in m.group(0), m.group(0)
