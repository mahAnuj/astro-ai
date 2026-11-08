"""A merge re-dispatches the sweep (2026-11-07).

The sweep takes one PR per run and the */30 cron is throttled to roughly every
6 hours. #749 and #750 sat fully cleared and mergeable while the 22:16 sweep
took #706 and no sweep ran for 2.5h+. These pin the step that drains the rest."""
from __future__ import annotations

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "agent-merge.yml"


def _steps():
    doc = yaml.safe_load(WF.read_text())
    return doc["jobs"]["merge"]["steps"]


def _step(name):
    return next(s for s in _steps() if s.get("name") == name)


def test_a_successful_merge_dispatches_another_sweep():
    s = _step("Sweep again after a merge")
    assert "gh workflow run agent-merge.yml" in s["run"] and "--ref main" in s["run"]


def test_only_a_run_that_merged_dispatches_so_the_chain_ends():
    cond = _step("Sweep again after a merge")["if"]
    assert "steps.boundary.outputs.ok == 'true'" in cond and "success()" in cond


def test_it_runs_after_the_merge_and_cannot_turn_a_merged_pr_red():
    names = [s.get("name") for s in _steps()]
    assert names.index("Sweep again after a merge") > names.index("Merge")
    s = _step("Sweep again after a merge")
    assert s.get("continue-on-error") is True and "${{" not in s["run"]


def test_a_dispatched_run_sweeps():
    """The re-dispatch is useless unless workflow_dispatch enters sweep mode."""
    run = _step("Find the pull request")["run"]
    assert '[ "$EVENT_NAME" = "workflow_dispatch" ]' in run
