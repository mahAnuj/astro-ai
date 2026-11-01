"""`qa-on-green` dispatches a round the moment the gates pass — and nothing else.

WHY THIS IS A TEST, given the charter in conftest.py.

This workflow is a shell script inside a YAML string that can spend ~50 Actions
minutes and, uniquely among the dispatchers, fires on EVERY green gate run on
every PR. Nothing type-checks it. Three of its conditions are load-bearing in a
way that is silent when wrong:

  * the author match, where `claude[bot]`'s brackets are a glob character class
    unless quoted -- unquoted it matches nothing and the workflow is inert;
  * the namespace list, where the obvious widening `^[a-z]+/(\\d+)` reads
    `measurements/40140256532-1` as issue 40140256532, ~8 times a day;
  * the LOOP GUARD, where being wrong is not inert at all. A cycle that runs a
    round, pushes a fix and ends without a verdict leaves exactly the state this
    workflow fires on. Without a per-head guard it dispatches at its own output
    forever, and the first symptom is the Actions budget.

WHAT IT MAY NOT DO. It holds `pull-requests: write`, needed for the one comment
that IS the loop guard's memory. That grant is only safe while the workflow
cannot label: a dispatcher that could label could hand itself `qa-pass` and make
`agent-merge` decorative. `steward.md` carries the same rule for the same reason
("you may not apply or remove `qa-pass` or `qa-fail` ... if you could label, you
could unblock any PR by labelling it"). Here it is pinned rather than trusted.

MEASURED, 2026-10-25, which is why this exists. PR #536's cycle shipped 16
files, ran QA round 1, fixed its findings in `f91a2bc` and stopped. Both gates
were green at 16:35Z. `detect_stalls.py` could not see the PR -- 47 minutes old
against a 4h threshold -- and once it could, it queued behind #524 and #530 at
one dispatch per steward run. A finished, green, unverified PR waited most of a
day for a round that takes fifteen minutes.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

WF = (Path(__file__).resolve().parent.parent
      / ".github" / "workflows" / "qa-on-green.yml")
SRC = WF.read_text(encoding="utf-8")
DOC = yaml.safe_load(SRC)
# `on:` is YAML 1.1 true. Every other workflow test in this repo hits this.
ON = DOC.get("on") or DOC.get(True)
STEPS = DOC["jobs"]["consider"]["steps"]


def _step(name: str) -> dict:
    for s in STEPS:
        if s.get("name") == name:
            return s
    raise AssertionError(f"no step named {name!r}; the workflow was restructured")


PICK = _step("Is this a PR a cycle should finish?")["run"]


def _code(text: str) -> str:
    """`text` with comment-only lines dropped.

    Scanning the raw file would match this workflow's own prose about what it
    must not do -- the comments name `--add-label` and `gh workflow run` in
    order to forbid them. A guard that fires on its own rationale is noise, and
    noise is how a real hit gets ignored.
    """
    return "\n".join(ln for ln in text.splitlines()
                      if not ln.lstrip().startswith("#"))


RUNS = _code("\n".join(s.get("run") or "" for s in STEPS))


# --- 1. the grant it holds, and the thing that makes it safe ----------------

def test_the_dispatcher_can_never_write_a_verdict_label():
    """The whole justification for `pull-requests: write` on this file.

    If this workflow could label, it could apply `qa-pass` to any PR it chose
    and `agent-merge` would merge it on the strength of a label no QA round
    wrote. That is not a hypothetical shape in this repo -- it is the
    `USER AUTHORISED PUSH` failure, which has happened twice.
    """
    for forbidden in ("--add-label", "--remove-label", "gh pr edit",
                      "gh issue edit", "gh pr ready", "gh pr merge",
                      "gh pr close", "gh issue close"):
        assert forbidden not in RUNS, (
            f"qa-on-green.yml contains {forbidden!r}. It holds "
            f"`pull-requests: write` only for its dispatch comment; a verdict "
            f"is written by scripts/qa_verdict.sh and by nothing else."
        )


def test_the_permission_block_grants_no_more_than_it_needs():
    perms = DOC["permissions"]
    assert perms["contents"] == "read", "a dispatcher never needs to push"
    assert perms["actions"] == "write", "needed to dispatch agent-work"
    assert perms["issues"] == "read"
    assert "packages" not in perms and "id-token" not in perms


# --- 2. the trigger ---------------------------------------------------------

def test_the_trigger_names_the_workflow_by_its_name_and_not_its_filename():
    """`workflows: ["pr-gates"]` matched nothing and fired never.

    That exact mistake killed `agent-steward.yml`'s `workflow_run` leg, which
    is #421's class -- wiring that reports present and never runs. The value
    must be pr-gates.yml's `name:`.
    """
    assert ON["workflow_run"]["workflows"] == ["PR gates"]
    pr_gates = (WF.parent / "pr-gates.yml").read_text(encoding="utf-8")
    assert re.search(r"^name:\s*PR gates\s*$", pr_gates, re.M), (
        "pr-gates.yml no longer declares `name: PR gates`, so this trigger "
        "now matches nothing and this workflow can never fire"
    )


def test_it_is_serialised_so_two_pushes_do_not_race():
    assert DOC["concurrency"]["group"] == "qa-on-green"
    assert DOC["concurrency"]["cancel-in-progress"] is False


# --- 3. the author gate, executed ------------------------------------------

def _author_case() -> str:
    m = re.search(r'(case ",\$AGENT_AUTHORS," in.*?\n\s*esac)', PICK, re.S)
    assert m, "the author `case` is no longer recognisable"
    return m.group(1)


def _accepts(author: str, authors: str = "claude[bot],mahAnuj") -> bool:
    """Drive the REAL `case` block, not a reimplementation of it."""
    script = (
        'author="$1"\n'
        'AGENT_AUTHORS="$2"\n'
        'say() { :; }\n'
        + _author_case().replace("exit 0", "exit 1") + "\n"
        'echo ACCEPTED\n'
    )
    p = subprocess.run(["bash", "-c", script, "bash", author, authors],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    return "ACCEPTED" in p.stdout


@pytest.mark.parametrize("author", ["claude[bot]", "mahAnuj"])
def test_an_agent_author_is_accepted(author):
    assert _accepts(author), author


@pytest.mark.parametrize("author", [
    "b", "o", "t",                 # what `[bot]` matches as a character class
    "claude[bot]-x", "Claude[bot]", "xclaude[bot]",
    "dependabot[bot]", "mahAnu", "notmahAnuj",
])
def test_a_near_miss_on_the_author_is_refused(author):
    assert not _accepts(author), author


def test_the_author_match_is_quoted_so_brackets_are_literal():
    """Unquoted, `$author` expands into the `case` PATTERN and `[bot]` becomes
    a character class — so `claude[bot]` matches only `b`, `o` or `t`, the gate
    matches nothing, and the workflow is silently inert. Measured; the same
    trap is pinned in tests/test_agent_merge_fork_guard.py."""
    assert '*",$author,"*)' in PICK, (
        "the author pattern is no longer quoted; `[bot]` will be read as a glob "
        "character class and this gate will match nothing"
    )


# --- 4. the owning issue ----------------------------------------------------

def _issue_for(branch: str) -> str:
    m = re.search(r"(sed -nE 's#\^\(issue\|partial\|fix\)[^']*')", PICK)
    assert m, "the owning-issue sed is no longer recognisable"
    p = subprocess.run(["bash", "-c", f"printf '%s' \"$1\" | {m.group(1)}",
                        "bash", branch],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    return p.stdout.strip()


@pytest.mark.parametrize("branch,issue", [
    ("issue/523-per-area-day-ratings", "523"),
    ("partial/475-cached-token-header-measure", "475"),
    ("fix/515-claude-cannot-write-to-tmp", "515"),
])
def test_every_cycle_namespace_yields_its_issue(branch, issue):
    assert _issue_for(branch) == issue


@pytest.mark.parametrize("branch", [
    "measurements/40140256532-1", "measurements/39867786023-1",
    "main", "chore/hand-edit",
])
def test_a_branch_with_no_owning_issue_yields_nothing(branch):
    """`^[a-z]+/(\\d+)` is the obvious widening and it is wrong: it would aim a
    ~50-minute cycle at issue 40140256532, ~8 times a day."""
    assert _issue_for(branch) == ""


def test_the_sed_uses_a_portable_dialect():
    """BSD sed (macOS) treats `\\|` as a literal, so a GNU-style alternation
    matches NOTHING, and `|` cannot be the `s` delimiter when the regex uses
    alternation. Both were hit writing this."""
    assert "sed -nE 's#" in PICK, "use -E with `#` as the delimiter"
    assert r"\|" not in PICK, r"`\|` is a GNU extension; BSD sed matches nothing"


# --- 5. the loop guard, which is the reason this is safe to run on every green

def test_the_dispatch_is_remembered_against_the_head_commit():
    """Without this the workflow dispatches at its own output, forever.

    A cycle that runs a round, pushes a fix and ends with no verdict leaves
    precisely the state this workflow fires on. The guard must be keyed on the
    HEAD, not on the PR: a new commit is new information and earns another
    round; the same commit never does.
    """
    assert "qa-on-green: dispatched at $head" in PICK, (
        "the loop guard no longer searches for a per-head dispatch marker"
    )
    comment = _step("Record the dispatch on the PR")["run"]
    assert "qa-on-green: dispatched at $PR_HEAD" in comment, (
        "the comment no longer writes the marker the guard reads — the guard "
        "would never match and every green would dispatch again"
    )


def test_the_marker_is_written_before_the_dispatch_and_not_after():
    """The comment is the guard's only memory. A dispatch that happened with no
    comment is invisible to the next run, which dispatches again."""
    names = [s.get("name") for s in STEPS]
    assert names.index("Record the dispatch on the PR") < \
           names.index("Carry out the dispatch")


def test_the_guard_and_the_dispatch_share_one_condition():
    """If the comment could be skipped while the dispatch ran, the guard is
    bypassed for that head."""
    for name in ("Record the dispatch on the PR", "Carry out the dispatch"):
        assert _step(name)["if"] == "steps.pick.outputs.go == 'true'", name


# --- 6. what it declines ----------------------------------------------------

@pytest.mark.parametrize("label,why", [
    ("qa-pass", "agent-merge owns it from there"),
    ("qa-fail", "needs a fix, and which fix is a judgment steward.md holds"),
    ("needs-human-review", "someone has been told"),
])
def test_it_declines_a_pr_that_is_already_routed(label, why):
    assert f'*",{label},"*)' in PICK, f"{label} is no longer declined ({why})"


def test_a_workflow_touching_diff_IS_JUDGED_and_no_longer_declined():
    """THE #610 CHANGE, and the old test asserted the opposite of it.

    Until 2026-11-01 this step exited on such a diff -- "the App token cannot
    push that branch. A human has to." That reasoning conflated *cannot fix*
    with *cannot judge*, and the consequence was not "a human handles it": it
    was that nothing ever wrote `qa-pass`, which `agent-merge` will not merge
    without. PR #631 sat green, unlabelled and unmergeable for a day on that
    line.

    The test that stood here passed on `'.github/workflows/' in PICK`, which
    is still true after the behaviour inverted -- a substring assertion so
    loose it could not tell decline from dispatch. That is #634's BUG-2 class,
    and this replacement asserts the branch's effect instead of its vocabulary.
    """
    assert "judge_only=true" in _code(PICK), "the judge-only flag is gone"
    # `_code`, not PICK: the new comment block QUOTES the deleted lines so the
    # next reader can see what changed, and a raw scan would match that
    # rationale. The file's own `_code` exists for exactly this -- "a guard
    # that fires on its own rationale is noise".
    assert "A human has to" not in _code(PICK), (
        "the old decline is back; a workflow PR gets no verdict and so cannot merge")
    assert "A human has to" in PICK, (
        "the comment no longer records what this step used to do, so the next "
        "reader cannot tell this was a deliberate inversion")


def test_judge_only_defaults_to_false_before_anything_tests_the_diff():
    """Fail toward the NORMAL cycle, not toward judge-only.

    An unset flag that defaulted to judge-only would silently stop every cycle
    from pushing -- a repo-wide outage that looks like success.
    """
    code = _code(PICK)
    assert "judge_only=false" in code
    assert code.index("judge_only=false") < code.index("judge_only=true")


def test_the_judge_only_flag_is_an_output_of_the_pick_step():
    assert 'echo "judge_only=$judge_only"' in PICK


def test_the_dispatch_comment_receives_the_flag_as_an_env_var():
    """A value interpolated into `run:` instead of passed through `env:` is the
    injection shape this workflow's own tests already police elsewhere."""
    env = _step("Record the dispatch on the PR").get("env") or {}
    assert env.get("JUDGE_ONLY") == "${{ steps.pick.outputs.judge_only }}"


