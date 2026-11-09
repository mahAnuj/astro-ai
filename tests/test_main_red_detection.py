"""A red `main` must be seen, by two routes (2026-11-09).

#797 changed the `today_iso` fixture to the IST day at 17:28Z on 2026-11-08.
A strip-cache test keyed on the UTC date then failed from 18:30Z to 24:00Z --
on `main` and on all seven open PRs -- and nothing reported it:

  1. agent-merge merges with GITHUB_TOKEN, whose push starts no workflow, so
     `pr-gates` never ran on the merge commit and `main-red-report.yml` had
     nothing to report. Fixed by a post-merge dispatch, a daily evening
     schedule inside the IST/UTC skew window, and a reporter that accepts both.
  2. Seven PRs red on one test read as seven unrelated problems. Fixed by
     `collect_gate_failures.py` and the detector's `main-red-suspected`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime, timedelta, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
NOW = datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc)
TEST = "tests/test_panchang_strip_cache.py::test_eviction_is_bounded_and_keeps_what_matters"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


col = _load("collect_gate_failures")
det = _load("detect_ops_regressions")


def _doc(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text())


def _on(doc: dict) -> dict:
    return doc[next(k for k in doc if str(k) in ("on", "True"))]


def _steps(doc: dict, job: str) -> list[dict]:
    return doc["jobs"][job]["steps"]


# --- route 1: `main` is gated after a loop merge, and daily ------------------

def test_pr_gates_sweeps_main_daily_inside_the_ist_utc_skew_window():
    crons = [c["cron"] for c in _on(_doc("pr-gates.yml")).get("schedule") or []]
    assert crons, "pr-gates has no schedule, so a merge nothing pushed is never gated"
    minute, hour = (int(x) for x in crons[0].split()[:2])
    # 18:30Z-24:00Z is when the IST date is a day ahead of the UTC date. A
    # daily run outside it would have passed on 2026-11-08 like every PR gate did.
    assert 18 * 60 + 30 <= hour * 60 + minute < 24 * 60, (
        f"cron {crons[0]!r} runs outside 18:30-24:00 UTC, where #797's defect was invisible")


def _scope_script() -> str:
    step = next(s for s in _steps(_doc("pr-gates.yml"), "gates") if s.get("id") == "scope")
    return step["run"].replace("${{ github.event.pull_request.base.sha }}", "")


def _run_scope(tmp_path, event: str, ref: str) -> str:
    out = tmp_path / "out"
    out.write_text("")
    env = {**os.environ, "EVENT_NAME": event, "GITHUB_REF": ref,
           "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(tmp_path / "sum")}
    # An empty git repo with one docs-only commit: a diff-scoped run reads it
    # as code=false, which is exactly what a sweep of `main` must not do.
    repo = tmp_path / "r"
    repo.mkdir()
    g = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*g, "init", "-q"], check=True)
    for i in range(2):
        (repo / "README.md").write_text(str(i))
        subprocess.run([*g, "add", "."], check=True)
        subprocess.run([*g, "commit", "-qm", str(i)], check=True)
    subprocess.run(["bash", "-e", "-c", _scope_script()], cwd=repo, env=env, check=True,
                   capture_output=True)
    return out.read_text()


def test_a_scheduled_run_gates_everything_even_after_a_docs_only_commit(tmp_path):
    assert "code=true" in _run_scope(tmp_path, "schedule", "refs/heads/main")


def test_a_dispatched_run_on_main_gates_everything(tmp_path):
    assert "code=true" in _run_scope(tmp_path, "workflow_dispatch", "refs/heads/main")


def test_a_dispatched_run_on_a_branch_is_still_scoped_by_its_diff(tmp_path):
    # #322's fallback dispatches against a PR branch; that stays diff-scoped.
    assert "code=false" in _run_scope(tmp_path, "workflow_dispatch", "refs/heads/feat/x")


def test_agent_merge_dispatches_pr_gates_on_main_after_a_merge():
    steps = _steps(_doc("agent-merge.yml"), "merge")
    step = next((s for s in steps
                 if re.search(r"gh workflow run pr-gates\.yml\b.*--ref main", s.get("run") or "")),
                None)
    assert step, "agent-merge never dispatches pr-gates on main, so a loop merge is never gated"
    assert step.get("continue-on-error") is True, "a failed dispatch must not mark a clean merge red"
    assert "steps.boundary.outputs.ok == 'true'" in step.get("if", ""), (
        "dispatch only after a merge actually happened")


def test_the_reporter_accepts_dispatched_and_scheduled_main_runs():
    cond = _doc("main-red-report.yml")["jobs"]["report"]["if"]
    for event in ("push", "schedule", "workflow_dispatch"):
        assert f'"{event}"' in cond, f"a `{event}` run of pr-gates on main is never reported"
    assert "head_branch == 'main'" in cond, "a branch dispatch (#322) must stay excluded"
    assert "pull_request" not in cond, "PR runs are reported on the PR, not as a red main"


# --- route 2: one test red on several PRs is a red main ----------------------

LOG = (f"2026-11-08T23:29:32.2469375Z \x1b[31mFAILED {TEST} - AssertionError: default-city entry was evicted\x1b[0m\n"
       "2026-11-08T23:29:32.2449526Z tests/test_feedback_email_escaping.py::test_storage_keeps_the_raw_text\n"
       f"2026-11-08T23:29:32.2470000Z FAILED {TEST} - again\n"
       "2026-11-08T23:29:32.2475680Z 1 failed, 2799 passed in 70.31s\n")


def test_failed_tests_reads_the_short_summary_only():
    assert col.failed_tests(LOG) == [TEST]


def _fake_gh(prs: dict[int, list[str] | None], unreadable: set[int] = frozenset()):
    """prs: number -> failing node ids (None = green). Job id == PR number."""
    def gh(args):
        url = args[1]
        if url.startswith("repos/o/r/pulls?"):
            return json.dumps([{"number": n, "head": {"sha": f"s{n}"}} for n in prs])
        m = re.search(r"head_sha=s(\d+)", url)
        if m:
            n = int(m.group(1))
            concl = "success" if prs[n] is None else "failure"
            return json.dumps({"workflow_runs": [
                {"id": n, "name": "PR gates", "conclusion": concl},
                {"id": 9000 + n, "name": "Agent merge", "conclusion": "failure"}]})
        m = re.search(r"runs/(\d+)/jobs", url)
        if m:
            n = int(m.group(1))
            assert n < 9000, "only gate workflows' jobs may be read"
            return json.dumps({"jobs": [{"id": n, "name": "gates", "conclusion": "failure"}]})
        m = re.search(r"jobs/(\d+)/logs", url)
        if m:
            n = int(m.group(1))
            if n in unreadable:
                raise RuntimeError("HTTP 403")
            return "".join(f"2026-11-08T00:00:00.0Z FAILED {t} - x\n" for t in prs[n])
        raise AssertionError(url)
    return gh


def test_collect_tallies_tests_across_prs_and_counts_unreadable_logs():
    doc = col.collect(_fake_gh({1: [TEST], 2: [TEST, "tests/a.py::own"], 3: None, 4: [TEST]},
                               unreadable={4}), "o/r", NOW)
    assert doc["red_prs"] == [1, 2, 4]
    assert doc["by_test"][0] == {"test": TEST, "prs": [1, 2]}
    assert {"test": "tests/a.py::own", "prs": [2]} in doc["by_test"]
    assert doc["fetch_failed"] == 1 and doc["logs_fetched"] == 2


def _find(tmp_path, monkeypatch, gates: dict | None):
    m = tmp_path / "measurements"
    m.mkdir()
    if gates is not None:
        (m / "gate_failures.json").write_text(json.dumps(gates))
    monkeypatch.setattr(det, "ROOT", tmp_path)
    monkeypatch.setattr(det, "MEASUREMENTS", m)
    return det.find(NOW)


def _gates(by_test, at=NOW, **kw):
    return {"generated_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"), "logs_fetched": 3,
            "fetch_failed": 0, "by_test": by_test, **kw}


def test_one_test_on_two_prs_is_a_red_main_finding(tmp_path, monkeypatch):
    found, _ = _find(tmp_path, monkeypatch, _gates([{"test": TEST, "prs": [799, 805]}]))
    hit = [f for f in found if f["kind"] == "main-red-suspected"]
    assert len(hit) == 1 and hit[0]["level"] == "red"
    assert TEST in hit[0]["detail"] and "#799" in hit[0]["detail"] and "#805" in hit[0]["detail"]


def test_a_failure_on_one_pr_is_that_prs_own_problem(tmp_path, monkeypatch):
    found, _ = _find(tmp_path, monkeypatch, _gates([{"test": TEST, "prs": [799]}]))
    assert not [f for f in found if f["kind"] == "main-red-suspected"]


def test_a_stale_tally_is_unreadable_not_a_finding(tmp_path, monkeypatch):
    found, unreadable = _find(tmp_path, monkeypatch, _gates(
        [{"test": TEST, "prs": [1, 2]}], at=NOW - timedelta(hours=det.STALE_HOURS + 1)))
    assert not [f for f in found if f["kind"] == "main-red-suspected"]
    assert any("gate_failures.json" in u for u in unreadable)


def test_all_log_fetches_failing_is_reported_as_unreadable(tmp_path, monkeypatch):
    _, unreadable = _find(tmp_path, monkeypatch, _gates([], logs_fetched=0, fetch_failed=5))
    assert any("job-log fetches failed" in u for u in unreadable)


def test_agent_measure_collects_gate_failures_before_the_lessons_ledger():
    names = [s.get("name") for s in _steps(_doc("agent-measure.yml"), "commit")]
    assert "Collect gate failures" in names, "nothing writes measurements/gate_failures.json"
    assert names.index("Collect gate failures") < names.index("Collect lessons"), (
        "the lessons step runs the detector, so the tally must be written first")
