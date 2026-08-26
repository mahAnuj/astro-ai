#!/usr/bin/env python3
"""Verify that nothing in numerology.py's Lo Shu material credits Cheiro.

WHY THIS EXISTS
---------------
#172. `numerology.py:224-231` said "NOT sourced to Cheiro … nothing may present
it as Cheiro's", and forty lines below it `:278-281` carried
"Source: Cheiro (Count Louis Hamon), *Cheiro's Book of Numbers*" for the grid,
plus "zeros excluded per Cheiro" in `compute_lo_shu_grid`. The refutation and
the claim shipped together for months. Cheiro's book contains no Lo Shu: the
recorded measurement is in `templates/numerology.html:302-306` (2026-08-10,
`pdftotext -layout`, 0 hits for 'lo shu'/'loshu'/'lo-shu' in the Cheiro PDF and
across the corpus), and `knowledge/numerology.md` §13.2 files Lo Shu under
"Still missing from both books".

Nothing guarded that, so it could regress the same way it arrived. Cheiro stays
legitimate elsewhere in the file (Chaldean table, compound numbers 10-52,
name/birth accord) — so this gate is scoped to the Lo Shu spans only.

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. If an anchor below no longer matches, re-point it. A missing anchor is a
   FAIL, not a skip: a gate that cannot find its subject passes vacuously,
   which is #193.
2. Every Cheiro mention in the spans must be a denial listed in `_DENIALS`,
   and the expected count is derived from that list. Adding an entry is how
   you justify a new mention; if you are adding one to make a new
   "per Cheiro" green, you are the regression.
3. Deleting or rewording a denial is a FAIL too, and this is the reason the
   list exists rather than a bare number: QA re-broke #172 by restoring the
   old "Cheiro / Chinese classical" header and trimming one denial to hold
   the count at 7, and a count-only check passed it.
4. The self-test runs on every invocation: it re-inserts #172's two real
   attributions, a bare new mention, and the three denial-tampering
   mutations, and asserts this gate goes red on each. Keep it that way.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "numerology.py"

# (name, first line contains, last line starts with / span ends before)
_SPANS: tuple[tuple[str, str, str], ...] = (
    ("lo_shu field comment", "Lo Shu 3×3 birth-number matrix", r"^\s*lo_shu:"),
    ("Lo Shu section", "─── Lo Shu (birth-number matrix)", r"^# ───"),
    ("compute_lo_shu_grid", "def compute_lo_shu_grid(", r"^(def |# ───|@dataclass)"),
)

# Every Cheiro mention inside the spans, today, is a denial. Each fragment
# below is matched against the flattened span text and carries exactly one of
# those mentions, so a denial that is deleted, reworded or swapped for an
# attribution fails this gate even when the mention COUNT is unchanged.
_DENIALS: tuple[str, ...] = (
    "NOT sourced to Cheiro, despite what this comment said until #172",
    "Cheiro's Book of Numbers contains ZERO occurrences",
    "0 hits in the Cheiro PDF (8,389 lines)",
    "nothing may present it as Cheiro's",
    "This block credited Cheiro until #172; it is not his",
    "assigns Feng Shui texts, not Cheiro, as the source class",
    "they are not Cheiro's (see the sourcing note",
)

# One mention per denial and no mention that is not one — zero slack. The
# slack matters: _ATTRIBUTION does not match "— Cheiro / Chinese classical",
# so a restored section header is caught by this count and by nothing else.
# A HIGHER count is a new mention nobody justified. A LOWER one means a denial
# was deleted, which is exactly how the attribution came back last time: the
# refutation goes, the claim stays, and the total drops. So `!=`, never `>`.
_EXPECTED_MENTIONS = len(_DENIALS)

# Phrases that bind Cheiro to the material as its SOURCE. Each is a form that
# has actually appeared in this file.
_ATTRIBUTION = re.compile(
    r"(?:per|from|source:|sourced to|attributed to|according to|credited to|"
    r"cross-referenced (?:with|from))\s+(?:the\s+)?Cheiro"
    r"|Cheiro'?s?\s+(?:own\s+|classical\s+)?(?:rule|grid|square|system|method|convention)"
    r"|Cheiro\s*\+",
    re.IGNORECASE,
)
_NEGATED = re.compile(r"(?:not|never|no)\s+$", re.IGNORECASE)


def _spans(text: str) -> tuple[dict[str, str], list[str]]:
    """Return {span name: flattened span text} and a list of missing anchors."""
    lines = text.splitlines()
    out: dict[str, str] = {}
    missing: list[str] = []
    for name, start_marker, end_pat in _SPANS:
        start = next((i for i, l in enumerate(lines) if start_marker in l), None)
        if start is None:
            missing.append(f"{name}: start anchor {start_marker!r} not found")
            continue
        end_re = re.compile(end_pat)
        end = next((j for j in range(start + 1, len(lines)) if end_re.match(lines[j])),
                   len(lines))
        # Comments wrap mid-sentence, so flatten before matching phrases.
        body = " ".join(l.lstrip().lstrip("#").strip() for l in lines[start:end + 1])
        out[name] = re.sub(r"\s+", " ", body)
    return out, missing


def _mention_count(spans: dict[str, str]) -> int:
    """The MEASURED number of Cheiro mentions across the spans."""
    return sum(len(re.findall("cheiro", body, re.IGNORECASE))
               for body in spans.values())


def _problems(text: str) -> list[str]:
    spans, missing = _spans(text)
    problems = list(missing)

    for name, body in spans.items():
        for m in _ATTRIBUTION.finditer(body):
            if _NEGATED.search(body[max(0, m.start() - 12):m.start()]):
                continue  # "NOT sourced to Cheiro" is the fix, not the defect
            problems.append(f"{name}: attributes Lo Shu to Cheiro — {m.group(0)!r}")

    joined = " ".join(spans.values())
    for denial in _DENIALS:
        if denial not in joined:
            problems.append(
                f"denial gone from the Lo Shu spans: {denial!r}. Restore it. "
                "Drop it from _DENIALS only if what it refutes is gone too.")

    mentions = _mention_count(spans)
    if mentions != _EXPECTED_MENTIONS:
        problems.append(
            f"{mentions} Cheiro mentions in the Lo Shu spans, expected exactly "
            f"{_EXPECTED_MENTIONS} — one per entry in _DENIALS. More means an "
            "unjustified new mention; fewer means a denial was deleted.")
    return problems


def _self_test(text: str) -> int:
    """Re-break #172's attributions; each mutation must turn the gate red.

    The last three are QA's escapes. With the count check written `>`,
    `_problems()` returned nothing for any of them: each deletes or rewrites a
    denial instead of adding a mention, so the count never rises and a
    count-only gate stays green.
    """
    mutations: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
        ("#172's docstring line", ((
            "Zeros in the DOB are excluded — the convention this code implements,",
            "Zeros in the DOB are excluded per Cheiro's classical rule."),)),
        ("#172's section source block", ((
            "# [UNSOURCED — widely cited, not in corpus]. The grid, the arrows, the",
            "# Source: Cheiro (Count Louis Hamon), *Cheiro's Book of Numbers*, the"),)),
        ("a new mention with no attributing verb", ((
            "    lo_shu: \"LoShuGrid | None\" = None",
            "    # Compare Cheiro here too.\n    lo_shu: \"LoShuGrid | None\" = None"),)),
        ("a denial swapped for an attribution, count held at 7", ((
            "    # nothing may present it as Cheiro's.\n",
            "    # the grid is Cheiro's teaching.\n"),)),
        ("a denial deleted outright, count down to 6", ((
            "    # NOT sourced to Cheiro, despite what this comment said until #172.\n",
            ""),)),
        # The historical defect verbatim: #172's own header, back again, with a
        # denial trimmed so the total still reads 7.
        ("the pre-#172 header restored, count held at 7 by trimming a denial", (
            ("# ─── Lo Shu (birth-number matrix) — unsourced; see note below ─────────",
             "# ─── Lo Shu (birth-number matrix) — Cheiro / Chinese classical ────────"),
            ("    # / 'lo-shu' return 0 hits in the Cheiro PDF (8,389 lines) and 0\n",
             "    # / 'lo-shu' return 0 hits in that PDF (8,389 lines) and 0\n"))),
    )
    failures = 0
    for label, edits in mutations:
        mutated = text
        for old, new in edits:
            if old not in mutated:
                mutated = None
                break
            mutated = mutated.replace(old, new, 1)
        if mutated is None:
            print(f"  FAIL  {label}: anchor gone — re-point this mutation")
            failures += 1
            continue
        if _problems(mutated):
            print(f"  ok    {label} — caught")
        else:
            print(f"  FAIL  {label} — gate stayed green on a known defect")
            failures += 1
    return failures


def main(argv: list[str]) -> int:
    # `--self-test` is accepted for symmetry with verify_muhurat_tables.py,
    # which has a real one. Here the self-test always runs, so it is a no-op
    # rather than a mode — but it should not be read as a file path and die.
    args = [a for a in argv[1:] if a != "--self-test"]
    text = Path(args[0]).read_text(encoding="utf-8") if args else \
        SRC.read_text(encoding="utf-8")

    problems = _problems(text)
    for p in problems:
        print(f"FAIL — {p}")
    if problems:
        return 1

    # The measured count, not _EXPECTED_MENTIONS: a gate that reports the
    # number it assumed rather than the one it counted states a falsehood the
    # moment they diverge, which is the defect class this whole file guards.
    mentions = _mention_count(_spans(text)[0])
    print(f"Lo Shu spans clean — {mentions} Cheiro mentions, all denials.")
    print("Self-test (each known defect must turn this gate red):")
    if _self_test(text):
        print("FAIL — the gate does not bite. A gate that cannot fail is worse "
              "than none (#193).")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
