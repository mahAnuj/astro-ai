"""A trust-boundary hold must wake `chief` (#709).

WHY THIS TEST EXISTS
--------------------
`detect_stalls.py` emitted `boundary-hold-clearable` ("CHIEF decides this one")
for PR #706 and printed `OBLIGED_ACTIONS=0`, because the kind was missing from
the obliged set. `agent-steward.yml`'s accountability step exits at
`demanded == 0`, so chief was never invoked: three green steward runs, seven
hours, one unruled hold. Every component behaved as written.

The assertions with teeth are the ones on the COUNT, not the classification --
the classification was always right.

The workflow-PR case is pinned separately because `agent_pushable` is False for
it and the obvious fix (add the kind to the filtered set) would leave exactly
those holds unwoken. Chief rules without pushing.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "detect_stalls", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "detect_stalls.py")
detect_stalls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_stalls)


def _pr(number: int, labels: list[str], hours: float = 7) -> dict:
    from datetime import datetime, timedelta, timezone
    created = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "number": number, "title": f"PR {number}", "isDraft": False,
        "labels": [{"name": n} for n in labels],
        "headRefName": f"partial/{number - 300}-held", "headRefOid": f"sha{number}",
        "createdAt": created, "updatedAt": created, "mergeable": "MERGEABLE",
    }


def _run(monkeypatch, prs, *, workflow_prs=frozenset()) -> str:
    import json as _json

    def gh(*args):
        if args[0] == "pr" and args[1] == "list":
            return _json.dumps(prs)
        return "[]"

    monkeypatch.setattr(detect_stalls, "gh", gh)
    monkeypatch.setattr(detect_stalls, "latest_checks", lambda sha: {"gates": "success"})
    monkeypatch.setattr(detect_stalls, "agent_pushable", lambda n: n not in workflow_prs)
    monkeypatch.setattr(detect_stalls, "boundary_paths",
                        lambda n: {".github/workflows/x.yml"} if n in workflow_prs
                        else {"src/astro_ai/prompts/ask.txt"})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        detect_stalls.main(["detect_stalls.py", "--hours", "4"])
    return buf.getvalue()


HELD = ["needs-human-review", "qa-pass"]


def test_a_boundary_hold_is_reported_and_counts_as_an_obliged_action(monkeypatch):
    out = _run(monkeypatch, [_pr(706, HELD)])
    assert "boundary-hold-clearable" in out
    assert "OBLIGED_ACTIONS=1" in out, (
        f"the kind is emitted but not obliged, so chief is never woken:\n{out}")


def test_a_boundary_hold_on_a_workflow_pr_still_counts(monkeypatch):
    """No agent can PUSH here, but chief does not push -- it rules."""
    out = _run(monkeypatch, [_pr(631, HELD)], workflow_prs={631})
    assert "boundary-hold-clearable" in out
    assert "OBLIGED_ACTIONS=1" in out, (
        f"filtering this kind by agent_pushable leaves workflow holds unwoken:\n{out}")


def test_a_cleared_hold_is_no_longer_a_ruling_to_make(monkeypatch):
    """Once `chief-cleared` is on, the hold stops being reported. What remains is
    the ordinary mergeable-but-open arm, which is agent-merge's to finish."""
    out = _run(monkeypatch, [_pr(706, HELD + ["chief-cleared"])])
    assert "boundary-hold-clearable" not in out
    assert "mergeable-but-open" in out


def test_the_push_filter_still_applies_to_dispatch_kinds():
    """Widening for rulings must not widen for dispatches (#315)."""
    stalls = [{"kind": "no-qa-verdict", "agent_pushable": False},
              {"kind": "no-qa-verdict", "agent_pushable": True},
              {"kind": "human-owned-stall", "agent_pushable": False}]
    assert len(detect_stalls.obliged_actions(stalls)) == 1
