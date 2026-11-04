"""A repeat `qa-fail` round is dated from its COMMENT, not from the label event.

WHY THIS IS A TEST, given the charter in conftest.py. #678 / #502, measured
twice: `qa_verdict.sh` adds `qa-fail`, and GitHub emits no `labeled` event when
the label is already on the PR, so every FAIL after round 1 was dated at
round 1.

  PR #675 (2026-11-02): timeline held ONE `labeled qa-fail` at 13:38Z; round 2
  FAILED at 17:03Z on head 33036d45 and left no event. The detector reported
  `qa-fail-refixed` -- "2 non-merge commits landed and no round has seen them"
  -- for two commits round 2 had already examined, and the steward was told to
  spend ~50 Actions minutes reproducing a FAIL.

  PR #498 (2026-10-23): four verdict comments, one label event. Detector said 3
  unreviewed commits; the true number was 1.

These tests drive the REAL `qa_fail_age`, `verdict_sha` and `find_stalls` with a
stubbed `gh` and no network. The comments endpoint is answered by running the
real `jq` filter the production call passes over a REST-shaped payload, so the
filter is under test too, not only the Python after it. A test that
monkeypatched `qa_fail_age` would test nothing here.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)

OLD_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
HEAD_SHA = "33036d45115bac53b50d95d83669061d2ab911a7"


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _comment(hours_ago: float, verdict: str, sha: str, user: str = "claude[bot]",
             body: str | None = None) -> dict:
    """A comment in the REST shape `gh api .../issues/N/comments` returns."""
    return {"user": {"login": user}, "created_at": _iso(hours_ago),
            "body": body if body is not None else f"QA: {verdict} — verified at `{sha}`\n\nnotes"}


def _commit(oid: str, hours_ago: float) -> dict:
    return {"oid": oid, "committedDate": _iso(hours_ago)}


class World:
    """One PR's worth of GitHub, answering the exact `gh` calls the detector makes."""

    def __init__(self, *, comments=None, label_events=None, commits=None,
                 comments_error: bool = False, number: int = 675):
        self.number = number
        self.comments = comments or []
        self.label_events = label_events or []
        self.commits = commits or []
        self.comments_error = comments_error
        self.calls: list[tuple[str, ...]] = []

    def pr(self, *, labels=("qa-fail",), head: str = HEAD_SHA, hours: float = 30) -> dict:
        return {"number": self.number, "title": "t", "isDraft": False,
                "labels": [{"name": n} for n in labels],
                "headRefName": f"issue/{self.number - 10}-x", "headRefOid": head,
                "createdAt": _iso(hours), "updatedAt": _iso(hours), "mergeable": "MERGEABLE"}

    def gh(self, *args):
        self.calls.append(args)
        if args[:2] == ("pr", "list"):
            return json.dumps([self.pr_obj])
        if args[:2] == ("pr", "view") and "commits" in args:
            return json.dumps({"commits": self.commits})
        if args[0] == "api" and args[1].endswith("/comments"):
            if self.comments_error:
                raise RuntimeError("gh api comments -> 1: boom")
            jq = args[args.index("--jq") + 1]
            res = subprocess.run(["jq", "-c", jq], input=json.dumps(self.comments),
                                 capture_output=True, text=True, check=True)
            return res.stdout
        if args[0] == "api" and args[1].endswith("/timeline"):
            return json.dumps(self.label_events)
        if args[0] == "api" and "/commits/" in args[1]:
            return json.dumps({"parents": 1})           # a real, non-merge commit
        return "[]"

    def install(self, monkeypatch, pr: dict | None = None):
        self.pr_obj = pr or self.pr()
        monkeypatch.setattr(detect_stalls, "gh", self.gh)
        monkeypatch.setattr(detect_stalls, "latest_checks", lambda sha: {"gates": "success"})
        monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: True)
        return self


def _find(world: World, monkeypatch, *, head: str = HEAD_SHA, hours: float = 4):
    world.install(monkeypatch, world.pr(head=head))
    return detect_stalls.find_stalls(hours)


