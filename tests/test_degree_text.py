"""#896: a one-decimal degree within a sign is 0.0..29.9, never 30.0.

`"%.1f"|format(longitude)` rounded 29.95..29.999 up to "30.0" in the positions
table, the lagna tile, /today and the LLM prompt prose. `degree_text` truncates,
matching the whole-degree chart label (#893). Hermetic: no ephemeris, no network.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from astro_ai.chart import RASHIS, Chart, PlanetPosition, degree_text, format_for_prompt  # noqa: E402


@pytest.mark.parametrize(
    "lon,expected",
    [
        (0.0, "0.0"), (0.04, "0.0"), (14.3, "14.3"), (14.299999999999999, "14.3"),
        (29.94, "29.9"), (29.95, "29.9"), (29.999, "29.9"), (30.0, "29.9"), (-0.01, "0.0"),
    ],
)
def test_degree_text_truncates_and_never_reaches_30(lon, expected):
    assert degree_text(lon) == expected


def test_degree_text_agrees_with_whole_degree_label():
    from astro_ai.chart import _degree_label

    for i in range(0, 3000):
        lon = i / 100
        assert int(degree_text(lon).split(".")[0]) == _degree_label(lon)


def test_prompt_and_templates_use_it():
    p = PlanetPosition(
        name="Mars", rashi=RASHIS[0], house=1, longitude=29.999,
        nakshatra="Ashwini", retrograde=False, pada=1,
    )
    ch = Chart(
        lagna_rashi=RASHIS[0], lagna_longitude=29.97, planets=[p], birth_lat=0.0,
        birth_lon=0.0, birth_tz="UTC", birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    text = format_for_prompt(ch)
    assert "30.0deg" not in text
    assert "at 29.9deg" in text

    from astro_ai.routes.deps import templates

    assert templates.env.filters["degree_text"](29.999) == "29.9"
    root = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates"
    for name in ("result.html", "today.html"):
        assert '"%.1f"|format(p.longitude)' not in (root / name).read_text(), name
    assert '"%.1f"|format(chart.lagna_longitude)' not in (root / "result.html").read_text()
