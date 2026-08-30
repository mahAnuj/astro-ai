#!/usr/bin/env python3
"""Verify that no chart rule cites a book this repo cannot open.

WHY THIS EXISTS
---------------
#216, #218. `chart.py` shipped twelve yoga rules carrying
`source="Brihat Parashara Hora Shastra"` or `"BPHS / Phaladeepika"`, and
`templates/result.html` renders that string to the reader as
`Source: Brihat Parashara Hora Shastra` under every yoga card. BPHS is not in
`data/`, is not one of the eight entries in `scripts/fetch_corpus.py`, and
never was — so not one of those citations was checkable by anybody, on this
machine or reading the site. Forty lines from one of them, the same file
documented the rule's orb as UNSOURCED.

A wrong rule is a bug. A wrong rule wearing a real book's name is worse,
because the citation tells the reader not to check. `knowledge/SOURCES.md`
used to license a bare `[BPHS]` for rules that are "universally cited"; that
licence is how an uncheckable attribution reached shipped code and a published
article, and it has been withdrawn. Nothing else stopped the next one.

WHAT IT CHECKS
--------------
1. Every `source=` on a `YogaResult(...)` or `ManglikRule(...)` in `chart.py`.
   A label may name a book only if `fetch_corpus.py` registers it, or if it is
   listed in `_UNHELD_ATTRIBUTIONS` below with a reason.
2. `Brihat Parashara Hora Shastra` / `BPHS` fails unconditionally. There is no
   ledger escape for it: that is the defect this gate is named for.
3. The ledgers are EXACT. An attribution that no longer appears in the code
   must be removed from its ledger, or this gate fails. A ledger that only
   grows becomes a list of things nobody looks at again.
4. Where the cited book is actually present in `data/`, the cited section
   (`§11.4.1`) must exist in its text. This is the check that makes the gate
   assert a citation rather than merely a spelling — a label can name a held
   book and still point at a section that is not there.
5. `templates/result.html` must not print an unregistered book name to the
   reader. Jinja comments (`{# … #}`) are stripped first: they do not render,
   and this file's own history note names the book it removed.

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
- Adding a ledger entry is how you justify an attribution nobody can check. If
  you are adding one to make a new citation green, you are the regression.
- Check 4 cannot run against a book that is missing from `data/`, which is the
  normal state of a fresh clone. It reports that PER CITATION, loudly, and does
  not silently count as verified. Say which books were present whenever you
  report on this gate (CLAUDE.md).
- The self-test runs on every invocation: it re-breaks #216 and #218 six ways
  — including on the page's own provenance line — and asserts this gate goes
  red on each. A gate that has never failed is not evidence (ARCHITECTURE.md).
  The count in this sentence is the length of `_MUTATIONS` plus the HTML one;
  keep it honest if you add another.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHART = ROOT / "src" / "astro_ai" / "chart.py"
RESULT_HTML = ROOT / "src" / "astro_ai" / "templates" / "result.html"

sys.path.insert(0, str(ROOT / "scripts"))

# The rule constructors whose `source=` reaches result.html. Both are in
# chart.py; if a third appears, add it here — an unlisted constructor is not
# checked, and this gate would pass vacuously over it.
_RULE_CTORS = frozenset({"YogaResult", "ManglikRule"})

# Never acceptable, ledger or no ledger. Spellings kept separate so a label
# saying "BPHS" is caught as surely as one spelling it out.
_FORBIDDEN: tuple[str, ...] = (
    "Brihat Parashara Hora Shastra",
    "BPHS",
    "Parashara Hora",
)

# Book titles that may legitimately appear in a citation but are NOT in
# `fetch_corpus.py`'s registry, with the reason each is still here.
#
# These are all in `_manglik_cancellations()`, which predates this gate and is
# outside #218's scope: it was audited for the ONE label that was not a
# citation at all (`mars_combust`, now disclosed as unsourced). The rest name
# real classical compendia we do not hold and cannot check — the same defect
# class as the BPHS labels, one step less severe because knowledge/
# vedic_reference.md §1.3 at least records where the rule set came from
# (Rao's Jagannath Hora rule-set) rather than asserting a first-hand reading.
#
# This ledger is a disclosure, not an approval. Shrinking it is work; growing
# it needs a reason written here.
_UNHELD_ATTRIBUTIONS: dict[str, str] = {
    "Jataka Parijata":
        "Manglik cancellations, via Rao's Jagannath Hora rule-set — "
        "knowledge/vedic_reference.md §1.3. Text not held; open (#216).",
    "Jataka Chandrika":
        "Manglik cancellation (Mars debilitated). Text not held; open (#216).",
    "Phaladeepika":
        "Manglik cancellations and mitigations. Text not held; open (#216).",
    "Muhurtha Chintamani":
        "Cancer/Leo lagna yogakaraka exclusion. Text not held; open (#216).",
}

# Labels that name no book at all. Each is either an honest disclosure of a
# gap, or a vague formula inherited from before this gate — and the two are
# listed apart on purpose, because a vague formula is a defect waiting and a
# disclosure is the fix.
_HONEST_DISCLOSURES: frozenset[str] = frozenset({
    "unsourced: absent from the classical Kuja-dosha antidote lists we hold",
})

_VAGUE_ATTRIBUTIONS: dict[str, str] = {
    "Classical compatibility practice":
        "venus_with_mars. Not a citation — the same shape of phrase as the "
        "'Classical matching practice' that #218 removed from mars_combust, "
        "and not audited by it. Open (#216).",
}


def _module_strings(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "…"` bindings, so an f-string using one resolves.

    `_RAO` is defined once and interpolated into every yoga label; reading the
    label without it would see `§11.4.1` and no book name, and pass.
    """
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            out[node.targets[0].id] = node.value.value
    return out


