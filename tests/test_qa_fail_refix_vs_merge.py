"""`qa-fail-refixed` asserted a fix from a timestamp. A merge is not a fix.

WHY THIS TEST EXISTS
--------------------
The detector compared the `qa-fail` label's age against the head commit's age
and, when the head was newer, routed the PR as `qa-fail-refixed` with the detail
"a fix landed after the verdict and no round has seen it. Dispatch QA."

Measured 2026-10-20 against the live repository: PRs #418 and #419 were both
classified that way, and the only commit after either verdict was
`Merge origin/main` clearing a conflict. Their findings were untouched. The
routed action would have spent two independent QA rounds re-discovering the same
defects, and the routed COMMENT would have told each round that the fix had
already landed -- a false premise handed to the one role whose job is to check.

This is the week's recurring shape at the routing layer rather than the test
layer: the signal was real, the inference from it was not, and nothing could
tell the difference because nobody asked what the new commits were.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)


def _pr(number: int, *, labels: list[str], hours: float = 30.0) -> dict:
    created = datetime.now(timezone.utc) - timedelta(hours=hours)
    return {
        "number": number, "title": f"PR {number}", "isDraft": False,
        "labels": [{"name": n} for n in labels],
        "headRefName": f"issue/{number - 10}-whatever", "headRefOid": f"sha{number}",
        "createdAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mergeable": "MERGEABLE",
    }


@pytest.fixture
def world(monkeypatch):
    """A single open PR carrying `qa-fail`, green checks, head newer than the verdict."""
    prs = [_pr(418, labels=["qa-fail", "qa:independent"])]

    def gh(*args):
        if args[0] == "pr" and args[1] == "list":
            return json.dumps(prs)
        return "[]"

    monkeypatch.setattr(detect_stalls, "gh", gh)
    monkeypatch.setattr(detect_stalls, "latest_checks", lambda sha: {"gates": "success"})
    monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: True)
    monkeypatch.setattr(detect_stalls, "qa_fail_age", lambda n: 5.0)
    monkeypatch.setattr(detect_stalls, "head_pushed_hours_ago", lambda n: 2.0)
    # RETURN monkeypatch, not the module. The first version of this file
    # assigned `world.post_verdict_commits = ...` directly, which monkeypatch
    # never undoes -- so the stub from one test leaked into the next and the
    # last test in the file read a `(0, 0)` left behind by an earlier one.
    # The tests passed; the isolation did not exist. Same class as every
    # vacuous fixture this repo found this week.
    return monkeypatch


def _only(stalls, *kinds):
    return [s for s in stalls if s["kind"] in kinds]


def test_a_merge_after_the_verdict_is_not_a_refix(world):
    """THE DEFECT, restored: one merge commit and nothing else."""
    world.setattr(detect_stalls, "post_verdict_commits", lambda pr, age: (0, 1))
    stalls = detect_stalls.find_stalls(4)

    hit = _only(stalls, "qa-fail-unaddressed", "qa-fail-refixed")
    assert len(hit) == 1, [s["kind"] for s in stalls]
    assert hit[0]["kind"] == "qa-fail-unaddressed", (
        "a merge forward leaves the findings exactly where they were")
    assert "MERGES" in hit[0]["detail"]
    assert "not a fix" in hit[0]["detail"]
    # And it must not send a QA round at unaddressed findings.
    assert "Dispatch a cycle" in hit[0]["detail"]
    assert "Dispatch QA." not in hit[0]["detail"]


def test_a_real_commit_after_the_verdict_still_routes_to_qa(world):
    """The other side of the boundary, so the fix is not just "never refixed"."""
    world.setattr(detect_stalls, "post_verdict_commits", lambda pr, age: (2, 0))
    stalls = detect_stalls.find_stalls(4)

    hit = _only(stalls, "qa-fail-unaddressed", "qa-fail-refixed")
    assert len(hit) == 1
    assert hit[0]["kind"] == "qa-fail-refixed"
    assert "Dispatch QA" in hit[0]["detail"]
    assert "2 non-merge commit(s)" in hit[0]["detail"]


def test_a_merge_plus_a_real_commit_is_a_refix(world):
    """A branch that merged main AND then fixed something is a refix."""
    world.setattr(detect_stalls, "post_verdict_commits", lambda pr, age: (1, 3))
    stalls = detect_stalls.find_stalls(4)
    hit = _only(stalls, "qa-fail-unaddressed", "qa-fail-refixed")
    assert hit[0]["kind"] == "qa-fail-refixed"


def test_unclassifiable_commits_hedge_instead_of_guessing(world):
    """`None` means the parents could not be read.

    The detail must claim NEITHER a fix nor a merge. A detector that guesses a
    direction here dispatches the wrong agent and burns a full cycle, which is
    the reasoning already written beside `qa-fail-unreadable`.
    """
    world.setattr(detect_stalls, "post_verdict_commits", lambda pr, age: None)
    stalls = detect_stalls.find_stalls(4)

    hit = _only(stalls, "qa-fail-unaddressed", "qa-fail-refixed")
    assert len(hit) == 1
    d = hit[0]["detail"]
    assert "could not be classified" in d
    assert "unknown" in d
    assert "a fix landed" not in d, "this is the assertion the detector must not make"


def test_no_commits_newer_than_the_verdict_is_not_a_refix(world):
    """Defensive: `(0, 0)` must not read as "a fix landed"."""
    world.setattr(detect_stalls, "post_verdict_commits", lambda pr, age: (0, 0))
    stalls = detect_stalls.find_stalls(4)
    hit = _only(stalls, "qa-fail-unaddressed", "qa-fail-refixed")
    assert hit[0]["kind"] == "qa-fail-refixed", (
        "(0,0) means nothing was found to classify; it must not claim a merge")
    assert "non-merge commit(s)" in hit[0]["detail"]


def test_merge_ness_comes_from_parent_count_not_the_message(monkeypatch):
    """A commit whose headline says "Merge" may be an ordinary commit, and one
    that fixes something may be a merge. Only the parent count decides."""
    calls = []

    def gh(*args):
        calls.append(args)
        if args[0] == "pr" and args[1] == "view":
            return json.dumps({"commits": [
                {"oid": "aaa", "committedDate":
                    (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "messageHeadline": "Merge origin/main"},
            ]})
        if args[0] == "api":
            return json.dumps({"parents": 1})      # headline lies; one parent
        return "[]"

    monkeypatch.setattr(detect_stalls, "gh", gh)
    assert detect_stalls.post_verdict_commits(418, 5.0) == (1, 0)
    assert any(a[0] == "api" for a in calls), "it must ask the API for parents"
