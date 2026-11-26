"""#1221: a pr-gates run agent-merge dispatches on main is reported, and the wiring that
carries it. Measured 2026-11-18 by steward: GitHub delivered `workflow_run` to
main-red-report for 1 of 20 dispatched `main` runs, so a red merge result went unreported.
Also pins the measurement wiring the same session PR added (#1205, #1409, #974, #1065)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
_spec = importlib.util.spec_from_file_location("await_main_gates", ROOT / "scripts" / "await_main_gates.py")
amg = importlib.util.module_from_spec(_spec)
sys.modules["await_main_gates"] = amg
_spec.loader.exec_module(amg)

AFTER = amg._ts("2026-11-25T14:06:00Z")
SHA = "a" * 40


def run(rid, created, status="completed", conclusion="success"):
    return {"id": rid, "created_at": created, "status": status, "conclusion": conclusion,
            "head_branch": "main", "head_sha": SHA, "html_url": f"https://github.com/o/r/actions/runs/{rid}"}


class Gh:
    def __init__(self, seq, steps=None):
        self.seq = list(seq)        # one runs list per poll; the last repeats
        self.steps = steps or {}    # run id -> list of steps in its one job (default: one step ran)

    def __call__(self, args):
        url = next(a for a in args if a.startswith("repos/"))
        if "/jobs" in url:
            rid = int(url.split("/runs/")[1].split("/")[0])
            return json.dumps({"jobs": [{"steps": self.steps.get(rid, [{"name": "Set up job"}])}]})
        runs = self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]
        return json.dumps({"workflow_runs": runs})


def test_waits_for_the_dispatched_run_and_describes_it():
    gh = Gh([[], [run(5, "2026-11-25T14:06:03Z", "queued", None)],
             [run(5, "2026-11-25T14:06:03Z", "completed", "failure")]])
    rc, r, why = amg.await_run(gh, "o/r", AFTER, sleep=lambda s: None)
    assert rc == 0 and r["id"] == 5 and "failure" in why


def test_a_run_from_before_the_merge_is_never_taken():
    gh = Gh([[run(4, "2026-11-25T14:05:00Z")]])
    rc, r, why = amg.await_run(gh, "o/r", AFTER, sleep=lambda s: None, find_wait=60)
    assert rc == 1 and r is None and "no dispatched" in why


def test_a_replaced_pending_run_is_not_a_red_main():
    """#1284's shape: a later merge's dispatch replaced the pending run, which concluded
    cancelled having run nothing."""
    gh = Gh([[run(5, "2026-11-25T14:06:03Z", conclusion="cancelled"),
              run(6, "2026-11-25T14:09:00Z", "in_progress", None)]], steps={5: []})
    rc, r, why = amg.await_run(gh, "o/r", AFTER, sleep=lambda s: None)
    assert rc == 0 and r is None and "before any step ran" in why


def test_a_timed_out_run_with_a_newer_run_behind_it_is_still_reported():
    """#1486: the old 'a newer run exists' test swallowed a run that TIMED OUT with the next
    merge's run queued behind it -- exactly the case #461 exists for. It ran steps."""
    gh = Gh([[run(5, "2026-11-25T14:06:03Z", conclusion="cancelled"),
              run(6, "2026-11-25T14:09:00Z", "in_progress", None)]])
    rc, r, _ = amg.await_run(gh, "o/r", AFTER, sleep=lambda s: None)
    assert rc == 0 and r["id"] == 5 and r["conclusion"] == "cancelled"


def test_an_unreadable_job_list_reports_rather_than_swallows():
    class Broken(Gh):
        def __call__(self, args):
            if any("/jobs" in a for a in args):
                raise RuntimeError("HTTP 502")
            return super().__call__(args)
    rc, r, _ = amg.await_run(Broken([[run(5, "2026-11-25T14:06:03Z", conclusion="cancelled")]]),
                             "o/r", AFTER, sleep=lambda s: None)
    assert rc == 0 and r["id"] == 5


