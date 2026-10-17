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

REPORT-ONLY ROWS (#405)

Four rows are volatile: Python (lines), top-level modules, verification gates and
the behaviour suite. Measured on main@50a9c42 over the last 100 commits, the
doc moved in 27 of them, verify_behaviour.py in 22 and
mutate_behaviour_suite.py in 19 — and every PR that added a test or a gate
hand-edited the same number in the same shared file, so concurrent PRs
conflicted on a line that carried no information the command did not.

So those rows (REPORT_ONLY, below) store the word `measured` in the count cell
instead of a number, and this gate prints the live value. The rule runs in BOTH
directions, because either half alone reopens a hole:

  - a REPORT_ONLY row carrying a number FAILS — a number there is exactly what
    makes every PR conflict, and it would be unchecked by nothing but this rule;
  - any other row carrying `measured` FAILS — otherwise `measured` becomes a way
    to exempt a row from checking by editing one word.

A REPORT_ONLY row is not unchecked: its command must still run and its last
numeric token must be greater than zero, so a command that rotted (a moved
path counts 0) still turns the gate red. Two rows sharing a label or a command
also FAIL — EXPECTED_ROWS is a floor, and a floor is blind to a row that was
duplicated rather than removed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "ARCHITECTURE.md"

# Pinned so a row cannot be deleted silently. Raise it when adding one.
EXPECTED_ROWS = 10

# Rows whose count cell must read exactly `measured` (see the docstring). Labels
# are the first cell of the §1 table, verbatim.
REPORT_ONLY = {
    "Python",
    "top-level modules",
    "verification gates",
    "behaviour suite",
}
MEASURED = "measured"

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
        and not l.lower().startswith("| what ")      # header
    ]
    # A §1 row MUST carry a backticked command. One that does not is
    # unverifiable, and the first version of this filter required a backtick
    # to even consider a line a row — so a row without one was invisible
    # rather than failing. QA proved it: a bogus row claiming 99 passed.
    uncommanded = [l for l in looks_like_row if "`" not in l]
    if uncommanded:
        print("FAIL — §1 row(s) carry no backticked command, so nothing can\n"
              "       verify them. Add the command or remove the row:")
        for l in uncommanded:
            print(f"         {l[:88]}")
        return 1
    looks_like_row = [l for l in looks_like_row if "`" in l]
    if len(looks_like_row) != len(rows):
        print(f"FAIL — {len(looks_like_row)} rows look like checkable rows but only "
              f"{len(rows)} parsed.\n       An unparseable row is a failure, not a skip "
              f"— that is how two stale\n       numbers were reported as verified.")
        for l in looks_like_row:
            if not ROW.match(l + "\n"):
                print(f"         unparsed: {l[:88]}")
        return 1

    # Hole B: deleting a row passed, because nothing pinned how many there
    # are. A table that can silently shrink is a table that can silently stop
    # covering something.
    if len(rows) < EXPECTED_ROWS:
        print(f"FAIL — §1 has {len(rows)} checkable rows, expected at least "
              f"{EXPECTED_ROWS}.\n       A row was removed. If that is intended, "
              f"lower EXPECTED_ROWS in this file\n       and say why in the commit.")
        return 1

    # EXPECTED_ROWS counts rows, so a row that is DUPLICATED rather than
    # removed leaves it satisfied while a different row quietly stops being
    # covered. Compare label and (unescaped) command.
    dupes: list[str] = []
    for what, keys in (("label", [r[0] for r in rows]),
                       ("command", [r[2].replace("\\|", "|") for r in rows])):
        for k in sorted({k for k in keys if keys.count(k) > 1}):
            dupes.append(f"duplicate {what}: {k}")
    missing = sorted(REPORT_ONLY - {r[0] for r in rows})
    if dupes or missing:
        print("FAIL — §1 rows are not one-per-thing:")
        for d in dupes:
            print(f"  - {d}")
        for m in missing:
            print(f"  - REPORT_ONLY row {m!r} is not in §1 (renamed or removed?)")
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

        got_all = _numbers(out.stdout)
        if label in REPORT_ONLY:
            if value != MEASURED:
                problems.append(
                    f"{label}: volatile; a number here is what makes every PR "
                    f"conflict — write `{MEASURED}`, not {value!r}")
                continue
            if not got_all or got_all[-1] <= 0:
                problems.append(
                    f"{label}: report-only row's command printed {got_all}; the "
                    f"last number must be > 0 (a rotted command counts 0): {cmd}")
                continue
            print(f"  rep {label:<30} doc={value:<16} actual=[{got_all[-1]}]")
            continue
        if value == MEASURED:
            problems.append(
                f"{label}: `{MEASURED}` is reserved for REPORT_ONLY rows "
                f"({', '.join(sorted(REPORT_ONLY))}); this row must state its number")
            continue
        claimed = _numbers(value)
        if not claimed:
            problems.append(f"{label}: no number in the value cell {value!r}")
            continue
        # one claimed number -> the command's last number; several -> the last N
        # Hole C: comparing the LAST len(claimed) numbers meant dropping one
        # from `11 files, 8,021 lines` left 10 numbers checked, 11 claimed,
        # and a PASS. That is "verified eight and reported on ten" in
        # miniature — the exact defect this gate was written for. So the
        # counts must match exactly.
        if len(got_all) != len(claimed):
            problems.append(
                f"{label}: value cell has {len(claimed)} number(s) but its "
                f"command prints {len(got_all)} ({got_all}). The row and the "
                f"command disagree about what is being counted."
            )
            continue
        got = got_all
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
