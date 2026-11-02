"""The steward dispatches what it can reach, and stays silent when it cannot.

WHY THIS IS A TEST, given the charter in conftest.py.

MEASURED 2026-11-01. Across four PRs the steward wrote SIX comments and **every
one of them said "no dispatch by me"**. All four PRs were in fact dispatchable.
Two of the three causes were sentences in this very file:

  * its ruling line was "exactly `issue=<n>`", and `dispatch_cycle.sh` had
    learned `pr=<n>` that morning (#650) while nothing told the steward;
  * a "what a stall is NOT" bullet read "A dispatch needs an issue to aim at",
    which is the sentence that produced "there is nothing legitimate to write";
  * and its quiet-run instruction said "say so and produce nothing", so a run
    with nothing to do still commented on every PR, every time.

The cost was not the comments. `detect_stalls` marks those kinds OBLIGED, so
`agent-steward.yml:306` demanded proof of an action, the steward had none to
take, `:322` read `cycles=0, issues=0`, and chief was woken -- which is issue
#580 from the other end. Three invocations per stuck PR per run, structurally,
with no possible outcome.

A PROMPT'S failure mode is a plausible comment rather than an exception, so
these are static assertions over the file. They pin that the two forms are
offered, that the stale sentence is gone, and that a quiet run is silent.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
STEWARD = ROOT / ".claude" / "agents" / "steward.md"
SRC = STEWARD.read_text(encoding="utf-8")
FLAT = " ".join(SRC.split())


def test_the_steward_can_dispatch_a_pr_scoped_round():
    """THE FIX. `pr=<n>` aims a QA round at the PR itself and needs no owning
    issue, which is the state that held four green PRs."""
    assert "`issue=<n>` **or** `pr=<n>`" in FLAT, (
        "the ruling line offers only one form; a PR with no owning issue is "
        "then unreachable and the steward can only comment about it"
    )
    assert "pr=<n>" in SRC


def test_the_two_forms_are_distinguished_not_interchangeable():
    """`issue=` runs a full cycle that can build; `pr=` runs a QA round. A
    steward that treated them as the same thing would aim a round at an issue
    with no PR, or a build cycle at a PR."""
    assert "aims a **QA round** at the PR itself" in FLAT
    assert "richer dispatch" in FLAT


def test_the_sentence_that_caused_the_six_no_op_comments_is_gone():
    assert "A dispatch needs an issue to aim at" not in FLAT, (
        "the stale precondition is back; this is the sentence that produced "
        "\"there is nothing legitimate to write\" six times in one day"
    )


def test_a_measurements_branch_is_still_not_a_stall():
    """The bullet was narrowed, not deleted. `measurements/*` carries no owning
    issue BY CONSTRUCTION and nothing about it is delivery work -- and the
    widened branch regex that would catch it reads run id 40140256532 as an
    issue number ~8 times a day."""
    assert "`measurements/*` branch" in SRC


def test_who_opened_the_pr_is_still_never_the_test():
    """#531 removed six copies of this coupling and the rule has to survive the
    bullet being rewritten around it: the owner opens PRs on cycle branches."""
    assert "Who OPENED the PR is not the test" in SRC
    assert "#531" in SRC


def test_a_quiet_steward_run_writes_no_pr_comment():
    """"say so and produce nothing" produced a comment per PR per run. A quiet
    run belongs in the run summary, where a human looking for it will find it,
    not on four pull requests."""
    assert "produce nothing — including no PR" in SRC, (
        "a quiet run may still comment on every PR"
    )
    assert "in\nthe run summary" in SRC or "in the run summary" in FLAT


def test_it_does_not_comment_twice_on_the_same_head():
    """MEASURED: no per-head guard existed on either model-invoking agent, while
    `qa-on-green` has had one from the start and calls it "the reason this
    workflow is safe to run on every green"."""
    assert "ONE COMMENT PER HEAD" in SRC
    assert "write nothing" in FLAT
    assert "A new commit is new information and earns a fresh reading" in FLAT, (
        "without this the guard would also silence a legitimate fresh reading"
    )


def test_the_guard_names_a_command_that_reads_the_head():
    """A guard the agent cannot evaluate is advice. It needs the head and its
    own prior comments in one call."""
    block = SRC[SRC.index("ONE COMMENT PER HEAD"):]
    assert "headRefOid" in block
    assert 'startswith("**steward")' in block


def test_it_still_may_not_run_gh_workflow_run_itself():
    """#442: inside this loop the steward's `gh` is the App token and the
    Actions API answers 403. The ruling FILE is the only dispatch path, and
    adding `pr=` must not have reopened the direct one."""
    assert "Do NOT run `gh workflow run` yourself" in SRC
    assert "#442" in SRC


def test_every_ruling_form_the_steward_offers_is_one_the_carrier_parses():
    """THE CONTRACT, asserted across the two files rather than trusted. The
    carrier parses `^(issue|pr)=[0-9]+$` and refuses anything else, so a third
    form invented here would be written, refused, and reported as a dispatch."""
    carrier = (ROOT / "scripts" / "dispatch_cycle.sh").read_text(encoding="utf-8")
    m = re.search(r"grep -oE '\^\(([a-z|]+)\)=\[0-9\]\+\$'", carrier)
    assert m, "the carrier's ruling pattern is no longer recognisable"
    accepted = set(m.group(1).split("|"))
    offered = set(re.findall(r"`([a-z]+)=<n>`", SRC))
    assert offered <= accepted, (
        f"steward.md offers {sorted(offered - accepted)}, which "
        f"dispatch_cycle.sh does not parse (it accepts {sorted(accepted)})"
    )
    assert offered == accepted, (
        f"the carrier accepts {sorted(accepted - offered)} but the steward is "
        "never told it may use them"
    )
