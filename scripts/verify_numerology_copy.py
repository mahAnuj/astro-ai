#!/usr/bin/env python3
"""Verify that the numerology pages' RENDERED copy names traditions, not authors.

WHY THIS EXISTS
---------------
#200. CLAUDE.md: "citing the classical tradition rather than book-and-chapter
references in user-facing prose". `numerology.html` and `numerology_compat.html`
told readers "exalted date per Johari", "Kumar's formula", "(Cheiro)" and
"Origin: L. Dow Balliett / Juno Jordan". Naming a book implies the page is
quoting it; where the claim is not traceable that manufactures authority — the
mechanism by which the Lo Shu grid came to be credited to a book with zero
occurrences of "Lo Shu" (#172, guarded by verify_lo_shu_attribution.py).

Provenance was RELOCATED, not deleted: it lives in the adjacent `{# … #}` Jinja
comments, which never reach the browser, and in knowledge/numerology.md. So this
gate looks only at what a reader receives — comments are stripped first — and
the comments are free to say "Johari §4 / Kumar Ch.1".

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. A missing anchor is a FAIL, not a skip. A gate that cannot find its subject
   passes vacuously (#193). Each `_ANCHORS` entry is the replacement wording for
   a site that used to name an author; if you reword the site, re-point it.
2. Every author name left in rendered copy must be in `_ALLOWED`, with a reason.
   The expected count is derived from that list, in both directions: more is an
   unjustified mention; fewer means an allowance outlived its reason and should
   be deleted rather than left as a standing licence.
3. The self-test runs on every invocation. It puts each removed phrase back and
   asserts this gate goes red, then does the same for a bare new mention. A
   mutation whose anchor has gone is a FAIL ("re-point this mutation").
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "templates"
FILES = ("numerology.html", "numerology_compat.html")

# Author names that must not appear as the source of a rule in rendered copy.
# Jordan/Warner/Hamon are the secondary names that rode along with Balliett and
# Cheiro ("Balliett / Jordan", "William John Warner").
_NAMES = re.compile(r"Johari|Kumar|Cheiro|Balliett|Seton|Juno Jordan|Warner|Hamon",
                    re.IGNORECASE)

# (file, fragment containing the mention, reason). Each carries exactly one
# mention. These are SEO strings, not citations of a rule: "Chaldean (Cheiro)" is
# how people search for the system, and the same string heads page_title and
# page_meta in routes/numerology.py. Changing search-facing text is a ranking
# decision for a human, not a copy fix (#200 deliberately left it).
_ALLOWED: tuple[tuple[str, str, str], ...] = (
    ("numerology.html",
     'Free numerology calculator — Chaldean (Cheiro) and the Lo Shu grid.',
     "JSON-LD tool_desc mirrors the page_title/page_meta search term "
     "'Chaldean (Cheiro)'; a ranking decision, not a citation"),
)

# (file, rewritten wording that must be present, the phrase it replaced). The
# replaced phrase is what the self-test puts back.
_ANCHORS: tuple[tuple[str, str, str], ...] = (
    ("numerology.html",
     "Chaldean and Lo Shu grid calculators",
     "Chaldean (Cheiro) and Lo Shu grid calculators"),
    ("numerology.html",
     "through a modern Western (Chaldean) or ancient Chinese (Lo Shu) framework",
     "through a modern Western (Cheiro) or ancient Chinese (Lo Shu) framework"),
    ("numerology.html",
     "Origin: early-20th-century American numerology, ~1908-1940s.",
     "Origin: L. Dow Balliett / Juno Jordan, USA, ~1908-1940s."),
    ("numerology.html",
     "Origin: same early-20th-century American lineage.",
     "Origin: same Balliett/Jordan lineage."),
    ("numerology.html",
     "Origin of the Chaldean table: early-20th-century Western Chaldean numerology; "
     "the tables in wide Indian circulation trace to that lineage.",
     "Origin of the Chaldean table: Cheiro (William John Warner, 1866-1936); "
     "the tables in wide Indian circulation trace to him."),
    ("numerology.html",
     "★ = exalted date in the Vedic-integrated numerology tradition",
     "★ = exalted date per Johari"),
    ("numerology.html",
     "In the Vedic-integrated numerology tradition. Practise",
     "Per Johari's Vedic-integrated system. Practise"),
    ("numerology.html",
     "The standard Personal Year method: birth-month digits",
     "Kumar's formula: birth-month digits"),
    ("numerology_compat.html",
     "compatibility in the Vedic-integrated numerology tradition",
     "compatibility per Johari"),
    ("numerology_compat.html",
     "compared in the Vedic-integrated numerology tradition.",
     "compared per Johari's classical Vedic-integrated system."),
    ("numerology_compat.html",
     "the tradition's specific 6 favourable + 6 avoid marriage pairs",
     "Johari's specific 6 favourable + 6 avoid marriage pairs"),
    ("numerology_compat.html",
     "<strong>The tradition's honest framing:</strong>",
     "<strong>Johari's honest framing:</strong>"),
    ("numerology_compat.html",
     "Classical marriage-favourable pair in this tradition",
     "Classical marriage-favourable pair per Johari"),
    ("numerology_compat.html",
     "Classical marriage-avoid pair in this tradition",
     "Classical marriage-avoid pair per Johari"),
)

_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)


def _rendered(text: str) -> str:
    """What the template can send a reader: Jinja comments removed."""
    return _COMMENT.sub("", text)


def _problems(texts: dict[str, str]) -> list[str]:
    problems: list[str] = []
    stripped = {name: _rendered(texts[name]) for name in FILES}

    for fname, new, _old in _ANCHORS:
        if new not in stripped[fname]:
            problems.append(f"{fname}: anchor not found in rendered copy — {new!r}. "
                            "Re-point it if the site was reworded; do not delete it.")

    permitted = 0
    for fname, body in stripped.items():
        for m in _NAMES.finditer(body):
            line = body[max(0, m.start() - 90):m.end() + 40].replace("\n", " ")
            ok = False
            for af, frag, _r in _ALLOWED:
                at = body.find(frag)
                if af == fname and at != -1 and at <= m.start() < at + len(frag):
                    ok = True
                    break
            if ok:
                permitted += 1
            else:
                problems.append(f"{fname}: author named in rendered copy — "
                                f"{m.group(0)!r} in …{line.strip()}…")

    for fname, frag, _reason in _ALLOWED:
        if frag not in stripped[fname]:
            problems.append(f"{fname}: allowlisted fragment gone — {frag!r}. Drop it "
                            "from _ALLOWED; an allowance with no subject is a licence.")
    if permitted != len(_ALLOWED):
        problems.append(f"{permitted} allowed mentions found, expected exactly "
                        f"{len(_ALLOWED)} — one per _ALLOWED entry.")
    return problems


def _self_test(texts: dict[str, str]) -> int:
    failures = 0
    mutations: list[tuple[str, str, str, str]] = [
        (f"{old!r} restored", fname, new, old) for fname, new, old in _ANCHORS]
    mutations.append(("a bare new mention", "numerology_compat.html",
                      "Numerology Compatibility Check",
                      "Numerology Compatibility Check (after Kumar)"))
    for label, fname, new, old in mutations:
        body = texts[fname]
        if new not in body:
            print(f"  FAIL  {label}: anchor gone — re-point this mutation")
            failures += 1
            continue
        mutated = dict(texts)
        mutated[fname] = body.replace(new, old, 1)
        if _problems(mutated):
            print(f"  ok    {label} — caught")
        else:
            print(f"  FAIL  {label} — gate stayed green on a known defect")
            failures += 1
    # The converse: a mention inside a Jinja comment is provenance and must pass.
    mutated = dict(texts)
    mutated["numerology.html"] = texts["numerology.html"] + "\n{# Johari §4 / Kumar Ch.1 #}\n"
    if _problems(mutated):
        print("  FAIL  an author in a {# #} comment — gate flagged provenance")
        failures += 1
    else:
        print("  ok    an author in a {# #} comment — correctly ignored")
    return failures


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--self-test"]
    root = Path(args[0]) if args else TEMPLATES
    texts = {name: (root / name).read_text(encoding="utf-8") for name in FILES}

    problems = _problems(texts)
    for p in problems:
        print(f"FAIL — {p}")
    if problems:
        return 1

    print(f"Rendered numerology copy clean — {len(_ANCHORS)} anchors present, "
          f"{len(_ALLOWED)} allowed mention(s) (SEO term), no other author named.")
    print("Self-test (each known defect must turn this gate red):")
    if _self_test(texts):
        print("FAIL — the gate does not bite. A gate that cannot fail is worse "
              "than none (#193).")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
