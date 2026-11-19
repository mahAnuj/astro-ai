"""pr-gates runs as parallel jobs (2026-11-19, owner: "there is no way to speed the gates?").

One job ran everything in sequence: median ~14 min per PR, 28-45 min for a full sweep. Now
`scope` decides once; `suite`, four `mutants` shards and `verify` run side by side; `gates`, the
required check, waits for them. These pin the properties that keep that as strict as before.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "pr-gates.yml"
PARALLEL = ("scope", "suite", "mutants", "verify")


def _jobs() -> dict:
    return yaml.safe_load(WF.read_text())["jobs"]


def test_every_new_job_holds_no_token_scope():
    """verify_workflow_permissions passes a new job only if it grants nothing, and a gate
    that holds no scope cannot relax anything."""
    jobs = _jobs()
    for name in PARALLEL:
        assert jobs[name]["permissions"] == {}, name


def test_gates_waits_for_every_job_and_runs_even_when_one_failed():
    g = _jobs()["gates"]
    assert set(g["needs"]) == set(PARALLEL)
    assert g["if"] == "always()", "a failed job must give a RED gates, never a skipped one"


def test_no_gate_job_can_be_skipped_as_a_whole():
    """agent-merge counts a `skipped` check as not green, and a skipped job would also hide
    behind `gates` if the assertion were loose. Jobs always run; their STEPS skip."""
    jobs = _jobs()
    for name in PARALLEL:
        assert "if" not in jobs[name], name


def test_gates_fails_unless_every_job_succeeded():
    steps = {s.get("name"): s for s in _jobs()["gates"]["steps"]}
    check = steps["Every gate job succeeded"]
    assert "toJSON(needs)" in check["env"]["RESULTS"]
    assert '!= "success"' in check["run"] and "sys.exit(1)" in check["run"]
    assert "if" not in check, "the check must run on every outcome the job reaches"


def test_the_marker_main_red_report_reads_keeps_its_meaning():
    steps = [s for j in _jobs().values() for s in j["steps"] if s.get("name") == "GATES ASSERTED"]
    assert len(steps) == 1 and steps[0]["if"] == "needs.scope.outputs.code == 'true'"


def test_the_sweep_is_split_four_ways_on_both_branches():
    m = _jobs()["mutants"]
    assert m["strategy"]["matrix"]["shard"] == [0, 1, 2, 3] and m["strategy"]["fail-fast"] is False
    step = next(s for s in m["steps"] if s.get("name") == "Prove the suite can fail")
    assert step["run"].count('--shard "$SHARD/4"') == 2, "the PR leg AND the full-sweep leg"
    assert step["env"]["SHARD"] == "${{ matrix.shard }}"


def test_a_bad_shard_is_refused_not_run():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/mutate_behaviour_suite.py"), "--shard", "4/4"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 2 and "--shard must be I/N" in r.stdout