def test_the_RULE_lives_in_agent_cycle_md_and_the_comment_only_reminds():
    """A rule an agent must obey cannot be sourced from the artefact under review.

    The PR comment is data the cycle reads. If the comment were the only place
    the no-push rule existed, anyone who could comment on the PR could lift it.
    """
    cycle = (WF.parent.parent.parent / ".claude" / "commands" / "agent-cycle.md")
    text = cycle.read_text(encoding="utf-8")
    assert "JUDGE-ONLY" in text, "agent-cycle.md does not carry the rule"
    assert "you cannot push to this branch" in text
    assert "agent-cycle.md" in PICK, "the comment does not point at the authority"


def test_the_workflow_path_predicate_actually_matches_a_workflow_file():
    """Runs the step's own jq expression through real jq.

    A substring assertion cannot tell whether the predicate works; this repo
    has already shipped a `startswith` against the wrong field. Both arms are
    checked, because a predicate that matched everything would pass the
    positive case alone.
    """
    m = re.search(r"jq -e '([^']+)'", PICK)
    assert m, "the files predicate is no longer a single-quoted jq expression"
    expr = m.group(1)

    def _matches(paths):
        payload = json.dumps([{"files": [{"path": q} for q in paths]}])
        r = subprocess.run(["jq", "-e", expr], input=payload,
                           capture_output=True, text=True)
        return r.returncode == 0

    assert _matches([".github/workflows/agent-work.yml"])
    assert _matches(["src/astro_ai/chart.py", ".github/workflows/agent-merge.yml"])
    assert not _matches(["src/astro_ai/chart.py", "tests/test_x.py"])
    assert not _matches(["docs/.github/workflows/not-really.yml"]), (
        "the predicate matched a path that merely CONTAINS the prefix")


