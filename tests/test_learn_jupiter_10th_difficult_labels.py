"""#1049: the Jupiter-in-10th guide's "weak or afflicted" bullets label their outcome patterns as practitioner reading.

Held, in `knowledge/vedic_reference.md` section 4.1: only the Hamsa / Pancha Mahapurusha rule and its effects (wisdom,
respect, dharma, scholarly fame). Nothing held states a debilitated-Jupiter career stall, a combust-Jupiter
'overshadowed second-in-command' pattern, a Jupiter-Saturn late bloom, or an age window for one. The page stated all
three flat and gave 'around age 35-40' with no source. data/ was absent when this was written, so no absence is asserted;
the claim is only that the page must not present these as rules.

The scan reads the list items of the real rendered "weak or afflicted" block, so a reworded flat claim is caught as
well as the exact phrases. Kept in its own file so it cannot conflict with the claims suite (#1045).
"""
from __future__ import annotations

import re

SLUG = "jupiter-in-10th-house-career"

# the flat wording #1049 removed; matched case-insensitively on tag-stripped text
FLAT_PHRASES = (
    "can produce a person of genuine wisdom",
    "Careers under this configuration often show",
    "Careers under this pairing often move",
    "turning point is often around age 35-40",
)

# the three bullets that state an outcome pattern, found by the bold lead-in of the list item
OUTCOME_BULLETS = ("Debilitated Jupiter", "Combust Jupiter", "Jupiter with Saturn")

_AGE_WINDOW = re.compile(r"age\s*\d\d\s*[-–]\s*\d\d", re.I)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _html(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return r.text


def _weak_block_items(html: str) -> list[str]:
    """Plain text of each <li> between the 'weak or afflicted' heading and the next heading."""
    start = html.index("When Jupiter in the 10th is weak or afflicted")
    nxt = re.search(r"<h2", html[start + 1 :])
    block = html[start : start + 1 + nxt.start()] if nxt else html[start:]
    return [_plain(m).strip() for m in re.findall(r"<li>(.*?)</li>", block, re.S)]


def test_page_states_none_of_the_flat_difficult_placement_claims(client):
    text = _plain(_html(client)).lower()
    for phrase in FLAT_PHRASES:
        assert phrase.lower() not in text, phrase


def test_each_outcome_bullet_is_labelled_practitioner_reading(client):
    items = _weak_block_items(_html(client))
    assert len(items) >= 5, "the weak-or-afflicted list was not found"
    for lead in OUTCOME_BULLETS:
        matching = [i for i in items if i.startswith(lead)]
        assert len(matching) == 1, f"expected one bullet starting {lead!r}, got {len(matching)}"
        low = matching[0].lower()
        assert "practitioner" in low, lead
        assert "not a rule the texts state" in low, lead


def test_weak_block_gives_no_age_window(client):
    for item in _weak_block_items(_html(client)):
        assert not _AGE_WINDOW.search(item), item
