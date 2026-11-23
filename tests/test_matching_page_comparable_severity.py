"""#1376 (a): /matching stops listing "comparable severity" among the cancellations as if classical.

The antidote list we work from (see the manglik-remedies page) says that when both partners
are Manglik the dosha is cancelled and names no severity condition. The "comparable severity"
band is Bhagya's own threshold, so the /matching Manglik paragraph must say so rather than
list it beside the classical cancellations."""
from __future__ import annotations

import html
import re


def _paragraph(client) -> str:
    r = client.get("/matching")
    assert r.status_code == 200
    block = re.search(r"Manglik matching.*?</h3>(.*?)<h3", r.text, re.S)
    assert block, "Manglik matching section not found on /matching"
    text = re.sub(r"<[^>]+>", " ", block.group(1))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def test_matching_page_does_not_list_comparable_severity_among_implemented_cancellations(client):
    p = _paragraph(client)
    assert "cancellations it implements" in p, p
    listed = p.split("cancellations it implements", 1)[1].split("Read the full", 1)[0]
    # The list ends at "and a few others"; the sentences after it may discuss the band.
    listed = listed.split("and a few others", 1)[0]
    assert "comparab" not in listed, listed


def test_matching_page_names_the_comparable_band_as_bhagyas_own(client):
    p = _paragraph(client)
    sentences = [s for s in re.split(r"[.;]\s", p) if "comparab" in s]
    assert sentences, f"no mention of the comparable band: {p!r}"
    for s in sentences:
        assert "Bhagya's own" in s, s


def test_matching_page_says_the_antidote_list_names_no_severity_condition(client):
    assert "names no severity condition" in _paragraph(client)
