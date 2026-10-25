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
import subprocess
import tempfile
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


def test_the_eligibility_filter_reads_env_vars_not_interpolations():
    # The injection point in #358: the filter itself was
    # `case "${{ steps.pr.outputs.branch }}" in`, so the branch name was shell
    # source inside the step meant to reject it.
    #
    # Since 2026-10-25 the step tests the AUTHOR rather than the branch name,
    # and the author is attacker-chosen in exactly the same sense -- a fork PR
    # carries whatever login opened it -- so it arrives the same way, by env.
    own = next(s for s in JOB["steps"] if s.get("id") == "own")
    assert 'case ",$AGENT_AUTHORS," in' in run_text(own)
    assert '*",$PR_AUTHOR,"*' in run_text(own)
    assert "${{" not in run_text(own)


def test_the_eligibility_gate_executes_correctly_for_every_author():
    """Run the `own` step's real shell, rather than reading its text.

    `claude[bot]` contains `[` and `]`, which are glob metacharacters, and the
    author is expanded into a `case` PATTERN -- the one position in shell where
    a variable's contents become matching syntax. Quoting the expansion
    (`*",$PR_AUTHOR,"*`) is what makes it literal, and nothing about the source
    says so: both forms parse, and the unquoted one reads `[bot]` as a
    character class.

    The unquoted form happens to fail CLOSED here (it matches nothing, so the
    loop merges nothing), which is the benign direction but still a silent
    outage of the kind this repo has shipped before -- #469 was the last
    autonomous merge and nobody noticed for four days. So this executes it.
    """
    own = next(st for st in JOB["steps"] if st.get("id") == "own")
    body = own["run"]
    authors = JOB["env"]["AGENT_AUTHORS"].replace(
        "${{ github.repository_owner }}", "mahAnuj")

    def eligible(author: str) -> bool:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            p = subprocess.run(
                ["bash", "-c", body],
                capture_output=True, text=True,
                env={"AGENT_AUTHORS": authors, "PR_AUTHOR": author,
                     "PR_BRANCH": "partial/523-x", "GITHUB_OUTPUT": str(out),
                     "PATH": "/usr/bin:/bin"},
            )
            assert p.returncode == 0, p.stderr
            return "ok=true" in (out.read_text() if out.exists() else "")

    # In the list.
    assert eligible("claude[bot]")
    assert eligible("mahAnuj")

    # The glob reading of `[bot]`, which must NOT be how this matches.
    for ch in ("claudeb", "claudeo", "claudet", "b", "o", "t"):
        assert not eligible(ch), ch

    # Substring and case near-misses.
    for impostor in ("claude[bot]-x", "xclaude[bot]", "claude", "Claude[bot]",
                     "notmahAnuj", "mahAnuj-evil", "", "shubhagya-publisher[bot]"):
        assert not eligible(impostor), impostor


def test_the_author_is_matched_exactly_and_not_by_substring():
    # `claude[bot]` contains `[`, a glob metacharacter in a shell `case`. The
    # membership test must therefore be the comma-delimited form -- a bare
    # `*"$PR_AUTHOR"*` would admit `claude[bot]-x`, and an unanchored `case
    # "$PR_AUTHOR" in claude[bot])` would read the brackets as a character
    # class and match the single characters b, o and t.
    own = run_text(next(s for s in JOB["steps"] if s.get("id") == "own"))
    assert '*"$PR_AUTHOR"*' not in own, "substring match on the author"
    for literal in ("claude[bot])", "mahAnuj)"):
        assert literal not in own, (
            f"{literal} as a `case` pattern reads `[bot]` as a glob character "
            "class; the author list belongs in AGENT_AUTHORS, matched by "
            "comma-delimited membership"
        )


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
