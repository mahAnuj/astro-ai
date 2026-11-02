"""The committed share card must be built from the registry, not typed (#265).

`static/og/default.png` is the og:image for the homepage and every /learn
article, and it is a committed binary that nothing re-renders. It shipped with
"76 cited explainers" typed into a script and "Swiss Ephemeris chart math"
(#234's ruling: body copy, not a badge), drawn in the retired purple identity.
The count was right the day it was written and stale the day article 77 landed.

`scripts/generate_og_card.py` now reads `len(learn_registry.ARTICLES)` and
writes its inputs into the PNG as tEXt chunks. This file reads them back with
the stdlib only -- Pillow is not a project dependency and OCR is not a test.
The consequence worth knowing: adding an article turns THIS red until
`uv run --with pillow python scripts/generate_og_card.py` is re-run and the
PNG recommitted. That is the point.
"""
from __future__ import annotations

import re
import struct
import zlib
from pathlib import Path

from astro_ai.learn_registry import ARTICLES

ROOT = Path(__file__).resolve().parent.parent
CARD = ROOT / "src" / "astro_ai" / "static" / "og" / "default.png"
SCRIPT = ROOT / "scripts" / "generate_og_card.py"


def _chunks(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        yield data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length


def _text_chunks() -> dict[str, str]:
    out: dict[str, str] = {}
    for kind, body in _chunks(CARD.read_bytes()):
        if kind == b"tEXt":
            key, _, value = body.partition(b"\x00")
            out[key.decode("latin-1")] = value.decode("latin-1")
        elif kind == b"iTXt":  # Pillow writes this for non-latin-1 text
            key, _, rest = body.partition(b"\x00")
            compressed, _method = rest[0], rest[1]
            rest = rest[2:]
            _lang, _, rest = rest.partition(b"\x00")
            _tkey, _, text = rest.partition(b"\x00")
            if compressed:
                text = zlib.decompress(text)
            out[key.decode("latin-1")] = text.decode("utf-8")
    return out


def test_card_is_exactly_1200_by_630():
    ihdr = next(body for kind, body in _chunks(CARD.read_bytes()) if kind == b"IHDR")
    assert struct.unpack(">II", ihdr[:8]) == (1200, 630), (
        "1.905:1 is the one ratio Facebook, LinkedIn, X and WhatsApp all render "
        "uncropped; any other size is letterboxed or centre-cropped."
    )


def test_embedded_article_count_matches_the_registry():
    meta = _text_chunks()
    assert "bhagya:article_count" in meta, (
        "the PNG carries no generation inputs -- it was not produced by "
        "scripts/generate_og_card.py"
    )
    assert int(meta["bhagya:article_count"]) == len(ARTICLES), (
        f"card says {meta['bhagya:article_count']} explainers, the registry has "
        f"{len(ARTICLES)}. Re-run: uv run --with pillow python scripts/generate_og_card.py"
    )


def test_embedded_proof_line_states_that_count_and_no_swiss_ephemeris_badge():
    proof = _text_chunks()["bhagya:proof"]
    assert re.search(rf"\b{len(ARTICLES)} cited explainers\b", proof), proof
    assert "Swiss Ephemeris" not in proof, "#234: Swiss Ephemeris is body copy, not a badge"


def test_generator_reads_the_registry_and_types_no_count():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "len(ARTICLES)" in src, "the count must be read from the registry"
    # A digit run next to the noun is the typed-literal shape this issue was.
    assert not re.search(r"\d+\s+cited explainers", src), (
        "a number typed into the proof line goes stale when article N+1 ships"
    )
    assert "(59, 7, 100)" not in src, "the retired astro-950 purple is back on the card"
    assert "Swiss Ephemeris chart math" not in src
