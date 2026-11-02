"""`agent-work`'s safety net must rescue every branch a cycle may end on.

WHY THIS IS A TEST, given the charter in conftest.py.

Same footing as test_agent_merge_sweep.py: the control is a shell `case` inside
a YAML string, nothing type-checks it, and its failure mode is silent in the
worst possible way -- it DISCARDS WORK and reports success.

The step is the last thing standing between a finished cycle and a destroyed
runner. agent-cycle.md records why it exists, measured: run 37749887640 spent
63 minutes on #270 -- architect, engineer, QA -- produced a complete branch and
died at the push with `Invalid username or token`, because the GitHub App token
the action hands out expires after one hour. 25 turns and $5.34 of finished
work, lost, as it had never left the runner.

Until 2026-10-25 the `case` accepted `issue/*` and nothing else. agent-cycle.md
Step 4 tells a cycle to name its branch `partial/<n>-<slug>` whenever acceptance
criteria remain that the loop cannot do, and on such a branch this step printed
"Cycle shipped nothing", **exited 0 and pushed nothing** -- the exact loss it was
written to prevent, in the namespace that needed it most. agent-cycle.md:363
carried the warning ("nothing will catch you") because the loop's own token
cannot edit a workflow to fix it.

So the question the step must ask is "are there commits here that would be
lost", which a branch NAME cannot answer. These tests drive the real `case` with
every namespace a cycle produces, and pin the two refusals that remain: `main`,
where a push is the deploy, and a detached HEAD, which is not a pushable ref.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WF = (Path(__file__).resolve().parent.parent
      / ".github" / "workflows" / "agent-work.yml")
JOB = yaml.safe_load(WF.read_text(encoding="utf-8"))["jobs"]


def _net_case() -> str:
    """The `case` block out of the net step, verbatim.

    Lifted rather than reimplemented: a copy of the logic in the test body would
    pass forever while the workflow shipped something else, which is the defect
    `mutate_behaviour_suite.py` caught twice in this repo.
    """
    steps = next(iter(JOB.values()))["steps"]
    step = next(s for s in steps
                if s.get("name") == "Push the branch and open the PR")
    run = step["run"]
    m = re.search(r"(case \"\$branch\" in.*?\n\s*esac)", run, re.S)
    assert m, "the net's `case \"$branch\"` block is no longer recognisable"
    return m.group(1)


CASE = _net_case()


def _would_push(branch: str) -> bool:
    """True when the net proceeds past the `case` for this branch name.

    The real step continues to a commit check and a `git push`; neither can run
    here. So the block is driven with `exit 0` replaced by a marker: reaching
    the end of the `case` means the step would go on to push.
    """
    script = (
        'branch="$1"\n'
        'GITHUB_STEP_SUMMARY=/dev/null\n'
        + CASE + "\n"
        'echo PROCEEDS\n'
    )
    p = subprocess.run(["bash", "-c", script, "bash", branch],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return "PROCEEDS" in p.stdout


# --- 1. every namespace a cycle may end on is rescued -----------------------

@pytest.mark.parametrize("branch", [
    "issue/523-per-area-day-ratings",
    "partial/523-per-area-day-ratings",
    "partial/398-bphs-attributions-and-grain-cross-assignments",
    "fix/515-claude-cannot-write-to-tmp",
    "chore/something-unanticipated",
])
def test_the_push_net_rescues_every_branch_a_cycle_may_end_on(branch):
    assert _would_push(branch), branch


def test_a_partial_branch_is_rescued_because_that_was_the_defect():
    """Named separately from the sweep above so the regression is unmissable.

    #480, #487, #512 and #530 all shipped from `partial/` branches. Each
    survived only because the agent pushed by hand inside the hour; the net
    would have thrown any of them away.
    """
    assert _would_push("partial/398-surya-namaskar-and-grid-attribution")


# --- 2. the two refusals that remain ----------------------------------------

def test_the_net_never_pushes_main():
    """A push to `main` is the deploy. This net must never be the thing that
    deploys, and a cycle that meant to ship never ends on `main` -- it branches
    first."""
    assert not _would_push("main")


def test_the_net_never_pushes_a_detached_head():
    """`git rev-parse --abbrev-ref HEAD` prints `HEAD` when detached, which is
    not a ref that can be pushed."""
    assert not _would_push("HEAD")


# --- 3. a local alias of work already on the remote is not rescued ----------

def _alias_guard() -> str:
    steps = next(iter(JOB.values()))["steps"]
    run = next(s for s in steps if s.get("name") == "Push the branch and open the PR")["run"]
    m = re.search(r"(^if ! git ls-remote --exit-code --heads origin \"\$branch\".*?\n  fi\nfi)",
                  run, re.S | re.M)
    assert m, "the alias guard is no longer recognisable"
    return m.group(1)


def _git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *a], check=True, capture_output=True, timeout=60)


def _guard_says(tmp_path, *, local, pushed_as=None, extra_local_commit=False):
    """A real origin and clone. `pushed_as` is the remote branch already holding
    the PR's commit; `local` is the name the cycle ended on."""
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True,
                   capture_output=True)
    _git(clone, "commit", "-q", "--allow-empty", "-m", "base")
    _git(clone, "push", "-q", "origin", "HEAD:main")
    _git(clone, "checkout", "-q", "-b", local)
    _git(clone, "commit", "-q", "--allow-empty", "-m", "pr work")
    if pushed_as:
        _git(clone, "push", "-q", "origin", f"HEAD:{pushed_as}")
        _git(clone, "update-ref", "-d", f"refs/remotes/origin/{pushed_as}")  # a fresh runner
    if extra_local_commit:
        _git(clone, "commit", "-q", "--allow-empty", "-m", "not yet pushed")
    script = ('branch="$1"\nGITHUB_STEP_SUMMARY=/dev/null\n' + _alias_guard() + "\necho PROCEEDS\n")
    # `-eo pipefail`: the strictest shell the step could ever be given. Plain
    # `bash -c` passed with or without B1's fix (#675 QA round 3).
    p = subprocess.run(["bash", "-eo", "pipefail", "-c", script, "bash", local], cwd=clone,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_a_QA_checkout_under_a_local_name_is_not_pushed_as_a_new_PR(tmp_path):
    """PR #677: a judge-only round checked #675 out as `qa-675`, and the net
    pushed it and opened a duplicate PR at an older head."""
    out = _guard_says(tmp_path, local="qa-675", pushed_as="claude/peaceful-pascal-c5vwht")
    assert "nothing to rescue" in out and "PROCEEDS" not in out, out


def test_unpushed_commits_on_a_new_name_are_still_rescued(tmp_path):
    """The case the net exists for: a cycle committed and ran out of time."""
    assert "PROCEEDS" in _guard_says(tmp_path, local="issue/523-x")


def test_an_alias_with_a_NEW_commit_on_top_is_still_rescued(tmp_path):
    out = _guard_says(tmp_path, local="qa-675", pushed_as="claude/peaceful-pascal-c5vwht",
                      extra_local_commit=True)
    assert "PROCEEDS" in out, out


def test_a_branch_the_agent_pushed_under_its_OWN_name_continues(tmp_path):
    """It must reach the #322 pr-gates dispatch further down."""
    out = _guard_says(tmp_path, local="issue/523-x", pushed_as="issue/523-x")
    assert "PROCEEDS" in out, out