def _kinds(stalls) -> set[str]:
    return {s["kind"] for s in stalls}


def _one(stalls, kind):
    hit = [s for s in stalls if s["kind"] == kind]
    assert hit, f"no {kind} in {_kinds(stalls)}"
    return hit[0]


# --- (a) the defect, executed ------------------------------------------------

def test_a_round_2_fail_on_the_current_head_is_unaddressed_not_refixed(monkeypatch):
    """THE #675 CASE. The label event says round 1, nine hours ago. Round 2's
    comment, five hours ago, names the head. The head commit's date (1h ago) is
    LATER than the comment -- a rebase does that -- so only the sha comparison
    can say nobody has pushed since."""
    w = World(
        comments=[_comment(9, "FAIL", OLD_SHA), _comment(5, "FAIL", HEAD_SHA)],
        label_events=[_iso(9)],
        commits=[_commit(OLD_SHA, 9.5), _commit(HEAD_SHA, 1)])
    stalls = _find(w, monkeypatch)
    assert "qa-fail-refixed" not in _kinds(stalls), _kinds(stalls)
    st = _one(stalls, "qa-fail-unaddressed")
    assert round(st["age_h"]) == 5, st            # dated from the comment, not the label
    assert "exact head" in st["detail"], st["detail"]


def test_a_fresh_fail_on_the_current_head_keeps_the_freshness_floor(monkeypatch, capsys):
    """The sha check must not defeat #659's floor: a verdict written an hour ago
    on the head is not yet a stall, it is just recent."""
    w = World(comments=[_comment(1, "FAIL", HEAD_SHA)], label_events=[_iso(9)],
              commits=[_commit(HEAD_SHA, 0.2)])
    stalls = _find(w, monkeypatch)
    assert _kinds(stalls) == set(), _kinds(stalls)
    assert "floor" in capsys.readouterr().out


def test_a_short_sha_in_the_comment_still_matches_the_head(monkeypatch):
    w = World(comments=[_comment(6, "FAIL", HEAD_SHA[:7])], label_events=[_iso(20)],
              commits=[_commit(HEAD_SHA, 1)])
    assert "qa-fail-unaddressed" in _kinds(_find(w, monkeypatch))


# --- (b) a real fix after the verdict is still seen ---------------------------

def test_exactly_one_non_merge_commit_after_the_verdict_is_refixed_with_count_1(monkeypatch):
    """The sha differs from the head, so the age comparison decides, and the
    commit count comes from the comment's time (not round 1's)."""
    w = World(
        comments=[_comment(9, "FAIL", OLD_SHA), _comment(5, "FAIL", OLD_SHA[:12])],
        label_events=[_iso(9)],
        # one commit before round 2 (reviewed by it) and exactly one after
        commits=[_commit("c" * 40, 7), _commit(HEAD_SHA, 2)])
    st = _one(_find(w, monkeypatch), "qa-fail-refixed")
    assert "1 non-merge commit(s)" in st["detail"], st["detail"]
    assert round(st["age_h"]) == 5, st


def test_a_fix_inside_the_fresh_window_is_still_refixed(monkeypatch):
    """The sha check sits in front of the arm order #659 fixed and must not
    reorder it: a verdict an hour old with a DIFFERENT head is refixed at once."""
    w = World(comments=[_comment(1, "FAIL", OLD_SHA)], label_events=[_iso(1)],
              commits=[_commit(OLD_SHA, 1.5), _commit(HEAD_SHA, 0.2)])
    assert "qa-fail-refixed" in _kinds(_find(w, monkeypatch))


# --- (c) the label event is the fallback, and only the fallback ---------------

def test_with_no_verdict_comment_the_label_event_dates_the_verdict(monkeypatch):
    w = World(comments=[], label_events=[_iso(12), _iso(10)], commits=[_commit(HEAD_SHA, 15)])
    w.install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 10
    assert detect_stalls.verdict_sha(675) is None
    st = _one(_find(w, monkeypatch), "qa-fail-unaddressed")
    assert round(st["age_h"]) == 10, st


