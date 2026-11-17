"""#1139: nothing the site says ranks Abhijit as the best / most auspicious window.

knowledge/ sources only that Abhijit is the muhurta of midday (Rao, *Lessons*, Lesson 1 item 16,
quoted in the chart.py comment) and that daylight divides into 15 muhurtas (Raman, *Muhurtha*,
pp. 31-32). No line there ranks it, and #1025 removed the ranking from /muhurat. These tests pin
the same on every other surface: the i18n labels (EN and HI), the trivia card, the /panchang page,
the Panchang docstring, and the two prompt lines the readings are generated from.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from astro_ai import chart
from astro_ai.i18n import translate
from astro_ai.trivia import DID_YOU_KNOW

DELHI = ("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata")

# English ranking words, and the Hindi ones the old strings used (श्रेष्ठ, सर्वोत्तम, सबसे शुभ, अनुकूल).
_RANKING = re.compile(
    r"most auspicious|best|most favourable|favourable for|auspicious window|perfect for|good for signing"
    r"|to act in|श्रेष्ठ|सर्वोत्तम|उत्तम|सबसे शुभ|सबसे अनुकूल|के लिए अनुकूल",
    re.I,
)
_KEYS = ("abhijit_tag", "abhijit_desc", "strip_abhijit", "rashifal_window_facts")


@pytest.mark.parametrize("lang", ("en", "hi"))
@pytest.mark.parametrize("key", _KEYS)
def test_no_abhijit_label_ranks_the_window(lang, key):
    text = translate(lang, key)
    assert text and not _RANKING.search(text), f"{lang}.{key} ranks Abhijit: {text!r}"


def test_the_labels_say_midday_which_is_what_the_source_says():
    assert "midday" in translate("en", "abhijit_tag").lower()
    assert "midday" in translate("en", "strip_abhijit").lower()
    assert "मध्याह्न" in translate("hi", "abhijit_tag")
    assert "मध्याह्न" in translate("hi", "strip_abhijit")


def test_the_trivia_card_does_not_rank_abhijit():
    cards = [c for c in DID_YOU_KNOW if "Abhijit" in c["en"] or "अभिजित" in c["hi"]]
    assert cards, "the Abhijit trivia card is gone; update this test, do not delete it"
    for c in cards:
        assert not _RANKING.search(c["en"]), c["en"]
        assert not _RANKING.search(c["hi"]), c["hi"]


def _panchang(monkeypatch):
    name, lat, lon, tz = DELHI
    monkeypatch.setattr(chart, "geocode_place", lambda place: (lat, lon, tz))
    natal = chart.compute_chart("2000-01-01", "12:00", name)
    return chart.compute_panchang(natal, when=datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo(tz)))


def test_the_prompt_lines_do_not_call_abhijit_auspicious(monkeypatch):
    p = _panchang(monkeypatch)
    line = next(l for l in chart.format_panchang_for_prompt(p).splitlines() if "Abhijit" in l)
    assert "auspicious" not in line and "favourable" not in line, line
    assert "midday" in line
    for lang in ("en", "hi"):
        block = chart.format_day_windows_for_rashifal(p, lang)
        assert not _RANKING.search(block.split("\n")[0]), block


def test_the_panchang_page_labels_abhijit_midday_and_does_not_rank_it(client, monkeypatch):
    name, lat, lon, tz = DELHI
    monkeypatch.setattr(chart, "geocode_place", lambda place: (lat, lon, tz))
    resp = client.get("/panchang/2026-11-05", params={"city": name})
    assert resp.status_code == 200
    html = resp.text
    assert "Abhijit Muhurat (midday)" in html
    for phrase in ("Abhijit Muhurat (best)", "Most auspicious ~48 min", "most universally auspicious",
                   "Perfect for signing"):
        assert phrase not in html, phrase


_TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates"


def test_the_daily_email_row_does_not_tag_abhijit_auspicious():
    """QA on #1139: email/daily_rashifal.html tagged the Abhijit row '(auspicious)' / '(शुभ)'."""
    src = (_TEMPLATES / "email" / "daily_rashifal.html").read_text()
    start = src.index("Abhijit Muhurta{% endif %}</strong>")
    row = src[start:start + 600].split("</tr>")[0]
    assert "auspicious" not in row and "शुभ" not in row, row
    assert "midday" in row and "मध्याह्न" in row


def test_the_homepage_today_card_does_not_say_to_act_in_abhijit():
    """QA on #1139: index.html's /today card said 'Abhijit Muhurta to act in'."""
    src = (_TEMPLATES / "index.html").read_text()
    line = next(l for l in src.splitlines() if "Abhijit Muhurta" in l and "Rahu Kaal window to avoid" in l)
    assert not _RANKING.search(line), line
    assert "midday Abhijit Muhurta" in line


def test_the_panchang_docstring_does_not_claim_a_ranking():
    doc = chart.DailyPanchang.__doc__
    assert "Abhijit Muhurta is the most" not in re.sub(r"\s+", " ", doc)
