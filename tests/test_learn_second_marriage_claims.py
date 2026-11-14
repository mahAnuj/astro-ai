"""#980: /learn/second-marriage-yoga-kundli/ stops calling 7th lord in the 8th "the strongest
second-marriage signature in classical texts".

`knowledge/*.md` holds no second-marriage text for that placement (grep for "second marriage" /
"remarriage" over the corpus returns nothing), and the sibling 7th-lord guide already says it cannot
source the claim (#978). Two pages contradicting each other on one placement was the defect.

Scope of the first half of this file is that one claim and its copies in the registry (the FAQ answer the
route renders into JSON-LD, and the `llm_summary` that chart.py injects into the natal prompt).

#982 is the follow-up: the page's other ~30 per-signature attributions to 'classical texts' / BPHS /
Jataka Parijata / Saravali / 'marriage-specific compilations' had no `knowledge/*.md` source either (the
corpus holds no second-marriage text). The page now says so once, in a disclosure callout, lists the
general marriage facts the sources we hold DO carry, and words every signature as practitioner practice.
The readings stay. A phrase test: it catches the wording it names, not every possible rewording. The
title and seo_title are deliberately untouched.
"""
from __future__ import annotations

import re

SLUG = "second-marriage-yoga-kundli"


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def test_7th_lord_in_8th_is_no_longer_the_strongest_signature_in_classical_texts(client):
    t = _text(client)
    assert "strongest second-marriage signature in classical texts" not in t
    assert "signature in classical texts" not in t


def test_7th_lord_in_8th_says_it_is_practitioner_usage_we_cannot_source(client):
    t = _text(client)
    assert (
        "7th lord in the 8th (transformation/hidden house): commonly named by practitioners as one of the "
        "stronger second-marriage signatures. We cannot source that to the texts we hold, and we have not measured it."
    ) in t


def test_7th_lord_in_8th_bullet_keeps_its_content_and_the_guide_link(client):
    r = client.get(f"/learn/{SLUG}/")
    assert "in-law complications" in r.text
    assert 'href="/learn/7th-lord-placement-marriage-guide/"' in r.text


def test_registry_fields_do_not_carry_the_strongest_8th_claim():
    a = _article()
    fields = " ".join([a.summary, a.seo_description, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs]).lower()
    assert "8th is the strongest single signature" not in fields
    assert "8 strongest" not in fields
    assert "strongest second-marriage" not in fields
    # the replacement wording is present in both places that carried the ranking
    faq = next(f for f in a.faqs if f["q"] == "Which yoga indicates second marriage in Kundli?")
    assert "we cannot source that ranking to the texts we hold" in faq["a"]
    assert "any ranking among them is unsourced" in a.llm_summary


def test_registry_keeps_every_faq_question():
    assert [f["q"] for f in _article().faqs] == [
        "Which yoga indicates second marriage in Kundli?",
        "Does Venus in 8th house always mean second marriage?",
        "Can Kundli predict divorce?",
        "Is second marriage yoga always bad?",
        "Which Dasha activates second marriage?",
        "What should I do if my chart shows second-marriage signatures?",
    ]


def test_title_and_seo_title_are_untouched():
    a = _article()
    assert a.title == "Second Marriage Indicators in Kundli — Classical Rules and Honest Reading"
    assert a.seo_title == "Second Marriage Yoga in Kundli: Classical Rules, Honest Reading"


def test_7th_lord_guide_dignity_bullet_keeps_the_venus_condition(client):
    """#980 item 2: houses.md:229 reads 'Strong 7th lord + Venus (for men) unafflicted = harmonious
    marriage'. The Dignity bullet had dropped the Venus condition."""
    import re

    r = client.get("/learn/7th-lord-placement-marriage-guide/")
    assert r.status_code == 200
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    assert "a strong 7th lord, together with an unafflicted Venus (for men), as a harmonious marriage" in t
    assert "read a strong 7th lord as favouring a harmonious marriage" not in t


# ---------------------------------------------------------------------------------------------------
# #982 -- the remaining per-signature 'classical' attributions
# ---------------------------------------------------------------------------------------------------

# Each was an attribution of a second-marriage signature to a source no knowledge/*.md file holds.
_BANNED = [
    "classical texts",
    "classical vedic tradition",
    "classical tradition",
    "classical framework",
    "classical framing",
    "classical signature",
    "classical rule",
    "classical stability",
    "classical protector",
    "classical peak-risk",
    "classical instability",
    "classical second-marriage",
    "classical strengthening",
    "classical remed",
    "classically",
    "bphs",
    "jataka parijata",
    "saravali",
    "marriage-specific compilations",
    "what the texts actually name",
    "most consistently named",
    "texts consistently note",
    "texts flag",
    "texts do ",
    "texts describe",
    "texts assign",
]
# The only 'classical' wordings the article may keep: they DENY the attribution.
_ALLOWED = ["not a quotation from a classical text", "not a classical list"]


