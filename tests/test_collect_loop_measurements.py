"""The loop/cost collector (#338): every test is a way the ops page's data could lie.

WHY THESE EXIST. `measurements/loop.json` says what each autonomous cycle
produced; `cost.json` says what the team costs. The page built on them (#335)
will be believed, so the failures that matter are the quiet ones:

  * attributing a PR to a run that did not open it (the time-window heuristic
    this replaces, and its cousin: "newest PR on the branch" handing a run a PR a
    LATER run opened -- runs 37734421636/37735035844 printed "no commits on
    issue/272-..." and PR #292 on that branch shipped two hours later);
  * reading the receipt out of a step's ECHOED SOURCE rather than its output;
  * a vendor with no readable figure written as 0;
  * one bad parse frozen forever, because settled rows are never re-read.

Hermetic: `GhSource._run` is poisoned, so an accidental network call fails loudly
instead of "passing" on whatever the sandbox's token can see. The job-log
fixtures under tests/fixtures/loop_measurements/ are REAL excerpts (net step
group + output, from runs 37735035844, 37749887640, 38037787957, 38341529127,
38435548008, fetched 2026-10-13). The receipt log is built by EXECUTING the
workflow's own receipt step, not by typing what we hope it prints.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures" / "loop_measurements"

_spec = importlib.util.spec_from_file_location("collect_loop_measurements", ROOT / "scripts" / "collect_loop_measurements.py")
cm = importlib.util.module_from_spec(_spec)
sys.modules["collect_loop_measurements"] = cm
_spec.loader.exec_module(cm)

NOW = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(self, *a, **k):
        raise AssertionError("a collector test reached for the network")
    monkeypatch.setattr(cm.GhSource, "_run", refuse)


class Fake(cm.Source):
    """Runs/jobs/pulls from a dict; job logs from the fixture directory. Records
    every call so a test can say what was NOT fetched."""

    def __init__(self, data=None, logs=None):
        self.data, self.logs, self.calls = data or {}, logs or {}, []

    def get(self, path, paginate=False):
        self.calls.append(path)
        for k, v in self.data.items():
            if path == k or (k.endswith("*") and path.startswith(k[:-1])):
                return v
        raise cm.ApiError(404, path, "no fake")

    def text(self, path):
        self.calls.append(path)
        job = path.split("/")[2]
        if job in self.logs:
            return self.logs[job]
        f = FIX / f"actions_jobs_{job}_logs.log"
        if f.exists():
            return f.read_text()
        raise cm.ApiError(404, path, "no log")


def run(id, conclusion="success", start="2026-10-13T10:00:00Z", end="2026-10-13T10:20:00Z",
        status="completed", event="schedule"):
    return {"id": id, "status": status, "conclusion": conclusion, "event": event,
            "created_at": start, "run_started_at": start, "updated_at": end}


def jobs(run_id, job_id):
    return {f"actions/runs/{run_id}/jobs?per_page=100": {"jobs": [{"id": job_id, "conclusion": "success"}]}}


def pull(n, state="closed", merged=True, created="2026-10-13T10:10:00Z"):
    return {"number": n, "state": state, "merged_at": "2026-10-13T11:00:00Z" if merged else None,
            "created_at": created}


def runs_listing(*rs):
    return {"actions/workflows/agent-work.yml/runs*": {"workflow_runs": list(rs)}}


def collect(src, existing=None):
    return cm.collect(src, existing, NOW, "mahAnuj")


def receipt_log(branch_name="issue/338-x", pr_number=42, have_branch=True):
    """The agent-work receipt step, EXECUTED in a scratch repo with a stub `gh`,
    wrapped the way Actions logs a `run:` step: the script source in a
    `##[group]Run` block, then the real output."""
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-work.yml").read_text())
    step = next(s for s in wf["jobs"]["cycle"]["steps"] if s.get("name") == "Record the loop receipt")
    return step["run"], _exec_step(step["run"], branch_name, pr_number, have_branch)


def _exec_step(script, branch_name, pr_number, have_branch, gh_fails=False):
    import tempfile
    d = Path(tempfile.mkdtemp())
    try:
        (d / "bin").mkdir()
        gh = d / "bin" / "gh"
        gh.write_text("#!/bin/sh\nexit 1\n" if gh_fails else f"#!/bin/sh\necho {pr_number or ''}\n")
        gh.chmod(0o755)
        (d / "r").mkdir()
        git = ["git", "-c", "user.email=a@b", "-c", "user.name=n"]
        subprocess.run(["git", "init", "-q", "."], cwd=d / "r", check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=d / "r", check=True)
        if have_branch:
            subprocess.run(["git", "checkout", "-q", "-b", branch_name], cwd=d / "r", check=True)
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "y"], cwd=d / "r", check=True)
        env = {**os.environ, "PATH": f"{d / 'bin'}:{os.environ['PATH']}", "GH_REPO": "o/r", "GH_TOKEN": "t"}
        r = subprocess.run(["bash", "-e", "-c", script], cwd=d / "r", env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr      # the receipt must never fail the run
        return r.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def wrap_as_actions_log(script, output):
    head = "2026-10-13T03:00:00.0000000Z ##[group]Run " + script.splitlines()[0]
    echoed = "\n".join("2026-10-13T03:00:00.0000001Z " + ln for ln in script.splitlines()[1:])
    out = "\n".join("2026-10-13T03:00:01.0000000Z " + ln for ln in output.splitlines())
    return f"{head}\n{echoed}\n2026-10-13T03:00:00.0000002Z ##[endgroup]\n{out}\n"


# --------------------------------------------------------------------------- #
# the receipt
# --------------------------------------------------------------------------- #

def test_receipt_matches_the_printed_line_but_not_the_echoed_source():
    script, out = receipt_log()
    assert out.strip() == "LOOP-RECEIPT issue=338 branch=issue/338-x pr=42"
    log = wrap_as_actions_log(script, out)
    assert "LOOP-RECEIPT issue=%s" in log                  # the source IS in the log...
    assert cm.parse_receipt(log) == (338, "issue/338-x", 42)   # ...and is not what matched
    assert cm.parse_receipt(log.split("##[endgroup]")[0]) is None   # source alone: no receipt


def test_receipt_records_no_branch_and_no_pr_as_none():
    script, out = receipt_log(have_branch=False)
    assert cm.parse_receipt(wrap_as_actions_log(script, out)) == (None, None, None)


def test_a_failed_pr_lookup_prints_no_receipt_rather_than_a_false_pr_none():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-work.yml").read_text())
    script = next(s for s in wf["jobs"]["cycle"]["steps"] if s.get("name") == "Record the loop receipt")["run"]
    out = _exec_step(script, "issue/9-x", None, True, gh_fails=True)
    assert "LOOP-RECEIPT" not in out
    assert cm.parse_receipt(out) is None


def test_agent_work_pins_the_printf_literal_and_runs_the_receipt_last_and_always():
    text = (ROOT / ".github" / "workflows" / "agent-work.yml").read_text()
    assert "printf 'LOOP-RECEIPT issue=%s branch=%s pr=%s\\n'" in text
    steps = yaml.safe_load(text)["jobs"]["cycle"]["steps"]
    assert steps[-1]["name"] == "Record the loop receipt"
    assert steps[-1]["if"] == "always()"
    # No step may hold the receipt as a literal: it would be echoed into every log.
    assert not cm.RECEIPT.search(text)


# --------------------------------------------------------------------------- #
# attribution and outcome
# --------------------------------------------------------------------------- #

def test_a_receipt_run_with_a_merged_pr_is_shipped_and_labelled_receipt():
    script, out = receipt_log(pr_number=334)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77), "pulls/334": pull(334, merged=True)},
               logs={"77": wrap_as_actions_log(script, out)})
    doc, stats = collect(src)
    (row,) = doc["rows"]
    assert (row["outcome"], row["attribution"], row["issue"], row["pr"], row["pr_merged"]) == \
        ("shipped", "receipt", 338, 334, True)
    assert cm.validate_loop(doc) == []


def test_receipt_with_no_pr_is_nothing_not_unknown():
    script, out = receipt_log(have_branch=False)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77)}, logs={"77": wrap_as_actions_log(script, out)})
    (row,) = collect(src)[0]["rows"]
    assert (row["outcome"], row["attribution"], row["pr"]) == ("nothing", "receipt", None)


def test_legacy_run_is_labelled_log_and_its_pr_is_looked_up_by_branch():
    # Real net-step output of run 38435548008: "issue/311-title-meta-ctr-test already on origin".
    src = Fake({**runs_listing(run(38435548008)), **jobs(38435548008, 115428442309),
                "pulls?head=mahAnuj:issue/311-title-meta-ctr-test&state=all&per_page=100": [pull(334, created="2026-10-13T10:10:00Z")],
                "pulls/334": pull(334)})
    (row,) = collect(src)[0]["rows"]
    assert (row["attribution"], row["issue"], row["pr"], row["outcome"]) == ("log", 311, 334, "shipped")


def test_the_checkout_line_for_main_is_not_read_as_the_branch():
    # Every fixture starts with actions/checkout's "branch 'main' set up to track
    # 'origin/main'." -- a first-hit search read every run as "ended on main".
    log = (FIX / "actions_jobs_115113373120_logs.log").read_text()
    assert log.splitlines()[0].endswith("branch 'main' set up to track 'origin/main'.")
    assert cm.parse_net_line(log) == ("issue/255-privacy-copy-and-relay", False)


def test_echoed_net_step_source_is_not_evidence():
    # The unattributed fixture is a REAL log whose group header echoes the whole
    # script, which contains "already on origin" and "no commits on" as text.
    log = (FIX / "actions_jobs_113220244143_logs.log").read_text()
    assert "already on origin" in log and "no commits on" in log
    assert cm.parse_net_line(log) is None


def test_unparseable_success_run_is_unattributed_unknown_and_never_guessed():
    # Real log of 37749887640: the 63-minute run that died pushing. No net-step line.
    src = Fake({**runs_listing(run(37749887640)), **jobs(37749887640, 113220244143)})
    (row,) = collect(src)[0]["rows"]
    assert (row["attribution"], row["issue"], row["pr"], row["outcome"]) == ("unattributed", None, None, "unknown")


def test_unattributed_run_that_did_not_succeed_is_failed():
    src = Fake({**runs_listing(run(37749887640, conclusion="failure")), **jobs(37749887640, 113220244143)})
    (row,) = collect(src)[0]["rows"]
    assert (row["outcome"], row["attribution"], row["conclusion"]) == ("failed", "unattributed", "failure")


def test_failed_run_with_a_rescued_merged_pr_keeps_its_conclusion_but_is_shipped():
    script, out = receipt_log(pr_number=315)
    src = Fake({**runs_listing(run(1, conclusion="failure")), **jobs(1, 77), "pulls/315": pull(315)},
               logs={"77": wrap_as_actions_log(script, out)})
    (row,) = collect(src)[0]["rows"]
    assert (row["conclusion"], row["outcome"]) == ("failure", "shipped")


def test_no_commits_run_is_nothing_and_does_not_borrow_a_later_runs_pr():
    # Real line "no commits on issue/272-measurement-dimensions". PR #292 on that
    # branch was opened two hours LATER by a different run. The lookup must not run.
    src = Fake({**runs_listing(run(37735035844, end="2026-10-08T06:00:03Z", start="2026-10-08T05:57:48Z")),
                **jobs(37735035844, 113172541347)})
    (row,) = collect(src)[0]["rows"]
    assert (row["outcome"], row["issue"], row["pr"]) == ("nothing", 272, None)
    assert not any(c.startswith("pulls") for c in src.calls)


def test_a_reused_branch_gets_the_pr_that_existed_when_the_run_ended():
    # issue/255-... carries #328 (opened 10-11) and #330 (opened 10-13 by a later run).
    prs = [pull(330, merged=False, created="2026-10-13T03:41:27Z"), pull(328, created="2026-10-11T18:27:37Z")]
    src = Fake({**runs_listing(run(38162823809, start="2026-10-11T18:12:15Z", end="2026-10-11T19:14:45Z")),
                **jobs(38162823809, 114539134695),
                "pulls?head=mahAnuj:issue/255-privacy-copy-and-relay&state=all&per_page=100": prs,
                "pulls/328": pull(328)}, logs={"114539134695": (FIX / "actions_jobs_115113373120_logs.log").read_text()})
    (row,) = collect(src)[0]["rows"]
    assert row["pr"] == 328


def test_open_closed_and_unreadable_pr_outcomes():
    c = cm.outcome_of
    assert c("success", 5, False, "open", "receipt", False) == "pr open"
    assert c("success", 5, False, "closed", "log", False) == "failed"
    assert c("failure", None, None, None, "log", False) == "failed"
    assert c("success", None, None, None, "log", False) == "unknown"
    assert c("success", None, None, None, "unattributed", False) == "unknown"
    # a PR that exists but could not be read is unknown, and stays re-readable
    script, out = receipt_log(pr_number=9)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77)}, logs={"77": wrap_as_actions_log(script, out)})
    (row,) = collect(src)[0]["rows"]
    assert (row["outcome"], row["pr_merged"]) == ("unknown", None) and cm.reopen(row)


def test_incomplete_runs_are_skipped_not_recorded():
    src = Fake({**runs_listing(run(1, status="in_progress", conclusion=None))})
    doc, stats = collect(src)
    assert doc["rows"] == [] and stats["pending"] == 1


def test_a_transient_log_error_defers_the_row_instead_of_freezing_a_guess():
    src = Fake({**runs_listing(run(1)), "actions/runs/1/jobs?per_page=100": {"jobs": [{"id": 5, "conclusion": "success"}]}},
               logs={})
    src.text = lambda path: (_ for _ in ()).throw(cm.ApiError(403, path, "forbidden"))
    doc, stats = collect(src)
    assert doc["rows"] == [] and stats["deferred"] == 1
    gone = Fake({**runs_listing(run(1)), "actions/runs/1/jobs?per_page=100": {"jobs": [{"id": 5, "conclusion": "success"}]}})
    gone.text = lambda path: (_ for _ in ()).throw(cm.ApiError(410, path, "expired"))
    (row,) = collect(gone)[0]["rows"]
    assert row["attribution"] == "unattributed"      # an expired log never comes back


# --------------------------------------------------------------------------- #
# freezing and pruning
# --------------------------------------------------------------------------- #

def _row(**kw):
    base = {"run": 1, "workflow": "agent-work", "date": "2026-10-13", "started": "2026-10-13T10:00:00Z",
            "trigger": "schedule", "conclusion": "success", "minutes": 20.0, "issue": 5, "pr": 42,
            "pr_merged": True, "outcome": "shipped", "attribution": "receipt", "kind": "issue"}
    row = {**base, **kw}
    # A settled shipped row already knows who finished it (2026-11-09); any other row is null.
    row.setdefault("owner_helped", False if row["outcome"] == "shipped" else None)
    return row


def test_a_frozen_row_is_not_re_fetched_at_all():
    src = Fake(runs_listing(run(1)))     # no jobs, no pulls: any fetch would be a 404 and show in calls
    doc, stats = collect(src, {"rows": [_row()]})
    assert stats["frozen"] == 1 and doc["rows"] == [_row()]
    assert src.calls == [c for c in src.calls if c.startswith("actions/workflows")]


def test_a_pr_open_row_re_reads_the_pr_only_never_the_log():
    src = Fake({**runs_listing(run(1)), "pulls/42": pull(42, merged=True)})
    doc, stats = collect(src, {"rows": [_row(outcome="pr open", pr_merged=False)]})
    assert stats["refreshed"] == 1
    assert (doc["rows"][0]["outcome"], doc["rows"][0]["pr_merged"]) == ("shipped", True)
    assert not any("/jobs" in c or "/logs" in c for c in src.calls)


def test_rows_older_than_120_days_are_pruned_and_the_rest_kept():
    old = _row(run=2, started="2026-05-01T00:00:00Z", date="2026-05-01")
    doc, stats = collect(Fake(runs_listing()), {"rows": [old, _row()]})
    assert [r["run"] for r in doc["rows"]] == [1] and stats["pruned"] == 1


# --------------------------------------------------------------------------- #
# validation, and "write nothing"
# --------------------------------------------------------------------------- #

def test_loop_validator_rejects_an_outcome_its_own_fields_contradict():
    def doc(**kw):
        return {"generated_at": "2026-10-13T00:00:00Z", "rows": [_row(**kw)]}
    assert cm.validate_loop(doc()) == []
    assert cm.validate_loop(doc(pr=None, pr_merged=None))               # shipped, no PR
    assert cm.validate_loop(doc(outcome="pr open"))                     # open but merged
    assert cm.validate_loop(doc(outcome="success"))                     # not a known outcome
    assert cm.validate_loop(doc(attribution="guess"))
    assert cm.validate_loop(doc(attribution="unattributed", outcome="failed"))   # names an issue/pr
    assert cm.validate_loop(doc(issue=None, pr=None, pr_merged=None, outcome="nothing",
                                attribution="unattributed"))


def test_an_empty_collection_writes_nothing_and_exits_1(tmp_path, monkeypatch, capsys):
    (tmp_path / "loop.json").write_text('{"keep": "me"}')
    monkeypatch.setattr(cm, "LogSource", lambda repo: Fake(runs_listing()))
    assert cm.main(["--out", str(tmp_path)]) == 1
    assert json.loads((tmp_path / "loop.json").read_text()) == {"keep": "me"}
    assert not (tmp_path / "cost.json").exists()


def test_main_writes_both_files_from_a_collection(tmp_path, monkeypatch):
    script, out = receipt_log(pr_number=1)
    now = datetime.now(timezone.utc)
    start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    src = Fake({**runs_listing(run(1, start=start, end=start)), **jobs(1, 77), "pulls/1": pull(1)},
               logs={"77": wrap_as_actions_log(script, out)})
    monkeypatch.setattr(cm, "LogSource", lambda repo: src)
    assert cm.main(["--out", str(tmp_path)]) == 0
    assert json.loads((tmp_path / "loop.json").read_text())["rows"][0]["outcome"] == "shipped"
    assert cm.validate_loop(json.loads((tmp_path / "loop.json").read_text())) == []
    assert (tmp_path / "cost.json").read_text() == cm.dump(cm.build_cost())


def test_log_source_asks_gh_for_escape_sequences_and_retries_on_an_old_gh(monkeypatch):
    seen = []

    def fake(self, path, extra):
        seen.append(extra)
        if extra:
            raise cm.ApiError(None, path, "unknown flag: --allow-escape-sequences")
        return "log"
    monkeypatch.setattr(cm.GhSource, "_run", fake)
    assert cm.LogSource("o/r").text("actions/jobs/1/logs") == "log"
    assert seen == [["--allow-escape-sequences"], []]


# --------------------------------------------------------------------------- #
# cost
# --------------------------------------------------------------------------- #

def _cost(**kw):
    row = {"item": "X", "vendor": "V", "monthly_usd": 0, "basis": "b", "status": "known", "note": ""}
    return {"rows": [{**row, **kw}]}


def test_the_rates_table_is_valid_and_google_cloud_is_null_not_zero():
    doc = cm.build_cost()
    assert cm.validate_cost(doc) == []
    by = {r["item"].split(" (")[0]: r for r in doc["rows"]}
    assert by["Google Cloud"]["monthly_usd"] is None and by["Google Cloud"]["status"] == "awaiting billing export"
    assert by["OpenAI"]["monthly_usd"] is None
    assert by["Claude Max 5x"]["monthly_usd"] == 100
    assert "total" not in doc and "generated_at" not in doc      # unchanged output must be no commit


def test_a_zero_standing_on_an_explanation_fails():
    assert cm.validate_cost(_cost(monthly_usd=0, status="known")) == []
    assert cm.validate_cost(_cost(monthly_usd=0, status="free-tier")) == []
    assert cm.validate_cost(_cost(monthly_usd=0, status="awaiting billing export"))
    assert cm.validate_cost(_cost(monthly_usd=0, status=""))


def test_a_null_without_a_reason_or_with_a_figure_status_fails():
    assert cm.validate_cost(_cost(monthly_usd=None, status="awaiting billing export")) == []
    assert cm.validate_cost(_cost(monthly_usd=None, status=""))
    assert cm.validate_cost(_cost(monthly_usd=None, status=None))
    assert cm.validate_cost(_cost(monthly_usd=None, status="known"))
    assert cm.validate_cost(_cost(monthly_usd=5, status="free-tier"))
    assert cm.validate_cost(_cost(monthly_usd=-1, status="known"))


# --------------------------------------------------------------------------- #
# the wiring and the committed files
# --------------------------------------------------------------------------- #

MEASURE = ROOT / ".github" / "workflows" / "agent-measure.yml"


def test_commit_job_grants_exactly_the_scopes_the_collector_needs_and_orders_its_steps():
    job = yaml.safe_load(MEASURE.read_text())["jobs"]["commit"]
    # `issues: read` was added by #344 for scripts/collect_issue_backlog.py.
    # This is an exact pin, not a floor: a scope appearing here that no step
    # needs is as much a defect as a missing one, so widening it has to be a
    # deliberate edit to this line rather than something a PR can drift into.
    #
    # #393 widened three of them, and each buys one thing the job could not do
    # before: `pull-requests: write` opens the PR and enables auto-merge, and
    # `actions: write` dispatches pr-gates and verify-build -- without which a
    # PR opened by GITHUB_TOKEN carries no checks at all (#322) and can never
    # merge. The read scopes they replace were strictly weaker, not additional.
    assert job["permissions"] == {"contents": "write", "actions": "write",
                                  "pull-requests": "write", "issues": "read"}
    names = [s.get("name") for s in job["steps"]]
    collect_i, commit_i = names.index("Collect loop measurements"), names.index("Commit the measurement")
    assert collect_i < commit_i
    step = job["steps"][collect_i]
    assert step["continue-on-error"] is True
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert "scripts/collect_loop_measurements.py" in step["run"]
    run_text = job["steps"][commit_i]["run"]
    # the report-less early exit would skip the collector's files on the worst days
    assert 'echo "no report to persist"\n            exit 0' not in run_text
    # The push itself moved to scripts/publish_measurements.sh (#393) and is
    # pinned by tests/test_publish_measurements.py, across all six loops. What
    # stays here is the ORDERING this file is about: the collector has to run
    # before the step that publishes its output.
    assert "scripts/publish_measurements.sh" in run_text


#: Since 2026-11-09 the collectors run on `agent-work` completing (debounced by
#: scripts/measure_due.py); this one clock slot is the backstop for a day on
#: which no cycle runs. Before that: "0 2 * * *" (2026-10-14) and
#: "0 5,8,11,14,17,20 * * *" (#353), which GitHub throttled to ~4 runs a day.
COLLECTORS_ONLY_CRON = "23 9 * * *"
#: The only schedule that may invoke the analyst.
ANALYST_CRON = "0 21 * * *"


def test_the_second_slot_runs_the_collectors_without_the_analyst():
    """A collectors-only run -- the backstop slot or a cycle completing -- must
    NOT invoke the analyst.

    Dropping or loosening `measure.if` would silently multiply the analyst's
    spend against the Claude cap, and nothing else in the suite would notice:
    every run would simply go green. Since 2026-11-09 the stakes are higher: a
    run fires on every `agent-work` completion, up to ~20 a day.
    """
    doc = yaml.safe_load(MEASURE.read_text())
    on = doc.get(True) or doc.get("on")
    crons = [c["cron"] for c in on["schedule"]]
    assert crons == [ANALYST_CRON, COLLECTORS_ONLY_CRON]
    assert on["workflow_run"]["workflows"] == ["Agent work"]

    # An ALLOW-LIST naming what MAY run the analyst. `github.event.schedule ==
    # ''` used to stand in for "dispatched", and a `workflow_run` event matches
    # it too -- so it must be gone, and no `!=` (a deny-list fails open).
    cond = doc["jobs"]["measure"]["if"]
    assert "!=" not in cond, "a deny-list here fails open; list what MAY run the analyst"
    # Since #903 the allow-list is wrapped in the loop pause, spelled !(==) so
    # the rule above still holds; the allow-list itself is unchanged.
    assert cond == (f"!(vars.LOOP_PAUSED == 'true') && "
                    f"(github.event_name == 'workflow_dispatch' || github.event.schedule == '{ANALYST_CRON}')")
    assert "workflow_run" not in cond and "schedule == ''" not in cond
    assert f"== '{COLLECTORS_ONLY_CRON}'" not in cond

    # ...and the collectors still run, which only holds while `commit` is
    # always() over a needs: measure that may be skipped (the debounce lives in
    # its own steps -- tests/test_measure_cadence.py).
    commit = doc["jobs"]["commit"]
    assert commit["needs"] == "measure"
    assert commit["if"] == "always()"
    assert commit.get("permissions", {}).get("contents") == "write"


def test_no_workflow_was_added():
    # 19 since 2026-11-02: agent-queue.yml, which starts the oldest queued
    # agent-work ruling when a cycle completes, so a dispatch made while one
    # runs is queued rather than dropped (scripts/cycle_queue.py).
    #
    # 18 since 2026-10-28: main-red-report.yml, which turns a non-green run of
    # `PR gates` on `main` into an issue comment. It is a separate workflow and
    # not a step in pr-gates because `failure()` is false when a job is KILLED,
    # so a reporter inside that job cannot report a `cancelled` or `timed_out`
    # run -- the two likeliest shapes of a red `main` (#461).
    #
    # 17 since 2026-10-25: qa-on-green.yml, which dispatches a QA round when a
    # PR's gates go green rather than waiting for detect_stalls.py's 4h
    # threshold and the steward's one-dispatch-per-run budget.
    assert len(list((ROOT / ".github" / "workflows").glob("*.yml"))) == 19


def test_committed_measurement_files_pass_their_validators():
    loop, cost = ROOT / "measurements" / "loop.json", ROOT / "measurements" / "cost.json"
    assert loop.exists() and cost.exists(), "run scripts/collect_loop_measurements.py and commit the result"
    assert cm.validate_loop(json.loads(loop.read_text())) == []
    assert json.loads(cost.read_text()) == cm.build_cost()      # the rates table is the source of truth


# --------------------------------------------------------------------------- #
# 2026-11-03: what the run was ASKED to do, and where the loop's time went.

def _prompt_line(p):
    """The action step's env listing, as Actions prints it -- the RESOLVED value."""
    return f"2026-10-13T10:01:00.0000000Z   PROMPT: {p}\n"


