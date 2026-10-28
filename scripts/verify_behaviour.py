#!/usr/bin/env python3
"""Gate wrapper around the pytest behaviour suite.

Exists so `tests/` participates in the same `for g in scripts/verify_*.py`
sweep the other twelve gates do, and so someone who does not know the suite is
there still runs it. It is a thin shell-out, NOT a second implementation —
this repo has been bitten twice by two copies of one rule drifting apart.

    uv run python scripts/verify_behaviour.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TESTS = 767
"""ABSOLUTE BACKSTOP ONLY — do NOT raise this per pull request (#446).

This used to be the real floor, bumped by every PR, which made it the single
most conflict-prone line in the repository: every PR adds tests, so every pair
of concurrent PRs collided here. On 2026-10-20 three did, and one hand
resolution silently concatenated two `ARCHITECTURE.md` decision rows.

The per-PR floor now lives in `scripts/verify_test_floor.py`, which DERIVES it
by comparing test names at the merge base with `origin/main` against HEAD. That
stores nothing, so nothing conflicts. It is NOT "strictly stronger" than a
constant (this docstring used to say so; QA on PR #448 disproved it): it names
the tests that disappeared, catches a test renamed out of `test_*`, and compares
literal `parametrize` case counts per function -- but it does not see a computed
parametrize list or pytest's real collection, which this constant alone counts.

This number stays as a floor under BOTH of them, for the cases the derived gate
cannot cover: a shallow clone with no merge base, and `main` itself. Its slack
GROWS as PRs add tests, because nobody raises it: it is a backstop against mass
loss, not a per-PR guard.

IT IS LEFT EXACTLY WHERE IT WAS, and that is deliberate. The first version of
this change lowered it to 700 to "leave headroom", which `verify_no_relaxation.py`
correctly reads as a RELAXATION -- a falling floor is its first rule, and the
rule does not care that the author meant well. Nothing here needs it lowered:
the point is that PRs stop EDITING it, not that it gets weaker. It only has to
move if a deliberate deletion ever takes the real count below it, which is the
reviewed case that detector exists for.

Never lower it to make a run green."""


def main() -> int:
    print("Behaviour suite (tests/) — request-path regressions")
    print("  covers  : panchang-strip cache lifecycle, degraded rashifal paths,")
    print("            daily-blast outcome reporting")
    print("  why     : the other gates check DATA. Eleven defects across four QA")
    print("            rounds were request-path behaviour, which nothing checked.")
    print()
    result = subprocess.run(
        # No -q here: pyproject's addopts already sets it, and a second one
        # makes it -qq, which suppresses the summary line the skip check reads.
        # That is why the first version of this backstop passed its own probe.
        [sys.executable, "-m", "pytest", str(ROOT / "tests")],
        cwd=ROOT, capture_output=True, text=True,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")

    # A SKIP must not read as a pass. The blast tests used to skip themselves
    # when ADMIN_PASSWORD was absent, and `.env` is gitignored — so on a fresh
    # clone a third of the suite vanished, pytest exited 0, and this printed
    # PASS. A suite that skips into green is worse than a missing one, because
    # it looks like coverage. The skip is gone at source; this is the backstop
    # for the next one.
    # Search the WHOLE of stdout for a "N skipped" count. Reading only the last
    # line looked right and was wrong: pytest's final line is the warnings-docs
    # URL, so this backstop silently passed the very probe written to test it.
    muted = re.search(r"(\d+)\s+(skipped|xfailed|xpassed|deselected)", result.stdout)
    summary = muted.group(0) if muted else ""

    # And count what RAN. A skip at least prints itself; a test renamed out of
    # `test_*`, or a whole file that stops being collected, prints nothing at
    # all — the suite just gets quietly smaller and the gate stays green. That
    # is the same disappearing-coverage failure the skip check was added for,
    # one step further along.
    passed = re.search(r"(\d+)\s+passed", result.stdout)
    count = int(passed.group(1)) if passed else 0

    print()
    if result.returncode == 0 and not muted and count >= EXPECTED_TESTS:
        print(f"PASS ({count} tests)")
        return 0
    if muted:
        print(f"FAIL — tests did not run: {summary}")
        print("       A skip or xfail is not a pass. Make the test hermetic, fix it,")
        print("       or delete it — but do not let it report green while absent.")
        return 1
    if result.returncode == 0 and count < EXPECTED_TESTS:
        print(f"FAIL — only {count} tests ran, expected at least {EXPECTED_TESTS}.")
        print("       Coverage vanished silently: a test renamed out of `test_*`, a")
        print("       file no longer collected, or a deletion.")
        print("       This is the ABSOLUTE backstop, so hitting it means a large drop.")
        print("       `scripts/verify_test_floor.py` names which tests went missing;")
        print("       read that first. Lowering this number is a last resort and")
        print("       never a way to make a run green.")
        return 1
    print("FAIL — do not tune a test to silence it. Each one is a defect that")
    print("       shipped; a red test means it is back.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
