#!/usr/bin/env python3
"""Merge `origin/main` into the current branch, resolving only the conflicts
this repository produces mechanically — and refusing everything else.

WHY THIS IS A SCRIPT AND NOT AN INSTRUCTION

A conflicting PR gets no check runs at all: `pull_request` workflows run against
the merge ref `refs/pull/N/merge`, which GitHub cannot compute while the PR has
conflicts, so pushes fire no run and `agent-merge` refuses forever on "no checks
reported". The PR is dead until someone merges `main` into it, and until
2026-10-20 nothing in the loop could: `no-checks-ever` is deliberately absent
from the detector's `obliged` set, so the steward produced no action and chief
was woken to rule on a mechanical operation.

WHAT IS MECHANICAL HERE, MEASURED RATHER THAN ASSUMED

Every conflict resolved by hand on 2026-10-20 — across #412, #418, #419 and
#424 — was one of exactly three shapes, and each has one correct resolution:

  ARCHITECTURE.md                    decision-log rows are independent entries.
                                     UNION, then sort by date. Taking a side
                                     silently drops the other branch's row, and
                                     `git checkout --theirs` on this file has
                                     already wiped five rows in this repo once.

  scripts/mutate_behaviour_suite.py  both sides' mutation rows. UNION, never
                                     drop: `verify_no_relaxation.py` fails on a
                                     falling row count, and it is right to.

  scripts/verify_behaviour.py        EXPECTED_TESTS is an absolute BACKSTOP that
                                     PRs no longer edit (#446), so a conflict
                                     here should not happen. If one does, keep
                                     OURS: the per-PR floor is derived by
                                     scripts/verify_test_floor.py and stores
                                     nothing.

ANYTHING ELSE IS REFUSED AND THE MERGE IS ABORTED. A conflict in a source file
is a semantic question, and this script has no way to answer one.

AND A CLEAN RESOLUTION IS NOT A CORRECT MERGE. That is the other half, and it is
the half that bites. On 2026-10-20 both merges whose conflicts were purely
mechanical still produced a red suite, from defects neither branch could see
alone:

  * #418 x main — #424's gate tests drive a stub HTTP server on an ephemeral
    port through `urlopen`, and #418's new suite-wide hermeticity fixture
    blocked every `urlopen` including loopback. Two green branches, two
    failures, neither a network request.
  * #419 x #418 — #418's new test reset the app cache with `_app_cache = None`,
    the convention #419 had replaced with a dict. `/admin/ops` 500'd inside the
    test written to prove the page survives.

So this script verifies the merge RESULT and reports rather than pushing when it
is red. `--push` is opt-in and is ignored unless every check passes: a merge
nobody verified is how a branch that was green becomes a branch that is red with
a commit saying "Merge origin/main" and no mention of it.

EXIT CODES, so a caller can route on them:

  0  merged, every check green. Pushed if --push was given.
  1  merged, but a check failed. The merge is left in the working tree with its
     commit NOT made, so an agent or a human can look at what the merge broke.
  2  refused: a conflict outside the three mechanical classes. Merge aborted,
     tree restored.
  3  could not run: dirty tree, detached HEAD, no such branch, git failure.
  4  nothing to do: already up to date.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The three files whose conflicts have one correct mechanical resolution. A
#: conflict in any other path is a semantic question and is refused.
MECHANICAL = ("ARCHITECTURE.md",
              "scripts/mutate_behaviour_suite.py",
              "scripts/verify_behaviour.py")

_DATED_ROW = re.compile(r"^\| 20\d\d-\d\d-\d\d ")


def git(*args: str, check: bool = True) -> str:
    out = subprocess.run(("git", "-C", str(ROOT), *args),
                         capture_output=True, text=True, timeout=300)
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {out.returncode}: "
                           f"{out.stderr.strip()[:400]}")
    return out.stdout


def hunks(text: str, mark: str) -> list[tuple[int, int, int, str, str]]:
    """Every conflict hunk as `(start, mid, end, ours, theirs)`, char offsets.

    LINE-BASED, after two character-offset versions each got a side wrong. Both
    failures were real conflict shapes, found on 2026-10-20 while resolving PR
    #443 against #425 by hand because this script could not run at all:

    * `text.index("\n=======")` misses an EMPTY OURS side, because then
      `=======` sits at the very start of the search region with no newline
      before it inside that region.
    * `text.index("\n=======\n")` misses an EMPTY THEIRS side, because then the
      text reads `=======\n>>>>>>>` and there is no newline before the marker.

    Both raised ValueError, which the caller reads as "no hunk here" rather than
    "an empty side" -- a parse bug that presents as a clean file.

    Each side is returned WITH its trailing newline, or as `""`. A side whose
    last line lost its newline silently CONCATENATED two decision-log rows in
    `ARCHITECTURE.md`: one row's text ended up inside another and a third
    stopped being a row, with every test green.
    """
    lines = text.splitlines(True)
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln)
    offs.append(acc)

    out: list[tuple[int, int, int, str, str]] = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<< "):
            i += 1
            continue
        mid = next((j for j in range(i + 1, len(lines))
                    if lines[j].rstrip("\n") == "======="), None)
        if mid is None:
            raise RuntimeError("a conflict hunk has no `=======` separator")
        end = next((j for j in range(mid + 1, len(lines))
                    if lines[j].startswith(f">>>>>>> {mark}")), None)
        if end is None:
            raise RuntimeError(f"a conflict hunk has no `>>>>>>> {mark}` marker")
        ours = "".join(lines[i + 1:mid])
        theirs = "".join(lines[mid + 1:end])
        for side in (ours, theirs):
            assert side == "" or side.endswith("\n"), "a conflict side lost its newline"
        # `mid` and `end` keep the original contract: the offset of the newline
        # ENDING the line before the marker, so `text.index("\n", b + 1)` in the
        # resolvers still finds the end of the `>>>>>>>` line.
        out.append((offs[i], offs[mid] - 1, offs[end] - 1, ours, theirs))
        i = end + 1
    return out


def resolve_union_dated(text: str, mark: str) -> str:
    """Both sides' rows, dated rows sorted. For a decision log."""
    for a, m, b, ours, theirs in reversed(hunks(text, mark)):
        both = (theirs + ours).splitlines(True)
        rows = sorted((l for l in both if _DATED_ROW.match(l)),
                      key=lambda l: l.split("|")[1].strip())
        rest = [l for l in both if not _DATED_ROW.match(l)]
        end = text.index("\n", b + 1) + 1
        text = text[:a] + "".join(rows) + "".join(rest) + text[end:]
    return text


