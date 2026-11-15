"""#1056: the two /learn muhurat articles stop calling unsourced rules classical.

#1024 (PR #1055) relabelled the Muhurat Finder and its landing copy and deliberately left the articles.
knowledge/vedic_reference.md section 29.10 measures chaturmas, kharmas, dagdha and choghadiya as absent from
every book this site holds, and the eclipse-day rule (with its one-day margin) has no source there either.
section 29.9 does hold Panchak, the five nitya-yogas Raman condemns, and his tithi and weekday judgements.

So /learn/vivah-muhurat-2027/ and /learn/griha-pravesh-muhurat-2026-2027/ now say, per rule, which is Raman's
and which is a widely followed convention the finder applies. The 'Classical sources cited' callouts, which
credited Ashvalayana Grihya Sutra, Padma Purana, Vasishtha Samhita, a 'Kalanidhi' chapter of BPHS, Vastu Vidya
and Mayamatam (none held), became 'What this guide checks, and what it does not'.

Pinned through the real route and on the registry fields the route renders. A phrase test: it catches the
wording it names, not every possible rewording. The Namkaran rule defects (#1060, #1062) are separate.
"""
from __future__ import annotations

import re

import pytest

SLUGS = ("vivah-muhurat-2027", "griha-pravesh-muhurat-2026-2027")

# Attributions with nothing behind them in the held books (knowledge/SOURCES.md).
_UNHELD_SOURCES = (
    "ashvalayana", "padma purana", "vasishtha samhita", "kalanidhi", "mayamatam", "vastu vidya",
    "vastu shastra +",
)


def _html(client, slug: str) -> str:
    """Just the <article> body. The page chrome (footer 'Classical sources cited' disclaimer, inline CSS
    comments) is site-wide and is not what #1056 is about."""
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    m = re.search(r"<article\b.*?</article>", r.text, flags=re.S)
    assert m, "learn article container not found"
    return re.sub(r"<!--.*?-->", "", m.group(0), flags=re.S)


def _text(client, slug: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _html(client, slug)))


def _article(slug: str):
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == slug)


def _registry_text(slug: str) -> str:
    a = _article(slug)
    return " ".join(
        [a.title, a.summary, a.seo_title, a.seo_description, a.llm_summary]
        + [f["q"] + " " + f["a"] for f in a.faqs]
    ).lower()


@pytest.mark.parametrize("slug", SLUGS)
def test_the_article_never_calls_a_rule_classical(client, slug):
    t = _text(client, slug).lower()
    assert "classical" not in t.replace("classic-", ""), re.findall(r".{40}classical.{40}", t)


@pytest.mark.parametrize("slug", SLUGS)
def test_the_registry_fields_never_call_a_rule_classical(slug):
    assert "classical" not in _registry_text(slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_no_source_the_corpus_does_not_hold_is_credited(client, slug):
    t = _text(client, slug).lower()
    for needle in _UNHELD_SOURCES:
        assert needle not in t, needle
        assert needle not in _registry_text(slug), needle


# A source-shaped word the held books do not back. Broader than the named list above on purpose: a rewrite that
# swaps Padma Purana for Vishnu Purana, or 'Brihat Parashara', must still fail. Raman and Rao are the only
# authors these two articles may name.
_SOURCE_SHAPED = ("purana", "samhita", "sutra", "parashara", "shastra", "chintamani", "scripture")


@pytest.mark.parametrize("slug", SLUGS)
def test_no_source_shaped_word_appears_at_all(client, slug):
    body = _text(client, slug).lower()
    reg = _registry_text(slug)
    for w in _SOURCE_SHAPED:
        assert w not in body, w
        assert w not in reg, w


@pytest.mark.parametrize("slug", SLUGS)
def test_the_sources_callout_says_what_is_checked_and_what_is_not(client, slug):
    html = _html(client, slug)
    assert html.count("What this guide checks, and what it does not") == 1
    assert "Classical sources cited" not in html
    t = _text(client, slug)
    assert "we could not trace the dagdha pairings to any source" in t.lower()
    assert "Chintamani" not in t  # no attribution the finder itself does not make (muhurat.py _DAGDHA comment)
    assert "B.V. Raman, Muhurtha (1948)" in t


def test_vivah_labels_each_unsourced_rule_as_a_convention_in_its_own_section(client):
    html = _html(client, "vivah-muhurat-2027")
    for heading, label in (
        ("3. No Kharmas", "we have not found a Kharmas rule in the books this site holds"),
        ("4. Chaturmas restriction", "we have not found a Chaturmas rule in the books this site holds"),
        ("6. Favourable tithis + no Dagdha yoga", "we could not trace them to a source"),
        ("8. No eclipse days", "we have not found an eclipse-day rule or the one-day margin in the books this site holds"),
    ):
        start = html.index(heading)
        nxt = html.find("<h3>", start + 10)
        assert label in re.sub(r"\s+", " ", html[start: nxt if nxt != -1 else len(html)]), heading


def test_vivah_intro_separates_raman_from_convention(client):
    t = _text(client, "vivah-muhurat-2027")
    assert "Panchak and the tithi rule are checked against B.V. Raman" in t
    assert "widely followed conventions that our finder applies and that we have not found in the books this site holds" in t


def test_griha_pravesh_labels_the_four_unsourced_criteria(client):
    html = _html(client, "griha-pravesh-muhurat-2026-2027")
    assert html.count("A widely followed convention that our finder applies, not a rule from the books this site holds") == 3
    assert "a widely followed convention of &quot;burnt&quot; tithi-weekday pairings" in html or \
        "a widely followed convention of \"burnt\" tithi-weekday pairings" in html
    assert "we could not trace them to a source" in html


def test_registry_summaries_carry_the_same_split():
    v = _article("vivah-muhurat-2027")
    assert "checked against B.V. Raman's Muhurtha" in v.summary
    assert "widely followed conventions" in v.llm_summary
    g = _article("griha-pravesh-muhurat-2026-2027")
    assert "widely followed conventions rather than rules from the books this site holds" in g.summary
    assert "widely followed conventions, not rules from the books this site holds" in g.llm_summary


def test_the_unsourced_panchak_subtypes_are_not_stated_as_classical():
    a = _article("vivah-muhurat-2027")
    faq = next(f["a"] for f in a.faqs if f["q"].startswith("What is Panchak"))
    assert "we have not checked those against the books this site holds" in faq


def test_the_finder_links_stop_saying_classical(client):
    from astro_ai import muhurat as m

    html = client.get("/muhurat").text
    assert "The classical rules behind wedding dates" not in html
    assert "The rules behind wedding dates, and where each comes from" in html
    assert "is the classical starting syllable" not in html
    for ev in m.EVENT_LANDING.values():
        for _href, label in ev.get("related_articles", ()):
            assert "classical" not in label.lower(), label
