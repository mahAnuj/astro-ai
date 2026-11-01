"""`chief` defaults to letting work proceed, and knows the system before it rules.

WHY THIS IS A TEST, given the charter in conftest.py.

`.claude/agents/chief.md` is a prompt, so nothing type-checks it and its failure
mode is not an exception — it is a ruling that reads plausibly and costs a turn.
Two of those have now been paid for:

  * MEASURED 2026-11-01, PR #649. chief was escalated 0.0h after the `qa-fail`
    was written, restated what the steward had posted two minutes earlier, and
    produced no act. The branch did not move and an invocation was spent.
  * MEASURED 2026-11-01, PR #642. Two rulings the same day reached the same
    conclusion, the second re-deriving the first, because chief starts every
    escalation with no memory of its own prior rulings.

A PROMPT THAT CONTRADICTS ITSELF IS THE REAL HAZARD HERE, and this repo has
shipped one: an earlier `chief.md` draft said chief MAY merge a workflows PR on
line 117 and that such a PR is "not yours and never will be" on line 130. A
reader resolves a contradiction by picking, so a contradicted rule is no rule.
The new `proceed, no objection` disposition is exactly the shape that creates
one, because two other sections enumerate the allowed outcomes and a third
forbids "a third option". Those three places are asserted to agree below.

NOT TESTED HERE, and worth saying: whether the rules produce better rulings.
That is only observable in the rulings themselves. These tests pin that the
rules are present, consistent, and point at commands that exist.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHIEF = ROOT / ".claude" / "agents" / "chief.md"
SRC = CHIEF.read_text(encoding="utf-8")


def _sections() -> dict[str, str]:
    out, name = {}, None
    for line in SRC.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            out[name] = ""
        elif name is not None:
            out[name] += line + "\n"
    return out


SECTIONS = _sections()


# --- 1. the default, and that nothing in the file forbids it ----------------

def test_the_default_disposition_is_to_proceed():
    assert any(h.startswith("Your default is PROCEED") for h in SECTIONS), sorted(SECTIONS)
    body = next(v for k, v in SECTIONS.items() if k.startswith("Your default is PROCEED"))
    flat = " ".join(body.split())          # the sentence wraps in the source
    assert "`proceed, no objection` is a complete ruling" in flat


def test_the_three_places_that_enumerate_outcomes_all_allow_proceeding():
    """THE CONTRADICTION GUARD, and the reason this file has one.

    `How you decide`, `What you hand back` and `Non-negotiables` each constrain
    the output. A `proceed` default added to one and not the others is a rule a
    reader resolves by picking — which is how the 2026-10 draft shipped line 117
    permitting what line 130 forbade.
    """
    decide = SECTIONS["How you decide"]
    assert "proceed, no objection" in decide, "the decision procedure does not offer it"

    nonneg = SECTIONS["Non-negotiables"]
    assert "Never a third option." not in nonneg, (
        "the non-negotiable still forbids a third option without exempting "
        "`proceed`, which is declining to intervene rather than an option"
    )
    assert "proceed" in nonneg.lower(), "the non-negotiables do not mention proceeding"

    hand_back = SECTIONS["What you hand back"]
    assert "`proceed` ruling is SHORTER" in hand_back, (
        "a proceed ruling still has to satisfy the six-bullet shape, which "
        "reproduces the cost the default exists to remove"
    )


def test_proceeding_is_distinguished_from_inventing_an_option():
    """The distinction is load-bearing: inventing an option decides what gets
    built (architect's job), proceeding decides nothing at all."""
    assert "not a third OPTION" in SRC
    assert re.search(r"declining to intervene", SRC)


def test_the_ladder_is_ordered_and_ends_in_proceed():
    body = next(v for k, v in SECTIONS.items() if k.startswith("Your default is PROCEED"))
    for rung in ("weakens or removes a guard", "TRUST_BOUNDARY", "reverses a decision",
                 "irreversible", "Otherwise: proceed"):
        assert rung in body, rung
    assert body.index("weakens or removes a guard") < body.index("Otherwise: proceed")


def test_importance_alone_is_not_a_reason_to_intervene():
    """Stated because it is the natural drift: "this PR matters, so I should
    look harder" turns a brake into a checkpoint."""
    assert "Importance is not a reason to intervene" in SRC


# --- 2. it reads the diff ---------------------------------------------------

def test_it_is_told_to_read_the_pr_diff_before_ruling():
    assert any(h.startswith("Read the diff") for h in SECTIONS), sorted(SECTIONS)
    body = next(v for k, v in SECTIONS.items() if k.startswith("Read the diff"))
    flat = " ".join(body.split())
    # The DIRECTIVE, not merely the string `gh pr diff` -- which also appears in
    # the look-for table below it, so asserting the string alone let the mutant
    # "the labels and check conclusions are enough" survive this test and be
    # caught elsewhere. Reported by the harness as a MIS-POINTED row.
    assert "read `gh pr diff <n>` before deciding" in flat, (
        "the imperative to read the diff is gone; a ruling built from labels is "
        "a ruling about bookkeeping and the ladder cannot be applied to it"
    )
    assert "labels and check conclusions are enough" not in flat
    assert "name the files" in flat, (
        "a ruling that does not say what it read cannot be checked"
    )


# --- 3. memory, and that it is READ-ONLY ------------------------------------

def test_it_is_told_where_its_memory_lives():
    body = SECTIONS["Your memory, and how to load it"]
    for place in ("chief ruling", "ARCHITECTURE.md", "agents.json", "detect_stalls.py"):
        assert place in body, place


def test_it_reads_the_measurement_and_never_regenerates_it():
    """`collect_agent_performance.py` WRITES measurements/agents.json. chief is
    a read-only judge, and a ruling that left a modified measurement in the tree
    would silently change a number other roles are scored on — the cycle around
    it may commit whatever is dirty."""
    body = SECTIONS["Your memory, and how to load it"]
    assert "READ `agents.json`, do not run its collector" in body
    assert "uv run python scripts/collect_agent_performance.py" not in body, (
        "chief is instructed to run a collector that writes into the repo tree"
    )
    assert "collect_" not in body.split("Same rule for every")[0].replace(
        "collect_agent_performance.py` WRITES", ""), "a collector is still invoked"


def test_a_red_main_is_reported_but_does_not_stop_the_ruling():
    """This started as "a red `main` outranks everything in front of you" and
    that was a HALTING HAZARD, which is the thing this whole PR exists to
    remove: chief cannot push, so it cannot fix a red `main`, and a rule
    redirecting it there would stop it ruling on what it was actually woken
    for. Report it, then rule anyway."""
    flat = " ".join(SRC.split())
    assert "say so in one line and then rule anyway" in flat
    assert "A red `main` outranks everything in front of you" not in flat, (
        "the halting form of this rule is back"
    )
    assert "you cannot push, so you cannot fix it" in flat


def test_it_does_not_rule_twice_on_the_same_head():
    """MEASURED 2026-11-01 on PR #642: chief ruled THREE times on the unchanged
    SHA `668f35bd` — "second look", "third look" — same conclusion each time.
    `qa-on-green` has had a per-head guard from the start and calls it "the
    reason this workflow is safe to run on every green"; chief had none."""
    assert any(h.startswith("One ruling per head") for h in
               [ln[4:].strip() for ln in SRC.splitlines() if ln.startswith("### ")]), \
        "the per-head guard section is missing"
    flat = " ".join(SRC.split())
    assert "do not rule again. Say nothing." in flat
    assert "Same head, same conclusion → write nothing" in flat
    assert "New head → rule freely" in flat, (
        "without this the guard would silence a legitimate fresh reading"
    )
    assert "A comment is not an act" in flat


# --- 4. every command it is told to run must exist --------------------------

#: Scripts `chief.md` cites that are NOT on this branch, each with its reason.
#: This is a SELF-CLEANING allowance: the assertion is equality, so landing the
#: missing file fails this test too and forces the entry to be deleted. A silent
#: `if m not in KNOWN` would rot into permanent cover for the next gap.
CITED_BUT_ABSENT = {
    # Four citations in the Shape C section rest on this gate, and it is still
    # on unmerged PR #636. So the trust-boundary clearance chief was granted
    # currently has NO gate behind its safety argument -- recorded here rather
    # than discovered again later. Delete this entry when #636 merges.
    "verify_workflow_permissions.py",
}


def test_every_script_chief_is_told_to_run_exists():
    """A prompt naming a script that does not exist teaches the agent to
    improvise, and improvising is the one thing this role may not do."""
    missing = {m for m in re.findall(r"scripts/([a-z_]+\.py)", SRC)
               if not (ROOT / "scripts" / m).exists()}
    assert missing == CITED_BUT_ABSENT, (
        f"chief.md's missing-script set changed.\n"
        f"  newly missing : {sorted(missing - CITED_BUT_ABSENT)}\n"
        f"  now present   : {sorted(CITED_BUT_ABSENT - missing)}  <- delete from "
        f"CITED_BUT_ABSENT, with its reason"
    )


def test_every_measurement_file_chief_is_told_to_read_exists():
    missing = [m for m in set(re.findall(r"measurements/([a-z_]+\.json)", SRC))
               if not (ROOT / "measurements" / m).exists()]
    assert not missing, f"chief.md names measurements that do not exist: {missing}"


def test_the_roles_are_pointed_at_not_restated():
    """A 31-row table listing all fifteen roles and their comment markers was
    written and then REMOVED, deliberately.

    It restated what `.claude/agents/*.md` already defines, so a renamed agent
    or a reworded marker would have left chief grepping for something nobody
    writes — and it needed a test of its own to stay honest, which is the tell.
    This repo's own rule, stated in `CLAUDE.md` after #531/#534 removed six
    copies of one coupling: grep for every copy before believing a fix is done.
    A copy of fifteen definitions is fifteen things that rot.

    What replaced it is a pointer plus the one non-obvious fact — `dev-lead`'s
    comment names which agents ran.
    """
    body = SECTIONS["Your memory, and how to load it"]
    assert "they are not restated here" in " ".join(body.split())
    assert "dev-lead" in body, "the one genuinely non-obvious pointer is gone"
    assert "#607" in body, "the rule that makes the issue thread the record"
    rows = [ln for ln in body.splitlines()
            if ln.startswith("| `") and "agents/" not in ln]
    assert len(rows) == 0, (
        f"the role table is back ({len(rows)} rows); point at the definitions "
        "instead of copying them"
    )


def test_the_objective_is_turnaround_not_caution():
    body = next(v for k, v in SECTIONS.items() if k.startswith("What you are optimising for"))
    assert "Turnaround" in body
    assert "caution is not the objective" in body


def test_the_file_still_parses_as_one_frontmatter_plus_body():
    assert SRC.startswith("---\n")
    assert SRC.count("\n---\n") >= 1
    head = SRC.split("\n---\n", 1)[0]
    assert "name: chief" in head and "tools:" in head


def test_chief_has_no_write_tool_so_the_read_only_rule_is_enforceable():
    """The read-only instruction above is a rule, and this is the mechanism
    behind it: chief's tool list grants no Write or Edit. If that ever changes,
    the instruction stops being structural and becomes a request."""
    head = SRC.split("\n---\n", 1)[0]
    tools = next(ln for ln in head.splitlines() if ln.startswith("tools:"))
    for forbidden in ("Write", "Edit", "NotebookEdit"):
        assert forbidden not in tools, f"chief now has {forbidden}: {tools}"
