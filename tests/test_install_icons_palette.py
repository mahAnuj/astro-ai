"""The install and favicon icons must wear the live palette, not the retired one (#381).

#233 moved the whole site onto the `bhagya` night/cream/gold palette, and the
manifest already declares `theme_color #140F1C`. The five PNGs in
`static/icons/` are committed binaries that nothing re-renders, so they kept
`astro-700` purple (107, 33, 168) on every tab and every home screen until
`scripts/generate_icons.py` was re-run.

Stdlib only -- Pillow is not a project dependency (same as test_og_card.py).
The first pixel of a PNG's first scanline is always stored raw whatever the
filter byte says (its left and up neighbours are 0, and Paeth(0, 0, 0) is 0),
so the corner colour can be read straight out of the inflated IDAT stream.
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src" / "astro_ai" / "static" / "icons"
MANIFEST = ROOT / "src" / "astro_ai" / "static" / "manifest.webmanifest"
GENERATOR = ROOT / "scripts" / "generate_icons.py"
RETIRED_PURPLE = (107, 33, 168)
NAMES = (
    "icon-192.png",
    "icon-512.png",
    "icon-maskable-512.png",
    "favicon-32.png",
    "apple-touch-icon.png",
)


def _corner_rgb(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    pos, idat, bpp = 8, b"", 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            depth, color = body[8], body[9]
            assert depth == 8 and color in (2, 6), f"{path.name}: unexpected PNG layout"
            bpp = 3 if color == 2 else 4
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    return tuple(raw[1:1 + 3])  # byte 0 is the filter type; then R, G, B


def _theme_color() -> tuple[int, int, int]:
    hexval = json.loads(MANIFEST.read_text(encoding="utf-8"))["theme_color"].lstrip("#")
    return tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4))


def test_every_icon_corner_is_the_manifest_theme_colour():
    expected = _theme_color()
    assert expected == (20, 15, 28), "manifest theme_color moved; re-check the icons"
    wrong = {n: _corner_rgb(ICONS / n) for n in NAMES if _corner_rgb(ICONS / n) != expected}
    assert not wrong, f"icons not on the manifest theme colour {expected}: {wrong}"


def test_no_icon_still_carries_the_retired_purple():
    stale = [n for n in NAMES if _corner_rgb(ICONS / n) == RETIRED_PURPLE]
    assert not stale, f"retired astro-700 purple still on: {stale}"


def test_generator_no_longer_defines_the_retired_purple():
    src = GENERATOR.read_text(encoding="utf-8")
    assert not re.search(r"107,\s*33,\s*168", src), "generate_icons.py still names the retired purple"
