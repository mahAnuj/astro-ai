#!/usr/bin/env python
"""Measure where the homepage's primary CTA lands relative to the fold — issue #195.

Why this exists
---------------
"Is the Get-my-free-Kundli button above the fold?" was being answered three
different ways by three different people, and the answers disagreed. This is
the one harness: every engineer task and every QA pass runs this script, so a
number in a report can be compared with a number in another report.

The one measurement trap
------------------------
The homepage `autofocus`es the Name input. Chromium scrolls that input into
view during load, so by the time you measure, the document is already scrolled
down by a few hundred pixels on the narrow viewports. `getBoundingClientRect()`
is *viewport* relative, so a naive `rect.bottom` reads exactly that much too
small and a CTA that is badly below the fold looks fine.

Worse, the amount is not stable: three consecutive runs of this script against
the same tree measured scrollY at 375x667 as 429, 365 and 339 — it depends on
when load settles relative to the focus scroll. The reported `scrollY` column
exists to make that visible. Document-space `cta_bottom` was 1119 in all three
runs, which is the point.

So we report **document** coordinates: `rect.bottom + scrollY`. That is the
distance from the top of the page to the bottom of the button, independent of
where the browser happened to scroll. The fold is `innerHeight`. The signed
delta is `bottom - innerHeight`; positive means the CTA is below the fold for a
visitor who has not scrolled.

We also report the panchang strip's height and row count, because it is the one
variable-height block sitting above the CTA — it wraps to more rows on narrow
viewports and every extra row pushes the CTA down by roughly its own height.

Playwright is NOT a repo dependency
-----------------------------------
`playwright` is deliberately not in `pyproject.toml` — it would add a browser
download to every `uv sync`. It lives in a scratchpad venv. Run this script
with that interpreter, not with `uv run`:

    /private/tmp/claude-501/-Users-anujmahajan-github-astro-ai/\
e111b755-d1e6-45d6-8eea-2fdade93330a/scratchpad/pw-venv/bin/python \
        scripts/measure_cta_fold.py

If that venv is gone, recreate it:

    python3 -m venv <somewhere>/pw-venv
    <somewhere>/pw-venv/bin/pip install playwright
    <somewhere>/pw-venv/bin/playwright install chromium

Usage
-----
    ... /pw-venv/bin/python scripts/measure_cta_fold.py
    ... /pw-venv/bin/python scripts/measure_cta_fold.py --url http://127.0.0.1:8000/
    ... /pw-venv/bin/python scripts/measure_cta_fold.py 360x640 320x568
    ... /pw-venv/bin/python scripts/measure_cta_fold.py --json

The four fixed viewports are always measured; extra `WxH` arguments are
appended for ad-hoc checks.

Exit code 0 if the CTA is above the fold at 375x667 (the gate viewport — the
smallest common phone and the worst case of the fixed set), 1 otherwise. Also
1 if the page will not load or the CTA cannot be found, because a harness that
cannot measure must not report a pass.
"""

from __future__ import annotations

import argparse
import json
import sys

DEFAULT_URL = "http://127.0.0.1:8000/"

# Fixed set, in the order they are reported. Widths under this threshold get
# is_mobile/has_touch, which changes layout (mobile UA + touch media queries).
FIXED_VIEWPORTS: tuple[tuple[int, int], ...] = ((375, 667), (390, 844), (412, 915), (1280, 800))
MOBILE_WIDTH_MAX = 800

# The viewport the exit code is decided on.
GATE_VIEWPORT = (375, 667)

CTA_TEXT = "Get my free Kundli"
PANCHANG_SELECTOR = 'section[aria-label="Today\'s Panchang"]'

# Measured in the page. Returns document-space coordinates — see the module
# docstring for why `+ scrollY` is not optional here.
MEASURE_JS = """
(args) => {
  const cta = [...document.querySelectorAll('button[type=submit]')]
    .find(b => (b.textContent || '').includes(args.ctaText));

  const out = {
    fold: window.innerHeight,
    scrollY: Math.round(window.scrollY),
    cta: null,
    panchang: null,
  };

  if (cta) {
    const r = cta.getBoundingClientRect();
    // Viewport -> document. The autofocused Name input self-scrolls the page
    // on load, so rect.top/bottom alone under-report by the scroll offset.
    out.cta = {
      top: Math.round(r.top + window.scrollY),
      bottom: Math.round(r.bottom + window.scrollY),
      height: Math.round(r.height),
    };
  }

  const strip = document.querySelector(args.panchangSelector);
  if (strip) {
    const r = strip.getBoundingClientRect();
    // Chips live in the inner flex-wrap group; fall back to the strip itself
    // if that wrapper is ever removed.
    const group = strip.querySelector('[role=group]') || strip;
    const chips = [...group.children];
    const rows = new Set(chips.map(c => Math.round(c.offsetTop)));
    out.panchang = {
      height: Math.round(r.height),
      top: Math.round(r.top + window.scrollY),
      bottom: Math.round(r.bottom + window.scrollY),
      chips: chips.length,
      rows: rows.size,
    };
  }

  return out;
}
"""


def parse_viewport(token: str) -> tuple[int, int]:
    """`'360x640'` -> `(360, 640)`. Raises argparse.ArgumentTypeError on junk."""
    raw = token.lower().replace("*", "x").strip()
    parts = raw.split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"viewport must look like 360x640, got {token!r}")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"viewport must be two integers, got {token!r}") from None
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError(f"viewport dimensions must be positive, got {token!r}")
    return width, height


