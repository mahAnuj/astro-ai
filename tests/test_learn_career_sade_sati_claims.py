"""#1082: /learn/career-during-sade-sati/ and its FAQ stop attributing to the classics what they do not say.

The page shipped one wrong attribution and four unsourced groups, all hand-written prose:

* "Classical Vedic tradition explicitly notes this" under a dignity list (own sign, exalted in
  Libra, kendra with Jupiter). The held source (Rao, Lessons Vol. I, note 29;
  knowledge/vedic_reference.md section 2.7.2, lines 476-478) is functional: Saturn as lagna lord
  or yogakaraka. Own sign / exaltation / "good house" are our generalisation and UNSOURCED.
* "Vedic tradition consistently names" a list (Libra judiciary, "Jupiter's rescue", past age 45).
* Sub-windows (early Madhya caution, late Madhya good window) called "the Vedic caution". Rao
  gives only the three 2.5-year signs.
* Ashtama / Kantaka named as if classical ("literally thorn Saturn") with specific effects.
  The sourced fact is the Gochara table: Saturn in the 4th and 8th from the Moon is malefic.
* A flat Saturn-domains career list.

The registry's llm_summary is not injected by any code path today and carried none of these
claims; it is pinned here anyway so a later edit cannot add them.

What this does NOT catch: phrase tests catch the wording they name, not every rewording, and
whether the labelled-as-practice text is good advice is not a question a test can answer.
"""
from __future__ import annotations

import re

import pytest

from astro_ai.learn_registry import get_article

SLUG = "career-during-sade-sati"


def _page(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return r.text


def _faq(question_fragment: str) -> str:
    for f in get_article(SLUG).faqs:
        if question_fragment in f["q"]:
            return f["a"]
    raise AssertionError(f"no FAQ containing {question_fragment!r}")


def _all_text(client) -> str:
    art = get_article(SLUG)
    faqs = " ".join(f["a"] for f in art.faqs)
    return _page(client) + " " + faqs + " " + art.llm_summary


def _section(page: str, heading: str) -> str:
    m = re.search(rf"<h2>{re.escape(heading)}</h2>(.*?)<h2>", page, re.S)
    assert m, f"section {heading!r} missing"
    return m.group(1)


# --- row 1: the strong-Saturn rule is Rao's functional one ---------------------------------

def test_strong_saturn_rule_is_the_functional_one_on_page_and_faqs(client):
    page = _page(client)
    faq1 = _faq("always cause job loss")
    faq3 = _faq("get a promotion")
    for text in (page, faq1, faq3):
        assert "lagna lord" in text and "yogakaraka" in text
        assert "Capricorn or Aquarius rising" in text and "Taurus or Libra rising" in text
    for text in (page, faq1, faq3):
        assert "own sign, exalted" not in text
        assert "in a kendra" not in text
        assert "Saturn in its own sign" not in text
        assert "strong natal Saturn" not in text
        assert "People with strong natal Saturn" not in text


def test_classical_tradition_is_not_said_to_note_the_dignity_list(client):
    text = _all_text(client)
    assert "Classical Vedic tradition explicitly notes this" not in text
    assert "Classical tradition explicitly names the pattern" not in text
    assert "Vedic tradition consistently names" not in text


# --- row 2: the "people who benefit" section -----------------------------------------------

def test_benefit_section_keeps_the_sourced_condition_and_drops_unsourced_signatures(client):
    page = _page(client)
    section = _section(page, "The people who benefit from Sade Sati at work")
    assert "lagna lord" in section and "yogakaraka" in section
    assert "not about dignity" in section  # states why the dignity list is not the source's rule
    for gone in ("classical peak placement", "judiciary, arbitration", "Jupiter's rescue",
                 "past age 45", "karaka of age", "Saturn in a kendra with Jupiter"):
        assert gone not in page, f"{gone!r} is back"
    # what stays beyond the sourced rule must be labelled, not worded as classical
    assert "common practice" in section
    assert "not a classical rule" in section


# --- row 3: sub-windows are the site's guidance --------------------------------------------

def test_sub_windows_are_not_called_vedic_or_classical(client):
    text = _all_text(client)
    assert "The Vedic caution" not in text
    page = _page(client)
    assert "this site's practical guidance, not a classical rule" in _section(page, "When to change jobs during Sade Sati")
    assert "practical guidance, not a classical rule" in page.split("Starting a business during Sade Sati")[1].split("<h2>")[0]
    assert "not a classical rule" in _faq("change jobs")
    assert "not a classical rule" in _faq("start a business")
    assert "The usual advice is" not in _faq("change jobs")


# --- row 4: Ashtama / Kantaka ---------------------------------------------------------------

def test_ashtama_and_kantaka_are_modern_names_with_the_gochara_table_as_the_sourced_fact(client):
    page = _page(client)
    assert "thorn Saturn" not in page and "literally \"" not in page
    assert "modern names, not classical terms" in page
    assert "Gochara table" in page
    assert "cluster here" not in page


# --- row 5: Saturn-domains career list ------------------------------------------------------

def test_saturn_domains_list_is_not_stated_as_fact(client):
    page = _page(client)
    assert "these are Saturn's domains" not in page
    assert "Saturn-native fields" not in _faq("always cause job loss")
    section = _section(page, "The people who benefit from Sade Sati at work")
    assert "practitioners commonly associate with Saturn" in section


# --- the sweep for other attributions -------------------------------------------------------

def test_saturday_donations_are_split_between_sourced_and_custom(client):
    page = _page(client)
    assert "it is a classical structure" not in page
    assert "Sesame seeds are the grain a modern textbook's table gives Saturn" in page and "common practice" in page


def test_seo_description_does_not_promise_classical_guidance():
    assert "classical" not in get_article(SLUG).seo_description.lower()


@pytest.mark.parametrize("attribution", ["Phaladeepika", "Brihat Jataka", "BPHS", "knowledge base"])
def test_unheld_books_and_internal_files_are_not_cited(client, attribution):
    assert attribution not in _all_text(client), attribution


def test_llm_summary_carries_no_dignity_or_classical_claim():
    summary = get_article(SLUG).llm_summary
    for bad in ("own sign", "exalted", "kendra", "strong natal Saturn", "classical", "Vedic tradition"):
        assert bad not in summary, bad


def test_page_and_jsonld_faq_still_render(client):
    import json

    page = _page(client)
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    faq_blocks = [json.loads(b) for b in blocks if '"FAQPage"' in b]
    assert faq_blocks, "FAQPage JSON-LD missing"
    answers = " ".join(q["acceptedAnswer"]["text"] for q in faq_blocks[0]["mainEntity"])
    assert "lagna lord" in answers and "yogakaraka" in answers