@pytest.mark.parametrize("prompt,kind", [
    ("/agent-cycle --qa-pr 679", "qa-round"),
    ("/agent-cycle 675", "issue"),
    ("/agent-cycle ", "ranked"),
    ("/agent-cycle", "ranked"),
])
def test_the_kind_is_read_from_the_runs_own_prompt(prompt, kind):
    assert cm.kind_of(["noise\n" + _prompt_line(prompt)]) == kind


def test_no_prompt_line_is_unknown_not_guessed():
    assert cm.kind_of(["2026-10-13T10:01:00Z nothing to see\n"]) == "unknown"


def test_a_QA_round_with_no_PR_is_JUDGED_not_nothing():
    """13 of the 47 `nothing` runs measured 2026-11-03 were rounds that had done
    their job -- 158 minutes filed as waste."""
    script, out = receipt_log(have_branch=False)
    log = _prompt_line("/agent-cycle --qa-pr 649") + wrap_as_actions_log(script, out)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77)}, logs={"77": log})
    (row,) = collect(src)[0]["rows"]
    assert (row["kind"], row["outcome"]) == ("qa-round", "judged")


def test_a_QA_round_is_never_credited_with_the_PRs_merge():
    """A round reviews a PR; counting it `shipped` would count one PR twice."""
    script, out = receipt_log(pr_number=334)
    log = _prompt_line("/agent-cycle --qa-pr 334") + wrap_as_actions_log(script, out)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77), "pulls/334": pull(334, merged=True)},
               logs={"77": log})
    (row,) = collect(src)[0]["rows"]
    assert row["outcome"] == "judged" and row["pr"] == 334


