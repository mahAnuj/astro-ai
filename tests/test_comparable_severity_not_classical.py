"""No surface may call "comparable severity" for two Manglik charts classical (#1369).

Raman's antidote list (knowledge/grahas.md section 12.4, book line 3642) says the
dosha is cancelled when both partners are Manglik, with no severity condition. "Comparable
severity" is Shubh Bhagya's own convention (`matching._severity_comparable`). Six /learn
pages, the FAQPage JSON-LD built from the registry, the matching notes, the natal LLM
instruction and vedic_reference.md rule 20 all said the opposite: that the classical
texts "require" it, or that it is "the classical requirement". Fixing the wording
once is not a gate; this is.

WHAT IS SCANNED is the SOURCES, not rendered pages, so the FAQPage JSON-LD (built from
learn_registry.py) is covered without a request:

  * `.py` files: parsed with `ast`, every string Constant (docstrings and f-string
    pieces included);
  * templates: tags and Jinja comments stripped, entities decoded, whitespace collapsed;
  * knowledge/vedic_reference.md: per LINE, because rule 20's cells are one table row.

THE RULE, per sentence (split on `. ; : ! ?` + whitespace, bullets and newlines): a
sentence that mentions comparability (`comparab`, `similarly strong/afflicted`) is
checked.

  * HARD phrases fail it always, even beside a disclosure ("texts require ..., but
    that is ours" is still the claim);
  * SOFT words ("classical", "the tradition", "the texts") fail it unless the SAME
    sentence says it is not scripture / names no severity condition / is ours.

This is a PHRASE test. It catches the wording it names, not every rewording; a new
way to say "the texts demand it" that avoids every pattern below passes it. The
positive pins at the bottom are the half that does not depend on phrasing, and the
unit cases use the sentences that shipped before the fix as fixtures, so a loosened
pattern goes red here rather than in review.
"""
from __future__ import annotations

import ast
import html
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
TEMPLATES = SRC / "templates"

_PY_FILES = ("learn_registry.py", "matching.py", "chart.py")
_VEDIC_REFERENCE = SRC / "knowledge" / "vedic_reference.md"

_TRIGGER = re.compile(r"comparab|similarly (?:strong|afflicted)", re.I)

# Always a defect when the sentence is about comparability. "ONLY when" is the
# shouted form chart.py's old instruction used, so it is case-sensitive.
_HARD = [
    re.compile(r"ONLY when"),
    re.compile(r"whole rule", re.I),
    re.compile(r"the qualifier", re.I),
    re.compile(r"classical (?:requirement|recommendation|solution)", re.I),
    re.compile(r"texts require", re.I),
    re.compile(r"rule asks", re.I),
    re.compile(r"is what the classical", re.I),
    re.compile(r"the tradition is describing", re.I),
]

# Words that attribute the condition to a tradition. Fine only beside a disclosure.
_SOFT = [
    re.compile(r"classical", re.I),
    re.compile(r"tradition (?:holds|asks|says)", re.I),
    re.compile(r"the (?:tradition|texts) ", re.I),
    re.compile(r"the sources we (?:work from|hold) (?:cite|list|give)", re.I),
]

_DISCLOSURE = [
    re.compile(r"not (?:found|scripture|a classical)", re.I),
    re.compile(r"no severity condition", re.I),
    re.compile(r"names no", re.I),
    re.compile(r"our own", re.I),
    re.compile(r"\bours\b", re.I),
    re.compile(r"Bhagya'?s own", re.I),
    re.compile(r"we (?:set|draw|treat)", re.I),
    re.compile(r"Shubh Bhagya (?:grades|sets|treats)", re.I),
]

_SPLIT = re.compile(r"[.;:!?]\s|•|\n")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if s.strip()]


def violations_in_text(text: str) -> list[str]:
    """Every sentence in `text` that calls comparable severity classical, with why."""
    out = []
    for s in _sentences(text):
        if not _TRIGGER.search(s):
            continue
        hard = next((p.pattern for p in _HARD if p.search(s)), None)
        if hard:
            out.append(f"HARD {hard!r}: {s}")
            continue
        soft = next((p.pattern for p in _SOFT if p.search(s)), None)
        if soft and not any(d.search(s) for d in _DISCLOSURE):
            out.append(f"SOFT {soft!r} with no disclosure: {s}")
    return out


def py_strings(source: str) -> str:
    """Every string Constant in a module, one per line (the scan splits on newlines)."""
    return "\n".join(
        n.value for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    )


def template_text(source: str) -> str:
    """Visible-ish text of a Jinja template: comments and tags gone, entities decoded."""
    s = re.sub(r"\{#.*?#\}", " ", source, flags=re.S)
    s = re.sub(r"\{%.*?%\}", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s))


