#!/usr/bin/env python3
"""Generate the label-slot table for the North Indian diamond chart (#380).

WHY THIS EXISTS. The diamond SVG is `viewBox="0 0 400 400"` and shows at 259-301
CSS px on a phone, so a label sized in viewBox units renders at (size x box/400).
At the old 11 that was 6.5-8.3 px. Raising the size is not enough: eight of the
twelve cells are triangles whose usable width collapses toward the apex (house 2
is (2,2),(200,2),(101,101): ~50 units wide at y=76), and the old stack pitch of
13 is smaller than the text it is meant to separate once the text is 16 high.

So the positions are solved geometrically, here, and pasted into
`templates/_diamond_labels.html` as a literal. `tests/test_diamond_label_geometry.py`
re-checks the pasted table (it imports the geometry from this file), so editing a
size or a coordinate by hand goes red rather than silently overlapping.

    uv run python scripts/gen_diamond_label_slots.py          # print the Jinja literal
    uv run python scripts/gen_diamond_label_slots.py --check  # exit 1 if nothing fits

Modes per (house, n planets), first that fits wins:
  full     one column of "Su 29° R" labels
  compact  "Su R" labels (degree dropped) -- up to three per row
  tiny     "Su" labels (degree and R dropped) -- only a triangle holding 7+ grahas
The degree is dropped only in a cell too small for it. It is not lost from the
page: /kundli has a planetary-positions table under the chart, and /matching (which
has none) prints a compact positions line under each mini chart (#889,
`templates/_chart_positions.html`).

Widths are an ESTIMATE (Manrope is a webfont, not installed here). The per-glyph
numbers below are deliberately wider than Manrope SemiBold and a 6% safety pad is
added; the test also records a measured pass in headless Chromium.
"""
from __future__ import annotations

import itertools
import sys

FS = 16.0            # planet label size, viewBox units
NUM_FS = 15.0        # house-number size
R_FS = 16.0          # the retrograde "R" tspan
PITCH = 17.6         # stack pitch (1.1 x FS); was 13 at size 11
MARGIN = 3.0         # clearance from a cell line (stroke is 2 wide => 1 + 2)
GAP = 7.0            # horizontal gap between two labels in one row
ASC, DESC = 0.74, 0.20   # text box above / below the baseline, in em
SAFETY = 1.06
# Rahu and Ketu are 180 degrees apart, so at most seven grahas plus one node can
# share a sign: 8 labels is the ceiling, and 9 is not a state a chart can reach.
MAX_N = 8

# Inner-square vertices and where the two diagonals cross its edges.
P, Q, R_, S, O = (101, 101), (299, 101), (101, 299), (299, 299), (200, 200)
CELLS: dict[int, list[tuple[float, float]]] = {
    1: [(200, 2), P, O, Q],
    2: [(2, 2), (200, 2), P],
    3: [(2, 2), (2, 200), P],
    4: [P, (2, 200), R_, O],
    5: [(2, 200), (2, 398), R_],
    6: [(2, 398), (200, 398), R_],
    7: [R_, O, S, (200, 398)],
    8: [(200, 398), (398, 398), S],
    9: [(398, 200), (398, 398), S],
    10: [Q, O, S, (398, 200)],
    11: [(398, 2), (398, 200), Q],
    12: [(200, 2), (398, 2), Q],
}
_W = {"digit": 0.66, "letter": 0.70, "space": 0.30, "deg": 0.48, "R": 0.72}


def text_w(kind: str, abbr: str = "Su", deg: int = 29, retro: bool = True) -> float:
    """Estimated advance width of one label in viewBox units."""
    if kind == "num":
        return len(str(deg)) * _W["digit"] * NUM_FS * SAFETY
    w = len(abbr) * _W["letter"] * FS
    if kind == "full":
        w += _W["space"] * FS + 2 * _W["digit"] * FS + _W["deg"] * FS
    if retro:
        w += _W["space"] * FS + _W["R"] * R_FS
    return w * SAFETY


# Worst case a label can be: two-letter code, two-digit degree, retrograde.
FULL_W = text_w("full")
COMPACT_W = text_w("compact")
TINY_W = text_w("compact", retro=False)
NUM_W = text_w("num", deg=12)


def box(cx: float, y: float, w: float, fs: float = FS):
    return (cx - w / 2, y - ASC * fs, cx + w / 2, y + DESC * fs)


def _edges(poly):
    """(a, b, c, norm): inside is a*x + b*y >= c for a CCW-or-CW polygon."""
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly)))
    sign = 1.0 if area > 0 else -1.0
    out = []
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        a, b = -(y2 - y1) * sign, (x2 - x1) * sign
        n = (a * a + b * b) ** 0.5
        out.append((a / n, b / n, (a * x1 + b * y1) / n))
    return out


def inside(poly, x: float, y: float, margin: float = MARGIN) -> bool:
    return all(a * x + b * y - c >= margin - 1e-9 for a, b, c in _edges(poly))


def box_inside(poly, bx, margin: float = MARGIN) -> bool:
    x0, y0, x1, y1 = bx
    return all(inside(poly, x, y, margin) for x in (x0, x1) for y in (y0, y1))


def overlap(a, b, pad: float = 0.0) -> bool:
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _interval(poly, y: float):
    """Allowed x-range (margin applied) of a horizontal line at y, or None."""
    lo, hi = -1e9, 1e9
    for a, b, c in _edges(poly):
        rhs = c + MARGIN - b * y
        if abs(a) < 1e-9:
            if rhs > 1e-9:
                return None
        elif a > 0:
            lo = max(lo, rhs / a)
        else:
            hi = min(hi, rhs / a)
    return (lo, hi) if lo < hi else None