def test_an_issue_cycle_with_no_PR_is_still_nothing():
    script, out = receipt_log(have_branch=False)
    log = _prompt_line("/agent-cycle 518") + wrap_as_actions_log(script, out)
    src = Fake({**runs_listing(run(1)), **jobs(1, 77)}, logs={"77": log})
    (row,) = collect(src)[0]["rows"]
    assert (row["kind"], row["outcome"]) == ("issue", "nothing")


def test_a_row_settled_before_kind_existed_is_read_ONCE_then_frozen():
    old = _row(outcome="nothing", pr=None, pr_merged=None)
    del old["kind"]
    src = Fake({**runs_listing(run(1)), **jobs(1, 77)},
               logs={"77": _prompt_line("/agent-cycle --qa-pr 9")})
    doc, stats = collect(src, {"rows": [old]})
    assert stats["migrated"] == 1
    assert (doc["rows"][0]["kind"], doc["rows"][0]["outcome"]) == ("qa-round", "judged")
    src2 = Fake(runs_listing(run(1)))
    doc2, stats2 = collect(src2, doc)
    assert stats2["migrated"] == 0 and stats2["frozen"] == 1


def test_an_old_row_outside_the_listing_window_is_unknown_not_re_read():
    old = _row(run=9, started="2026-08-01T00:00:00Z", date="2026-08-01")
    del old["kind"]
    doc, _ = collect(Fake(runs_listing()), {"rows": [old, _row()]})
    assert {r["run"]: r["kind"] for r in doc["rows"]}[9] == "unknown"


