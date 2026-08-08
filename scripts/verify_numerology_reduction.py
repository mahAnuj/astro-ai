#!/usr/bin/env python3
"""Verify the numerology reduction policy — who keeps 11/22/33, and who does not.

WHY THIS EXISTS
---------------
`numerology._reduce` used to be `_reduce(n)` with the master-number policy
hard-wired inside it: 11, 22 and 33 always survived. Nothing said so at any call
site, so every call site inherited that decision silently — and four separate
issues were filed against the consequences before anyone noticed they were the
same defect:

    #162  `_life_path`'s docstring said "sum of all digits" while the body
          reduced year, month and day separately and summed those. Two different
          methods, one of them written down and not executed.
    #164  `_birthday_number` returned 11 for the 11th and 22 for the 22nd, but
          `_BIRTHDAY_MEANING` had no such rows and Johari's own birthday lists
          file 11 and 29 under 2 and 22 under 4. The number rendered as blank.
    #169  `_personal_year` could return 11/22/33 into a panel that captions
          itself "Cycles 1-9", matching no branch of the score.
    #179  the same undeclared policy proposed as a user-facing toggle, i.e. the
          question "which convention does this site use?" reaching the reader
          because the code could not answer it either.

**The date tables in this repo shipped wrong four times because gates asserted
nothing.** This one asserts the policy itself, in the source, so a fifth
undeclared call site cannot appear quietly.

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. **Never re-derive an expected value from `numerology.py`.** A gate whose
   expected side came from the implementation it is testing proves only that the
   code is self-consistent — which is exactly the blindness that let #162 ship a
   docstring and a body that disagreed. Every anchored row below carries its
   source next to it, and Gate 4 re-implements all three rules inline from the
   corpus text, importing nothing from `numerology.py` for the expected side.
2. **`_reduce` must not be rebound.** Not `_r = _reduce` at module scope, not as
   a default argument (`def f(..., _reduce=_reduce)`), not captured into a dict
   of handlers. Gate 5 corrupts `numerology._reduce` as a module global and
   relies on the call sites looking it up at call time; a rebind would freeze the
   original function into the caller, silently stop the bite test biting, and
   still print PASS. Gate 1 checks for this.
3. Do not tune `numerology.py` to silence a gate. A red gate here means a number
   a user sees has moved.

  Gate 1 - the policy is declared in the source. Two halves, both required. The
      signature must still carry `preserve_masters` as KEYWORD_ONLY with NO
      default — a default is what made the policy inheritable in the first
      place, so it is forbidden rather than merely discouraged. Then the file is
      parsed with `ast` and every `_reduce(...)` call site is read out with its
      enclosing function; the resulting map must equal EXPECTED_POLICY exactly.
      An unexpected NEW function name is a failure too: that is how a fifth
      undeclared call site gets caught on the day it is written.

  Gate 2 - anchored values, each row carrying its source. Hand arithmetic from
      the stated rules, plus Johari's own worked example (1934-05-12 -> 7, plain
      `pdftotext` line 302), which owes this codebase nothing. This gate also
      asserts the OLD values are GONE — `_life_path('1990-01-11') != 4`, the
      11th's birthday number `!= 11` — so a partial revert reddens rather than
      passing on the half that was not reverted.

  Gate 3 - ranges and table reachability over a 1900-2030 census. Ranges in both
      directions: every value the code produces must be in its declared range,
      AND every key of every interpretation table must actually occur. A table
      row nothing can reach is dead interpretation text (#146's abujha table
      rotted exactly that way), and a value with no row renders as blank (#164).
      `_LIFE_PATH`'s 11/22/33 rows are proved LIVE here, which is what says they
      must not be deleted alongside `_BIRTHDAY_MEANING`'s.

  Gate 4 - independent re-derivation. All three rules re-implemented inline from
      the corpus text. Includes the `lp_base` invariance claim — `_life_path`'s
      docstring asserts "profiles, remedies and compatibility verdicts key off
      the base number and are therefore unaffected", and that is checked over
      47,847 dates rather than believed. The measured 1940-2012 change
      distribution must reproduce the recorded table exactly; drift there means
      the method changed again.

  Gate 5 - bite test (`--self-test`). Two corruptions, each restored in a
      `finally`. Gate 1 reads the SOURCE FILE and therefore cannot see a
      monkeypatch — it stays green under both corruptions by construction, and
      is exercised instead by the file-corruption procedure in the QA plan.

Usage:  uv run python scripts/verify_numerology_reduction.py
        uv run python scripts/verify_numerology_reduction.py --self-test
"""

from __future__ import annotations

import ast
import inspect
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import numerology as num  # noqa: E402

SOURCE_PATH = REPO_ROOT / "src" / "astro_ai" / "numerology.py"

# --------------------------------------------------------------------------
# Gate 1 - the policy, restated here so the source has something to disagree with
# --------------------------------------------------------------------------
# Function name -> the literal `preserve_masters` its `_reduce` call must pass.
# This is the whole policy of the module in four lines. It is written here and
# checked against the AST rather than read out of the AST, because a map derived
# from the file can never disagree with the file.
#
#   _personal_year    False   corpus §12.8 gives the cycle a range of 1-9, and
#                             the panel captions itself "Cycles 1-9" (#169)
#   _birthday_number  False   corpus §2.1 states the range 1-9; Johari ch.2
#                             calls it "a simple whole number" (#164)
#   _sum_letters      True    Destiny / Soul Urge / Personality / Name Number —
#                             11/22/33 are part of the letter-value framework
#   _life_path        True    masters kept, on the final all-digits total (#162)
EXPECTED_POLICY: dict[str, bool] = {
    "_personal_year": False,
    "_birthday_number": False,
    "_sum_letters": True,
    "_life_path": True,
}

