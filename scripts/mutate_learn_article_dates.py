#!/usr/bin/env python3
"""Mutation-test the learn-article date gate: corrupt a date, confirm it goes red.

A gate that has never failed is not evidence, and this one is a live example:
`scripts/verify_learn_article_dates.py` exits 0 today on two corruptions that
change a date a reader would act on. Both are bare dates in prose that the gate
classifies as "no usable year" and reports as UNCHECKED — including
`diwali-muhurat-2026.html:22`'s `until Nov 10`, which is Govardhan Puja, the
#143 date, unguarded in the very article #143 was filed against.

    uv run python scripts/mutate_learn_article_dates.py   # exit 1 if any escapes

THIS SCRIPT IS RED BY DESIGN until the corroborate-or-fail gate (#193 S3) lands.
Two of the four rows below are the defect it will fix, so 2/4 caught is the
CORRECT reading of the current tree, not a regression. When S3 lands, all four
must be caught and this becomes a normal green gate.

It must not join the `verify_*` sweep — the `mutate_` prefix keeps it out of
that glob, exactly as `mutate_behaviour_suite.py` stays out. It corrupts
articles on purpose; a sweep that ran it would be scoring a broken tree.

Rows are anchored by BOTH line number and substring. `Jul 14, 2027` occurs on
two lines of `vivah-muhurat-2027.html`, so a file-wide substring is not a
unique anchor, and a gate verdict quoted as `file.html:65` has to be tied to a
line to mean anything. If either half of the anchor drifts, the row reports
ANCHOR MISSED rather than silently mutating the wrong text.
"""
import hashlib
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile

GATE = "scripts/verify_learn_article_dates.py"
DIWALI = "src/astro_ai/templates/learn/diwali-muhurat-2026.html"
VIVAH = "src/astro_ai/templates/learn/vivah-muhurat-2027.html"

# (label, path, line_no, from_substring, to_substring, why it must fail)
MUTATIONS = [
    # The two escapes. Both move a date by two days in prose a reader plans
    # around, and both sit in a string the gate currently files as UNCHECKED.
    ("vivah: Chaturmas opens two days later, on the WRONG day",
     VIVAH, 98, "on Jul 14", "on Jul 16",
     "Gate 4 — bare `Jul 14` must corroborate the Jul 14 2027 Devshayani claim"),

    ("diwali: Shukla Pratipada reaches sunrise on the WRONG day (#143's date)",
     DIWALI, 22, "until Nov 10", "until Nov 12",
     "Gate 4 — bare `Nov 10` must corroborate the Nov 10 2026 Govardhan claim"),

    # The two controls-of-a-different-kind: dated claims the gate already
    # covers. They are here so a run that catches nothing tells you the gate
    # broke, not that the escapes widened.
    ("vivah: Devshayani Ekadashi moved off the registry date",
     VIVAH, 65, "Jul 14, 2027", "Jul 13, 2027",
     "Gate 1 — attributed claim vs computed source (also Gate 2, day name)"),

    ("diwali: Govardhan Puja's weekday no longer matches its date",
     DIWALI, 18, "Tuesday, Nov 10, 2026", "Wednesday, Nov 10, 2026",
     "Gate 2 — 2026-11-10 is a Tuesday"),
]

ROOT = pathlib.Path(__file__).resolve().parent.parent

# A mutation that changes NOTHING a date gate can see. It MUST report MISSED.
#
# Same reason `mutate_behaviour_suite.py` carries one: without it, a sandbox
# that is red for its own reasons — a bad copy, a missing module, an import
# error — scores every row CAUGHT and the summary measures nothing. Here the
# specific risk is the sandbox `src/`: the gate does `sys.path.insert(0,
# REPO_ROOT/"src")` and reads `LEARN_DIR` relative to its own file, so if the
# copy were wrong it would still exit non-zero and look like four catches.
# This row proves, every run, that the sandbox is green before mutation.
_CONTROL = (
    "CONTROL: a prose edit carrying no date — MUST report MISSED",
    DIWALI, 61, "Morning muhurat is preferred.", "A morning muhurat is preferred.",
    "_control",
)


def _die_cleanly(signum, _frame):
    """Turn SIGTERM/SIGHUP into SystemExit so TemporaryDirectory unwinds."""
    raise SystemExit(f"terminated by signal {signum}")


