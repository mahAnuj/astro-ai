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
    skip_match = re.search(r"(\d+)\s+skipped", result.stdout)
    skipped = bool(skip_match)
    summary = skip_match.group(0) if skip_match else ""

    print()
    if result.returncode == 0 and not skipped:
        print("PASS")
        return 0
    if skipped:
        print(f"FAIL — tests were SKIPPED: {summary}")
        print("       A skip is not a pass. Make the test hermetic or delete it.")
        return 1
    print("FAIL — do not tune a test to silence it. Each one is a defect that")
    print("       shipped; a red test means it is back.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
