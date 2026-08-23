#!/usr/bin/env python3
"""Gate wrapper around the pytest behaviour suite.

Exists so `tests/` participates in the same `for g in scripts/verify_*.py`
sweep the other twelve gates do, and so someone who does not know the suite is
there still runs it. It is a thin shell-out, NOT a second implementation —
this repo has been bitten twice by two copies of one rule drifting apart.

    uv run python scripts/verify_behaviour.py
"""
from __future__ import annotations

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
        [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
        cwd=ROOT,
    )
    print()
    if result.returncode == 0:
        print("PASS")
    else:
        print("FAIL — do not tune a test to silence it. Each one is a defect that")
        print("       shipped; a red test means it is back.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
