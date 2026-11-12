"""#889: the South Indian chart's planet stack stays inside its cell, clear of LAGNA.

Found 2026-11-11 by reading the partial against its own numbers. A cell is 100
viewBox units tall; the stack started at `cy + 42` with a pitch of 13 and the
`LAGNA` caption sat at `cy + 92`, in the stack's path:

  * from the 5th planet in the lagna cell the caption collided with a planet label;
  * from the 6th the stack ran past `cy + 100`, out of the cell and across the line.

Neither is a rare chart (a stellium of 5+ in a sign is common enough to be a
reading headline), and the partial is only ever exercised with 1-3 planets by eye.
So this renders `_south_indian_chart.html` for 1..8 planets in the lagna cell and in
a non-lagna cell, with and without a retrograde flag, and checks from the emitted
`<text>` elements themselves: every box lies inside its cell, and no two boxes in a
cell overlap (house number, rashi, LAGNA and every planet label).

Widths are estimated from the same per-glyph numbers `gen_diamond_label_slots.py`
uses for the diamond (wider than Manrope) plus its 6% pad. Hermetic: no network,
no LLM, no route.
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

GRAHAS = list(PLANET_SHORT.values())
PLANET_FS = 11.0    # a planet label; the rashi abbreviation is 10, LAGNA 9
MARGIN = 3.0        # 1 (half the 2-wide line) + 2 clearance, as the diamond test
SIZE = 100.0
_W = gen._W
_TEXT = re.compile(r'<text x="([\d.]+)" y="([\d.]+)" text-anchor="(\w+)"[^>]*?font-size="(\d+)"[^>]*>(.*?)</text>', re.S)

# (col, row, rashi_num): the 12 border cells exactly as chart.py lays them out.
_CELLS = [(0, 0, 12), (1, 0, 1), (2, 0, 2), (3, 0, 3), (3, 1, 4), (3, 2, 5),
          (3, 3, 6), (2, 3, 7), (1, 3, 8), (0, 3, 9), (0, 2, 10), (0, 1, 11)]
_SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]


class _Ch:
    """A chart with `n` planets in ONE cell (index `where` in _CELLS)."""

    def __init__(self, where: int, n: int, retro: bool, lagna: int):
        self.where, self.n, self.retro, self.lagna = where, n, retro, lagna

    def south_indian_chart(self):
        out = []
        for i, (col, row, rashi) in enumerate(_CELLS):
            planets = [(GRAHAS[k % 9], 29, self.retro) for k in range(self.n)] if i == self.where else []
            out.append({"col": col, "row": row, "rashi_num": rashi, "rashi_short": _SHORT[rashi - 1],
                        "house": ((rashi - _CELLS[self.lagna][2]) % 12) + 1,
                        "is_lagna": i == self.lagna, "planets": planets})
        return out


def _render(where, n, retro, lagna):
    return templates.env.get_template("_south_indian_chart.html").render(
        ch=_Ch(where, n, retro, lagna), aria="chart")


def _width(fs: float, body: str, bold: bool) -> float:
    """Estimated advance of one <text>, viewBox units."""
    plain = re.sub(r"<tspan.*?</tspan>", "", body, flags=re.S).replace("&nbsp;", " ").replace("&deg;", "°")
    w = 0.0
    for ch in plain:
        w += fs * (_W["space"] if ch == " " else _W["deg"] if ch == "°"
                   else _W["digit"] if ch.isdigit() else (0.76 if bold else _W["letter"]))
    for m in re.finditer(r'<tspan font-size="(\d+)"[^>]*>(.*?)</tspan>', body, re.S):
        tfs = float(m.group(1))
        w += tfs * _W["space"] + tfs * _W["R"]
    return w * gen.SAFETY


def _boxes(svg: str):
    out = []
    for x, y, anchor, fs, body in _TEXT.findall(svg):
        x, y, fs = float(x), float(y), float(fs)
        w = _width(fs, body, bold=fs != PLANET_FS)  # header text is 700/600 caps; planets are 600
        x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        label = re.sub(r"<[^>]*>", "", body).replace("&nbsp;", " ").replace("&deg;", "°").strip()
        out.append((label, fs, (x0, y - gen.ASC * fs, x0 + w, y + gen.DESC * fs)))
    return out


def _is_planet(label: str, fs: float) -> bool:
    """A rashi abbreviation can start with a graha code ("Sag" -> "Sa"), so size too."""
    return fs == PLANET_FS and label[:2] in GRAHAS


def _cell_of(bx):
    cx = (bx[0] + bx[2]) / 2
    cy = (bx[1] + bx[3]) / 2
    return int(cx // SIZE), int(cy // SIZE)


@pytest.mark.parametrize("retro", [True, False])
@pytest.mark.parametrize("where,lagna,kind", [(0, 0, "lagna cell"), (5, 0, "non-lagna cell"),
                                              (1, 3, "non-lagna, other edge"), (7, 7, "lagna, bottom edge")])
@pytest.mark.parametrize("n", range(1, gen.MAX_N + 1))
def test_every_label_stays_inside_its_cell_and_nothing_overlaps(n, where, lagna, kind, retro):
    boxes = _boxes(_render(where, n, retro, lagna))
    col, row, _ = _CELLS[where]
    planets = [b for b in boxes if _cell_of(b[2]) == (col, row) and _is_planet(b[0], b[1])]
    assert len(planets) == n, f"{kind}: expected {n} planet labels in the cell, found {len(planets)}"
    x0, y0, x1, y1 = col * SIZE + MARGIN, row * SIZE + MARGIN, col * SIZE + SIZE - MARGIN, row * SIZE + SIZE - MARGIN
    in_cell = [b for b in boxes if _cell_of(b[2]) == (col, row)]
    for label, fs, bx in in_cell:
        assert bx[0] >= x0 and bx[2] <= x1, f"{kind} n={n}: {label!r} leaves the cell sideways {bx}"
        assert bx[1] >= y0 and bx[3] <= y1, f"{kind} n={n}: {label!r} leaves the cell vertically {bx}"
    for a in range(len(in_cell)):
        for b in range(a + 1, len(in_cell)):
            A, B = in_cell[a][2], in_cell[b][2]
            overlap = not (A[2] <= B[0] or B[2] <= A[0] or A[3] <= B[1] or B[3] <= A[1])
            assert not overlap, f"{kind} n={n}: {in_cell[a][0]!r} overlaps {in_cell[b][0]!r}"


def test_the_lagna_caption_is_rendered_once_and_outside_the_planet_stack():
    boxes = _boxes(_render(0, 8, True, 0))
    lagna = [b for b in boxes if b[0] == "LAGNA"]
    assert len(lagna) == 1
    stack_top = min(b[2][1] for b in boxes if _is_planet(b[0], b[1]))
    assert lagna[0][2][3] <= stack_top, "LAGNA must end above the first planet label"


def test_planet_labels_keep_their_rendered_size():
    """11 units in a <=512px box. Not shrunk to make room (the fix is the layout)."""
    for n in (1, 6, 8):
        sizes = {fs for label, fs, _ in _boxes(_render(0, n, True, 0)) if _is_planet(label, fs)}
        assert sizes == {11.0}, f"n={n}: planet label sizes {sizes}"


def test_a_dense_cell_still_prints_every_planet_and_its_retrograde_mark():
    out = _render(0, 8, True, 0)
    assert out.count("R</tspan>") == 8, "the 7-8 planet layout dropped a retrograde mark"
    for g in GRAHAS[:8]:
        assert f">{g}" in out
