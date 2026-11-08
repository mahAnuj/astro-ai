"""A held PR wakes chief the moment it is ready (2026-11-08, #788 waited hours).

agent-merge dispatches the steward once per head when it applies the hold, and
detect_stalls lets a ready held PR past its 4h age gate so that dispatch finds it."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime, timedelta, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("detect_stalls", ROOT / "scripts" / "detect_stalls.py")
ds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ds)


def _pr(labels, *, hours, draft=False):
    created = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"number": 900, "title": "t", "isDraft": draft, "labels": [{"name": n} for n in labels],
            "headRefName": "claude/x", "headRefOid": "sha900", "createdAt": created,
            "updatedAt": created, "mergeable": "MERGEABLE"}


def _detect(monkeypatch, pr, *, green=True):
    monkeypatch.setattr(ds, "gh", lambda *a: json.dumps([pr]) if a[:2] == ("pr", "list") else "[]")
    monkeypatch.setattr(ds, "latest_checks", lambda sha: {"gates": "success" if green else "pending"})
    monkeypatch.setattr(ds, "agent_pushable", lambda n: False)
    monkeypatch.setattr(ds, "boundary_paths", lambda n: {".github/workflows/x.yml"})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ds.main(["detect_stalls.py", "--hours", "4"])
    return buf.getvalue()


def test_a_ready_held_pr_minutes_old_is_reported_for_chief(monkeypatch):
    out = _detect(monkeypatch, _pr(["needs-human-review", "qa-pass"], hours=0.2))
    assert "boundary-hold-clearable" in out and "CHIEF_RULINGS=1" in out


def test_other_young_prs_are_still_skipped(monkeypatch):
    assert "CHIEF_RULINGS=1" not in _detect(monkeypatch, _pr(["qa-pass"], hours=0.2))
    assert "CHIEF_RULINGS=1" not in _detect(monkeypatch, _pr(["needs-human-review", "qa-fail"], hours=0.2))


def test_a_young_held_pr_whose_gates_are_not_green_raises_no_stall_at_all(monkeypatch):
    """Let past the age gate only to reach the boundary arm; with red or pending
    gates it must not fall through to any other arm while it is still young."""
    pr = {**_pr(["needs-human-review", "qa-pass"], hours=0.2), "mergeable": "CONFLICTING"}
    out = _detect(monkeypatch, pr, green=False)
    assert "pr-conflicting" not in out and "OBLIGED_ACTIONS=0" in out, out


# --- agent-merge's wake, executed with a fake gh -----------------------------

def _boundary_run():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-merge.yml").read_text())
    run = next(s["run"] for s in doc["jobs"]["merge"]["steps"] if s.get("name") == "Trust boundary")
    m = re.search(r"(woke=\$\(.*?\n          esac\n)", run, re.S)
    if not m:
        m = re.search(r"(woke=\$\(.*?\nesac\n)", run, re.S)
    assert m, "the wake block is no longer recognisable"
    return m.group(1)


def _wake(tmp_path, already):
    b = tmp_path / "bin"
    b.mkdir()
    (b / "gh").write_text(f"""#!/usr/bin/env bash
echo "gh $*" >> {tmp_path}/calls
case "$*" in
  *"/comments"*) echo '{already}' ;;
  *) : ;;
esac
""")
    (b / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "GH_REPO": "o/r",
           "PR_NUMBER": "900", "PR_SHA": "a" * 40}
    r = subprocess.run(["bash", "-c", _boundary_run()], env=env, capture_output=True, text=True)
    calls = (tmp_path / "calls").read_text() if (tmp_path / "calls").exists() else ""
    return r, calls


def test_the_first_hold_on_a_head_comments_first_then_wakes_the_steward(tmp_path):
    r, calls = _wake(tmp_path, 0)
    lines = calls.splitlines()
    comment = next(i for i, l in enumerate(lines) if l.startswith("gh pr comment"))
    dispatch = next(i for i, l in enumerate(lines) if "workflow run agent-steward.yml" in l)
    assert comment < dispatch, calls


def test_the_same_head_never_wakes_chief_twice(tmp_path):
    r, calls = _wake(tmp_path, 1)
    assert "workflow run agent-steward.yml" not in calls


def test_an_unreadable_marker_does_not_dispatch(tmp_path):
    r, calls = _wake(tmp_path, "oops")
    assert "workflow run agent-steward.yml" not in calls
