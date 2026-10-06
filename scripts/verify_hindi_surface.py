#!/usr/bin/env python3
"""Gate: the 13 published Hindi URLs actually render Hindi — #124.

WHY NOTHING ELSE COVERS THIS

Eight QA rounds on #124 found English leaking onto Hindi pages five separate
times, and every one was found by a human reading a rendered page. Nothing in
the tree reads a rendered page:

  * `verify_english_surface.py` deliberately records NO body — it pins titles,
    canonicals and redirects on ENGLISH URLs. It structurally cannot see a
    Hindi leak.
  * `verify_lang_switch_browser.py` reads `<html lang>` and the root
    font-size. It says the document CLAIMS Hindi, not that it IS Hindi.
  * `tests/test_hindi_urls.py` asserts the `<title>` has >= 10 Devanagari
    characters. One element, on one page.
  * `test_i18n_symmetry.py` says a translation EXISTS and that no key is
    wholly unused. It cannot see a single lost call site for a key that is
    still used elsewhere — QA demonstrated exactly that: replacing one
    `t(lang, 'nav_rashifal_link')` with an English literal left all 194 tests
    green and put a live English string on 13 indexed Hindi URLs.

So: a count tells you a construct is still present; only a render tells you
the reader gets Hindi. This gate renders.

WHAT IT ENFORCES, per published Hindi URL

  1. No ENGLISH SENTINEL in <main>. The sentinels are the English strings this
     issue actually shipped by accident — "zodiac silhouette", "All 12 rashis",
     "Full birth chart", "Back to the form" — plus a generic sweep for runs of
     ASCII words long enough to be prose rather than a brand name or a
     technical term.
  2. A Devanagari FLOOR over <main>'s text, per page type — see FLOORS. The
     floor stops a page getting worse; it does not certify one as finished.

ALLOWED English, deliberately: "Shubh Bhagya", the sign names in parentheses
(`मेष (Aries)` is the intended bilingual form), "WhatsApp", "Lahiri", the
footer and nav (English site-wide by design), and anything inside <script>.

LOCAL BLINDNESS, stated because it is the same trap verify_english_surface.py
fell into: the 12 rashi URLs 503 on a dev box, because the .env default model
is decommissioned, so their <main> is the degraded card and this gate cannot
see a reverted block in the real body. Bite-tested and confirmed — reverting
`rashifal_kundli_desc` to English still PASSES here.

So this gate's real coverage locally is the HUB plus the sentinel sweep on all
13. The rashi pages' rendered body is covered by
`tests/test_hindi_urls.py::test_hindi_rashi_page_body_has_no_english`, which
stubs the provider and therefore sees the 200 path. The two together are the
check; neither alone is.

TOKEN COST — measure it before wiring this into anything automated.

This gate requests all 13 URLs, and the 12 rashi pages GENERATE on a cache
miss. Measured by QA round 9 with the provider instrumented: one cold request
is ~13,659 prompt chars ≈ 4,405 input tokens, so a full cold run is
**~53,000 input tokens — about 26% of the 200k TPD rashifal budget per
invocation**, with the first call putting 4,405 into an 8,000 TPM bucket.

That cost is invisible on a dev box only because the .env default model 404s
and every page degrades to 503 — the silent failure mode CLAUDE.md names. And
the QA convention of pointing BHAGYA_DAILY_CACHE_DIR at scratch *guarantees*
the cold path.

So: run it against production, or against a warm cache. It is deliberately NOT
in any CI workflow.

Needs a running server: pass --url. Exits 2 when it cannot reach one, never 0,
because an unrunnable gate must not read as a green one.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"
# Per-page floors, because the pages differ in what they legitimately contain.
#
# The 12 rashi pages are generated Hindi prose and measure 96%+; a 0.60 floor
# there means a reverted block fails immediately.
#
# The /hi/rashifal HUB is 24% today and that is NOT a leak this gate should
# hide: it carries a ~4-paragraph English SEO explainer ("How Bhagya's
# Rashifal is different"), PRE-EXISTING on both origin/main and the #124
# branch. Localising it means composing four paragraphs of Hindi that no
# native reader has checked, and CLAUDE.md is explicit that composed Hindi
# needs review — shipping a machine-translated explainer onto an indexed page
# is worse than leaving it English and saying so. Tracked separately.
#
# So the hub's floor is set just under its measured value: this gate stops the
# page getting WORSE, and does not certify it as finished. The sentinel check
# above is what catches a precise regression.
FLOORS = {"hub": 0.20, "rashi": 0.60}


# English strings that actually leaked onto a Hindi page during #124.
# Nav labels that ARE localised. Their Hindi forms must be PRESENT; absence
# means a t() call site reverted to an English literal. Filled from i18n at
# run time so the gate cannot drift from the table.
# nav_rashifal_link only: it is the key QA's mutation targeted and it renders
# in the top nav on EVERY page including the degraded 503. nav_home was tried
# and dropped — it is a breadcrumb label the error page does not render, so it
# produced a false positive on all 12 rashi URLs.
NAV_KEYS = ("nav_rashifal_link",)
# English labels that must NOT appear inside <nav aria-label="Main"> on a
# Hindi page. The top nav is localised; the footer and bottom tab bar are not.
NAV_ENGLISH = ("Rashifal", "Panchang", "Matching", "Kundli", "Muhurat")

SENTINELS = [
    "zodiac silhouette", "All 12 rashis", "Full birth chart",
    "Back to the form", "Open full page", "Try again",
    "Reading not ready yet", "High demand right now", "Unknown rashi",
    "daily Vedic horoscope", "Want a deeper reading",
    "Tithi, nakshatra", "Share on WhatsApp", "Today's Panchang",
    "Free Janma Kundli",
    # the aria-label that shipped on 12 tiles of the indexed Hindi hub
    "Reveal today's reading",
]

# Bilingual-by-design or brand/technical, so not a leak.
ALLOWED = re.compile(
    r"Shubh Bhagya|WhatsApp|Lahiri|Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra"
    r"|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces|Mesha|Vrishabha|Mithuna"
    r"|Karka|Simha|Kanya|Tula|Vrishchika|Dhanu|Makara|Kumbha|Meena|Rashifal"
    r"|Panchang|Kundli|Choghadiya|Abhijit|Rahu"
)


def _region_attr(html: str, tag: str, attr: str) -> str:
    """The region for the element carrying `attr` — `<nav aria-label="Main">`.

    Needed because a plain tag search finds the first `<nav` in the document,
    which is a CSS rule inside a <style> block.
    """
    m = re.search(rf"<{tag}\b[^>]*{re.escape(attr)}[^>]*>(.*?)</{tag}>", html, re.S | re.I)
    return m.group(1) if m else ""


def _region(html: str, tag: str) -> str:
    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, re.S | re.I)
    return m.group(1) if m else ""


def _visible(fragment: str) -> str:
    """Text PLUS the attribute values a reader or screen reader is given.

    Stripping tags to get the text drops `alt`, `title`, `aria-label` and
    `placeholder` entirely — and those are exactly where leaks hid. The first
    version of this gate did only the strip, so twelve English `alt`s sat
    inside <main> on the Hindi hub while it reported PASS, with
    "zodiac silhouette" as entry #1 of its own SENTINELS list. The same
    blindness was found and fixed in the pytest test one commit earlier and
    left here; QA round 9 caught it as the third instance of the pattern.
    """
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    attrs = " ".join(
        re.findall(r'(?:alt|title|aria-label|placeholder)="([^"]*)"', body)
    )
    text = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", text + " " + attrs).strip()


def _english_prose(text: str) -> list[str]:
    """Runs of ASCII words long enough to be prose rather than a name.

    This is the generic sweep the docstring has always promised and the code
    did not have — `ALLOWED` was defined and never referenced, the fossil of
    it. Measured consequence while it was missing: a 19-word English paragraph
    injected into the hub's <main> moved the Devanagari share 24% -> 22%,
    stayed above the floor, and the gate reported `leaks=0`.

    Four or more consecutive ASCII words, after removing the bilingual and
    brand/technical vocabulary that is English on a Hindi page BY DESIGN.
    """
    stripped = ALLOWED.sub(" ", text)
    runs = re.findall(r"(?:\b[A-Za-z][A-Za-z'’-]{1,}\b[ ,;:]{1,3}){3,}\b[A-Za-z][A-Za-z'’-]{1,}\b",
                      stripped)
    return [r.strip() for r in runs if len(r.split()) >= 4]


def _devanagari_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "ऀ" <= c <= "ॿ") / len(letters)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=DEFAULT_BASE)
    args = ap.parse_args()

    sys.path.insert(0, "src")
    try:
        from astro_ai import hindi_pages
    except ImportError as e:
        print(f"COULD NOT VERIFY: {e}")
        return 2

    from astro_ai.i18n import translate as _t

    NAV_EXPECTED = {k: _t("hi", k) for k in NAV_KEYS}

    paths = sorted(hindi_pages.HINDI_PUBLISHED)
    hindi_urls = [hindi_pages.hindi_url(p) for p in paths]

    print(f"Hindi surface (#124) — {len(hindi_urls)} published URLs, reading <main>\n")
    problems: list[str] = []
    checked = 0

    for url in hindi_urls:
        full = args.url + url
        try:
            with urllib.request.urlopen(full, timeout=60) as r:
                html = r.read().decode("utf-8", "replace")
                code = r.status
        except urllib.error.HTTPError as e:
            html = e.read().decode("utf-8", "replace")
            code = e.code
        except Exception as e:
            print(f"COULD NOT VERIFY: {full} unreachable ({e})")
            return 2

        main = _region(html, "main")
        text = _visible(main)
        share = _devanagari_share(text)
        hits = [s for s in SENTINELS if s in text]
        prose = _english_prose(text)

        # The localised nav labels, asserted POSITIVELY by presence.
        #
        # A negative sweep over <nav> was tried and was wrong twice: the regex
        # matched a <style> block containing `nav.sticky {`, and the only real
        # <nav> element is the bottom tab bar, which IS deliberately English
        # along with the footer. The top nav is not inside a <nav> at all.
        #
        # So instead: the Hindi forms of the nav labels must appear in the
        # document. That is what catches QA's nav_rashifal_link mutation —
        # replacing one t() call with an English literal put live English on
        # all 13 URLs while 196 tests stayed green, and a presence check sees
        # it where a region sweep could not.
        # The TOP NAV, read as its own region.
        #
        # Three wrong versions before this one, each caught by a bite test:
        #   1. sweep <nav> — the regex matched a <style> block containing
        #      `nav.sticky {`, and the first real <nav> is the bottom tab bar,
        #      which IS deliberately English along with the footer.
        #   2. assert the Hindi label is present in the document — passes,
        #      because राशिफल appears in the <title> and the breadcrumbs of
        #      every rashifal page, so it cannot isolate the nav.
        #   3. read the expectation out of i18n — self-defeating: a mutated
        #      TABLE value is "found" in an English page.
        #
        # `<nav aria-label="Main">` is the top nav specifically. An English
        # label inside it is a lost call site; the Devanagari check on the
        # expected value additionally catches the table reverting.
        nav_main = _visible(_region_attr(html, "nav", 'aria-label="Main"'))
        missing_nav = [k for k, want in NAV_EXPECTED.items()
                       if not any("\u0900" <= c <= "\u097f" for c in want)]
        missing_nav += [e for e in NAV_ENGLISH if e in nav_main]

        # A degraded page is still required to be Hindi — that was defect F9 —
        # but its body is short, so the floor is only applied to a 200.
        if hits:
            problems.append(f"{url} [{code}]: English in <main>: {hits}")
        if prose:
            problems.append(
                f"{url} [{code}]: English prose in <main>: {prose[:2]}"
            )
        if missing_nav:
            problems.append(
                f"{url} [{code}]: localised nav label(s) absent from the page: "
                f"{missing_nav} — a t() call site has been replaced with an "
                f"English literal"
            )
        kind = "rashi" if re.match(r"^/hi/rashifal/[a-z]+$", url) else "hub"
        floor = FLOORS[kind]
        if code == 200 and share < floor:
            problems.append(
                f"{url} [200]: Devanagari share {share:.0%} is below the "
                f"{floor:.0%} {kind} floor — a block has reverted to English"
            )
        checked += 1
        print(f"  {url:<28} [{code}] devanagari={share:5.0%} "
              f"sentinels={len(hits)} prose={len(prose)} nav={len(missing_nav)}")

    if problems:
        print(f"\nFAIL — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        print("\nAn English string inside <main> on an indexed Hindi URL is the defect\n"
              "this gate exists for. Route it through t(lang, …).")
        return 1

    print(f"\nPASS ({checked} Hindi URLs: no English sentinel in <main>, "
          f"Devanagari above each page type's floor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
