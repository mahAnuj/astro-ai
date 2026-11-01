"""A CONFLICTING PR is work, not a gate defect — whatever its checks say (#616).

THE DEFECT, found by `steward` on 2026-10-31 while verifying its own finding.
`detect_stalls.py` classifies with an `if/elif` chain, and `qa-pass and green`
came BEFORE any test of `mergeable`. `green` is computed from check runs on the
HEAD SHA, which are **history**: they stay green after `main` moves underneath
the branch and the PR becomes CONFLICTING.

So a PR that was green with `qa-pass` and then conflicted satisfied the
`mergeable-but-open` branch — whose detail line says the merge GATE has a
defect. The routing table sends the two kinds to OPPOSITE actions:

    mergeable-but-open   do not touch the PR, diagnose the gate, file an issue
    pr-conflicting       dispatch a cycle, run merge_main_into_branch.py --push

Measured on PR #608 (head `0880a6a`): CONFLICTING/DIRTY, labels `qa-pass` +
`qa:in-cycle`, both gates green from the previous day, reported
`mergeable-but-open` with no mention of the conflict. `git merge-tree` showed
the conflict was one file, `scripts/mutate_behaviour_suite.py` — a class
`merge_main_into_branch.py` resolves mechanically. **The gate was correct**:
`agent-merge` skips a conflicting PR by design (#403). The steward was sent to
diagnose something that had nothing wrong with it.

A CONFLICTING TEST ALREADY EXISTED and could not reach this case: it sits under
`elif not checks:`, a branch only entered when NOTHING ever ran. A PR with green
history and a later conflict never gets there.

WHY `UNKNOWN` IS THE CASE THAT MATTERS MOST HERE. GitHub computes `mergeable`
lazily and answers `UNKNOWN` until the background job finishes — routinely, for
seconds after every push. An equality test against `"CONFLICTING"` is correct;
a truthiness or negation test (`!= "MERGEABLE"`) would classify every freshly
pushed PR as conflicting and send a cycle to merge `main` into a branch that
does not need it. That is the defect class this whole area keeps producing: a
guard whose input can be legitimately empty or ambiguous. Three cases below
pin it.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
det = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(det)


def _pr(number=608, *, draft=False, hours=9.0, labels=("qa-pass",), mergeable="MERGEABLE"):
    """One open PR as `gh pr list --json ...,mergeable` returns it.

    `mergeable` is passed through verbatim, including the absent case, because
    the shape of the real payload is the thing under test.
    """
    created = datetime.now(timezone.utc) - timedelta(hours=hours)
    doc = {
        "number": number, "title": f"PR {number}", "isDraft": draft,
        "labels": [{"name": n} for n in labels],
        "headRefName": f"issue/{number - 158}-whatever",
        "headRefOid": f"sha{number}",
        "createdAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if mergeable is not None:
        doc["mergeable"] = mergeable
    return doc


def _run(monkeypatch, prs, *, checks=None):
    """`find_stalls` with every network call stood in for.

    `checks` defaults to a green `gates`, which is the whole point: the defect
    only appears when the check history IS green.
    """
    monkeypatch.setattr(det, "latest_checks",
                        lambda sha: {"gates": "success"} if checks is None else checks)
    monkeypatch.setattr(det, "agent_pushable", lambda n: True)
    monkeypatch.setattr(det, "boundary_paths", lambda n: set())

    def gh(*args):
        if args[0] == "pr" and args[1] == "list":
            return json.dumps(prs)
        return "[]"

    monkeypatch.setattr(det, "gh", gh)
    return det.find_stalls(4)


def _for(stalls, number):
    return [s for s in stalls if s.get("pr") == number]


def _kinds(stalls, number=608):
    return {s["kind"] for s in _for(stalls, number)}


# ------------------------------------------------------------- the defect

def test_a_green_qa_pass_pr_that_CONFLICTED_is_not_called_a_gate_defect(monkeypatch):
    """PR #608's exact shape. This is the regression."""
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING")])
    assert "pr-conflicting" in _kinds(stalls)
    assert "mergeable-but-open" not in _kinds(stalls), (
        "a conflicted PR is routed to 'diagnose the gate' instead of 'merge main in' "
        "-- #616, and the gate it would diagnose is working correctly (#403)")


def test_the_detail_says_the_green_checks_are_HISTORY(monkeypatch):
    """The steward reads the detail line, and the previous one never mentioned
    the conflict at all. Naming why the checks look green is what stops the
    next reader re-deriving this."""
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING")])
    detail = _for(stalls, 608)[0]["detail"]
    assert "history" in detail
    assert "#403" in detail, "the detail does not say the gate is behaving correctly"
    assert "merge_main_into_branch.py" in detail


