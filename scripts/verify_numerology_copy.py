#!/usr/bin/env python3
"""Verify that the numerology pages' user-facing copy names traditions, not authors.

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
gate looks only at what can reach a reader — Jinja comments are stripped from
the two templates, and `numerology.py` is read through `ast` so only string
constants count (docstrings, `#` comments and identifiers are free to say
"Johari §4 / Kumar Ch.1"). It scans SOURCE, not rendered pages: a string built at
runtime from pieces would not be seen.

Two more surfaces were added on chief's ruling on #200 (2026-11-07): the SEO
strings in `routes/numerology.py` (`page_title` / `page_meta`, read through `ast`
like `numerology.py`) and the `num_caveat_body_*` strings in `i18n.py`, which
must not name the Balliett / Seton / Jordan lineage. That lineage is not in
knowledge/*.md (0 hits, measured 2026-11-07), so a user-facing sentence stating
it was a claim nothing could source. The Cheiro / Chaldean-table sentence in
`num_caveat_body_2` stays: it IS sourced (knowledge/numerology.md line 6, §14.2).

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. A missing anchor is a FAIL, not a skip. A gate that cannot find its subject
   passes vacuously (#193). Each `_ANCHORS` entry is the replacement wording for
   a site that used to name an author; if you reword the site, re-point it.
2. Every author name left in rendered copy must be in `_ALLOWED`, with a reason.
   The expected count is derived from that list, in both directions: more is an
   unjustified mention; fewer means an allowance outlived its reason and should
   be deleted rather than left as a standing licence. The list is EMPTY since
   2026-11-07; adding to it again needs a ruling, not a reason string.
3. The self-test runs on every invocation. It puts each removed phrase back and
   asserts this gate goes red, then does the same for a bare new mention. A
   mutation whose anchor has gone is a FAIL ("re-point this mutation").
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
TEMPLATES = PKG / "templates"
FILES = ("numerology.html", "numerology_compat.html")
PYFILE = "numerology.py"
ROUTEFILE = "routes/numerology.py"   # page_title / page_meta: the SEO strings
I18NFILE = "i18n.py"                 # num_caveat_body_*: the on-page caveat

# Author names that must not appear as the source of a rule in rendered copy.
# Includes the given names and secondary names that ride along with a surname
# ("Balliett / Juno Jordan", "William John Warner", "Harish Johari", "Jayant
# Kumar", Goodwin from the corpus's source key) — a mutation adding
# "(Jayant, Goodwin, Harish)" must go red, and a surname-only list let it pass.
_NAMES = re.compile(r"Johari|Harish|Kumar|Jayant|Cheiro|Warner|Hamon|Balliett|"
                    r"Seton|Juno Jordan|Goodwin", re.IGNORECASE)

# The lineage the on-page caveat may not state: knowledge/*.md has no Balliett,
# Seton, Juno Jordan or 1908 (0 hits, 2026-11-07), so naming them in a sentence
# readers see is an unsourced claim. English and Hindi (बैलियेट, सीटन, जूनो).
#
# #773 item 2 (2026-11-11) adds the two named people the caveat used to cite for
# a view: K.N. Rao and "scholar Shyamasundara Dasa". Neither is in knowledge/*.md
# (0 hits), so the sentence put words in two real people's mouths with nothing
# to quote. English and Hindi (के.एन. राव, श्यामसुन्दर).
_CAVEAT_BANNED = re.compile(r"Balliett|Seton|Juno Jordan|बैलियेट|सीटन|जूनो|"
                            r"Shyamasundara|K\.N\. Rao|श्यामसुन्दर|के\.एन\. राव",
                            re.IGNORECASE)

# #773 item 3: the "~1908-1940s" dating of the Life Path lineage is not in
# knowledge/*.md either. Rendered template copy may say "20th-century Western",
# the wording num_caveat_body_1 and _3 use, and no more specific than that.
_UNSOURCED_DATING = re.compile(r"1908|1940s")

# (file, fragment containing the mention, reason). Each carries exactly one
# mention. EMPTY since 2026-11-07: it held one entry, the `tool_desc` that
# mirrored the "Chaldean (Cheiro)" search term, and chief ruled the author out of
# the SEO strings (#200: the only "cheiro" query in 19,608 GSC impressions had 1).
# The count checks below still run, at zero.
_ALLOWED: tuple[tuple[str, str, str], ...] = ()

# (file, rewritten wording that must be present, the phrase it replaced). The
# replaced phrase is what the self-test puts back.
_ANCHORS: tuple[tuple[str, str, str], ...] = (
    ("numerology.html",
     "Free numerology calculator — Chaldean and the Lo Shu grid.",
     "Free numerology calculator — Chaldean (Cheiro) and the Lo Shu grid."),
    ("numerology.html",
     "Chaldean and Lo Shu grid calculators",
     "Chaldean (Cheiro) and Lo Shu grid calculators"),
    ("numerology.html",
     "through a modern Western (Chaldean) or ancient Chinese (Lo Shu) framework",
     "through a modern Western (Cheiro) or ancient Chinese (Lo Shu) framework"),
    ("numerology.html",
     "Origin: 20th-century Western numerology.",
     "Origin: L. Dow Balliett / Juno Jordan, USA, ~1908-1940s."),
    ("numerology.html",
     "Origin: same 20th-century Western lineage.",
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
     "These remedies follow the Vedic-integrated numerology tradition. Practise",
     "Per Johari's Vedic-integrated system. Practise"),
    ("numerology.html",
     "The Personal Year method used on this page: birth-month digits",
     "Kumar's formula: birth-month digits"),
    ("numerology_compat.html",
     "compatibility in the Vedic-integrated numerology tradition",
     "compatibility per Johari"),
    ("numerology_compat.html",
     "compared in the Vedic-integrated numerology tradition.",
     "compared per Johari's classical Vedic-integrated system."),
    ("numerology_compat.html",
     "the Vedic-integrated tradition's specific 6 favourable + 6 avoid marriage pairs",
     "Johari's specific 6 favourable + 6 avoid marriage pairs"),
    ("numerology_compat.html",
     "<strong>The Vedic-integrated tradition's honest framing:</strong>",
     "<strong>Johari's honest framing:</strong>"),
    ("numerology_compat.html",
     "Classical marriage-favourable pair in the Vedic-integrated tradition",
     "Classical marriage-favourable pair per Johari"),
    ("numerology_compat.html",
     "Classical marriage-avoid pair in the Vedic-integrated tradition",
     "Classical marriage-avoid pair per Johari"),
)

# numerology.py string constants that used to name Johari and render beside the
# badges (compat summary) or in the life-challenge prose. (replacement fragment,
# phrase it replaced). Same rule as _ANCHORS: missing = FAIL.
_PY_ANCHORS: tuple[tuple[str, str], ...] = (
    ("The Vedic-integrated tradition's caveat: friend-pairings",
     "Johari's caveat: friend-pairings"),
    ("the Vedic-integrated tradition sees this as more valuable",
     "Johari sees this as more valuable"),
    (" Classical marriage-favourable pair in the Vedic-integrated tradition",
     " Classical marriage-favourable pair per Johari"),
    (" Classical marriage-avoid pair in the Vedic-integrated tradition",
     " Classical marriage-avoid pair per Johari"),
    ("the Vedic-integrated tradition specifically warns 26-borns",
     "Johari specifically warns 26-borns"),
    ("are the tradition's ideal partner for 9-men",
     "are Johari's ideal partner for 9-men"),
)

# routes/numerology.py string constants that are the SEO strings. (replacement
# fragment, phrase it replaced). Missing = FAIL, like the others.
_ROUTE_ANCHORS: tuple[tuple[str, str], ...] = (
    ("Free Numerology Calculator — Chaldean and Lo Shu (with honest tradition note)",
     "Free Numerology Calculator — Chaldean (Cheiro) and Lo Shu (with honest tradition note)"),
    ("Free numerology calculator using the Chaldean system plus the Chinese Lo Shu grid.",
     "Free numerology calculator using the Chaldean (Cheiro) system plus the Chinese Lo Shu grid."),
    ("Free numerology calculator using the Chaldean system.",
     "Free numerology calculator using the Chaldean (Cheiro) system."),
)

# i18n.py num_caveat_body_2, EN and HI. The first words of the sentence that
# survives; the self-test puts the deleted Balliett/Seton/Jordan sentence back in
# front of it. (raw-source start of the surviving value, the same with the deleted
# sentence restored, language).
_CAVEAT_ANCHORS: tuple[tuple[str, str, str], ...] = (
    ('"num_caveat_body_2":       "The \\"Chaldean\\" name-number tables',
     '"num_caveat_body_2":       "The Life Path / Expression / Soul Urge framework '
     'was built by three Americans between 1908 and mid-20th century — L. Dow '
     'Balliett, Julia Seton (who coined the word \\"numerology\\" ~1912), and Juno '
     'Jordan. The \\"Chaldean\\" name-number tables',
     "EN"),
    ('"num_caveat_body_2":       "व्यापक प्रचलन में',
     '"num_caveat_body_2":       "लाइफ पाथ / एक्सप्रेशन / सोल अर्ज ढाँचा 1908 से '
     'मध्य-20वीं शताब्दी के बीच तीन अमेरिकियों — एल. डो बैलियेट, जूलिया सीटन '
     '(जिन्होंने ~1912 में \\"numerology\\" शब्द गढ़ा), और जूनो जॉर्डन ने बनाया था। '
     'व्यापक प्रचलन में',
     "HI"),
)

# i18n.py num_caveat_body_2, the sentence that replaced the named-people one
# (#773 item 2). (surviving wording, the removed K.N. Rao / Shyamasundara Dasa
# clause put back in its place, language). The self-test restores the clause.
_PERSON_ANCHORS: tuple[tuple[str, str, str], ...] = (
    ("(William John Warner, 1866\u20131936). The method is also calendar- and "
     "alphabet-dependent rather than universal:",
     "(William John Warner, 1866\u20131936). Respected Jyotish teachers such as "
     "K.N. Rao practice without numerology; scholar Shyamasundara Dasa argues the "
     "method is calendar- and alphabet-dependent rather than universal:",
     "EN"),
    ("1866-1936) \u0938\u0947 \u0906\u0924\u0940 \u0939\u0948\u0902\u0964 "
     "\u092f\u0939 \u0935\u093f\u0927\u093f \u0938\u0930\u094d\u0935\u0935"
     "\u094d\u092f\u093e\u092a\u0940 \u0928 \u0939\u094b\u0915\u0930",
     "1866-1936) \u0938\u0947 \u0906\u0924\u0940 \u0939\u0948\u0902\u0964 "
     "\u0915\u0947.\u090f\u0928. \u0930\u093e\u0935 \u091c\u0948\u0938\u0947 "
     "\u0938\u092e\u094d\u092e\u093e\u0928\u093f\u0924 \u091c\u094d\u092f"
     "\u094b\u0924\u093f\u0937 \u0906\u091a\u093e\u0930\u094d\u092f "
     "\u0905\u0902\u0915\u0936\u093e\u0938\u094d\u0924\u094d\u0930 "
     "\u0915\u0947 \u092c\u093f\u0928\u093e \u0905\u092d\u094d\u092f\u093e"
     "\u0938 \u0915\u0930\u0924\u0947 \u0939\u0948\u0902; "
     "\u0935\u093f\u0926\u094d\u0935\u093e\u0928 "
     "\u0936\u094d\u092f\u093e\u092e\u0938\u0941\u0928\u094d\u0926\u0930 "
     "\u0926\u093e\u0938 \u0924\u0930\u094d\u0915 \u0926\u0947\u0924\u0947 "
     "\u0939\u0948\u0902 \u0915\u093f \u092f\u0939 \u0935\u093f\u0927\u093f "
     "\u0938\u0930\u094d\u0935\u0935\u094d\u092f\u093e\u092a\u0940 \u0928 "
     "\u0939\u094b\u0915\u0930",
     "HI"),
)

_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)


def _rendered(text: str) -> str:
    """What the template can send a reader: Jinja comments removed."""
    return _COMMENT.sub("", text)


def _py_literals(text: str) -> list[tuple[int, str]]:
    """(line, value) of every non-docstring string constant in the module."""
    tree = ast.parse(text)
    docs: set[int] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)) and n.body:
            first = n.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                docs.add(id(first.value))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs]


def _caveat_values(text: str) -> list[tuple[int, str, str]]:
    """(line, key, value) of every `num_caveat_body_*` entry in i18n.py."""
    out: list[tuple[int, str, str]] = []
    for n in ast.walk(ast.parse(text)):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and k.value.startswith("num_caveat_body_")
                        and isinstance(v, ast.Constant) and isinstance(v.value, str)):
                    out.append((v.lineno, k.value, v.value))
    return out


def _problems(texts: dict[str, str]) -> list[str]:
    problems: list[str] = []
    caveats = _caveat_values(texts[I18NFILE])
    # 3 bodies x EN + HI. A parse that finds fewer would pass vacuously (#193).
    if len(caveats) != 6:
        problems.append(f"{I18NFILE}: found {len(caveats)} num_caveat_body_* strings, "
                        "expected 6 (3 x EN+HI). Re-point the scan if the keys moved.")
    for line, key, value in caveats:
        for m in _CAVEAT_BANNED.finditer(value):
            problems.append(f"{I18NFILE}:{line}: {key} names an unsourced lineage — "
                            f"{m.group(0)!r} (not in knowledge/*.md, #200)")
    for new, _old, lang in _PERSON_ANCHORS:
        if new not in texts[I18NFILE]:
            problems.append(f"{I18NFILE}: {lang} num_caveat_body_2 person-sentence "
                            f"anchor not found — {new!r}. Re-point it if the string "
                            "was reworded; do not delete it.")
    for new, _old, lang in _CAVEAT_ANCHORS:
        if new not in texts[I18NFILE]:
            problems.append(f"{I18NFILE}: {lang} num_caveat_body_2 anchor not found — "
                            f"{new!r}. Re-point it if the string was reworded; do not "
                            "delete it.")
    route_literals = _py_literals(texts[ROUTEFILE])
    joined_route = "\n".join(v for _l, v in route_literals)
    for new, _old in _ROUTE_ANCHORS:
        if new not in joined_route:
            problems.append(f"{ROUTEFILE}: SEO anchor not found in string literals — "
                            f"{new!r}. Re-point it if the string was reworded; do not "
                            "delete it.")
    for line, value in route_literals:
        for m in _NAMES.finditer(value):
            problems.append(f"{ROUTEFILE}:{line}: author named in an SEO/string literal — "
                            f"{m.group(0)!r} in …{value[max(0, m.start() - 50):m.end() + 30]!r}…")
    literals = _py_literals(texts[PYFILE])
    joined_py = "\n".join(v for _l, v in literals)
    for new, _old in _PY_ANCHORS:
        if new not in joined_py:
            problems.append(f"{PYFILE}: anchor not found in string literals — {new!r}. "
                            "Re-point it if the string was reworded; do not delete it.")
    for line, value in literals:
        for m in _NAMES.finditer(value):
            problems.append(f"{PYFILE}:{line}: author named in a string literal — "
                            f"{m.group(0)!r} in …{value[max(0, m.start() - 50):m.end() + 30]!r}…")
    stripped = {name: _rendered(texts[name]) for name in FILES}

    for fname, new, _old in _ANCHORS:
        if new not in stripped[fname]:
            problems.append(f"{fname}: anchor not found in rendered copy — {new!r}. "
                            "Re-point it if the site was reworded; do not delete it.")

    for fname, body in stripped.items():
        for m in _UNSOURCED_DATING.finditer(body):
            line = body[max(0, m.start() - 60):m.end() + 30].replace("\n", " ")
            problems.append(f"{fname}: unsourced dating in rendered copy — "
                            f"{m.group(0)!r} in …{line.strip()}… (not in "
                            "knowledge/*.md, #773)")

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
    mutations += [(f"{PYFILE}: {old!r} restored", PYFILE, new, old)
                  for new, old in _PY_ANCHORS]
    mutations += [(f"{ROUTEFILE}: {old!r} restored", ROUTEFILE, new, old)
                  for new, old in _ROUTE_ANCHORS]
    mutations += [(f"{I18NFILE}: {lang} Balliett/Seton/Jordan sentence restored",
                   I18NFILE, new, old) for new, old, lang in _CAVEAT_ANCHORS]
    mutations += [(f"{I18NFILE}: {lang} K.N. Rao / Shyamasundara Dasa sentence restored",
                   I18NFILE, new, old) for new, old, lang in _PERSON_ANCHORS]
    mutations.append(("a ~1908 dating in rendered copy", "numerology.html",
                      "Origin: 20th-century Western numerology.",
                      "Origin: 20th-century Western numerology, ~1908."))
    mutations.append(("a bare new mention", "numerology_compat.html",
                      "Numerology Compatibility Check",
                      "Numerology Compatibility Check (after Kumar)"))
    mutations.append(("given names added (Jayant, Goodwin, Harish)",
                      "numerology_compat.html", "Numerology Compatibility Check",
                      "Numerology Compatibility Check (Jayant, Goodwin, Harish)"))
    mutations.append(("a new author in a numerology.py string literal", PYFILE,
                      '"This is a neutral pairing',
                      '"Per Kumar: This is a neutral pairing'))
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
    # The converse: provenance in a Jinja comment, a `#` comment or a docstring
    # must pass.
    for label, fname, tail in (
            ("an author in a {# #} comment", "numerology.html",
             "\n{# Johari §4 / Kumar Ch.1 #}\n"),
            ("an author in a # comment and a docstring", PYFILE,
             '\n# Johari §4, Kumar Ch.1\ndef _zz():\n    """Per Johari §7."""\n')):
        mutated = dict(texts)
        mutated[fname] = texts[fname] + tail
        if _problems(mutated):
            print(f"  FAIL  {label} — gate flagged provenance")
            failures += 1
        else:
            print(f"  ok    {label} — correctly ignored")
    return failures


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--self-test"]
    root = Path(args[0]) if args else TEMPLATES
    texts = {name: (root / name).read_text(encoding="utf-8") for name in FILES}
    texts[PYFILE] = (PKG / PYFILE).read_text(encoding="utf-8")
    texts[ROUTEFILE] = (PKG / ROUTEFILE).read_text(encoding="utf-8")
    texts[I18NFILE] = (PKG / I18NFILE).read_text(encoding="utf-8")

    problems = _problems(texts)
    for p in problems:
        print(f"FAIL — {p}")
    if problems:
        return 1

    print(f"Numerology template source and {PYFILE} string literals clean — "
          f"{len(_ANCHORS)} template + {len(_PY_ANCHORS)} literal + "
          f"{len(_ROUTE_ANCHORS)} SEO anchors present, {len(_CAVEAT_ANCHORS)} caveat "
          f"anchors present, {len(_ALLOWED)} allowed mention(s), no author named.")
    print("Self-test (each known defect must turn this gate red):")
    if _self_test(texts):
        print("FAIL — the gate does not bite. A gate that cannot fail is worse "
              "than none (#193).")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