# --------------------------------------------------------------------------
# Gate 2 - anchored values, each with its provenance
# --------------------------------------------------------------------------
# Life Path = add every digit of the date, reduce, stop at 11/22/33.
# The arithmetic is written out so a reader can check each row WITHOUT running
# this script or reading `numerology.py`.
#
# (iso, expected, the arithmetic, the source of the row)
ANCHOR_LIFE_PATH: tuple[tuple[str, int, str, str], ...] = (
    ("1934-05-12", 7, "5+1+2+1+9+3+4 = 25 -> 7",
     "JOHARI'S OWN WORKED EXAMPLE — Numerology: With Tantra, Ayurveda, and "
     "Astrology, ch.2 'Destiny Number', plain pdftotext line 302. This row owes "
     "this codebase nothing: it is the corpus stating the rule and then applying "
     "it to a date."),
    ("1990-01-11", 22, "1+9+9+0+0+1+1+1 = 22 (master, kept)",
     "hand arithmetic from Johari's all-digits rule. THE CASE #162 IS ABOUT: the "
     "old reduce-parts-then-sum method gave 4 here."),
    ("1994-12-04", 3, "1+9+9+4+1+2+0+4 = 30 -> 3",
     "hand arithmetic; a plain non-master date, unchanged by the method switch"),
    ("1980-04-22", 8, "1+9+8+0+0+4+2+2 = 26 -> 8",
     "hand arithmetic; day 22 in the date must NOT make the Life Path a master"),
)

# Birthday number = day of month reduced to 1-9, masters dropped.
# (day, expected, arithmetic, source)
ANCHOR_BIRTHDAY: tuple[tuple[int, int, str, str], ...] = (
    (11, 2, "1+1 = 2",
     "corpus §2.1 states the range 1-9; §4's birthday lists file 11 AND 29 under "
     "psychic number 2. Johari ch.2: 'obtained by making a simple whole number of "
     "the date of birth' (plain pdftotext lines 273-275) — no master exception."),
    (22, 4, "2+2 = 4", "corpus §4 files 22 under psychic number 4"),
    (29, 2, "2+9 = 11 -> 1+1 = 2",
     "corpus §4 files 29 under psychic number 2 — note this one reduces THROUGH "
     "11, so it is the row that proves masters are not being caught mid-flight"),
    (13, 4, "1+3 = 4", "hand arithmetic; ordinary two-digit day"),
    (12, 3, "1+2 = 3", "hand arithmetic; ordinary two-digit day"),
)

# Personal Year = month digits + day digits + target-year digits, reduced 1-9.
# (birth iso, target year, expected, arithmetic, source)
ANCHOR_PERSONAL_YEAR: tuple[tuple[str, int, int, str, str], ...] = (
    ("1990-01-01", 2007, 2, "(0+1) + (0+1) + (2+0+0+7) = 11 -> 1+1 = 2",
     "hand arithmetic from Kumar Ch.1 with corpus §12.8's 1-9 range. This row is "
     "the #169 case: the sum lands ON 11, so it is exactly where a preserved "
     "master would escape into a panel captioned 'Cycles 1-9'."),
)

# The values the OLD code gave. Asserting these are GONE is what makes a PARTIAL
# revert red — reverting `_life_path` alone while leaving `_birthday_number`
# fixed would otherwise leave half the anchors above still green.
ANCHOR_OLD_VALUES: tuple[tuple[str, str, int, str], ...] = (
    ("_life_path", "1990-01-11", 4,
     "the old reduce-parts-then-sum method: reduce(1990)=1, reduce(01)=1, "
     "reduce(11)=11, sum 13 -> 4"),
    ("_birthday_number", "2000-01-11", 11,
     "the old always-preserve-masters reduction returned the master 11 for the "
     "11th, which had no row in _BIRTHDAY_MEANING and rendered blank (#164)"),
)

# --------------------------------------------------------------------------
# Gate 3 / 4 census
# --------------------------------------------------------------------------
# Every date in this range. 47,847 of them; the whole census costs well under a
# second, so there is no reason to narrow it. The width is what makes the
# reachability half of Gate 3 meaningful — 33 as a Life Path is rare enough that
# a short census would not see one and the assertion would prove nothing.
CENSUS_START = date(1900, 1, 1)
CENSUS_END = date(2030, 12, 31)
CENSUS_DATES = 47847  # asserted, so a silently shrunk census cannot pass quietly

# Personal Year is a function of the TARGET year as well as the birth date, so
# the census sweeps sixteen target years rather than pinning 2026. A policy that
# only holds in the current year is not a policy.
PY_TARGET_YEARS = range(2020, 2036)

# `_reduce` is swept directly over this range too.
REDUCE_SWEEP = range(1, 10001)

MASTERS = (11, 22, 33)
BASE_OF_MASTER = {11: 2, 22: 4, 33: 6}

# --------------------------------------------------------------------------
# Gate 4 - the recorded measurement of the method change
# --------------------------------------------------------------------------
# Old Life Path (reduce year, month and day separately, sum, reduce again —
# masters preserved at every step) vs new (sum all eight digits, reduce once,
# masters kept). Measured over 1940-2012, one row per (old -> new) pair.
#
# Required to match EXACTLY, not approximately: this is the number that says
# which method is running. A different distribution means the method moved
# again, and the whole point of this file is that such a move cannot be silent.
DIVERGENCE_1940_2012: dict[tuple[int, int], int] = {
    (6, 33): 1295,
    (2, 11): 986,
    (22, 4): 634,
    (4, 22): 434,
    (11, 2): 216,
    (33, 6): 33,
}
DIVERGENCE_1940_2012_TOTAL = 3598
DIVERGENCE_1940_2012_DATES = 26664

# Two further windows, recorded as (changed, total). Different spans give
# different rates because master-producing digit sums are not uniform across
# decades; pinning three of them stops a single lucky window being quoted.
DIVERGENCE_WINDOWS: dict[tuple[int, int], tuple[int, int]] = {
    (1930, 2025): (4492, 35064),
    (1980, 2025): (1612, 16802),
    (1940, 2012): (DIVERGENCE_1940_2012_TOTAL, DIVERGENCE_1940_2012_DATES),
}

# Personal Year: how often the old always-preserve-masters reduction returned a
# master that the corpus range does not admit. Target year 2026, dates 1940-2012.
PY_DROPOUT = (2555, 26664)
PY_DROPOUT_TARGET = 2026
PY_DROPOUT_WINDOW = (1940, 2012)


