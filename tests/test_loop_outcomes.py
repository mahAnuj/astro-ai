"""The loop-outcome report (#316): every test is a defect that was invisible.

WHY THESE EXIST. On 2026-10-08/09 four defects in the autonomous loops each hid
behind a green or absent workflow status: agent-merge's `workflow_run` leg 422'd
on every run, close-on-evidence's close step 403'd, the measurement fetch 403'd
inside a `continue-on-error` step, and close-on-evidence's first real run closed
nothing. `scripts/report_loop_outcomes.py` judges EFFECT rather than conclusion,
and a report that cannot see defects we already know about is not worth running.
So the first four tests replay those defects from fixtures and demand BROKEN.

The rest are the controls, and the controls matter as much: a report that cries
BROKEN at an idle week trains everyone to ignore it, and one that prints OK when
it could not read the evidence is the defect it was written to catch.

Hermetic: every test reads `tests/fixtures/loop_outcomes/` and nothing else.
`GhSource._run` is poisoned below, so an accidental network call fails loudly
instead of "passing" on whatever the sandbox's token can see. Fixtures built from
real ids but not recorded from the API say `recorded: false` in MANIFEST.json.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures" / "loop_outcomes"

_spec = importlib.util.spec_from_file_location("report_loop_outcomes", ROOT / "scripts" / "report_loop_outcomes.py")
lo = importlib.util.module_from_spec(_spec)
sys.modules["report_loop_outcomes"] = lo      # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(lo)

WINDOW = lo.Window(lo.parse_when("2026-10-08"), lo.parse_when("2026-10-10T12:00:00Z"))
ARGS = ["--since", "2026-10-08", "--until", "2026-10-10T12:00:00Z"]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(self, *a, **k):
        raise AssertionError("a loop-outcome test reached for the network")
    monkeypatch.setattr(lo.GhSource, "_run", refuse)


def source(name, *extra: Path):
    return lo.FixtureSource([*extra, FIX / name, FIX / "healthy"])


def report(name, *extra: Path):
    findings = lo.run_all(source(name, *extra), WINDOW)
    return {f.loop: f for f in findings}, findings


def _run(id, event, concl, created, updated, status="completed"):
    return {"id": id, "event": event, "status": status, "conclusion": concl, "created_at": created,
            "run_started_at": created, "updated_at": updated, "head_sha": "d" * 40, "head_branch": "main",
            "html_url": ""}


def _commit(date):
    return {"commit": {"committer": {"date": date}}}


def _pr(number, body="", ref=None, merged_at="2026-10-09T00:00:00Z", labels=("qa-pass",), by="github-actions[bot]"):
    return {"number": number, "title": f"t{number}", "body": body, "state": "closed", "draft": False,
            "merged_at": merged_at, "merge_commit_sha": "e" * 40, "created_at": "2026-10-08T23:00:00Z",
            "updated_at": merged_at or "2026-10-09T00:00:00Z", "labels": [{"name": n} for n in labels],
            "head": {"ref": ref or f"issue/{number}-x", "sha": "f" * 40}, "merged_by": {"login": by}}


VERIFIED = [{"head_sha": "e" * 40, "event": "workflow_dispatch", "status": "completed", "conclusion": "success"}]


def _closed_by(login):
    return [{"event": "closed", "actor": {"login": login}, "created_at": "2026-10-09T01:00:00Z"}]


# --------------------------------------------------------------------------- #
# the four defects of 2026-10-08/09
# --------------------------------------------------------------------------- #

def test_defect1_a_merge_leg_that_always_fails_is_broken_even_though_merges_happen():
    f, findings = report("defect1_merge_leg_422")
    leg = f["agent-merge workflow_run leg"]
    assert leg.verdict == lo.BROKEN
    assert "4 of 4 runs failed" in leg.sentence
    assert "pull_request_target leg alone has been succeeding" in leg.sentence
    assert any("37878770889" in e for e in leg.evidence)
    # the working leg must not excuse the broken one, nor be called broken itself
    assert f["agent-merge pull_request_target leg"].verdict == lo.OK
    assert lo.exit_code(findings) == 1


def test_defect2_close_step_that_403s_leaves_the_issue_open_and_says_why():
    f, findings = report("defect2_close_forbidden")
    close = f["close-on-evidence"]
    assert close.verdict == lo.BROKEN
    assert "#90" in close.sentence and "still open" in close.sentence
    assert "denied" in close.sentence and "403" in close.sentence
    assert lo.exit_code(findings) == 1


def test_defect3_a_403_in_a_continue_on_error_step_is_not_a_green_run():
    # Every agent-work and agent-discover run here CONCLUDED SUCCESS; only the
    # job log says the measurement fetch was refused.
    f, findings = report("defect3_measurement_403")
    for loop in ("agent-work", "agent-discover"):
        rec = f[f"{loop} measurement receipt"]
        assert rec.verdict == lo.BROKEN, loop
        assert "received no measurement" in rec.sentence and "403" in rec.sentence
    assert f["agent-work"].verdict == lo.OK, "the runs themselves did succeed; that is the trap"
    assert lo.exit_code(findings) == 1


def test_defect4_close_on_evidence_that_closed_nothing_is_broken_and_prints_the_refs_line():
    # Recorded: PR 312 and issue 304's events. #304 was closed by a human.
    f, findings = report("defect4_close_declined")
    close = f["close-on-evidence"]
    assert close.verdict == lo.BROKEN
    assert "#304" in close.sentence and "closed by mahAnuj, not by the loop" in close.sentence
    assert "claims no issue" in close.sentence
    # the report does not adjudicate intent: the Refs line is shown verbatim
    assert any("Refs #304 (agent merge will close with evidence after deploy)" in e for e in close.evidence)
    assert lo.exit_code(findings) == 1


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #

def test_healthy_week_is_all_ok_and_exits_zero():
    f, findings = report("healthy")
    assert [x for x in findings if x.verdict in (lo.BROKEN, lo.UNKNOWN)] == []
    assert lo.exit_code(findings) == 0
    assert f["agent-merge outcome"].verdict == lo.OK
    assert f["close-on-evidence"].verdict == lo.OK


def test_empty_week_is_idle_not_broken():
    # No PRs, no gates, no labels: the expected set is empty, so nothing is owed.
    f, findings = report("empty_week")
    for loop in ("agent-merge workflow_run leg", "agent-merge pull_request_target leg", "agent-merge outcome",
                 "agent-merge post-merge verification", "close-on-evidence"):
        assert f[loop].verdict == lo.IDLE, loop
    # agent-work ran twice, opened nothing, and left a cannot-reproduce trace each time: legitimate.
    assert f["agent-work"].verdict == lo.IDLE
    assert lo.exit_code(findings) == 0


def test_unreadable_evidence_is_unknown_exits_two_and_is_never_green():
    # `forbidden` is searched first, so every runs endpoint answers 403
    _, findings = report("forbidden")
    assert {x.verdict for x in findings} == {lo.UNKNOWN}
    assert {x.loop for x in findings} == set(lo.LOOPS)
    assert all("403" in x.sentence for x in findings)
    assert lo.exit_code(findings) == 2


def test_unknown_never_masks_broken(tmp_path):
    (tmp_path / "actions_workflows_agent-measure.yml_runs.error").write_text("403 nope\n")
    f, findings = report("defect1_merge_leg_422", tmp_path)
    assert f["agent-measure"].verdict == lo.UNKNOWN
    assert f["agent-merge workflow_run leg"].verdict == lo.BROKEN
    assert lo.exit_code(findings) == 1


def test_a_report_bug_surfaces_as_unknown_not_a_stack_trace(monkeypatch):
    monkeypatch.setitem(lo.LOOPS, "agent-design", lambda s, w: 1 / 0)
    f, findings = report("healthy")
    assert f["agent-design"].verdict == lo.UNKNOWN and "ZeroDivisionError" in f["agent-design"].sentence
    assert lo.exit_code(findings) == 2


def test_in_flight_work_is_excluded_not_broken():
    done = _run(1, "workflow_run", "success", "2026-10-09T10:00:00Z", "2026-10-09T10:01:00Z")
    running = _run(2, "workflow_run", None, "2026-10-10T11:50:00Z", "2026-10-10T11:51:00Z", status="in_progress")
    recent_gate = _run(3, "pull_request", "success", "2026-10-10T11:40:00Z", "2026-10-10T11:50:00Z")
    legs = lo.classify_merge_legs([done, running], [recent_gate], [], WINDOW)
    wr = next(x for x in legs if "workflow_run" in x.loop)
    # a gate that finished 10 minutes before the window closed is not owed a merge yet,
    # and a run still going is neither a success nor a failure
    assert wr.verdict == lo.OK and "1 of 1 runs succeeded" in wr.sentence
    only_running = lo.classify_merge_legs([running], [recent_gate], [], WINDOW)
    assert next(x for x in only_running if "workflow_run" in x.loop).verdict == lo.IDLE

    # and a PR labelled qa-pass 20 minutes ago is not "stranded"
    pr = {**_pr(7, merged_at=None), "state": "open", "checks": [{"name": "gates", "status": "completed", "conclusion": "success"}]}
    fresh = [{"pr": 7, "created_at": "2026-10-10T11:40:00Z"}]
    assert lo.classify_merge_outcome([pr], fresh, WINDOW).verdict == lo.OK
    old = [{"pr": 7, "created_at": "2026-10-10T06:00:00Z"}]
    stranded = lo.classify_merge_outcome([pr], old, WINDOW)
    assert stranded.verdict == lo.BROKEN and "agent-merge did not act" in stranded.sentence


def test_a_leg_that_never_fired_is_broken():
    gate = _run(3, "pull_request", "success", "2026-10-09T10:00:00Z", "2026-10-09T10:05:00Z")
    legs = lo.classify_merge_legs([], [gate], [], WINDOW)
    wr = next(x for x in legs if "workflow_run" in x.loop)
    assert wr.verdict == lo.BROKEN and "never fired" in wr.sentence


def test_success_with_no_report_commit_is_broken_not_idle():
    run = _run(10, "schedule", "success", "2026-10-09T21:00:00Z", "2026-10-09T21:30:00Z")
    nothing = lo.classify_report_loop("agent-measure", [run], [], WINDOW)
    assert nothing.verdict == lo.BROKEN
    assert "concluded success but produced nothing" in nothing.sentence
    # same loop, even with "0 issues" on discover: the report is the contract
    assert lo.classify_report_loop("agent-discover", [run], [], WINDOW, issues_created=0).verdict == lo.BROKEN
    got = lo.classify_report_loop("agent-measure", [run], [_commit("2026-10-09T21:31:00Z")], WINDOW)
    assert got.verdict == lo.OK
    # a commit from some OTHER run's window does not count
    other = lo.classify_report_loop("agent-measure", [run], [_commit("2026-10-08T21:31:00Z")], WINDOW)
    assert other.verdict == lo.BROKEN


def test_discover_with_a_report_and_no_issues_is_idle_not_broken():
    run = _run(10, "schedule", "success", "2026-10-09T21:00:00Z", "2026-10-09T21:30:00Z")
    f = lo.classify_report_loop("agent-discover", [run], [_commit("2026-10-09T21:31:00Z")], WINDOW, issues_created=0)
    assert f.verdict == lo.IDLE


def test_none_yet_is_broken_only_while_agent_measure_has_succeeded():
    receipts = [(1, lo.NONE_YET), (2, lo.NONE_YET)]
    assert lo.classify_receipts("agent-work", receipts, measure_successes=3).verdict == lo.BROKEN
    assert lo.classify_receipts("agent-work", receipts, measure_successes=0).verdict == lo.IDLE
    mixed = lo.classify_receipts("agent-work", [(1, lo.RECEIVED), (2, lo.UNKNOWN)], 3)
    assert mixed.verdict == lo.UNKNOWN, "an unreadable log is not a received measurement"
    assert lo.classify_receipts("agent-work", [(1, lo.RECEIVED)], 3).verdict == lo.OK


def test_work_run_that_succeeds_with_no_pr_and_no_trace_is_a_silent_success():
    run = _run(20, "schedule", "success", "2026-10-09T23:00:00Z", "2026-10-10T00:50:00Z")
    silent = lo.classify_work([run], [], [], WINDOW)
    assert silent.verdict == lo.BROKEN and "no PR and no cannot-reproduce/needs-evidence trace" in silent.sentence
    traced = lo.classify_work([run], [], [{"at": "2026-10-09T23:30:00Z", "what": "comment"}], WINDOW)
    assert traced.verdict == lo.IDLE


def test_measurement_receipt_reads_output_not_the_echoed_script():
    # Every one of these logs CONTAINS the words "no prior measurement" and
    # "measurement from run" -- in the echoed script source. Only the output counts.
    assert lo.measurement_receipt((FIX / "defect3_measurement_403" / "actions_jobs_94011_logs.log").read_text()) == lo.DENIED
    assert lo.measurement_receipt((FIX / "healthy" / "actions_jobs_94011_logs.log").read_text()) == lo.RECEIVED
    assert lo.measurement_receipt("2026-10-09T01:00:00Z ##[group]Run actions/checkout@v4\n") == lo.UNKNOWN
    assert lo.measurement_receipt("") == lo.UNKNOWN


# --------------------------------------------------------------------------- #
# the Refs / closing-keyword logic
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("body, ref, expected, declined", [
    ("Closes #5", "issue/9-x", [5, 9], []),
    ("fixes #5 and resolved #6", "feat/x", [5, 6], []),
    ("", "issue/9-x", [9], []),
    ("Refs #9 -- does not close it", "issue/9-x", [], [9]),
    ("Refs #9, closes #9", "issue/9-x", [9], []),
    ("nothing", "feat/x", [], []),
])
def test_claimed_issues_mirrors_close_on_evidence(body, ref, expected, declined):
    c = lo.claimed_issues(_pr(1, body, ref))
    assert (c["expected"], c["declined"]) == (expected, declined)


def test_claimed_issues_patterns_are_the_workflows_patterns():
    # DRY guard: if the workflow's grep changes, this module's copy must too.
    wf = (ROOT / ".github" / "workflows" / "close-on-evidence.yml").read_text()
    assert "(clos(e|es|ed)|fix(e[sd])?|resolv(e|es|ed))[[:space:]]+#[0-9]+" in wf
    assert "refs?[[:space:]]+#[0-9]+" in wf
    assert "^issue/[0-9]+" in wf


def test_refs_decline_on_a_still_open_issue_is_not_a_shortfall():
    # PR #314 / issue #313: "Refs #313 -- does not close it". Deliberate, not a defect.
    pr = _pr(314, "Refs #313 -- does not close it.", "issue/313-gate")
    f = lo.classify_close([pr], VERIFIED, [], {313: []}, WINDOW)
    assert f.verdict == lo.OK and "deliberately declined" in f.sentence


def test_a_closing_keyword_closed_by_a_human_is_still_a_shortfall():
    pr = _pr(5, "Closes #5")
    f = lo.classify_close([pr], VERIFIED, [], {5: _closed_by("someone")}, WINDOW)
    assert f.verdict == lo.BROKEN and "closed by someone, not by the loop" in f.sentence
    ok = lo.classify_close([pr], VERIFIED, [], {5: _closed_by("github-actions[bot]")}, WINDOW)
    assert ok.verdict == lo.OK


def test_a_red_or_missing_verification_owes_no_close_but_the_missing_one_is_flagged():
    pr = _pr(5, "Closes #5")
    red = [{**VERIFIED[0], "conclusion": "failure"}]
    assert lo.classify_close([pr], red, [], {}, WINDOW).verdict == lo.IDLE
    mile = lo.classify_last_mile([pr], [], WINDOW)
    assert mile.verdict == lo.BROKEN and "#5" in mile.sentence
    assert lo.classify_last_mile([pr], red, WINDOW).verdict == lo.OK
    human = _pr(6, "Closes #6", by="mahAnuj")
    assert lo.classify_last_mile([human], [], WINDOW).verdict == lo.IDLE


# --------------------------------------------------------------------------- #
# the report's own machinery
# --------------------------------------------------------------------------- #

def test_loops_are_pinned():
    assert set(lo.LOOPS) == {"agent-merge", "close-on-evidence", "agent-work",
                             "agent-measure", "agent-discover", "agent-design"}


def test_min_runs_agrees_with_the_cron_lines():
    for loop, per_week in lo.MIN_RUNS.items():
        text = (ROOT / ".github" / "workflows" / f"{loop}.yml").read_text()
        cron = re.search(r'cron:\s*"([^"]+)"', text).group(1).split()
        daily = cron[2] == "*" and cron[4] == "*"
        assert (per_week >= 5) == daily, f"{loop}: cron {cron} vs MIN_RUNS {per_week}"


def test_the_report_paths_and_log_anchor_match_the_workflows_they_watch():
    for loop, path in lo.REPORT_PATH.items():
        text = (ROOT / ".github" / "workflows" / f"{loop}.yml").read_text()
        assert path in text, f"{loop}.yml no longer writes {path}"
    for loop in ("agent-work", "agent-discover"):
        text = (ROOT / ".github" / "workflows" / f"{loop}.yml").read_text()
        assert f"gh run list --workflow {lo.MEASURE_ANCHOR}" in text and "Fetch the latest measurement" in text


def test_gh_pagination_output_is_parsed_without_slurp():
    assert lo._parse_stream('[1,2]\n[3]') == [[1, 2], [3]]
    assert lo._merge_pages(lo._parse_stream('[1,2]\n[3]')) == [1, 2, 3]
    merged = lo._merge_pages(lo._parse_stream('{"total_count":3,"workflow_runs":[1,2]}{"total_count":3,"workflow_runs":[3]}'))
    assert merged["workflow_runs"] == [1, 2, 3]
    assert lo._merge_pages(lo._parse_stream("")) == []


def test_fixture_keys_drop_paging_but_keep_what_selects_data():
    assert lo.fixture_key("actions/workflows/agent-merge.yml/runs?per_page=100&created=a..b") \
        == "actions_workflows_agent-merge.yml_runs"
    assert lo.fixture_key("commits?path=measurements/discover/latest.md&since=x") \
        == "commits__path-measurements_discover_latest.md"
    assert lo.fixture_key("pulls?state=all&sort=updated") == "pulls__state-all"


def test_a_missing_fixture_is_a_404_not_an_empty_answer():
    with pytest.raises(lo.ApiError) as e:
        lo.FixtureSource([FIX / "empty_week"]).get("pulls/9999")
    assert e.value.status == 404


def test_every_fixture_is_listed_in_the_manifest_and_says_whether_it_was_recorded():
    manifest = json.loads((FIX / "MANIFEST.json").read_text())
    on_disk = {str(p.relative_to(FIX)) for p in FIX.rglob("*") if p.is_file() and p.name != "MANIFEST.json"}
    assert on_disk == set(manifest)
    assert all(isinstance(v["recorded"], bool) and v["note"] for v in manifest.values())
    recorded = sorted(k for k, v in manifest.items() if v["recorded"])
    # honesty pin: only data actually fetched from the API may claim it
    assert recorded == ["defect4_close_declined/issues_304_events.json",
                        "defect4_close_declined/pulls_312.json",
                        "healthy/commits__path-measurements_discover_latest.md.json"]


def test_the_script_is_stdlib_only():
    tree = ast.parse((ROOT / "scripts" / "report_loop_outcomes.py").read_text())
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= set(sys.stdlib_module_names), mods - set(sys.stdlib_module_names)


def test_cli_writes_the_report_and_returns_the_exit_code(tmp_path, capsys):
    out = tmp_path / "out"
    code = lo.main([*ARGS, "--out", str(out), "--fixtures", str(FIX / "defect1_merge_leg_422"), str(FIX / "healthy")])
    assert code == 1
    md = (out / "report.md").read_text()
    assert "agent-merge workflow_run leg: 4 of 4 runs failed" in md
    assert md in capsys.readouterr().out
    findings = json.loads((out / "findings.json").read_text())
    assert {f["loop"] for f in findings} >= {"agent-merge workflow_run leg", "close-on-evidence"}
    assert lo.main([*ARGS, "--fixtures", str(FIX / "healthy")]) == 0


# --------------------------------------------------------------------------- #
# the workflow that runs it
# --------------------------------------------------------------------------- #

WORKFLOW = ROOT / ".github" / "workflows" / "loop-outcomes.yml"


def _scopes_needed() -> dict[str, str]:
    """Scopes named in the script header's endpoint table: `... ... actions: read`."""
    doc = ast.get_docstring(ast.parse((ROOT / "scripts" / "report_loop_outcomes.py").read_text()))
    return dict(re.findall(r"\.\s+([a-z-]+): (read|write)\s*$", doc, re.M))


