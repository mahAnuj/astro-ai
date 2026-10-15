"""The sweep must pick only a PR every downstream step would also accept (#357).

WHY THIS IS HERE, given the charter in conftest.py.

Admitted on the same footing as test_agent_merge_trust_boundary.py: the control
lives in a jq filter inside a YAML string, nothing type-checks it, and both of
its failure modes are silent.

  * Too loose, and the sweep spends every run on an ineligible PR -- it picks
    the lowest number, so one unlabelled PR sitting below an eligible one
    starves the eligible one forever and the loop looks fixed while nothing
    merges.
  * Too loose in the other direction and it picks a PR a human is holding
    (`needs-human-review`, `too-large-to-automerge`), re-labels it, and the
    hold becomes a 30-minute comment loop.
  * Too strict, and it silently never fires, which looks exactly like "the bug
    never recurred".

So these tests run the real filter: they lift the jq out of the workflow's own
run block and drive it with synthetic `/pulls` payloads. They do not
reimplement it. The sweep's job is candidate SELECTION -- the authority to
merge stays with the `own`/`gates`/`qa`/`size`/`boundary` steps, which re-read
everything from the API -- so what is pinned here is exactly that the candidate
is worth those steps' time, and that a held PR is not one.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "agent-merge.yml")
REPO = "mahAnuj/astro-ai"


def _sweep_filter() -> str:
    """The jq program out of the `Find the pull request` step, verbatim."""
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]
    run = next(s for s in job["steps"] if s.get("id") == "pr")["run"]
    # The filter is the single-quoted argument to `--jq` on the sweep's gh call.
    m = re.search(r"pulls\?state=open[^\n]*--jq\s+'(.*?)'\)", run, re.S)
    assert m, "the sweep's gh api --jq call is no longer recognisable in the `pr` step"
    return m.group(1)


FILTER = _sweep_filter()


def _pick(pulls: list[dict]) -> str:
    """Run the workflow's own filter over a /pulls payload. '' = no candidate."""
    shell = (
        'printf %s "$PULLS" | jq --raw-output \''
        + FILTER.replace("'\"$GH_REPO\"'", REPO)
        + "'"
    )
    p = subprocess.run(["bash", "-c", shell], capture_output=True, text=True,
                       env={"PULLS": json.dumps(pulls), "PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def pr(number: int, *, labels=("qa-pass",), branch=None, draft=False, repo=REPO) -> dict:
    return {
        "number": number,
        "draft": draft,
        "head": {"ref": branch or f"issue/{number}-x", "repo": {"full_name": repo}},
        "labels": [{"name": n} for n in labels],
    }


# --- 1. the eligible case ---------------------------------------------------

def test_an_eligible_pr_is_picked():
    assert _pick([pr(356)]) == "356"


def test_the_lowest_number_is_picked_so_the_queue_drains_in_order():
    assert _pick([pr(360), pr(352), pr(356)]) == "352"


def test_no_open_prs_yields_no_candidate():
    # The live state on 2026-10-15 after #356 was merged by hand. The step
    # treats an empty value as "nothing to merge" and exits 0.
    assert _pick([]) == ""


# --- 2. qa-pass is required ------------------------------------------------

def test_a_pr_without_qa_pass_is_not_a_candidate():
    assert _pick([pr(356, labels=())]) == ""


def test_an_unlabelled_lower_pr_does_not_starve_an_eligible_higher_one():
    # The starvation case. `sort | first` over ALL open PRs would pick 300 and
    # the sweep would stop at the `qa` step every 30 minutes forever.
    assert _pick([pr(300, labels=()), pr(356)]) == "356"


# --- 3. the three human-hold labels ----------------------------------------

@pytest.mark.parametrize("hold", ["qa-fail", "needs-human-review", "too-large-to-automerge"])
def test_a_pr_a_human_is_holding_is_not_a_candidate(hold):
    assert _pick([pr(356, labels=("qa-pass", hold))]) == ""


def test_a_held_pr_does_not_block_the_next_eligible_one():
    assert _pick([pr(352, labels=("qa-pass", "needs-human-review")), pr(356)]) == "356"


# --- 4. the things the job `if:` also refuses -------------------------------

def test_a_fork_head_is_never_a_candidate():
    # Belt and braces with the job-level fork guard (#358): a fork PR must not
    # reach a job holding contents+actions write by any path, including this one.
    assert _pick([pr(356, repo="someone/astro-ai")]) == ""


def test_a_human_branch_is_never_a_candidate():
    assert _pick([pr(356, branch="chore/hand-edit")]) == ""
    assert _pick([pr(356, branch="main")]) == ""


def test_a_draft_is_never_a_candidate():
    # The `Take it out of draft` step exists for the edge-triggered path, where
    # gates and qa-pass are already known good. The sweep has no such context,
    # so it does not ready anything.
    assert _pick([pr(356, draft=True)]) == ""


# --- the filter's own shape -------------------------------------------------

def test_the_sweep_only_supplies_a_number_and_decides_nothing_else():
    # If the filter ever returned an object, or the step consumed anything but
    # a number, the sweep would start carrying state the later steps should be
    # re-reading. `.number` is the whole contract.
    assert ".number" in FILTER
    out = _pick([pr(356)])
    assert out.isdigit()


def test_the_schedule_leg_cannot_be_reached_without_the_sweep_filter():
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]
    run = next(s for s in job["steps"] if s.get("id") == "pr")["run"]
    assert '"$EVENT_NAME" = "schedule"' in run
    assert '"$EVENT_NAME" = "workflow_dispatch"' in run
    # And the already-handled guard, which is what keeps a sweep racing an edge
    # from reaching `gh pr merge` on a merged PR.
    assert '"$state" != "OPEN"' in run
