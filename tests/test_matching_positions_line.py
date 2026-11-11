"""#889: /matching prints every planet's degree and retrograde flag under each chart.

The diamond macro drops a planet's degree in a cell too small for it (a stellium:
slot mode 1) and its retrograde flag in a triangle holding 7+ grahas (mode 2).
`_diamond_labels.html` and `scripts/gen_diamond_label_slots.py` both said what was
dropped "remains in the positions table under the chart". That is true on /kundli
(`result.html` has the table) and false on /matching, which has no planet table at
all -- so a degree or an R dropped from a /matching chart was lost from the page.

Driven through the real POST /matching route and template with the chart computer
stubbed to put a stellium in each chart; the LLM is stubbed (#449). The partial is
also rendered on its own for the exact markup. Hermetic.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from astro_ai.chart import PLANET_SHORT

ROOT = Path(__file__).resolve().parents[1]
_PARAS = re.compile(r"<p [^>]*data-chart-positions>(.*?)</p>", re.S)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", fragment)).replace("&nbsp;", " ").replace("&deg;", "°") \
        .replace("&middot;", "·").strip()


def _stellium(chart, house: int, degrees: dict[str, int], retro: set[str]):
    """The real chart with the named grahas moved into one house at known degrees.
    Rashi and nakshatra are left alone, so the Guna Milan scores are unchanged."""
    nodes = ("Rahu", "Ketu")   # always retrograde, and left in their own houses
    planets = [dataclasses.replace(p, house=house, longitude=float(degrees[p.name]),
                                   retrograde=p.name in retro) if p.name in degrees
               else dataclasses.replace(p, retrograde=p.name in nodes)   # pin the real chart's own vakri
               for p in chart.planets]
    return dataclasses.replace(chart, planets=planets)


@pytest.fixture
def stellium_page(client, stub_llm, monkeypatch):
    import astro_ai.routes.matching as m
    real = m.compute_chart
    # Groom: seven grahas in house 3 -> slot mode 2 (degree AND R dropped from the diamond).
    g = {"Sun": 21, "Moon": 3, "Mars": 14, "Mercury": 7, "Jupiter": 28, "Venus": 11, "Saturn": 19}
    # Bride: five grahas in house 2 -> slot mode 1 (degree dropped, R kept).
    b = {"Sun": 5, "Moon": 26, "Mars": 17, "Mercury": 9, "Venus": 23}
    groom_retro, bride_retro = {"Mars", "Saturn"}, {"Mercury"}
    calls = {"n": 0}

    def fake(date, time, place):
        calls["n"] += 1
        chart = real(date, time, place)
        if calls["n"] % 2 == 1:
            return _stellium(chart, 3, g, groom_retro)
        return _stellium(chart, 2, b, bride_retro)

    monkeypatch.setattr(m, "compute_chart", fake)
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)

    def get(lang="en"):
        calls["n"] = 0
        r = client.post(f"/matching?lang={lang}", data={
            "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00", "g_birth_place": "Mumbai",
            "b_name": "B", "b_birth_date": "1990-01-10", "b_birth_time": "10:00", "b_birth_place": "Mumbai"})
        assert r.status_code == 200
        return r.text

    return get, g, b, groom_retro, bride_retro


def test_each_chart_lists_every_planet_with_its_degree_and_retrograde_flag(stellium_page):
    get, g, b, groom_retro, bride_retro = stellium_page
    html = get()
    lines = [_text(x) for x in _PARAS.findall(html)]
    assert len(lines) == 2, f"expected one positions line under each of the two charts, got {len(lines)}"
    for line, degrees, retro in ((lines[0], g, groom_retro), (lines[1], b, bride_retro)):
        for name, deg in degrees.items():
            mark = " R" if name in retro else ""
            assert f"{PLANET_SHORT[name]} {deg}°{mark}" in line, f"{name}: {line!r}"
        # A retrograde flag appears only where one belongs. Rahu and Ketu are always
        # retrograde (chart.py) and stay in their own houses, so they add two.
        assert line.count("° R") == len(retro) + 2, line


def test_the_degrees_the_diamond_dropped_are_only_on_the_page_in_the_positions_line(stellium_page):
    """The premise: the stellium really does lose its degrees from the SVG, so the
    line is the ONLY place they exist. Each `Su 21°` string must appear exactly once
    (the line) -- if the diamond ever printed it too this test says so, and if the
    line vanished it would be zero."""
    get, g, b, *_ = stellium_page
    html = get()
    for name, deg in {**{k: v for k, v in g.items() if k in ("Sun", "Jupiter")},
                      **{"Venus": b["Venus"]}}.items():
        needle = f"{PLANET_SHORT[name]}&nbsp;{deg}&deg;"
        in_svg = sum(s.count(needle) for s in re.findall(r"<svg.*?</svg>", html, re.S))
        assert in_svg == 0, f"{name} {deg}: the diamond printed it after all -- premise changed"
        assert html.count(needle) >= 1, f"{name} {deg}: not recoverable anywhere on the page"


def test_the_line_is_labelled_in_both_languages(stellium_page):
    get, *_ = stellium_page
    assert "Positions:</span>" in get("en")
    hi = get("hi")
    assert "ग्रह स्थिति:</span>" in hi
    # Abbreviations stay as the chart prints them -- no invented Hindi codes.
    assert "data-chart-positions" in hi and "Su&nbsp;21&deg;" in hi


def test_the_line_is_never_below_the_12px_floor():
    src = (ROOT / "src/astro_ai/templates/_chart_positions.html").read_text()
    m = re.search(r'<p class="([^"]*)" data-chart-positions>', src)
    assert m, "the positions line lost its marker"
    classes = m.group(1).split()
    assert "text-xs" in classes and not {"text-[10px]", "text-[11px]", "text-2xs"} & set(classes)
    assert "text-bhagya-muted" in classes, "the colour the caption above the chart already uses on white"


def test_an_ordinary_chart_renders_the_line_for_real_charts(client, stub_llm):
    """No stub on the chart computer: the real chart's own diamond data is what is listed."""
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    from astro_ai.chart import compute_chart
    r = client.post("/matching", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00", "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": "1990-01-10", "b_birth_time": "10:00", "b_birth_place": "Mumbai"})
    lines = [_text(x) for x in _PARAS.findall(r.text)]
    assert len(lines) == 2
    for line, date in zip(lines, ("1990-01-01", "1990-01-10")):
        ch = compute_chart(date, "10:00", "Mumbai")
        want = [f"{a} {d}°" + (" R" if rt else "") for cell in ch.diamond_chart() for a, d, rt in cell["planets"]]
        assert len(want) == 9
        assert line == "Positions: " + " · ".join(want), line


def test_the_false_sentence_about_the_positions_table_is_gone():
    """`_diamond_labels.html` and `gen_diamond_label_slots.py` said every dropped
    degree "remain[s] in the positions table under the chart". Only /kundli has one."""
    stale = ("remain in the positions table under the",
             "the positions table under\nthe chart still carries every degree")
    for p in [*(ROOT / "src").rglob("*.html"), *(ROOT / "src").rglob("*.py"),
              *(ROOT / "scripts").glob("*.py")]:
        text = p.read_text()
        for s in stale:
            assert s not in text, f"{p.relative_to(ROOT)} still carries the false sentence: {s!r}"
    tpl = (ROOT / "src/astro_ai/templates/_diamond_labels.html").read_text()
    gen = (ROOT / "scripts/gen_diamond_label_slots.py").read_text()
    for name, text in (("_diamond_labels.html", tpl), ("gen_diamond_label_slots.py", gen)):
        assert "/kundli" in text and "/matching" in text and "_chart_positions.html" in text, name


def test_every_page_that_calls_the_diamond_macro_can_recover_what_it_drops():
    """The claim in the header, as a check: a template that calls `diamond_labels`
    without abbr_only must carry a positions table (/kundli) or the line (/matching)."""
    for p in (ROOT / "src/astro_ai/templates").glob("*.html"):
        if p.name == "_diamond_labels.html":
            continue
        text = p.read_text()
        full = re.search(r"diamond_labels\((?![^)]*abbr_only)", text)
        if not full:
            continue
        assert "<table" in text or "chart_positions(" in text, (
            f"{p.name} prints the diamond labels but has no table or positions line for what they drop")
