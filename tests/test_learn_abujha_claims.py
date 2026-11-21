"""#1346 + #1354: the two /learn muhurat articles say about Abujha dates what the finder does.

Since #1346 the finder applies the hard exclusions first and lifts an Abujha date only if it clears
them, so every Abujha date in 2026-11..2027-12 comes out `avoid` for New Delhi (Panchak on
2026-11-20, 2027-02-11, 2027-11-10, 2027-11-11; an avoid tithi on 2027-05-09; Venus combust on
2027-07-12). The articles used to say the opposite: Devuthani 2026-11-20 "rated excellent" and
"without being cancelled by Panchak", the Vivah page "universally auspicious ... regardless of
tithi/nakshatra/weekday" and listing three Panchak days as wedding dates. Abujha is a regional
almanac custom that no book this site holds names (knowledge/vedic_reference.md 29.14).

A phrase test for the wording, an execution test for the dates: the dates are asserted against the
real `find_candidates`, not against a table copied into the test. No network: geocoding is stubbed
to New Delhi. Mutation rows: scripts/mutations/2026_11_21_1346_abujha_articles.py.
"""
from __future__ import annotations

import re
from datetime import date

import pytest

from astro_ai import chart, muhurat as m

NEW_DELHI = (28.6139, 77.2090, "Asia/Kolkata")
VIVAH = "vivah-muhurat-2027"
GRIHA = "griha-pravesh-muhurat-2026-2027"

# The five 2027 Abujha dates the Vivah article lists or names, and the two Devuthani dates the
# Griha Pravesh article dates.
VIVAH_ABUJHA_2027 = (date(2027, 2, 11), date(2027, 5, 9), date(2027, 7, 12),
                     date(2027, 11, 10), date(2027, 11, 11))
GRIHA_ABUJHA = (date(2026, 11, 20), date(2027, 11, 10))

RETIRED = ("regardless of tithi", "without being cancelled by panchak", "standing exception",
           "universally auspicious", "override calculation", "no muhurat calculation needed")


@pytest.fixture(autouse=True)
def _delhi(monkeypatch):
    monkeypatch.setattr(chart, "geocode_place", lambda place: NEW_DELHI)


def _rating(event: str, d: date) -> str:
    rows = [c for c in m.find_candidates(event, "Delhi", d, 1) if c.d == d]
    assert len(rows) == 1, rows
    return rows[0].rating


def _text(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    body = re.search(r"<article\b.*?</article>", r.text, flags=re.S).group(0)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).lower()


@pytest.mark.parametrize("d", VIVAH_ABUJHA_2027)
def test_every_2027_abujha_date_the_vivah_article_names_is_avoid_in_the_finder(d):
    assert _rating("vivah", d) == "avoid"


@pytest.mark.parametrize("d", GRIHA_ABUJHA)
def test_the_devuthani_dates_the_griha_pravesh_article_names_are_avoid_in_the_finder(d):
    assert _rating("griha_pravesh", d) == "avoid"


@pytest.mark.parametrize("slug", (VIVAH, GRIHA))
def test_neither_article_still_makes_the_retired_abujha_claims(client, slug):
    t = _text(client, slug)
    assert [p for p in RETIRED if p in t] == []


def test_the_griha_pravesh_article_says_devuthani_2026_is_avoid_and_panchak_is_not_waived(client):
    t = _text(client, GRIHA)
    assert "rates it avoid" in t and "does not waive panchak" in t
    assert "rates it excellent" not in t


def test_the_vivah_article_calls_abujha_a_regional_custom_and_lists_no_panchak_day_as_a_wedding_date(client):
    t = _text(client, VIVAH)
    assert "regional" in t and "does not waive any exclusion" in t
    for gone in ("tulsi vivah — thursday, nov 11, 2027", "basant panchami — thursday, feb 11, 2027",
                 "devuthani ekadashi — wednesday, nov 10, 2027 (kartika shukla ekadashi"):
        assert gone not in t
    assert "all five 2027 abujha dates" in t and "avoid" in t
