"""#1321: the manglik-remedies headings and the Manglik-Manglik FAQ stop claiming more than the held sources say.

* h2 1 called Hanuman "Mars's presiding deity", the toor daal item called it "Mars's classical grain",
  and h2 6 called matching "the truest Manglik remedy". knowledge/ holds a modern textbook's table for
  the first two and one held antidote list for the third; none of them states a classical ranking.
* The comparable-severity condition was attributed to "tradition" (section 6) and to "one held
  antidote list ... one condition that most retellings drop" (FAQ 4). The held list names no
  severity condition; the band is Shubh Bhagya's own convention.

Pinned through the real route, on the visible text and on the FAQPage JSON-LD. It is a phrase test:
it catches the wording it names, not every possible rewording.
"""
from __future__ import annotations

import html
import json
import re

_PATH = "/learn/manglik-remedies/"
_FAQ4_Q = "What if I'm Manglik and my partner is not?"


def _page(client) -> str:
    r = client.get(_PATH)
    assert r.status_code == 200
    return r.text


def _text(page: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))


def _faq4_jsonld_answer(page: str) -> str:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    for b in blocks:
        data = json.loads(b)
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if node.get("@type") != "FAQPage":
                continue
            for q in node["mainEntity"]:
                if html.unescape(q["name"]) == _FAQ4_Q:
                    return html.unescape(q["acceptedAnswer"]["text"])
    raise AssertionError("FAQ 4 not found in the FAQPage JSON-LD")


def _faq4_visible(text: str) -> str:
    i = text.index(_FAQ4_Q)
    return text[i:i + 1500]


def test_headings_do_not_claim_a_classical_ranking(client):
    t = _text(_page(client))
    for bad in ("presiding deity", "classical grain", "truest"):
        assert bad not in t, bad
    for good in (
        "first of Mars's deities in a modern table",
        "the grain a modern textbook's table gives Mars",
        "the one remedy a held source states",
    ):
        assert good in t, good


def test_faq4_does_not_attribute_the_severity_condition_to_the_held_list(client):
    page = _page(client)
    for surface, t in (("visible", _faq4_visible(_text(page))), ("json-ld", _faq4_jsonld_answer(page))):
        for good in (
            "it names no severity condition",
            "we have not found that condition in a book we hold",
            "That band is our convention, not scripture",
        ):
            assert good in t, f"{surface}: {good}"
        for bad in ("one condition that most retellings drop", "Tradition asks for comparability"):
            assert bad not in t, f"{surface}: {bad}"


def test_section_6_does_not_attribute_the_threshold_to_tradition(client):
    t = _text(_page(client))
    i = t.index("6. Marriage matching")
    sec = t[i:i + 1800]
    assert "Tradition also says" not in sec
    assert "we have not found that condition in a book we hold" in sec
    assert "the severity condition is ours, not that author's" in sec
