"""A starved build lane assigns the Evidence Block retrofit (2026-11-10).

Measured that day: 112 issues open, 63 failing `verify_issue_evidence.py`, and
the last two build cycles built nothing. Every ranked item was refused at Step
1, the cycle may not write its own eligibility, and nobody else owned writing
the missing blocks. Three pieces close that:

  1. `chain_cycle.py` dispatches `agent-prioritise.yml` with `mode=evidence`
     on the second empty build cycle in a row (rate-limited).
  2. `agent-prioritise.yml` in that mode lists the refused issues with
     `scripts/evidence_backlog.py` and has project-manager retrofit or close.
  3. `detect_ops_regressions.py` raises `loop-starved` so /admin/ops shows it.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


cc = _load("chain_cycle", ROOT / "scripts" / "chain_cycle.py")
eb = _load("evidence_backlog", ROOT / "scripts" / "evidence_backlog.py")
tod = _load("test_ops_regression_detector_helpers", ROOT / "tests" / "test_ops_regression_detector.py")

NOW = datetime(2026, 11, 10, 5, 10, tzinfo=timezone.utc)
REPO = "o/r"
USAGE = {"generated_at": "2026-11-10T05:03:00Z", "latest": {"seven_day": 0.39, "status": "allowed"}}
# The finished cycle (05:02) and the one before it (02:06), as on 2026-11-10.
RUN = {"name": "Agent work", "title": "Agent work", "conclusion": "success",
       "started": "2026-11-10T05:02:00Z"}
STEWARD = {"name": "Agent steward", "title": "Agent steward", "conclusion": "success",
           "started": "2026-11-10T05:01:00Z"}
BUILDS = [{"display_title": "Agent work", "conclusion": "success", "run_started_at": "2026-11-10T05:02:00Z",
           "created_at": "2026-11-10T05:02:00Z"},
          {"display_title": "QA round: PR #833", "conclusion": "success",
           "run_started_at": "2026-11-10T03:00:00Z", "created_at": "2026-11-10T03:00:00Z"},
          {"display_title": "Agent work", "conclusion": "success", "run_started_at": "2026-11-10T02:06:00Z",
           "created_at": "2026-11-10T02:06:00Z"}]


def pr(n, created, updated, ref="issue/1-x", login="claude[bot]"):
    return {"number": n, "user": {"login": login}, "head": {"ref": ref},
            "created_at": created, "updated_at": updated}


# What the API really returned for that window (QA on #841): measurement PRs
# #834/#840 and #833/#839, built earlier and merged by agent-merge mid-window.
REPLAY = [pr(840, "2026-11-10T05:04:00Z", "2026-11-10T05:04:18Z", "measurements/42759-1",
             "shubhagya-publisher[bot]"),
          pr(839, "2026-11-10T04:55:00Z", "2026-11-10T05:08:09Z"),
          pr(833, "2026-11-09T23:50:00Z", "2026-11-10T05:08:36Z"),
          pr(834, "2026-11-10T02:09:00Z", "2026-11-10T02:09:04Z", "measurements/42740-1",
             "shubhagya-publisher[bot]")]
HEADS = {839: "2026-11-10T04:50:00Z", 833: "2026-11-10T01:40:00Z"}


class FakeGh:
    def __init__(self, prs=REPLAY, heads=HEADS, builds=BUILDS, retrofits=(), busy=0):
        self.prs, self.heads, self.builds = list(prs), dict(heads), list(builds)
        self.retrofits, self.busy = list(retrofits), busy
        self.calls: list[list[str]] = []

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["run", "list"]:
            return f"{self.busy}\n"
        url = args[1] if args[0] == "api" else ""
        if "agent-work.yml/runs" in url and "status=completed" in url:
            return json.dumps({"workflow_runs": self.builds})
        if "agent-work.yml/runs" in url:
            return json.dumps({"workflow_runs": [{"display_title": "Agent work"}] * 3})
        if "agent-prioritise.yml/runs" in url:
            return json.dumps({"workflow_runs": self.retrofits})
        if "/commits?" in url:
            n = int(url.split("/pulls/")[1].split("/")[0])
            return json.dumps([{"commit": {"committer": {"date": self.heads[n]}}}])
        if "/pulls?" in url:
            return json.dumps(self.prs)
        if args[:2] == ["workflow", "run"]:
            return ""
        raise AssertionError(args)

    def dispatched(self, wf):
        return [a for a in self.calls if a[:3] == ["workflow", "run", wf]]


def _main(gh, monkeypatch, tmp_path, run=RUN, usage=USAGE):
    p = tmp_path / "usage.json"
    p.write_text(json.dumps(usage))
    monkeypatch.setenv("GH_REPO", REPO)
    for k, v in run.items():
        monkeypatch.setenv(f"WR_{k.upper()}", v)
    assert cc.main(["x"], gh=gh, now=NOW, usage_path=p) == 0


# --- 1. the trigger ----------------------------------------------------------

def _refused(monkeypatch, n):
    monkeypatch.setattr(cc, "refused_count", lambda gh, repo: n)


def test_a_locked_out_backlog_dispatches_the_retrofit_after_an_empty_cycle(monkeypatch, tmp_path, capsys):
    _refused(monkeypatch, 63)                     # 2026-11-10
    gh = FakeGh()
    _main(gh, monkeypatch, tmp_path)
    (call,) = gh.dispatched("agent-prioritise.yml")
    assert call[-2:] == ["-f", "mode=evidence"]
    assert not gh.dispatched("agent-work.yml"), "an empty cycle still must not chain"
    assert "refused backlog" in capsys.readouterr().out


def test_the_steward_trigger_reaches_it_too(monkeypatch, tmp_path):
    # Dispatched cycles never reach agent-queue (0 of 26); the steward's completion does.
    _refused(monkeypatch, 63)
    gh = FakeGh()
    _main(gh, monkeypatch, tmp_path, run=STEWARD)
    assert gh.dispatched("agent-prioritise.yml")


def test_a_clean_backlog_dispatches_nothing(monkeypatch, tmp_path):
    _refused(monkeypatch, cc.RETROFIT_MIN_REFUSED - 1)    # 2026-11-10 after the retrofit: 1 (#444)
    gh = FakeGh()
    _main(gh, monkeypatch, tmp_path, run=STEWARD)
    assert not gh.dispatched("agent-prioritise.yml")


def test_the_count_is_the_evidence_backlog_list(monkeypatch):
    monkeypatch.setattr(eb, "failing", lambda gh, repo: [{}] * 7)
    assert cc.refused_count(None, REPO) == 7


def test_the_cooldown_is_checked_before_the_expensive_count(monkeypatch, tmp_path):
    def boom(gh, repo):
        raise AssertionError("counted the backlog inside the cooldown")
    monkeypatch.setattr(cc, "refused_count", boom)
    recent = {"display_title": cc.RETROFIT_TITLE, "status": "completed", "created_at": "2026-11-10T01:00:00Z"}
    gh = FakeGh(retrofits=[recent])
    _main(gh, monkeypatch, tmp_path)
    assert not gh.dispatched("agent-prioritise.yml")


def test_a_running_retrofit_blocks_another(monkeypatch, tmp_path):
    _refused(monkeypatch, 63)
    running = {"display_title": cc.RETROFIT_TITLE, "status": "in_progress", "created_at": "2026-11-09T01:00:00Z"}
    gh = FakeGh(retrofits=[running])
    _main(gh, monkeypatch, tmp_path)
    assert not gh.dispatched("agent-prioritise.yml")


def test_an_old_retrofit_or_a_weekly_ranking_does_not_block(monkeypatch, tmp_path):
    _refused(monkeypatch, 63)
    old = {"display_title": cc.RETROFIT_TITLE, "status": "completed", "created_at": "2026-11-09T20:00:00Z"}
    weekly = {"display_title": "Agent prioritise", "status": "completed", "created_at": "2026-11-10T04:00:00Z"}
    gh = FakeGh(retrofits=[weekly, old])
    _main(gh, monkeypatch, tmp_path)
    assert gh.dispatched("agent-prioritise.yml")


def test_an_exhausted_quota_dispatches_nothing(monkeypatch, tmp_path):
    _refused(monkeypatch, 63)
    gh = FakeGh()
    _main(gh, monkeypatch, tmp_path, usage={**USAGE, "latest": {"seven_day": 0.75, "status": "allowed"}})
    assert not gh.dispatched("agent-prioritise.yml")


# --- what counts as a cycle's output (QA on #841, defect 2) ------------------

def test_measurement_prs_and_mid_window_merges_are_not_cycle_output():
    # The 05:02 run's own window: #840 is a report, #839 and #833 were built
    # before it and merged by agent-merge during it.
    assert not cc.produced_something(FakeGh(), REPO, cc._ts("2026-11-10T05:02:00Z"))


def test_a_pr_opened_in_the_window_is_output():
    gh = FakeGh(prs=REPLAY + [pr(850, "2026-11-10T05:05:00Z", "2026-11-10T05:06:00Z")])
    assert cc.produced_something(gh, REPO, cc._ts("2026-11-10T05:02:00Z"))


def test_a_fix_pushed_to_an_older_pr_in_the_window_is_output():
    gh = FakeGh(heads={**HEADS, 833: "2026-11-10T05:05:00Z"})
    assert cc.produced_something(gh, REPO, cc._ts("2026-11-10T05:02:00Z"))


# --- 2. the workflow ---------------------------------------------------------

def _wf():
    return yaml.safe_load((WF / "agent-prioritise.yml").read_text())


def test_the_title_chain_cycle_matches_on_is_the_one_the_workflow_writes():
    assert f"'{cc.RETROFIT_TITLE}'" in _wf()["run-name"]


def test_evidence_mode_is_a_dispatch_choice_defaulting_to_rank():
    on = _wf()[next(k for k in _wf() if str(k) in ("on", "True"))]
    mode = on["workflow_dispatch"]["inputs"]["mode"]
    assert mode["options"] == ["rank", "evidence"] and mode["default"] == "rank"
    assert "schedule" in on, "the weekly ranking must keep its cron"


def test_each_mode_runs_only_its_own_agent_and_the_retrofit_commits_nothing():
    steps = {s.get("name"): s for s in _wf()["jobs"]["prioritise"]["steps"]}
    assert steps["Retrofit or close"]["if"] == "inputs.mode == 'evidence'"
    assert steps["List the issues the build loop refuses"]["if"] == "inputs.mode == 'evidence'"
    assert "scripts/evidence_backlog.py" in steps["List the issues the build loop refuses"]["run"]
    assert steps["Rank"]["if"] == "inputs.mode != 'evidence'"
    assert "uses" in steps["Rank"] and "uses" in steps["Retrofit or close"]
    assert "inputs.mode != 'evidence'" in _wf()["jobs"]["persist"]["if"]


def test_the_retrofit_prompt_requires_measurement_and_the_checker():
    prompt = {s.get("name"): s for s in _wf()["jobs"]["prioritise"]["steps"]}["Retrofit or close"]["with"]["prompt"]
    for must in ("MEASURE", "verify_issue_evidence.py", "[UNSOURCED]", "Never close for age",
                 "close-on-evidence.yml", "never touch a", "Stop after 15"):
        assert must in prompt, must


# --- the list ----------------------------------------------------------------

def _issue(n, labels, body, comments=0, created="2026-10-20T00:00:00Z"):
    return {"number": n, "title": f"t{n}", "labels": [{"name": x} for x in labels],
            "body": body, "comments": comments, "created_at": created}


BLOCK = ("repro: grep -c x f -> 1\ncorpus: n/a -- no astrology claim here\n"
         "tokens: 0 (measured: no LLM call)\nthesis: it works\nmetric: count goes to 0\n")


def test_the_list_holds_only_failures_in_harm_order_and_reads_comments():
    issues = [_issue(9, ["enhancement"], ""), _issue(8, ["bug"], ""),
              _issue(7, ["bug", "astrology-correctness"], ""),
              _issue(6, ["bug"], "", comments=1),                     # fixed by a comment
              _issue(5, [], "", created="2026-09-01T00:00:00Z"),      # exempt by date
              _issue(3, ["bug", "provenance:outsider"], ""),           # triaged elsewhere
              {"number": 4, "pull_request": {}, "labels": []}]

    def gh(args):
        url = args[1]
        if "/issues?" in url:
            return json.dumps(issues if "page=1" in url else [])
        if url.endswith("/issues/6/comments?per_page=100"):
            return json.dumps([{"body": BLOCK}])
        raise AssertionError(url)
    rows = eb.failing(gh, REPO)
    assert [r["number"] for r in rows] == [7, 8, 9]
    assert all(r["problems"] for r in rows)
    assert "#7 [bug, astrology-correctness]" in eb.render(rows)


# --- 3. the dashboard --------------------------------------------------------

def _find(tmp_path, monkeypatch, outcomes):
    root = tod._repo(tmp_path, tod._agents(), [(8, tod._issues()), (0, tod._issues())])
    rows = [{"started": f"2026-11-10T0{i}:00:00Z", "kind": k, "outcome": o}
            for i, (k, o) in enumerate(outcomes)]
    (root / "measurements" / "loop.json").write_text(json.dumps({"rows": rows}))
    monkeypatch.setattr(tod.det, "ROOT", root)
    monkeypatch.setattr(tod.det, "MEASUREMENTS", root / "measurements")
    return {f["kind"]: f for f in tod.det.find(now=tod.NOW)[0]}


def test_the_2026_11_10_alternating_pattern_raises_loop_starved(tmp_path, monkeypatch):
    f = _find(tmp_path, monkeypatch, [("ranked", "pr open"), ("ranked", "nothing"),
                                      ("qa-round", "judged"), ("ranked", "pr open"),
                                      ("ranked", "nothing")])
    assert f["loop-starved"]["level"] == "amber"
    assert "2 of the last 4" in f["loop-starved"]["title"]
    assert "mode=evidence" in f["loop-starved"]["detail"]


def test_one_empty_cycle_in_four_is_not_starved(tmp_path, monkeypatch):
    f = _find(tmp_path, monkeypatch, [("ranked", "nothing"), ("ranked", "pr open"),
                                      ("ranked", "shipped"), ("issue", "pr open")])
    assert "loop-starved" not in f
