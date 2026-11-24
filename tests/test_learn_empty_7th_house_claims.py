"""#1430: an answer-first section for a 7th house with no planet in it, on the 7th-house pair.

`knowledge/*.md` holds no rule for reading an empty 7th (astro-auditor ruling on #1430). It holds
only: the 7th is Yuvati Bhava (houses.md), a house is read whether or not a planet sits in it and
every planet aspects its 7th (aspects.md), a strong 7th lord + unafflicted Venus (men) reads as a
harmonious marriage (houses.md), and the dasha of the 7th lord, or of a planet in or aspecting the
7th, is a marriage-timing period (vedic_reference.md). Looking at the 7th lord's sign, house and
aspects is practice, and the section says so in its own callout.

Pinned through the real route. The forbidden-claim lists are scoped to the NEW BLOCK only, because
the rest of the page (L167 'often matters more', the Saturn 'delay' reading) predates this change
and is not this section's claim. A PHRASE TEST: it catches the wordings it names, not every possible
rewording; the astro-auditor and qa read the block for the rest.
"""
from __future__ import annotations

import re

PLANETS = "planets-in-7th-house-marriage"
GUIDE = "7th-lord-placement-marriage-guide"

START = "<h2>If no planet is in your 7th house</h2>"
END = "<h2>Sun in the 7th house</h2>"
EXISTING_LABEL = "What is sourced and what is practice"
NEW_LABEL = "Sourced and practice: an empty 7th house"

FIRST_SENTENCE = "The sources we hold do not set out how to read a 7th house with no planet in it."
AUDITOR_BODY = (
    "The sources we hold do not set out how to read a 7th house with no planet in it. "
    "What we can trace to them is narrower: the 7th is Yuvati Bhava, the house of spouse and marriage; "
    "every planet aspects the house opposite itself, and a house is read whether or not a planet sits in it; "
    "the dasha or antardasha of the 7th lord, or of a planet occupying or aspecting the 7th, is among the "
    "periods in which marriage typically happens; and a strong 7th lord with an unafflicted Venus (for men) "
    "is read as a harmonious marriage. Turning an empty 7th into a reading by looking at the 7th lord's sign, "
    "house and aspects is widely used interpretive practice, not a quotation from a classical text, and it is "
    "a way to find where to look, not a verdict on whether or when you marry."
)

_FORBIDDEN = [
    "smoother",
    "fewer problems",
    "not denied",
    "denied",
    "denial",
    "deny",
    "denies",
    "delay",
    "matters more",
    "more important",
    "read through the 7th lord",
    "malavya",
    "strongest",
    "best",
]
_FORBIDDEN_WORDS = re.compile(r"\b(good|bad|auspicious|inauspicious|lucky)\b", re.I)
_CITATIONS = ["Raman", "Ch.", "chapter", r"p\. \d"]


def _html(client, slug) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    return r.text


def _block(client) -> str:
    html = _html(client, PLANETS)
    assert html.count(START) == 1
    i = html.index(START)
    j = html.index(END, i)
    return html[i:j]


def _norm(markup: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


def _prose_outside_callout(block: str) -> str:
    return re.sub(r'(?s)<div class="callout callout-classic">.*?</div>', " ", block)


def test_h2_exists_once_between_the_tip_and_the_sun_section(client):
    html = _html(client, PLANETS)
    assert html.count(START) == 1
    assert html.index("Which planet sits in YOUR 7th house?") < html.index(START) < html.index(END)
    heads = re.findall(r"<h2>(\w+) in the 7th house</h2>", html)
    assert heads == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def test_block_has_one_practice_callout_with_the_audited_body(client):
    block = _block(client)
    assert block.count("callout-classic") == 1
    label = re.search(r'callout-label">([^<]+)<', block).group(1)
    assert label == NEW_LABEL
    assert label != EXISTING_LABEL
    body = _norm(re.search(r'(?s)callout-classic">.*?<p>(.*?)</p>', block).group(1))
    assert body.startswith(FIRST_SENTENCE)
    assert body == AUDITOR_BODY


def test_the_existing_disclosure_label_is_still_there_exactly_once(client):
    assert _html(client, PLANETS).count(EXISTING_LABEL) == 1


def test_block_points_to_the_7th_lord_guide_and_the_kundli_in_words(client):
    block = _block(client)
    assert 'href="/learn/7th-lord-placement-marriage-guide/"' in block
    assert 'href="/kundli"' in block
    assert "7th Lord Placement guide" not in block
    for text in re.findall(r"<a [^>]*>(.*?)</a>", block):
        assert re.search(r"[A-Za-z]{3,}", text), text


def test_block_says_an_empty_7th_is_not_a_verdict(client):
    block = _block(client)
    t = _norm(block)
    assert "not a verdict" in t
    assert "does not mean no marriage" in t
    assert "Yuvati Bhava" in t


def test_block_makes_none_of_the_claims_the_corpus_cannot_back(client):
    t = _norm(_block(client)).lower()
    for phrase in _FORBIDDEN:
        assert phrase not in t, phrase
    assert not _FORBIDDEN_WORDS.search(t)


def test_block_cites_no_book_or_chapter(client):
    t = _norm(_block(client))
    for pat in _CITATIONS:
        assert not re.search(pat, t), pat


def test_prose_outside_the_callout_carries_only_the_pointer_and_the_two_sourced_facts(client):
    t = _norm(_prose_outside_callout(_block(client))).lower()
    assert "in practice" in t or "practitioners commonly" in t
    assert "every ascendant has one" in t


def test_guide_links_back_to_the_planets_page_with_the_new_sentence(client):
    html = _html(client, GUIDE)
    sentence = (
        "A 7th house with no planet in it still has a 7th lord, because every house falls in a sign "
        "and every sign has a ruler; for the planets that do sit in the 7th, see our "
        '<a href="/learn/planets-in-7th-house-marriage/">Planets in 7th House guide</a>.'
    )
    assert html.count(sentence) == 1
    assert html.count('href="/learn/planets-in-7th-house-marriage/"') >= 3


def test_guides_new_sentence_makes_no_outcome_or_ranking_claim(client):
    t = _norm(_html(client, GUIDE)).lower()
    i = t.index("a 7th house with no planet in it still has a 7th lord")
    sentence = t[i : t.index("guide.", i) + len("guide.")]
    for phrase in ("delay", "deny", "denied", "matters more", "read through the 7th lord"):
        assert phrase not in sentence, phrase
