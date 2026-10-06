#!/usr/bin/env python3
"""Gate: every number in ARCHITECTURE.md §1 matches the command printed beside it.

WHY THIS EXISTS

§1 is a table of counts where each row carries the shell command that produces
it — the table's own header says "re-run the command; do not trust the
number". Nothing re-ran them, so they drifted. The header also records the
previous drift: six stale numbers at once, the line count 32% low, five of
them sitting unchanged beside a sixth being corrected.

That happened again. A change corrected five rows and left two wrong beside
them, and the verification claim attached to it — "I ran every row against the
command printed beside it and got zero mismatches" — was false in a specific
and instructive way: the checker's regex required a purely numeric value cell,
so the two rows whose cell carries a unit word (`28,490 lines`,
`100 tests`) never matched it. It verified eight rows and reported on ten.

So the one rule this gate enforces about itself: **a row it cannot parse is a
FAILURE, not a skip.** That is the whole point. A checker that silently
narrows its own scope and reports success is worse than no checker, because
the success is quoted later as evidence.

WHAT IT CHECKS

For every `| label | value | `command` |` row in §1: run the command, take the
last whitespace-separated token of its output, and compare. `value` may carry
a trailing unit word (`lines`, `tests`, `files`), which is stripped. A row with
a command that cannot run, or a value that cannot be read, fails.

Rows whose command is inherently multi-valued (`11 files, 8,021 lines`) declare
both numbers and both are checked.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "ARCHITECTURE.md"

ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*$", re.M)


def _numbers(text: str) -> list[int]:
    return [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)]


def main() -> int:
    if not DOC.exists():
        print(f"FAIL — {DOC} not found")
        return 1

    body = DOC.read_text()
    # §1 only: from its heading to the next ##
    start = body.index("## 1.")
    end = body.index("\n## ", start + 1)
    section = body[start:end]

    rows = ROW.findall(section)
    if not rows:
        print("FAIL — no parseable rows found in §1. The table's shape changed;\n"
              "       this gate must be updated rather than left reporting PASS.")
        return 1

    # Every table-looking line must have been parsed. An unparsed row is the
    # failure mode this gate exists for.
    looks_like_row = [
        l for l in section.splitlines()
        if l.startswith("|") and l.count("|") >= 4
        and not re.match(r"^\|[\s:-]+\|", l)        # separator
        and "`" in l                                 # carries a command
    ]
    if len(looks_like_row) != len(rows):
        print(f"FAIL — {len(looks_like_row)} rows look like checkable rows but only "
              f"{len(rows)} parsed.\n       An unparseable row is a failure, not a skip "
              f"— that is how two stale\n       numbers were reported as verified.")
        for l in looks_like_row:
            if not ROW.match(l + "\n"):
                print(f"         unparsed: {l[:88]}")
        return 1

    problems: list[str] = []
    print(f"ARCHITECTURE.md §1 — {len(rows)} rows, each against its own command\n")
    for label, value, cmd in rows:
        cmd = cmd.replace("\\|", "|")
        try:
            out = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                                 text=True, timeout=180)
        except subprocess.TimeoutExpired:
            problems.append(f"{label}: command timed out")
            continue
        if not out.stdout.strip():
            problems.append(f"{label}: command produced no output ({cmd})")
            continue

        claimed = _numbers(value)
        got_all = _numbers(out.stdout)
        if not claimed:
            problems.append(f"{label}: no number in the value cell {value!r}")
            continue
        # one claimed number -> the command's last number; several -> the last N
        got = got_all[-len(claimed):] if len(got_all) >= len(claimed) else got_all
        ok = got == claimed
        print(f"  {'ok ' if ok else 'BAD'} {label:<30} doc={value:<16} actual={got}")
        if not ok:
            problems.append(f"{label}: doc says {claimed}, command gives {got}")

    if problems:
        print(f"\nFAIL — {len(problems)} row(s) do not match their own command:")
        for p in problems:
            print(f"  - {p}")
        print("\nRe-run each command and write what it prints. Correcting some rows\n"
              "and leaving others beside them is this table's documented failure mode.")
        return 1

    print(f"\nPASS ({len(rows)} rows match the commands printed beside them)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
