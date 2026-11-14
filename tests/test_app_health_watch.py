"""The live app's health is filed as issues after every cycle, not seen by no one (2026-11-14).

The owner saw "10.19% of LLM calls are erroring" on /admin/ops and asked whether
the monitoring agent reported it. It had not: the detector runs from a checkout
and lists the error rate, exhaustion, 413s and fallbacks as NOT_COVERED, and
the only bucket reader was the once-a-day analyst. Now the steward, which runs
after every agent-work cycle, reads the bucket and files the dashboard's own
product alerts.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from astro_ai import ops_data

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


watch = _load("watch_app_health", ROOT / "scripts" / "watch_app_health.py")
fo = _load("file_ops_findings_t", ROOT / "scripts" / "file_ops_findings.py")
tfo = _load("test_file_ops_findings_t", ROOT / "tests" / "test_file_ops_findings.py")

APP = {"ok": True, "measured": True, "days": 7, "calls": 6426, "errors": 655, "error_rate": 10.19,
       "exhausted": 250, "too_large": 0, "fallback_rate": 0.0, "peak_day_pct": None,
       "store": "gcs:shubhagya-cache-us"}


def view_of(by_days):
    return lambda days: {**APP, **by_days[days], "days": days}


# --- what is raised ----------------------------------------------------------

def test_todays_error_rate_is_filed_with_the_dashboards_own_words():
    doc = watch.evaluate(view_of({1: {"calls": 400, "errors": 41, "error_rate": 10.25}, 7: {}}))
    assert doc["ok"] and doc["days"] == 1
    kinds = {f["kind"]: f for f in doc["findings"]}
    assert kinds["app-errors"]["level"] == "red"
    assert kinds["app-errors"]["title"] == "10.25% of LLM calls are erroring"
    assert "app-exhausted" in kinds


def test_a_quiet_morning_falls_back_to_the_week_rather_than_crying_100_percent():
    doc = watch.evaluate(view_of({1: {"calls": 3, "errors": 3, "error_rate": 100.0}, 7: {}}))
    assert doc["days"] == 7
    assert next(f for f in doc["findings"] if f["kind"] == "app-errors")["title"].startswith("10.19%")


def test_an_unreadable_or_local_store_is_not_ok_and_raises_nothing():
    assert watch.evaluate(lambda d: {"ok": False})["ok"] is False
    local = watch.evaluate(view_of({1: {"store": "local:/tmp/x"}, 7: {"store": "local:/tmp/x"}}))
    assert local["ok"] is False and local["findings"] == []


def test_the_watcher_and_the_dashboard_use_one_rule_set():
    dash = [a["title"] for a in ops_data._alerts({}, {}, {}, APP, {})]
    for a in ops_data._app_alerts(APP):
        assert a["title"] in dash, a["title"]


# --- how it is filed ---------------------------------------------------------

def _run_filer(tmp_path, app_doc, existing_kinds=()):
    gh = tfo.FakeGh()
    for k in existing_kinds:
        fo.carry(gh, "o/r", [tfo.F(kind=k, title=f"{k} open")], "t0")
    det = tmp_path / "det.json"
    det.write_text(json.dumps({"findings": []}))
    args = ["x", "--repo", "o/r", "--findings", str(det)]
    if app_doc is not None:
        p = tmp_path / "app.json"
        p.write_text(json.dumps(app_doc))
        args += ["--app", str(p)]
    assert fo.main(args, gh=gh) == 0
    return gh


def test_a_read_app_files_its_findings(tmp_path):
    doc = watch.evaluate(view_of({1: {"calls": 400, "errors": 41, "error_rate": 10.25}, 7: {}}))
    gh = _run_filer(tmp_path, doc)
    titles = [i["title"] for i in gh.issues.values()]
    assert "[OPS] 10.25% of LLM calls are erroring" in titles


def test_an_unread_app_leaves_its_open_issues_alone(tmp_path):
    gh = _run_filer(tmp_path, {"ok": False, "why": "auth failed"}, existing_kinds=("app-errors",))
    issue = next(iter(gh.issues.values()))
    assert not any("did not fire" in c for c in issue["comments"]), "unreadable is not cleared"


def test_a_read_app_with_no_alert_does_clear_its_issue(tmp_path):
    gh = _run_filer(tmp_path, {"ok": True, "days": 1, "findings": []}, existing_kinds=("app-errors",))
    issue = next(iter(gh.issues.values()))
    assert any("did not fire" in c for c in issue["comments"])


# --- the wiring --------------------------------------------------------------

def _steps():
    return yaml.safe_load((ROOT / ".github/workflows/agent-steward.yml").read_text())["jobs"]["steward"]["steps"]


def test_credentials_reach_only_the_watcher_and_are_gone_before_any_agent():
    steps = _steps()
    names = [s.get("name") or s.get("uses") for s in steps]
    auth = steps[names.index("Authenticate to the bucket (read-only)")]
    assert auth["with"]["export_environment_variables"] is False
    watch_step = steps[names.index("Read the live app's health")]
    assert watch_step["env"]["GOOGLE_APPLICATION_CREDENTIALS"] == "${{ steps.gcs.outputs.credentials_file_path }}"
    rm = names.index("Remove the bucket credentials before any agent runs")
    assert steps[rm]["if"] == "always()"
    first_agent = next(i for i, s in enumerate(steps) if "claude-code-action" in str(s.get("uses", "")))
    assert names.index("Read the live app's health") < rm < first_agent


def test_the_filer_is_given_the_app_findings():
    step = next(s for s in _steps() if s.get("name") == "File the ops dashboard's findings as issues")
    assert "--app /tmp/app-health.json" in step["run"]


def test_zero_calls_read_is_unreadable_not_a_clean_bill():
    # QA on #1002: a swallowed 403 reads as ok:true with 0 calls.
    doc = watch.evaluate(view_of({1: {"calls": 0, "errors": 0, "error_rate": 0.0, "measured": False},
                                  7: {"calls": 0, "errors": 0, "error_rate": 0.0, "measured": False}}))
    assert doc["ok"] is False and doc["findings"] == []


def test_the_real_view_with_an_unreachable_bucket_clears_nothing(tmp_path, monkeypatch):
    # The real _app_view, a bucket name, and no way to read it: the exact path QA
    # measured. Local fallbacks point at empty dirs so nothing leaks in.
    from astro_ai import events, llm_stats, storage
    monkeypatch.setenv("BHAGYA_STORAGE_BUCKET", "shubhagya-cache-us")
    monkeypatch.setattr(storage, "_client", lambda: None)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "s", raising=False)
    monkeypatch.setattr(events, "_LOCAL_FALLBACK_DIR", tmp_path / "e", raising=False)
    ops_data._app_cache.clear()
    out = tmp_path / "app.json"
    assert watch.main(["x", "--out", str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["ok"] is False, doc
    gh = _run_filer(tmp_path, doc, existing_kinds=("app-errors",))
    issue = next(iter(gh.issues.values()))
    assert not any("did not fire" in c for c in issue["comments"])
    assert len(gh.issues) == 1, "no false 'No LLM calls recorded' issue"


def test_local_numbers_behind_an_unreadable_bucket_are_never_reported_as_production():
    # Reproduced after QA on #1002: no credentials, local stats present -> the
    # view returned this machine's numbers under a gcs: store name.
    doc = watch.evaluate(view_of({1: {"calls": 400, "errors": 41, "error_rate": 10.25}, 7: {}}),
                         probe=lambda: (False, "could not read gs://x/llm_stats/yesterday.json"))
    assert doc["ok"] is False and doc["findings"] == []
    assert "could not read" in doc["why"]
