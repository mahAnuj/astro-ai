"""#1322 (slice 2 of #1017): the finder's headline counts only the dates it calls
auspicious, and the results name the timezone and the sunrise the clock times are
local to.

R2 honest count: `caution` is the lowest tier that passed no hard exclusion. It stays
visible, in its own "Use with caution" group, and is not counted in "N auspicious dates".
R5 location and time: "Times are local to <city> (<IANA zone>). Sunrise on the first
listed date, <date>: HH:MM." -- and on a date with no ordinary sunrise (#228) it says
so instead of printing a time.

Not changed, and pinned by tests/test_analytics_tool_completion_events.py: the
`muhurat_searched.valid_count` and `notify` good_count keep counting every non-avoid
date, so the #1218 baseline keeps its meaning.

No network (geocoding is stubbed per test) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1322_honest_count.py.
"""
from __future__ import annotations

import dataclasses
import re
from datetime import date

import pytest

AUSPICIOUS = ("excellent", "good", "acceptable")
DELHI = (28.61, 77.21, "Asia/Kolkata")
LONDON = (51.5072, -0.1276, "Europe/London")
REYKJAVIK = (64.1466, -21.9426, "Atlantic/Reykjavik")
START = date(2026, 11, 14)


def _stub(monkeypatch, **places):
    """Resolve each named city to its (lat, lon, tz) and nothing else."""
    from astro_ai import chart

    monkeypatch.setattr(chart, "geocode_place", lambda place: places[place])


def _post(client, city, event="griha_pravesh", start=START, days=60):
    return client.post("/muhurat", data={
        "event_type": event, "city": city, "start_date": start.isoformat(), "days": str(days)})


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _tables(html: str) -> list[str]:
    return re.findall(r"<table.*?</table>", html, flags=re.S)


def test_headline_counts_only_excellent_good_acceptable(client, monkeypatch):
    from astro_ai import muhurat

    _stub(monkeypatch, **{"Delhi, India": DELHI})
    rows = muhurat.find_candidates("griha_pravesh", "Delhi, India", START, 60)
    non_avoid = [c for c in rows if c.rating != "avoid"]
    cautions = [c for c in rows if c.rating == "caution"]
    auspicious = [c for c in rows if c.rating in AUSPICIOUS]
    # 10 non-avoid and 1 caution at 3bbfffc. It was 11 and 2 when #1017 was written; #1232
    # (Magha/Mula first pada) moved one date. #1504 (Dwadashi now avoided for house entry) moved
    # another: 2026-12-05, a Krishna Dwadashi, was "good" and is "avoid", leaving 9 and 1. A
    # legitimate rule change updates THESE numbers -- it does not loosen the assertions below.
    assert (len(non_avoid), len(cautions), len(auspicious)) == (9, 1, 8)

    r = _post(client, "Delhi, India")
    assert r.status_code == 200
    text = _text(r.text)
    assert f"{len(auspicious)} auspicious dates" in text and "8 auspicious dates" in text
    assert "9 auspicious dates" not in text
    assert f"{len(cautions)} use with caution" in text
    assert "Use with caution" in r.text

    tables = _tables(r.text)
    caution_date = cautions[0].d.strftime("%b %d, %Y")
    assert caution_date not in tables[0], "a caution date sits in the auspicious table"
    assert caution_date in tables[1], "the caution date is not in its own group"
    for c in auspicious:
        assert c.d.strftime("%b %d, %Y") in tables[0]
    # the label sits between the two tables, not before the first
    assert r.text.index("Use with caution") > r.text.index(tables[0])


def test_one_auspicious_date_reads_singular(client, monkeypatch):
    from astro_ai import muhurat

    _stub(monkeypatch, **{"Delhi, India": DELHI})
    rows = muhurat.find_candidates("griha_pravesh", "Delhi, India", START, 60)
    one = [next(c for c in rows if c.rating in AUSPICIOUS)]
    monkeypatch.setattr(muhurat, "find_candidates", lambda *a, **k: one)
    text = _text(_post(client, "Delhi, India").text)
    assert "1 auspicious date " in text and "1 auspicious dates" not in text


