"""A `qa-fail` written minutes ago is not a stall, and reporting it as one
manufactured three Claude invocations with no possible outcome.

WHY THIS IS A TEST, given the charter in conftest.py.

MEASURED 2026-11-01 on PR #649, and the chain is written into the workflow
rather than being anyone's misjudgement:

  16:39  `qa` writes `qa-fail`
  16:41  detect_stalls reports `qa-fail-unaddressed`, fail_age 0.0h
         -> that kind is in `obliged`
  ->     agent-steward.yml:306 reads OBLIGED_ACTIONS > 0 and demands proof of
         an action taken since the run began
  ->     the steward correctly has none: a fix cannot exist two minutes after
         the verdict that asks for it
  ->     agent-steward.yml:322 reads `cycles=0, issues=0` and logs
         "NOTHING happened - Waking chief."
  ->     chief rules "not a stall, normal operation" and produces no act

Across four PRs that day 26 comments were written; six were the steward's and
five were chief's, and all eleven produced no act. chief ruled three times on
one unchanged SHA. This is issue #580 -- "detect_stalls counts stalls no cycle
can act on as OBLIGED, so the steward is accused of inaction it correctly
took" -- reproduced from the other end.

EVERY OTHER THRESHOLD IN THAT FILE IS `hours`. The verdict age was the single
quantity compared against nothing, which is why the floor is `hours` and not a
new constant: a second number to keep in step is a second number to get wrong.

WHAT THIS MUST NOT DO is hide a real one. A verdict older than the floor with
nothing pushed since is exactly the stall the kind exists for, and
`test_an_old_unaddressed_verdict_is_still_a_stall` is the guard on that.
"""
from __future__ import annotations

import importlib.util
import pathlib
from datetime import datetime, timedelta, timezone

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)

SRC = (pathlib.Path(__file__).resolve().parents[1]
       / "scripts" / "detect_stalls.py").read_text(encoding="utf-8")


def _pr(number: int, *, hours: float, labels: list[str]) -> dict:
    created = datetime.now(timezone.utc) - timedelta(hours=hours)
    return {
        "number": number, "title": f"PR {number}", "isDraft": False,
        "labels": [{"name": n} for n in labels],
        "headRefName": f"issue/{number - 10}-whatever",
        "headRefOid": f"sha{number}",
        "createdAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _run(monkeypatch, prs, *, fail_age: float, head_age: float, hours: float = 4,
         split: tuple[int, int] = (0, 1)):
    """`find_stalls` with the three API reads it makes controlled.

    `split` is `(non_merge, merge)` commits since the verdict, and it is a
    PARAMETER rather than a fixture constant because the default `(0, 1)` --
    merges only -- is the "still unaddressed" case. Hard-coding it made a test
    that meant to check a landed FIX assert against a merge, and pass for the
    wrong reason.
    """
    import json as _json
    monkeypatch.setattr(detect_stalls, "latest_checks",
                        lambda sha: {"gates": "success"})
    monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: True)
    monkeypatch.setattr(detect_stalls, "qa_fail_age", lambda n: fail_age)
    monkeypatch.setattr(detect_stalls, "head_pushed_hours_ago", lambda n: head_age)
    monkeypatch.setattr(detect_stalls, "post_verdict_commits", lambda n, a: split)

    def gh(*args):
        if args[0] == "pr" and args[1] == "list":
            return _json.dumps(prs)
        return "[]"

    monkeypatch.setattr(detect_stalls, "gh", gh)
    return detect_stalls.find_stalls(hours)


def _kinds(stalls) -> set[str]:
    return {s["kind"] for s in stalls}


# --- the defect, executed ---------------------------------------------------

def test_a_verdict_written_minutes_ago_is_not_a_stall(monkeypatch):
    """THE #649 CASE. fail_age 0.03h is two minutes: nobody could have pushed a
    fix, so the absence of one carries no information."""
    stalls = _run(monkeypatch, [_pr(649, hours=9, labels=["qa-fail"])],
                  fail_age=0.03, head_age=9)
    assert "qa-fail-unaddressed" not in _kinds(stalls), (
        f"a two-minute-old verdict was reported as a stall: {_kinds(stalls)}"
    )


def test_it_produces_no_obliged_action_for_a_fresh_verdict(monkeypatch):
    """The obliged count is what `agent-steward.yml:306` reads, and a non-zero
    one is what demands proof of an action and eventually wakes chief. This is
    the assertion that maps to the three saved invocations."""
    stalls = _run(monkeypatch, [_pr(649, hours=9, labels=["qa-fail"])],
                  fail_age=0.03, head_age=9)
    obliged = [s for s in stalls if s["kind"] in {
        "draft-never-readied", "no-qa-verdict", "mergeable-but-open",
        "steward-ineffective", "qa-fail-unaddressed", "qa-fail-refixed",
        "draft-held-by-qa-fail", "pr-conflicting"} and s.get("agent_pushable", True)]
    assert obliged == [], f"a fresh verdict still demands an action: {obliged}"


# --- and it must not hide a real one ----------------------------------------

