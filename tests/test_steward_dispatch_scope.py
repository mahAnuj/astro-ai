"""The steward's dispatch rule must not refuse a PR for its branch name or its opener.

WHY THIS IS A TEST, given the charter in conftest.py.

The steward and `chief` decide whether a stall gets a cycle, and they decide it
from PROSE in their prompts. Nothing type-checks prose, and its failure mode is
the one this repo keeps paying for: the mechanism is right, the scope is wrong,
and every component reports success while the loop delivers nothing.

Measured 2026-10-25. #531 fixed the branch-name coupling in three places —
`agent-merge`'s eligibility gate, `agent-work`'s push net, and
`detect_stalls.py`'s issue derivation. Minutes after it merged, the detector
correctly named the owning issue for all three live stalls (#521 -> #518,
#524 -> #523, #530 -> #398) and the loop STILL could not dispatch, because two
more copies of the same rule live here as instructions:

    "write one only for a PR a cycle can actually adopt -- an `issue/*` branch
     with an owning issue, never a PR a human opened on their own branch"

Both clauses were wrong by then. `agent-cycle` Step 2.5 adopts an existing
branch and PR whoever opened it, `partial/` and `fix/` carry an issue number by
construction (Step 4), and the repository owner opens PRs on cycle branches
routinely -- #521 and #524 both were. So the fifth and sixth copies of one
coupling refused exactly the PRs the user had just asked the loop to drive.

WHAT THIS PINS, and what it deliberately does not. It cannot check that a model
OBEYS its prompt. It checks that the prompt still states the right rule: the
test is authorship plus an owning issue, and the two refusals that survive are
a diff touching `.github/workflows/**` (the App token has no `workflows`
permission) and a PR nobody trusted authored. A future edit that reintroduces
"an `issue/*` branch" or "a PR a human opened" fails here.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "agent-steward.yml"
AGENT = ROOT / ".claude" / "agents" / "steward.md"
CYCLE = ROOT / ".claude" / "commands" / "agent-cycle.md"

SOURCES = {
    "agent-steward.yml": WF.read_text(encoding="utf-8"),
    "steward.md": AGENT.read_text(encoding="utf-8"),
}


# --- 1. the two refused phrasings may not come back ---------------------------

@pytest.mark.parametrize("name", sorted(SOURCES))
def test_the_dispatch_rule_never_requires_an_issue_slash_branch(name):
    """`an \\`issue/*\\` branch with an owning issue` was the defect, verbatim.

    A dispatch needs an ISSUE to aim at, which the detector supplies for
    `issue/`, `partial/` and `fix/` alike. Requiring the `issue/` namespace
    discards two thirds of what a cycle produces -- and `partial/` is the
    namespace a cycle is TOLD to use whenever work remains.
    """
    src = SOURCES[name]
    bad = re.findall(r"`issue/\*`[^\n]*", src)
    assert not bad, f"{name} still gates a dispatch on the `issue/*` namespace: {bad}"


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_the_dispatch_rule_never_refuses_a_pr_for_who_opened_it(name):
    """Who OPENED the PR is not the question; who AUTHORED the work is.

    The repository owner opens PRs on cycle branches -- #521 and #524 were both
    `mahAnuj` on `partial/` branches carrying cycle commits. Under the old
    wording the steward read "a human opened it" and stood down, twice a day,
    for 21 hours, while `steward-ineffective` escalated to chief.
    """
    src = SOURCES[name]
    # Case-insensitive deliberately. Both real occurrences began a sentence
    # or a bullet -- "- A PR a human opened." -- so a case-sensitive pattern
    # would have matched the workflow's wording and missed steward.md's
    # entirely, which is the file the steward actually reads.
    bad = re.findall(r"a (?:PR|pull request) a human (?:opened|authored)[^\n]*",
                     src, re.IGNORECASE)
    assert not bad, f"{name} still refuses a dispatch by the PR's opener: {bad}"


# --- 2. the rule that must be there instead -----------------------------------

@pytest.mark.parametrize("name", sorted(SOURCES))
def test_the_dispatch_rule_states_the_authorship_test(name):
    """The replacement must name both halves: the owning issue AND the author.

    Deleting the bad clause without stating the good one would leave the
    steward with no eligibility rule at all, which is the opposite failure --
    it would dispatch at a contributor's PR, or at a `measurements/*` branch
    whose run id reads as issue 40140256532.
    """
    src = SOURCES[name]
    assert "claude[bot]" in src, f"{name} does not name the agent author"
    assert re.search(r"repository owner", src), f"{name} does not name the owner"

    # THE OWNING-ISSUE HALF WAS DELETED ON PURPOSE, 2026-11-01, and this test
    # used to assert it. It passed after the change ONLY because the phrase
    # "owning issue" survived inside a sentence saying the opposite -- "the
    # detector named no owning issue is NO LONGER a reason to stand down".
    # A substring that appears in its own negation is the `_code()` trap this
    # repo has now hit three times, so the assertion is replaced rather than
    # left to pass by accident.
    #
    # The eligibility rule is still two-part; the second part is just no longer
    # "an issue exists". It is "the dispatch names a target the carrier can
    # parse", which is `issue=<n>` or `pr=<n>`.
    assert re.search(r"`pr=<n(?:umber)?>`", src), (
        f"{name} offers no PR-scoped form, so a green PR whose branch carries "
        f"no number is unreachable -- the state that held four PRs on "
        f"2026-11-01")
    assert not re.search(r"needs an issue to aim at", src), (
        f"{name} still states the precondition that caused six no-op comments")


def test_chief_keeps_the_two_refusals_that_are_real():
    """`chief`'s rule must still refuse what a cycle genuinely cannot clear.

    A workflow-touching diff is unpushable by the App token (#442/#315), and an
    untrusted author's PR is not this loop's to drive. Widening the gate must
    not have widened it to everything.
    """
    src = SOURCES["agent-steward.yml"]
    # Whitespace-insensitive: this prose is wrapped to the YAML block's width,
    # so a reflow must not read as a deleted refusal. The first draft of this
    # assertion was literal and failed on exactly that.
    flat = " ".join(src.split())
    assert "`.github/workflows/**` (the App token has no `workflows` permission)" in flat
    assert re.search(r"authored by neither `claude\[bot\]` nor the repository owner", flat)


# --- 3. the adoption globs the dispatch relies on -----------------------------

def test_a_cycle_looks_for_every_namespace_the_steward_may_dispatch_at():
    """Step 2.5 must find the branch the steward dispatched about.

    The steward now dispatches for `issue/`, `partial/` and `fix/`. If the
    cycle's `git ls-remote` probe does not list a namespace, the cycle reports
    "no branch", starts a parallel one, and the stalled PR is never touched --
    a dispatch that costs ~50 Actions minutes and clears nothing.
    """
    src = CYCLE.read_text(encoding="utf-8")
    probes = re.findall(r"git ls-remote --heads origin[^\n]*", src)
    assert probes, "the branch-adoption probe is no longer recognisable in agent-cycle.md"
    for probe in probes:
        for ns in ("issue/<n>-*", "partial/<n>-*", "fix/<n>-*"):
            assert f'"{ns}"' in probe, f"{probe!r} does not look for {ns}"