def test_judged_is_rejected_for_anything_but_a_QA_round():
    def doc(**kw):
        return {"generated_at": "2026-10-13T00:00:00Z", "rows": [_row(**kw)]}
    assert cm.validate_loop(doc(outcome="judged", kind="qa-round", pr=None, pr_merged=None)) == []
    assert cm.validate_loop(doc(outcome="judged", kind="issue", pr=None, pr_merged=None))
    assert cm.validate_loop(doc(kind="sideways"))


def test_a_snapshot_written_before_kind_still_validates():
    r = _row()
    del r["kind"]
    assert cm.validate_loop({"generated_at": "x", "rows": [r]}) == []


def _w(outcome, kind, start, minutes, pr=None):
    return _row(run=hash((start, kind)) % 10**6, started=start, date=start[:10], minutes=minutes,
                outcome=outcome, kind=kind, pr=pr,
                pr_merged=(True if outcome == "shipped" else None if pr is None else False))


def test_waste_splits_minutes_by_outcome_and_counts_judged_as_a_result():
    rows = [_w("shipped", "issue", "2026-10-13T01:00:00Z", 40, pr=1),
            _w("judged", "qa-round", "2026-10-13T02:00:00Z", 10),
            _w("nothing", "ranked", "2026-10-13T03:00:00Z", 30),
            _w("failed", "issue", "2026-10-13T04:00:00Z", 20)]
    w = cm.waste(rows, NOW)
    assert w["minutes_by_outcome"]["judged"] == 10
    assert w["minutes_without_result"] == 50
    assert w["share_without_result"] == round(50 / 100, 3)
    assert w["shipped_prs"] == 1 and w["cycles"] == 4


