#!/usr/bin/env python3
"""Gate for #189 — Devanagari display type, and the payload shape it ships in.

WHY THIS NEEDS A BROWSER
The thing #189 fixes is which font the RENDERER picks. A template can list
`"Noto Serif Devanagari"` in a font-family and still paint sans — the face may
not have loaded, a later rule may win the cascade, or the glyph may not exist
in that face and fall through silently. Reading the CSS proves nothing. So this
walks CDP's CSS.getPlatformFontsForNode, which reports the faces Chromium
ACTUALLY used to paint each node.

WHAT IT ENFORCES

  1. Every rendered [lang="sa"] node paints in Noto Serif Devanagari.
  2. None of them is bold or italic. Devanagari has no italic form (a browser
     synthesises an oblique by shearing glyphs — the original #189 defect), and
     nothing being bold is the PRECONDITION for requesting the serif at
     wght@400 only. Add a bold shloka and this gate fails, correctly: you must
     then restore wght@400;700 in base.html and pay the full variable face.
  3. Devanagari inside `font-display font-bold` paints in Noto SANS Devanagari,
     which we load at 700. This is the regression that scoping the serif to
     lang="sa" exists to prevent — wire the serif into the `display` family
     instead and those headings get a SYNTHESISED bold, the same defect class
     #189 removes. Checked directly, because it is invisible in the diff.
  4. Web-font transfer stays at or under MAX_FONT_BYTES.

The gate was bite-tested against commit 4904f3b (the first shape of the #189
fix, serif wired into `display` at wght@400;700): check 3 fails and the payload
check fails at 345,052 B. It is not vacuous.

USAGE
    uv run astro-ai &                     # gate needs the dev server
    python3 scripts/verify_devanagari_serif.py [--url URL] [--width N]

EXIT CODES
    0  PASS
    1  FAIL — a check did not hold
    2  COULD NOT VERIFY — no playwright, or the server is not up. Deliberately
       distinct from PASS: an unrunnable gate must never read as a green one.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.error
import urllib.request

# Measured 2026-08-09 at 390x844 signed out: 268,820 B over 4 files.
# Headroom for subset drift, not for adding a family — adding one should make
# you re-read the payload table in base.html and decide deliberately.
MAX_FONT_BYTES = 285_000

# Both viewports are checked. The hero shloka is `hidden sm:block`, so it is
# display:none at 390 and only the desktop pass exercises it. A node that is
# not painted is SKIPped rather than passed — CDP reports no fonts for it, and
# reading that empty list as "no violation" is how this gate would go hollow.
VIEWPORTS = (390, 1280)


async def run(url: str, widths: tuple[int, ...]) -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("COULD NOT VERIFY: playwright is not installed.")
        print("  pip install playwright && playwright install chromium")
        return 2

    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            if r.status != 200:
                raise urllib.error.URLError(f"HTTP {r.status}")
    except Exception as exc:
        print(f"COULD NOT VERIFY: {url} is not reachable ({exc}).")
        print("  Start it with: uv run astro-ai")
        return 2

    all_failures: list[str] = []

    print("Devanagari serif verification (#189)\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for width in widths:
                ctx = await browser.new_context(viewport={"width": width, "height": 844})
                page = await ctx.new_page()
                font_bytes: dict[str, int] = {}

                async def on_response(resp):
                    if ".gstatic.com" in resp.url and resp.url.endswith(".woff2"):
                        try:
                            font_bytes[resp.url] = len(await resp.body())
                        except Exception:
                            pass

                page.on("response", on_response)
                cdp = await ctx.new_cdp_session(page)
                await cdp.send("DOM.enable")
                await cdp.send("CSS.enable")

                await page.goto(url, wait_until="networkidle")
                await page.evaluate("document.fonts.ready")

                root = (await cdp.send("DOM.getDocument", {"depth": -1}))["root"]["nodeId"]
                failures: list[str] = []

                print(f"  viewport {width}x844")

                # ── 1 + 2 ────────────────────────────────────────────────
                sa_ids = (
                    await cdp.send(
                        "DOM.querySelectorAll",
                        {"nodeId": root, "selector": '[lang="sa"]'},
                    )
                )["nodeIds"]
                if not sa_ids:
                    failures.append('no [lang="sa"] elements found — markup changed?')

                for idx, nid in enumerate(sa_ids):
                    used = [
                        f["familyName"]
                        for f in (
                            await cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})
                        )["fonts"]
                    ]
                    cs = {
                        pr["name"]: pr["value"]
                        for pr in (
                            await cdp.send("CSS.getComputedStyleForNode", {"nodeId": nid})
                        )["computedStyle"]
                    }
                    label = (
                        await cdp.send("DOM.getOuterHTML", {"nodeId": nid})
                    )["outerHTML"][:60].replace("\n", " ")

                    painted = await page.evaluate(
                        """i => { const r = document.querySelectorAll('[lang="sa"]')[i]
                                    .getBoundingClientRect();
                                  return r.width * r.height > 0; }""",
                        idx,
                    )
                    if not painted:
                        print(f"    skip  not rendered at this width :: {label}")
                        continue

                    if not any("Noto Serif Devanagari" in f for f in used):
                        failures.append(f"lang=sa painted in {used}, not the serif :: {label}")
                    else:
                        print(f"    ok    serif  w={cs.get('font-weight')} :: {used}")

                    if cs.get("font-weight") and int(cs["font-weight"]) >= 600:
                        failures.append(
                            f"lang=sa is BOLD (w={cs['font-weight']}) but the serif is "
                            f"requested at wght@400 only — this is a synthesised bold. "
                            f"Restore wght@400;700 in base.html :: {label}"
                        )
                    if cs.get("font-style") != "normal":
                        failures.append(
                            f"lang=sa is font-style:{cs.get('font-style')} — Devanagari "
                            f"has no italic, so this is a sheared oblique :: {label}"
                        )

                # ── 3 ────────────────────────────────────────────────────
                await page.evaluate(
                    """async () => {
                        const el = document.createElement('div');
                        el.id = '__bold_deva_probe';
                        el.className = 'font-display font-bold';
                        el.textContent = 'शुभ भाग्य';
                        el.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;'
                                         + 'font-size:32px;background:#fff';
                        document.body.appendChild(el);
                        await document.fonts.ready;
                        await new Promise(r =>
                            requestAnimationFrame(() => requestAnimationFrame(r)));
                    }"""
                )
                for nid in (
                    await cdp.send(
                        "DOM.querySelectorAll",
                        {"nodeId": root, "selector": "#__bold_deva_probe"},
                    )
                )["nodeIds"]:
                    used = [
                        f["familyName"]
                        for f in (
                            await cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})
                        )["fonts"]
                    ]
                    if any("Noto Serif Devanagari" in f for f in used):
                        failures.append(
                            f"bold Devanagari painted in the SERIF {used}; only its 400 "
                            f"is loaded, so that is a synthesised bold"
                        )
                    elif not any("Noto Sans Devanagari" in f for f in used):
                        failures.append(
                            f"bold Devanagari painted in {used}, expected Noto Sans Devanagari"
                        )
                    else:
                        print(f"    ok    bold Devanagari stays sans :: {used}")

                # ── 4 ────────────────────────────────────────────────────
                total = sum(font_bytes.values())
                print(f"    web-font transfer: {total:,} B over {len(font_bytes)} file(s)")
                for u, b in sorted(font_bytes.items(), key=lambda kv: -kv[1]):
                    print(f"        {b:>8,} B  {u.split('/')[-1][:34]}")
                if total > MAX_FONT_BYTES:
                    failures.append(
                        f"web-font transfer {total:,} B exceeds MAX_FONT_BYTES "
                        f"{MAX_FONT_BYTES:,} B"
                    )

                all_failures += [f"[{width}px] {f}" for f in failures]
                await ctx.close()
                print()
        finally:
            await browser.close()

    if all_failures:
        print("FAIL")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print("PASS — serif on every rendered shloka, none bold or obliqued,")
    print("       bold Devanagari stays sans, payload within budget")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8000/")
    ap.add_argument(
        "--width",
        type=int,
        action="append",
        help="viewport width; repeatable. Defaults to 390 and 1280.",
    )
    args = ap.parse_args()
    return asyncio.run(run(args.url, tuple(args.width or VIEWPORTS)))


if __name__ == "__main__":
    sys.exit(main())