def test_a_run_that_never_completes_times_out_loudly():
    gh = Gh([[run(5, "2026-11-25T14:06:03Z", "in_progress", None)]])
    rc, _, why = amg.await_run(gh, "o/r", AFTER, sleep=lambda s: None, max_wait=90)
    assert rc == 1 and "did not complete" in why


def test_main_writes_the_four_facts_and_validates_its_input(tmp_path, monkeypatch):
    env = tmp_path / "env"
    env.write_text("")
    monkeypatch.setenv("GH_REPO", "o/r")
    monkeypatch.setenv("GITHUB_ENV", str(env))
    monkeypatch.setenv("AFTER", "2026-11-25T14:06:00Z; rm -rf /")
    assert amg.main(["x"], gh=Gh([[]]), sleep=lambda s: None) == 2
    monkeypatch.setenv("AFTER", "2026-11-25T14:06:00Z")
    assert amg.main(["x"], gh=Gh([[run(5, "2026-11-25T14:06:03Z", conclusion="failure")]]),
                    sleep=lambda s: None) == 0
    assert env.read_text() == (f"GATES_SHA={SHA}\nGATES_URL=https://github.com/o/r/actions/runs/5\n"
                               "GATES_RUN_ID=5\nGATES_CONCLUSION=failure\n")


def _doc(name):
    return yaml.safe_load((WF / name).read_text())


def test_agent_merge_dispatches_the_reporter_with_the_time_before_the_gates_dispatch():
    step = next(s for s in _doc("agent-merge.yml")["jobs"]["merge"]["steps"]
                if s.get("name") == "Gate the merge result on main")
    run_ = step["run"]
    assert run_.index("after=$(") < run_.index("gh workflow run pr-gates.yml")
    # #1487: GitHub's clock (the Date header of an API call), the runner's only as a fallback.
    assert run_.index("gh api -i rate_limit") < run_.index("after=$(")
    assert 'gh workflow run main-red-report.yml --repo "$GH_REPO" --ref main -f after="$after"' in run_


def test_the_reporter_waits_on_its_dispatch_leg_and_reports_from_the_same_step():
    doc = _doc("main-red-report.yml")
    on = doc.get("on") or doc[True]
    assert on["workflow_dispatch"]["inputs"]["after"]["required"] is True
    job = doc["jobs"]["report"]
    assert job["if"].startswith("github.event_name == 'workflow_dispatch' ||")
    steps = {s.get("name"): s for s in job["steps"]}
    wait = steps["Wait for the dispatched pr-gates run on main"]
    assert wait["run"] == "python3 scripts/await_main_gates.py" and wait["env"]["AFTER"] == "${{ inputs.after }}"
    rep = steps["File, append to, or close the main-red sentinel"]
    assert rep["if"] == "github.event_name == 'workflow_run' || env.GATES_RUN_ID != ''"
    assert rep["env"]["RUN_ID"] == "${{ github.event.workflow_run.id || env.GATES_RUN_ID }}"
    assert job["timeout-minutes"] * 60 > amg.MAX_WAIT_S + amg.FIND_WAIT_S


def test_the_measurement_wiring_is_in_place():
    measure = _doc("agent-measure.yml")["jobs"]["measure"]
    assert measure["steps"][0]["with"]["fetch-depth"] == 0
    sync = _doc("agent-sync.yml")
    first = next(j for j in sync["jobs"].values())["steps"][0]
    assert first["uses"].startswith("actions/checkout") and first["with"]["fetch-depth"] == 0
    names = {s.get("name"): s for s in measure["steps"]}
    pull = names["Pull the numbers"]["run"]
    assert "fetch_ga4.py --days 28 --trend > /tmp/ga4-trend.json" in pull
    kundli = names["Count fresh kundli submissions"]
    assert kundli["continue-on-error"] is True and "collect_kundli_submissions.py" in kundli["run"]
    idx = names["Inspect index status"]
    assert idx["continue-on-error"] is True and "fetch_index_status.py" in idx["run"]
    order = list(names)
    assert order.index("Pull the numbers") < order.index("Inspect index status"), "needs gsc-all.json"
    assert "cp -f /tmp/ga4-trend.json /tmp/measure/" in names["Persist the measurement"]["run"]
