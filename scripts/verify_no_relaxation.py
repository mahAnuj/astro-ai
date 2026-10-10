#!/usr/bin/env python3
"""Fail a diff that WEAKENS a guardrail instead of fixing the defect.

WHY THIS EXISTS
---------------
`steward` is allowed to repair the pipeline, which it must be: the alternative
is that every pipeline bug routes its fix THROUGH the broken pipeline. That
deadlocked on 2026-10-10, when the `actions: read` fix for a 403 that had
silenced the measurement arm since it was wired sat in PR #315, waiting for a
`qa-pass` that needed a cycle that needed the pipeline.

But a role that repairs the gates has one tempting move available every single
time: relax whatever is blocking the work. It will have a good reason, because
the constraint IS what is blocking it. This repo has the same failure twice
already, as `USER AUTHORISED PUSH this turn` written into a status file and
then cited as the authorisation.

ASKING A QA AGENT TO JUDGE INTENT IS THE WEAK FORM, because a fix and a
relaxation look identical. For the cancelled-check-run defect, all three of
these unblock PR #319:

  1. reduce check runs to the latest per name     <- preserves the rule
  2. ignore a `cancelled` conclusion              <- slightly weaker
  3. require checks to be "not failure"           <- a relaxation in a fix's
                                                     clothes, and it works

An agent judging intent waves (3) through on a bad day. So this gate does not
judge intent. It compares the diff against a list of invariants that can only
move one way, and refuses the ones that moved the wrong way.

WHAT IT CHECKS, each against the merge base
  1. A numeric FLOOR may not fall      (EXPECTED_TESTS, EXPECTED_WORKFLOWS)
  2. A numeric CEILING may not rise    (MAX_LINES — the unattended diff limit)
  3. `disallowedTools` may not shrink  (removing a denial grants a power)
  4. A mutation may not be deleted     (a harness that tests less proves less)
  5. agent-merge's gate chain stays    (own -> gates -> qa -> size -> merge:
     every step's `if:` must still depend on its predecessor, which is what
     makes a single removed line unable to skip a condition)
  6. `qa-pass` / `qa-fail` handling in agent-merge stays present
  7. THIS FILE may not be edited in the same diff as anything it guards

Rule 7 is the one that keeps the rest honest. A change to the detector of
relaxations is the single change a human should look at, so it is allowed —
alone, and only alone.

EXIT CODES
  0  nothing weakened
  1  a guardrail was weakened
  2  could not determine (no git, no merge base) — NOT a pass

USAGE
  uv run python scripts/verify_no_relaxation.py [--base origin/main]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

SELF = "scripts/verify_no_relaxation.py"

# name -> (file, regex capturing one integer, direction that is a WEAKENING)
FLOORS = {
    "EXPECTED_TESTS": ("scripts/verify_behaviour.py", r"EXPECTED_TESTS\s*=\s*(\d+)", "down"),
    "EXPECTED_WORKFLOWS": ("scripts/verify_workflows.py", r"EXPECTED_WORKFLOWS\s*=\s*(\d+)", "down"),
    "MAX_LINES": (".github/workflows/agent-merge.yml", r"MAX_LINES:\s*(\d+)", "up"),
}

# agent-merge's chain. Each step's `if:` must still name its predecessor's
# output, so that deleting one line cannot quietly skip a condition.
CHAIN = [("own", "gates"), ("gates", "qa"), ("qa", "size")]

REQUIRED_SUBSTRINGS = {
    ".github/workflows/agent-merge.yml": ["qa-pass", "qa-fail"],
}


def git(*a: str) -> str:
    r = subprocess.run(("git", *a), capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[:200]}")
    return r.stdout


def at(ref: str, path: str) -> str | None:
    try:
        return git("show", f"{ref}:{path}")
    except RuntimeError:
        return None  # absent on that side


def ints(text: str | None, pattern: str) -> list[int]:
    return [int(m) for m in re.findall(pattern, text or "")]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv[1:])

    print("Guardrail-relaxation gate — compares the diff against invariants\n")

    # Try several bases. In `pr-gates` the checkout is `fetch-depth: 0`, so
    # `origin/main` resolves — but a shallow clone, a detached HEAD or a local
    # run may not have it, and this gate joins the sweep that every PR runs.
    # Failing every PR because a ref name differs would be a far worse defect
    # than the one this file prevents, so fall back before giving up.
    base, how = None, ""
    for cand in (args.base, "main", "origin/HEAD", "HEAD~1"):
        try:
            base = git("merge-base", "HEAD", cand).strip()
            how = cand
            break
        except RuntimeError:
            continue
    if not base:
        print("COULD NOT VERIFY (exit 2) — no usable base; tried "
              f"{args.base}, main, origin/HEAD, HEAD~1.")
        print("This is NOT a pass: an unverified diff may be weakening a guardrail.")
        return 2
    try:
        changed = [l for l in git("diff", "--name-only", f"{base}..HEAD").splitlines() if l]
    except RuntimeError as exc:
        print(f"COULD NOT VERIFY (exit 2) — {exc}")
        print("This is NOT a pass: an unverified diff may be weakening a guardrail.")
        return 2

    if not changed:
        print("PASS — no files changed against the merge base.")
        return 0

    print(f"  base {base[:9]} (via {how}), {len(changed)} file(s) changed\n")
    bad: list[str] = []

    # 7. this file, alone or not at all — but only once it EXISTS.
    #
    # Adding it for the first time cannot be a relaxation of itself, and the
    # first draft fired on exactly that, which made every adversarial test below
    # pass for the wrong reason: rule 7 caught them, and rules 1-6 were never
    # exercised at all. A gate validated by a rule other than the one under test
    # is a vacuous pass, which is the defect this whole repo keeps finding.
    if SELF in changed and at(base, SELF) is not None and len(changed) > 1:
        others = [c for c in changed if c != SELF]
        bad.append(f"{SELF} is edited alongside {len(others)} other file(s): {', '.join(others[:4])}."
                   " A change to the relaxation detector must land ALONE so a human can read it"
                   " against nothing else. Split the commit.")

    # 1 + 2. numeric floors and ceilings
    for name, (path, pat, weaken) in FLOORS.items():
        before, after = ints(at(base, path), pat), ints(at("HEAD", path), pat)
        if not before or not after:
            continue
        b, a = before[0], after[0]
        if b == a:
            print(f"  ok   {name:20} {a} (unchanged)")
        elif (weaken == "down" and a < b) or (weaken == "up" and a > b):
            bad.append(f"{name} moved {b} -> {a} in {path}, which is a WEAKENING. "
                       f"A floor may only rise and a ceiling may only fall. If this is "
                       f"deliberate it needs a human, not a gate.")
        else:
            print(f"  ok   {name:20} {b} -> {a} (tightened)")

    # 3. denial lists may not shrink
    for path in [c for c in changed if c.startswith(".github/workflows/")]:
        b_txt, a_txt = at(base, path), at("HEAD", path)
        if b_txt is None or a_txt is None:
            continue
        b_den = set(re.findall(r"Bash\(([^)]+)\)", re.search(r"disallowedTools[^\n]*\n?[^\n]*", b_txt).group(0))) \
            if "disallowedTools" in b_txt else set()
        a_den = set(re.findall(r"Bash\(([^)]+)\)", re.search(r"disallowedTools[^\n]*\n?[^\n]*", a_txt).group(0))) \
            if "disallowedTools" in a_txt else set()
        gone = b_den - a_den
        if gone:
            bad.append(f"{path}: disallowedTools lost {sorted(gone)}. Removing a denial GRANTS a "
                       f"power, which is a relaxation however it is framed.")
        elif b_den:
            print(f"  ok   denials kept        {path} ({len(a_den)})")

    # 4. mutations may not be deleted
    for path in [c for c in changed if "mutate_" in c]:
        b_txt, a_txt = at(base, path), at("HEAD", path)
        if b_txt is None or a_txt is None:
            continue
        b_n, a_n = b_txt.count('("'), a_txt.count('("')
        if a_n < b_n:
            bad.append(f"{path}: mutation/control entries fell {b_n} -> {a_n}. A harness that "
                       f"tests less proves less, and this repo has already had one enshrine a "
                       f"false positive. Removing a mutation needs a stated reason and a human.")
        else:
            print(f"  ok   mutations kept     {path} ({b_n} -> {a_n})")

    # 5 + 6. agent-merge's chain and its verdict handling
    am = ".github/workflows/agent-merge.yml"
    if am in changed:
        a_txt = at("HEAD", am) or ""
        for prev, step in CHAIN:
            if not re.search(rf"name:[^\n]*\n\s*id:\s*{step}\b", a_txt) and f"id: {step}" not in a_txt:
                bad.append(f"{am}: step `id: {step}` is gone. That breaks the chain "
                           f"{' -> '.join(p for p, _ in CHAIN)} -> merge, and a missing link "
                           f"is a skipped condition.")
            elif f"steps.{prev}.outputs.ok" not in a_txt:
                bad.append(f"{am}: nothing depends on `steps.{prev}.outputs.ok` any more, so the "
                           f"`{prev}` condition can no longer block a merge.")
        for needed in REQUIRED_SUBSTRINGS.get(am, []):
            if needed not in a_txt:
                bad.append(f"{am}: `{needed}` no longer appears. The QA verdict is the one thing "
                           f"an agent must not be able to route around.")
        if not any(b.startswith(am) for b in bad):
            print(f"  ok   gate chain intact  {am}")

    print()
    if bad:
        for b in bad:
            print(f"FAIL  {b}")
        print(f"\nFAIL - {len(bad)} guardrail(s) weakened. A fix that removes the condition "
              "is not a fix. If the constraint is genuinely wrong, say so on the issue and "
              "let a human change it.")
        return 1

    print("PASS — no guarded invariant moved the wrong way.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
