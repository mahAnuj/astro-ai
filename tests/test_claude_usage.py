"""scripts/collect_claude_usage.py -- how close the loop runs to its one Claude
Max subscription (owner, 2026-11-03). Measured that day: five-hour ~4%,
SEVEN-DAY 69%, so the weekly window binds; whether more parallel cycles are
affordable is read from this file, so a wrong number decides a real cost."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("collect_claude_usage",
                                               ROOT / "scripts" / "collect_claude_usage.py")
cu = importlib.util.module_from_spec(_spec)
sys.modules["collect_claude_usage"] = cu
_spec.loader.exec_module(cu)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def block(five, seven, status="allowed", ts="2026-11-03T03:52:00.0000000Z", seven_status="allowed"):
    """A rate_limit_info block exactly as the Actions log prints it: pretty-
    printed JSON, every line prefixed with a timestamp."""
    body = json.dumps({"rate_limit_info": {
        "status": status, "rateLimitType": "five_hour",
        "unifiedWindows": {
            "five_hour": {"utilization": five, "resetsAt": 1793694000, "status": status},
            "seven_day": {"utilization": seven, "resetsAt": 1793944800, "status": seven_status}}}},
        indent=2)
    inner = body.split("\n", 1)[1].rsplit("\n", 1)[0]      # drop the outer { }
    return "\n".join(f"{ts} {l}" for l in inner.splitlines()) + "\n"


def test_blocks_are_parsed_out_of_a_timestamped_log():
    log = "2026-11-03T03:51:00Z noise\n" + block(0.01, 0.68) + "x\n" + block(0.04, 0.69)
    b = cu.parse_blocks(log)
    assert len(b) == 2
    assert b[1]["unifiedWindows"]["seven_day"]["utilization"] == 0.69


def test_a_malformed_block_is_skipped_not_guessed():
    bad = '2026-11-03T03:52:00Z   "rate_limit_info": {\n2026-11-03T03:52:00Z     "status": \n2026-11-03T03:52:00Z   }\n'
    assert cu.parse_blocks(bad + block(0.02, 0.5)) [-1]["unifiedWindows"]["five_hour"]["utilization"] == 0.02


def test_a_run_is_summarised_by_its_WORST_state():
    s = cu.summarise(cu.parse_blocks(block(0.01, 0.60) + block(0.30, 0.71) + block(0.05, 0.65)))
    assert (s["five_hour"], s["seven_day"]) == (0.30, 0.71), "max per window, not the last"


def test_a_rejected_window_anywhere_makes_the_run_rejected():
    """The top-level `status` describes the five-hour limit (`rateLimitType`), so
    a SEVEN-DAY rejection shows only inside `unifiedWindows` -- the window that
    binds this subscription. Reading only the top level would miss the cap."""
    s = cu.summarise(cu.parse_blocks(block(0.2, 0.9) + block(0.05, 1.0, seven_status="rejected")))
    assert s["status"] == "rejected"


def test_a_top_level_rejection_is_noticed_too():
    s = cu.summarise(cu.parse_blocks(block(1.0, 0.5, status="rejected")))
    assert s["status"] == "rejected"


def test_no_utilization_at_all_is_no_reading():
    assert cu.summarise([{"status": "allowed"}]) is None


class FakeGh:
    """Serves runs, jobs and logs. Like gh 2.103 on a GitHub-hosted runner, it
    REFUSES a job-log fetch without `--allow-escape-sequences` (QA round 1 on
    #691) -- or, with `old_gh`, rejects the flag as unknown like an older gh."""

    def __init__(self, logs, old_gh=False, logs_fail=False):  # workflow -> list of log texts
        self.logs, self.calls, self.old_gh, self.logs_fail = logs, [], old_gh, logs_fail

    def __call__(self, args):
        self.calls.append(args)
        path = next(a for a in args[1:] if a.startswith("repos/"))
        if path.endswith("/logs"):
            flag = "--allow-escape-sequences" in args
            if self.logs_fail:
                raise RuntimeError("gh api: HTTP 403")
            if self.old_gh and flag:
                raise RuntimeError("gh api: unknown flag: --allow-escape-sequences")
            if not self.old_gh and not flag:
                raise RuntimeError("gh api: the response contains terminal escape sequences; "
                                   "pass --allow-escape-sequences")
        if "/actions/workflows/" in path:
            wf = path.split("/actions/workflows/")[1].split("/")[0]
            runs = [{"id": hash((wf, i)) % 10**9, "created_at": f"2026-11-03T0{i}:00:00Z"}
                    for i in range(len(self.logs.get(wf, [])))]
            return json.dumps(runs)
        if path.endswith("/jobs"):
            return json.dumps([int(path.split("/runs/")[1].split("/")[0])])
        if path.endswith("/logs"):
            jid = int(path.split("/jobs/")[1].split("/")[0])
            for wf, logs in self.logs.items():
                for i, l in enumerate(logs):
                    if hash((wf, i)) % 10**9 == jid:
                        return l
        raise RuntimeError("not found")


def test_collect_builds_a_time_series_across_workflows():
    gh = FakeGh({"agent-work.yml": [block(0.01, 0.60), block(0.04, 0.69)],
                 "agent-steward.yml": [block(0.02, 0.65)]})
    doc = cu.collect(gh, "o/r", NOW)
    assert len(doc["readings"]) == 3
    assert doc["peak_seven_day"] == 0.69
    assert doc["latest"]["at"] == max(r["at"] for r in doc["readings"])
    assert doc["rejected_runs"] == []
    assert cu.validate(doc) == []


def test_a_rejected_run_is_listed():
    gh = FakeGh({"agent-work.yml": [block(1.0, 0.99, status="rejected")]})
    assert len(cu.collect(gh, "o/r", NOW)["rejected_runs"]) == 1


def test_NOTHING_readable_writes_nothing_and_says_so(tmp_path, capsys):
    out = tmp_path / "claude_usage.json"
    out.write_text('{"previous": true}')
    rc = cu.main(["x", "--repo", "o/r", "--out", str(out)], gh=FakeGh({}), now=NOW)
    assert rc == 1 and json.loads(out.read_text()) == {"previous": True}
    assert "left standing" in capsys.readouterr().out


def test_a_written_file_validates(tmp_path):
    out = tmp_path / "u.json"
    rc = cu.main(["x", "--repo", "o/r", "--out", str(out)],
                 gh=FakeGh({"agent-work.yml": [block(0.04, 0.69)]}), now=NOW)
    assert rc == 0 and json.loads(out.read_text())["latest"]["seven_day"] == 0.69


def test_validate_rejects_an_impossible_utilization():
    assert cu.validate({"generated_at": "x", "latest": {}, "rejected_runs": [],
                        "readings": [{"run": 1, "five_hour": 7.0, "seven_day": 0.5}]})


def test_every_workflow_that_runs_claude_is_sampled():
    """A new Claude-backed workflow spends the same subscription; leaving it out
    would under-read the one number this file exists to give."""
    on_disk = {p.name for p in (ROOT / ".github" / "workflows").glob("*.yml")
               if "anthropics/claude-code-action" in p.read_text()}
    assert on_disk == set(cu.CLAUDE_WORKFLOWS)


def test_agent_measure_collects_it_without_new_permissions():
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-measure.yml").read_text())
    steps = doc["jobs"]["commit"]["steps"]
    names = [s.get("name") for s in steps]
    i = names.index("Collect Claude usage")
    assert steps[i].get("continue-on-error") is True
    assert "collect_claude_usage.py" in steps[i]["run"]
    assert i < names.index("Commit the measurement"), "must run before the publish"
    assert doc["jobs"]["commit"]["permissions"]["actions"] in ("read", "write")


def test_job_logs_are_fetched_with_allow_escape_sequences():
    """QA round 1 on #691: gh 2.103 refuses every job log without the flag, the
    collector swallowed it, and claude_usage.json was never written."""
    gh = FakeGh({"agent-work.yml": [block(0.04, 0.69)]})
    doc = cu.collect(gh, "o/r", NOW)
    assert doc and doc["latest"]["seven_day"] == 0.69
    assert any("--allow-escape-sequences" in c for c in gh.calls if c[-1].endswith("/logs"))


def test_an_older_gh_without_the_flag_is_retried_plainly():
    doc = cu.collect(FakeGh({"agent-work.yml": [block(0.04, 0.69)]}, old_gh=True), "o/r", NOW)
    assert doc and doc["latest"]["seven_day"] == 0.69


def test_every_FETCH_failing_is_reported_as_a_fetch_failure_not_as_empty_logs(tmp_path, capsys):
    out = tmp_path / "u.json"
    rc = cu.main(["x", "--repo", "o/r", "--out", str(out)],
                 gh=FakeGh({"agent-work.yml": [block(0.04, 0.69)]}, logs_fail=True), now=NOW)
    assert rc == 1 and not out.exists()
    msg = capsys.readouterr().out
    assert "FETCH failed" in msg and "403" in msg
