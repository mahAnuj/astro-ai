"""#988: /learn/planets-in-7th-house-marriage/ stops attributing per-planet 7th-house readings to
'classical texts'.

`knowledge/*.md` holds the 7th house in general (houses.md: Yuvati Bhava, karakas, malefics in the 7th,
Saturn's Digbala), the Manglik rules (vedic_reference.md section 1), the karaka table (grahas.md section 3),
Malavya Yoga (vedic_reference.md section 4.1) and D-9 as the marriage chart. It holds NO per-planet reading
of the 7th house for the Sun, Moon, Mercury, Jupiter, Venus, Rahu or Ketu, so the page's ~30 'classical /
classically / classical texts' attributions had nothing behind them (same defect class as #978 and #982).

The page now says so once, in a disclosure callout above the first section, lists what the sources we hold DO
carry, and words every per-planet reading as practitioner practice. The readings, headings, title and
seo_title are unchanged. The Manglik content already cited the held sources and stays.

Pinned through the real route, and on the registry fields the route renders (summary, seo_description, FAQ
answers -- the FAQ lands in the page's JSON-LD) plus the llm_summary. A phrase test: it catches the wording it
names, not every possible rewording.
"""
from __future__ import annotations

import re

SLUG = "planets-in-7th-house-marriage"

# Each was a per-planet claim (or a ranking of planets) attributed to classical texts with no source in knowledge/.
_BANNED = [
    "classical texts",
    "classical vedic tradition",
    "classical tradition",
    "classical reading",
    "classical primary",
    "classical protective",
    "classical instability",
    "classical caveat",
    "classical late-marriage",
    "classical concern",
    "classical patterns",
    "classically",
    "across classical",
    "in the classical",
]
# The only 'classical' wordings the page may keep: each DENIES an attribution.
_ALLOWED = [
    "not a quotation from a classical text",
    "no classical text behind it",
]


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


def _body(client) -> str:
    """Article body only: the page chrome ('Classical sources cited', the H1 that is the untouched title)
    is not what these tests are about."""
    t = _text(client)
    start = t.index("In short")
    end = t.index("7th Lord Placement guide") + 30
    return t[start:end]


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_text() -> str:
    a = _article()
    return " ".join([a.summary, a.seo_description, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs]).lower()


def test_disclosure_says_the_per_planet_readings_are_practice_not_sourced(client):
    t = _text(client)
    assert "The sources we hold do not set out per-planet readings for the 7th house." in t
    assert "widely used interpretive practice" in t
    assert "is practice, not something those sources state" in t


def test_disclosure_comes_once_and_before_the_first_section(client):
    html = client.get(f"/learn/{SLUG}/").text
    assert html.count("What is sourced and what is practice") == 1
    disclosure = html.index("What is sourced and what is practice")
    assert disclosure < html.index("Framing — the 7th house as the mirror of self</h2>")
    assert disclosure < html.index("Sun in the 7th house</h2>")


def test_disclosure_lists_what_the_sources_do_hold(client):
    """Each item traces to a knowledge file: Yuvati Bhava / malefics in the 7th / Saturn Digbala (houses.md
    7th House), Manglik houses and cancellation rules (vedic_reference.md 1.1 and 1.3), the karaka table
    (grahas.md 3), Venus and Jupiter as marriage karakas (houses.md), Malavya Yoga (vedic_reference.md 4.1),
    D-9 and the universal 7th aspect (houses.md marriage table, aspects.md)."""
    t = _text(client)
    for needle in (
        "the 7th is Yuvati Bhava",  # the Sanskrit names are <em>-wrapped in the page
        "the house of spouse, marriage and partnerships",
        "malefics in the 7th without cancellation are read as Manglik-like patterns and marital delay or friction",
        "Mars in the 7th is a Manglik placement (the 7th and 8th are the houses treated as most serious)",
        "Jupiter aspecting the 7th house or its lord",
        "Saturn has directional strength (Digbala) in the 7th",
        "marrying someone older or late, and often stable long-term",
        "Venus for marriage, luxury and the arts",
        "Venus is the marriage karaka in a male chart and Jupiter in a female chart",
        "Malavya Yoga is one of the five Pancha Mahapurusha Yogas, formed when Venus is in its own sign or exalted in a kendra",
        "marriage and spouse are read in the D-9 Navamsha, and every planet aspects the 7th house from itself",
    ):
        assert needle in t, needle


