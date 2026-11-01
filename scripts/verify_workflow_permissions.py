#!/usr/bin/env python3
"""Fail a diff that WIDENS a workflow's permissions or SHRINKS the trust boundary.

WHY THIS EXISTS

Until 2026-11-01 a PR touching `.github/workflows/` was held for the repo
owner, and the reason recorded in `.claude/agents/chief.md` was blast radius:
"a workflow edit can grant the loop new powers, read secrets, or disable the
gates that constrain every other agent. An agent clearing a change to the thing
that constrains agents is circular."

The owner then widened `chief`'s authority to the whole trust boundary — *"I
want the loop to not hold on me"*. That does not make the blast radius smaller.
It moves the risk from "a human reads every such diff" to "a gate catches the
two things that actually matter". This file is that gate, and `chief.md` is
written against it by name: a red run here is never chief's to rule on, it is
`insufficient-evidence`, and it goes to the owner.

So if these checks are weak, the grant is weak. That is why check 1 fails
CLOSED on a permissions block it has never seen before rather than trying to
judge whether a new scope is reasonable.

WHAT IT CHECKS, each against the merge base

  1. No JOB's EFFECTIVE permissions may WIDEN.
     The unit is the job, not the declared block, and that distinction is the
     whole of this check. A job's effective permissions are its own
     `permissions:` if it declares one, ELSE the workflow's top-level block,
     ELSE the repository default.

     THE FIRST DRAFT COMPARED DECLARED BLOCKS AND HAD A HOLE WIDE ENOUGH TO
     DRIVE THROUGH. `agent-merge.yml` carries a top-level
     `contents/pull-requests/issues: write, actions: write` and its one job
     declares nothing, so appending a second job gained the entire write set
     while adding ZERO new blocks — and the gate printed PASS. Eight of this
     repo's workflows are top-level-only and so were all exposed. Found by the
     independent round on this gate's own PR, demonstrated against the shipped
     file with a job that called `gh api -X PUT .../branches/main/protection`.

     Consequences of keying on the job instead:
       * a NEW job fails closed, because it gains whatever it inherits
       * a job whose own narrow block is DELETED under a broader top-level one
         is a widening, and is now caught
       * a workflow declaring nothing anywhere ranks `<repo-default>` WIDE,
         because that default is an admin toggle outside git which no gate can
         see. Measured 2026-11-01: `default_workflow_permissions: read`. It can
         be flipped to write without any diff.
       * a top-level widening under jobs that all declare their own block is NOT
         flagged, correctly — nothing can reach it.

     An omitted scope is `none` (GitHub never inherits one), so a scope merely
     APPEARING is a widening. `write-all` is normalised to an `<all>` scope and
     consulted as a FALLBACK rank, so tightening `write-all` to a narrow
     mapping reads as the narrowing it is. A workflow that cannot be parsed
     fails rather than being skipped.

  2. `TRUST_BOUNDARY` in `agent-merge.yml` may not lose an entry.
     Removing a path does not relax a number or a phrase; it takes a whole
     class of diff out of the hold, and the PR doing it reads as a tidy-up.
     Compared as a SET, because swapping one path for another keeps the count
     identical. ADDING an entry is deliberately unchecked: a wider boundary
     holds more, never less.

WHY THIS IS NOT PART OF `verify_no_relaxation.py`

It belongs there by subject, and it cannot live there. That file's own rule 7
refuses any diff that edits it alongside another file — "a change to the
relaxation detector must land ALONE so a human can read it against nothing
else" — and `ALONE` includes its tests and its mutation rows. So a TESTED
addition to it is not expressible in one PR: the gate would land unproven and
its proof would follow in a second merge.

Rule 7 is right and was not narrowed to make this convenient. A sibling gate
costs one more file in the `scripts/verify_*.py` sweep, which `pr-gates.yml`
discovers with a glob, and buys code and proof landing together. It also keeps
this PR inside `scripts/` and `tests/`, so the loop can merge it without a
human — which is the whole point of the change it exists to protect.

The ~25 lines of merge-base resolution below are duplicated from that file for
the same reason: extracting them into a shared helper would be an edit to it.

EXIT CODES
  0  nothing widened or removed
  1  a permission widened, or a boundary path was removed
  2  could not determine (no git, no merge base) — NOT a pass

USAGE
  uv run python scripts/verify_workflow_permissions.py [--base origin/main]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

import yaml

AGENT_MERGE = ".github/workflows/agent-merge.yml"

#: GitHub's permission ladder. An omitted scope is `none`, never inherited, so
#: absence ranks 0 and "the scope appeared at all" is a widening like any other.
_SCOPE_RANK = {"none": 0, "read": 1, "write": 2}
_SCOPE_NAME = {0: "none", 1: "read", 2: "write"}


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


def normalise_perms(block: object) -> dict[str, int]:
    """A workflow `permissions:` value as {scope: rank}.

    Four shapes occur in practice and all four must land on the same ladder:
      permissions:              -> {} (an empty value revokes everything)
      permissions: write-all    -> every scope at write, as `<all>`
      permissions: {}           -> {}
      permissions: {a: write}   -> {"a": 2}

    An unrecognised value ranks 2 rather than 0, so a shape this function has
    not met is treated as the widest thing it could be. The other direction
    would make `contents: <some value GitHub adds later>` read as a REVOCATION,
    and the gate would then report a widening as a tightening. Ranking it wide
    can only produce a false red, which costs one human merge.
    """
    if block is None:
        return {}
    if isinstance(block, str):
        return {"<all>": _SCOPE_RANK.get(block.split("-", 1)[0], 2)}
    if isinstance(block, dict):
        return {str(k): _SCOPE_RANK.get(str(v), 2) for k, v in block.items()}
    return {"<unparseable>": 2}


#: A workflow that declares no `permissions:` anywhere runs with the REPOSITORY
#: DEFAULT. That is an admin toggle outside git -- measured 2026-11-01 as
#: `default_workflow_permissions: read` -- so it can be flipped to write with no
#: diff and no gate able to see it. Represented by a sentinel that ranks WIDE,
#: which makes such a workflow fail closed rather than silently inherit
#: whatever the toggle says today.
REPO_DEFAULT = "<repo-default>"

_MISSING = object()


def perm_blocks(doc: object) -> dict[str, dict[str, int]]:
    """Every DECLARED `permissions:` mapping, keyed by where it sits.

    Retained because it answers "what does this file say", which the tests
    assert directly. Check 1 does NOT use it: a declared block is not what a
    job runs with. See `effective_jobs`.
    """
    if not isinstance(doc, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    if "permissions" in doc:
        out["<top-level>"] = normalise_perms(doc["permissions"])
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        for jid, job in jobs.items():
            if isinstance(job, dict) and "permissions" in job:
                out[f"jobs.{jid}"] = normalise_perms(job["permissions"])
    return out


def effective_jobs(doc: object) -> dict[str, dict[str, int]]:
    """Every JOB's EFFECTIVE permissions -- what the job's token actually gets.

    A job block OVERRIDES the top-level one rather than adding to it, so the
    resolution is a choice and not a merge: own block, else top-level, else the
    repository default sentinel.

    Keyed by `jobs.<id>` only. There is deliberately no `<top-level>` entry: a
    top-level block that every job overrides grants nothing, and flagging it
    would be a false red -- the kind that teaches the loop its reds are noise.
    """
    if not isinstance(doc, dict):
        return {}
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return {}
    top = doc.get("permissions", _MISSING)
    out: dict[str, dict[str, int]] = {}
    for jid, job in jobs.items():
        if isinstance(job, dict) and "permissions" in job:
            out[f"jobs.{jid}"] = normalise_perms(job["permissions"])
        elif top is not _MISSING:
            out[f"jobs.{jid}"] = normalise_perms(top)
        else:
            out[f"jobs.{jid}"] = {REPO_DEFAULT: 2}
    return out


def rank_of(block: dict[str, int], scope: str) -> int:
    """This block's rank for `scope`, honouring a `write-all`/`read-all` shorthand.

    Without the `<all>` fallback, tightening `permissions: write-all` to
    `{contents: read}` read as `contents` going none -> read -- a WIDENING
    reported on a genuine narrowing. A gate that reds when you tighten is a
    gate that gets switched off.
    """
    if scope in block:
        return block[scope]
    if "<all>" in block:
        return block["<all>"]
    return 0


def trust_boundary(text: str) -> set[str]:
    """The paths in agent-merge's `TRUST_BOUNDARY: |` block.

    Read from the raw text rather than from parsed YAML on purpose: the block
    sits under `env:` inside a job, and a diff that breaks the YAML should fail
    check 1's parse with a clear message rather than make this one quietly
    return an empty set — which would read as "nothing was lost".
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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv[1:])

    print("Workflow-permission gate — compares the diff against the merge base\n")

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
        print("This is NOT a pass: an unverified diff may be granting a power.")
        return 2
    try:
        changed = [l for l in git("diff", "--name-only", f"{base}..HEAD").splitlines() if l]
    except RuntimeError as exc:
        print(f"COULD NOT VERIFY (exit 2) — {exc}")
        print("This is NOT a pass: an unverified diff may be granting a power.")
        return 2

    wf_changed = [c for c in changed
                  if c.startswith(".github/workflows/") and c.endswith((".yml", ".yaml"))]
    if not wf_changed:
        print(f"PASS — no workflow file changed against {base[:9]} (via {how}).")
        return 0

    print(f"  base {base[:9]} (via {how}), {len(wf_changed)} workflow file(s) changed\n")
    bad: list[str] = []

    # 1. permissions may not widen
    for path in wf_changed:
        a_txt, b_txt = at("HEAD", path), at(base, path)
        if a_txt is None:
            # Deleted. `verify_workflows.py`'s EXPECTED_WORKFLOWS floor owns
            # that case, and a deleted workflow grants nothing.
            print(f"  ok   deleted            {path}")
            continue
        try:
            after = effective_jobs(yaml.safe_load(a_txt))
            before = effective_jobs(yaml.safe_load(b_txt)) if b_txt is not None else {}
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
                        f"{path}: `{where}` is new, and effectively grants "
                        f"{', '.join(granted)}. A new job gains whatever it inherits without "
                        f"adding any block, so this gate does not judge it — a human does.")
                continue
            # The UNION of both sides' scopes, consulted through `rank_of`.
            # Walking only `a_block` missed nothing, but walking it with a plain
            # `.get(scope, 0)` mishandled `<all>` on the base side.
            for scope in sorted(set(a_block) | set(b_block)):
                was, rank = rank_of(b_block, scope), rank_of(a_block, scope)
                if rank > was:
                    bad.append(
                        f"{path}: `permissions:` at `{where}` widens `{scope}` "
                        f"({_SCOPE_NAME.get(was, was)} -> {_SCOPE_NAME.get(rank, rank)}). "
                        f"Granting the loop a scope it did not have is the one change an agent "
                        f"clearing it would be deciding its own constraints.")
        if not any(b.startswith(path) for b in bad):
            print(f"  ok   permissions held  {path} ({len(after)} job(s))")

    # 2. TRUST_BOUNDARY may not lose an entry
    if AGENT_MERGE in wf_changed:
        a_tb = trust_boundary(at("HEAD", AGENT_MERGE) or "")
        b_tb = trust_boundary(at(base, AGENT_MERGE) or "")
        if b_tb and not a_tb:
            bad.append(f"{AGENT_MERGE}: the `TRUST_BOUNDARY` block is gone. Every boundary "
                       f"path it listed is now unheld, and `chief` has nothing left to clear.")
        elif lost := sorted(b_tb - a_tb):
            bad.append(f"{AGENT_MERGE}: `TRUST_BOUNDARY` lost {', '.join(lost)}. A path removed "
                       f"from the boundary stops being held at all — that is wider than "
                       f"anything `chief` was granted, which only clears a hold case by case.")
        elif b_tb:
            print(f"  ok   boundary intact   {AGENT_MERGE} ({len(a_tb)} path(s))")

    print()
    if bad:
        for b in bad:
            print(f"FAIL  {b}")
        print(f"\nFAIL — {len(bad)} widening(s). A workflow edit that grants the loop a power "
              "it did not have is not `chief`'s to clear: it is `insufficient-evidence` and it "
              "goes to the owner. If the grant is genuinely wanted, a human merges it.")
        return 1

    print("PASS — no permission widened and no boundary path was removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
