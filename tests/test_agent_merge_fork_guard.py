"""`agent-merge` must not read a fork's head, and must not put a PR value in shell.

WHY THIS IS A TEST AND NOT ONLY A GATE
--------------------------------------
`scripts/verify_workflows.py` check 5 enforces "no `${{ }}` in a `run:` block of
a privileged workflow" across the tree. That is the rule. This file pins the two
things specific to `agent-merge.yml` that the rule does not state:

  1. the job refuses a head repository that is not this repository, on BOTH
     trigger legs -- the guard that makes the write token unreachable from a
     fork at all (#358);
  2. every `$PR_*` / `$EVENT_*` / `$RUN_*` name a `run:` block expands is
     actually DECLARED, in that step's `env:` or the job's.

(2) is the failure mode of the fix itself. Moving a value behind `env:` and
forgetting to declare it in one of the eight steps that use it does not error --
bash expands an undeclared name to the empty string. `case "" in issue/*)` falls
through to the "not an agent branch" arm and the loop silently stops merging;
`gh pr view ""` fails noisily, but `gh issue comment ""` in the post-merge step
runs after the merge has already happened. So the refactor needs a test that
reads the declarations, not just one that reads the shell.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "agent-merge.yml"
TEXT = WF.read_text(encoding="utf-8")
DOC = yaml.safe_load(TEXT)
JOB = DOC["jobs"]["merge"]
COND = " ".join(JOB["if"].split())

# The names #358 introduced, plus the two that were always job-level.
MANAGED = re.compile(r"\$(?:\{)?(PR_BRANCH|PR_NUMBER|PR_SHA|EVENT_NAME|EVENT_PR_NUMBER"
                     r"|RUN_HEAD_SHA|RUN_CONCLUSION|RUN_URL)\b")


def run_text(step: dict) -> str:
    return step.get("run") or ""


def test_both_trigger_legs_require_the_head_to_be_this_repository():
    # pull_request_target carries event.pull_request.head.repo; workflow_run
    # carries event.workflow_run.head_repository. Neither is readable from the
    # other, so one clause cannot cover both legs.
    assert "github.event.pull_request.head.repo.full_name == github.repository" in COND
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in COND


def test_neither_leg_can_fire_without_its_own_head_check():
    # The shape that matters: `A || B` where A and B each carry their own
    # equality. An `||` that reaches a bare trigger test would let a fork in.
    left, _, right = COND.partition("||")
    assert "pull_request_target" in left and "head.repo.full_name" in left, left
    assert "workflow_run" in right and "head_repository.full_name" in right, right


def test_the_agent_branch_filter_reads_an_env_var_not_an_interpolation():
    # The injection point in #358: the filter itself was
    # `case "${{ steps.pr.outputs.branch }}" in`, so the branch name was shell
    # source inside the step meant to reject it.
    own = next(s for s in JOB["steps"] if s.get("id") == "own")
    assert 'case "$PR_BRANCH" in' in run_text(own)
    assert "${{" not in run_text(own)


def test_no_step_interpolates_anything_into_its_run_block():
    offenders = [s.get("name", s.get("id", "?")) for s in JOB["steps"] if "${{" in run_text(s)]
    assert offenders == [], offenders


@pytest.mark.parametrize("step", JOB["steps"], ids=lambda s: s.get("id") or s.get("name", "?"))
def test_every_managed_variable_a_step_expands_is_declared(step):
    used = set(MANAGED.findall(run_text(step)))
    declared = set(JOB.get("env") or {}) | set(step.get("env") or {})
    assert used <= declared, (
        f"{step.get('name')} expands {sorted(used - declared)} but declares none of them; "
        "bash would expand an undeclared name to the empty string")


def test_the_branch_name_is_only_ever_expanded_inside_double_quotes():
    # An unquoted `$PR_BRANCH` would word-split on a name containing $IFS
    # characters. Git forbids a literal space in a ref, but not `${IFS}`, and a
    # value that has already been through one substitution is not re-split --
    # so this is belt and braces on top of the env: fix, cheap to assert.
    for step in JOB["steps"]:
        for line in run_text(step).splitlines():
            bare = re.findall(r'(?<!")\$PR_BRANCH(?!")', line)
            if not bare:
                continue
            assert line.count('"') >= 2, f"unquoted $PR_BRANCH: {line.strip()}"


def test_the_job_still_has_no_checkout():
    # Stated in the file's own comments and load-bearing: this job runs with a
    # write token, so nothing from the PR may execute in it.
    assert not any("checkout" in str(s.get("uses", "")) for s in JOB["steps"])
