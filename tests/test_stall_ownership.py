"""A stall no agent can clear must not be blamed on the steward.

WHY THIS TEST EXISTS
--------------------
On 2026-10-11 the steward was handed five stalls, could clear none, and the
accountability step woke `chief`. chief ruled correctly — PR #315's diff touches
`.github/workflows/**`, the Claude App's token is refused on those pushes, so no
cycle can update that branch — and then noted that the detector would hand it the
same un-dispatchable stall twice a day forever, costing an invocation each time
to produce the same answer.

So ownership became a computed property rather than a judgement, and these tests
pin both halves of it:

  * an agent-pushable stall still escalates (`steward-ineffective`), because the
    steward genuinely failed to act on something it could have acted on;
  * a workflow-touching stall becomes `human-owned-stall` and is NOT counted as
    an obliged action, so it neither blames the steward nor wakes chief.

The second assertion is the one with teeth. Without it the classification could
be added, read correctly in prose, and still leave the count that actually gates
`chief` unchanged — which is precisely the defect shape this repo keeps finding:
a mechanism that is right with the wrong scope.
"""

from __future__ import annotations

import importlib.util
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)


def _pr(number: int, *, draft: bool, hours: float, labels: list[str]) -> dict:
    """One open PR as `gh pr list --json ...` returns it."""
    from datetime import datetime, timedelta, timezone
    created = datetime.now(timezone.utc) - timedelta(hours=hours)
    return {
        "number": number,
        "title": f"PR {number}",
        "isDraft": draft,
        "labels": [{"name": n} for n in labels],
        "headRefName": f"issue/{number - 10}-whatever",
        "headRefOid": f"sha{number}",
        "createdAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _install(monkeypatch, prs, *, workflow_prs: set[int]) -> None:
    """Stand in for every network call `find_stalls` makes."""
    monkeypatch.setattr(detect_stalls, "gh", lambda *a: "[]")
    monkeypatch.setattr(detect_stalls, "latest_checks", lambda sha: {"gates": "success"})
    monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: n not in workflow_prs)

    real = detect_stalls.find_stalls

    def patched(hours: float):
        import json as _json
        calls = {"n": 0}

        def gh(*args):
            # The first `gh` call in find_stalls is the PR list; later ones are
            # the agent-merge run history, which these cases do not exercise.
            if args[0] == "pr" and args[1] == "list":
                return _json.dumps(prs)
            calls["n"] += 1
            return "[]"

        monkeypatch.setattr(detect_stalls, "gh", gh)
        return real(hours)

    monkeypatch.setattr(detect_stalls, "find_stalls", patched)


def _kinds(stalls) -> set[str]:
    return {s["kind"] for s in stalls}


def test_agent_pushable_draft_still_escalates(monkeypatch):
    """The real failure stays a failure: PR #321's shape, 26h old, no workflow files."""
    prs = [_pr(331, draft=True, hours=26, labels=[])]
    _install(monkeypatch, prs, workflow_prs=set())
    stalls = detect_stalls.find_stalls(4)

    assert "draft-never-readied" in _kinds(stalls)
    assert "steward-ineffective" in _kinds(stalls), (
        "a draft an agent CAN ready, unreadied for 26h, is the steward failing to act")
    assert "human-owned-stall" not in _kinds(stalls)


def test_workflow_touching_pr_is_human_owned_not_steward_failure(monkeypatch):
    """PR #315's shape: gates green, no verdict, 46h — but the diff is workflow files."""
    prs = [_pr(325, draft=False, hours=46, labels=[])]
    _install(monkeypatch, prs, workflow_prs={325})
    stalls = detect_stalls.find_stalls(4)

    assert "no-qa-verdict" in _kinds(stalls), "the stall itself is still reported"
    assert "human-owned-stall" in _kinds(stalls)
    assert "steward-ineffective" not in _kinds(stalls), (
        "the steward is not ineffective for declining a push GitHub refuses it")


def test_human_owned_stall_does_not_count_as_an_obliged_action(monkeypatch):
    """The count that gates `chief` must agree with the classification.

    This is the assertion that stops the treadmill. The detector may classify
    perfectly and still wake chief on every run if `OBLIGED_ACTIONS` keeps
    counting the underlying `no-qa-verdict`.
    """
    prs = [_pr(325, draft=False, hours=46, labels=[])]
    _install(monkeypatch, prs, workflow_prs={325})

    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        detect_stalls.main(["detect_stalls.py", "--hours", "4"])
    out = buf.getvalue()

    assert "OBLIGED_ACTIONS=0" in out, (
        "a stall only a human can clear obliges the steward to nothing, so it must "
        f"not wake chief; got:\n{out}")


def test_obliged_count_is_emitted_in_json_mode(monkeypatch):
    """`agent-steward.yml` greps this line out of `--json` output specifically."""
    prs = [_pr(331, draft=True, hours=26, labels=[])]
    _install(monkeypatch, prs, workflow_prs=set())

    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        detect_stalls.main(["detect_stalls.py", "--hours", "4", "--json"])

    lines = [l for l in buf.getvalue().splitlines() if l.startswith("OBLIGED_ACTIONS=")]
    assert len(lines) == 1, f"the step does `grep -oE '^OBLIGED_ACTIONS=[0-9]+$' | tail -1`; got {lines}"
    assert int(lines[0].split("=")[1]) == 2, "the draft plus its steward-ineffective escalation"


def test_agent_pushable_fails_open(monkeypatch):
    """An API error must not silently reclassify a real stall as someone else's."""
    def boom(*a):
        raise RuntimeError("gh: HTTP 403")

    monkeypatch.setattr(detect_stalls, "gh", boom)
    assert detect_stalls.agent_pushable(999) is True, (
        "hiding a real stall is worse than spending a ruling on a false one")
