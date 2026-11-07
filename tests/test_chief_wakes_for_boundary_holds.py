"""A trust-boundary hold wakes chief even while a cycle runs (2026-11-06).

#706 sat held 52 hours: gates green and a QA PASS bound to its head. Every
steward run saw a QA round in flight, decided "chief has nothing to add while one
runs", and never woke chief, the only role that can clear such a hold. These
tests run the REAL accountability step's shell, with a fake `gh`."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-steward.yml"

SPEC = importlib.util.spec_from_file_location("detect_stalls", ROOT / "scripts" / "detect_stalls.py")
ds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ds)


def _step(name):
    doc = yaml.safe_load(WF.read_text())
    for job in doc["jobs"].values():
        for s in job.get("steps", []):
            if s.get("name") == name:
                return s
    raise AssertionError(name)


def _run_acted(tmp_path, stalls: str, inflight: bool):
    (tmp_path / "bin").mkdir()
    runs = '[{"createdAt":"2000-01-01T00:00:00Z","status":"%s"}]' % (
        "in_progress" if inflight else "completed")
    gh = tmp_path / "bin" / "gh"
    gh.write_text("#!/usr/bin/env bash\n"
                  'case "$1 $2" in\n'
                  f"  'run list') echo '{runs}' ;;\n"
                  "  'issue list') echo 0 ;;\n"
                  "esac\n")
    gh.chmod(0o755)
    stalls_file = pathlib.Path("/tmp/stalls.txt")
    saved = stalls_file.read_text() if stalls_file.exists() else None
    stalls_file.write_text(stalls)
    out = tmp_path / "out"
    out.write_text("")
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
           "GITHUB_OUTPUT": str(out), "GH_REPO": "o/r", "GH_TOKEN": "t",
           "SINCE": "2026-01-01T00:00:00Z"}
    try:
        r = subprocess.run(["bash", "-c", _step("Did the steward act on what it found?")["run"]],
                           env=env, capture_output=True, text=True)
    finally:
        if saved is None:
            stalls_file.unlink()
        else:
            stalls_file.write_text(saved)
    return out.read_text(), r.stdout


def test_a_boundary_hold_wakes_chief_while_a_cycle_is_in_flight(tmp_path):
    got, log = _run_acted(tmp_path, "OBLIGED_ACTIONS=1\nCHIEF_RULINGS=1\n", inflight=True)
    assert "ok=false" in got, log


def test_an_in_flight_cycle_still_stands_chief_down_when_no_hold_needs_ruling(tmp_path):
    """The 2026-11-02 behaviour stays for dispatches the queue carries."""
    got, log = _run_acted(tmp_path, "OBLIGED_ACTIONS=1\nCHIEF_RULINGS=0\n", inflight=True)
    assert "ok=true" in got, log


def _detect(monkeypatch, labels):
    import json
    from datetime import datetime, timedelta, timezone
    created = (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    pr = {"number": 706, "title": "t", "isDraft": False, "labels": [{"name": n} for n in labels],
          "headRefName": "partial/402-x", "headRefOid": "sha706", "createdAt": created,
          "updatedAt": created, "mergeable": "MERGEABLE"}
    monkeypatch.setattr(ds, "gh", lambda *a: json.dumps([pr]) if a[:2] == ("pr", "list") else "[]")
    monkeypatch.setattr(ds, "latest_checks", lambda sha: {"gates": "success"})
    monkeypatch.setattr(ds, "agent_pushable", lambda n: True)
    monkeypatch.setattr(ds, "boundary_paths", lambda n: {"src/astro_ai/prompts/ask.txt"})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ds.main(["detect_stalls.py", "--hours", "4"])
    return buf.getvalue()


def test_the_detector_counts_holds_only_chief_can_clear(monkeypatch):
    assert "CHIEF_RULINGS=1" in _detect(monkeypatch, ["needs-human-review", "qa-pass"])


def test_a_cleared_hold_is_not_counted(monkeypatch):
    out = _detect(monkeypatch, ["needs-human-review", "qa-pass", "chief-cleared"])
    assert "CHIEF_RULINGS=1" not in out


def test_chief_is_told_to_get_the_independent_round_itself():
    p = _step_with_prompt()
    assert "boundary-hold-clearable" in p and "--provenance independent" in p


def _step_with_prompt():
    doc = yaml.safe_load(WF.read_text())
    for job in doc["jobs"].values():
        for s in job.get("steps", []):
            p = (s.get("with") or {}).get("prompt", "")
            if "Dispatch the `chief` agent" in p and "steward just ran" in p:
                return p
    raise AssertionError("chief's accountability prompt not found")