def test_the_label_event_is_not_consulted_when_a_comment_exists(monkeypatch):
    w = World(comments=[_comment(3, "FAIL", HEAD_SHA)], label_events=[_iso(30)])
    w.install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 3
    assert not any(c[0] == "api" and c[1].endswith("/timeline") for c in w.calls), w.calls


# --- (d) only the QA identities can move the clock ----------------------------

@pytest.mark.parametrize("user", ["mallory", "claude-impostor[bot]", "mahAnuj"])
def test_a_look_alike_from_another_author_is_ignored(monkeypatch, user):
    """A pasted `QA: FAIL — verified at <head>` by anyone else must neither
    re-date the verdict nor mark the head as judged."""
    w = World(
        comments=[_comment(9, "FAIL", OLD_SHA),
                  _comment(0.5, "FAIL", HEAD_SHA, user=user)],
        label_events=[_iso(9)],
        commits=[_commit(OLD_SHA, 9.5), _commit(HEAD_SHA, 2)])
    w.install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 9
    assert detect_stalls.verdict_sha(675) == OLD_SHA
    assert "qa-fail-refixed" in _kinds(_find(w, monkeypatch))


@pytest.mark.parametrize("user", ["claude[bot]", "claude", "github-actions[bot]", "github-actions"])
def test_both_spellings_of_the_two_qa_identities_are_accepted(monkeypatch, user):
    """REST says `claude[bot]`; `gh pr view --json` says `claude`."""
    World(comments=[_comment(2, "FAIL", HEAD_SHA, user=user)]).install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 2


def test_only_the_first_line_of_a_comment_counts(monkeypatch):
    """A verdict QUOTED in the body of another comment is not a verdict."""
    body = f"re-running.\nQA: FAIL — verified at `{HEAD_SHA}`"
    World(comments=[_comment(1, "FAIL", HEAD_SHA, body=body)],
          label_events=[_iso(7)]).install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 7       # the label fallback
    assert detect_stalls.verdict_sha(675) is None


# --- (e) a later PASS is the newest verdict -----------------------------------

def test_a_pass_comment_later_than_the_fail_is_the_newest_verdict(monkeypatch):
    w = World(comments=[_comment(9, "FAIL", OLD_SHA), _comment(2, "PASS", HEAD_SHA)])
    w.install(monkeypatch)
    assert round(detect_stalls.qa_fail_age(675)) == 2
    assert detect_stalls.verdict_sha(675) == HEAD_SHA


def test_the_newest_is_by_time_not_by_position(monkeypatch):
    w = World(comments=[_comment(2, "FAIL", HEAD_SHA), _comment(9, "PASS", OLD_SHA)])
    w.install(monkeypatch)
    assert detect_stalls.verdict_sha(675) == HEAD_SHA


# --- (f) a failed read is None, never a guess ---------------------------------

def test_a_comment_fetch_failure_is_none_and_does_not_fall_back(monkeypatch):
    """"Could not ask" must not resolve to the label's (possibly round-1) date:
    that is the defect this file exists for, reached through an error path."""
    w = World(comments_error=True, label_events=[_iso(10)]).install(monkeypatch)
    assert detect_stalls.qa_fail_age(675) is None
    assert detect_stalls.verdict_sha(675) is None
    assert not any(c[0] == "api" and c[1].endswith("/timeline") for c in w.calls), w.calls


def test_an_unreadable_verdict_is_reported_as_unreadable(monkeypatch):
    w = World(comments_error=True, label_events=[_iso(10)], commits=[_commit(HEAD_SHA, 12)])
    assert "qa-fail-unreadable" in _kinds(_find(w, monkeypatch))


def test_comments_are_read_with_pagination(monkeypatch):
    """More than 30 comments is plausible on a PR with several QA rounds; the
    first page alone would miss the newest verdict."""
    w = World(comments=[_comment(1, "FAIL", HEAD_SHA)]).install(monkeypatch)
    detect_stalls.qa_fail_age(675)
    assert any(c[0] == "api" and c[1].endswith("/comments") and "--paginate" in c
               for c in w.calls), w.calls
