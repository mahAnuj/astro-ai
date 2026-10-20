#!/usr/bin/env python3
"""The test-count floor, DERIVED from the merge base instead of hand-edited.

WHY THIS EXISTS (#446, part 3 of #405)

`EXPECTED_TESTS` was a single integer on one line of `verify_behaviour.py` that
EVERY pull request had to edit, because every PR adds tests. So every pair of
concurrent PRs conflicted there, and on 2026-10-20 three of them did — #425,
#443 and #445 — with #443 resolving the same three files twice. One of those
hand resolutions silently concatenated two `ARCHITECTURE.md` decision rows, and
the script written to prevent exactly that had the same defect and could not run
at all. `ARCHITECTURE.md`'s own row for #405 predicted it: *"Until those land,
`verify_behaviour.py` and `mutate_behaviour_suite.py` still conflict."*

WHAT REPLACES IT, AND WHAT MUST NOT BE LOST

The floor's job was never the number. It was ONE property: coverage may not
vanish silently. It earned that job — a slice-based edit deleted six tests on
`feat/124-hindi-url-prefix`, two of them named guards for registered mutations,
and the floor is what caught it.

So the floor is now computed: count the tests at the MERGE BASE with
`origin/main`, count them at HEAD, and require HEAD not to be lower. Nothing is
stored, so nothing conflicts, and the comparison is strictly stronger than a
constant — a stale constant drifts below the real count and stops protecting
anything, which is precisely what a hand-edited floor does between bumps.

COUNTED BY PARSING, NOT BY COLLECTING. `ast` over `tests/**/*.py` needs only the
FILES, which `git show` hands over for any commit without a checkout, a venv or
an importable tree. Collection at an old commit would need all three. The two
counts are therefore measured the same way on both sides, which is the only
thing a comparison requires.

It also reports WHICH tests disappeared. The old gate printed a number, so a
drop meant a manual hunt; both times it happened that hunt is what took the
time, not the discovery.

A DELIBERATE DELETION IS STILL POSSIBLE, and still has to be said out loud: put
`Test-Count-Drop: <reason>` in the commit message. That is reviewable in the
diff, cannot be done by a tool run, and leaves the reason next to the act —
unlike lowering a constant, which looks identical whether it was reasoned or
convenient.

EXIT CODES
  0  the count did not fall (or a drop is declared, or there is no base to
     compare against — reported, never silent)
  1  tests disappeared and nothing declared it
  2  could not run: git failed, or `tests/` is missing. NOT a pass.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = "tests"


def git(*args: str) -> str:
    out = subprocess.run(("git", "-C", str(ROOT), *args),
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {out.stderr.strip()[:300]}")
    return out.stdout


def _names_from_source(src: str, path: str) -> set[str]:
    """`def test_*` at module level or inside a Test* class, as `path::name`.

    A SyntaxError is not zero tests — it is a file this cannot read, and
    returning an empty set would read as "every test here vanished". Raised so
    the caller exits 2 rather than 1.
    """
    tree = ast.parse(src, filename=path)
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found.add(f"{path}::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test"):
                    found.add(f"{path}::{node.name}::{sub.name}")
    return found


def names_at(ref: str | None) -> set[str]:
    """Every test name at `ref`, or in the working tree when `ref` is None."""
    out: set[str] = set()
    if ref is None:
        for p in sorted((ROOT / TESTS).rglob("test_*.py")):
            rel = p.relative_to(ROOT).as_posix()
            out |= _names_from_source(p.read_text(encoding="utf-8"), rel)
        return out
    listing = git("ls-tree", "-r", "--name-only", ref, "--", TESTS)
    for rel in listing.splitlines():
        name = rel.rsplit("/", 1)[-1]
        if not (name.startswith("test_") and rel.endswith(".py")):
            continue
        out |= _names_from_source(git("show", f"{ref}:{rel}"), rel)
    return out


def base_ref() -> str | None:
    """The merge base with `origin/main`, or None when there is nothing to compare.

    None is a real answer, not an error: on `main` itself the merge base IS
    HEAD, and a shallow clone may not have the history. Both are reported.
    """
    # `origin/main` ONLY, never local `main`. CLAUDE.md records that this
    # repository's local `main` is PRE-REWRITE history (703/751 divergence), and
    # the first version of this function fell back to it: `merge-base HEAD main`
    # answered an ancient commit where `tests/` did not exist, so the base count
    # came back 0 and the floor passed `543 >= 0`. A floor that compares against
    # nothing reports PASS, which is the exact failure mode this file replaces.
    try:
        base = git("merge-base", "HEAD", "origin/main").strip()
    except RuntimeError:
        return None
    if base and base != git("rev-parse", "HEAD").strip():
        return base
    return None


def drop_declared() -> str | None:
    """`Test-Count-Drop: <reason>` in any commit not on the base."""
    base = base_ref()
    rng = f"{base}..HEAD" if base else "HEAD~1..HEAD"
    try:
        log = git("log", "--format=%B", rng)
    except RuntimeError:
        return None
    for line in log.splitlines():
        if line.strip().lower().startswith("test-count-drop:"):
            reason = line.split(":", 1)[1].strip()
            return reason or "(no reason given)"
    return None


def main() -> int:
    if not (ROOT / TESTS).is_dir():
        print(f"COULD NOT RUN (exit 2) — no {TESTS}/ directory. This is NOT a pass.")
        return 2
    try:
        head = names_at(None)
        base = base_ref()
    except (RuntimeError, SyntaxError, OSError) as exc:
        print(f"COULD NOT RUN (exit 2) — {type(exc).__name__}: {exc}")
        print("A floor this cannot compute is not a floor that passed.")
        return 2

    print(f"Test-count floor — derived, nothing stored (see #446)")
    # `def test_*`, NOT pytest's collected count: one parametrised function is
    # one name here and N cases there. Both sides are measured the same way, so
    # the comparison holds -- but the numbers differ from `verify_behaviour.py`'s
    # and that must not read as a regression.
    print(f"  HEAD: {len(head)} test functions (not pytest cases) in {TESTS}/")

    if base is None:
        print("  base: none — HEAD is the merge base (on main), or the history is")
        print("        shallow. Nothing to compare against, so nothing is asserted.")
        print("\nPASS (no base; reported rather than silently skipped)")
        return 0

    try:
        before = names_at(base)
    except (RuntimeError, SyntaxError, OSError) as exc:
        print(f"COULD NOT RUN (exit 2) — reading {base[:9]}: {type(exc).__name__}: {exc}")
        return 2

    print(f"  base: {len(before)} at {base[:9]}")
    gone = sorted(before - head)
    added = len(head - before)

    if not gone:
        print(f"  +{added} added, 0 removed")
        print(f"\nPASS ({len(head)} >= {len(before)})")
        return 0

    reason = drop_declared()
    print(f"  +{added} added, {len(gone)} REMOVED:")
    for name in gone[:25]:
        print(f"    - {name}")
    if len(gone) > 25:
        print(f"    ... and {len(gone) - 25} more")

    if reason:
        print(f"\nPASS — {len(gone)} test(s) removed, declared: Test-Count-Drop: {reason}")
        print("       The deletion is deliberate and its reason is in the commit.")
        return 0

    print(f"\nFAIL — {len(gone)} test(s) present at the merge base are gone at HEAD, and")
    print("       nothing declared it. Each test in this repo is a defect that")
    print("       shipped; deleting one removes the proof it cannot come back.")
    print("       If the deletion IS deliberate, say so where it can be reviewed:")
    print("       add `Test-Count-Drop: <reason>` to the commit message.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
