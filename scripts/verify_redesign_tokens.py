#!/usr/bin/env python3
"""Gate: the redesign hexes Tailwind cannot see must still match the tokens.

WHY THIS EXISTS
---------------
The redesign palette lives in one place — `tailwind.config.js`, under
`theme.extend.colors.bhagya` (#238). Every screen that migrates picks up its
colours from there through utility classes, and `verify_css_build.py` proves
the built stylesheet is a fresh build of that config.

Four files cannot work that way, and #239 migrated all four:

    templates/cosmic_card.svg          SVG attributes, not classes
    templates/email/welcome.html       email clients strip <style>
    templates/email/daily_rashifal.html          "
    templates/email/kundli_reading.html          "
    routes/feedback.py                 an HTML string built in Python

Tailwind's scanner never emits a rule for any of them, so the hexes are
written out literally. Literal copies of a single source of truth drift — that
is the whole reason this repo has a `verify_*` sweep at all. Two failure modes,
both of which this gate makes impossible to ship quietly:

  Gate 1 - every hex in these files is either a bhagya token read live out of
      `tailwind.config.js`, or on the LEGACY list below with a reason. A hex
      that is neither is a hand-mixed colour: either a typo, or someone
      eyeballing a shade instead of using the palette. It also catches the
      reverse drift — change a token's value in the config and the literal
      here stops matching it, which is the failure this file mainly guards.

  Gate 2 - none of the `astro` purple ramp appears in a migrated file. That
      ramp is still live and still correct on every screen that has NOT
      migrated, so it cannot simply be deleted; the check is positional, not
      global. Purple reappearing HERE means a page was copy-pasted from an
      un-migrated screen, which is precisely how a half-migrated brand ships.

WHAT THIS DOES NOT DO
---------------------
It says nothing about the templates still on the purple ramp — `result.html`,
`index.html`, `_south_indian_chart.html`, `matching_result.html`,
`learn_index.html`, `learn_article_base.html` and the 76 `/learn` hero SVGs
(#259). Those deliberately still carry `#6b21a8` and friends, because the
utility classes beside them do too. Add a file to MIGRATED when its screen
lands, and this gate starts holding it to the palette.

It also does not check contrast — `scripts/verify_contrast.py` does that for
Tailwind utilities, and it cannot see these files either. The measured ratios
for the email colours are recorded in `email/daily_rashifal.html`'s header
comment; they are arithmetic on the same tokens this gate pins.

USAGE
    uv run python scripts/verify_redesign_tokens.py

EXIT CODES
    0  PASS
    1  FAIL — a hex drifted, or purple came back
    2  COULD NOT VERIFY — tailwind.config.js is missing or has no bhagya block
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "tailwind.config.js"

# Files that have migrated to the redesign palette and carry hexes Tailwind
# cannot reach. Extend as screens land — that is the point of the list.
#
# #242 widened what "cannot reach" means. The first five entries are files
# Tailwind cannot see AT ALL — an SVG, three emails, a Python string. index.html
# is not like that: its utility classes are scanned normally and are held to the
# palette by verify_contrast.py. What is unreachable is the 22 literal hexes
# inside its two inline SVGs (the sample-chart preview and the rashifal
# diamond), which are attribute values, not classes. Those are exactly the kind
# of colour that gets left behind on a palette swap — #239 explicitly deferred
# them to this issue — so the file is listed here to pin them.
MIGRATED = (
    "src/astro_ai/templates/cosmic_card.svg",
    "src/astro_ai/templates/email/welcome.html",
    "src/astro_ai/templates/email/daily_rashifal.html",
    "src/astro_ai/templates/email/kundli_reading.html",
    "src/astro_ai/routes/feedback.py",
    "src/astro_ai/templates/index.html",
)

# Hexes in the migrated files that are NOT bhagya tokens and are allowed to
# stay. Every entry needs a reason, because an allowlist without one is just a
# way of turning a gate off.
LEGACY: dict[str, str] = {
    # Neutrals the redesign has no token for. These are Tailwind stone values
    # already in use across the emails for body copy and hairlines; they read
    # correctly on the new cream and were out of #239's scope.
    "#1c1917": "stone-900 body text",
    "#44403c": "stone-700 long-form copy",
    "#57534e": "stone-600 secondary copy",
    "#78716c": "stone-500 footer meta",
    "#a8a29e": "stone-400 fine print",
    "#e7e5e4": "stone-200 card border",
    "#f5f5f4": "stone-100 footer rule",
    "#f3f0eb": "warm hairline above the kundli-reading footer",
    "#ffffff": "card fill and text on night",
    # The amber family on the shlok and festival panels, and the cosmic card's
    # ornament. Deliberately untouched by #239: it already reads warm against
    # the new cream, and re-authoring the card's three-stop metallic gradient
    # is art work rather than a token swap. NOT the `gold` token, which is
    # night-only.
    "#fef3c7": "amber-100 panel fill",
    "#fde68a": "amber-200 panel border",
    "#fef08a": "cosmic card gold gradient, inner stop",
    "#f59e0b": "amber-500 glyphs and the card's flag bar",
    "#d97706": "amber-600 festival rule",
    "#b45309": "amber-700 no-sunrise notice",
    "#92400e": "amber-800 eyebrow on the amber panels",
    "#a16207": "yellow-700 caption on the cosmic card",
    "#78350f": "amber-900 caption and gold gradient outer stop",
    # Semantic status colours in the panchang strip. Not brand colours.
    "#b91c1c": "Rahu Kaal warning",
    "#15803d": "Abhijit Muhurta positive",
}

# The purple ramp. Still correct everywhere that has not migrated; never
# correct in a MIGRATED file.
ASTRO_RAMP = re.compile(
    r"#(?:f6f1fb|ece1f6|ddd6fe|c4b5fd|a78bfa|8b5cf6|7c3aed|6b21a8|581c87|3b0764"
    r"|a855f7|4c1d95|c084fc|faf5ff|f0e7fb|e9d5ff|9c7bc4)\b",
    re.I,
)

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


class ConfigUnavailable(RuntimeError):
    """Exit 2, not a FAIL — a gate that could not run is not a pass."""


def bhagya_tokens() -> dict[str, str]:
    """Read the bhagya block out of tailwind.config.js, live.

    Deliberately parsed from the config rather than restated here. A table in
    this file would be a third copy of the palette, and a gate that carries its
    own copy of the thing it is checking cannot detect drift in that thing —
    the defect `scripts/mutate_behaviour_suite.py` was written to catch.
    """
    if not CONFIG.exists():
        raise ConfigUnavailable(f"{CONFIG.relative_to(REPO_ROOT)} does not exist")
    text = CONFIG.read_text(encoding="utf-8")
    m = re.search(r"bhagya:\s*\{(.*?)\n\s*\},", text, re.S)
    if not m:
        raise ConfigUnavailable(
            "no `bhagya: { ... }` block in tailwind.config.js — the redesign "
            "palette moved or was removed, and this gate cannot check anything"
        )
    tokens = {
        name.strip("'\""): value.lower()
        for name, value in re.findall(
            r"([\w'-]+):\s*'(#[0-9a-fA-F]{6})'", m.group(1)
        )
    }
    if not tokens:
        raise ConfigUnavailable("the bhagya block parsed to zero tokens")
    return tokens


def _blank(m: re.Match[str]) -> str:
    """Replace a comment with newlines only, so line numbers stay honest."""
    return "\n" * m.group(0).count("\n")


def _strip_comments(path: Path) -> str:
    """The file with its comments blanked out, line numbering preserved.

    Comments are stripped before either gate looks at the text, and that is
    load-bearing rather than tidiness: the header comments in these files
    RECORD the purple they replaced ("cream #FAF6EF ... was #faf7f2"). Scanning
    raw text failed all three of them, which would have taught the next person
    to delete the provenance to get the gate green — the opposite of what this
    repo wants. A hex only counts if it can reach a renderer.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        return "\n".join(
            "" if line.lstrip().startswith("#") else line
            for line in text.splitlines()
        )
    text = re.sub(r"\{#.*?#\}", _blank, text, flags=re.S)     # Jinja
    text = re.sub(r"<!--.*?-->", _blank, text, flags=re.S)    # HTML
    text = re.sub(r"/\*.*?\*/", _blank, text, flags=re.S)     # CSS
    return text


