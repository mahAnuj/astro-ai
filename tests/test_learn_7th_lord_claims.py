"""#978: /learn/7th-lord-placement-marriage-guide/ stops presenting twelve per-house readings as classical.

`knowledge/*.md` holds no per-house 7th-lord placement text. It holds four things: the 7th is a
maraka house (houses.md), a strong 7th lord + unafflicted Venus reads as a harmonious marriage
(houses.md), Jupiter aspecting the 7th house or 7th lord is a Manglik cancellation
(vedic_reference.md rule 7), and the dasha of the 7th lord (and the D-9 7th lord) times marriage
(vedic_reference.md section 5.5 and the D-9 row). Everything else on the page is interpretive practice,
so the page says so once, above the twelve sections, and no per-house claim says a classical text
names it. The readings stay: the defect was the silence, not the content.

Pinned through the real route, and on the registry fields the route also renders (summary,
seo_description, FAQ answers -- the FAQ lands in the page's JSON-LD). A phrase test: it catches the
wording it names, not every possible rewording. The title and seo_title are deliberately untouched.
"""
from __future__ import annotations

import re

SLUG = "7th-lord-placement-marriage-guide"

# Each was a per-house claim attributed to classical texts with no source in knowledge/.
_BANNED = [
    "classical texts",
    "some classical texts",
    "classical timing signature",
    "classical on-time",
    "classical primary",
    "classical caution",
    "classical mention",
    "classically low",
    "classically-praised",
    "classically indicates",
    "classically rules",
    "classical readings",
    "classical tradition insists",
    "classical tradition",
    "full classical reading",
    "classical marriage reading",
    "classical shortlist",
    "classical 'bedroom",
    "honestly named in classical",
    "primary classical",
]


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_text() -> str:
    a = _article()
    return " ".join([a.summary, a.seo_description] + [f["q"] + " " + f["a"] for f in a.faqs]).lower()


def test_disclosure_says_the_per_house_readings_are_practice_not_sourced(client):
    t = _text(client)
    assert "The twelve per-house readings below are widely used interpretive practice" in t
    assert "do not set out the 7th lord's placement house by house" in t


def test_disclosure_comes_before_the_first_per_house_section(client):
    r = client.get(f"/learn/{SLUG}/")
    html = r.text
    assert html.index("widely used interpretive practice") < html.index("7th lord in the 1st house</h2>")


def test_page_keeps_all_twelve_per_house_sections(client):
    r = client.get(f"/learn/{SLUG}/")
    heads = re.findall(r"<h2>7th lord in the (\d+)(?:st|nd|rd|th) house</h2>", r.text)
    assert heads == [str(n) for n in range(1, 13)]


def test_no_per_house_claim_is_attributed_to_classical_texts(client):
    t = _text(client).lower()
    for phrase in _BANNED:
        assert phrase not in t, phrase


def test_registry_fields_carry_no_classical_attribution():
    t = _registry_text()
    for phrase in _BANNED:
        assert phrase not in t, phrase
    # the broader forms the page also stopped using
    assert not re.search(r"classical(ly)? (reading|primary|low|praised)", t)


def test_registry_keeps_every_faq_question():
    assert [f["q"] for f in _article().faqs] == [
        "What does 7th lord in 6th house mean for marriage?",
        "Is 7th lord in 8th house always bad?",
        "What if 7th lord is in own house (7th)?",
        "Does 7th lord in 12th house mean foreign spouse?",
        "Which placement of 7th lord is best for happy marriage?",
    ]


def test_second_marriage_and_spouse_longevity_say_they_are_not_sourced(client):
    t = _text(client)
    assert "We cannot source that to the texts we hold, and we have not measured it" in t
    assert "We cannot source that to the texts we hold, so treat it as a tendency" in t


def test_sourced_items_remain(client):
    t = _text(client)
    assert "<em>maraka</em>" in client.get(f"/learn/{SLUG}/").text
    assert "maraka house" in t
    assert "dasha or antardasha of the 7th lord is one of the marriage-timing indicators" in t
    assert "period of the 7th lord in the D-9 Navamsha can also give marriage" in t
    assert "Jupiter aspecting the 7th house or the 7th lord is listed among the cancellation rules for Manglik dosha" in t
    assert "strong 7th lord with an unafflicted Venus (for men) is read as a harmonious marriage" in t


def test_jupiter_softener_no_longer_calls_itself_the_single_most_protective_signature(client):
    t = _text(client)
    assert "single most protective" not in t
    assert "common practice, not something those sources state" in t


def test_reading_order_is_marked_as_a_working_order(client):
    t = _text(client)
    assert "do not lay this five-step order down" in t
    assert "Classical tradition reads the marriage picture" not in t


def test_title_and_seo_title_are_untouched():
    a = _article()
    assert a.title == "7th Lord Placement Guide: How Your Marriage Life Reads From the Ruler of Partnership"
    assert a.seo_title == "7th Lord Placement Guide: Marriage Reading Across 12 Houses"