def _loop_bound_strings(fn: ast.AST) -> dict[str, list[str]]:
    """Candidate values for names a `for` loop unpacks out of a literal table.

    `_pancha_mahapurusha_yogas()` holds its five rules in a dict literal and
    builds each label as `f"{_RAO} §{section}"`, where `section` is a loop
    target. Statically that name has no single value, so `_label_variants` used
    to yield the placeholder `<section>` — which does not start with `<` once
    it is embedded in the f-string, so the guard missed it and NO SECTION CHECK
    RAN for any of the five.

    Rather than give up, over-approximate: every string literal in the function
    that has the SHAPE of a section number is a candidate. The gate then checks
    all five sections instead of none, and an over-approximation is the safe
    direction — a candidate that is not really reachable can only cause a
    spurious failure a human will notice, never a silent pass.
    """
    shaped = re.compile(r"^\d+(?:\.\d+)*$")
    pool = sorted({n.value for n in ast.walk(fn)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and shaped.match(n.value)})
    if not pool:
        return {}
    # Any name BOUND in the function, not just a `for` target. The real case
    # binds by tuple-unpacking an assignment:
    #     slug, name, effect, section = names[p.name]
    # so a for-targets-only version resolved nothing and the hole stayed open.
    # ast.Store covers both, and every other binding form.
    targets = {n.id for n in ast.walk(fn)
               if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    return {name: pool for name in targets}


def _label_variants(node: ast.AST, consts: dict[str, str],
                    locals_: dict[str, list[str]] | None = None) -> list[str]:
    """Every string this `source=` expression can evaluate to.

    Returns a LIST, not one string: `budha_aditya_yoga` appends its unsourced-
    orb disclosure conditionally, so the rule has two labels and both are
    printed to real readers. Checking only one of them would leave the branch
    that carries the disclosure unguarded — and that branch is the one #218 is
    about.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name):
        if node.id in consts:
            return [consts[node.id]]
        if locals_ and node.id in locals_:
            return list(locals_[node.id])
        return [f"<{node.id}>"]
    if isinstance(node, ast.JoinedStr):
        parts = [_label_variants(v, consts, locals_) for v in node.values]
        return _product(parts)
    if isinstance(node, ast.FormattedValue):
        return _label_variants(node.value, consts, locals_)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _product([_label_variants(node.left, consts, locals_),
                         _label_variants(node.right, consts, locals_)])
    if isinstance(node, ast.IfExp):
        return (_label_variants(node.body, consts, locals_)
                + _label_variants(node.orelse, consts, locals_))
    # A subscript, a call, anything computed at runtime: report it rather than
    # skip it. An unreadable label is an unchecked label.
    return [f"<unresolved:{type(node).__name__}>"]


def _product(parts: list[list[str]]) -> list[str]:
    """Concatenate one choice from each part, in order."""
    out = [""]
    for choices in parts:
        out = [acc + c for acc in out for c in choices]
    return out


def _citations(text: str) -> list[tuple[str, str]]:
    """(slug, label) for every rule-constructor `source=` in chart.py."""
    tree = ast.parse(text)
    consts = _module_strings(tree)
    found: list[tuple[str, str]] = []
    # Walk per enclosing function so loop-bound names can be resolved from the
    # literal table beside them. Module-level calls get an empty local map.
    scopes: list[tuple[ast.AST, dict[str, list[str]]]] = [(tree, {})]
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((fn, _loop_bound_strings(fn)))
    seen_calls: set[int] = set()
    for scope, locals_ in reversed(scopes):
      for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        if id(node) in seen_calls:
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id in _RULE_CTORS):
            continue
        seen_calls.add(id(node))
        src = next((k for k in node.keywords if k.arg == "source"), None)
        slug = next((k for k in node.keywords if k.arg == "slug"), None)
        slug_txt = "?"
        if slug is not None:
            slug_txt = "".join(_label_variants(slug.value, consts, locals_)[:1])
        if src is None:
            found.append((slug_txt, "<MISSING source= kwarg>"))
            continue
        for label in _label_variants(src.value, consts, locals_):
            found.append((slug_txt, label))
    return found


def _registry() -> tuple[dict[str, str], set[str]]:
    """(title -> filename, set of titles whose file is present in data/).

    Imported from `fetch_corpus.py` rather than restated, so the registry has
    exactly one definition. Restating it is how a gate ends up asserting
    against a list that has drifted from the one the corpus tools use.
    """
    import fetch_corpus  # noqa: PLC0415  — path is set up above

    titles = {b.title: b.filename for b in fetch_corpus.BOOKS}
    present = {b.title for b in fetch_corpus.BOOKS
               if (fetch_corpus.DATA_DIR / b.filename).exists()}
    return titles, present


def _cited_title(label: str, titles: dict[str, str]) -> str | None:
    """Which registered book, if any, this label names."""
    for title in titles:
        if title.lower() in label.lower():
            return title
    return None


def _book_text(filename: str) -> str | None:
    """The extracted text of one held book, or None if it cannot be read.

    Reuses `corpus_search._corpus()` so the extraction, its cache and its
    `-layout` flag are the ones every other sourcing claim in this repo rests
    on. It exits(2) when `data/` is absent, which is the fresh-clone case, so
    that is caught rather than propagated.
    """
    try:
        import corpus_search  # noqa: PLC0415

        books = corpus_search._corpus()
    except (SystemExit, Exception):  # noqa: BLE001 — any failure means "not verifiable"
        return None
    return books.get(filename) or books.get(Path(filename).name)


_SECTION_RE = re.compile(r"§\s*(\d+(?:\.\d+)*)")


def _problems(text: str, html: str) -> tuple[list[str], list[str]]:
    """(failures, notes). Notes are things this run could NOT verify."""
    fails: list[str] = []
    notes: list[str] = []
    titles, present = _registry()

    cites = _citations(text)
    if not cites:
        return ["no rule citations found at all — the anchors have moved, and "
                "a gate that cannot find its subject passes vacuously (#193)"], notes

    seen_unheld: set[str] = set()
    seen_vague: set[str] = set()
    section_checks: dict[str, set[str]] = {}

    for slug, label in cites:
        # ANYWHERE in the label, not just at the start. `_label_variants`
        # substitutes an unresolvable name with a `<name>` placeholder, and a
        # label built from a loop variable — `f"{_RAO} §{section}"` in
        # `_pancha_mahapurusha_yogas()` — resolves to
        #     'Rao, Vedic Astrology: An Integrated Approach §<section>'
        # which does NOT start with `<`. So it slipped past this guard, then
        # `_cited_title()` matched "Rao" and `_SECTION_RE` found no digits, so
        # NO SECTION CHECK RAN — for all five Pancha Mahapurusha yogas. QA
        # proved it: rewriting 11.4.1 -> 11.4.9 and 11.4.2 -> 77.7.7 left this
        # gate PASS at exit 0 and all 11 tests green, while the page printed
        # "Rao, Vedic Astrology: An Integrated Approach §77.7.7".
        #
        # That is the failure this file's own docstring forbids — "An
        # unreadable label is an unchecked label" — and it printed "all
        # resolvable" while doing it. A gate that cannot fail on a class it
        # advertises catching is the #193 defect, committed into the fix for
        # #216.
        if "<" in label:
            fails.append(
                f"{slug}: source is not a readable string literal ({label}). "
                "It is built at runtime, so no book or section in it can be "
                "checked. Make the label a literal, or add an explicit "
                "resolution for its construct here — do not leave it silent."
            )
            continue
        for bad in _FORBIDDEN:
            if bad.lower() in label.lower():
                fails.append(
                    f"{slug}: cites {bad!r}. That book is not in data/ and is not "
                    f"in fetch_corpus.py's registry, so the citation cannot be "
                    f"checked by anyone — this is #216 exactly. Cite the text you "
                    f"read the rule in."
                )
        title = _cited_title(label, titles)
        if title is not None:
            for sec in _SECTION_RE.findall(label):
                section_checks.setdefault(title, set()).add(sec)
            continue
        # ALL of them, not the first: "Jataka Parijata / Muhurtha Chintamani"
        # is one label naming two unheld books, and stopping at the first left
        # the second looking stale in the ledger.
        unheld = [u for u in _UNHELD_ATTRIBUTIONS if u.lower() in label.lower()]
        if unheld:
            seen_unheld.update(unheld)
            continue
        if label in _HONEST_DISCLOSURES:
            continue
        if label in _VAGUE_ATTRIBUTIONS:
            seen_vague.add(label)
            continue
        fails.append(
            f"{slug}: source {label!r} names no book in fetch_corpus.py's "
            f"registry and is in no ledger in this gate. Either cite a held "
            f"book, or say plainly that the rule is unsourced and add the "
            f"wording to _HONEST_DISCLOSURES."
        )

    # Ledgers are exact in both directions.
    for stale in sorted(set(_UNHELD_ATTRIBUTIONS) - seen_unheld):
        fails.append(f"_UNHELD_ATTRIBUTIONS lists {stale!r}, which no rule cites "
                     f"any more. Remove it — a ledger that only grows is a list "
                     f"nobody re-reads.")
    for stale in sorted(set(_VAGUE_ATTRIBUTIONS) - seen_vague):
        fails.append(f"_VAGUE_ATTRIBUTIONS lists {stale!r}, which no rule uses "
                     f"any more. Remove it.")

    # Cited sections must exist in the book, where the book is here to ask.
    for title, sections in sorted(section_checks.items()):
        filename = titles[title]
        if title not in present:
            notes.append(f"{title}: NOT in data/ — could not verify "
                         f"§{', §'.join(sorted(sections))}")
            continue
        body = _book_text(filename)
        if body is None:
            notes.append(f"{title}: present but not extractable — could not verify "
                         f"§{', §'.join(sorted(sections))}")
            continue
        for sec in sorted(sections):
            if not re.search(rf"^\s*{re.escape(sec)}(?!\d)", body, re.M):
                fails.append(f"cites {title} §{sec}, but no section heading "
                             f"{sec} appears in that book's text.")

    # The reader-facing page. Jinja comments do not render.
    rendered = re.sub(r"\{#.*?#\}", "", html, flags=re.S)
    for bad in _FORBIDDEN:
        if bad.lower() in rendered.lower():
            fails.append(f"result.html prints {bad!r} to the reader. Neither that "
                         f"book nor a way to check it is in this repo (#216).")
    for title in _UNHELD_ATTRIBUTIONS:
        if title.lower() in rendered.lower() and title not in _cited_in_html_ok(rendered):
            notes.append(f"result.html names {title!r}, which is not held. It "
                         f"arrives via a rule label; see _UNHELD_ATTRIBUTIONS.")
    return fails, notes


def _cited_in_html_ok(rendered: str) -> set[str]:
    """Titles the page names in its own prose rather than via a rule label.

    Rule labels reach the page through `{{ rule.source }}`, not as literal
    text, so any hard-coded occurrence is the page speaking for itself.
    """
    return {t for t in _UNHELD_ATTRIBUTIONS if f">{t}<" in rendered}


# ─── self-test ────────────────────────────────────────────────────────────
# Each mutation is a real defect, re-inserted. If any of them does not turn
# this gate red, the gate is decorative.
#
# The 4th field is the book a mutation needs on disk to be detectable at all.
# "" means none. A mutation whose book is missing is reported NOT EXERCISED,
# never quietly passed and never counted as survived: on a fresh clone the
# section check cannot run, and a self-test that failed there would make the
# whole gate red for an environment gap rather than a defect (#224).
_MUTATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("#216 as it shipped: a yoga cites BPHS",
     'source=f"{_RAO} §11.2.1",',
     'source="Brihat Parashara Hora Shastra",', ""),
    ("the compact spelling, which reads as a citation just as hard",
     'source=f"{_RAO} §11.2.1",',
     'source="BPHS / Phaladeepika",', ""),
    ("a plausible-sounding phrase that is not a citation",
     'source=f"{_RAO} §11.2.2",',
     'source="Classical yoga practice",', ""),
    ("#218's unsourced disclosure quietly deleted",
     'source="unsourced: absent from the classical Kuja-dosha antidote lists we hold",',
     'source="Classical matching practice",', ""),
    ("a held book cited to a section that is not in it",
     'source=f"{_RAO} §11.2.3",',
     'source=f"{_RAO} §11.2.9",', "Vedic Astrology: An Integrated Approach"),
)


def _self_test(text: str, html: str) -> list[str]:
    """Mutations that must fail the gate. Returns the ones that did not."""
    survived: list[str] = []
    _, present = _registry()
    for name, old, new, needs in _MUTATIONS:
        if needs and needs not in present:
            print(f"    NOT EXERCISED: {name} — {needs} is not in data/")
            continue
        if old not in text:
            survived.append(f"{name} — anchor {old!r} no longer in chart.py; "
                            f"re-point it (a mutation that cannot be applied "
                            f"proves nothing)")
            continue
        fails, _ = _problems(text.replace(old, new, 1), html)
        if not fails:
            survived.append(name)
        else:
            print(f"    red on: {name}")
    # And the page's own provenance line.
    bad_html = html.replace("</p>", " Compiled from Brihat Parashara Hora "
                                    "Shastra and Phaladeepika.</p>", 1)
    fails, _ = _problems(text, bad_html)
    if not fails:
        survived.append("result.html re-asserts BPHS in its provenance line")
    else:
        print("    red on: result.html re-asserts BPHS in its provenance line")
    return survived


def main(argv: list[str]) -> int:
    text = CHART.read_text(encoding="utf-8")
    html = RESULT_HTML.read_text(encoding="utf-8")

    fails, notes = _problems(text, html)
    for n in notes:
        print(f"NOT VERIFIED — {n}")
    for f in fails:
        print(f"FAIL — {f}")
    if fails:
        return 1

    cites = _citations(text)
    titles, present = _registry()
    print(f"{len(cites)} rule citations in chart.py, all resolvable.")
    print(f"corpus present: {len(present)}/{len(titles)} registered books — "
          f"{', '.join(sorted(present)) or 'none'}")
    if notes:
        print(f"{len(notes)} citation(s) named a book not on this machine and "
              f"were checked by NAME only. That is not a source verification.")
    print(f"disclosed gaps still open (#216): "
          f"{len(_UNHELD_ATTRIBUTIONS)} unheld book names, "
          f"{len(_VAGUE_ATTRIBUTIONS)} non-citations.")
    print("Self-test (each known defect must turn this gate red):")
    survived = _self_test(text, html)
    for s in survived:
        print(f"FAIL — mutation did not turn the gate red: {s}")
    if survived:
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
