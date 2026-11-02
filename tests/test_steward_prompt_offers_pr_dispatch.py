"""The steward's OWN prompt must offer `pr=<number>`, not only `steward.md`.

WHY THIS IS A TEST, given the charter in conftest.py.

`tests/test_steward_acts_instead_of_commenting.py` already pins that
`.claude/agents/steward.md` offers both dispatch forms. It passed the whole
time. It asserts on the wrong file.

MEASURED 2026-11-02T04:50Z. The steward's scheduled run read PR #654, derived
`qa-fail-refixed` correctly, verified the head, confirmed the PR was MERGEABLE,
named `pr=654` in prose as the repair -- and then wrote **"I hold no `pr=`
carrier"** and dispatched nothing. It was wrong about itself, and it was wrong
because of the prompt it was handed: `agent-steward.yml` told it to write
"exactly `issue=<number>`" and to do so only for "a PR the DETECTOR named an
owning issue for". Chief's prompt 210 lines below IN THE SAME FILE already
carried `issue=<number>` OR `pr=<number>`, and `steward.md:104` carried it too.
#659 taught those two and missed this one.

So the three copies disagreed, and the one that governed behaviour was the one
no test read. PRs #649 and #654 sat overnight with green gates and a correct
diagnosis attached, waiting for a dispatch the steward was able to make.

The inline prompt and the agent file are two sources for one fact, which is
#628's lesson. These tests read the YAML, select the steward's prompt by the
file it writes (`/tmp/steward-dispatch.txt`, which is what makes it the
steward's), and pin that it offers both forms and does not re-impose an owning
issue as a precondition for dispatching at all.
"""
from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-steward.yml"
JOBS = yaml.safe_load(WF.read_text(encoding="utf-8"))["jobs"]


def _prompt(dispatch_file: str) -> str:
    """The prompt of the agent that writes `dispatch_file`.

    Selected by the file it is told to write rather than by position or step
    name: both prompt steps in this workflow are unnamed, and position is
    exactly the kind of coupling that makes a test pass while reading the
    wrong block.
    """
    found = [
        s["with"]["prompt"]
        for jd in JOBS.values()
        for s in jd["steps"]
        if "prompt" in (s.get("with") or {}) and dispatch_file in s["with"]["prompt"]
    ]
    assert len(found) == 1, (
        f"expected exactly one prompt writing {dispatch_file}, found {len(found)}"
    )
    return found[0]


STEWARD = _prompt("/tmp/steward-dispatch.txt")
CHIEF = _prompt("/tmp/chief-dispatch.txt")
S_FLAT = " ".join(STEWARD.split())
C_FLAT = " ".join(CHIEF.split())


def test_the_steward_prompt_offers_the_pr_form():
    """THE FIX, and the thing the 04:50Z run got wrong about itself."""
    assert "`pr=<number>`" in S_FLAT, (
        "the steward's own prompt does not mention `pr=<number>`, so the "
        "steward will report that it holds no `pr=` carrier -- which it did, "
        "on PR #654, while naming `pr=654` as the repair in the same comment"
    )


def test_the_steward_prompt_does_not_say_exactly_issue_only():
    """The literal sentence that produced the refusal."""
    assert "exactly `issue=<number>`," not in S_FLAT, (
        "the prompt still narrows the ruling line to `issue=<number>` alone"
    )


def test_an_owning_issue_is_not_a_precondition_for_dispatching():
    """The second half of the same defect.

    Even a prompt that mentions `pr=` would still strand #654 if it also said
    to dispatch only for a PR the detector named an owning issue for: #654's
    detector line names none. `pr=` exists precisely for that case.
    """
    assert "DETECTOR named an owning" not in S_FLAT, (
        "the prompt still requires an owning issue before any dispatch; that "
        "is a precondition for `issue=` only, and re-imposing it on `pr=` "
        "re-creates the stall it was built to clear"
    )
    assert "an owning issue is NOT a precondition" in S_FLAT, (
        "the prompt must say so outright; the steward read the old wording as "
        "governing even though steward.md disagreed"
    )


def test_the_steward_and_chief_prompts_agree_on_the_forms():
    """One fact, two prompts. #628 is this repo's name for that going wrong.

    Chief's half was already right, which is why the disagreement was invisible:
    a reader of this file who stopped at chief's block would conclude the loop
    had the capability.
    """
    for form in ("`issue=<number>`", "`pr=<number>`"):
        assert form in C_FLAT, f"chief's prompt lost {form}"
        assert form in S_FLAT, f"the steward's prompt lacks {form}"


def test_the_prompt_still_forbids_the_steward_running_gh_workflow_run():
    """Not relaxed by the fix. The steward's token is refused HTTP 403 (#442);
    the ruling file plus a later `run:` step is the whole mechanism."""
    assert "DO NOT RUN `gh workflow run`" in S_FLAT
    assert "/tmp/steward-dispatch.txt" in S_FLAT


def test_a_dispatch_is_still_never_written_to_be_safe():
    """Also not relaxed. A wasted cycle is ~50 Actions minutes, and widening
    the FORM must not widen the THRESHOLD."""
    assert 'Never write one "to be safe"' in S_FLAT
    # Deliberately the substring common to the wording before and after the
    # fix. A pin that only matches the NEW phrasing is not a non-relaxation
    # test -- it fails on the unfixed file and so proves nothing about what
    # the fix preserved.
    assert "means no dispatch" in S_FLAT
