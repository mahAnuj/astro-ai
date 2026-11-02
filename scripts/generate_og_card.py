"""Generate the default Open Graph share card.

Run from repo root:
    uv run --with pillow python scripts/generate_og_card.py

Outputs:
    src/astro_ai/static/og/default.png   — 1200x630, the site-wide og:image

Why this exists: og:image defaulted to icon-512.png, a 512x512 square, while
the page also declared `twitter:card = summary_large_image`. Every platform
that wants a 1.91:1 landscape card — Facebook, LinkedIn, X, WhatsApp, Slack —
either letterboxes the square, centre-crops it into an unreadable fragment, or
drops it and renders a bare text link. 1200x630 is the size all of them agree
on, and it is the minimum that survives LinkedIn's 1.91:1 crop.

Reuses draw_kundli() from generate_icons.py so the mark can never drift from
the favicon and PWA icons.

The card is drawn in the redesign `bhagya` palette (#233; tailwind.config.js)
rather than the retired astro purple it shipped with (#265). The article count
in the proof line is READ from learn_registry.ARTICLES, never typed: the literal
"76" was correct the day it was written and wrong the day article 77 shipped,
on a committed binary nothing re-renders. The generation inputs are also
written into the PNG as tEXt chunks so tests/test_og_card.py can check them
without OCR.

Re-run any time the brand palette, wordmark or tagline changes, and whenever
an article is added to or removed from learn_registry.ARTICLES.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
# learn_registry imports only dataclasses, so this pulls in no app dependency.
sys.path.insert(0, str(REPO_ROOT / "src"))

from generate_icons import draw_kundli  # noqa: E402
from astro_ai.learn_registry import ARTICLES  # noqa: E402

OUT = REPO_ROOT / "src" / "astro_ai" / "static" / "og"
OUT.mkdir(parents=True, exist_ok=True)

# 1.905:1 — the ratio Facebook, LinkedIn, X and WhatsApp all render without
# cropping. Do not change these two numbers.
W, H = 1200, 630

# bhagya palette — tailwind.config.js `theme.extend.colors.bhagya`.
CREAM = (250, 246, 239)     # #FAF6EF  bhagya-cream, the card ground
NIGHT = (20, 15, 28)        # #140F1C  bhagya-night, left band + mark tile
INK = (23, 19, 26)          # #17131A  bhagya-ink, the title
MUTED = (107, 98, 89)       # #6B6259  bhagya-muted, tagline + proof
GOLD = (200, 164, 77)       # #C8A44D  bhagya-gold — ORNAMENT ONLY: 2.20:1 on
                            # cream, so it is the rule and the bindu, never text
SINDOOR = (158, 43, 37)     # #9E2B25  bhagya-sindoor, the URL

# The card is drawn on cream rather than night: a light card stands out in
# both light and dark chat threads, and dark cards disappear against WhatsApp's
# dark mode.
TITLE = "Shubh Bhagya"
TAGLINE = "Free Vedic Kundli, Rashifal & Panchang"
ARTICLE_COUNT = len(ARTICLES)
# "Swiss Ephemeris" is body copy, not a badge (#234); the homepage trust cell
# already says Sidereal Lahiri.
PROOF = f"Sidereal Lahiri ayanamsha  ·  {ARTICLE_COUNT} cited explainers  ·  No signup"


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """First font that exists wins. Pillow's built-in bitmap font is unusable
    at this size, so a real face is required — but which faces exist differs
    between a Mac laptop and a CI container, hence the chain."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit(
        "No usable TrueType font found. Install DejaVu or Liberation fonts, "
        "or add a path to load_font()."
    )


def main() -> None:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # Night band down the left edge — the brand present without making the
    # whole card dark.
    d.rectangle([(0, 0), (18, H)], fill=NIGHT)

    # The same mark as the favicon, pasted with its own alpha.
    mark = draw_kundli(148, bg=NIGHT, fg=CREAM, accent=GOLD).convert("RGBA")
    img.paste(mark, (84, 92), mark)

    d.text((266, 108), TITLE, font=load_font(72, bold=True), fill=INK)
    d.text((266, 196), TAGLINE, font=load_font(38), fill=MUTED)

    # Gold rule — the bindu colour, tying the card to the mark.
    d.rectangle([(84, 372), (200, 380)], fill=GOLD)

    d.text((84, 424), PROOF, font=load_font(30), fill=MUTED)
    d.text((84, 520), "shubhagya.com", font=load_font(30, bold=True), fill=SINDOOR)

    path = OUT / "default.png"
    # tEXt chunks: what the render was built FROM, readable without OCR.
    meta = PngInfo()
    meta.add_text("bhagya:article_count", str(ARTICLE_COUNT))
    meta.add_text("bhagya:proof", PROOF)
    img.save(path, "PNG", optimize=True, pnginfo=meta)
    print(f"  {path.relative_to(REPO_ROOT)}  {W}x{H}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
