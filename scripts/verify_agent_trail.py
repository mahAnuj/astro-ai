#!/usr/bin/env python3
"""Gate: every agent definition says where its output goes (#607).

WHY THIS EXISTS

`CLAUDE.md` used to tell every agent, in bold, to leave its trail in
`AGENT_STATUS.md` — a file `.gitignore:38` ignores. Nothing written there
leaves the machine it was written on. That was the only instruction most
agents got: measured 2026-10-30, **3 of 15** definitions mentioned commenting
on an issue, and the twelve without it included `engineer`, `qa`, `architect`
and `dev-lead`, the four that do the shipping.

The cost was observed, not hypothesised. Five issues (#573, #389, #510, #468,
#465) were audited that day and found already complete; **four carried zero
comments**, so closing them would have left no record of why, and the next
cycle would have had to redo the audit. #573 needed a workflow run-log read to
discover that `close-on-evidence` had declined it over a `refs` keyword —
nothing on the issue said so.

`CLAUDE.md` explains why stating it once was never going to work:

    "A subagent reads only its own definition and its prompt, so a rule stated
     once centrally is a rule most of them never see."

That is why the never-push rule is repeated in 9 of the 15 files. This rule was
stated once, centrally, pointing at a gitignored file. So it is now repeated in
all fifteen — and this gate is what stops it rotting back out, because a rule
with no gate is how it got here.

WHAT IT CHECKS

The agent list is DERIVED from `.claude/agents/*.md`, never hardcoded, so a
sixteenth agent added without the rule fails too. For each definition:

  - it carries the `## Where your output goes` section
  - that section names the **issue** and the **PR** distinctly, because they do
    different jobs: the issue is the durable decision record, the PR is the
    review at the point of review
  - it states that `AGENT_STATUS.md` is local only, so no agent treats a line
    it wrote there as the record

And in `CLAUDE.md`: the three surfaces are named, and the bold instruction no
longer presents `AGENT_STATUS.md` as the record.

A FILE IT CANNOT PARSE IS A FAILURE, NOT A SKIP. Same rule, and same reason, as
`verify_architecture_counts.py`: a checker that silently narrows its own scope
and reports success is worse than no checker, because the success gets quoted
later as evidence.

WHAT THIS DOES NOT CHECK, PLAINLY

  - That an agent actually comments. This reads definitions, not behaviour. An
    agent can carry the rule and ignore it; only the absence of a comment on a
    worked issue shows that, and nothing here can see it.
  - Whether what an agent writes is any good, or true.
  - Three roles write no routine PR comment — `analyst`, `product-manager` and
    `project-manager` — and they still have to name the PR surface to say
    "nothing routinely", which is deliberate: that is an answer, silence is
    not. (`chief` and `steward` DO specify one. An earlier draft of this
    sentence named the wrong three; QA on PR #609 caught it.)
  - Both markers are LITERAL strings, not meanings. Rewording `**On the PR:**`
    to `**On the PR**:` fails. That is the trade for machine-checkability, and
    this docstring says so rather than claiming the checks are about substance.

    uv run python scripts/verify_agent_trail.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude/agents"
CLAUDE = ROOT / "CLAUDE.md"

SECTION = "## Where your output goes"
LOCAL_ONLY = "local heartbeat"


def main() -> int:
    if not AGENTS.is_dir():
        print("COULD NOT RUN (exit 2) — .claude/agents is not a directory")
        return 2
    files = sorted(AGENTS.glob("*.md"))
    if not files:
        print("COULD NOT RUN (exit 2) — no agent definitions found")
        return 2

    print(f"Agent audit trail — {len(files)} definitions, derived from the directory\n")
    bad: list[str] = []

    for f in files:
        name = f.stem
        try:
            s = f.read_text()
        except OSError as exc:                                 # pragma: no cover
            bad.append(f"{name}: unreadable ({exc})")
            print(f"  FAIL  {name} — unreadable")
            continue

        if SECTION not in s:
            bad.append(f"{name}: no '{SECTION}' section")
            print(f"  FAIL  {name} — no '{SECTION}' section")
            continue

        block = s[s.index(SECTION):]
        problems = []
        # The issue and the PR do different jobs, and BOTH need a literal
        # marker. `"issue" in block` was near-vacuous: the block starts at the
        # heading, whose suffix reads "— the issue is durable, the PR is the
        # review", so the word was always present and an inverted instruction
        # under an intact heading passed. Found by QA on PR #609.
        if "**On the issue:**" not in block:
            problems.append("does not name the issue surface (needs `**On the issue:**`)")
        if "**On the PR:**" not in block:
            problems.append("does not name the PR surface (say 'nothing routinely' if so)")
        if LOCAL_ONLY not in block:
            problems.append("does not say AGENT_STATUS.md is local only")

        if problems:
            bad.append(f"{name}: " + "; ".join(problems))
            print(f"  FAIL  {name} — " + "; ".join(problems))
        else:
            print(f"  ok    {name}")

    # ---- CLAUDE.md ----
    print()
    try:
        c = CLAUDE.read_text()
    except OSError as exc:
        print(f"COULD NOT RUN (exit 2) — CLAUDE.md is unreadable ({exc})")
        return 2
    if "### The three surfaces" in c:
        print("  ok    CLAUDE.md names the three surfaces")
    else:
        bad.append("CLAUDE.md: no 'The three surfaces' section")
        print("  FAIL  CLAUDE.md — no 'The three surfaces' section")

    if "Nothing written there leaves this" in c:
        print("  ok    CLAUDE.md states AGENT_STATUS.md does not leave the machine")
    else:
        bad.append("CLAUDE.md: does not say AGENT_STATUS.md stays local")
        print("  FAIL  CLAUDE.md — does not say AGENT_STATUS.md stays local")

    print()
    if bad:
        print(f"FAIL — {len(bad)} definition(s) do not say where their output goes:")
        for b in bad:
            print(f"  - {b}")
        return 1
    print(f"PASS — all {len(files)} agent definitions name the issue and the PR, "
          "and CLAUDE.md names the three surfaces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