def test_an_old_unaddressed_verdict_is_still_a_stall(monkeypatch):
    """THE GUARD ON THE GUARD. A floor that swallowed the real case would be
    strictly worse than the noise it removes -- four PRs sat qa-fail and
    invisible for 12-64h before this kind existed at all."""
    stalls = _run(monkeypatch, [_pr(700, hours=40, labels=["qa-fail"])],
                  fail_age=30, head_age=35)
    assert "qa-fail-unaddressed" in _kinds(stalls), _kinds(stalls)


def test_the_floor_is_exactly_the_threshold_everything_else_uses(monkeypatch):
    """`hours`, not a new constant. A second number to keep in step is a second
    number to get wrong, and this file already had one threshold."""
    assert "fail_age < hours" in SRC, (
        "the floor uses something other than the run's own threshold"
    )
    # just under and just over, with the same PR
    pr = [_pr(701, hours=40, labels=["qa-fail"])]
    assert "qa-fail-unaddressed" not in _kinds(
        _run(monkeypatch, pr, fail_age=3.9, head_age=35, hours=4))
    assert "qa-fail-unaddressed" in _kinds(
        _run(monkeypatch, pr, fail_age=4.1, head_age=35, hours=4))


def test_a_custom_threshold_moves_the_floor_with_it(monkeypatch):
    """`--hours N` is a real flag, and a floor that ignored it would make the
    flag lie about what the run measured."""
    pr = [_pr(702, hours=40, labels=["qa-fail"])]
    assert "qa-fail-unaddressed" not in _kinds(
        _run(monkeypatch, pr, fail_age=8, head_age=35, hours=12))
    assert "qa-fail-unaddressed" in _kinds(
        _run(monkeypatch, pr, fail_age=13, head_age=35, hours=12))


def test_the_suppression_is_reported_and_not_silent(monkeypatch, capsys):
    """A finding dropped where nobody can see it is a detector lying by
    omission, and this file's own comments say every decision must be readable
    afterwards."""
    _run(monkeypatch, [_pr(649, hours=9, labels=["qa-fail"])],
         fail_age=0.5, head_age=9)
    out = capsys.readouterr().out
    assert "#649" in out and "floor" in out, out


def test_an_unreadable_verdict_time_is_still_reported(monkeypatch):
    """`None` means "could not read", which is not "fresh". Collapsing the two
    is the exact defect this file fixed for permissions: "could not ask" must
    never resolve to a verdict in either direction."""
    stalls = _run(monkeypatch, [_pr(703, hours=40, labels=["qa-fail"])],
                  fail_age=None, head_age=35)
    assert "qa-fail-unreadable" in _kinds(stalls), _kinds(stalls)


# --- the floor's PLACEMENT, which was wrong when it first landed ------------

def test_a_fix_pushed_inside_the_window_is_reported_immediately(monkeypatch):
    """THE REGRESSION #659 SHIPPED, executed.

    The floor's premise is "nobody could have fixed it yet". When a fix HAS
    landed the premise is false, so the floor must not apply -- but it sat
    FIRST in the if/elif chain, ahead of the `head_age < fail_age` arm, and
    suppressed the finding for the whole window.

    The cost was not noise, it was silence on every path at once:
    `qa-on-green` declines a `qa-fail` PR by design, the steward runs twice a
    day, and this detector was the only thing left that could notice a fix had
    landed. Measured on PRs #649 and #654, whose round-2 fixes went up ~2h
    after their verdicts.

    `fail_age=1` with `head_age=0.2` is a fix pushed 48 minutes after a verdict
    written an hour ago -- well inside a 4h floor.
    """
    stalls = _run(monkeypatch, [_pr(649, hours=9, labels=["qa-fail"])],
                  fail_age=1.0, head_age=0.2, split=(1, 0))   # one real fix commit
    assert "qa-fail-refixed" in _kinds(stalls), (
        f"a landed fix was suppressed by the freshness floor: {_kinds(stalls)}"
    )


def test_merges_pushed_inside_the_window_still_read_as_unaddressed(monkeypatch):
    """The other half of the landed-fix arm must survive too: a merge forward
    is not a fix, and it must not be reported as one just because it is new."""
    stalls = _run(monkeypatch, [_pr(650, hours=9, labels=["qa-fail"])],
                  fail_age=1.0, head_age=0.2, split=(0, 2))   # two merges, no fix
    assert "qa-fail-unaddressed" in _kinds(stalls), _kinds(stalls)


def test_the_floor_is_reached_only_after_the_landed_fix_arm():
    """Static, and it is what makes the two cases above hold for shapes this
    file does not enumerate: the chain's ORDER is the guarantee."""
    landed = SRC.index("elif head_age < fail_age:")
    floor = SRC.index("elif fail_age < hours:")
    assert landed < floor, (
        "the freshness floor is tested before the landed-fix arm again; a fix "
        "pushed inside the window will be suppressed for the whole window"
    )


def test_the_floor_says_that_nothing_was_pushed(monkeypatch, capsys):
    """The message has to state the premise it is relying on, or the next
    reader cannot tell this from "a fix landed and we ignored it"."""
    _run(monkeypatch, [_pr(651, hours=9, labels=["qa-fail"])],
         fail_age=0.5, head_age=9)
    out = capsys.readouterr().out
    assert "nothing pushed" in out, out