def test_page_keeps_all_nine_planet_sections_and_their_readings(client):
    r = client.get(f"/learn/{SLUG}/")
    heads = re.findall(r"<h2>(\w+) in the 7th house</h2>", r.text)
    assert heads == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    assert "<h2>Per-Ascendant shifts — how the same planet reads differently</h2>" in r.text
    for reading in (
        "Dominant spouse pattern.",
        "Emotionally responsive partner.",
        "Energetic, forceful partner.",
        "Communicative, verbally alive partner.",
        "Wise, dharmic, teacher-figure spouse.",
        "Beautiful, refined, aesthetically-inclined spouse.",
        "Older or more serious partner.",
        "Foreign or unconventional spouse.",
        "Detached or spiritually-oriented spouse.",
    ):
        assert reading in r.text, reading


def test_no_per_planet_reading_is_attributed_to_classical_texts(client):
    t = _body(client).lower()
    for phrase in _ALLOWED:
        t = t.replace(phrase, "")
    for phrase in _BANNED:
        assert phrase not in t, phrase
    assert "classical" not in t
    # no bare "texts say/flag" attribution survives; "the sources we work from" is the held-source wording
    assert not re.search(r"\btexts\b", t)


def test_unsourced_per_planet_claims_say_so_where_they_are_made(client):
    # article body only: the Saturn FAQ answer (also rendered on the page and in JSON-LD) carries
    # "we have not measured that" too, so a whole-page check would stay green with the body sentence gone
    t = _body(client)
    assert "the sources we work from do not say so. This is a tendency" in t  # Sun, spouse health
    assert "the sources we work from give no such figure" in t  # Mercury, younger spouse
    assert "neither the flag nor the reason is in them" in t  # Jupiter, late marriage for women
    assert "the past-life narrative is practice" in t  # Ketu
    assert "with lower divorce rates than average; we have not measured that" in t  # Saturn
    # second marriage is named as practice at both article-body placements that raise it (Mars, Rahu)
    assert t.count("the sources we work from do not discuss second marriage") == 2


def test_saturn_keeps_only_what_the_sources_say_as_sourced(client):
    t = _text(client)
    assert "the sources we work from say the placement can mean marrying late; the age range is practice" in t
    assert 'the sources we work from say only "someone older"' in t
    assert "The sources we work from describe Saturn in the 7th as often stable long-term." in t


def test_malavya_yoga_is_the_sourced_list_not_the_strongest_in_the_texts(client):
    t = _text(client)
    assert "one of the five Pancha Mahapurusha Yogas, which the sources we work from list with beauty, luxury, art and marital happiness among its effects" in t
    assert "strongest marriage-related yogas" not in t


def test_manglik_content_keeps_its_sourced_citations(client):
    t = _text(client)
    assert "one of the six Manglik-triggering houses (the sources we work from list five and treat the 1st as an optional addition" in t
    assert "that is a modern folk claim with no classical text behind it, and we do not rely on it" in t
    assert "(Cancer/Leo Ascendant Yogakaraka rule, Mars in own sign, Jupiter aspect, matching with a similar chart)" in t
    assert "the remedy the sources we work from cite most" in t


def test_d9_note_cites_the_sources_and_marks_the_rest_as_practice(client):
    t = _text(client)
    assert "primary reference chart for marriage and spouse in the sources we work from" in t
    assert "Practitioners commonly hold that when they disagree, the D-9 describes the private lived reality" in t
    assert "Serious classical reading" not in t


def test_registry_fields_carry_no_classical_attribution():
    t = _registry_text()
    # title and seo_title are deliberately untouched and are not in this string
    for phrase in _BANNED:
        assert phrase not in t, phrase
    assert "classical" not in t
    assert not re.search(r"\btexts\b", t)


def test_registry_says_the_readings_are_practice():
    a = _article()
    assert "which parts the sources we hold support and which are interpretive practice" in a.summary
    assert "common reading with per-Ascendant shifts" in a.seo_description
    assert "Per-planet 7th-house readings are common practice; the held sources do not set them out" in a.llm_summary
    assert "(practice, not sourced)" in a.llm_summary
    faq = {f["q"]: f["a"] for f in a.faqs}
    assert "we have not measured that" in faq["Is Saturn in 7th house bad for marriage?"]
    assert "the sources we work from do not discuss second marriage" in faq["What does Rahu in 7th house mean?"]


def test_registry_keeps_every_faq_question():
    assert [f["q"] for f in _article().faqs] == [
        "Which planet in the 7th house is best for marriage?",
        "What does Venus in 7th house mean for marriage?",
        "Is Saturn in 7th house bad for marriage?",
        "What does Rahu in 7th house mean?",
        "Does Mars in 7th house always cause Manglik dosha?",
        "What if I have two or more planets in the 7th house?",
    ]


def test_title_and_seo_title_are_untouched():
    a = _article()
    assert a.title == "Planets in the 7th House and What They Mean for Your Marriage"
    assert a.seo_title == "Planets in 7th House: Marriage Meaning of Each Graha"