def test_it_warns_that_resolving_the_conflict_invalidates_the_qa_pass(monkeypatch):
    """A push that resolves a conflict makes a new head, so a `qa-pass` bound
    to the old SHA is stale. Unbound labels have cost this repo twice in one
    week (#609, #564), so the finding says it rather than leaving it implied.
    """
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING")])
    assert "fresh round" in _for(stalls, 608)[0]["detail"]


def test_the_finding_carries_conflicting_true_so_the_routing_table_matches(monkeypatch):
    """Same `kind` and same flag as the pre-existing branch, deliberately: one
    cause, one kind, one action, so `steward.md` needs no new row."""
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING")])
    assert _for(stalls, 608)[0]["conflicting"] is True


# ---------------------------------------------- the controls that matter

def test_a_MERGEABLE_green_qa_pass_pr_is_STILL_mergeable_but_open(monkeypatch):
    """The control. If the new branch swallowed this, #319's real defect -- a
    PR with every merge condition met, open nine hours -- would stop being
    reported at all, and the fix would be worse than the bug."""
    stalls = _run(monkeypatch, [_pr(mergeable="MERGEABLE")])
    assert "mergeable-but-open" in _kinds(stalls)
    assert "pr-conflicting" not in _kinds(stalls)


@pytest.mark.parametrize("value", ["UNKNOWN", None, "", "mergeable", "DIRTY"])
def test_anything_that_is_not_exactly_CONFLICTING_is_not_treated_as_conflicting(
        value, monkeypatch):
    """GitHub answers `UNKNOWN` while it computes mergeability -- routinely, for
    seconds after every push -- and the field can be absent entirely.

    A negation test (`!= "MERGEABLE"`) would send a cycle to merge `main` into
    every freshly pushed branch. `DIRTY` is here too: it is `mergeStateStatus`,
    a DIFFERENT field, and matching it would couple this to a value the query
    does not even request.
    """
    stalls = _run(monkeypatch, [_pr(mergeable=value)])
    assert "pr-conflicting" not in _kinds(stalls), (
        f"mergeable={value!r} was read as a conflict")
    assert "mergeable-but-open" in _kinds(stalls)


def test_a_conflicting_pr_with_NO_checks_still_reaches_the_older_branch(monkeypatch):
    """The pre-existing path is untouched.

    That branch explains a second cause -- a PR created by GITHUB_TOKEN, whose
    events GitHub suppresses -- and only a human can rescue that one. Breaking
    it would trade one misroute for another.
    """
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING", labels=())], checks={})
    assert "pr-conflicting" in _kinds(stalls)
    assert _for(stalls, 608)[0]["conflicting"] is True


def test_a_conflicting_pr_with_no_verdict_is_still_reported_as_conflicting(monkeypatch):
    """The new branch does not require `qa-pass`.

    A conflict blocks the merge whatever the verdict is, and the action is the
    same. Requiring `qa-pass` would leave an unverdicted conflicted PR falling
    through to a later branch that tells the steward to run a QA round against
    a branch GitHub cannot build a merge ref for.
    """
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING", labels=())])
    assert "pr-conflicting" in _kinds(stalls)


def test_a_DRAFT_conflicting_pr_is_still_classified_by_its_draft_state(monkeypatch):
    """Chain order above the new branch is unchanged.

    A draft cannot merge at all, so the conflict is not the thing to act on
    first -- and `draft-never-readied` is in `STEWARD_CLEARABLE` while a
    conflict on a draft is not yet work.
    """
    stalls = _run(monkeypatch, [_pr(draft=True, hours=26, mergeable="CONFLICTING", labels=())])
    assert "draft-never-readied" in _kinds(stalls)
    assert "pr-conflicting" not in _kinds(stalls)


def test_a_boundary_hold_outranks_a_conflict(monkeypatch):
    """`needs-human-review` + `qa-pass` + green is tested before the new branch.

    A held PR's hold is the more important fact: resolving its conflict does
    not make it mergeable, and routing it to a cycle would have the cycle push
    to a branch that is still held. chief rules first.
    """
    monkeypatch.setattr(det, "boundary_paths", lambda n: {"src/astro_ai/prompts/natal.txt"})
    stalls = _run(monkeypatch, [_pr(mergeable="CONFLICTING",
                                    labels=("qa-pass", "needs-human-review"))])
    assert "pr-conflicting" not in _kinds(stalls)
    assert any(k.startswith("boundary-hold") for k in _kinds(stalls)), _kinds(stalls)