def test_it_refuses_to_act_on_a_stale_green():
    """The gates that passed may not be the gates on the current head: a push
    during the run moves it. Acting on a stale green aims a round at code the
    gates never saw."""
    assert '[ "$head" != "$HEAD_SHA" ]' in PICK


def test_a_red_gate_is_not_a_reason_to_do_anything():
    assert '[ "$GATES_CONCLUSION" != "success" ]' in PICK


# --- 7. it reuses the carrier rather than copying it ------------------------

def test_the_dispatch_goes_through_the_shared_carrier():
    """This repo's most reliable defect is a copied file diverging --
    `id-token: write` was missing from four loops each copied from a fifth. The
    carrier re-checks that the issue is open and that no cycle is in flight, and
    verifies the run survived 90s, because `gh workflow run` exits 0 on a run
    that dies in 1.5s (#421, hidden three days)."""
    run = _step("Carry out the dispatch")["run"]
    assert "scripts/dispatch_cycle.sh" in run
    assert "gh workflow run" not in RUNS, (
        "dispatching directly skips the carrier's concurrency and liveness "
        "checks — use scripts/dispatch_cycle.sh"
    )


def test_every_value_reaches_the_shell_as_an_env_var():
    """A `workflow_run` workflow runs with the base repo's permissions against
    a head it did not write, so a `${{ }}` in a `run:` block is an injection
    sink. verify_workflows.py enforces this; this test states why."""
    for step in STEPS:
        assert "${{" not in (step.get("run") or ""), step.get("name")