# --------------------------------------------------------------------------
# Independent re-implementations. NOTHING below imports from numerology.py.
# --------------------------------------------------------------------------

def _red_1_9(n: int) -> int:
    """Reduce to a single digit. No master exception — corpus §2.1 / §12.8."""
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def _red_masters(n: int) -> int:
    """Reduce, stopping at 11, 22 or 33 — Johari's Destiny Number convention."""
    while n > 9 and n not in MASTERS:
        n = sum(int(c) for c in str(n))
    return n


def _ref_life_path(iso: str) -> int:
    """Johari ch.2: add every digit of the date, reduce, keep masters."""
    return _red_masters(sum(int(c) for c in iso.replace("-", "")))


def _ref_birthday(iso: str) -> int:
    """Johari ch.2 / corpus §2.1: the day of month as a simple whole number."""
    return _red_1_9(int(iso[8:10]))


def _ref_personal_year_kumar(iso: str, target_year: int) -> int:
    """Kumar Ch.1 in its LITERAL form: int(month) + int(day) + the year itself.

    `numerology._personal_year` sums the DIGITS of the month, day and year
    instead. Digit-summing preserves value mod 9, so under full reduction the two
    forms agree — but that is an equivalence which holds only because masters are
    dropped, and the module's docstring claims it. Writing Kumar's form here
    checks the claim rather than restating it.
    """
    return _red_1_9(int(iso[5:7]) + int(iso[8:10]) + target_year)


def _ref_old_life_path(iso: str) -> int:
    """The method that was replaced: reduce year, month and day separately.

    Masters preserved at every step, which is what the single old no-argument
    `_reduce` did. Kept here — and only here — so Gate 4 can measure the change
    and so the `lp_base` invariance claim can be checked against something.
    """
    return _red_masters(
        _red_masters(int(iso[0:4])) + _red_masters(int(iso[5:7]))
        + _red_masters(int(iso[8:10]))
    )


def _ref_old_personal_year(iso: str, target_year: int) -> int:
    """The old Personal Year: same sum, but masters survived the reduction."""
    return _red_masters(
        sum(int(c) for c in iso[5:7]) + sum(int(c) for c in iso[8:10])
        + sum(int(c) for c in str(target_year))
    )


def _base(n: int) -> int:
    """A master number's underlying base. 11->2, 22->4, 33->6, else itself."""
    return BASE_OF_MASTER.get(n, n)


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------

def build_census() -> dict[str, object]:
    """Every date 1900-01-01..2030-12-31, run through the live functions.

    Every call goes through the MODULE (`num._life_path`, not a name bound at
    import) so that Gate 5's monkeypatches are visible here. Binding these would
    make the bite test lie.
    """
    isos: list[str] = []
    d = CENSUS_START
    while d <= CENSUS_END:
        isos.append(d.isoformat())
        d += timedelta(days=1)

    lp = [num._life_path(x) for x in isos]
    bd = [num._birthday_number(x) for x in isos]
    py = {y: [num._personal_year(x, y) for x in isos] for y in PY_TARGET_YEARS}
    return {"isos": isos, "lp": lp, "bd": bd, "py": py}


# --------------------------------------------------------------------------
# Gate 1 - the policy is declared in the source
# --------------------------------------------------------------------------

def _kw_literal(call: ast.Call) -> tuple[str, object]:
    """Read `preserve_masters` off a `_reduce(...)` call.

    Returns ("missing", None), ("nonliteral", <source-ish>) or ("literal", bool).
    A `**kwargs` splat counts as non-literal: it is unreadable from the source,
    which is the whole property this gate exists to protect.
    """
    for kw in call.keywords:
        if kw.arg is None:
            return ("nonliteral", "**kwargs splat")
        if kw.arg == "preserve_masters":
            v = kw.value
            if isinstance(v, ast.Constant) and isinstance(v.value, bool):
                return ("literal", v.value)
            return ("nonliteral", ast.dump(v))
    return ("missing", None)


def _reduce_call_sites(tree: ast.AST) -> list[tuple[str, int, tuple[str, object]]]:
    """(enclosing function name, line, keyword reading) for every `_reduce(...)`."""
    sites: list[tuple[str, int, tuple[str, object]]] = []

    def walk(node: ast.AST, fname: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, child.name)
                continue
            if (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id == "_reduce"):
                sites.append((fname, child.lineno, _kw_literal(child)))
            walk(child, fname)

    walk(tree, "<module>")
    return sites