def _hexes_in(path: Path) -> list[tuple[str, int, str]]:
    """(hex, line number, the line) for every 6-digit hex a renderer can see."""
    out = []
    for n, line in enumerate(_strip_comments(path).splitlines(), 1):
        for h in HEX.findall(line):
            out.append((h.lower(), n, line.strip()))
    return out


def gate_1_every_hex_is_a_token(tokens: dict[str, str]) -> list[str]:
    by_value = {v: k for k, v in tokens.items()}
    failures: list[str] = []
    counted = 0
    for rel in MIGRATED:
        path = REPO_ROOT / rel
        if not path.exists():
            failures.append(f"  FAIL {rel} does not exist — update MIGRATED")
            continue
        for h, n, line in _hexes_in(path):
            counted += 1
            if h in by_value or h in {k.lower() for k in LEGACY}:
                continue
            failures.append(
                f"  FAIL {rel}:{n} uses {h}, which is neither a bhagya token "
                f"nor on the LEGACY list.\n"
                f"       {line[:100]}\n"
                f"       Either use a token from tailwind.config.js, or add it "
                f"to LEGACY with the reason it is not one."
            )
    if not failures:
        print(f"  ok   {counted} hex literal(s) across {len(MIGRATED)} file(s) "
              f"all resolve to a token or a documented legacy value")
    return failures


def gate_2_no_purple_returns() -> list[str]:
    failures: list[str] = []
    for rel in MIGRATED:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        for n, line in enumerate(_strip_comments(path).splitlines(), 1):
            if ASTRO_RAMP.search(line):
                failures.append(
                    f"  FAIL {rel}:{n} carries a colour from the astro purple "
                    f"ramp:\n       {line.strip()[:100]}\n"
                    f"       This file has migrated. Purple here means it was "
                    f"copied from a screen that has not."
                )
    if not failures:
        print(f"  ok   no astro-ramp purple in any of the {len(MIGRATED)} "
              f"migrated files")
    return failures


def main() -> int:
    print("Redesign token verification")
    print(f"  config : {CONFIG.relative_to(REPO_ROOT)}")
    try:
        tokens = bhagya_tokens()
    except ConfigUnavailable as err:
        print(f"COULD NOT VERIFY: {err}")
        print("-> SKIPPED (exit 2). This is NOT a pass — the check did not run.")
        return 2
    print(f"  tokens : {len(tokens)} ({', '.join(sorted(tokens))})")
    print()

    failures: list[str] = []
    for title, fn in (
        ("Gate 1 - every hex in a migrated file is a token", lambda: gate_1_every_hex_is_a_token(tokens)),
        ("Gate 2 - the astro purple ramp has not come back", gate_2_no_purple_returns),
    ):
        print(title)
        found = fn()
        for line in found:
            print(line)
        print("  -> " + ("FAIL" if found else "PASS"))
        print()
        failures += found

    print("PASS" if not failures else f"FAIL ({len(failures)} problem(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