def test_idle_merges_overlapping_build_runs_and_ignores_QA_rounds():
    rows = [_w("shipped", "issue", "2026-10-13T10:00:00Z", 60, pr=1),
            _w("nothing", "ranked", "2026-10-13T10:30:00Z", 60),       # overlaps: busy 10:00-11:30
            _w("judged", "qa-round", "2026-10-13T14:00:00Z", 120)]     # own lane: not build-busy
    w = cm.waste(rows, NOW, days=1)
    assert w["build_idle_hours"] == round(24 - 1.5, 1)


def test_rows_outside_the_window_are_not_counted():
    w = cm.waste([_w("nothing", "ranked", "2026-09-01T00:00:00Z", 999)], NOW)
    assert w["cycles"] == 0 and w["share_without_result"] is None and w["build_idle_hours"] == 7 * 24


# --- owner_helped (2026-11-09) ----------------------------------------------
# The owner pushes and merges loop PRs routinely; "shipped" must say who finished it.

def _pr_api(merger, authors):
    return {"merged_by": {"login": merger} if merger else None, "merged_at": "x", "state": "closed"}, \
        [{"author": ({"login": a} if a else None)} for a in authors]


class _Src:
    def __init__(self, pr, commits, fail=False):
        self.pr, self.commits, self.fail = pr, commits, fail

    def get(self, path):
        if self.fail:
            raise cm.ApiError(503, "pulls/1", "down")
        return self.commits if path.endswith("/commits?per_page=100") else self.pr


