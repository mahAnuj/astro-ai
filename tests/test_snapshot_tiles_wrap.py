"""The /kundli identity tiles must wrap, never ellipsis-clip — #305.

`result.html`'s four snapshot tiles (Lagna / Moon / Sun / Mahadasha, #243) put
`truncate` on the value and meta lines. At 375px a tile's value box is ~138px,
so 10 of the 12 rashi names ("Cancer (Ka…") and meta strings such as "Uttara
Ashadha Nakshatra" were cut off, on the first thing a seeker reads after
submitting their details. The page rendered, the markup looked right and no
request-path test could see it, because the defect is geometry.

Geometry cannot be asserted without a browser (scripts/measure_snapshot_tiles.py
does that, and is the proof: 10/12 -> 0/12 at 375px), so this pins the markup
facts that geometry depends on, in the one place CI can run them:

  * no clipping utility on any tile or anything inside it — `truncate`,
    `text-ellipsis`, `overflow-hidden`, `whitespace-nowrap` on a LINE (the
    per-word spans inside the meta line are the one allowed use);
  * the value and meta lines carry `break-words`;
  * `whitespace-nowrap` and `break-words` have rules in the committed app.css.
    The Dockerfile never runs Node, so a class missing from that artefact is
    markup styled by nothing — the #229 / #254 failure shape.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

APP_CSS = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "static" / "css" / "app.css"

CLIPPING = ("truncate", "text-ellipsis", "overflow-hidden", "overflow-x-hidden", "line-clamp")

_NATAL = (
    "## Personality\n" + "The chart favours patient, deliberate work this season. " * 10 + "\n\n"
    "## Career\n" + "The chart favours patient, deliberate work this season. " * 10 + "\n"
)


def _tiles(html: str) -> list[str]:
    """The markup of each `[data-snapshot-tile]`, up to the next tile or the
    end of the grid. Tiles never nest, so splitting on the marker is exact."""
    # Split on the element, not the bare attribute: base.html's <style> also
    # contains `[data-snapshot-tile]` selectors.
    return ["<div data-snapshot-tile" + p for p in html.split("<div data-snapshot-tile")[1:]]


@pytest.fixture
def result_pages(client, saved_chart, stub_llm):
    stub_llm(_NATAL)
    saved_chart()
    return {"en": client.get("/kundli").text, "hi": client.get("/kundli?lang=hi").text}


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_snapshot_tiles_render_four(result_pages, lang):
    assert len(_tiles(result_pages[lang])) == 4


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_no_tile_clips_its_text(result_pages, lang):
    for tile in _tiles(result_pages[lang]):
        # Only the first element's own markup up to the tile's closing: the
        # last tile's slice runs on to the end of the page, so cut at the
        # grid's close (`</header>` follows the grid).
        tile = tile.split("</header>")[0]
        classes = " ".join(re.findall(r'class="([^"]*)"', tile))
        tokens = classes.split()
        for banned in CLIPPING:
            assert banned not in tokens, (
                f"snapshot tile carries `{banned}`: {banned} clips the Lagna at 375px (#305)"
            )


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_value_and_meta_lines_wrap(result_pages, lang):
    for tile in _tiles(result_pages[lang]):
        tile = tile.split("</header>")[0]
        lines = re.findall(r'<div class="([^"]*(?:text-bhagya-cream)[^"]*)"', tile)
        assert lines, tile
        assert all("break-words" in c.split() for c in lines), lines


def test_meta_words_are_nowrap_so_dates_do_not_split_at_hyphens(result_pages):
    html = result_pages["en"]
    # The Mahadasha meta is two ISO dates; each must sit in its own nowrap span.
    spans = re.findall(r'<span class="whitespace-nowrap">(\d{4}-\d{2}-\d{2})</span>', html)
    assert len(spans) == 2, spans


@pytest.mark.parametrize("cls", ["break-words", "whitespace-nowrap"])
def test_the_classes_the_tiles_rely_on_exist_in_the_built_stylesheet(cls):
    css = APP_CSS.read_text()
    assert re.search(rf"\.{re.escape(cls)}\s*\{{", css), (
        f".{cls} has no rule in app.css — run `npm ci && npm run build:css` and commit it"
    )
