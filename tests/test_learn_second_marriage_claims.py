"""#980: /learn/second-marriage-yoga-kundli/ stops calling 7th lord in the 8th "the strongest
second-marriage signature in classical texts".

`knowledge/*.md` holds no second-marriage text for that placement (grep for "second marriage" /
"remarriage" over the corpus returns nothing), and the sibling 7th-lord guide already says it cannot
source the claim (#978). Two pages contradicting each other on one placement was the defect.

Scope is this one claim and its copies in the registry (the FAQ answer the route renders into JSON-LD,
and the `llm_summary` that chart.py injects into the natal prompt). The page's other 'classical'
attributions are NOT claimed grounded by this test; they are a follow-up. A phrase test: it catches the
wording it names, not every possible rewording. The title and seo_title are deliberately untouched.
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
