#!/usr/bin/env python3
"""Gate: text colours must actually be readable on the surfaces they sit on.

Why this exists. A redesign handoff arrived with a palette whose own README
correctly identified one contrast failure (gold #C8A44D on cream, 2.20:1) and
shipped three more it had not measured — a meta colour used 50 times at 9-14px
at 3.56:1, a placeholder at 2.39:1, and a body line at 4.29:1. All three are
below the 4.5:1 WCAG AA needs for normal text.

Measuring it against the CURRENT theme then found the same class of defect
already live: `placeholder-stone-400` is 2.52:1 on white and is used in seven
form inputs, and the design charter in base.html claims `text-stone-600`
"Passes WCAG AA at ~4.6:1" when it is really 7.14:1 — 4.6 is `stone-500`'s
figure, which the charter separately (and correctly) restricts to decorative
use. A wrong number in the design system's own source of truth.

Contrast is arithmetic. Nothing about it needs a human eye, and a palette
change is exactly the kind of edit where nobody re-runs the arithmetic. So:

  Gate 1  every placeholder-* utility used in a template passes AA on the
          surfaces an input can have (white, cream)
  Gate 2  every ratio the base.html design charter states out loud is true
  Gate 3  the declared text-on-surface pairs pass at their stated threshold,
          with `/[.NN]` utilities composited onto their surface first
  Gate 4  no template uses a translucent bhagya text utility that Gate 3 has
          not been told about

COLOURS COME FROM THE BUILT CSS, NOT FROM A TABLE HERE. `app.css` carries the
rgb() each utility actually emits, which covers config colours and Tailwind's
own defaults uniformly and cannot drift from what the browser receives. The
one thing this file declares is design INTENT — which colour is allowed on
which surface — because that is a decision, not a measurement.

WCAG 2.1 SC 1.4.3: 4.5:1 for normal text, 3.0:1 only for large text, where
large means >=24px, or >=18.66px when bold. None of the uses this gate covers
is large, so 4.5 is the bar throughout.

USAGE
    uv run python scripts/verify_contrast.py

EXIT CODES
    0  PASS
    1  FAIL — a check did not hold
    2  COULD NOT VERIFY — app.css is missing or unparseable. Not a pass: run
       `npm ci && npm run build:css` first.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILT_CSS = REPO_ROOT / "src/astro_ai/static/css/app.css"
TEMPLATES = REPO_ROOT / "src/astro_ai/templates"
BASE_HTML = TEMPLATES / "base.html"

AA_NORMAL = 4.5

# The surface every placeholder in this tree actually renders on, checked by
# reading all seven sites: learn_index.html:42 sets `bg-white` explicitly, and
# the other six sit inside `bg-white` cards (e.g. index.html:189). Tailwind's
# preflight makes only BUTTON-type inputs transparent — text, date and time
# inputs keep the browser's white default — so none of them inherits the cream
# page behind the card.
#
# bg-cream is deliberately NOT in this list, and the margin is the reason to
# say so out loud: placeholder-stone-500 is 4.80:1 on white but 4.49:1 on cream,
# which fails by a hundredth. If an input is ever placed directly on the page
# rather than inside a white card, add "bg-cream" here and expect it to fail —
# the placeholder would need to go a step darker.
INPUT_SURFACES = ("bg-white",)

# Design intent: which text utility is allowed on which surface, and why.
# Extend this when the redesign tokens land (#238) — that is the point of it.
#
# For whoever lands #238: the handoff palette ships three values that fail at
# the sizes it uses them, measured from the prototype's own inline styles.
# Corrected values, same hue, passing on both cream backgrounds:
#
#     muted-2      #8A8175 -> #6F675E   (was 3.56:1 / 3.13:1, now 5.16 / 4.54)
#                                        50 text uses at 9-14px
#     placeholder  #A9A096 -> #71675D   (was 2.39:1, now 5.13 / 4.52)
#                                        20 text uses at 10-15px
#     myth line    rgba(250,246,239,.45) -> .48 on night  (4.29:1 -> 4.71:1)
#
# The handoff's own README recommends #8A8175 as one of two safe colours on
# cream, which is how all three got through review. Add the new tokens to
# DECLARED_PAIRS as they land so the next palette edit is checked, not read.
DECLARED_PAIRS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("text-stone-900", ("bg-cream", "bg-white", "bg-stone-50", "bg-astro-50"), "body text"),
    ("text-stone-800", ("bg-cream", "bg-white", "bg-stone-50", "bg-astro-50"), "headings"),
    ("text-stone-600", ("bg-cream", "bg-white", "bg-stone-50", "bg-astro-50"), "informational meta"),
    ("text-astro-700", ("bg-cream", "bg-white"), "links and accents"),
    ("text-astro-800", ("bg-cream", "bg-white"), "emphasis"),
    ("text-white",     ("bg-astro-700", "bg-astro-800"), "text on primary fills"),

    # Redesign shell (#241). The nav and footer are night panels, so these are
    # the light-on-dark pairs — the opposite direction to everything above.
    # `gold` appears here and NOWHERE against a cream surface: it is 2.20:1 on
    # cream, which is the one contrast bug the handoff caught itself.
    ("text-bhagya-cream",   ("bg-bhagya-night",), "nav and footer text"),
    ("text-bhagya-saffron", ("bg-bhagya-night",), "logo, active nav, hover"),
    ("text-bhagya-gold",    ("bg-bhagya-night",), "ornament — night only"),
    # Dropdown panels fall onto the page, so they are a light surface even
    # though the bar they hang from is night.
    ("text-bhagya-ink-soft", ("bg-bhagya-cream", "bg-bhagya-cream-2"), "dropdown items"),
    ("text-bhagya-sindoor",  ("bg-bhagya-cream", "bg-bhagya-cream-2"), "active dropdown item"),
    ("text-bhagya-ink",      ("bg-bhagya-cream", "bg-bhagya-cream-2"), "headings on the page"),

    # Homepage (#242). The night hero and the two night bands put light text on
    # bhagya-night; everything below them is on cream or the alternating cream-2.
    ("text-bhagya-ink",      ("bg-white",), "input text in the form card"),
    ("text-bhagya-ink-soft", ("bg-white",), "long-form body"),
    ("text-bhagya-muted",    ("bg-bhagya-cream", "bg-bhagya-cream-2", "bg-white"), "secondary copy"),
    ("text-bhagya-muted-2",  ("bg-bhagya-cream", "bg-bhagya-cream-2"), "micro-labels and meta"),
    ("text-bhagya-sindoor",  ("bg-white",), "glyphs and eyebrows on white cells"),
    ("placeholder-bhagya-placeholder", ("bg-white",), "form placeholders"),

    # ALPHA ON NIGHT. `/[.NN]` is not a separate colour — it is bhagya-cream
    # composited over whatever it sits on, and the composite is what a reader
    # sees. Measured over night: .48 -> 4.71:1 (the handoff's own .45 is 4.29:1
    # and fails), .55 -> 5.83, .62 -> 7.13, .66 -> 7.93, .72 -> 9.29, .8 -> 11.33.
    ("text-bhagya-cream/[.48]", ("bg-bhagya-night",), "myth line on the worry cards"),
    ("text-bhagya-cream/[.5]",  ("bg-bhagya-night",), "sample-chart caption"),
    ("text-bhagya-cream/[.55]", ("bg-bhagya-night",), "section standfirst"),
    ("text-bhagya-cream/[.62]", ("bg-bhagya-night",), "shloka translations"),
    ("text-bhagya-cream/[.66]", ("bg-bhagya-night",), "hero lede"),
    ("text-bhagya-cream/[.72]", ("bg-bhagya-night",), "truth line on the worry cards"),
    ("text-bhagya-cream/[.78]", ("bg-bhagya-night",), "nav links and the language select (#241)"),
    ("text-bhagya-cream/[.8]",  ("bg-bhagya-night",), "hero trust chips"),
)

# Permitted below AA, by the charter's own rule at base.html: "decorative only
# (subtle disclaimers, italic transliterations, dot separators). Never for
# actionable or standalone-readable text." Reported, never failed — whether a
# given use is decorative needs a human, and this gate does arithmetic.
DECORATIVE = {"text-stone-500"}


class CssUnavailable(RuntimeError):
    """app.css missing or unparseable — exit 2, not a FAIL.

    Same contract as verify_css_build.py: a gate that could not run must never
    be reported as one that passed.
    """


# ---------------------------------------------------------------------------
# Colour plumbing
# ---------------------------------------------------------------------------

def _srgb_to_linear(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    lo, hi = sorted((relative_luminance(fg), relative_luminance(bg)))
    return (hi + 0.05) / (lo + 0.05)


def emitted_colours(css: str) -> dict[str, tuple[int, int, int]]:
    """Map every colour utility in the built CSS to the rgb it actually emits.

    Tailwind writes `color:rgb(87 83 78/var(--tw-text-opacity,1))`, so the
    channels are plain integers and the opacity var is irrelevant here — every
    one of these utilities sets its opacity companion to 1 on the same rule.
    """
    out: dict[str, tuple[int, int, int]] = {}
    pattern = re.compile(
        r"\.((?:text|bg|placeholder)-[a-z0-9-]+)"      # the utility
        r"(?:::placeholder)?"                          # placeholder pseudo
        r"\{[^}]*?"
        r"(?:color|background-color):rgb\((\d+) (\d+) (\d+)"
    )
    for m in pattern.finditer(css):
        out[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return out


def config_bhagya_colours() -> dict[str, tuple[int, int, int]]:
    """`bhagya-*` utilities resolved from tailwind.config.js, not the built CSS.

    Tailwind is JIT: a token no template uses yet emits no rule, so reading
    app.css alone cannot check a colour until a screen adopts it. That would
    make this gate arrive one commit too late every time — the palette is
    decided in #238, and the screens that spend it land much later.

    Reading the config instead means a bad token fails the moment it is
    declared. The built CSS stays authoritative for everything Tailwind DOES
    emit; this only fills the gap for tokens that are declared and not yet
    spent.
    """
    out: dict[str, tuple[int, int, int]] = {}
    try:
        text = (REPO_ROOT / "tailwind.config.js").read_text(encoding="utf-8")
    except OSError:
        return out
    m = re.search(r"bhagya:\s*\{(.*?)\n\s*\},", text, re.S)
    if not m:
        return out
    for name, value in re.findall(r"([\w'-]+):\s*'#([0-9a-fA-F]{6})'", m.group(1)):
        rgb = tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        key = name.strip("'\"")
        for prefix in ("text", "bg", "border"):
            out.setdefault(f"{prefix}-bhagya-{key}", rgb)  # type: ignore[arg-type]
    return out


def utilities_used(prefix: str) -> dict[str, list[str]]:
    """Every `{prefix}-*` utility appearing in a template, with its files."""
    found: dict[str, list[str]] = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        # Strip HTML comments first. base.html's design charter names these
        # utilities while documenting them, and counting a comment as a usage
        # would point the failure message at the wrong file.
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        for util in set(re.findall(rf"\b({prefix}-[a-z]+-\d{{2,3}})\b", text)):
            found.setdefault(util, []).append(str(path.relative_to(REPO_ROOT)))
    return found


def _fmt(util: str, surface: str, ratio: float) -> str:
    return f"{util} on {surface} is {ratio:.2f}:1 (needs {AA_NORMAL}:1)"


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def gate_1_placeholders(colours) -> list[str]:
    """Placeholder text is text. It has no large-text exemption to hide behind."""
    fails = []
    used = utilities_used("placeholder")
    if not used:
        # Not a pass: the gate would be asserting over an empty set.
        return ["no placeholder-* utility found in any template — "
                "did the class naming change? This gate is asserting nothing."]
    for util, files in sorted(used.items()):
        fg = colours.get(util)
        if fg is None:
            fails.append(f"{util} is used in {files[0]} but emits no rule in app.css "
                         "— run `npm ci && npm run build:css`")
            continue
        for surface in INPUT_SURFACES:
            bg = colours.get(surface)
            if bg is None:
                continue
            ratio = contrast_ratio(fg, bg)
            if ratio < AA_NORMAL:
                fails.append(f"{_fmt(util, surface, ratio)} — used in {len(files)} template(s): "
                             + ", ".join(sorted(files)))
    return fails


def gate_2_charter_is_honest(colours) -> list[str]:
    """The charter states ratios out loud. Stated numbers must be true numbers.

    base.html's DESIGN SYSTEM CANONICALS block is the written source of truth
    for text colour on cream. It carried "Passes WCAG AA at ~4.6:1" against
    text-stone-600, which is stone-500's figure — the charter's own next rule
    is what restricts stone-500 to decorative use, so the two were crossed.
    """
    fails = []
    text = BASE_HTML.read_text(encoding="utf-8")

    # Two claim shapes. The original one states a ratio on bg-cream implicitly,
    # because that was the only page surface when it was written. The redesign
    # block (#233) has three surfaces — cream, cream-2 and night — so its claims
    # NAME the surface, and #242 extended this gate rather than letting the new
    # half of the charter go unchecked. An unchecked charter is worse than none:
    # it reads as authority.
    claims = [
        (util, stated, "bg-cream")
        for util, stated in re.findall(
            r"(text-[a-z]+-\d{2,3})[^\n]*\n?[^\n]*?Passes WCAG AA at ~?([0-9.]+):1",
            text,
        )
    ] + [
        (util, stated, surface)
        for util, stated, surface in re.findall(
            r"(text-bhagya-[a-z0-9-]+)[^\n]*\n?[^\n]*?"
            r"Passes WCAG AA at ~?([0-9.]+):1 on (bg-[a-z0-9-]+)",
            text,
        )
    ]
    if not claims:
        return ["base.html states no 'Passes WCAG AA at N:1' ratio — the charter "
                "block moved or was reworded, and this gate now checks nothing."]
    if not any(u.startswith("text-bhagya-") for u, _s, _b in claims):
        return ["base.html states no redesign-palette ratio — the REDESIGN "
                "CANONICALS block moved or was reworded, and half the charter "
                "is now unchecked."]
    for util, stated, surface in claims:
        fg = colours.get(util)
        cream = colours.get(surface)
        if fg is None or cream is None:
            fails.append(f"charter cites {util} on {surface} but one of them "
                         "emits no rule in app.css")
            continue
        actual = contrast_ratio(fg, cream)
        if abs(actual - float(stated)) > 0.15:
            fails.append(f"charter says {util} on {surface} is ~{stated}:1; "
                         f"it is {actual:.2f}:1")
    return fails


ALPHA_UTIL = re.compile(r"^(?P<base>[a-z-]+-bhagya-[a-z0-9-]+)/\[\.(?P<alpha>\d+)\]$")


def composite(fg: tuple[int, int, int], alpha: float,
              bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """Flatten a translucent foreground onto its surface.

    WCAG measures what reaches the eye. `text-bhagya-cream/[.45]` is not cream —
    it is cream mixed with whatever is behind it, and on night that mix is
    #7c777b, which fails AA. Measuring the un-composited token instead reports
    17.49:1 for a colour a reader experiences at 4.29:1, which is worse than not
    checking at all: it is a gate that says PASS on the exact defect it exists
    to catch. This is the arithmetic behind the handoff's .45 -> .48 correction.
    """
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))  # type: ignore[return-value]


def resolve(util: str, surface_rgb, colours):
    """rgb for a utility, compositing `/[.NN]` variants over their surface.

    Returns None when the base colour is unknown, so the caller can report a
    missing rule rather than silently skipping the pair.
    """
    m = ALPHA_UTIL.match(util)
    if not m:
        return colours.get(util)
    base = colours.get(m.group("base"))
    if base is None or surface_rgb is None:
        return None
    return composite(base, float(f"0.{m.group('alpha')}"), surface_rgb)


def gate_3_declared_pairs(colours) -> list[str]:
    fails = []
    for util, surfaces, role in DECLARED_PAIRS:
        for surface in surfaces:
            bg = colours.get(surface)
            if bg is None:
                fails.append(f"{surface} emits no rule in app.css")
                continue
            fg = resolve(util, bg, colours)
            if fg is None:
                fails.append(f"{util} ({role}) emits no rule in app.css")
                continue
            ratio = contrast_ratio(fg, bg)
            if ratio < AA_NORMAL:
                fails.append(f"{_fmt(util, surface, ratio)} — {role}")
    return fails


def gate_4_alpha_declared(colours) -> list[str]:
    """Every translucent bhagya TEXT utility in a template must be declared.

    Gate 3 only measures what DECLARED_PAIRS lists. Without this, adding
    `/[.4]` to a template is invisible to the whole file — the utility emits a
    rule, nothing references it here, and the gate stays green. That is how the
    handoff shipped a 4.29:1 body line past its own review.
    """
    declared = {util for util, _s, _r in DECLARED_PAIRS}
    used: dict[str, list[str]] = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = re.sub(r"<!--.*?-->", " ", path.read_text(encoding="utf-8"),
                      flags=re.DOTALL)
        text = re.sub(r"\{#.*?#\}", " ", text, flags=re.DOTALL)
        for util in set(re.findall(r"\btext-bhagya-[a-z0-9-]+/\[\.\d+\]", text)):
            used.setdefault(util, []).append(path.name)
    fails = []
    for util in sorted(used):
        if util not in declared:
            where = ", ".join(sorted(set(used[util])))
            fails.append(f"{util} is used in {where} but is not in DECLARED_PAIRS "
                         "— its composited ratio has never been measured")
    return fails


def report_decorative(colours) -> None:
    """Not a gate. Surfaces how much weight the decorative exemption carries."""
    for util in sorted(DECORATIVE):
        fg, bg = colours.get(util), colours.get("bg-cream")
        if fg is None or bg is None:
            continue
        ratio = contrast_ratio(fg, bg)
        count = sum(
            len(re.findall(rf"\b{re.escape(util)}\b", p.read_text(encoding="utf-8")))
            for p in TEMPLATES.rglob("*.html")
        )
        print(f"  note {util} on bg-cream is {ratio:.2f}:1, used {count}x. "
              "Charter permits it for decorative text only; not failed here "
              "because whether a use is decorative needs a human.")


def main() -> int:
    if not BUILT_CSS.exists():
        print(f"COULD NOT VERIFY: {BUILT_CSS.relative_to(REPO_ROOT)} does not exist.")
        print("  npm ci && npm run build:css")
        print("-> SKIPPED (exit 2). This is NOT a pass — the check did not run.")
        return 2

    colours = emitted_colours(BUILT_CSS.read_text(encoding="utf-8"))
    # Config values fill in only where the built CSS has nothing — emitted
    # rules win, so this can never mask what actually ships.
    for util, rgb in config_bhagya_colours().items():
        colours.setdefault(util, rgb)
    if "bg-cream" not in colours:
        print("COULD NOT VERIFY: app.css parsed but yielded no bg-cream rule.")
        print("-> SKIPPED (exit 2). This is NOT a pass — the check did not run.")
        return 2

    print(f"Contrast verification — {len(colours)} colour utilities read from app.css\n")

    gates = (
        ("Gate 1 - placeholder text meets AA on input surfaces", gate_1_placeholders),
        ("Gate 2 - the base.html charter states true ratios", gate_2_charter_is_honest),
        ("Gate 3 - declared text-on-surface pairs meet AA", gate_3_declared_pairs),
        ("Gate 4 - every translucent text utility is declared", gate_4_alpha_declared),
    )

    all_failures: list[str] = []
    results: list[tuple[str, str]] = []
    for title, fn in gates:
        print(title)
        failures = fn(colours)
        for f in failures:
            print(f"  FAIL {f}")
        if not failures:
            print("  ok   no violations")
        results.append(("FAIL" if failures else "PASS", title))
        all_failures.extend(failures)
        print(f"  -> {'FAIL' if failures else 'PASS'}\n")

    print("Decorative colours (reported, not gated)")
    report_decorative(colours)
    print()

    print("Summary")
    for verdict, title in results:
        print(f"  {verdict:9} {title}")
    print()

    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s)")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
