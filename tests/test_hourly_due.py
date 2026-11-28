"""2026-11-18: agent-queue's hourly steps (timers, liveness) no longer wait on
GitHub's cron, which fired once in fifteen slots on its first day. Every run
asks scripts/hourly_due.py; these drive it against an in-memory API."""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hourly_due", ROOT / "scripts" / "hourly_due.py")
hd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hd)

REPO = "o/r"
NOW = datetime(2026, 11, 18, 18, 0, 0, tzinfo=timezone.utc)


def _run(rid, started, status="completed"):
    return {"id": rid, "status": status, "run_started_at": started}


def _jobs(step_conclusion):
    steps = [] if step_conclusion is None else [{"name": hd.TIMER_STEP, "conclusion": step_conclusion}]
    return {"jobs": [{"steps": steps}]}


class Api:
    def __init__(self, runs, jobs=None, fail=False):
        self.runs, self.jobs, self.fail, self.calls = runs, jobs or {}, fail, []

    def __call__(self, args):
        self.calls.append(args)
        if self.fail:
            raise RuntimeError("HTTP 403")
        path = args[-1]
        if "/workflows/" in path:
            return json.dumps({"workflow_runs": self.runs})
        rid = int(path.split("/runs/")[1].split("/")[0])
        return json.dumps(self.jobs.get(rid, _jobs(None)))


def test_a_scheduled_run_is_always_due_and_reads_nothing():
    api = Api([])
    assert hd.decide(api, REPO, "schedule", "9", NOW)[0] is True
    assert api.calls == []


def test_an_event_wake_is_due_when_no_recent_run_fired_the_timers():
    """The defect: cron silent, wakes frequent, timers never ran."""
    api = Api([_run(1, "2026-11-18T17:30:00Z")], {1: _jobs("skipped")})
    assert hd.decide(api, REPO, "workflow_run", "9", NOW)[0] is True


def test_an_event_wake_is_not_due_when_a_run_fired_them_within_the_window():
    api = Api([_run(1, "2026-11-18T17:30:00Z")], {1: _jobs("success")})
    assert hd.decide(api, REPO, "workflow_dispatch", "9", NOW)[0] is False


def test_a_run_older_than_the_window_does_not_count():
    api = Api([_run(1, "2026-11-18T16:50:00Z")], {1: _jobs("success")})
    assert hd.decide(api, REPO, "workflow_run", "9", NOW)[0] is True


def test_this_run_and_unfinished_runs_do_not_count():
    api = Api([_run(9, "2026-11-18T17:59:00Z"), _run(2, "2026-11-18T17:50:00Z", "in_progress")],
              {9: _jobs("success"), 2: _jobs("success")})
    assert hd.decide(api, REPO, "workflow_run", "9", NOW)[0] is True


def test_an_unreadable_api_answers_due():
    """Both steps are idempotent; a missed hour is the defect, a duplicate is not."""
    assert hd.decide(Api([], fail=True), REPO, "workflow_run", "9", NOW)[0] is True


def _raw_api(runs_raw, jobs_raw=None):
    """Replies as literal strings: `Api` always json.dumps well-formed dicts, so
    it cannot express a list, null or scalar where the API promised an object."""
    def gh(args):
        if "/workflows/" in args[-1]:
            return runs_raw
        return jobs_raw if jobs_raw is not None else json.dumps(_jobs(None))
    return gh


def _assert_due_and_unreadable(gh):
    due, why = hd.decide(gh, REPO, "workflow_run", "9", NOW)
    # `due is True` alone also holds on the benign "no run fired them" path, so
    # the reason is what proves the reply was caught rather than read.
    assert due is True
    assert why.startswith("could not read recent runs"), why


@pytest.mark.parametrize("runs_raw", [
    "[]", "null", "5", '"x"',
    '{"workflow_runs":[1]}', '{"workflow_runs":{"a":1}}', '{"workflow_runs":"abc"}',
])
def test_a_runs_reply_of_the_wrong_shape_answers_due(runs_raw):
    """A non-dict at any level raises AttributeError from .get, which once escaped
    the handler and crashed the step, skipping timers and liveness (#1298)."""
    _assert_due_and_unreadable(_raw_api(runs_raw))


@pytest.mark.parametrize("jobs_raw", [
    "[]", "null", '{"jobs":[1]}', '{"jobs":[{"steps":[1]}]}', '{"jobs":[{"steps":"x"}]}',
])
def test_a_jobs_reply_of_the_wrong_shape_answers_due(jobs_raw):
    runs_raw = json.dumps({"workflow_runs": [_run(1, "2026-11-18T17:30:00Z")]})
    _assert_due_and_unreadable(_raw_api(runs_raw, jobs_raw))


def test_main_writes_the_output(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GH_REPO", REPO)
    monkeypatch.setenv("EVENT_NAME", "workflow_run")
    monkeypatch.setenv("THIS_RUN", "9")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    api = Api([_run(1, "2026-11-18T17:30:00Z")], {1: _jobs("success")})
    assert hd.main(["hourly_due.py"], gh=api, now=NOW) == 0
    assert out.read_text() == "due=false\n"


# --------------------------------------------------------------- wiring

def _steps():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-queue.yml").read_text())
    return {s.get("name"): s for s in doc["jobs"]["drain"]["steps"]}


def test_timers_and_liveness_do_not_depend_on_cron_alone():
    by = _steps()
    gate = by["Are the hourly steps due"]
    assert gate["id"] == "hourly" and "hourly_due.py" in gate["run"] and "if" not in gate
    assert gate["env"]["EVENT_NAME"] == "${{ github.event_name }}"
    for name in (hd.TIMER_STEP, "Liveness check, filed as ops findings"):
        cond = by[name]["if"]
        assert "steps.hourly.outputs.due == 'true'" in cond
        assert "event_name == 'schedule'" not in cond, f"{name} is back to cron-only"


def test_the_step_name_the_script_looks_for_exists():
    assert hd.TIMER_STEP in _steps()
