"""#1008: the Guru-Jupiter guide stops telling readers to avoid yellow sapphire by Ascendant.

`knowledge/*.md` holds the rule (remedies.md 4.1: wear only the gemstone of a functional benefic, never that of a
functional malefic; functional status depends on the Ascendant) but no table of functional benefics and malefics by
Lagna (tree grep, 2026-11-14; data/ was absent on the runner, so this is a tree check, not a claim about the books).
The page said "Avoid for Capricorn Ascendant ... functional malefic. Also avoid for Taurus + Libra", and pointed to
"ascendant-by-ascendant Pukhraj guidance" that #1001 had already removed from jupiter-remedies.

Phrase tests on the rendered route: they catch the wordings they name, not every possible rewording.
"""
from __future__ import annotations

import re

SLUG = "guru-jupiter-in-vedic-astrology"


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    body = re.sub(r"<[^>]+>", " ", r.text)
    return re.sub(r"\s+", " ", body)


def test_guru_jupiter_gem_bullet_asserts_no_verdict_by_ascendant(client):
    t = _text(client)
    for phrase in ("Avoid for Capricorn Ascendant",
                   "Also avoid for Taurus",
                   "rules the 3rd/12th dusthanas",
                   "ascendant-by-ascendant Pukhraj guidance"):
        assert phrase not in t, phrase


def test_guru_jupiter_gem_bullet_keeps_the_sourced_rule_and_the_consult_warning(client):
    t = _text(client)
    assert "wear only the gemstone of a functional benefic" in t
    assert "no table of functional benefics and malefics by Ascendant" in t
    assert "requires a chart consultation" in t
    assert "Jupiter is debilitated in Capricorn" in t
