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
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_HTML = REPO_ROOT / "src/astro_ai/templates/base.html"
TEMPLATES = REPO_ROOT / "src/astro_ai/templates"

# The Hindi UI needs a Devanagari SANS at every weight the templates use bold
# at. This is the static half of the gate and it is the half that survives a
# browser it cannot launch or a font host it cannot reach.
#
# Why it exists (#235). A redesign handoff proposed replacing the type stack
# with Marcellus + Manrope + Tiro Devanagari Sanskrit. Neither Marcellus nor
# Manrope ships a Devanagari subset, and Tiro is a 400-only Sanskrit serif —
# so the whole Hindi UI would have lost its face and every bold Hindi heading
# would have fallen through to a system font. That is #189 returning.
#
# The browser probe below catches it too, and more strongly, because it reads
# what actually painted. But it needs a running server, a working Chromium and
# network access to fonts.gstatic. This check needs a file.
REQUIRED_DEVANAGARI_SANS = "Noto Sans Devanagari"
REQUIRED_SANS_WEIGHTS = (400, 500, 600, 700)

# Measured 2026-08-09 at 390x844 signed out: 268,820 B over 4 files.
# Headroom for subset drift, not for adding a family — adding one should make
# you re-read the payload table in base.html and decide deliberately.
MAX_FONT_BYTES = 285_000

# Both viewports are checked. The hero shloka is `hidden sm:block`, so it is
# display:none at 390 and only the desktop pass exercises it. A node that is
# not painted is SKIPped rather than passed — CDP reports no fonts for it, and
# reading that empty list as "no violation" is how this gate would go hollow.
VIEWPORTS = (390, 1280)


def check_font_link_statically() -> list[str]:
    """Assert base.html still requests a Devanagari sans at 400-700.

    Runs with no browser, no server and no network, so it is the one part of
    this gate that cannot be skipped into silence. Returns failure strings.
    """
    fails: list[str] = []
    html = BASE_HTML.read_text(encoding="utf-8")
    links = re.findall(r'href="(https://fonts\.googleapis\.com/css2\?[^"]+)"', html)
    if not links:
        return ["base.html requests no Google Fonts css2 stylesheet — the font "
                "<link> moved or was rewritten, and this check now verifies nothing."]

    families: dict[str, set[int]] = {}
    for link in links:
        # family=Noto+Sans+Devanagari:wght@400;500;600;700
        for spec in re.findall(r"family=([^&]+)", link):
            name, _, axis = spec.partition(":")
            name = name.replace("+", " ")
            weights = {int(w) for w in re.findall(r"\d{3}", axis)} or {400}
            families.setdefault(name, set()).update(weights)

    have = families.get(REQUIRED_DEVANAGARI_SANS)
    if have is None:
        fails.append(
            f"the font <link> no longer requests {REQUIRED_DEVANAGARI_SANS!r}. "
            f"Requested families: {sorted(families) or 'none'}. The Hindi UI "
            "renders at html[lang=hi]{font-size:108%} across 43 templates; "
            "without a Devanagari sans every bold Hindi heading falls back to "
            "a system font (#189, #235)."
        )
    else:
        missing = sorted(w for w in REQUIRED_SANS_WEIGHTS if w not in have)
        if missing:
            fails.append(
                f"{REQUIRED_DEVANAGARI_SANS} is requested at {sorted(have)} but "
                f"the templates need {list(REQUIRED_SANS_WEIGHTS)} — missing "
                f"{missing}. A weight that is not loaded is synthesised by the "
                "browser, which is what #189 looked like."
            )

    fails.extend(check_hardcoded_faces_are_loaded(set(families)))
    return fails


# Families a template may name without the <link> requesting them: generic CSS
# keywords, and system faces that are present because the OS has them. Anything
# else must be a face we actually load.
GENERIC_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded",
    "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto", "helvetica",
    "helvetica neue", "arial", "georgia", "times", "times new roman",
    "courier", "courier new", "cambria", "consolas", "menlo", "monaco",
    "noto color emoji", "apple color emoji", "segoe ui emoji", "inherit",
}


