"""#893: a chart label for a planet's degree within its sign is 0..29, never 30.

`int(round(longitude))` printed 29.5..29.99 as `30`. Both renderers
(`diamond_chart` / `house_summary` and `south_indian_chart`) must truncate.
Hermetic: builds a Chart by hand, no ephemeris, no network.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from astro_ai.chart import RASHIS, Chart, PlanetPosition, _degree_label  # noqa: E402


def _chart(longitude: float) -> Chart:
    p = PlanetPosition(
        name="Mars", rashi=RASHIS[0], house=1, longitude=longitude,
        nakshatra="Ashwini", retrograde=False, pada=1,
    )
    return Chart(
        lagna_rashi=RASHIS[0], lagna_longitude=5.0, planets=[p], birth_lat=0.0,
        birth_lon=0.0, birth_tz="UTC", birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "lon,expected",
    [(0.0, 0), (0.99, 0), (14.5, 14), (29.0, 29), (29.49, 29), (29.5, 29), (29.7, 29), (29.99, 29), (30.0, 29)],
)
def test_degree_label_truncates_and_never_reaches_30(lon, expected):
    assert _degree_label(lon) == expected


@pytest.mark.parametrize("lon", [29.49, 29.5, 29.7, 29.99])
def test_diamond_and_south_charts_print_29_not_30(lon):
    ch = _chart(lon)
    diamond = [pl for cell in ch.diamond_chart() for pl in cell["planets"]]
    south = [pl for cell in ch.south_indian_chart() for pl in cell["planets"]]
    assert diamond == [("Ma", 29, False)]
    assert south == [("Ma", 29, False)]