def _rebinds_of_reduce(tree: ast.AST) -> list[str]:
    """Places where `_reduce` is bound to another name or frozen as a default.

    Either would defeat Gate 5: the corrupted module global would never be looked
    up, the bite test would find nothing, and this script would print PASS while
    detecting nothing at all.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Name) and node.value.id == "_reduce":
                names = ", ".join(t.id for t in node.targets
                                  if isinstance(t, ast.Name))
                found.append(f"line {node.lineno}: `{names} = _reduce` (alias)")
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.value, ast.Name) and node.value.id == "_reduce":
                found.append(f"line {node.lineno}: annotated alias of _reduce")
        elif isinstance(node, ast.arguments):
            for default in list(node.defaults) + [d for d in node.kw_defaults if d]:
                if isinstance(default, ast.Name) and default.id == "_reduce":
                    found.append(
                        f"line {default.lineno}: _reduce frozen as a default argument"
                    )
    return found


def gate_1_policy_declared() -> list[str]:
    failures: list[str] = []

    # --- (a) the signature itself.
    try:
        sig = inspect.signature(num._reduce)
    except (TypeError, ValueError) as exc:
        print(f"  FAIL could not read signature of _reduce: "
              f"{type(exc).__name__}: {exc}")
        return [f"inspect.signature(numerology._reduce) raised {exc}"]

    param = sig.parameters.get("preserve_masters")
    if param is None:
        print("  FAIL signature  _reduce has no `preserve_masters` parameter")
        failures.append(
            "numerology._reduce has no `preserve_masters` parameter. Its "
            f"signature is {sig}. The whole policy of this module is that whether "
            "11/22/33 survive is decided AT THE CALL SITE — without this "
            "parameter it is decided inside _reduce again, which is the state "
            "issues #162, #164, #169 and #179 were all filed against."
        )
    else:
        ok_kind = param.kind is inspect.Parameter.KEYWORD_ONLY
        ok_default = param.default is inspect.Parameter.empty
        print(f"  {'ok  ' if ok_kind else 'FAIL'} signature  preserve_masters kind "
              f"= {param.kind.name} (must be KEYWORD_ONLY)")
        print(f"  {'ok  ' if ok_default else 'FAIL'} signature  preserve_masters "
              f"default = {'<empty>' if ok_default else param.default!r} "
              "(must be <empty>)")
        if not ok_kind:
            failures.append(
                f"preserve_masters is {param.kind.name}, not KEYWORD_ONLY. "
                "Positionally, `_reduce(n, True)` reads as nothing at all at the "
                "call site — the reader cannot tell which of the four policies is "
                "being asked for, which is precisely the unreadability this gate "
                "exists to prevent."
            )
        if not ok_default:
            failures.append(
                f"preserve_masters has default {param.default!r}. A DEFAULT IS "
                "FORBIDDEN HERE, not merely discouraged: a default is what makes "
                "the policy INHERITABLE. The next call site written will silently "
                "take whatever this default happens to be, exactly as all four of "
                "#162 / #164 / #169 / #179 did when the policy lived inside the "
                "function body. Delete the default and make each new call site "
                "state its own choice."
            )

    # --- (b) the call sites, read out of the source with ast.
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sites = _reduce_call_sites(tree)

    print(f"  {len(sites)} `_reduce(...)` call site(s) found in "
          f"{SOURCE_PATH.relative_to(REPO_ROOT)}:")

    observed: dict[str, bool] = {}
    for fname, lineno, (kind, value) in sorted(sites, key=lambda s: s[1]):
        if kind == "literal":
            print(f"    line {lineno:>5}  {fname:<20} preserve_masters={value}")
            if fname in observed and observed[fname] != value:
                failures.append(
                    f"{fname} calls _reduce with BOTH preserve_masters=True and "
                    "=False. One function, two policies — say which number is "
                    "which, or split the function."
                )
            observed[fname] = bool(value)
        elif kind == "missing":
            print(f"    line {lineno:>5}  {fname:<20} preserve_masters MISSING")
            failures.append(
                f"{fname} (line {lineno}) calls _reduce WITHOUT preserve_masters. "
                "The parameter has no default on purpose, so this is a TypeError "
                "at runtime — but it is caught here because an undeclared call "
                "site is the defect itself, not merely a crash."
            )
        else:
            print(f"    line {lineno:>5}  {fname:<20} preserve_masters NON-LITERAL")
            failures.append(
                f"{fname} (line {lineno}) passes a non-literal preserve_masters "
                f"({value}). The policy must be readable from the source without "
                "running anything: a computed flag means nobody — including this "
                "gate — can say what convention that number uses."
            )

    print(f"  policy map read from source: {observed}")
    print(f"  policy map expected        : {EXPECTED_POLICY}")

    if observed != EXPECTED_POLICY:
        for fname in sorted(set(observed) - set(EXPECTED_POLICY)):
            failures.append(
                f"NEW `_reduce` call site in {fname}() "
                f"(preserve_masters={observed[fname]}) that EXPECTED_POLICY does "
                "not know about. This is the fifth-call-site case this gate was "
                "written for. Decide the convention deliberately, record the "
                "corpus section that justifies it in numerology.py, add the "
                "function to EXPECTED_POLICY here, and check whether its "
                "interpretation table has rows for the values it can now produce."
            )
        for fname in sorted(set(EXPECTED_POLICY) - set(observed)):
            failures.append(
                f"{fname}() no longer calls _reduce at all (expected "
                f"preserve_masters={EXPECTED_POLICY[fname]}). Either it was "
                "renamed, or its reduction was inlined — and an inlined reduction "
                "is a policy that has escaped this gate entirely."
            )
        for fname in sorted(set(EXPECTED_POLICY) & set(observed)):
            if observed[fname] != EXPECTED_POLICY[fname]:
                failures.append(
                    f"{fname}() passes preserve_masters={observed[fname]}, policy "
                    f"says {EXPECTED_POLICY[fname]}. This is a user-visible change "
                    "in a number, not a refactor: check the interpretation table "
                    "for that number has rows for 11/22/33 before flipping it to "
                    "True, and check nothing renders those rows before flipping it "
                    "to False."
                )

    # --- (c) _reduce must not be rebound — see the module docstring.
    rebinds = _rebinds_of_reduce(tree)
    print(f"  {'ok  ' if not rebinds else 'FAIL'} no rebinding of _reduce "
          "(alias or default argument)")
    for where in rebinds:
        failures.append(
            f"_reduce is rebound — {where}. Gate 5 corrupts `numerology._reduce` "
            "as a module global and depends on every call site looking it up at "
            "call time. A rebind freezes the original function into the caller, "
            "so the bite test stops biting AND STILL PRINTS PASS. That is worse "
            "than having no gate."
        )
    return failures


# --------------------------------------------------------------------------
# Gate 2 - anchored values
# --------------------------------------------------------------------------

def gate_2_anchors() -> list[str]:
    failures: list[str] = []

    for iso, want, arithmetic, source in ANCHOR_LIFE_PATH:
        got = num._life_path(iso)
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'} life_path      {iso} -> {got:<3} "
              f"want {want:<3}  [{arithmetic}]")
        print(f"       source: {source}")
        if not ok:
            failures.append(
                f"_life_path({iso!r}) = {got}, anchored value is {want} "
                f"({arithmetic}). Source: {source} — do NOT change this row to "
                "match the code."
            )

    for day, want, arithmetic, source in ANCHOR_BIRTHDAY:
        iso = f"2000-01-{day:02d}"
        got = num._birthday_number(iso)
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'} birthday       day {day:<3} -> "
              f"{got:<3} want {want:<3}  [{arithmetic}]")
        print(f"       source: {source}")
        if not ok:
            failures.append(
                f"_birthday_number({iso!r}) = {got}, anchored value is {want} "
                f"({arithmetic}). Source: {source}"
            )

    for iso, target, want, arithmetic, source in ANCHOR_PERSONAL_YEAR:
        got = num._personal_year(iso, target)
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'} personal_year  {iso} @ {target} -> "
              f"{got:<3} want {want:<3}  [{arithmetic}]")
        print(f"       source: {source}")
        if not ok:
            failures.append(
                f"_personal_year({iso!r}, {target}) = {got}, anchored value is "
                f"{want} ({arithmetic}). Source: {source}"
            )

    # The old values must be GONE. Without this, reverting one function while
    # leaving the other fixed leaves half the rows above green.
    for fname, iso, old_value, how in ANCHOR_OLD_VALUES:
        got = getattr(num, fname)(iso)
        ok = got != old_value
        print(f"  {'ok  ' if ok else 'FAIL'} old-value gone {fname}({iso}) = "
              f"{got}, must NOT be {old_value}")
        print(f"       the old behaviour: {how}")
        if not ok:
            failures.append(
                f"{fname}({iso!r}) returned {old_value} — the OLD value. {how}. "
                "This is a revert, whole or partial. Note that a partial revert "
                "can leave the other anchors above green, which is exactly why "
                "this check exists separately."
            )

    print(f"  {len(ANCHOR_LIFE_PATH)} Life Path, {len(ANCHOR_BIRTHDAY)} Birthday, "
          f"{len(ANCHOR_PERSONAL_YEAR)} Personal Year anchor(s), plus "
          f"{len(ANCHOR_OLD_VALUES)} old-value(s) asserted absent")
    return failures


# --------------------------------------------------------------------------
# Gate 3 - ranges and table reachability
# --------------------------------------------------------------------------

def gate_3_ranges(census: dict[str, object]) -> list[str]:
    failures: list[str] = []
    isos: list[str] = census["isos"]          # type: ignore[assignment]
    lp: list[int] = census["lp"]              # type: ignore[assignment]
    bd: list[int] = census["bd"]              # type: ignore[assignment]
    py: dict[int, list[int]] = census["py"]   # type: ignore[assignment]

    n = len(isos)
    print(f"  census {CENSUS_START}..{CENSUS_END} — {n} date(s), Personal Year "
          f"swept over target years {PY_TARGET_YEARS.start}-"
          f"{PY_TARGET_YEARS.stop - 1}")
    if n != CENSUS_DATES:
        failures.append(
            f"the census is {n} dates, not the recorded {CENSUS_DATES}. Either the "
            "range moved or the build is broken; a shrunk census is how a "
            "reachability assertion stops proving anything while still passing."
        )

    lp_legal = set(range(1, 10)) | set(MASTERS)
    bad_lp = {(isos[i], v) for i, v in enumerate(lp) if v not in lp_legal}
    bad_bd = {(isos[i], v) for i, v in enumerate(bd) if not 1 <= v <= 9}
    bad_py = {(isos[i], y, v) for y, col in py.items()
              for i, v in enumerate(col) if not 1 <= v <= 9}

    print(f"  {'ok  ' if not bad_lp else 'FAIL'} life_path      in 1-9 + "
          f"{MASTERS}  ({len(bad_lp)} violation(s))")
    print(f"  {'ok  ' if not bad_bd else 'FAIL'} birthday       in 1-9          "
          f"({len(bad_bd)} violation(s))")
    print(f"  {'ok  ' if not bad_py else 'FAIL'} personal_year  in 1-9          "
          f"({len(bad_py)} violation(s))")

    if bad_lp:
        failures.append(
            f"{len(bad_lp)} date(s) give a Life Path outside 1-9 + {MASTERS}, "
            f"e.g. {sorted(bad_lp)[:5]}"
        )
    if bad_bd:
        failures.append(
            f"{len(bad_bd)} date(s) give a Birthday Number outside 1-9, e.g. "
            f"{sorted(bad_bd)[:5]}. Corpus §2.1 states the range as 1-9, and "
            "_BIRTHDAY_MEANING has no rows outside it — an 11 here renders as "
            "blank text on the page (#164)."
        )
    if bad_py:
        failures.append(
            f"{len(bad_py)} (date, target year) pair(s) give a Personal Year "
            f"outside 1-9, e.g. {sorted(bad_py)[:5]}. The panel captions itself "
            "'Cycles 1-9' and the score has no branch for a master (#169)."
        )

    # --- reachability, both directions.
    py_seen = {v for col in py.values() for v in col}
    bd_seen = set(bd)
    lp_seen = set(lp)

    if set(num._PERSONAL_YEAR_THEME) != set(range(1, 10)):
        failures.append(
            f"_PERSONAL_YEAR_THEME keys are {sorted(num._PERSONAL_YEAR_THEME)}, "
            "expected exactly 1-9. Master rows were removed because "
            "_personal_year cannot produce them; re-adding one is an "
            "interpretation nobody can ever be shown."
        )
    missing_py = sorted(set(range(1, 10)) - py_seen)
    # The marker covers BOTH directions plus the table keys, so a line showing
    # 11/22/33 among the observed values can never print `ok`.
    py_line_ok = (not missing_py and not (py_seen - set(range(1, 10)))
                  and set(num._PERSONAL_YEAR_THEME) == set(range(1, 10)))
    print(f"  {'ok  ' if py_line_ok else 'FAIL'} _PERSONAL_YEAR_THEME keys "
          f"{sorted(num._PERSONAL_YEAR_THEME)}, values observed "
          f"{sorted(py_seen)}")
    if missing_py:
        failures.append(
            f"_PERSONAL_YEAR_THEME rows {missing_py} were never produced anywhere "
            "in the census — unreachable interpretation text."
        )

    master_bd_keys = sorted(k for k in num._BIRTHDAY_MEANING if k in MASTERS)
    missing_bd = sorted(set(range(1, 10)) - bd_seen)
    bd_line_ok = not master_bd_keys and not missing_bd and not (
        bd_seen - set(range(1, 10)))
    print(f"  {'ok  ' if bd_line_ok else 'FAIL'} _BIRTHDAY_MEANING keys "
          f"{sorted(num._BIRTHDAY_MEANING)} — master keys present: "
          f"{master_bd_keys or 'none'}, values observed {sorted(bd_seen)}")
    if master_bd_keys:
        failures.append(
            f"_BIRTHDAY_MEANING has master key(s) {master_bd_keys}, but "
            "_birthday_number reduces fully to 1-9 and can never produce them. "
            "An unreachable row is how #146's abujha table rotted; delete them "
            "rather than leaving them as evidence of a policy that is not in force."
        )
    if missing_bd:
        failures.append(
            f"_BIRTHDAY_MEANING rows {missing_bd} never occur in the census, which "
            "means either the table has a key the rule cannot reach or the census "
            "is not sweeping every day of the month."
        )

    live_masters = sorted(m for m in MASTERS if m in lp_seen)
    have_rows = sorted(m for m in MASTERS if m in num._LIFE_PATH)
    print(f"  {'ok  ' if live_masters == list(MASTERS) else 'FAIL'} _LIFE_PATH "
          f"master rows {have_rows} — observed in census: {live_masters}")
    for m in MASTERS:
        if m not in lp_seen:
            failures.append(
                f"Life Path {m} never occurs over {CENSUS_START}..{CENSUS_END}. It "
                "must: masters are kept on the all-digits total, and if one is "
                "unreachable then _LIFE_PATH's row for it is dead text."
            )
        elif m not in num._LIFE_PATH:
            failures.append(
                f"_LIFE_PATH has no row for {m}, but the census produces it "
                f"{lp.count(m)} time(s). THESE ROWS ARE LIVE AND MUST NOT BE "
                "DELETED. _BIRTHDAY_MEANING's and _PERSONAL_YEAR_THEME's master "
                "rows went because those two numbers reduce fully; Life Path does "
                "not, and a real reader lands here."
            )
    missing_lp = sorted(set(range(1, 10)) - lp_seen)
    if missing_lp:
        failures.append(
            f"Life Path value(s) {missing_lp} never occur in the census — the "
            "index is not spanning its range."
        )

    # --- _reduce swept directly.
    bad_reduce: list[tuple[int, int]] = []
    bad_diff: list[tuple[int, int, int]] = []
    differed = 0
    for i in REDUCE_SWEEP:
        plain = num._reduce(i, preserve_masters=False)
        kept = num._reduce(i, preserve_masters=True)
        if not 1 <= plain <= 9:
            bad_reduce.append((i, plain))
        if kept != plain:
            differed += 1
            if kept not in MASTERS or _base(kept) != plain:
                bad_diff.append((i, plain, kept))

    print(f"  {'ok  ' if not bad_reduce else 'FAIL'} _reduce(n, "
          f"preserve_masters=False) in 1-9 for n in "
          f"{REDUCE_SWEEP.start}..{REDUCE_SWEEP.stop - 1} "
          f"({len(bad_reduce)} violation(s))")
    print(f"  {'ok  ' if not bad_diff else 'FAIL'} preserve_masters=True differs "
          f"only by landing on {MASTERS}: {differed} of "
          f"{len(REDUCE_SWEEP)} values differ, {len(bad_diff)} of them illegally")
    if bad_reduce:
        failures.append(
            f"_reduce(..., preserve_masters=False) left {len(bad_reduce)} value(s) "
            f"outside 1-9, e.g. {bad_reduce[:5]}"
        )
    if bad_diff:
        failures.append(
            f"{len(bad_diff)} value(s) where preserve_masters=True differs from "
            f"False by something other than stopping at {MASTERS}, e.g. "
            f"{bad_diff[:5]} as (n, False-result, True-result). The two modes must "
            "differ ONLY in whether the reduction halts on a master — never in "
            "which base number they land on."
        )
    if differed == 0:
        failures.append(
            "preserve_masters=True and =False gave identical results for every n "
            f"in {REDUCE_SWEEP.start}..{REDUCE_SWEEP.stop - 1}. The flag does "
            "nothing, so every call site's declared policy is decoration."
        )
    return failures


# --------------------------------------------------------------------------
# Gate 4 - independent re-derivation
# --------------------------------------------------------------------------

def gate_4_rederivation(census: dict[str, object]) -> list[str]:
    failures: list[str] = []
    isos: list[str] = census["isos"]          # type: ignore[assignment]
    lp: list[int] = census["lp"]              # type: ignore[assignment]
    bd: list[int] = census["bd"]              # type: ignore[assignment]
    py: dict[int, list[int]] = census["py"]   # type: ignore[assignment]

    # --- (a) Life Path: all digits, reduce, keep masters.
    bad_lp = [(isos[i], lp[i], _ref_life_path(isos[i]))
              for i in range(len(isos)) if lp[i] != _ref_life_path(isos[i])]
    print(f"  {'ok  ' if not bad_lp else 'FAIL'} (a) life_path vs inline "
          f"all-digits rule: {len(isos) - len(bad_lp)}/{len(isos)} agree")
    if bad_lp:
        failures.append(
            f"{len(bad_lp)} date(s) where _life_path disagrees with the inline "
            f"all-digits rule, e.g. {bad_lp[:5]} as (date, code, reference). "
            "Johari ch.2: 'the addition of the date, month, and year of birth', "
            "worked example at plain pdftotext line 302."
        )

    # --- (b) Birthday: int(day), reduce to 1-9.
    bad_bd = [(isos[i], bd[i], _ref_birthday(isos[i]))
              for i in range(len(isos)) if bd[i] != _ref_birthday(isos[i])]
    print(f"  {'ok  ' if not bad_bd else 'FAIL'} (b) birthday vs inline "
          f"reduce-to-1-9: {len(isos) - len(bad_bd)}/{len(isos)} agree")
    if bad_bd:
        failures.append(
            f"{len(bad_bd)} date(s) where _birthday_number disagrees with the "
            f"inline rule, e.g. {bad_bd[:5]} as (date, code, reference)"
        )

    # --- (c) Personal Year against KUMAR'S LITERAL FORM, not our digit-sum one.
    bad_py: list[tuple[str, int, int, int]] = []
    py_checked = 0
    for y, col in py.items():
        for i, v in enumerate(col):
            py_checked += 1
            ref = _ref_personal_year_kumar(isos[i], y)
            if v != ref:
                bad_py.append((isos[i], y, v, ref))
    print(f"  {'ok  ' if not bad_py else 'FAIL'} (c) personal_year vs KUMAR'S "
          f"LITERAL form int(mo)+int(d)+year: {py_checked - len(bad_py)}/"
          f"{py_checked} agree")
    if bad_py:
        failures.append(
            f"{len(bad_py)} (date, year) pair(s) where _personal_year disagrees "
            f"with Kumar's literal formula, e.g. {bad_py[:5]} as (date, target, "
            "code, reference). The module docstring CLAIMS these two forms are "
            "equivalent because digit-summing preserves value mod 9 — an "
            "equivalence that holds only while masters are dropped. A failure "
            "here means either the formula moved or a master is surviving."
        )

    # --- (d) lp_base invariance. THE CLAIM IN _life_path's OWN DOCSTRING.
    bad_base = [(isos[i], _ref_old_life_path(isos[i]), lp[i])
                for i in range(len(isos))
                if _base(_ref_old_life_path(isos[i])) != _base(lp[i])]
    print(f"  {'ok  ' if not bad_base else 'FAIL'} (d) lp_base invariance "
          f"old-vs-new over {len(isos)} date(s): {len(bad_base)} mismatch(es), "
          "0 required")
    if bad_base:
        failures.append(
            f"{len(bad_base)} date(s) where the OLD and NEW Life Path methods land "
            f"on different BASE numbers, e.g. {bad_base[:5]} as (date, old, new). "
            "_life_path's docstring asserts 'profiles, remedies and compatibility "
            "verdicts key off the base number and are therefore unaffected' — this "
            "is the check that claim rests on, and it has just failed. A digit sum "
            "is congruent to its value mod 9, and 11/22/33 are 2/4/6, so the two "
            "methods can only ever differ by master-vs-base. Differing by base "
            "means one of them is not a digit sum at all."
        )

    # --- (e) the measured change distribution, exactly.
    for (lo, hi), (want_changed, want_total) in sorted(DIVERGENCE_WINDOWS.items()):
        total = changed = 0
        counts: Counter[tuple[int, int]] = Counter()
        for i, iso in enumerate(isos):
            y = int(iso[:4])
            if not lo <= y <= hi:
                continue
            total += 1
            old = _ref_old_life_path(iso)
            if old != lp[i]:
                changed += 1
                counts[(old, lp[i])] += 1
        pct = (100.0 * changed / total) if total else 0.0
        want_pct = (100.0 * want_changed / want_total) if want_total else 0.0
        ok = (changed, total) == (want_changed, want_total)
        print(f"  {'ok  ' if ok else 'FAIL'} (e) Life Path method change "
              f"{lo}-{hi}: {changed}/{total} = {pct:.2f}%  "
              f"(recorded {want_changed}/{want_total} = {want_pct:.2f}%)")
        if not ok:
            failures.append(
                f"over {lo}-{hi} the old and new Life Path methods differ on "
                f"{changed} of {total} dates; the recorded measurement is "
                f"{want_changed} of {want_total}. This number is what says WHICH "
                "method is running. Do not update it to match — find out what "
                "moved."
            )
        if (lo, hi) == (1940, 2012):
            for shift in sorted(set(counts) | set(DIVERGENCE_1940_2012),
                                key=lambda s: -DIVERGENCE_1940_2012.get(s, 0)):
                got_n = counts.get(shift, 0)
                want_n = DIVERGENCE_1940_2012.get(shift, 0)
                row_ok = got_n == want_n
                print(f"        {'ok  ' if row_ok else 'FAIL'} {shift[0]:>2} -> "
                      f"{shift[1]:<2}  {got_n:>5}  (recorded {want_n})")
                if not row_ok:
                    failures.append(
                        f"Life Path shift {shift[0]} -> {shift[1]} occurs {got_n} "
                        f"time(s) over 1940-2012; recorded {want_n}. The six shifts "
                        "are all master-vs-base pairs (2/11, 4/22, 6/33) in both "
                        "directions — a shift outside that set means the methods "
                        "differ by more than master preservation."
                    )

    # --- (f) Personal Year: how many masters the old reduction leaked.
    lo, hi = PY_DROPOUT_WINDOW
    want_dropped, want_total = PY_DROPOUT
    dropped = total = 0
    col = py.get(PY_DROPOUT_TARGET)
    if col is None:
        failures.append(
            f"target year {PY_DROPOUT_TARGET} is not in PY_TARGET_YEARS "
            f"{PY_TARGET_YEARS}, so the Personal Year dropout measurement could "
            "not be made"
        )
    else:
        for i, iso in enumerate(isos):
            y = int(iso[:4])
            if not lo <= y <= hi:
                continue
            total += 1
            if _ref_old_personal_year(iso, PY_DROPOUT_TARGET) != col[i]:
                dropped += 1
        pct = (100.0 * dropped / total) if total else 0.0
        ok = (dropped, total) == (want_dropped, want_total)
        print(f"  {'ok  ' if ok else 'FAIL'} (f) Personal Year masters dropped "
              f"vs old rule, target {PY_DROPOUT_TARGET}, {lo}-{hi}: "
              f"{dropped}/{total} = {pct:.2f}%  (recorded {want_dropped}/"
              f"{want_total})")
        if not ok:
            failures.append(
                f"the old always-preserve-masters Personal Year differs from the "
                f"current one on {dropped} of {total} dates for target "
                f"{PY_DROPOUT_TARGET}; recorded {want_dropped} of {want_total}. If "
                "this reads 0, the master-dropping was reverted and #169 is live "
                "again."
            )
    return failures


# --------------------------------------------------------------------------

GATE_TITLES = (
    "Gate 1 - the policy is declared in the source (signature + ast call sites)",
    "Gate 2 - anchored values, each row carrying its source",
    "Gate 3 - ranges and table reachability over the census",
    "Gate 4 - independent re-derivation from the corpus text",
)


def run_gates(verbose: bool = True,
              only: tuple[int, ...] = (1, 2, 3, 4)) -> list[tuple[str, int]]:
    """Run the requested gates and return (title, failure count) per gate.

    The census is rebuilt on every call, deliberately: Gate 5 corrupts the module
    between runs, and a census carried over would be pre-corruption data.
    """
    census: dict[str, object] | None = None
    if 3 in only or 4 in only:
        census = build_census()

    runners = {
        1: gate_1_policy_declared,
        2: gate_2_anchors,
        3: lambda: gate_3_ranges(census or {}),
        4: lambda: gate_4_rederivation(census or {}),
    }

    results: list[tuple[str, int]] = []
    for i in (1, 2, 3, 4):
        if i not in only:
            continue
        title = GATE_TITLES[i - 1]
        if verbose:
            print(title)
        failures = runners[i]()
        if verbose:
            for line in failures[:20]:
                print(f"  FAIL: {line}")
            if len(failures) > 20:
                print(f"  ... and {len(failures) - 20} more")
            print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
            print()
        results.append((title, len(failures)))
    return results


# --------------------------------------------------------------------------
# Gate 5 - bite test
# --------------------------------------------------------------------------

def _corruption_reinstate_original_bug():
    """`_reduce` that ignores preserve_masters and always keeps 11/22/33.

    This IS the original function, verbatim in behaviour — the single
    no-argument `_reduce(n)` that made the policy inheritable. If the gates do
    not notice it, they do not notice the defect all four issues were about.
    """
    def corrupted(n: int, *, preserve_masters: bool) -> int:
        while n > 9 and n not in MASTERS:
            n = sum(int(c) for c in str(n))
        return n
    return "numerology._reduce", corrupted


def _corruption_old_life_path():
    """`_life_path` reverted to reduce-year-month-day-separately-then-sum."""
    def corrupted(birth_date: str) -> int:
        import re as _re
        m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
        if not m:
            digits = _re.sub(r"[^0-9]", "", birth_date or "")
            return _red_masters(sum(int(c) for c in digits)) if digits else 0
        y, mo, d = m.groups()
        return _red_masters(
            _red_masters(int(y)) + _red_masters(int(mo)) + _red_masters(int(d))
        )
    return "numerology._life_path", corrupted


CORRUPTIONS = (
    ("_reduce ignores preserve_masters and always keeps 11/22/33 "
     "(the original bug, reinstated)",
     "_reduce", _corruption_reinstate_original_bug),
    ("_life_path reverted to the old reduce-parts-then-sum method",
     "_life_path", _corruption_old_life_path),
)


def gate_5_self_test() -> int:
    """Bite test: corrupt the module twice and require the gates to notice.

    A gate that cannot fail proves nothing. Gates 2-4 are re-run against each
    corruption; at least one must go red for each, or this script is decoration.

    GATE 1 IS NOT RE-RUN, and could not detect either corruption if it were: it
    reads `src/astro_ai/numerology.py` off disk with `ast`, and a monkeypatch
    does not change the file. That is not a hole — Gate 1 defends a property of
    the SOURCE (the policy is written down and readable) which no runtime
    corruption can express. It is exercised by the file-corruption procedure in
    the QA plan instead, which edits the file and re-runs this script.
    """
    print("Gate 5 - bite test (--self-test)")
    print("  each corruption is installed on the MODULE, restored in a finally, "
          "and Gates 2-4 re-run against it with a freshly built census")
    print()

    any_dead = False
    for label, attr, make in CORRUPTIONS:
        print(f"  corruption: {label}")
        _target, corrupted = make()
        original = getattr(num, attr)
        setattr(num, attr, corrupted)
        try:
            results = run_gates(verbose=False, only=(2, 3, 4))
        finally:
            setattr(num, attr, original)

        total = sum(n for _t, n in results)
        for title, n in results:
            print(f"    {'RED  ' if n else 'green'}  {title}"
                  + (f"  ({n} failure(s))" if n else ""))
        reddened = [t for t, n in results if n]
        print(f"    -> {len(reddened)} of {len(results)} gate(s) reddened, "
              f"{total} failure(s) total")
        if total == 0:
            any_dead = True
            print("    -> NOTHING BIT")
        print()

    print("  NOTE: Gate 1 is deliberately absent above. It parses "
          "src/astro_ai/numerology.py from disk, so a monkeypatch is invisible "
          "to it by construction; it is exercised by the file-corruption "
          "procedure in the QA plan, not here.")
    print()

    if any_dead:
        print("  FAIL: this script detects nothing and must not be trusted as "
              "evidence.")
        return 1
    print("  -> PASS (the gates bite)")
    return 0


def main(argv: list[str]) -> int:
    self_test = "--self-test" in argv[1:]

    print("Numerology reduction-policy verification (#162, #164, #169, #179)")
    print(f"  computation : {SOURCE_PATH.relative_to(REPO_ROOT)}")
    print(f"  rules ver.  : NUMEROLOGY_RULES_VERSION = "
          f"{num.NUMEROLOGY_RULES_VERSION!r}")
    print("  policy      : _personal_year/_birthday_number reduce to 1-9; "
          "_sum_letters/_life_path keep 11/22/33")
    print("  sources     : Johari (Vedic corpus) for Life Path + Birthday, "
          "Kumar Ch.1 for Personal Year; each anchor row carries its own")
    print(f"  census      : {CENSUS_START}..{CENSUS_END} "
          f"({CENSUS_DATES} dates) x target years "
          f"{PY_TARGET_YEARS.start}-{PY_TARGET_YEARS.stop - 1}")
    print()

    t0 = time.time()
    results = run_gates(verbose=True)
    elapsed = time.time() - t0

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print(f"  census wall time: {elapsed:.1f}s")
    print()

    total = sum(n for _t, n in results)
    if total:
        print(f"FAIL — {total} problem(s). Never re-derive an expected value from "
              "numerology.py to make a gate green: every anchored row above "
              "carries its own source, and Gate 4 re-implements the rules inline "
              "from the corpus. A red gate here means a number a user sees has "
              "moved.")
        return 1

    if self_test:
        print()
        rc = gate_5_self_test()
        if rc:
            return rc
        print()

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
