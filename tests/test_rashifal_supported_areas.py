"""Option 1 for the area counts (owner, 2026-11-09).

"Work 1/4 · Money 1/3 · Relationships 1/3 · Health 0/4" read as marks out of
four -- "quite disheartening" -- beside "Chandra Bala strong". The page, the
flip card and the email now NAME the areas with at least one well-placed
karaka; the exact counts survive only in the explanatory note.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from astro_ai.routes.deps import templates

T = pathlib.Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates"
MIXED = [{"area": "Work", "favourable": 1, "total": 4}, {"area": "Money", "favourable": 1, "total": 3},
         {"area": "Relationships", "favourable": 0, "total": 3}, {"area": "Health", "favourable": 0, "total": 4}]
NONE = [dict(a, favourable=0) for a in MIXED]


def _card(areas, lang="en"):
    return templates.env.get_template("_rashifal_card_content.html").render(
        lang=lang, glyph="♈", reading_body="A plain reading.", day_detail={"areas": areas},
        chandra_bala=None, panchang_strip=None, rashi_slug="aries", rashi_name="Aries",
        rashi_sanskrit="Mesha", date_pretty="", read_more_url="/rashifal/aries")


def test_the_card_names_only_the_supported_areas():
    html = _card(MIXED)
    assert "Supported today: Work, Money" in html
    assert "Health" not in html and "0/4" not in html and "1/4" not in html


def test_a_day_with_no_support_says_so_without_a_zero():
    html = _card(NONE)
    assert "No area has extra support from the planets today" in html
    assert "0/" not in html


def test_the_hindi_card_uses_hindi_names():
    html = _card(MIXED, "hi")
    assert "आज साथ देने वाले क्षेत्र: कार्य, धन" in html


@pytest.mark.parametrize("name", ["email/daily_rashifal.html", "rashifal_single.html"])
def test_page_and_email_lead_with_the_supported_list_and_keep_counts_in_the_note(name):
    src = (T / name).read_text()
    assert "Supported today: " in src
    # Every remaining fraction sits on the same line as the note that explains it.
    for line in src.splitlines():
        if "{{ a.favourable }}/{{ a.total }}" in line:
            assert "Not a score" in line, line.strip()[:120]