def _body(client) -> str:
    """Article body only: the page chrome ('Classical sources cited', the H1 that is the untouched
    title) is not what this test is about."""
    t = _text(client)
    start = t.index("In short")
    end = t.index("For the 7th lord's placement across all twelve houses") + 200
    return t[start:end]


def _registry_text() -> str:
    a = _article()
    return " ".join([a.summary, a.seo_description, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs]).lower()


def test_disclosure_says_second_marriage_is_not_in_the_sources_we_hold(client):
    t = _text(client)
    assert "The sources we hold do not discuss second marriage." in t
    assert "widely used interpretive practice" in t
    assert "any ranking among them is practice too" in t


def test_disclosure_comes_before_the_first_signature_section(client):
    html = client.get(f"/learn/{SLUG}/").text
    assert html.count("What is sourced and what is practice") == 1
    disclosure = html.index("What is sourced and what is practice")
    assert disclosure < html.index("The honest framing")
    assert disclosure < html.index("1. The 7th lord in a dusthana")


def test_disclosure_lists_what_the_sources_do_hold(client):
    """Each item traces to a knowledge file: dusthana (houses.md), 7th malefics + Manglik (houses.md,
    vedic_reference.md section 1), karakas and marriage timing (vedic_reference.md 5.5), 8th-house
    in-laws (houses.md), D-9 (vedic_reference.md 6.9 and the D-9 row), Sade Sati (vedic_reference.md 2.3)."""
    t = _text(client)
    for needle in (
        "the dusthana houses, the houses of struggle and obstacles",
        "malefics in the 7th without cancellation are read as marital delay or friction",
        "Mars in the 7th is the Manglik pattern",
        "Venus is the marriage karaka in a male chart and Jupiter in a female chart",
        "the 8th house covers in-laws (the spouse's family)",
        "marriage is read in the D-9 Navamsha, and the period of the 7th lord in the D-9 can give marriage",
        "maturity-forcing transit",
    ):
        assert needle in t, needle


def test_page_keeps_every_signature_section_and_reading(client):
    r = client.get(f"/learn/{SLUG}/")
    heads = re.findall(r"<h3>(\d)\. ([^<]+)</h3>", r.text)
    assert [n for n, _ in heads] == ["1", "2", "3", "4", "5", "6"]
    for reading in (
        "recurring friction pattern in the partnership",
        "delay + emotional distance pattern",
        "unconventional or foreign partnership",
        "detachment pattern",
        "physical separation pattern",
        "Chosen-transformation pattern",
        "multiple partnerships across a lifetime",
        "Do not read D-1 signatures alone; always check the D-9.",
    ):
        assert reading in r.text, reading


def test_no_signature_is_attributed_to_classical_texts_or_named_books(client):
    t = _body(client).lower()
    for phrase in _ALLOWED:
        t = t.replace(phrase, "")
    for phrase in _BANNED:
        assert phrase not in t, phrase
    assert "classical" not in t
    assert not re.search(r"\btexts\b(?! we hold)", t)


def test_the_signature_heading_no_longer_claims_the_texts_name_them(client):
    r = client.get(f"/learn/{SLUG}/")
    assert "<h2>The signatures practitioners commonly name</h2>" in r.text
    assert "Classical signatures" not in r.text


def test_the_dusthana_ranking_is_not_the_most_consistently_named(client):
    t = _text(client)
    assert "A commonly named signature." in t
    assert "most consistently named" not in t


def test_the_d9_rule_is_marked_as_practice_not_a_classical_rule(client):
    t = _text(client)
    assert "they do not state a confirm-or-soften rule for second-marriage readings, so that rule is practice" in t
    assert "insists" not in t


def test_widow_yogas_are_not_credited_to_classical_texts(client):
    t = _text(client)
    assert "some practitioners describe specific patterns for spouse-early-departure" in t
    assert "Some practitioners describe widow/widower yogas" in t


def test_registry_fields_carry_no_classical_attribution():
    t = _registry_text()
    # title and seo_title are deliberately untouched and are not in this string
    for phrase in _BANNED:
        assert phrase not in t, phrase
    for phrase in _ALLOWED:
        t = t.replace(phrase, "")
    assert "classical" not in t


def test_registry_llm_summary_says_the_signatures_are_practice():
    s = _article().llm_summary
    assert "no second-marriage text in the sources we hold" in s
    assert "no confirm rule is stated" in s
    assert "practice, unsourced" in s
    assert "MUST confirm" not in s
    assert "peak-risk," not in s
