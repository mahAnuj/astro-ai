#!/usr/bin/env python
"""Count clipped snapshot-tile text on the /kundli result page — issue #305.

Why this exists
---------------
`result.html`'s four identity tiles (Lagna / Moon / Sun / Mahadasha, #243) put
`truncate` on the value line and the meta line. At 375px the grid is two
columns and each value box is ~138px, so 10 of the 12 rashi names ("Cancer
(Karka)", "Sagittarius (Dhanu)") and meta strings such as "Uttara Ashadha
Nakshatra" were cut off with an ellipsis and no way to read the rest. The page
rendered, the markup looked right, no test could see it: the defect is purely
geometric, so the only honest check is to inject every name and compare
`scrollWidth` to `clientWidth`.

What it measures
----------------
For each width, every one of the 12 rashi names is injected into the Lagna
tile's value line and every one of the 27 nakshatra names (+ the page's own
"Nakshatra" / "नक्षत्र" suffix) into the Moon tile's meta line. An element counts
as clipped when `scrollWidth > clientWidth`. The tiles as rendered for the real
chart are measured too.

Since the fix lets text wrap, `scrollWidth > clientWidth` can only trip on a
single unbreakable word wider than the box; `max_height` is reported so a
wrapped tile that has grown absurdly tall is visible as well.

The static twin of this check, which CI can run without a browser, is
tests/test_snapshot_tiles_wrap.py.

Playwright is NOT a repo dependency
-----------------------------------
Same as measure_cta_fold.py: it lives in a throwaway venv outside the repo.

    python3 -m venv /tmp/pw-venv
    /tmp/pw-venv/bin/pip install playwright
    # either `playwright install chromium`, or point at a system browser:
    PW_CHROMIUM=/usr/bin/chromium /tmp/pw-venv/bin/python scripts/measure_snapshot_tiles.py

Usage
-----
    ... python scripts/measure_snapshot_tiles.py            # renders /kundli itself (LLM stubbed)
    ... python scripts/measure_snapshot_tiles.py --html en.html hi.html
    ... python scripts/measure_snapshot_tiles.py 375 360 320 --json

Rendering needs no network and no LLM: it shells out to `uv run python` with
the geocoder and provider stubbed, saves /kundli in English and in Hindi, and
points the stylesheet at the committed app.css.

Exit codes: 0 nothing clipped at any width; 1 something clipped; 2 could not
verify (no playwright / no browser / render failed). 2 is not a pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_CSS = ROOT / "src" / "astro_ai" / "static" / "css" / "app.css"
DEFAULT_WIDTHS = (375, 360)
SUFFIX = {"en": "Nakshatra", "hi": "नक्षत्र"}

_RENDER = r"""
import os, sys
sys.path.insert(0, sys.argv[1])
os.environ["OPENAI_API_KEY"] = "x"
from fastapi.testclient import TestClient
from astro_ai import chart, llm
from astro_ai.main import app
chart.geocode_place = lambda p: (19.076, 72.8777, "Asia/Kolkata")
llm.providers.chat = lambda *a, **k: "## Aries / Mesha\n" + "A steady day. " * 80
c = TestClient(app)
r = c.post("/reading", data={"name": "T", "birth_date": "1990-05-15",
           "birth_time": "10:30", "birth_place": "Mumbai, India"}, follow_redirects=False)
assert r.status_code == 303, r.status_code
for path, out in (("/kundli", sys.argv[2]), ("/kundli?lang=hi", sys.argv[3])):
    html = c.get(path).text
    assert "data-snapshot-tile" in html, path
    open(out, "w").write(html)
