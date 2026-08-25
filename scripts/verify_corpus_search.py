#!/usr/bin/env python3
"""Gate: corpus_search matches Sanskrit case endings without re-opening the
false-SOURCED direction.

WHY THIS EXISTS
---------------
#217: `corpus_search.py "maudhya" --absent` printed a clean absence while
`Maudhyam` sits in Rao Vol. I. The boundary regex was `s?(?![a-z])`, so it
could only see a suffix that is APPENDED to the term. Sanskrit a-stems do not
append — they REPLACE the stem's final -a. `maudhyena` does not contain
`maudhya` at all, which is why no relaxation of the trailing boundary could
have fixed this through the search term itself.

Measured through the real pipeline — `variants()` then `_pat()`, which is what
`_hits()` below does — #217's first suggestion (an appended suffix set) reaches
4 of the 5 inflected forms and its second (`(?![a-z]{4,})`) reaches all 5, by
way of the truncated stem `maudhy` that `variants()` already emits. So the
second one is not refuted on form count; it is rejected for what else it finds,
and the measurement is recorded next to `_ENDINGS` in `corpus_search.py`. The
figures once carried here (1/5 and 4/5) and in the #217 commit message (0/5 and
3/5) do not reproduce and are superseded there.

A false ABSENT is the dangerous direction: it retires a gap that is still
open, or licenses inventing a rule the corpus already carries. But the
opposite error is worse still, and this file has to hold both ends at once —
the boundary was tightened in the first place because substring matching found
`vasya` inside `amavasya` and `washy` inside `wishy-washy`, reporting Vashya
as sourced when the corpus does not contain it.

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. **This gate never reads the corpus.** `data/` currently holds 1 of the 8
   source books, and the one carrying `Maudhyam` (`book1-for-CD.pdf`) is not
   among them. A gate whose evidence is a book that may or may not be on the
   disk passes for the wrong reason on most machines. Every string below is an
   in-file fixture; `_corpus()` is never called.
2. **Never re-implement the regex in the test body.** Ask `variants()` and
   `_pat()` for the real pattern and assert on hardcoded expectations. Two
   tests in this repo reimplemented their subject and would have passed
   forever.
3. Run `--self-test` after editing. It applies two mutants — the pre-#217
   pattern, and the 6-character stem floor lowered on its own — and asserts
   this gate goes red for each. A gate that has never failed is not evidence,
   and a fixture that only fires when two things break at once guards neither.

EXIT CODES
    0  PASS
    1  FAIL
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus_search as cs  # noqa: E402


# ─── Fixtures ───────────────────────────────────────────────────────────
#
# SYNTHETIC, not quotations. They are shaped like corpus lines so the gate
# exercises the same path a search does (the search lowercases each line, then
# tries every spelling), but nothing here is offered as a citation. Four of
# the five inflected forms carry endings #217 names (-am, -ena, -asya); the
# locative -e is added because it is the shortest a-stem ending and so the one
# most exposed to the boundary rules. All are standard declensions, not a
# choice this gate is free to make.
_MUST_MATCH: tuple[tuple[str, str], ...] = (
    ("maudhya", "Maudhyam of Venus is discussed in the next chapter."),
    ("maudhya", "results caused by maudhyena are held to be weak"),
    ("maudhya", "the effect of maudhyasya is set out below"),
    ("maudhya", "a planet in maudhye loses its power to do good"),
    ("maudhya", "MAUDHYAM AND ITS CANCELLATION"),
    # The plural "s" the boundary has always allowed, and which cost 6 and 12
    # real hits the one time it was dropped. "koota" not "navamsa": mutation
    # showed the navamsa plural is ALSO reachable through the new -as ending
    # (navams + as), so it would have kept passing with `s?` deleted. "kuta"
    # is four letters, below the stem-truncation floor, so it has nothing but
    # `s?` to catch "kutas" — it fails the moment the plural is dropped.
    ("koota", "the seven kutas are counted in order"),
    ("navamsa", "see the Navamsa-lagna for the same rule"),
)

# Each of these is a real false positive this tool has produced, the
# overcorrection that the obvious #217 fix would produce, or — for the last
# one — a false positive a single loosening of the pattern would produce.
_MUST_NOT_MATCH: tuple[tuple[str, str, str], ...] = (
    ("vashya", "the amavasya tithi falls on the thirtieth",
     "'vasya' inside 'amavasya' — reported Vashya as sourced when it is not"),
    ("vashya", "a wishy-washy answer helps nobody",
     "'washy' inside 'wishy-washy' — the same false SOURCED verdict, in Cheiro"),
    ("maudhya", "the Maudhyamika school is Buddhist, not astrological",
     "#217's overcorrection: an ending set that ran on would swallow this"),
    ("dasha", "he dashes the hopes of the native",
     "the ending set must stay a Sanskrit case set behind its 6-character "
     "floor — 'dash' plus an English-looking 'es' swallows ordinary prose"),
    # The line above needs TWO mutations to fire (drop the floor AND add an
    # English ending), so on its own it left the 6-character floor unguarded.
    # This one bites on the floor alone: at a floor of 3, `bala` truncates to
    # `bal`, and `bal` + the locative `-e` is the English word "bale".
    ("bala", "the cart carried a single bale of hay",
     "the 6-character floor alone keeps 'bal' + '-e' out of 'bale' — a "
     "3-letter stem plus a Sanskrit case ending lands inside English prose"),
)


def _hits(term: str, line: str) -> list[str]:
    """Every spelling of `term` that matches `line`, via the real pipeline."""
    low = line.lower()
    return [v for v in cs.variants(term) if cs._pat(v).search(low)]


def gate_1_inflections() -> list[str]:
    failures = []
    for term, line in _MUST_MATCH:
        got = _hits(term, line)
        mark = "ok " if got else "MISS"
        print(f"    {mark} {term:<10} {line[:58]:<58} {','.join(got) or '—'}")
        if not got:
            failures.append(
                f"{term!r} did not match {line!r} — false ABSENT, the #217 defect")
    return failures


def gate_2_false_positives() -> list[str]:
    failures = []
    for term, line, why in _MUST_NOT_MATCH:
        got = _hits(term, line)
        mark = "ok " if not got else "HIT "
        print(f"    {mark} {term:<10} {line[:58]:<58} {','.join(got) or '—'}")
        if got:
            failures.append(f"{term!r} matched {line!r} via {got} — {why}")
    return failures


def gate_3_structure() -> list[str]:
    """The two halves of the pattern that #217 was not allowed to touch."""
    failures = []
    lead = cs._pat("maudhya").pattern
    if not lead.startswith("(?<![a-z])"):
        failures.append(
            "the leading (?<![a-z]) is gone — that lookbehind is the only thing "
            "keeping 'vasya' out of 'amavasya'; #217 is a trailing-side change")
    print(f"    {'ok ' if lead.startswith('(?<![a-z])') else 'BAD'} leading "
          f"lookbehind present")

    # The endings must stay an EXPLICIT alternation. A quantified letter run
    # ("stem" + [a-z]{1,5}) reaches maudhyamika and every other word that
    # merely starts the same way — the false-SOURCED direction again, and the
    # reason the ending list is written out longhand.
    body = re.sub(r"\(\?<!\[a-z\]\)|\(\?!\[a-z\]\)", "", lead)
    ok_explicit = "[a-z]{" not in body
    print(f"    {'ok ' if ok_explicit else 'BAD'} endings are an explicit "
          f"alternation, not a letter run")
    if not ok_explicit:
        failures.append("the ending set has become a quantified [a-z] run; "
                        "write the endings out or it will match any word "
                        "sharing the stem")

    # Devanagari still matches as a substring: भकूट appears inside भकूटगुणाः,
    # and requiring a boundary would miss every compound. What this catches is
    # the realistic mutation, a \b boundary — measured False on दुष्टभकूटपरिहारः
    # and भकूटगुणाः. What it does NOT catch is deleting the Devanagari dispatch
    # entirely: the Latin branch's (?<![a-z])/(?![a-z]) are both satisfied by
    # Devanagari neighbours, so the two branches diverge only where Devanagari
    # is glued to an ASCII letter (`bhakootभकूटdosha`), which no OCR of these
    # books produces. That mutant survives, knowingly.
    deva = cs._pat("भकूट")
    ok = bool(deva.search("दुष्टभकूटपरिहारः"))
    print(f"    {'ok ' if ok else 'BAD'} devanagari matches inside a compound")
    if not ok:
        failures.append("भकूट no longer matches inside दुष्टभकूटपरिहारः — the "
                        "Devanagari branch must stay substring-matched")
    return failures


