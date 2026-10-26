"""`pr-gates` must run on `main`, and a `main` run must not be cancellable.

#461: every other trigger asserts against `<branch> + main-at-the-time`, never
against `main` as it ends up. Two PRs landed on 2026-10-20 that were each green
alone and red as a pair -- one added a mutation row naming a test that has never
existed, the other added the check that reads that field -- and `main` stayed red
for a day with nothing reporting it. It surfaced only when PR #451 merged `main`
in and inherited the failure.

These are assertions on the WORKFLOW FILE, because that is where the defect was:
not a wrong value in code, but a trigger that was never declared. A unit test
over a parsed config is the only thing that can hold a trigger in place.
"""

import pathlib

import yaml

WF = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pr-gates.yml"


def _on() -> dict:
    """The `on:` block. YAML 1.1 parses the bare key `on` as the boolean True,
    which is why this is looked up by string rather than subscripted."""
    doc = yaml.safe_load(WF.read_text())
    key = next(k for k in doc if str(k) in ("on", "True"))
    return doc[key]


def test_pr_gates_runs_on_pushes_to_main():
    push = _on().get("push")
    assert push, "pr-gates declares no `push:` trigger, so `main` is never gated (#461)"
    assert "main" in (push.get("branches") or []), (
        f"pr-gates `push.branches` is {push.get('branches')!r}; `main` must be in it, "
        "or a red main is invisible until the next PR merges it in (#461)"
    )


def test_a_main_run_is_not_cancelled_by_the_next_push():
    # A cancelled run reports nothing, so cancelling on `main` would re-create
    # the invisibility #461 exists to fix, via the mechanism added to fix it.
    cancel = yaml.safe_load(WF.read_text())["concurrency"]["cancel-in-progress"]
    assert cancel is not True, (
        "cancel-in-progress is an unconditional true: a second push to `main` "
        "would cancel the first push's run and the breaking commit would leave "
        "no verdict at all (#461)"
    )
    assert "refs/heads/main" in str(cancel), (
        f"cancel-in-progress is {cancel!r}; it must exempt refs/heads/main so "
        "every main commit gets its own verdict (#461)"
    )


def test_the_full_mutation_sweep_runs_when_there_is_no_pull_request_base():
    # The #455 row arrived in one main commit and its reader in another, so a
    # sweep scoped to either commit's diff sees neither half. Only the full
    # sweep reads the tree as it actually is -- this pins that branch of the
    # step against being "optimised" to the push diff.
    #
    # Read off the PARSED step, not off the file text: an earlier version of
    # this test split the raw YAML on a sentinel phrase that also appears in
    # the `on:` block's own comment, so it asserted against a comment.
    doc = yaml.safe_load(WF.read_text())
    steps = doc["jobs"]["gates"]["steps"]
    step = next((x for x in steps if x.get("name") == "Prove the suite can fail"), None)
    assert step is not None, "the step that proves the suite can fail is gone (#461)"
    run = step["run"]
    assert "--changed-since" in run, (
        "the PR leg must still scope the sweep to the diff; unscoped on every PR "
        "is the ~22min job this repo already paid for"
    )
    # Split on the `else` that handles "no pull_request base".
    assert "else" in run, f"the step no longer branches on a missing base:\n{run}"
    unscoped = run.split("else", 1)[1]
    assert "mutate_behaviour_suite.py" in unscoped, (
        f"the non-PR branch does not run the sweep at all:\n{unscoped}"
    )
    assert "--changed-since" not in unscoped, (
        "the non-PR branch of the mutation step must run the sweep UNSCOPED; "
        f"scoping it to the push diff is what hides a two-commit defect (#461):\n{unscoped}"
    )