def test_a_caution_only_search_is_not_called_auspicious(client, monkeypatch):
    from astro_ai import muhurat

    _stub(monkeypatch, **{"London, UK": LONDON})
    real = muhurat.find_candidates("griha_pravesh", "London, UK", START, 60)
    cautions = [c for c in real if c.rating == "caution"][:2]
    assert len(cautions) == 2, "premise: the fixture needs two real caution rows"
    monkeypatch.setattr(muhurat, "find_candidates", lambda *a, **k: cautions)

    r = _post(client, "London, UK")
    assert r.status_code == 200
    text = _text(r.text)
    assert "No auspicious dates found" in text
    assert not re.search(r"\d+ auspicious dates?\b(?! found in)", text)
    assert "0 auspicious dates" in text  # the headline still says zero rather than hiding
    assert "Use with caution" in r.text and "2 use with caution" in text
    tables = _tables(r.text)
    assert len(tables) >= 1
    for c in cautions:
        assert c.d.strftime("%b %d, %Y") in tables[0]
    # the personal-notes / sunrise anchor still has a row to read: the first listed one
    assert "Times are local to London, UK (Europe/London)" in text


def test_delhi_and_london_name_their_own_zone_and_sunrise(client, monkeypatch):
    from astro_ai import muhurat

    _stub(monkeypatch, **{"Delhi, India": DELHI, "London, UK": LONDON})
    seen = {}
    for city, zone in (("Delhi, India", "Asia/Kolkata"), ("London, UK", "Europe/London")):
        first = next(c for c in muhurat.find_candidates("griha_pravesh", city, START, 60)
                     if c.rating != "avoid")
        assert re.fullmatch(r"\d\d:\d\d", first.sunrise), first.sunrise
        text = _text(_post(client, city).text)
        assert f"Times are local to {city} ({zone})." in text
        assert (f"Sunrise on the first listed date, {first.d.strftime('%b %d, %Y')}: "
                f"{first.sunrise}.") in text
        seen[city] = (first.d, first.sunrise)
    assert seen["Delhi, India"][1] != seen["London, UK"][1]


def test_polar_date_says_no_sunrise_instead_of_printing_one(client, monkeypatch):
    # Reykjavik 2026-06-24 is the date tests/test_polar_daylight_surfaces.py pins as
    # having no ordinary sunrise-to-sunset span (#228).
    from astro_ai import muhurat

    _stub(monkeypatch, **{"Reykjavik": REYKJAVIK, "Mumbai": (19.0760, 72.8777, "Asia/Kolkata")})
    day = date(2026, 6, 24)
    polar = muhurat.find_candidates("business", "Reykjavik", day, 1)
    assert polar and polar[0].rating != "avoid", "premise: the date must be a listed row"
    assert polar[0].sunrise == ""
    html = _post(client, "Reykjavik", event="business", start=day, days=1).text
    text = _text(html)
    assert "(Atlantic/Reykjavik)" in text
    assert "no ordinary sunrise on this date at this latitude" in text
    assert "Sunrise on" not in text

    # control: the same date at an ordinary latitude does print one
    ordinary = muhurat.find_candidates("business", "Mumbai", day, 1)
    assert ordinary and ordinary[0].sunrise
    assert f"Sunrise on the first listed date, {day.strftime('%b %d, %Y')}: {ordinary[0].sunrise}." in _text(
        _post(client, "Mumbai", event="business", start=day, days=1).text)


def test_the_zone_line_is_absent_when_no_zone_was_resolved(monkeypatch):
    # The route passes search_tz=""; tests that render the template directly pass nothing.
    from astro_ai import muhurat
    from astro_ai.routes.deps import templates
    from starlette.requests import Request

    _stub(monkeypatch, **{"Delhi, India": DELHI})
    cands = muhurat.find_candidates("griha_pravesh", "Delhi, India", START, 20)
    for extra in ({}, {"search_tz": ""}):
        html = templates.env.get_template("muhurat_finder.html").render(
            lang="en", candidates=cands, event_label="Griha Pravesh", city="Delhi, India",
            start_date=START.isoformat(), personal_active=False, couple_active=False,
            request=Request({"type": "http", "method": "GET", "path": "/muhurat",
                             "raw_path": b"/muhurat", "root_path": "", "headers": [],
                             "query_string": b"", "scheme": "http",
                             "server": ("testserver", 80), "client": ("test", 1234),
                             "app": None}), **extra)
        assert "Times are local to" not in html and "Sunrise on" not in html
        assert 'data-label="Windows"' in html