def _strip(poly, y_top: float, y_bot: float):
    """x-range that keeps a box spanning [y_top, y_bot] inside (convex: the
    extremes of the strip are the binding rows)."""
    a, b = _interval(poly, y_top), _interval(poly, y_bot)
    if a is None or b is None:
        return None
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo < hi else None


def _centroid(poly):
    return (sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly))


# The four diamond cells keep their number at the OUTER tip, as before.
OUTER_TIP = {1: (200, 2), 4: (2, 200), 7: (200, 398), 10: (398, 200)}


def number_candidates(house: int):
    """One house-number slot per cell vertex: slide the number from that vertex
    toward the cell's centroid until its box fits. The generator then keeps the
    candidate that leaves the planet stack the most room."""
    poly = CELLS[house]
    cx, cy = _centroid(poly)
    found = []
    for (x0, y0) in ([OUTER_TIP[house]] if house in OUTER_TIP else poly):
        for i in range(401):
            t = i / 400
            x, y = x0 + (cx - x0) * t, y0 + (cy - y0) * t
            yb = y + (ASC - DESC) * NUM_FS / 2     # box vertically centred on y
            if box_inside(poly, box(x, yb, NUM_W, NUM_FS)):
                slot = (round(x, 1), round(yb, 1))
                if slot not in found:
                    found.append(slot)
                break
    return found


def _patterns(n: int, allow_pairs: bool):
    if not allow_pairs:
        yield (1,) * n
        return
    for k in range(1, n + 1):
        for combo in itertools.product((1, 2, 3), repeat=k):
            if sum(combo) == n:
                yield combo


def _solve(house: int, n: int, w: float, allow_pairs: bool, num):
    poly = CELLS[house]
    obstacle = box(num[0], num[1], NUM_W, NUM_FS) if num else None
    best = None
    for pat in _patterns(n, allow_pairs):
        rows = len(pat)
        span = (rows - 1) * PITCH
        y0 = 4.0
        while y0 + span <= 396.0:
            slack, pts, ok = 1e9, [], True
            for r, k in enumerate(pat):
                yb = y0 + r * PITCH
                iv = _strip(poly, yb - ASC * FS, yb + DESC * FS)
                need = k * w + (k - 1) * GAP
                if iv is None or iv[1] - iv[0] < need:
                    ok = False
                    break
                slack = min(slack, iv[1] - iv[0] - need)
                left = (iv[0] + iv[1]) / 2 - need / 2
                for j in range(k):
                    cx = left + j * (w + GAP) + w / 2
                    bx = box(cx, yb, w)
                    if obstacle and overlap(bx, obstacle, 2.0):
                        ok = False
                    pts.append((round(cx, 1), round(yb, 1)))
            if ok:
                # prefer the roomiest, then fewer rows, then fewer pairs
                key = (round(slack, 1), -rows, -pat.count(2))
                if best is None or key > best[0]:
                    best = (key, pts)
            y0 += 0.5
    return best[1] if best else None


def _rows_for(h: int, num):
    rows = []
    for n in range(1, MAX_N + 1):
        for mode, w, pairs in ((0, FULL_W, False), (1, COMPACT_W, True), (2, TINY_W, True)):
            pts = _solve(h, n, w, pairs, num)
            if pts is not None:
                rows.append((mode, pts))
                break
        else:
            rows.append((2, None))
    return rows


def solve_table():
    """{house: [(mode, [(x, y), ...]) for n in 1..MAX_N]} plus house-number slots.
    mode 0 = full label, 1 = compact (no degree), 2 = tiny (no degree, no R)."""
    table: dict[int, list] = {}
    nums: dict[int, tuple[float, float]] = {}
    missing = []
    for h in range(1, 13):
        best = None
        for num in number_candidates(h):
            rows = _rows_for(h, num)
            if any(pts is None for _, pts in rows):
                continue
            score = (-sum(m for m, _ in rows), -sum(m == 2 for m, _ in rows))
            if best is None or score > best[0]:
                best = (score, num, rows)
        if best is None:
            missing.append(h)
            continue
        _, nums[h], table[h] = best
    return table, nums, missing


def render_jinja(table, nums) -> str:
    out = ["{% set _numpos = {"]
    out.append("  " + ", ".join(f"{h}: [{x}, {y}]" for h, (x, y) in nums.items()))
    out.append("} %}")
    out.append("{% set _slots = {")
    for h in range(1, 13):
        out.append(f"  {h}: [")
        for compact, pts in table[h]:
            flat = ", ".join(f"[{x}, {y}]" for x, y in pts)
            out.append(f"    [{compact}, [{flat}]],")
        out.append("  ],")
    out.append("} %}")
    return "\n".join(out)


if __name__ == "__main__":
    table, nums, missing = solve_table()
    print(render_jinja(table, nums))
    print(f"# FULL_W={FULL_W:.1f} COMPACT_W={COMPACT_W:.1f} NUM_W={NUM_W:.1f}", file=sys.stderr)
    if missing:
        print(f"# NO FIT houses: {missing}", file=sys.stderr)
        if "--check" in sys.argv:
            sys.exit(1)
    for h in sorted(table):
        caps = [n + 1 for n, (c, _) in enumerate(table[h]) if c == 0]
        print(f"# house {h}: full labels up to n={max(caps) if caps else 0}; number at {nums[h]}", file=sys.stderr)
