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
    "src/astro_ai/templates/result.html",
    "src/astro_ai/templates/_south_indian_chart.html",
    # Both carry their palette inside an inline <style>, which is the same
    # blind spot as an SVG attribute: Tailwind never rewrites it, so a swap
    # leaves it behind. learn_index.html's category chips were exactly that —
    # #239 deferred them on purpose, #250 moved the screen and not the block,
    # and they stayed the last live purple on /learn until this listing.
    "src/astro_ai/templates/learn_index.html",
    "src/astro_ai/templates/muhurat_finder.html",
    # The third and largest inline <style>: the prose rules every one of the
    # 76 article bodies renders through. #239 deferred its purple, #250 moved
    # the CTA banner it was waiting on and left the block behind, so prose
    # links shipped astro-700 site-wide — and four rules kept naming
    # Crimson Pro after ea0725b retired it from the font request.
    "src/astro_ai/templates/learn_article_base.html",
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
    # The Vimshottari dasha strip's two component fills, named by the handoff
    # for this one component. Not palette roles — a spent period and the
    # current one are states of a single widget, and minting two bhagya tokens
    # for one strip would put them on a table that every other screen has to
    # read past. Declared in base.html's .dasha-seg--* rules and nowhere else.
    "#e6dac6": "spent Mahadasha segment fill (also the matching ring's track)",
    "#fbebd6": "current Mahadasha segment fill",
    # Semantic status colours in the panchang strip. Not brand colours.
    "#b91c1c": "Rahu Kaal warning",
    "#15803d": "Abhijit Muhurta positive",
    # The two article-prose callouts. Status, not brand: `callout-warning`
    # means "be careful", not "Shubh Bhagya". Scoped to
    # learn_article_base.html only — see LEGACY_SCOPE.
    "#fee2e2": "red-100 callout-warning fill",
    "#dc2626": "red-600 callout-warning rule",
    # #243, the two chart SVGs. The retrograde marker is a STATUS colour, not a
    # brand one — the palette has no amber, and "R" beside a planet means
    # retrograde, not "Shubh Bhagya". amber-800 rather than -700 because -700
    # is 4.10:1 on cream-2 and fails AA at the 9px this renders at.
    "#92400e": "amber-800 retrograde marker in the chart SVGs",
}

# WHICH files each LEGACY hex is actually allowed in.
#
# LEGACY used to apply to every MIGRATED file at once, and that quietly got
# weaker with each file added: listing learn_index.html and muhurat_finder.html
# handed them the entire stone ramp, so putting stone-500 back into
# muhurat_finder's inline <style> passed the gate. Measured, not assumed — that
# exact mutation was run and MISSED before this scope existed.
#
# So the allowance is per file, and the default is NOTHING. A file added to
# MIGRATED from here on gets no legacy hexes unless someone writes down which
# ones and why. The eight below keep the blanket allowance they were admitted
# under: they are emails, SVGs and a Python string whose stone neutrals and
# amber status colours are genuinely still correct.
_ALL_LEGACY = frozenset(k.lower() for k in LEGACY)
LEGACY_SCOPE: dict[str, frozenset[str]] = {
    "src/astro_ai/templates/cosmic_card.svg": _ALL_LEGACY,
    "src/astro_ai/templates/email/welcome.html": _ALL_LEGACY,
    "src/astro_ai/templates/email/daily_rashifal.html": _ALL_LEGACY,
    "src/astro_ai/templates/email/kundli_reading.html": _ALL_LEGACY,
    "src/astro_ai/routes/feedback.py": _ALL_LEGACY,
    "src/astro_ai/templates/index.html": _ALL_LEGACY,
    "src/astro_ai/templates/result.html": _ALL_LEGACY,
    "src/astro_ai/templates/_south_indian_chart.html": _ALL_LEGACY,
    # The named exception the scope exists for: this file gets FIVE legacy
    # hexes, not the whole list. They are the two semantic callouts in the
    # article prose — tip and warning — which are status colours, not brand
    # ones. Everything else in the block must be a bhagya token, and the
    # stone ramp in particular is NOT allowed here.
    "src/astro_ai/templates/learn_article_base.html": frozenset({
        "#fef3c7",  # amber-100, callout-tip fill (and the shlok card)
        "#fde68a",  # amber-200, shlok card border
        "#d97706",  # amber-600, callout-tip rule
        "#fee2e2",  # red-100, callout-warning fill
        "#dc2626",  # red-600, callout-warning rule
    }),
}