def run_gates(prefix: str = "") -> int:
    total = 0
    for title, fn in (("1  Sanskrit inflections match (#217)", gate_1_inflections),
                      ("2  historical false positives stay rejected",
                       gate_2_false_positives),
                      ("3  pattern structure preserved", gate_3_structure)):
        print(f"{prefix}Gate {title}")
        failures = fn()
        for f in failures:
            print(f"{prefix}      FAIL: {f}")
        total += len(failures)
        print()
    return total


def _old_pat(v: str) -> "re.Pattern[str]":
    """The pre-#217 pattern: an appended plural and nothing else."""
    if any(ord(ch) > 0x0900 for ch in v):
        return re.compile(re.escape(v))
    return re.compile(rf"(?<![a-z]){re.escape(v)}s?(?![a-z])")


def _floor3_pat(v: str) -> "re.Pattern[str]":
    """`_pat` with ONLY the 6-character stem floor lowered to 3.

    Everything else — the endings, both lookarounds, the Devanagari branch — is
    left exactly as it ships. QA found the floor was the one load-bearing piece
    no fixture guarded on its own: the `dasha`/"he dashes" line needs the floor
    lowered AND an English ending added before it fires, so it could not fail
    under a single mutation.
    """
    if any(ord(ch) > 0x0900 for ch in v):
        return re.compile(re.escape(v))
    body = rf"{re.escape(v)}s?"
    if v.endswith("a") and len(v) >= 3:
        body += "|" + re.escape(v[:-1]) + "(?:" + "|".join(cs._ENDINGS) + ")"
    return re.compile(rf"(?<![a-z])(?:{body})(?![a-z])")


def self_test() -> int:
    """Mutate the pattern and assert this gate goes red for each mutant.

    A gate that has never failed is not evidence, and a gate that fails only
    when two things break at once leaves the second one unguarded.
    """
    mutants = (
        ("the pre-#217 pattern", _old_pat),
        ("the 6-character stem floor lowered to 3, alone", _floor3_pat),
    )
    original = cs._pat
    bad = 0
    for label, mutant in mutants:
        print(f"SELF-TEST — {label}; the gate must FAIL.")
        cs._pat = mutant
        try:
            failures = run_gates(prefix="  ")
        finally:
            cs._pat = original
        if not failures:
            print(f"SELF-TEST FAILED — {label} passed every gate, so this "
                  "gate does not detect it.")
            bad += 1
        else:
            print(f"SELF-TEST OK — {failures} failure(s) with {label}.")
        print()
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    print("Verifying corpus_search spelling patterns (fixtures only, no corpus).")
    print()
    failures = run_gates()
    if failures:
        print(f"FAIL — {failures} problem(s). A miss here is a false ABSENT "
              "verdict (#217); a hit in Gate 2 is a false SOURCED verdict, "
              "which is worse — it retires a gap that is still open.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