"""

# JS run in the page. Injects text into the first tile's value line / second
# tile's meta line and reports whether each box clips it.
_MEASURE = """
([rashis, naks, suffix]) => {
  const tiles = [...document.querySelectorAll('[data-snapshot-tile]')];
  const val = (t) => t.children[1];
  const meta = (t) => t.children[2];
  const clipped = (el) => el.scrollWidth > el.clientWidth;
  const out = {rashi: [], nak: [], live: [], max_h: 0};
  const origV = val(tiles[0]).innerHTML, origM = meta(tiles[1]).innerHTML;
  const glyph = val(tiles[0]).querySelector('span');
  const gh = glyph ? glyph.outerHTML + ' ' : '';   // keep the real glyph: it costs ~25px
  for (const r of rashis) {
    val(tiles[0]).innerHTML = gh + r;
    out.rashi.push([r, clipped(val(tiles[0])), tiles[0].getBoundingClientRect().height]);
  }
  val(tiles[0]).innerHTML = origV;
  for (const n of naks) {
    // mirror the template: one nowrap span per word
    meta(tiles[1]).innerHTML = (n + ' ' + suffix).split(' ')
      .map(w => '<span class="whitespace-nowrap">' + w + '</span>').join(' ');
    out.nak.push([n, clipped(meta(tiles[1])), tiles[1].getBoundingClientRect().height]);
  }
  meta(tiles[1]).innerHTML = origM;
  tiles.forEach((t, i) => [val(t), meta(t)].forEach((el, j) => {
    if (el) out.live.push([i + (j ? 'm' : 'v'), el.textContent.trim(), clipped(el)]);
  }));
  return out;
}
"""


def _names() -> tuple[list[str], list[str]]:
    src = (ROOT / "src" / "astro_ai" / "chart.py").read_text()
    def grab(var):
        body = re.search(rf"^{var} = \[(.*?)\]", src, re.S | re.M).group(1)
        return re.findall(r'"([^"]+)"', body)
    return grab("RASHIS"), grab("NAKSHATRAS")


def _render(tmp: Path) -> dict[str, Path]:
    en, hi = tmp / "en.html", tmp / "hi.html"
    try:
        subprocess.run(["uv", "run", "python", "-c", _RENDER, str(ROOT / "src"), str(en), str(hi)],
                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=180)
    except (subprocess.SubprocessError, OSError) as e:
        detail = getattr(e, "stderr", "") or str(e)
        print(f"could not render /kundli: {detail[-400:]}", file=sys.stderr)
        sys.exit(2)
    return {"en": en, "hi": hi}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("widths", nargs="*", type=int, default=list(DEFAULT_WIDTHS))
    ap.add_argument("--html", nargs=2, metavar=("EN", "HI"), help="pre-rendered pages")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed; see the docstring. Exit 2 = could not verify.",
              file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="snapshot-tiles-"))
    pages = ({"en": Path(args.html[0]), "hi": Path(args.html[1])} if args.html else _render(tmp))
    rashis, naks = _names()
    results, any_clipped = [], False

    try:
        with sync_playwright() as pw:
            kw = {"executable_path": os.environ["PW_CHROMIUM"]} if os.environ.get("PW_CHROMIUM") else {}
            browser = pw.chromium.launch(**kw)
            for lang, path in pages.items():
                html = re.sub(r'href="/static/css/app\.css[^"]*"', f'href="{APP_CSS.as_uri()}"',
                              path.read_text())
                page_file = tmp / f"page_{lang}.html"
                page_file.write_text(html)
                for w in args.widths:
                    ctx = browser.new_context(viewport={"width": w, "height": 800},
                                              is_mobile=True, has_touch=True)
                    page = ctx.new_page()
                    page.goto(page_file.as_uri())
                    page.evaluate("document.fonts.ready")
                    m = page.evaluate(_MEASURE, [rashis, naks, SUFFIX[lang]])
                    ctx.close()
                    row = {
                        "lang": lang, "width": w,
                        "rashi_clipped": sum(1 for _, c, _ in m["rashi"] if c), "rashi_total": len(m["rashi"]),
                        "nak_clipped": sum(1 for _, c, _ in m["nak"] if c), "nak_total": len(m["nak"]),
                        "live_clipped": [f"{k}:{t}" for k, t, c in m["live"] if c],
                        "max_tile_height": round(max(h for *_, h in m["rashi"] + m["nak"])),
                        "rashi_names_clipped": [n for n, c, _ in m["rashi"] if c],
                    }
                    any_clipped |= bool(row["rashi_clipped"] or row["nak_clipped"] or row["live_clipped"])
                    results.append(row)
            browser.close()
    except Exception as e:  # no browser, bad executable, page would not load
        print(f"could not measure: {e}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"{'lang':4} {'width':>5} {'rashi':>7} {'nakshatra':>10} {'live':>5} {'max tile h':>10}")
        for r in results:
            print(f"{r['lang']:4} {r['width']:>5} {r['rashi_clipped']:>3}/{r['rashi_total']:<3} "
                  f"{r['nak_clipped']:>5}/{r['nak_total']:<4} {len(r['live_clipped']):>5} "
                  f"{r['max_tile_height']:>9}px")
    return 1 if any_clipped else 0


if __name__ == "__main__":
    sys.exit(main())
