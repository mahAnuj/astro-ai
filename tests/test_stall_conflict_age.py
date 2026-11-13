"""`pr-conflicting` carries the CONFLICT's age, not the PR's (#457).

THE DEFECT. Both `pr-conflicting` emitters passed `age_h=round(age, 1)` where
`age` is the PR's age since `createdAt`. `main` moves under every open branch,
so a PR can be days old and conflicted for an hour -- and the
`STEWARD_CLEARABLE` loop turns `age_h > 18` into `steward-ineffective`
("outlived 3+ steward runs, ESCALATE TO CHIEF"). Measured on #410: 79h old,
conflicted ~1h, and chief was told to rule on a conflict one hour old.

GitHub has no "became conflicting at" timestamp, so `conflict_age` takes the
smallest of three upper bounds: the PR's age, the newest check run's start on
the head (a `pull_request` run needs the merge ref, which a conflict removes),
and the age of a merge-commit head. The 18h threshold and the kind stay.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip
or xfail, by design.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
from datetime import datetime, timedelta, timezone

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
det = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(det)

N = 410


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pr(*, hours=79.0, mergeable="CONFLICTING"):
    return {
        "number": N, "title": f"PR {N}", "isDraft": False,
        "labels": [], "headRefName": f"issue/{N - 158}-whatever", "headRefOid": f"sha{N}",
        "createdAt": _iso(hours), "updatedAt": _iso(hours), "mergeable": mergeable,
    }


def _run(monkeypatch, *, pr_hours=79.0, checks, check_started=None, parents=1,
         head_hours=None, check_api_raises=False):
    """`find_stalls` with every network call stood in for.

    `checks` is what `latest_checks` returns ({} selects the no-checks arm).
    `check_started` is a list of (name, hours_ago) the check-runs API returns.
    """
    monkeypatch.setattr(det, "latest_checks", lambda sha: checks)
    monkeypatch.setattr(det, "agent_pushable", lambda n: True)
    monkeypatch.setattr(det, "boundary_paths", lambda n: set())

    def gh(*args):
        if args[0] == "pr" and args[1] == "list":
            return json.dumps([_pr(hours=pr_hours)])
        if args[0] == "pr" and args[1] == "view" and "commits" in args:
            if head_hours is None:
                return json.dumps({"commits": []})
            return json.dumps({"commits": [{"oid": f"sha{N}",
                                            "committedDate": _iso(head_hours)}]})
        if args[0] == "api" and args[1].endswith("/check-runs"):
            if check_api_raises:
                raise RuntimeError("gh api check-runs -> 1: boom")
            # What the helper's jq emits: one `name<TAB>started_at` per run. The
            # fake returns EVERY row, `merge` included, so the exclusion under
            # test is the helper's own.
            return "".join(f"{name}\t{_iso(h)}\n" for name, h in (check_started or []))
        if args[0] == "api" and "/commits/" in args[1]:
            return json.dumps({"parents": parents})
        return "[]"

    monkeypatch.setattr(det, "gh", gh)
    return det.find_stalls(4)


def _of(stalls, kind):
    return [s for s in stalls if s.get("pr") == N and s["kind"] == kind]


# ------------------------------------------------ the check-run bound (a, b, c)

def test_a_79h_old_PR_conflicted_for_an_hour_is_not_steward_ineffective(monkeypatch):
    """#410's exact shape. The newest check started 1h ago, so the PR was
    mergeable then and cannot have been conflicting longer."""
    stalls = _run(monkeypatch, checks={"gates": "success"}, check_started=[("gates", 1.0)])
    found = _of(stalls, "pr-conflicting")
    assert len(found) == 1
    assert found[0]["age_h"] < 3, found[0]["age_h"]
    assert not _of(stalls, "steward-ineffective"), (
        "an hour-old conflict was escalated to chief as outliving three steward runs (#457)")


def test_a_conflict_that_really_has_persisted_still_escalates(monkeypatch):
    """The control. The newest check started 30h ago, so the conflict can be
    ~30h old and the steward really has had its three runs. Silencing this would
    make the fix a relaxation, which is the one thing it must not be."""
    stalls = _run(monkeypatch, checks={"gates": "success"}, check_started=[("gates", 30.0)])
    found = _of(stalls, "pr-conflicting")
    assert 29 < found[0]["age_h"] < 31, found[0]["age_h"]
    assert _of(stalls, "steward-ineffective"), "real persistence stopped escalating"


def test_an_unreadable_check_api_falls_back_to_the_PR_age_and_still_emits(monkeypatch):
    stalls = _run(monkeypatch, checks={"gates": "success"}, check_api_raises=True)
    found = _of(stalls, "pr-conflicting")
    assert len(found) == 1, "an API error made the finding vanish or crash"
    assert 78 < found[0]["age_h"] < 80, found[0]["age_h"]
    assert _of(stalls, "steward-ineffective")


def test_the_merge_check_run_does_not_bound_the_conflict(monkeypatch):
    """`agent-merge`'s own `merge` check is not a gate and the sweep can start
    one on a conflicting head, so it proves nothing about mergeability."""
    stalls = _run(monkeypatch, checks={"gates": "success"},
                  check_started=[("merge", 0.2), ("gates", 30.0)])
    assert 29 < _of(stalls, "pr-conflicting")[0]["age_h"] < 31


# --------------------------------------------------- the merge-head bound (d, e)

def test_a_merge_commit_head_bounds_the_conflict_by_its_own_age(monkeypatch):
    """A head with two parents is a merge of `main`, which resolved any conflict
    that existed when it was made. Checks 40h ago would allow 40; the merge says 2."""
    stalls = _run(monkeypatch, checks={"gates": "success"}, check_started=[("gates", 40.0)],
                  parents=2, head_hours=2.0)
    found = _of(stalls, "pr-conflicting")
    assert 1.5 < found[0]["age_h"] < 2.5, found[0]["age_h"]
    assert not _of(stalls, "steward-ineffective")


def test_a_single_parent_head_does_not_bound_the_conflict(monkeypatch):
    """An ordinary commit proves nothing about mergeability: a fix can be pushed
    onto an already-conflicting branch. Only a merge resolves a conflict."""
    stalls = _run(monkeypatch, checks={"gates": "success"}, check_started=[("gates", 40.0)],
                  parents=1, head_hours=2.0)
    found = _of(stalls, "pr-conflicting")
    assert 39 < found[0]["age_h"] < 41, found[0]["age_h"]
    assert _of(stalls, "steward-ineffective")


# ------------------------------------------------------- the no-checks arm (f)

def test_no_checks_arm_a_merge_head_bounds_the_conflict(monkeypatch):
    stalls = _run(monkeypatch, checks={}, parents=2, head_hours=1.0)
    found = _of(stalls, "pr-conflicting")
    assert len(found) == 1
    assert "no check will ever run" in found[0]["detail"], "wrong arm"
    assert found[0]["age_h"] < 2, found[0]["age_h"]
    assert not _of(stalls, "steward-ineffective")


def test_no_checks_arm_without_a_merge_head_keeps_the_PR_age(monkeypatch):
    stalls = _run(monkeypatch, checks={}, parents=1, head_hours=1.0)
    found = _of(stalls, "pr-conflicting")
    assert 78 < found[0]["age_h"] < 80, found[0]["age_h"]
    assert _of(stalls, "steward-ineffective")


# ---------------------------------------------------------- the helper itself

def test_conflict_age_never_exceeds_the_PR_age_and_never_goes_negative(monkeypatch):
    """A check that 'started' after the PR was created is fine, but one dated in
    the future (clock skew) must clamp to zero rather than report -1h."""
    monkeypatch.setattr(det, "gh", lambda *a: f"gates\t{_iso(-1.0)}\n"
                        if a[1].endswith("/check-runs") else json.dumps({"parents": 1}))
    assert det.conflict_age(N, 5.0, "abc") == 0.0
    monkeypatch.setattr(det, "gh", lambda *a: "")
    assert det.conflict_age(N, 5.0, "abc") == 5.0


def test_conflict_age_does_not_raise_on_garbage(monkeypatch):
    monkeypatch.setattr(det, "gh", lambda *a: "not json, not a date\n")
    assert det.conflict_age(N, 7.0, "abc") == 7.0