def resolve_union(text: str, mark: str) -> str:
    """Both sides, in order, nothing dropped. For a mutation table."""
    for a, m, b, ours, theirs in reversed(hunks(text, mark)):
        end = text.index("\n", b + 1) + 1
        text = text[:a] + ours + theirs + text[end:]
    return text


def resolve_ours(text: str, mark: str) -> str:
    """Keep our side as a placeholder. Only for a value measured afterwards."""
    for a, m, b, ours, theirs in reversed(hunks(text, mark)):
        end = text.index("\n", b + 1) + 1
        text = text[:a] + ours + text[end:]
    return text


RESOLVERS = {
    "ARCHITECTURE.md": resolve_union_dated,
    "scripts/mutate_behaviour_suite.py": resolve_union,
    "scripts/verify_behaviour.py": resolve_ours,
}


def conflicted() -> list[str]:
    return [l for l in git("diff", "--name-only", "--diff-filter=U").splitlines() if l]


def run(label: str, *cmd: str) -> tuple[bool, str]:
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    ok = out.returncode == 0
    print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    return ok, (out.stdout + out.stderr)


def measured_test_count() -> int | None:
    out = subprocess.run(("uv", "run", "pytest", "--collect-only", "--no-header",
                          "-p", "no:warnings"), cwd=ROOT, capture_output=True,
                         text=True, timeout=900)
    n = len(re.findall(r"<(?:Function|TestCaseFunction) ", out.stdout))
    return n or None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--push", action="store_true",
                    help="push the merge, but only if every check passes")
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv)

    # `--untracked-files=no`, and this is not a loosening. The plain form lists
    # UNTRACKED files too, and this repository permanently carries several by
    # intention -- CLAUDE.md names `.local/`, `.serena/`, `QA_LOG.md`,
    # `.claude/worktrees/` and `verify-main/` and says to leave them alone. So
    # this check was unsatisfiable in the only tree it was written for: the
    # script could NEVER run here, while `steward.md` routed every
    # `pr-conflicting` stall to it. An instruction the system cannot execute,
    # which is #442's defect class exactly, found the first time a conflict
    # actually needed it (PR #443 against #425, 2026-10-20).
    #
    # Untracked files cannot be lost by a merge: git refuses one that would
    # overwrite an untracked path, with its own error. TRACKED modifications
    # still block, which is the case that matters.
    if git("status", "--porcelain", "--untracked-files=no").strip():
        print("COULD NOT RUN: the working tree has uncommitted TRACKED changes. "
              "Commit or stash first.")
        return 3
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch == "HEAD":
        print("COULD NOT RUN: detached HEAD. Check out the branch you mean.")
        return 3

    try:
        git("fetch", "origin", "--quiet")
    except RuntimeError as exc:
        print(f"COULD NOT RUN: {exc}")
        return 3

    before = git("rev-parse", "HEAD").strip()
    merged = subprocess.run(("git", "-C", str(ROOT), "merge", "--no-commit",
                             "--no-ff", args.base),
                            capture_output=True, text=True, timeout=300)
    if "Already up to date" in merged.stdout:
        print(f"NOTHING TO DO: {branch} already contains {args.base}.")
        git("merge", "--abort", check=False)
        return 4

    bad = [f for f in conflicted() if f not in MECHANICAL]
    if bad:
        print("REFUSED — conflicts outside the mechanical classes:")
        for f in bad:
            print(f"  - {f}")
        print("\nA conflict in a source file is a semantic question and this script\n"
              "cannot answer one. Resolve it by hand; the three it does handle are\n"
              f"{', '.join(MECHANICAL)}.")
        git("merge", "--abort", check=False)
        return 2

    # Git writes `>>>>>>> origin/main` as the closing marker, so the hunk parser
    # is given the ref and prefixes it itself.
    mark = args.base
    for f in conflicted():
        p = ROOT / f
        p.write_text(RESOLVERS[f](p.read_text(), mark))
        print(f"  resolved {f}  ({RESOLVERS[f].__name__})")
        git("add", f)

    # EXPECTED_TESTS IS NO LONGER MEASURED HERE (#446). It stopped being the
    # per-PR floor: `scripts/verify_test_floor.py` derives that from the merge
    # base and stores nothing. Rewriting the constant on every merge would put
    # the churn back in the one line this change exists to stop editing -- and
    # a RISING floor is still a diff on a shared line, which is all a conflict
    # needs. If a merge genuinely drops the count under the backstop, the gate
    # says so and names the tests.

    print("\nVerifying the MERGE RESULT, which is code no round has seen:")
    checks: list[tuple[bool, str]] = []
    markers = git("grep", "-n", "-e", "^<<<<<<< ", "-e", "^>>>>>>> ", check=False)
    ok = not markers.strip()
    print(f"  {'ok  ' if ok else 'FAIL'} no conflict markers anywhere in the tree")
    checks.append((ok, markers))
    checks.append(run("ast syntax sweep over src/ and scripts/", "bash", "-c",
                      "find src scripts -name '*.py' -print0 | xargs -0 -n1 "
                      "uv run python -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())'"))
    checks.append(run("behaviour suite", "uv", "run", "pytest", "-p", "no:warnings"))
    for g in ("verify_behaviour", "verify_architecture_counts",
              "verify_no_relaxation", "verify_token_budget"):
        checks.append(run(g, "uv", "run", "python", f"scripts/{g}.py"))

    if not all(ok for ok, _ in checks):
        print("\nMERGE LEFT UNCOMMITTED. The conflicts resolved cleanly and the result\n"
              "is still broken, which is the normal case here rather than a surprise:\n"
              "two merges on 2026-10-20 whose conflicts were purely mechanical both\n"
              "produced a red suite from defects neither branch could see alone.\n"
              "Look at what the merge broke; do not re-run this expecting a different\n"
              "answer.")
        for ok, out in checks:
            if not ok:
                print("\n--- first failure ---\n" + out[-2500:])
                break
        return 1

    git("commit", "--no-edit", "-m",
        f"Merge {args.base} into {branch}\n\n"
        f"Conflicts resolved mechanically by scripts/merge_main_into_branch.py:\n"
        f"decision-log rows unioned and date-ordered, mutation rows unioned with\n"
        f"nothing dropped. EXPECTED_TESTS is NOT touched (#446).\n\n"
        f"Verified ON THE MERGE RESULT: no conflict markers, ast syntax sweep,\n"
        f"behaviour suite, verify_behaviour, verify_architecture_counts,\n"
        f"verify_no_relaxation, verify_token_budget — all green.")
    print(f"\nMERGED and verified. {before[:9]} -> {git('rev-parse', 'HEAD').strip()[:9]}")
    if args.push:
        git("push", "origin", f"HEAD:refs/heads/{branch}")
        print(f"pushed to origin/{branch}")
    else:
        print("not pushed (pass --push).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
