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
  8. A workflow's `permissions:` may not WIDEN   (added 2026-11-01, #610)
  9. `TRUST_BOUNDARY` may not lose an entry      (added 2026-11-01, #610)

RULES 8 AND 9 ARE WHAT MAKE `chief` CLEARING A WORKFLOW PR NON-CIRCULAR.
Until 2026-11-01 a `.github/workflows/` PR was held for the owner, and the
stated reason was blast radius: "a workflow edit can grant the loop new powers
or disable the gates that constrain every other agent." The user then widened
chief's Shape C to the whole trust boundary — *"I want the loop to not hold on
me"* — which moved that risk from "a human looks at it" to "a gate catches it".

These two rules are that gate. `chief.md` is written against them: a red
`verify_no_relaxation` is never chief's to rule on, it is `insufficient-evidence`
and it goes to the owner. So if these two checks are weak, the whole grant is
weak, and that is why rule 8 fails CLOSED on a permissions block it has never
seen before rather than trying to judge whether the new scope is reasonable.

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

import yaml

#: GitHub's permission ladder. An omitted scope is `none`, never inherited, so
#: absence ranks 0 and "scope appeared at all" is a widening like any other.
_SCOPE_RANK = {"none": 0, "read": 1, "write": 2}
_SCOPE_NAME = {0: "none", 1: "read", 2: "write"}


def _normalise_perms(block: object) -> dict[str, int]:
    """A workflow `permissions:` value as {scope: rank}.

    Four shapes occur in practice and all four must map onto the same ladder:
      permissions:              -> {} (an empty value revokes everything)
      permissions: write-all    -> every scope at write, as `<all>`
      permissions: {}           -> {}
      permissions: {a: write}   -> {"a": 2}
    An unrecognised value ranks 2 rather than 0, so a shape this function has
    not met is treated as the widest thing it could be.
    """
    if block is None:
        return {}
    if isinstance(block, str):
        return {"<all>": _SCOPE_RANK.get(block.split("-", 1)[0], 2)}
    if isinstance(block, dict):
        return {str(k): _SCOPE_RANK.get(str(v), 2) for k, v in block.items()}
    return {"<unparseable>": 2}


def _perm_blocks(doc: object) -> dict[str, dict[str, int]]:
    """Every `permissions:` mapping in a parsed workflow, keyed by where it sits.

    Top-level and per-job are compared SEPARATELY and never merged: a job block
    overrides the top-level one entirely rather than adding to it, so summing
    them would both miss a widening and invent one.
    """
    if not isinstance(doc, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    if "permissions" in doc:
        out["<top-level>"] = _normalise_perms(doc["permissions"])
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        for jid, job in jobs.items():
            if isinstance(job, dict) and "permissions" in job:
                out[f"jobs.{jid}"] = _normalise_perms(job["permissions"])
    return out


def _trust_boundary(text: str) -> set[str]:
    """The paths in agent-merge's `TRUST_BOUNDARY: |` block.

    Read from the raw text rather than from parsed YAML on purpose: the block
    sits under `env:` inside a job, and a diff that breaks the YAML should fail
    rule 8's parse with a clear message rather than make this one quietly return
    an empty set — which would read as "nothing was lost".
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)TRUST_BOUNDARY:\s*\|\s*$", line)
        if not m:
            continue
        indent = len(m.group(1))
        paths = set()
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            if len(nxt) - len(nxt.lstrip()) <= indent:
                break
            paths.add(nxt.strip())
        return paths
    return set()

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

    # 4. mutations may not be deleted
    for path in [c for c in changed if "mutate_" in c]:
        b_txt, a_txt = at(base, path), at("HEAD", path)
        if b_txt is None or a_txt is None:
            continue
        b_n, a_n = mutation_rows(b_txt), mutation_rows(a_txt)
        what = "rows"
        if b_n is None or a_n is None:
            # No countable table on one side. Fall back to the old substring
            # tally rather than skip the file — but SAY it is a proxy, because
            # a number that claims to be a count and is not is the whole of
            # #389. A labelled proxy is honest; an unlabelled one costs the
            # next reader the time it takes to find out which number lied.
            b_n, a_n = b_txt.count('("'), a_txt.count('("')
            what = 'proxy `("` tally'
        if a_n < b_n:
            bad.append(f"{path}: mutation {what} fell {b_n} -> {a_n}. A harness that "
                       f"tests less proves less, and this repo has already had one enshrine a "
                       f"false positive. Removing a mutation needs a stated reason and a human.")
        else:
            print(f"  ok   mutations kept     {path} ({what} {b_n} -> {a_n})")

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

    # 8. A workflow's `permissions:` may not widen.
    #
    # WHY THIS FAILS CLOSED ON A BLOCK IT HAS NOT SEEN BEFORE. A brand-new
    # `permissions:` mapping -- a new workflow file, or a new job in an existing
    # one -- is reported as a weakening even though nothing shrank, because a new
    # block is the obvious way to grant a power without touching an old one. The
    # cost of that strictness is bounded and already paid: the App token is
    # refused the `workflows` permission, so EVERY change under
    # `.github/workflows/` already comes from a human or a Claude session and
    # already needs one merge. Failing here costs that same merge and buys a
    # check that cannot be talked around.
    wf_changed = [c for c in changed
                  if c.startswith(".github/workflows/") and c.endswith((".yml", ".yaml"))]
    for path in wf_changed:
        a_txt, b_txt = at("HEAD", path), at(base, path)
        if a_txt is None:
            continue            # deleted; the EXPECTED_WORKFLOWS floor owns that
        try:
            after = _perm_blocks(yaml.safe_load(a_txt))
            before = _perm_blocks(yaml.safe_load(b_txt)) if b_txt is not None else {}
        except yaml.YAMLError as exc:
            bad.append(f"{path}: cannot be parsed as YAML ({exc.__class__.__name__}), so its "
                       f"`permissions:` cannot be compared. An unreadable gate is not a pass.")
            continue
        for where, a_block in after.items():
            b_block = before.get(where)
            if b_block is None:
                granted = sorted(k for k, v in a_block.items() if v > 0)
                if granted:
                    bad.append(
                        f"{path}: `permissions:` at `{where}` is new, granting "
                        f"{', '.join(granted)}. A new block is how a power gets added without "
                        f"widening an old one, so this gate does not judge it — a human does.")
                continue
            for scope, rank in a_block.items():
                was = b_block.get(scope, 0)
                if rank > was:
                    bad.append(
                        f"{path}: `permissions:` at `{where}` widens `{scope}` "
                        f"({_SCOPE_NAME.get(was, was)} -> {_SCOPE_NAME.get(rank, rank)}). "
                        f"Granting the loop a scope it did not have is the one change an agent "
                        f"clearing it would be deciding its own constraints.")
        if not any(b.startswith(path) for b in bad):
            print(f"  ok   permissions held  {path} ({len(after)} block(s))")

    # 9. `TRUST_BOUNDARY` may not lose an entry.
    #
    # It is the list of paths `agent-merge` holds for review. Removing one is not
    # a relaxation of a number or a phrase — it silently takes a whole class of
    # diff out of the hold, and the PR that did it would look like a tidy-up.
    # ADDING an entry is fine and deliberately unchecked: a wider boundary holds
    # more, never less.
    if am in changed:
        a_tb = _trust_boundary(at("HEAD", am) or "")
        b_tb = _trust_boundary(at(base, am) or "")
        if b_tb and not a_tb:
            bad.append(f"{am}: the `TRUST_BOUNDARY` block is gone. Every boundary path it "
                       f"listed is now unheld, and `chief` has nothing left to clear.")
        elif lost := sorted(b_tb - a_tb):
            bad.append(f"{am}: `TRUST_BOUNDARY` lost {', '.join(lost)}. A path removed from "
                       f"the boundary stops being held at all — that is wider than anything "
                       f"`chief` was granted, which only clears a hold case by case.")
        elif b_tb:
            print(f"  ok   boundary intact    {am} ({len(a_tb)} path(s))")

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
