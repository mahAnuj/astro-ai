"""A shared /r/{id} link advertises an og:image a crawler can actually use (#231).

`result.html` pointed the snapshot page's og:image at `/kundli/card`, which fails
for a crawler on two independent counts:

1. it is `image/svg+xml`, and Facebook, LinkedIn, X, WhatsApp and Slack do not
   render SVG as a preview image;
2. it is derived from the VISITOR'S session cookie (`load_collection(request)`),
   and a crawler has none -- it gets a 303 to an HTML page. The issue named only
   the first; swapping the SVG for a PNG at the same URL would still have shown
   nothing, and a human opening the link would have seen their OWN card.

So the snapshot page now inherits the site-wide 1200x630 PNG. This pins what a
crawler is told, and that what it is told is true of the bytes it will fetch.

Hermetic: `snapshots.load` is stubbed, so no storage and no LLM are touched.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "src" / "astro_ai" / "static"

_SNAP_ID = "TESTSNAP"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    return TestClient(app)


@pytest.fixture()
def snapshot_page(client, monkeypatch):
    from astro_ai import snapshots
    from astro_ai.routes import kundli

    snap = snapshots.Snapshot(
        id=_SNAP_ID,
        created_at="2026-11-01T00:00:00Z",
        expires_at="2099-01-01T00:00:00Z",
        lang="en",
        birth_details={
            "name": "Share Fixture",
            "birth_date": "1957-09-07",
            "birth_time": "01:05",
            "birth_place": "Mumbai",
        },
        reading_text="## Overview\nA fixture reading.",
    )
    monkeypatch.setattr(kundli.snapshots, "load", lambda short_id: snap)
    r = client.get(f"/r/{_SNAP_ID}")
    assert r.status_code == 200, r.status_code
    return r.text


def _meta(html: str, prop: str) -> str:
    m = re.search(rf'<meta property="{re.escape(prop)}" content="([^"]*)"', html)
    assert m, f"{prop} missing from the snapshot page"
    return m.group(1)


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", data[16:24])


def test_snapshot_og_image_is_a_png_not_the_session_derived_card(snapshot_page):
    url = _meta(snapshot_page, "og:image")
    assert url.endswith(".png"), url
    assert "/kundli/card" not in url, (
        "/kundli/card is SVG and keyed on the visitor's cookie; a crawler gets a "
        "303 to HTML there"
    )


def test_snapshot_declared_size_matches_the_bytes_served(client, snapshot_page):
    url = _meta(snapshot_page, "og:image")
    path = url[url.index("/static/"):]
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    assert r.headers["content-type"] == "image/png", r.headers["content-type"]
    served = struct.unpack(">II", r.content[16:24])
    declared = (
        int(_meta(snapshot_page, "og:image:width")),
        int(_meta(snapshot_page, "og:image:height")),
    )
    assert served == declared, (
        f"the page declares {declared} but the file is {served}; a crawler lays "
        "out the declared box before it fetches"
    )
    assert served == _png_size(STATIC / path.removeprefix("/static/"))


def test_twitter_image_agrees_with_og_image(snapshot_page):
    m = re.search(r'<meta name="twitter:image" content="([^"]*)"', snapshot_page)
    assert m and m.group(1) == _meta(snapshot_page, "og:image")