def _load_playwright():
    """Import playwright or explain exactly how to run this script."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not importable from this interpreter.")
        print("It is NOT a repo dependency — run this script with the scratchpad venv:")
        print("  /private/tmp/claude-501/-Users-anujmahajan-github-astro-ai/"
              "e111b755-d1e6-45d6-8eea-2fdade93330a/scratchpad/pw-venv/bin/python "
              "scripts/measure_cta_fold.py")
        print(f"(current interpreter: {sys.executable})")
        return None
    return sync_playwright


def measure(url: str, viewports: list[tuple[int, int]]) -> list[dict]:
    sync_playwright = _load_playwright()
    if sync_playwright is None:
        raise SystemExit(1)

    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for width, height in viewports:
                mobile = width < MOBILE_WIDTH_MAX
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=mobile,
                    has_touch=mobile,
                )
                try:
                    page = context.new_page()
                    page.goto(url, wait_until="networkidle")
                    data = page.evaluate(
                        MEASURE_JS,
                        {"ctaText": CTA_TEXT, "panchangSelector": PANCHANG_SELECTOR},
                    )
                finally:
                    context.close()

                row = {
                    "viewport": f"{width}x{height}",
                    "width": width,
                    "height": height,
                    "is_mobile": mobile,
                    "fold": data["fold"],
                    "scroll_y_on_load": data["scrollY"],
                    "cta_bottom_doc": None,
                    "delta": None,
                    "panchang_height": None,
                    "panchang_rows": None,
                    "panchang_chips": None,
                }
                if data["cta"] is not None:
                    row["cta_bottom_doc"] = data["cta"]["bottom"]
                    row["cta_top_doc"] = data["cta"]["top"]
                    row["delta"] = data["cta"]["bottom"] - data["fold"]
                if data["panchang"] is not None:
                    row["panchang_height"] = data["panchang"]["height"]
                    row["panchang_rows"] = data["panchang"]["rows"]
                    row["panchang_chips"] = data["panchang"]["chips"]
                rows.append(row)
        finally:
            browser.close()
    return rows


def report(rows: list[dict], url: str) -> int:
    print(f"url: {url}")
    print(f"CTA: button[type=submit] containing {CTA_TEXT!r}")
    print(f"panchang strip: {PANCHANG_SELECTOR}")
    print("coordinates are DOCUMENT-space (rect.bottom + scrollY) — the autofocused")
    print("Name input self-scrolls the page on load, so raw viewport coords under-report.")
    print()
    header = (f"{'viewport':<10} {'CTA bottom':>10} {'fold':>6} {'delta':>7}  "
              f"{'panchang h':>10} {'rows':>5} {'chips':>5} {'scrollY':>8}")
    print(header)
    print("-" * len(header))

    missing: list[str] = []
    for row in rows:
        if row["cta_bottom_doc"] is None:
            missing.append(row["viewport"])
            print(f"{row['viewport']:<10} {'NOT FOUND':>10}  (CTA not in DOM at this viewport)")
            continue
        ph = "-" if row["panchang_height"] is None else str(row["panchang_height"])
        pr = "-" if row["panchang_rows"] is None else str(row["panchang_rows"])
        pc = "-" if row["panchang_chips"] is None else str(row["panchang_chips"])
        print(f"{row['viewport']:<10} {row['cta_bottom_doc']:>10} {row['fold']:>6} "
              f"{row['delta']:>+7}  {ph:>10} {pr:>5} {pc:>5} {row['scroll_y_on_load']:>8}")

    if any(r["panchang_height"] is None for r in rows):
        print()
        print(f"note: {PANCHANG_SELECTOR} did not match at one or more viewports — "
              f"the strip's aria-label may have changed.")

    print()
    if missing:
        print(f"FAIL: CTA not found at {', '.join(missing)} — cannot measure, "
              f"so this is not a pass.")
        return 1

    gate_label = f"{GATE_VIEWPORT[0]}x{GATE_VIEWPORT[1]}"
    gate = next((r for r in rows if r["viewport"] == gate_label), None)
    if gate is None:
        print(f"FAIL: gate viewport {gate_label} was not measured.")
        return 1

    if gate["delta"] > 0:
        print(f"FAIL: at {gate_label} the CTA bottom sits {gate['delta']}px BELOW the fold "
              f"({gate['cta_bottom_doc']} > {gate['fold']}).")
        return 1
    print(f"PASS: at {gate_label} the CTA bottom sits {-gate['delta']}px above the fold "
          f"({gate['cta_bottom_doc']} <= {gate['fold']}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"page to measure (default {DEFAULT_URL})")
    parser.add_argument("--json", action="store_true",
                        help="also emit the rows as JSON on the last line")
    parser.add_argument("extra", nargs="*", type=parse_viewport, metavar="WxH",
                        help="additional viewports to measure, e.g. 360x640 320x568")
    args = parser.parse_args(argv)

    viewports = list(FIXED_VIEWPORTS)
    for vp in args.extra:
        if vp not in viewports:
            viewports.append(vp)

    rows = measure(args.url, viewports)
    code = report(rows, args.url)
    if args.json:
        print(json.dumps(rows))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
