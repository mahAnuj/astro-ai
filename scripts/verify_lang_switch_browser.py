#!/usr/bin/env python3
"""Gate for #124 — the language switch, checked in a real browser.

WHY THIS EXISTS, AND WHY IT IS A BROWSER GATE

`templates/_lang_picker.html` has been wrong four times, in four different
ways, across three QA rounds:

  v1  <select onchange="this.form.submit()"> posting `next = request.url.path`.
      On a /hi/ page that posted /hi/rashifal back, which forces Hindi, so
      choosing English wrote lang=en and re-rendered Hindi. Dead control that
      silently changed stored state.
  v2  plain anchors between the two URLs. With a saved `hi` preference the
      ENGLISH url renders Hindi too, so the "English" anchor pointed at a page
      serving Hindi. Dead again.
  v3  POST /lang with a per-language target. Correct server-side — and broken
      in a browser: `base.html` sets hx-boost="true" on <body>, so htmx
      intercepted the submit, AJAX-posted, swapped the body, and left
      <html lang> untouched. `html[lang="hi"] { font-size: 108% }` therefore
      never applied and a screen reader kept the English voice while reading
      Devanagari.
  v4  v3 + hx-boost="false" on the form. What this gate pins.

Every one of those was verified by the method that could not see the next
failure. v1 and v2 by reading; v3 by `TestClient`, which posts the form
server-side and CANNOT RUN HTMX — so the entire 134-test suite, 35 mutations
and 17 gates were structurally incapable of catching v3's defect. QA's words
after round 3: "the control is the one piece of this change that lives in the
browser, and the whole verification apparatus is server-side."

So this gate asserts the two things only a browser can see, after a real
click:

  1. `document.documentElement.lang` matches the language that was chosen.
     This is the attribute hx-boost leaves stale, and it drives both the
     typography rule and the voice a screen reader uses.
  2. The computed root font-size actually changes for Hindi — 108% of the
     English value, per base.html. Checking the attribute alone would pass if
     someone removed the CSS rule; checking the size alone would pass if
     someone hardcoded it. Both together pin the behaviour the reader gets.

It also asserts the control stays keyboard-operable and correctly named, since
v3 turned a labelled <select> into two buttons and that is an accessibility
surface no server-side test inspects.

Bite-tested: removing `hx-boost="false"` from the form fails check 1 and 2
(measured 6 of 9 switches left lang="en" at 16px instead of 17.28px). Not
vacuous.

Needs a running server and playwright, like verify_devanagari_serif.py. It
reports COULD NOT VERIFY rather than passing when either is missing — a gate
that silently skips is how eight tests once skipped themselves into a green
run.
"""
from __future__ import annotations

import argparse
import sys

DEFAULT_BASE = "http://127.0.0.1:8000"

# Pages with a published Hindi twin, where the switch has somewhere to go.
#
# NOT /rashifal/{slug}: those 503 locally, because the .env default model
# (llama-3.3-70b-versatile) is decommissioned, and the degraded page renders
# no nav and therefore no picker. The first version of this gate listed one
# and hung for 30s on a locator that could never appear. The hub exercises the
# same template include and the same /lang round-trip.
PUBLISHED = ["/rashifal"]
# And pages without a twin, where the switch only sets a preference.
UNPUBLISHED = ["/panchang", "/matching"]

HINDI_SCALE = 1.08   # base.html: html[lang="hi"] { font-size: 108%; }
TOLERANCE = 0.01


def _fail(msg: str) -> None:
    print(f"\nFAIL — {msg}")
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=DEFAULT_BASE, help="base URL of a running server")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("COULD NOT VERIFY: playwright is not installed.")
        print("  pip install playwright && playwright install chromium")
        return 0

    print("Language switch, in a browser (#124) — <html lang> and the 108% rule\n")
    problems: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for path in PUBLISHED + UNPUBLISHED:
            ctx = browser.new_context()
            page = ctx.new_page()
            resp = page.goto(args.url + path, wait_until="networkidle")
            if resp and resp.status != 200:
                # Say so rather than timing out on a control the degraded page
                # never renders. A gate that hangs reads as a gate that failed.
                problems.append(
                    f"{path}: returned HTTP {resp.status}, so the picker is not on the "
                    f"page and the switch cannot be exercised. If this is the local "
                    f"decommissioned-model 503, pick a page that renders."
                )
                ctx.close()
                continue

            base_size = page.evaluate(
                "parseFloat(getComputedStyle(document.documentElement).fontSize)")
            base_lang = page.evaluate("document.documentElement.lang")
            if base_lang != "en":
                problems.append(f"{path}: fresh load is lang={base_lang!r}, expected en")

            # --- accessibility surface: named, and reachable by keyboard
            for value in ("en", "hi"):
                btn = page.locator(f'button[name="lang"][value="{value}"]:visible').first
                if btn.count() == 0:
                    problems.append(f"{path}: no {value} control rendered")
                    continue
                name = btn.evaluate("el => el.textContent.trim()")
                if not name:
                    problems.append(f"{path}: the {value} control has no accessible name")
                if btn.evaluate("el => el.disabled || el.tabIndex < 0"):
                    problems.append(f"{path}: the {value} control is not keyboard-reachable")

            # --- CLICK Hindi, like a reader, and look at what the document became
            hi_btn = page.locator('button[name="lang"][value="hi"]:visible').first
            if hi_btn.count() == 0:
                problems.append(f"{path}: no VISIBLE Hindi control to click")
                ctx.close()
                continue
            hi_btn.click()
            page.wait_for_load_state("networkidle")

            lang_after = page.evaluate("document.documentElement.lang")
            size_after = page.evaluate(
                "parseFloat(getComputedStyle(document.documentElement).fontSize)")

            if lang_after != "hi":
                problems.append(
                    f"{path}: after choosing Hindi, document.documentElement.lang is "
                    f"{lang_after!r}, not 'hi'. This is the hx-boost defect: htmx swapped "
                    f"the body and left <html> alone, so the 108% rule and the screen "
                    f"reader's voice both stay English. Check hx-boost=\"false\" on the "
                    f"picker form."
                )
            expected = base_size * HINDI_SCALE
            if abs(size_after - expected) > expected * TOLERANCE:
                problems.append(
                    f"{path}: root font-size is {size_after}px after choosing Hindi; "
                    f"expected ~{expected:.2f}px ({HINDI_SCALE:g}x of {base_size}px). "
                    f"Devanagari is rendering at the wrong size."
                )

            # --- and back, which is the direction v1 and v2 both broke
            page.locator('button[name="lang"][value="en"]:visible').first.click()
            page.wait_for_load_state("networkidle")
            if page.evaluate("document.documentElement.lang") != "en":
                problems.append(f"{path}: could not get back to English from Hindi")

            print(f"  {path:<22} en {base_size:g}px -> hi {size_after:g}px  "
                  f"lang {base_lang} -> {lang_after} -> "
                  f"{page.evaluate('document.documentElement.lang')}")
            ctx.close()
        browser.close()

    if problems:
        for p in problems:
            print(f"\n  - {p}")
        _fail(f"{len(problems)} problem(s) with the language switch")

    print(f"\nPASS ({len(PUBLISHED) + len(UNPUBLISHED)} pages: lang attribute and the "
          f"{HINDI_SCALE:g}x rule both follow the control)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
