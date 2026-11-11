"""#380: the North Indian diamond's labels are legible on a phone AND still fit.

The chart is `viewBox="0 0 400 400"`, so a label's rendered size is
`font-size x box/400`. Measured 2026-11-10 in headless Chromium at a 375px
viewport: the /kundli box is 301px (scale 0.7525) and a /matching mini chart is
259px (scale 0.6475). At the old size 11 that was 8.3px and 6.5px.

Raising the size alone put a stellium outside its triangle, so these tests render
the shared `_diamond_labels.html` macro for EVERY house holding 1..8 planets and
check, from the emitted `<text>` elements themselves (not from the generator's
intent):

  * no two label boxes overlap, and none overlaps its house number;
  * every box lies inside its own cell, clear of the cell lines;
  * the stack pitch is at least 1.1 x the font size (it was 13 at size 11);
  * the rendered size clears 10px at both measured box widths.

Widths are estimated (Manrope is a webfont, not installed in CI); the estimate is
wider than the face. Hermetic: no network, no LLM, no route.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("gen_slots", ROOT / "scripts" / "gen_diamond_label_slots.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["gen_slots"] = gen
_spec.loader.exec_module(gen)

from astro_ai.chart import PLANET_SHORT  # noqa: E402
from astro_ai.main import templates  # noqa: E402

KUNDLI_BOX_PX = 301.0     # measured at 375px viewport (#380)
MATCHING_BOX_PX = 259.0   # measured at 375px viewport (#380)
GRAHAS = list(PLANET_SHORT.values())

_TEXT = re.compile(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-size="(\d+)"[^>]*>(.*?)</text>', re.S)


class _Ch:
    def __init__(self, counts: dict[int, int], retro: bool = True):
        self.counts, self.retro = counts, retro

    def diamond_chart(self):
        out = []
        for h in range(1, 13):
            n = self.counts.get(h, 0)
            # Worst-case label: two-digit degree, retrograde.
            planets = [(GRAHAS[i % 9], 29, self.retro) for i in range(n)]
            out.append({"house": h, "sign_num": 12, "sign_short": "Pi", "planets": planets})
        return out


def _render(counts, abbr_only=False, retro=True):
    src = ('{% from "_diamond_labels.html" import diamond_labels %}'
           "{{ diamond_labels(ch, '#111', '#222', '#333', abbr_only=abbr_only) }}")
    return templates.env.from_string(src).render(ch=_Ch(counts, retro), abbr_only=abbr_only)


def _boxes(svg: str):
    """[(x, y, font_size, kind, box)] for every <text>; kind is 'num' or 'planet'."""
    out = []
    for x, y, fs, body in _TEXT.findall(svg):
        x, y, fs = float(x), float(y), float(fs)
        plain = re.sub(r"<tspan.*?</tspan>", "", body)
        txt = plain.replace("&nbsp;", " ").replace("&deg;", "°")
        if fs == gen.NUM_FS:
            w, kind = gen.NUM_W, "num"
        else:
            w = len(txt.strip().split(" ")[0]) * gen._W["letter"] * gen.FS
            if "°" in txt:
                w += gen._W["space"] * gen.FS + 2 * gen._W["digit"] * gen.FS + gen._W["deg"] * gen.FS
            if "<tspan" in body:
                w += gen._W["space"] * gen.FS + gen._W["R"] * gen.R_FS
            w *= gen.SAFETY
            kind = "planet"
        out.append((x, y, fs, kind, gen.box(x, y, w, fs)))
    return out


def _house_of(x, y):
    """The cell whose polygon contains the label's anchor point."""
    for h, poly in gen.CELLS.items():
        if gen.inside(poly, x, y - 4, 0.0):
            return h
    raise AssertionError(f"label anchor ({x}, {y}) is in no cell")


