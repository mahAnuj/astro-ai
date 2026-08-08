#!/usr/bin/env python3
"""Verify the committed Tailwind build is honest.

The site used to load Tailwind from the Play CDN, which compiled the whole
stylesheet in the browser on every page load. That is gone: the CSS is built
ahead of time by `npm run build:css` and the OUTPUT IS COMMITTED, because the
Cloud Run image is Python-only and the Cloud Build trigger is configured
GCP-side where it cannot be tested before it reaches production.

A committed build artefact can drift from its source. It can also be silently
wrong in a way the old CDN never was, because Tailwind's content scanner is a
plain text matcher: a class name a template assembles at render time
(`bg-{{ status_color[0] }}-50`) is invisible to it and gets purged, shipping a
colourless panel. The CDN never had that failure mode — it generated rules
from the live DOM.

So four gates:

  Gate 1  the committed CSS matches a fresh build of the current sources
  Gate 2  every colour family templates use dynamically is safelisted
  Gate 3  the astro palette has no holes (#186 regression guard)
  Gate 4  no Play CDN reference has crept back into a template

Exit 0 on pass, 1 on any failure. `--skip-rebuild` runs 2-4 only, for
environments without Node.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "src" / "astro_ai" / "templates"
BUILT_CSS = REPO_ROOT / "src" / "astro_ai" / "static" / "css" / "app.css"
CONFIG = REPO_ROOT / "tailwind.config.js"
INPUT_CSS = REPO_ROOT / "assets" / "tailwind.css"

# Shades the astro palette must define. 200/300/400 are the ones #186 found
# missing after 106 template usages had already shipped against them.
REQUIRED_ASTRO_SHADES = ("50", "100", "200", "300", "400",
                         "500", "600", "700", "800", "900")

# `bg-{{ var }}-100`, `border-{{ status_color[0] }}-200`, ...
DYNAMIC_CLASS = re.compile(
    r"(?:bg|text|border|from|via|to|ring|fill|stroke|divide)-\{\{[^}]+\}\}(?:-\d{2,3})?"
)
# The Jinja dicts those variables resolve to map a verdict to a colour:
#     {'friend': 'emerald', 'neutral': 'stone', 'enemy': 'amber'}
#     phase_labels.get(x, ('stone', 'Sade Sati', ''))
# Only the VALUE side names a colour family. That distinction is not
# cosmetic: 'neutral' is a verdict key in two templates and also a real
# Tailwind family name, so a matcher that reads both sides reports it as an
# unsafelisted colour and invites you to bloat the safelist to silence a bug
# in the matcher. So: match only after ':' '=' or ',' (optionally into a
# tuple), and reject anything whose closing quote is followed by ':' — that
# is a key, not a value.
VALUE_FAMILY = re.compile(
    r"""[:=,]\s*\(?\s*['"]([a-z]+)(?:-\d{2,3})?[^'"]*['"](?!\s*:)"""
)
KNOWN_FAMILIES = {
    "astro", "slate", "gray", "zinc", "neutral", "stone", "red", "orange",
    "amber", "yellow", "lime", "green", "emerald", "teal", "cyan", "sky",
    "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose",
}


def _fail(msg: str) -> str:
    print(f"  FAIL {msg}")
    return msg


def gate_1_css_is_fresh() -> list[str]:
    """The committed stylesheet must equal a fresh build of current sources."""
    failures: list[str] = []
    npx = shutil.which("npx")
    if npx is None:
        print("  SKIP no npx on PATH — cannot rebuild (run with Node to check)")
        return failures

    if not BUILT_CSS.exists():
        return [_fail(f"{BUILT_CSS.relative_to(REPO_ROOT)} does not exist — "
                      "run `npm run build:css`")]

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "fresh.css"
        proc = subprocess.run(
            [npx, "tailwindcss", "-i", str(INPUT_CSS), "-o", str(out), "--minify"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return [_fail("tailwind build failed:\n" + (proc.stderr or proc.stdout))]

        fresh = out.read_bytes()
        committed = BUILT_CSS.read_bytes()

    if fresh == committed:
        print(f"  ok   committed CSS matches a fresh build "
              f"({len(committed):,} bytes)")
    else:
        failures.append(_fail(
            f"committed CSS is STALE ({len(committed):,} bytes) vs a fresh "
            f"build ({len(fresh):,} bytes). A template or the config changed "
            f"without re-running `npm run build:css`, so the site would ship "
            f"markup whose classes have no rules. Run: npm run build:css"
        ))
    return failures


def _safelisted_families() -> set[str]:
    text = CONFIG.read_text(encoding="utf-8")
    # pull the (astro|emerald|...) alternation group out of the safelist pattern
    families: set[str] = set()
    for group in re.findall(r"\(([a-z|]+)\)", text):
        parts = set(group.split("|"))
        if parts & KNOWN_FAMILIES:
            families |= parts & KNOWN_FAMILIES
    return families


def _families_used_dynamically() -> dict[str, list[str]]:
    """Colour families that reach a class name through a template variable."""
    used: dict[str, list[str]] = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        body = path.read_text(encoding="utf-8", errors="ignore")
        if not DYNAMIC_CLASS.search(body):
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for line in body.splitlines():
            # a line that both defines colour-ish data and quotes family names
            if not re.search(r"(colors?|_colors|label_class|status_color|"
                             r"phase_|verdict|rating)", line, re.I):
                continue
            for quoted in VALUE_FAMILY.findall(line):
                if quoted in KNOWN_FAMILIES:
                    used.setdefault(quoted, [])
                    if rel not in used[quoted]:
                        used[quoted].append(rel)
    return used


def gate_2_dynamic_families_safelisted() -> list[str]:
    """Anything a template builds at render time must survive the purge."""
    failures: list[str] = []
    safelisted = _safelisted_families()
    used = _families_used_dynamically()

    if not safelisted:
        return [_fail("could not find a colour-family alternation in the "
                      "safelist pattern in tailwind.config.js")]

    print(f"  ok   safelist covers: {', '.join(sorted(safelisted))}")

    missing = {f: paths for f, paths in used.items() if f not in safelisted}
    for family, paths in sorted(missing.items()):
        failures.append(_fail(
            f"colour family {family!r} is used to build class names at render "
            f"time ({', '.join(paths[:3])}) but is NOT in the safelist. "
            f"Tailwind's scanner cannot see it, so every {family}-* utility "
            f"those templates emit is purged and the panel ships unstyled. "
            f"Add it to the safelist pattern in tailwind.config.js."
        ))
    if not missing:
        print(f"  ok   all {len(used)} dynamically-used family(ies) safelisted "
              f"({', '.join(sorted(used))})")
    return failures


def gate_3_astro_palette_complete() -> list[str]:
    """#186: 106 usages shipped against three shades that did not exist."""
    failures: list[str] = []
    if not BUILT_CSS.exists():
        return [_fail("no built CSS to check the palette against")]
    css = BUILT_CSS.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")

    for shade in REQUIRED_ASTRO_SHADES:
        if not re.search(rf"^\s*{shade}:\s*'#", config, re.M):
            failures.append(_fail(
                f"astro-{shade} is not defined in tailwind.config.js. This is "
                f"exactly #186: templates reference the shade, Tailwind emits "
                f"no colour rule, and the element falls back to the default "
                f"border grey."
            ))
    if not failures:
        print(f"  ok   astro palette defines all {len(REQUIRED_ASTRO_SHADES)} "
              f"shades ({', '.join(REQUIRED_ASTRO_SHADES)})")

    # and the three #186 shades must actually reach the stylesheet
    for shade, hexv in (("200", "#ddd6fe"), ("300", "#c4b5fd"), ("400", "#a78bfa")):
        if hexv not in css:
            failures.append(_fail(
                f"astro-{shade} ({hexv}) is defined in the config but absent "
                f"from the built CSS — the build is stale or the shade is "
                f"referenced nowhere and got purged."
            ))
    return failures


def gate_4_no_cdn_regression() -> list[str]:
    """The Play CDN must not come back — it is why FOUC existed."""
    failures: list[str] = []
    hits: list[str] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        for i, line in enumerate(path.read_text(encoding="utf-8",
                                                errors="ignore").splitlines(), 1):
            if "cdn.tailwindcss.com" in line and not line.lstrip().startswith(
                    ("<!--", "*", "#", "//")):
                hits.append(f"{path.relative_to(REPO_ROOT)}:{i}")
    if hits:
        failures.append(_fail(
            "the Tailwind Play CDN is referenced again at "
            + ", ".join(hits)
            + " — it ships a ~400KB in-browser compiler and reintroduces the "
              "flash of unstyled content the build step removed."
        ))
    else:
        print("  ok   no Play CDN reference in any template")
    return failures


def main() -> int:
    print("CSS build verification — build-step Tailwind + #186 palette")
    print()

    gates = [
        ("Gate 1 - committed CSS is a fresh build", gate_1_css_is_fresh),
        ("Gate 2 - dynamic colour families are safelisted", gate_2_dynamic_families_safelisted),
        ("Gate 3 - astro palette has no holes (#186)", gate_3_astro_palette_complete),
        ("Gate 4 - no Play CDN regression", gate_4_no_cdn_regression),
    ]
    if "--skip-rebuild" in sys.argv[1:]:
        gates = gates[1:]

    all_failures: list[str] = []
    results: list[tuple[str, bool]] = []
    for title, run in gates:
        print(title)
        failures = run()
        print(f"  -> {'PASS' if not failures else 'FAIL'}")
        print()
        results.append((title, not failures))
        all_failures.extend(failures)

    print("Summary")
    for title, ok in results:
        print(f"  {'PASS' if ok else 'FAIL':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s)")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
