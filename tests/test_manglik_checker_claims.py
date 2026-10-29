"""The Manglik checker does not claim to apply "every" / "all" classical cancellation rules (#398 slice 11).

`vedic_reference.md` 1.3 lists 19 cancellation rules; `chart.py`
`_manglik_cancellations` implements a subset (it has no strong-Moon aspect, no
Mars-Mercury, no lagna-specific own-sign rule, no retrograde rule, no enemy-sign
rule), and 1.3 itself says no source we hold counts the rules. Yet the checker's
own lead and meta description, the result page, /kundli, /matching, /about and two
remedies pages said the checker applies "every" / "all" / "the FULL" classical
evaluation. The claim is now the one that is true: it checks the rules it
implements and shows which ones applied.

Pinned through the real routes, because the claim lives in templates and route
strings that nothing else reads. It is a phrase list, so it catches the phrases it
names and not every possible rewording; the second test is what stops that being
the only protection, by pinning that the rules the lead NAMES are ones the code
implements.
"""
from __future__ import annotations

import re

import pytest

_BIRTH = {
    "name": "Claims Fixture",
    "birth_date": "1957-09-07",
    "birth_time": "01:05",
    "birth_place": "Mumbai",
}

# Each is a claim of completeness the checker cannot make. Matched on text with
# tags, entities and whitespace normalised, case-insensitively.
_OVERCLAIMS = (
    "every classical cancellation",
    "all classical cancellation",
    "all the classical cancellation",
    "full classical evaluation",
    "applies them all",
    "applies every",
    "libra debility",
    "explicitly applies the classical cancellation",
)

_PAGES = ("/manglik-check", "/kundli", "/matching", "/about",
          "/learn/manglik-remedies/", "/learn/mars-remedies/")


def _text(html: str) -> str:
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&mdash;", "—").replace("&rsquo;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", html).lower()


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    return TestClient(app)


@pytest.mark.parametrize("path", _PAGES)
def test_no_page_claims_the_checker_applies_every_cancellation_rule(client, path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    text = _text(r.text)
    hits = [p for p in _OVERCLAIMS if p in text]
    assert not hits, f"{path} claims completeness the checker cannot make: {hits}"


def test_the_result_page_makes_no_such_claim_either(client):
    r = client.post("/manglik-check", data=_BIRTH)
    assert r.status_code == 200, r.status_code
    text = _text(r.text)
    hits = [p for p in _OVERCLAIMS if p in text]
    assert not hits, hits


def test_the_checker_lead_and_meta_name_only_rules_the_code_implements(client):
    """The replacement claim is a list; a list is only honest if each item is real."""
    from pathlib import Path

    from astro_ai.routes.dosha import _MANGLIK_CHECK_LEAD, _MANGLIK_CHECK_META

    page = client.get("/manglik-check").text
    assert _MANGLIK_CHECK_LEAD.replace("'", "&#39;") in page or _MANGLIK_CHECK_LEAD in page
    assert _MANGLIK_CHECK_META.replace("'", "&#39;") in page or _MANGLIK_CHECK_META in page
    # The meta stays inside a search snippet.
    assert len(_MANGLIK_CHECK_META) <= 160, len(_MANGLIK_CHECK_META)

    # Every rule the lead names must exist as a slug in _manglik_cancellations.
    src = (Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "chart.py").read_text()
    for named, slugs in (
        ("Jupiter's influence", ("mars_jupiter_conjunct", "jupiter_aspects_mars")),
        ("own-sign or exalted Mars", ("mars_own_sign", "mars_exalted")),
        ("a Cancer or Leo ascendant", ("cancer_lagna_yogakaraka", "leo_lagna_yogakaraka")),
    ):
        assert named in _MANGLIK_CHECK_LEAD, named
        for slug in slugs:
            assert f'slug="{slug}"' in src, (named, slug)