# The purple ramp. Still correct everywhere that has not migrated; never
# correct in a MIGRATED file.
ASTRO_RAMP = re.compile(
    r"#(?:f6f1fb|ece1f6|ddd6fe|c4b5fd|a78bfa|8b5cf6|7c3aed|6b21a8|581c87|3b0764"
    r"|a855f7|4c1d95|c084fc|faf5ff|f0e7fb|e9d5ff|9c7bc4)\b",
    re.I,
)

# `(?<!&)` is the whole reason this is not a plain hex pattern. An HTML
# NUMERIC CHARACTER REFERENCE looks exactly like one to a naive scanner:
# `&#128172;` (the speech-balloon emoji, used as a bare glyph in result.html)
# matches `#[0-9a-fA-F]{6}` on its first six digits, and the gate reported it as
# an off-palette colour. That is worse than a missed check — the obvious way to
# "fix" it is to add 128172 to LEGACY, which pollutes the allowlist with
# something that was never a colour and teaches the next person that entries
# there do not need to mean anything. A `#RRGGBB` is never preceded by `&`.
HEX = re.compile(r"(?<!&)#[0-9a-fA-F]{6}\b")


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
        allowed = LEGACY_SCOPE.get(rel, frozenset())
        for h, n, line in _hexes_in(path):
            counted += 1
            if h in by_value or h in allowed:
                continue
            known = " (it IS on LEGACY, but not for this file)" if h in _ALL_LEGACY else ""
            failures.append(
                f"  FAIL {rel}:{n} uses {h}, which is neither a bhagya token "
                f"nor allowed here{known}.\n"
                f"       {line[:100]}\n"
                f"       Either use a token from tailwind.config.js, or add it "
                f"to LEGACY and name this file in LEGACY_SCOPE, with the reason."
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


# #307: #43 set 12px as the mobile text floor, and three templates were still
# under it (tab bar labels on every page, 233 nodes on /learn/, the panchang
# strip). Files listed here have been brought up to the floor; the gate keeps
# them there. It is deliberately NOT applied to every template: index.html,
# panchang.html and other templates (see `git grep 'text-\[1[01]px\]'`) still
# carry 10-11px labels that are not yet decided, and a gate that fails today
# on files nobody is touching just gets switched off. Add a file here when its
# sub-12px text is fixed.
MIN_TEXT_PX = 12
TEXT_FLOOR_CLEAN = (
    "src/astro_ai/templates/_tab_bar.html",
    "src/astro_ai/templates/_panchang_strip.html",
    "src/astro_ai/templates/learn_index.html",
)
_SUB_FLOOR = re.compile(r"text-\[(\d+(?:\.\d+)?)px\]")


def gate_3_text_floor() -> list[str]:
    failures: list[str] = []
    for rel in TEXT_FLOOR_CLEAN:
        path = REPO_ROOT / rel
        if not path.exists():
            failures.append(f"  FAIL {rel} does not exist — update TEXT_FLOOR_CLEAN")
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in _SUB_FLOOR.finditer(line):
                if float(m.group(1)) < MIN_TEXT_PX:
                    failures.append(
                        f"  FAIL {rel}:{n} uses {m.group(0)}, under the "
                        f"{MIN_TEXT_PX}px mobile floor (#43, #307).\n"
                        f"       {line.strip()[:100]}\n"
                        f"       Use text-xs (12px) or larger."
                    )
    if not failures:
        print(f"  ok   no text under {MIN_TEXT_PX}px in the {len(TEXT_FLOOR_CLEAN)} "
              f"floor-clean file(s)")
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
        ("Gate 3 - no text under the 12px floor in cleaned files", gate_3_text_floor),
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
