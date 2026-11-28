"""#1501: the home-page "Don't fear your Kundali" cards stop asserting classical backing the held
books do not give.

* Sade Sati: "most lives are better on the other side of it" is in no held book
  (knowledge/vedic_reference.md section 2.7.1-2 gives the transit definition and says the natal
  position is the main thing).
* Manglik: "a lot of people labelled Manglik actually aren't" is in no held book, and the held
  sources disagree on cancellation (grahas.md section 12.4 lists rules; vedic_reference.md
  section 1.6.1, Vasudev, rejects them).
* Kaal Sarp: "over-diagnosed" is in no held book (vedic_reference.md section 3.4).
* The section lead said "the classical texts"; it now names "the books we hold".

Pinned through the real route. It is a phrase test: it catches only the wording it names, not
every possible rewording that reintroduces an unsourced claim. The learn pages that still carry
the old claims are a separate follow-up.
"""
from __future__ import annotations

import html
import re

import pytest

_REMOVED = [
    "what the classical texts actually say",
    "most lives are better on the other side",
    "actually aren",
    "over-diagnosed",
]


def _home_text(client) -> str:
    r = client.get("/")
    assert r.status_code == 200
    stripped = re.sub(r"<[^>]+>", " ", r.text)
    return re.sub(r"\s+", " ", html.unescape(stripped)).lower()


@pytest.mark.parametrize("phrase", _REMOVED)
def test_home_page_no_longer_asserts_unsourced_classical_backing(client, phrase):
    assert phrase not in _home_text(client)


def test_home_worry_cards_name_the_books_we_hold_and_attribute_our_own_view(client):
    t = _home_text(client)
    assert "what the books we hold actually say about them" in t
    assert "in our view" in t
