"""Measurement refreshes follow the loop, and measurement PRs skip the build (2026-11-09).

Measured 2026-11-05..09: `agent-measure`'s eight clock slots delivered ~4 runs a
day at irregular times, while what the collectors describe changes when a cycle
finishes. And `verify-build` ran the full suite over every measurement PR, so a
red `main` failed them all and they stacked (#800, #805 behind #797).
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
from datetime import datetime, timedelta, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
NOW = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)

_spec = importlib.util.spec_from_file_location("measure_due", ROOT / "scripts" / "measure_due.py")
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh(last_commit_ago=None, prs=()):
    def gh(args):
        url = args[1]
        if url.startswith("repos/o/r/commits?"):
            assert f"path={md.MARKER}" in url and "sha=main" in url
            return json.dumps([] if last_commit_ago is None else
                              [{"commit": {"committer": {"date": _iso(NOW - last_commit_ago)}}}])
        if url.startswith("repos/o/r/pulls?state=open"):
            return json.dumps([{"number": n, "user": {"login": who}, "head": {"ref": ref},
                                "created_at": _iso(NOW - ago)} for n, who, ref, ago in prs])
        raise AssertionError(url)
    return gh


# --- the debounce ------------------------------------------------------------

def test_scheduled_and_dispatched_runs_are_always_due():
    boom = lambda a: (_ for _ in ()).throw(AssertionError("must not query"))  # noqa: E731
    assert md.decide(boom, "o/r", "schedule", NOW)[0] is True
    assert md.decide(boom, "o/r", "workflow_dispatch", NOW)[0] is True


def test_a_cycle_right_after_a_measurement_does_not_refresh_again():
    due, why = md.decide(_gh(last_commit_ago=timedelta(minutes=20)), "o/r", "workflow_run", NOW)
    assert due is False and "20 min ago" in why


def test_an_open_measurement_pr_blocks_a_second_one():
    prs = [(805, md.PUBLISHER, "measurements/42535138094-1", timedelta(minutes=30))]
    due, why = md.decide(_gh(timedelta(hours=2), prs), "o/r", "workflow_run", NOW)
    assert due is False and "#805" in why


def test_a_stuck_measurement_pr_no_longer_blocks():
    prs = [(800, md.PUBLISHER, "measurements/42511112031-1", md.STUCK_AFTER + timedelta(minutes=1))]
    assert md.decide(_gh(timedelta(hours=5), prs), "o/r", "workflow_run", NOW)[0] is True


def test_a_human_pr_on_a_measurements_branch_name_does_not_block():
    prs = [(9, "mahAnuj", "measurements/x", timedelta(minutes=5))]
    assert md.decide(_gh(timedelta(hours=2), prs), "o/r", "workflow_run", NOW)[0] is True


def test_a_quiet_hour_after_a_cycle_refreshes():
    assert md.decide(_gh(timedelta(minutes=61)), "o/r", "workflow_run", NOW)[0] is True


def test_an_api_failure_fails_open(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GH_REPO", "o/r")
    monkeypatch.setenv("EVENT_NAME", "workflow_run")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))

    def broken(args):
        raise RuntimeError("HTTP 502")
    assert md.main(["x"], gh=broken, now=NOW) == 0
    assert out.read_text() == "due=true\n"


# --- agent-measure wiring ----------------------------------------------------

def _doc(name):
    return yaml.safe_load((WF / name).read_text())


def test_a_collector_run_cannot_cancel_the_analyst():
    assert _doc("agent-measure.yml")["concurrency"]["cancel-in-progress"] is False


def test_the_debounce_gates_every_later_step_of_the_commit_job():
    steps = _doc("agent-measure.yml")["jobs"]["commit"]["steps"]
    i = next(n for n, s in enumerate(steps) if s.get("id") == "due")
    assert "scripts/measure_due.py" in steps[i]["run"]
    assert steps[i]["env"]["EVENT_NAME"] == "${{ github.event_name }}"
    ungated = [s.get("name") or s.get("uses") for s in steps[i + 1:]
               if s.get("if") != "steps.due.outputs.due == 'true'"]
    assert not ungated, f"these still run when no refresh is due: {ungated}"


# --- verify-build scope ------------------------------------------------------

def _scope_script():
    steps = _doc("verify-build.yml")["jobs"]["build-gates"]["steps"]
    return next(s for s in steps if s.get("id") == "scope")["run"]


def _scope(tmp_path, files, on_main=False):
    repo = tmp_path / "r"
    repo.mkdir()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*g, "init", "-q", "-b", "main"], check=True)
    (repo / "README.md").write_text("x")
    subprocess.run([*g, "add", "."], check=True)
    subprocess.run([*g, "commit", "-qm", "base"], check=True)
    subprocess.run([*g, "update-ref", "refs/remotes/origin/main", "main"], check=True)
    if not on_main:
        subprocess.run([*g, "checkout", "-qb", "measurements/1-1"], check=True)
    for f in files:
        (repo / f).parent.mkdir(parents=True, exist_ok=True)
        (repo / f).write_text("y")
    if files:
        subprocess.run([*g, "add", "."], check=True)
        subprocess.run([*g, "commit", "-qm", "change"], check=True)
    if on_main:
        subprocess.run([*g, "update-ref", "refs/remotes/origin/main", "main"], check=True)
    out = tmp_path / "out"
    out.write_text("")
    env = {**os.environ, "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(tmp_path / "s")}
    subprocess.run(["bash", "-e", "-c", _scope_script()], cwd=repo, env=env, check=True,
                   capture_output=True)
    return out.read_text().strip()


def test_a_measurements_only_branch_skips_the_build(tmp_path):
    assert _scope(tmp_path, ["measurements/loop.json", "measurements/agents.json"]) == "build=false"


def test_a_branch_touching_anything_else_builds(tmp_path):
    assert _scope(tmp_path, ["measurements/loop.json", "src/astro_ai/x.py"]) == "build=true"


def test_a_lookalike_path_builds(tmp_path):
    assert _scope(tmp_path, ["measurements-extra/x.json"]) == "build=true"


def test_main_itself_always_builds(tmp_path):
    # A push to main diffs empty against its own merge base: fail safe, build.
    assert _scope(tmp_path, ["measurements/loop.json"], on_main=True) == "build=true"


def test_every_step_after_the_scope_is_gated_on_it():
    steps = _doc("verify-build.yml")["jobs"]["build-gates"]["steps"]
    i = next(n for n, s in enumerate(steps) if s.get("id") == "scope")
    ungated = [s.get("name") or s.get("uses") for s in steps[i + 1:]
               if s.get("if") != "steps.scope.outputs.build == 'true'"]
    assert not ungated, f"these still run on a measurements-only PR: {ungated}"
