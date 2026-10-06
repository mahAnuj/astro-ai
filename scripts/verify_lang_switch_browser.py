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
  v4  v3 + hx-boost="false". Fixed the stale lang, and its english_url() call
      for `next` normalised the path, adding a second redirect hop to every
      switch on the 77 /learn/ URLs (76 articles + the hub, measured).
  v5  REVERTED to main's <select>, with only `next` changed. The <select> is
      immune to v3 entirely: `this.form.submit()` is programmatic and fires no
      submit event, so htmx never intercepts it. The button group was better in
      real ways and should return as its own change — see the note in
      _lang_picker.html.

This gate pins v5, and keeps the hx-boost check live because the button group
is expected back.

Every one of those was verified by the method that could not see the next
failure. v1 and v2 by reading; v3 by `TestClient`, which posts the form
server-side and CANNOT RUN HTMX — so the entire 134-test suite, 35 mutations
and 17 gates were structurally incapable of catching v3's defect. QA's words
after round 3: "the control is the one piece of this change that lives in the
browser, and the whole verification apparatus is server-side."

So this gate asserts the two things only a browser can see, after a real
click:

  0. The switch lands on the right URL — the /hi twin where one exists, the
     same page where it does not — in ONE redirect hop. The hop count is what
     catches a `next` that has been normalised (lowercased, trailing slash
     stripped), which is why a trailing-slash page is in the list below. Checking language alone passed a tree whose
     `next` was hardcoded to /about: right language, wrong page.
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
UNPUBLISHED = [
    "/panchang",
    "/matching",
    # A TRAILING-SLASH url, deliberately. Without one the gate passed with the
    # picker's `next` reverted to the normalising english_url() — /rashifal,
    # /panchang and /matching are all identity under it, so the extra redirect
    # hop on the 77 /learn/ URLs was invisible here. That was the fourth way
    # this gate has been wrong (QA round 5, N1).
    "/learn/",
]

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
        # EXIT 2, not 0. playwright is in no dependency group in
        # pyproject.toml, so `uv sync` produces an environment without it —
        # which means returning 0 here made this gate a silent PASS for
        # everyone who is not running it from a hand-built venv. That is the
        # eight-tests-skipped-themselves-green pattern, re-shipped inside the
        # file written to prevent it (QA 2026-10-04).
        # verify_devanagari_serif.py returns 2 for the same reason; matching it.
        return 2

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

            # htmx comes from a third party (base.html: unpkg.com), and this
            # gate's entire subject is what htmx DOES to the submit. With htmx
            # unreachable — a blocked CDN, an unpkg outage, a sandboxed runner,
            # a CSP change — the form does a native POST, <html lang> updates,
            # and this gate PASSED a tree that was broken for every real user.
            # Measured both ways (QA 2026-10-04): htmx reachable -> FAIL 6
            # problems; htmx unreachable -> PASS. So the precondition is now
            # asserted, not assumed.
            # WAIT for htmx rather than sampling once. Each page gets a fresh
            # context, so htmx is re-fetched from unpkg with no HTTP cache and
            # the first one or two lose the race — QA round 10 measured this
            # gate at ~50% flaky across five runs against a healthy server,
            # with unpkg reachable in 0.12s throughout. A gate that fails
            # randomly cannot be wired into anything.
            try:
                page.wait_for_function("typeof window.htmx !== 'undefined'",
                                       timeout=15000)
            except Exception:
                pass
            if not page.evaluate("typeof window.htmx !== 'undefined'"):
                problems.append(
                    f"{path}: htmx did not load, so hx-boost is inert and this "
                    f"gate cannot observe what it exists to check. Not a PASS — "
                    f"check network access to unpkg.com."
                )
                ctx.close()
                continue

            base_size = page.evaluate(
                "parseFloat(getComputedStyle(document.documentElement).fontSize)")
            base_lang = page.evaluate("document.documentElement.lang")
            if base_lang != "en":
                problems.append(f"{path}: fresh load is lang={base_lang!r}, expected en")

            # --- accessibility surface
            sel = page.locator('select[name="lang"]:visible').first
            if sel.count() == 0:
                problems.append(f"{path}: no visible language control rendered")
                ctx.close()
                continue
            if not sel.evaluate("el => el.getAttribute('aria-label') || el.labels.length"):
                problems.append(f"{path}: the language control has no accessible name")
            if sel.evaluate("el => el.disabled || el.tabIndex < 0"):
                problems.append(f"{path}: the language control is not keyboard-reachable")
            opts = sel.evaluate("el => Array.from(el.options).map(o => o.value)")
            if sorted(opts) != ["en", "hi"]:
                problems.append(f"{path}: options are {opts}, expected en and hi")

            # --- CLICK Hindi, like a reader, and look at what the document became
            # expect_navigation, not a bare select_option: `onchange` fires
            # this.form.submit() synchronously, so the very next evaluate()
            # races the navigation and dies with "Execution context was
            # destroyed". With hx-boost active there is no document navigation
            # at all, which is the defect — so fall back to networkidle rather
            # than requiring one.
            # Count the redirect chain, not just where it ends. F3 was a
            # NORMALISED `next` adding a second hop on every trailing-slash
            # URL — the reader still arrived, so a landing-URL check could not
            # see it. redirected_from walks the chain backwards.
            hops = {"n": 0}

            def _count(resp):
                # SAME-ORIGIN only. The first version counted unpkg.com's own
                # 301 for the htmx script, so every page looked like it took
                # an extra hop and the healthy tree failed. An external CDN
                # redirect is not part of the switch.
                if 300 <= resp.status < 400 and resp.url.startswith(args.url):
                    hops["n"] += 1

            page.on("response", _count)
            try:
                with page.expect_navigation(timeout=5000):
                    sel.select_option("hi")
            except Exception:
                pass
            page.wait_for_load_state("networkidle")
            page.remove_listener("response", _count)

            # POST /lang -> 303 to the target is the one legitimate hop.
            if hops["n"] > 1:
                problems.append(
                    f"{path}: the switch took {hops['n']} redirect hops, expected 1. "
                    f"A normalised `next` (lowercased, trailing slash stripped) adds "
                    f"one — see strip_hi_prefix."
                )

            # WHERE it landed, not only what language it rendered. Without
            # this the gate passed with `next` hardcoded to /about: it read
            # lang="hi" and 17.28px on the wrong page and called it green.
            # QA found the same hole from the other side — removing the twin
            # redirect from POST /lang also passed. A language control that
            # teleports the reader is not working.
            landed = page.url.replace(args.url, "")
            expected_landing = (path if path in UNPUBLISHED
                                else "/hi" + path.rstrip("/"))
            if landed.split("?")[0].rstrip("/") != expected_landing.rstrip("/"):
                problems.append(
                    f"{path}: choosing Hindi landed on {landed!r}, expected "
                    f"{expected_landing!r}"
                )

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
            back = page.locator('select[name="lang"]:visible').first
            try:
                with page.expect_navigation(timeout=5000):
                    back.select_option("en")
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                # QA round 10 run 1 died here with an uncaught playwright
                # TimeoutError — a traceback that is neither PASS, FAIL nor
                # COULD NOT VERIFY. Record it as a problem instead.
                problems.append(
                    f"{path}: the page never went idle after switching back "
                    f"to English (network stall, not necessarily a defect — "
                    f"re-run before believing it)"
                )
            if page.evaluate("document.documentElement.lang") != "en":
                problems.append(f"{path}: could not get back to English from Hindi")
            back_landed = page.url.replace(args.url, "").split("?")[0]
            if back_landed.rstrip("/") != path.rstrip("/"):
                problems.append(
                    f"{path}: returning to English landed on {back_landed!r}, "
                    f"not back at {path!r}"
                )

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