def _surfaces() -> list[tuple[str, str]]:
    out = [(f"src/astro_ai/{n}", py_strings((SRC / n).read_text(encoding="utf-8")))
           for n in _PY_FILES]
    out += [(str(p.relative_to(SRC.parent.parent)), template_text(p.read_text(encoding="utf-8")))
            for p in sorted(TEMPLATES.rglob("*.html"))]
    # Per LINE, not per cell: rule 20's cells are one table row, and splitting on `|` would
    # strand its old "Classical compatibility rule" cell away from the "comparable severity" cell.
    out += [(f"vedic_reference.md:{i}", line)
            for i, line in enumerate(_VEDIC_REFERENCE.read_text(encoding="utf-8").splitlines(), 1)]
    return out


def test_scan_reaches_the_surfaces_it_claims_to():
    """A scan that silently finds nothing passes forever."""
    names = [n for n, _ in _surfaces()]
    for must in ("src/astro_ai/learn_registry.py", "src/astro_ai/matching.py",
                 "src/astro_ai/chart.py",
                 "src/astro_ai/templates/learn/manglik-dosh.html",
                 "src/astro_ai/templates/result.html",
                 "src/astro_ai/templates/manglik_check_result.html",
                 "src/astro_ai/templates/matching.html"):
        assert must in names, must
    reached = sum(1 for _, t in _surfaces() for s in _sentences(t) if _TRIGGER.search(s))
    assert reached >= 15, f"only {reached} comparability sentences found; the scan is not reading the sources"


def test_no_surface_calls_comparable_severity_classical():
    found = [f"{name}: {v}" for name, text in _surfaces() for v in violations_in_text(text)]
    assert not found, "\n".join(found)


# --- the scanner itself, on the sentences that shipped before #1369 (7b29d1a) -----------

_OLD_SENTENCES = [
    # matching.py _COMPARABILITY_BAND_SENTENCE
    "Classical texts require 'comparable severity' for this mutual cancellation but do "
    "not define the band — Bhagya treats equal or adjacent grades as comparable, and a "
    "low-versus-high pairing as not comparable.",
    # learn_registry.py manglik keypoint
    "• 'Comparable severity' is the classical requirement; the texts set no band, so "
    "Bhagya's own convention (state it as ours, not scripture) is that equal or adjacent "
    "grades are comparable",
    # manglik-dosh.html opener
    "Classical tradition holds that when both partners carry Manglik Dosh of comparable "
    "severity, the two doshas neutralise each other.",
    # result.html
    "Matching with another Manglik partner can still cancel the dosha mutually — but "
    "classical texts require the two partners to be of comparable severity, and they do "
    "not define the band, so Bhagya treats equal or adjacent grades as comparable.",
    # chart.py LLM instruction, same sentence minus the disclosure
    "The traditional remedy — a partner who also carries the dosha — classically holds "
    "only when both carry it at comparable strength, so give it as that condition.",
    # learn_registry.py FAQ
    "the rule asks for two doshas of comparable severity: it is the symmetry that cancels.",
    "The cancellation rests on the two charts being similarly afflicted, as the classical "
    "recommendation says.",
]


@pytest.mark.parametrize("sentence", _OLD_SENTENCES)
def test_the_scanner_flags_the_old_wording(sentence):
    assert violations_in_text(sentence), sentence


def test_a_hard_phrase_fails_even_beside_a_disclosure():
    assert violations_in_text(
        "Classical texts require comparable severity, but that band is ours, not scripture.")


@pytest.mark.parametrize("sentence", [
    "One held antidote list names no severity condition; comparable severity is Bhagya's "
    "own condition, not scripture.",
    "Many retellings add that the two doshas should be of comparable strength, but we have "
    "not found that condition in a book we hold, so we set one and name it as ours.",
    "Comparable severity is Bhagya's own condition, not scripture.",
    "The classical cancellation list has no sentence about severity.",  # not about comparability
])
def test_the_scanner_passes_the_new_wording(sentence):
    assert violations_in_text(sentence) == [], sentence


def test_py_strings_and_template_text_do_what_the_scan_assumes():
    assert "Classical texts require comparable" in py_strings(
        'X = ("Classical texts require "\n     "comparable severity")')
    assert "comparable" not in template_text("{# comparable #}<p>a</p>")
    assert template_text("<em>of</em> &ldquo;meets&rdquo;\n  itself") == " of “meets” itself"


# --- positive pins: they do not depend on phrasing -------------------------------------

def test_manglik_dosh_page_says_the_held_list_names_no_severity_condition(client):
    r = client.get("/learn/manglik-dosh/")
    assert r.status_code == 200
    assert "names no severity condition" in template_text(r.text)


def _manglik(severity: str):
    from astro_ai.chart import ManglikDetails

    return ManglikDetails(
        is_manglik=True, houses=(7,), primary_house=7,
        severity=severity, cancellations=(), effective_status="present",
    )


@pytest.mark.parametrize("branch, groom, bride", [
    ("both_comparable", "high", "moderate"),
    ("both_incomparable", "high", "low"),
])
def test_both_manglik_notes_say_the_held_list_names_no_severity_condition(branch, groom, bride):
    from astro_ai.matching import mangal_dosh_verdict

    v = mangal_dosh_verdict(_manglik(groom), _manglik(bride))
    assert v.branch == branch, f"fixture no longer reaches {branch!r}: got {v.branch!r}"
    assert "no severity condition" in v.note, v.note