def _scopes_granted() -> dict[str, str]:
    block = re.search(r"^    permissions:\n((?:      [a-z-]+: (?:read|write).*\n)+)", WORKFLOW.read_text(), re.M)
    return dict(re.findall(r"^      ([a-z-]+): (read|write)", block.group(1), re.M))


def test_workflow_grants_every_scope_the_scripts_endpoints_need():
    # The static gate (#315) cannot see `gh api` inside the script, so the table in
    # the script header is the only statement of what it needs. A scope missing here
    # makes the report say UNKNOWN for the loop it cannot read.
    needed, granted = _scopes_needed(), _scopes_granted()
    assert set(needed) == {"actions", "pull-requests", "issues", "contents", "checks"}, needed
    rank = {"read": 1, "write": 2}
    for scope, level in needed.items():
        assert scope in granted and rank[granted[scope]] >= rank[level], f"{scope}: needs {level}, granted {granted.get(scope)}"
    assert granted["issues"] == "write", "the standing report issue is created and commented on"


def test_workflow_cron_collides_with_no_other_workflow():
    mine = re.search(r'cron:\s*"([^"]+)"', WORKFLOW.read_text()).group(1).split()
    for other in (ROOT / ".github" / "workflows").glob("*.yml"):
        if other == WORKFLOW:
            continue
        for cron in re.findall(r'cron:\s*[\'"]([^\'"]+)[\'"]', other.read_text()):
            c = cron.split()
            same_day = c[4] in ("*", mine[4]) or mine[4] == "*"
            assert not (c[:2] == mine[:2] and same_day), f"{other.name} fires at {cron}, as does loop-outcomes"


def test_workflow_takes_since_and_until_and_the_script_accepts_them():
    text = WORKFLOW.read_text()
    assert re.search(r"workflow_dispatch:\n    inputs:\n      since:", text) and "      until:" in text
    assert 'IN_SINCE: ${{ github.event.inputs.since }}' in text
    # inputs reach the shell through env, never interpolated into the script text
    assert "${{ github.event.inputs" not in text.split("steps:", 1)[1]
    for flag in ("--since", "--until", "--out"):
        assert flag in text and flag in (ROOT / "scripts" / "report_loop_outcomes.py").read_text()


def test_workflow_posts_even_when_the_report_step_fails_and_never_closes():
    text = WORKFLOW.read_text()
    publish = text.split("name: Post to the standing report issue", 1)[1].split("upload-artifact", 1)[0]
    assert "if: always()" in text.split("name: Post to the standing report issue", 1)[1][:60]
    assert "gh issue comment" in publish and "gh issue create" in publish
    assert "gh issue close" not in text, "closing is a human decision"
    assert "GH_TOKEN: ${{ github.token }}" in text