def check_hardcoded_faces_are_loaded(requested: set[str]) -> list[str]:
    """Every font family hardcoded in a template must be one we load.

    This exists because the same defect shipped twice inside one epic, and
    neither time did anything fail:

      #242 dropped Inter from the font <link>. Ten SVG labels across
      result.html, _south_indian_chart.html and matching_result.html still
      said `style="font-family: Inter, sans-serif"`, so they silently fell
      back to a system sans.

      ea0725b retired Crimson Pro. Six rules still named it — four in
      learn_article_base.html's inline <style>, which every one of the 76
      article bodies renders through, plus the loader caption and the Om
      glyph in base.html. All six fell back to a generic serif.

    A face in a `font-family:` declaration or an SVG `font-family=` attribute
    is invisible to a Tailwind class audit and invisible to the browser probe
    below unless that exact node happens to be sampled. It is only visible to
    a check that reads the templates and compares them to the <link>.

    Tailwind utilities are NOT checked here — those resolve through
    tailwind.config.js, which is a different failure mode with its own gate.
    """
    fails: list[str] = []
    loaded = {f.lower() for f in requested}

    # `font-family: X, Y;` in CSS and `font-family="X, Y"` in SVG attributes.
    decl = re.compile(r"""font-family\s*[:=]\s*["']?([^;"'}>]+)""", re.I)

    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Comments record the faces they replaced; a name in prose is not a
        # declaration. Blank them first or the gate fails on its own history.
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.S)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

        for stack in decl.findall(text):
            for raw in stack.split(","):
                name = raw.strip().strip("\"'").strip()
                if not name or name.startswith("{{") or name.startswith("var("):
                    continue
                low = name.lower()
                if low in GENERIC_FAMILIES or low in loaded:
                    continue
                fails.append(
                    f"{path.relative_to(REPO_ROOT)} hardcodes font-family "
                    f"{name!r}, which the font <link> does not request. "
                    f"Loaded: {sorted(requested)}. A named face that is not "
                    f"loaded falls back silently — nothing errors, the text "
                    f"just renders in something else. Either request it or "
                    f"name a face we already load."
                )
    return fails


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
    unreachable = False  # set when a viewport transferred zero web-font bytes

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

                # A viewport that loaded NO web fonts cannot tell you which
                # face painted anything — every [lang="sa"] node falls back to
                # a system font and every check above fails for a reason that
                # has nothing to do with this repo. That is COULD NOT VERIFY,
                # not FAIL, and the distinction is the same one acf27db had to
                # fix in verify_css_build: a gate that reports an unrunnable
                # environment as a defect trains people to ignore it.
                #
                # Seen in a sandbox where Chromium cannot reach fonts.gstatic
                # (ERR_CONNECTION_RESET, including through a proxy whose CA the
                # browser does not trust) while curl reaches it fine.
                if total == 0:
                    print("    COULD NOT VERIFY: no web font was transferred at "
                          "all — the browser could not reach the font host.")
                    unreachable = True
                    failures = []

                all_failures += [f"[{width}px] {f}" for f in failures]
                await ctx.close()
                print()
        finally:
            await browser.close()

    if unreachable and not all_failures:
        print("COULD NOT VERIFY: the page rendered without its web fonts, so")
        print("  nothing can be concluded about which face painted the shlokas.")
        print("  Check the browser's network access to fonts.googleapis.com.")
        print("-> SKIPPED (exit 2). This is NOT a pass — the check did not run.")
        return 2

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

    # Static check first, and its failure is final. It needs no browser and no
    # network, so it is the part that still runs when the rest cannot — and a
    # missing Devanagari sans is a defect whether or not a browser was
    # available to watch it happen.
    print("Static check — the font <link> requests a Devanagari sans\n")
    static_failures = check_font_link_statically()
    for f in static_failures:
        print(f"  FAIL {f}")
    if not static_failures:
        print(f"  ok   {REQUIRED_DEVANAGARI_SANS} requested at "
              f"{list(REQUIRED_SANS_WEIGHTS)}")
    print()
    if static_failures:
        print("FAIL")
        return 1

    return asyncio.run(run(args.url, tuple(args.width or VIEWPORTS)))


if __name__ == "__main__":
    sys.exit(main())
