"""/kundli advertises nakshatra padas, so the result page must show them (#209).

The landing's meta description, JSON-LD `tool_desc` and body copy all say
"planetary positions in nakshatra padas". `PlanetPosition.pada` has been
computed since 9d5f3a1, but `result.html`'s planet table printed only
`{{ p.nakshatra }}` — a promise to a searcher the result never kept.

Hermetic: the chart is really computed (geocoding stubbed by conftest), no LLM.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai.routes import kundli as K

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "templates"
_NATAL = "## Personality\n" + "The chart favours patient, deliberate work this season. " * 10 + "\n"
_PADA_SPAN = re.compile(r"<span data-pada>([^<]*)</span>")


@pytest.fixture
def result_pages(client, saved_chart, stub_llm, monkeypatch):
    """Both languages' pages, plus the padas of the chart each route rendered.

    The expectation is captured from the route's OWN `compute_chart` call and
    not recomputed in the test body: swisseph's sidereal mode is per-thread
    (#762), so a chart computed on the test's thread differs from the one the
    TestClient's portal thread rendered (Jupiter pada 2 against 1) and the
    comparison would test the thread, not the template.
    """
    stub_llm(_NATAL)
    saved_chart()
    seen: list[list[int]] = []
    real = K.compute_chart

    def spy(*a, **k):
        chart = real(*a, **k)
        seen.append([p.pada for p in chart.planets])
        return chart

    monkeypatch.setattr(K, "compute_chart", spy)
    pages = {"en": client.get("/kundli").text, "hi": client.get("/kundli?lang=hi").text}
    return pages, seen


def test_landing_still_advertises_padas():
    # If the claim is ever dropped this test should be deleted with it, not
    # left asserting a promise nobody makes; until then it is the coupling.
    html = (TEMPLATES / "kundli_landing.html").read_text(encoding="utf-8")
    assert "pada" in html.lower()
    assert "27-nakshatra granularity" not in html  # padas are 108-fold, not 27


@pytest.mark.parametrize("lang,word", [("en", "Pada"), ("hi", "पाद")])
def test_result_planet_table_shows_each_planets_pada(result_pages, lang, word):
    pages, seen = result_pages
    assert len(seen) == 2, seen  # one chart per language render
    expected = seen[0] if lang == "en" else seen[1]
    assert len(expected) == 9 and all(1 <= n <= 4 for n in expected)
    shown = _PADA_SPAN.findall(pages[lang])
    assert shown == [f"{word} {n}" for n in expected], (shown, expected)
