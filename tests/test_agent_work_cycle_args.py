"""`agent-work` composes `/agent-cycle`'s argument in a step a test can run.

WHY THIS IS A TEST, given the charter in conftest.py.

The prompt line was `/agent-cycle ${{ github.event.inputs.issue }}`. Adding a
second, mutually exclusive input the obvious way means an expression like

    ${{ inputs.pr != '' && format('--qa-pr {0}', inputs.pr) || inputs.issue }}

which is GitHub-expression truthiness over an input that is `null` on a
`schedule` fire and `''` on a dispatch. Getting it wrong does not fail: the leg
goes SILENTLY INERT. That is #421's class and this repo has shipped it three
times -- `agent-steward.yml`'s `workflow_run` leg named a workflow by its
filename and could never fire, and nothing noticed because nothing failed.

An expression is also not executable. So the composition lives in a `run:`
step, and this file runs that step's real text against the four input
combinations rather than reading it.

WHAT IT IS FOR, measured 2026-11-01. Four of the five green PRs then open had
received ZERO QA dispatches because their branch names carried no issue number,
and `agent-merge` merges only on `qa-pass` whose only writer is a dispatched
round. `qa-on-green.yml` now falls back to `pr=<num>`, and this is the step that
turns that into `/agent-cycle --qa-pr <num>`.

THE ONE THING THAT MUST NOT BREAK is the cron. Six scheduled fires a day arrive
with no `inputs` object at all, so both expressions render empty; under
`set -u` a bare `$ISSUE` would abort every one of them. That case is
`test_a_scheduled_fire_with_no_inputs_at_all_composes_an_empty_argument`, and
it is the regression guard for this whole change.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WF = (Path(__file__).resolve().parent.parent
      / ".github" / "workflows" / "agent-work.yml")
SRC = WF.read_text(encoding="utf-8")
DOC = yaml.safe_load(SRC)
ON = DOC.get("on") or DOC.get(True)          # `on:` is YAML 1.1 true
STEPS = DOC["jobs"]["cycle"]["steps"]


def _step(name: str) -> dict:
    for s in STEPS:
        if s.get("name") == name:
            return s
    raise AssertionError(f"no step named {name!r}; the workflow was restructured")


COMPOSE = _step("Compose the cycle arguments")


def _compose(tmp_path: Path, issue=None, pr=None) -> tuple[int, str, str]:
    """Run the REAL step. `None` means the variable is not set at all, which is
    what a `schedule` fire produces once the empty expression is substituted."""
    out = tmp_path / "out"
    summary = tmp_path / "summary"
    out.write_text("")
    summary.write_text("")
    env = {"PATH": "/usr/bin:/bin",
           "GITHUB_OUTPUT": str(out),
           "GITHUB_STEP_SUMMARY": str(summary)}
    if issue is not None:
        env["ISSUE"] = issue
    if pr is not None:
        env["PR"] = pr
    p = subprocess.run(["bash", "-c", COMPOSE["run"]],
                       capture_output=True, text=True, env=env)
    args = ""
    for line in out.read_text().splitlines():
        if line.startswith("args="):
            args = line[len("args="):]
    return p.returncode, args, p.stdout + p.stderr


# --- 1. the four combinations, executed -------------------------------------

def test_a_scheduled_fire_with_no_inputs_at_all_composes_an_empty_argument(tmp_path):
    """THE REGRESSION GUARD. Six crons a day take this path. An empty argument
    is meaningful: it tells `/agent-cycle` to let project-manager rank and
    pick. Under `set -u` a bare `$ISSUE` would abort the run instead."""
    rc, args, log = _compose(tmp_path)
    assert rc == 0, log
    assert args == "", f"a cron fire must compose no argument, got {args!r}"


def test_an_empty_dispatch_composes_an_empty_argument(tmp_path):
    """`workflow_dispatch` with both boxes blank renders `''`, not absent."""
    rc, args, log = _compose(tmp_path, issue="", pr="")
    assert rc == 0, log
    assert args == ""


def test_an_issue_dispatch_is_unchanged(tmp_path):
    """The behaviour that existed before this step did. It is the common case
    and the steward's and chief's dispatches all take it."""
    rc, args, log = _compose(tmp_path, issue="536", pr="")
    assert rc == 0, log
    assert args == "536"


def test_a_pr_dispatch_becomes_a_qa_round(tmp_path):
    """THE NEW PATH. `--qa-pr` is `/agent-cycle` Step 0c, which skips Step 0a
    -- an ISSUE provenance check, and the thing that killed both dispatched
    rounds on #642 on 2026-11-01 (`OUTSIDER -- author is a bot`, because the
    loop had filed #616 itself; 40 of the 130 open issues that morning were
    bot-authored)."""
    rc, args, log = _compose(tmp_path, issue="", pr="639")
    assert rc == 0, log
    assert args == "--qa-pr 639"


# --- 2. it refuses rather than choosing -------------------------------------

def test_both_inputs_at_once_is_refused_not_resolved(tmp_path):
    """A dispatcher that sends both has a bug. Picking one hides it behind a
    ~50-minute run that reads as a success, which is the worst of the three
    available outcomes."""
    rc, args, log = _compose(tmp_path, issue="536", pr="639")
    assert rc != 0, f"both inputs were accepted and composed {args!r}"
    assert "BOTH" in log or "both" in log


@pytest.mark.parametrize("bad", ["abc", "63 9", "639;rm -rf /", "-1", "639x",
                                 "$(id)", "#639"])
def test_a_non_numeric_input_is_refused(tmp_path, bad):
    """These reach the agent's PROMPT rather than a shell, so the realistic
    damage is a cycle aimed at nonsense -- still refused, because a cycle aimed
    at nonsense spends the budget and reports success."""
    rc_i, _, _ = _compose(tmp_path, issue=bad, pr="")
    rc_p, _, _ = _compose(tmp_path, issue="", pr=bad)
    assert rc_i != 0, f"issue={bad!r} was accepted"
    assert rc_p != 0, f"pr={bad!r} was accepted"


# --- 3. the wiring to the prompt --------------------------------------------

def test_the_prompt_reads_the_composed_output_and_not_the_raw_input():
    """If the prompt still read `github.event.inputs.issue` the step above
    would be dead code, and a `pr=` dispatch would run an ordinary cycle with
    no argument -- ranking the backlog instead of judging the PR."""
    action = next(s for s in STEPS
                  if str(s.get("uses", "")).startswith("anthropics/claude-code-action"))
    prompt = action["with"]["prompt"]
    assert "steps.args.outputs.args" in prompt, prompt
    assert "github.event.inputs.issue" not in prompt, (
        "the prompt still reads the raw input; the composing step is bypassed"
    )


def test_the_slash_command_is_first_on_its_prompt_line():
    """`verify_workflows.py` only recognises a slash command at the start of a
    prompt line, and that recognition is what makes it check the command's
    tools against what `claude_args` grants."""
    action = next(s for s in STEPS
                  if str(s.get("uses", "")).startswith("anthropics/claude-code-action"))
    found = re.findall(r"(?m)^[ \t]*/([a-z][a-z0-9-]*)(?=[ \t]|$)",
                       action["with"]["prompt"])
    assert "agent-cycle" in found, found


def test_both_inputs_are_declared_so_a_dispatch_can_name_either():
    inputs = ON["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"issue", "pr"}, sorted(inputs)
    for name in ("issue", "pr"):
        assert inputs[name].get("required") is False, (
            f"`{name}` must stay optional; a required input breaks the cron"
        )


def test_the_composing_step_takes_its_values_as_env_vars():
    """A `${{ }}` inside a `run:` block is a script-injection sink and
    `verify_workflows.py` fails the build on one. Stated here too, because this
    step is the first in this file to read a dispatch input in shell."""
    assert "${{" not in COMPOSE["run"], COMPOSE["run"]
    assert set(COMPOSE["env"]) == {"ISSUE", "PR"}, COMPOSE["env"]


def test_the_step_runs_before_the_agent_does():
    names = [s.get("name") or s.get("uses") for s in STEPS]
    assert (names.index("Compose the cycle arguments")
            < next(i for i, n in enumerate(names)
                   if str(n).startswith("anthropics/claude-code-action")))