for _sig in (signal.SIGTERM, signal.SIGHUP):
    signal.signal(_sig, _die_cleanly)


def _fingerprints() -> dict:
    """md5 of every article this run can touch, read from the real repo."""
    paths = {row[1] for row in [_CONTROL] + list(MUTATIONS)}
    return {rel: hashlib.md5((ROOT / rel).read_bytes()).hexdigest()
            for rel in sorted(paths)}


def _run_in_sandbox(rel: str, line_no: int, old: str, new: str) -> tuple[bool, str]:
    """Apply one corruption to a COPY of the tree and run the gate there.

    The repository is never written to. A restore-in-`finally` would leave a
    wrong festival date sitting in a shipped article if the process took a
    signal that does not raise — which for THIS harness means the #143 defect
    back on disk, in prose, where a casual `git diff` skims past it. A sandbox
    removes the failure mode instead of handling it.
    """
    with tempfile.TemporaryDirectory(prefix="mutate-dates-") as tmp:
        sandbox = pathlib.Path(tmp) / "repo"
        shutil.copytree(ROOT / "src", sandbox / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (sandbox / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / GATE, sandbox / GATE)

        target = sandbox / rel
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        if line_no > len(lines):
            return False, f"ANCHOR MISSED (file has {len(lines)} lines)"
        line = lines[line_no - 1]
        if line.count(old) != 1:
            return False, f"ANCHOR MISSED ({line.count(old)}x on line {line_no})"
        lines[line_no - 1] = line.replace(old, new)
        target.write_text("".join(lines), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(sandbox / GATE)],
            capture_output=True, text=True, cwd=sandbox,
        )
        if result.returncode == 0:
            return False, "*** MISSED ***"
        # A non-zero exit from a traceback would look like a catch and be worth
        # nothing. Require the gate to name the line it is complaining about,
        # which is also what makes the verdict actionable for whoever reads it.
        where = f"{pathlib.PurePath(rel).name}:{line_no}"
        if where not in result.stdout + result.stderr:
            return False, f"RED BUT SILENT (rc={result.returncode}, no '{where}')"
        return True, "CAUGHT"


before = _fingerprints()

rows = []
control_ok = True
for label, rel, line_no, old, new, why in [_CONTROL] + list(MUTATIONS):
    _, verdict = _run_in_sandbox(rel, line_no, old, new)
    if why == "_control":
        # Inverted: for the control, MISSED is the pass.
        control_ok = verdict == "*** MISSED ***"
        rows.append((label, "OK (correctly missed)" if control_ok else f"BLIND ({verdict})",
                     "the sandbox must be green before mutation"))
        continue
    rows.append((label, verdict, why))

after = _fingerprints()
drifted = [rel for rel in before if before[rel] != after[rel]]

print(f"{'mutation':<62} {'verdict'}")
print("-" * 80)
bad = 0
for label, verdict, why in rows:
    if verdict != "CAUGHT":
        bad += 1
    print(f"  {label:<60} {verdict}")
    print(f"      must be caught by: {why}")
print()
# The control row never has the verdict "CAUGHT" — pass or fail — so it always
# adds exactly 1 to `bad`. Subtract it once, unconditionally.
real = len(rows) - 1
caught = real - (bad - 1)
print(f"{caught}/{real} corruptions caught")
for rel, digest in sorted(after.items()):
    print(f"  unchanged  {digest}  {rel}")
if drifted:
    print()
    print("REPOSITORY MODIFIED — " + ", ".join(drifted))
    print("The sandbox leaked. Restore these files from git before trusting anything.")
if not control_ok:
    print()
    print("CONTROL FAILED — the sandbox reports a catch for an edit carrying no")
    print("date at all, so every verdict above is worthless. Fix the sandbox")
    print("before believing any number this printed.")
if caught < real and control_ok and not drifted:
    print()
    print("Expected on the current tree: 2/4, escaping rows 1 and 2. That is #193's")
    print("defect, not a regression — bare dates in prose reach no gate. Both become")
    print("catches when the corroborate-or-fail gate lands.")
sys.exit(0 if control_ok and not drifted and caught == real else 1)