def test_a_pr_the_owner_merged_was_helped():
    assert cm.read_owner_helped(_Src(*_pr_api("mahAnuj", ["github-actions[bot]"])), 750) is True


def test_a_session_commit_on_a_loop_pr_was_helped():
    assert cm.read_owner_helped(_Src(*_pr_api("github-actions[bot]", ["github-actions[bot]", "claude"])), 778) is True


def test_an_unlinked_commit_author_is_not_credited_to_the_loop():
    assert cm.read_owner_helped(_Src(*_pr_api("github-actions[bot]", [None])), 1) is True


def test_a_pr_only_loop_bots_touched_was_the_loop_alone():
    src = _Src(*_pr_api("github-actions[bot]", ["github-actions[bot]", "claude[bot]", "shubhagya-publisher[bot]"]))
    assert cm.read_owner_helped(src, 797) is False


def test_an_unreadable_pr_is_unknown_not_loop_alone():
    assert cm.read_owner_helped(_Src(None, None, fail=True), 1) is None


def test_owner_helped_on_a_row_that_did_not_ship_is_invalid():
    errs = cm.validate_loop({"generated_at": "2026-10-13T00:00:00Z",
                             "rows": [_row(outcome="pr open", pr_merged=False, owner_helped=True)]})
    assert any("did not ship" in e for e in errs)


def test_a_settled_shipped_row_without_the_field_is_read_once():
    src = Fake({**runs_listing(run(1)), "pulls/42": {"merged_by": {"login": "mahAnuj"}, "merged_at": "x"},
                "pulls/42/commits?per_page=100": []})
    old = _row()
    del old["owner_helped"]
    doc, stats = collect(src, {"rows": [old]})
    assert doc["rows"][0]["owner_helped"] is True and stats["migrated"] == 1
