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
2. `_EXPECTED_MENTIONS` may only be raised for a mention that DENIES the
   attribution, and the denial goes in the list next to it. If you are raising
   it to make a new "per Cheiro" green, you are the regression.
3. The self-test runs on every invocation: it re-inserts #172's two real
   attributions plus a bare new mention, and asserts this gate goes red on
   each. Keep it that way.
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

# Every Cheiro mention inside the spans, today, is a denial:
#   1. "NOT sourced to Cheiro, despite what this comment said until #172"
#   2. "Cheiro's Book of Numbers contains ZERO occurrences of …"
#   3. "0 hits in the Cheiro PDF (8,389 lines)"
#   4. "nothing may present it as Cheiro's"
#   5. "This block credited Cheiro until #172; it is not his"
#   6. "assigns Feng Shui texts, not Cheiro, as the source class"
#   7. "they are not Cheiro's (see the sourcing note …)"
_EXPECTED_MENTIONS = 7

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


def _problems(text: str) -> list[str]:
    spans, missing = _spans(text)
    problems = list(missing)

    mentions = 0
    for name, body in spans.items():
        for m in _ATTRIBUTION.finditer(body):
            if _NEGATED.search(body[max(0, m.start() - 12):m.start()]):
                continue  # "NOT sourced to Cheiro" is the fix, not the defect
            problems.append(f"{name}: attributes Lo Shu to Cheiro — {m.group(0)!r}")
        mentions += len(re.findall("cheiro", body, re.IGNORECASE))

    if mentions > _EXPECTED_MENTIONS:
        problems.append(
            f"{mentions} Cheiro mentions in the Lo Shu spans, expected at most "
            f"{_EXPECTED_MENTIONS}. A new one must be a denial, listed in "
            "_EXPECTED_MENTIONS next to the bump.")
    return problems


def _self_test(text: str) -> int:
    """Re-break #172's attributions; each mutation must turn the gate red."""
    mutations = (
        ("#172's docstring line",
         "Zeros in the DOB are excluded — the convention this code implements,",
         "Zeros in the DOB are excluded per Cheiro's classical rule."),
        ("#172's section source block",
         "# [UNSOURCED — widely cited, not in corpus]. The grid, the arrows, the",
         "# Source: Cheiro (Count Louis Hamon), *Cheiro's Book of Numbers*, the"),
        ("a new mention with no attributing verb",
         "    lo_shu: \"LoShuGrid | None\" = None",
         "    # Compare Cheiro here too.\n    lo_shu: \"LoShuGrid | None\" = None"),
    )
    failures = 0
    for label, old, new in mutations:
        if old not in text:
            print(f"  FAIL  {label}: anchor gone — re-point this mutation")
            failures += 1
            continue
        if _problems(text.replace(old, new, 1)):
            print(f"  ok    {label} — caught")
        else:
            print(f"  FAIL  {label} — gate stayed green on a known defect")
            failures += 1
    return failures


def main(argv: list[str]) -> int:
    text = Path(argv[1]).read_text(encoding="utf-8") if len(argv) > 1 else \
        SRC.read_text(encoding="utf-8")

    problems = _problems(text)
    for p in problems:
        print(f"FAIL — {p}")
    if problems:
        return 1

    print(f"Lo Shu spans clean — {_EXPECTED_MENTIONS} Cheiro mentions, all denials.")
    print("Self-test (each known defect must turn this gate red):")
    if _self_test(text):
        print("FAIL — the gate does not bite. A gate that cannot fail is worse "
              "than none (#193).")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