@pytest.mark.parametrize("house", range(1, 13))
@pytest.mark.parametrize("n", range(1, gen.MAX_N + 1))
def test_a_stellium_fits_its_cell_without_overlap(house, n):
    items = _boxes(_render({house: n}))
    planets = [i for i in items if i[3] == "planet"]
    assert len(planets) == n
    poly = gen.CELLS[house]
    for x, y, fs, _, bx in planets:
        assert fs >= 16, f"planet label is {fs}, below the 16-unit floor"
        assert gen.box_inside(poly, bx), f"house {house} n={n}: label at ({x},{y}) leaves its cell"
    for a in range(len(planets)):
        for b in range(a + 1, len(planets)):
            assert not gen.overlap(planets[a][4], planets[b][4]), (
                f"house {house} n={n}: labels {a} and {b} overlap")
    num = [i for i in items if i[3] == "num" and gen.box_inside(poly, i[4], 0.0)]
    assert num, f"house {house}: its number is not inside it"
    for p in planets:
        assert not gen.overlap(p[4], num[0][4]), f"house {house} n={n}: a label covers the house number"


def test_every_house_number_sits_inside_its_own_cell_and_clear_of_the_lines():
    items = _boxes(_render({}))
    nums = [i for i in items if i[3] == "num"]
    assert len(nums) == 12
    for (x, y, fs, _, bx), (h, poly) in zip(nums, sorted(gen.CELLS.items())):
        assert fs >= 15
        assert gen.box_inside(poly, bx), f"house {h}: number leaves its cell"


@pytest.mark.parametrize("house", range(1, 13))
def test_the_stack_pitch_is_scaled_with_the_text(house):
    """A pitch under 1.1 x the font is what 13 was at size 11 -- fine there, a
    collision at 16."""
    planets = [i for i in _boxes(_render({house: 4})) if i[3] == "planet"]
    ys = sorted({round(i[1], 1) for i in planets})
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    assert all(g >= 1.1 * gen.FS - 0.2 for g in gaps), f"house {house}: row pitch {gaps}"


def test_rendered_size_clears_ten_px_at_375():
    """The issue's metric: min planet-label size >= 10px at a 375px viewport."""
    for name, box in (("/kundli Lagna", KUNDLI_BOX_PX), ("/matching mini", MATCHING_BOX_PX)):
        planets = [i for i in _boxes(_render({1: 2, 2: 2})) if i[3] == "planet"]
        smallest = min(i[2] for i in planets) * box / 400
        assert smallest >= 10.0, f"{name}: smallest planet label renders at {smallest:.2f}px"


def test_the_full_label_is_kept_where_it_fits():
    """The degree is only dropped for a cell too small for it."""
    assert "&deg;" in _render({1: 1}), "a lone planet in the largest cell lost its degree"
    assert "&deg;" in _render({7: 4}), "four planets in a diamond lost their degrees"
    assert "&deg;" not in _render({3: 5}), "five planets in a side triangle cannot all carry a degree"


def test_retrograde_is_kept_until_the_last_resort_mode():
    assert ">&nbsp;R</tspan>" in _render({1: 3})
    assert "R</tspan>" in _render({2: 5}), "compact mode must keep the retrograde mark"
    assert "R</tspan>" not in _render({2: 8}), "8 in a top triangle only fits as abbreviations"


def test_divisional_charts_print_only_the_abbreviation():
    out = _render({7: 3, 2: 4}, abbr_only=True)
    assert "&deg;" not in out and "<tspan" not in out


def test_the_templates_use_the_shared_macro_not_their_own_loops():
    """The old per-template copies, which carried `font-size="11"` and a pitch of
    13. A diff that reverts one is exactly this."""
    tpl = ROOT / "src" / "astro_ai" / "templates"
    for name in ("result.html", "matching_result.html"):
        src = (tpl / name).read_text()
        assert "diamond_labels(" in src, f"{name} no longer calls the shared macro"
        assert "loop.index0 * 13" not in src, f"{name}: the 13-unit stack pitch is back"
        assert 'font-size="11" font-weight="700"' not in src, f"{name}: the old 11-unit house number is back"
        assert "c.planet_cy" not in src, f"{name}: reads the old planet_cy again"
