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
  4. The TOTAL mutation-row count may not fall, across the WHOLE harness
     (a harness that tests less proves less. The total rather than per
      file, so the floor survives the rows being reorganised; moving a
      row between harness files is free, losing one is not)
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
import ast
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

# file -> phrases that must still appear in it at HEAD.
#
# One entry today, and the loop below is written for many on purpose: the
# first attempt to add a second one is what exposed the defect this commit
# fixes. #361's outsider policy is the waiting caller -- it is prose in a file
# agents edit, and it lands here once that branch is on main.
REQUIRED_SUBSTRINGS = {
    ".github/workflows/agent-merge.yml": ["qa-pass", "qa-fail"],
    # #361. The loop does not implement an outsider's issue, under any label or
    # assignment. Floored because it lives as PROSE in files agents are expected
    # to edit, and because the softening is specific and predictable: the rule
    # REPLACED a "proceed, but under four stricter rules" version, so reverting
    # to one is the obvious move for an agent that wants to work an issue it has
    # been told to skip.
    #
    # Phrases, not paraphrases: each is a single line in the file, short enough
    # to survive reflow and distinctive enough that nothing else matches it.
    ".claude/commands/agent-cycle.md": [
        "Comment, label, skip",
        "under any label, assignment or circumstance",
    ],
    ".claude/agents/project-manager.md": ["not ranked at all"],
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


def _in_harness(path: str) -> bool:
    """Is this a file where mutation rows may live?

    Two conventions, both deliberate. `mutate_` is the historical one --
    `mutate_behaviour_suite.py`, `mutate_verify_workflows.py`,
    `mutate_natal_prompt_gate.py`. `scripts/mutations/` is where per-area
    tables go, so that two PRs touching different code never touch the same
    table and never conflict.
    """
    if not path.endswith(".py"):
        return False
    # ANCHORED to `scripts/`, not a substring match on `mutate_` anywhere in
    # the path. The first draft used `"mutate_" in path`, which is correct for
    # all five harness files today and wrong the moment someone adds
    # `tests/test_mutate_behaviour_suite.py` -- the obvious name, and the split
    # that motivated this rule plausibly adds it. Two effects, and the second
    # is the one that matters: `note` noise for an uncountable test file, and a
    # `MUTATIONS = [...]` FIXTURE inside a test counted into the production
    # total, where it could offset a real deletion. Found by the independent
    # round on this PR.
    return path.startswith("scripts/mutations/") or path.startswith("scripts/mutate_")


def harness_rows(ref: str) -> tuple[int | None, list[str]]:
    """(total MUTATIONS rows across the harness at `ref`, files with no table).

    None for the total only when the tree cannot be listed at all. A file that
    exists but is uncountable contributes 0 and is NAMED in the second element,
    because "uncountable" and "empty" produce the same number and only one of
    them is fine: `mutate_natal_prompt_gate.py` has no table by design, while a
    file whose table stopped parsing is a hole.
    """
    try:
        paths = [p for p in git("ls-tree", "-r", "--name-only", ref).splitlines()
                 if _in_harness(p)]
    except RuntimeError:
        return None, []
    total, uncountable = 0, []
    for path in paths:
        n = mutation_rows(at(ref, path))
        if n is None:
            uncountable.append(path)
        else:
            total += n
    return total, uncountable


def mutation_rows(text: str | None) -> int | None:
    """Rows in a mutation harness's MUTATIONS table, or None if not countable.

    #389. This used to be `text.count('("')` — a tally of a two-character
    substring over the WHOLE module, so it also counted tuples nested inside
    mutation bodies and every `print("` and `re.search("` in the file. On the
    real harness it read 183 against a table of 141, and the harness's own
    output two lines away said `141/141 mutations caught`.

    The wrong number was the cheaper half of the defect. The expensive half is
    that a tally over the whole file can RISE while a row is deleted: one added
    comment containing `("` pays for the row that left, and rule 4's floor is
    "the number did not fall". A real row count cannot be bought that way.

    None, not 0, when there is no readable table: `mutate_natal_prompt_gate.py`
    has no MUTATIONS at all and rule 4 selects it on filename alone. Returning
    0 there would read as "the table emptied" and fail every diff touching it.
    """
    if not text:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None  # a side we cannot parse is a side we cannot count
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(getattr(t, "id", "") == "MUTATIONS" for t in targets):
            continue
        if isinstance(node.value, (ast.List, ast.Tuple)):
            return len(node.value.elts)
        return None  # built by concatenation or a call — not a literal to count
    return None


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

    # 4. the TOTAL mutation-row count may not fall.
    #
    # PER FILE WAS THE WRONG UNIT, and it only became wrong when the rows
    # needed reorganising. Every PR in this repo appends to the end of ONE
    # table in `scripts/mutate_behaviour_suite.py`, so two PRs conflict there
    # by construction -- four resolutions in two hours on 2026-11-01, each
    # costing a full suite run and a re-gate. Splitting that table per area
    # makes the conflicts impossible, and a per-file floor FORBIDS the split:
    # the main file's count goes to zero however carefully the rows are kept.
    #
    # THE TEMPTING SHORTCUT WAS A SILENT WEAKENING, which is why this rule
    # moved rather than being worked around. Writing
    # `MUTATIONS = [...] + _load_area_rows()` makes `mutation_rows` return
    # None -- "built by concatenation or a call, not a literal to count" -- the
    # old code then fell back to the `("` proxy tally, and the proxy would have
    # PASSED, because the file's text barely changes. `mutation_rows`'s own
    # docstring says why that is worthless: "a tally over the whole file can
    # RISE while a row is deleted: one added comment containing `("` pays for
    # the row that left." The split would have been waved through by a check
    # that had quietly stopped counting, which is the exact shape this file
    # exists to refuse.
    #
    # The invariant that actually matters is the one asserted now: HOW MANY
    # MUTATIONS DOES THE HARNESS HAVE. Indifferent to layout, not buyable with
    # a comment, and still red on a deleted row wherever that row lived.
    #
    # Read from BOTH TREES rather than from the diff, like rule 7: a total is
    # not a property of the files that happen to have changed, and a row moved
    # out of the surface entirely would otherwise be invisible.
    b_total, _b_un = harness_rows(base)
    a_total, a_un = harness_rows("HEAD")
    if b_total is None or a_total is None:
        bad.append("could not list the mutation harness on one side, so the row total "
                   "cannot be compared. An uncountable harness is not a pass.")
    elif a_total < b_total:
        bad.append(f"mutation rows fell {b_total} -> {a_total} across the harness. A harness "
                   f"that tests less proves less, and this repo has already had one enshrine "
                   f"a false positive. Removing a mutation needs a stated reason and a human. "
                   f"Moving rows BETWEEN harness files is free; only the total is floored.")
    else:
        delta = "" if a_total == b_total else f" ({b_total} -> {a_total})"
        print(f"  ok   mutation rows      {a_total} total{delta}")
    # Named, every run. A file that stops being countable is how a total
    # silently stops including it, and #389 is this repo's record of a count
    # that lied for weeks while the harness's own output disagreed two lines
    # away.
    for path in sorted(set(a_un)):
        print(f"  note no countable MUTATIONS table  {path} (contributes 0)")

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
        if not any(b.startswith(am) for b in bad):
            print(f"  ok   gate chain intact  {am}")

    # 7. Phrases that must survive, in EVERY file that declares one.
    #
    # This loop used to live inside the `if am in changed:` block above and read
    # `REQUIRED_SUBSTRINGS.get(am, ...)` -- so it only ever consulted the
    # agent-merge entry, and any other key added to the table was INERT. Found
    # 2026-10-15 by adding the #361 policy floors and watching the gate stay
    # green while the phrase was deleted. A floor nobody checks is worse than no
    # floor, because it is cited as protection.
    #
    # Checked on EVERY run, not only when the file is in the diff: the point is
    # that the phrase is present, and a diff-scoped check cannot notice a file
    # that was weakened on a branch this run did not compare against.
    for path, needed_list in REQUIRED_SUBSTRINGS.items():
        txt = at("HEAD", path)
        if txt is None:
            bad.append(f"{path}: declared in REQUIRED_SUBSTRINGS and not readable at HEAD. "
                       f"A guarded file that vanished is a weakening, not a skip.")
            continue
        missing = [n for n in needed_list if n not in txt]
        if missing:
            for n in missing:
                bad.append(f"{path}: `{n}` no longer appears. It is floored because the rule "
                           f"it carries is one an agent is tempted to soften rather than keep.")
        else:
            print(f"  ok   phrases floored   {path} ({len(needed_list)})")

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
