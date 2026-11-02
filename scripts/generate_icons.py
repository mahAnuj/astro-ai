"""Generate Bhagya's PWA icon set from the Kundli-diamond logo design.

Run from repo root:
    uv run --with pillow python scripts/generate_icons.py

Outputs to src/astro_ai/static/icons/:
    icon-192.png            — Android Chrome PWA install icon
    icon-512.png            — high-res splash + install
    icon-maskable-512.png   — Android adaptive icon (content inside safe zone)
    favicon-32.png          — crisp browser-tab favicon
    apple-touch-icon.png    — iOS home-screen icon (180x180 is Apple's canonical size)

Design: North-Indian Kundli (outer diamond + diagonals + inner diamond from
edge midpoints, creating the classic 12-house layout) with a gold center
dot ("bindu") on astro-700 purple. Reads as Vedic astrology to Indian
viewers at any size from 16px to 512px.

Re-run any time the brand palette or shape changes.
"""
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "src" / "astro_ai" / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

# Palette — keep in sync with tailwind config in templates/base.html.
BG = (107, 33, 168)       # astro-700 purple
FG = (255, 255, 255)      # white
ACCENT = (255, 215, 100)  # warm gold (saffron-ish) for the bindu


def draw_kundli(size: int, *, r_ratio: float = 0.42, stroke_ratio: float = 0.022,
                dot_ratio: float = 0.045, bg_alpha: int = 255,
                bg: tuple | None = None, fg: tuple | None = None,
                accent: tuple | None = None) -> Image.Image:
    """Render the Kundli-diamond logo at `size`x`size`.

    r_ratio:      diamond half-width as a fraction of canvas size. 0.42 is
                  good for normal icons; drop to ~0.35 for maskable so the
                  vertices stay inside Android's adaptive safe zone.
    stroke_ratio: line width as a fraction of canvas size.
    dot_ratio:    center bindu radius as a fraction of canvas size.
    bg/fg/accent: optional RGB overrides, default to the module constants so
                  the install icons are unaffected (#381 owns their colours).
                  generate_og_card.py passes the bhagya palette (#265).
    """
    bg = BG if bg is None else bg
    fg = FG if fg is None else fg
    accent = ACCENT if accent is None else accent
    img = Image.new("RGBA", (size, size), bg + (bg_alpha,))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = int(size * r_ratio)
    stroke = max(2, int(size * stroke_ratio))

    # Diamond vertices.
    top    = (cx,     cy - r)
    right  = (cx + r, cy)
    bottom = (cx,     cy + r)
    left   = (cx - r, cy)

    # Outer diamond.
    d.line([top, right, bottom, left, top],
           fill=fg + (255,), width=stroke, joint="curve")
    # The two through-lines (vertical + horizontal) carve the 12 houses.
    d.line([top, bottom], fill=fg + (255,), width=stroke)
    d.line([left, right], fill=fg + (255,), width=stroke)
    # Inner diamond from edge midpoints — completes the classical layout.
    m_tr = ((top[0]+right[0])//2,  (top[1]+right[1])//2)
    m_rb = ((right[0]+bottom[0])//2, (right[1]+bottom[1])//2)
    m_bl = ((bottom[0]+left[0])//2,  (bottom[1]+left[1])//2)
    m_lt = ((left[0]+top[0])//2,     (left[1]+top[1])//2)
    d.line([m_tr, m_rb, m_bl, m_lt, m_tr],
           fill=fg + (255,), width=stroke, joint="curve")

    # Gold bindu at center — the spiritual anchor point.
    dot_r = int(size * dot_ratio)
    d.ellipse([(cx-dot_r, cy-dot_r), (cx+dot_r, cy+dot_r)],
              fill=accent + (255,))
    return img


def save(img: Image.Image, name: str) -> None:
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print(f"  {name:<30s} {path.stat().st_size // 1024:>4d} KB")


def main() -> None:
    print(f"Writing icons to {OUT.relative_to(REPO_ROOT)}/")
    # PWA install icons (normal — vertices reach close to the canvas edge).
    save(draw_kundli(192), "icon-192.png")
    save(draw_kundli(512), "icon-512.png")
    # Maskable — vertices shrunk inside the safe-zone circle (radius 0.4*size)
    # so Android's adaptive-icon masking can crop to circle/squircle/etc.
    save(draw_kundli(512, r_ratio=0.36, stroke_ratio=0.022, dot_ratio=0.04),
         "icon-maskable-512.png")
    # Browser-tab favicon — slightly thicker stroke at 32px keeps the lines
    # visible against the purple ground.
    save(draw_kundli(32, r_ratio=0.42, stroke_ratio=0.05, dot_ratio=0.10),
         "favicon-32.png")
    # iOS home-screen icon (Apple's canonical size).
    save(draw_kundli(180), "apple-touch-icon.png")
    print("Done.")


if __name__ == "__main__":
    main()
