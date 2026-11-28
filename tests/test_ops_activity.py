"""The Recent activity data for /admin/ops Overview (#1133 slice 2d, `ops_activity.py`).

Unit tests on hand-written fixtures: no network, no template (the page tests are
`tests/test_ops_activity_page.py`). Expected states, words and hrefs are WRITTEN OUT BY
HAND, never derived from the module's own tables, so a mutated table is red.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from astro_ai import ops_activity as A
from astro_ai import ops_data, ops_tabs

IST = ops_data.IST
NOW = datetime(2026, 11, 28, 12, 0, 0, tzinfo=timezone.utc).astimezone(IST)
REPO = "https://github.com/mahAnuj/astro-ai"
KEYS = {"state", "error", "active", "chips", "rows", "reason", "empty_text", "notes",
        "skipped", "skipped_text", "as_of", "live_text", "view_all"}
ROW_KEYS = {"kind", "state", "word", "title", "subtitle", "type_label", "when", "at_ist",
            "iso", "href"}
LINKS = ops_tabs.tab_links("overview", 7, "")


def _t(minutes_ago: int) -> str:
    return (NOW.astimezone(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cycle(n=0, outcome="shipped", kind="issue", pr=None, run=None, issue=None, minutes=30, **kw):
    return {"run": run, "workflow": "agent-work", "started": _t(n), "outcome": outcome,
            "kind": kind, "pr": pr, "issue": issue, "minutes": minutes, **kw}


def _wf(name, n=0, health="green", concl="success", display=None):
    return {"workflow": name, "display": display or name[:-4], "last_run": _t(n),
            "last_conclusion": concl, "last_run_health": health}


def _issue(num, n=0, blocked=False, title=None):
    return {"number": num, "title": title or f"Issue title {num}", "created": _t(n),
            "blocked": blocked, "type": "bug", "priority": "low"}


def _ops(cycles=(), wfs=(), issues=(), live=False, shipped=(), failed=(), **extra):
    o = {"now_ist": NOW,
         "loop": {"ok": True, "rows": list(cycles), "today_live": live,
                  "today_shipped": list(shipped), "today_failed": list(failed)},
         "agents": {"ok": True, "loops": list(wfs)},
         "issues": {"ok": True, "rows": list(issues)},
         "ages": {"Delivery": {"text": "5h ago"}, "Team": {"text": "5h ago"},
                  "Backlog": {"text": "2h ago"}}}
    o.update(extra)
    return o


def _titles(d):
    return [r["title"] for r in d["rows"]]


# --- pick_filter ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,want", [
    ("agents", "agents"), ("Workflows", "workflows"), ("  ISSUES ", "issues"), ("all", "all"),
    ("zzz", "all"), ("", "all"), (None, "all"), (["agents"], "all"), (b"agents", "all"),
    ("agents&x=1", "all"), ("deployments", "all")])
def test_pick_filter_is_a_membership_test_and_never_raises(raw, want):
    assert A.pick_filter(raw) == want


# --- one row per kind, written out by hand -------------------------------------------------

@pytest.mark.parametrize("outcome,state,word", [
    ("shipped", "ok", "shipped"), ("pr open", "watch", "PR open"), ("failed", "bad", "failed"),
    ("nothing", "info", "nothing to ship"), ("judged", "info", "judged"),
    ("unknown", "watch", "outcome unknown"), ("exploded", "unavailable", "outcome not recognised")])
def test_each_cycle_outcome_has_its_state_and_word(outcome, state, word):
    d = A.build(_ops(cycles=[_cycle(outcome=outcome, pr=7, issue=5)]), LINKS, "agents")
    r = d["rows"][0]
    assert (r["state"], r["word"]) == (state, word)
    assert r["title"] == "Build cycle on issue #5 and PR #7"
    assert (r["kind"], r["type_label"]) == ("agent", "Agent")


@pytest.mark.parametrize("kind,title", [
    ("issue", "Build cycle"), ("ranked", "Ranked build cycle"), ("qa-round", "QA round"),
    ("fix-pr", "Fix cycle"), ("unknown", "Agent cycle"), ("???", "Agent cycle")])
def test_each_cycle_kind_has_its_title(kind, title):
    assert A.build(_ops(cycles=[_cycle(kind=kind)]), LINKS, "agents")["rows"][0]["title"] == title


def test_a_cycle_row_carries_its_time_in_four_forms_and_its_subtitle():
    r = A.build(_ops(cycles=[_cycle(n=90, minutes=49.2)]), LINKS, "agents")["rows"][0]
    assert r["when"] == "1h ago" and r["subtitle"] == "agent-work · 49 min"
    assert r["iso"] == _t(90) and r["at_ist"].endswith("IST") is False and ":" in r["at_ist"]
    assert set(r) == ROW_KEYS


def test_a_cycle_links_its_pr_before_its_run_and_neither_gives_no_link():
    def href(**kw):
        return A.build(_ops(cycles=[_cycle(**kw)]), LINKS, "agents")["rows"][0]["href"]
    assert href(pr=12, run=99) == f"{REPO}/pull/12"
    assert href(run=99) == f"{REPO}/actions/runs/99"
    assert href() == ""


@pytest.mark.parametrize("bad", [True, 0, -3, "7", 1.5, None, [1], {"a": 1}])
def test_these_are_not_ids_so_they_never_make_a_link(bad):
    d = A.build(_ops(cycles=[_cycle(pr=bad, run=bad, issue=bad)],
                     issues=[dict(_issue(1), number=bad)]), LINKS)
    assert [r["href"] for r in d["rows"]] == ["", ""]
    assert "#" not in " ".join(r["title"] for r in d["rows"] if r["kind"] == "agent")


def test_the_workflow_row_uses_the_rings_own_words_and_its_workflow_page():
    wfs = [_wf("pr-gates.yml", 5, "green"), _wf("agent-discover.yml", 6, "red", "failure"),
           _wf("agent-work.yml", 7, "running", "in_progress"), _wf("loop-outcomes.yml", 8, "amber", "failure"),
           _wf("x.yml", 9, "purple")]
    d = A.build(_ops(wfs=wfs), LINKS, "workflows")
    got = {r["title"]: (r["state"], r["word"], r["subtitle"], r["href"]) for r in d["rows"]}
    assert got["pr-gates"] == ("ok", "last run green", "last conclusion: success",
                               f"{REPO}/actions/workflows/pr-gates.yml")
    assert got["agent-discover"][:3] == ("bad", "last run red", "last conclusion: failure")
    assert got["agent-work"][:2] == ("running", "running at last collection")
    assert got["loop-outcomes"][:2] == ("watch", "last run amber")
    assert got["x"][:2] == ("unavailable", "unavailable")
    assert {r["type_label"] for r in d["rows"]} == {"Workflow"}


def test_an_issue_is_watch_when_blocked_and_still_open_otherwise_and_links_by_number():
    d = A.build(_ops(issues=[_issue(11, 5, blocked=True), _issue(12, 6)]), LINKS, "issues")
    assert [(r["title"], r["state"], r["word"], r["href"], r["subtitle"]) for r in d["rows"]] == [
        ("Issue title 11", "watch", "blocked", f"{REPO}/issues/11", "#11 · bug · low"),
        ("Issue title 12", "info", "still open", f"{REPO}/issues/12", "#12 · bug · low")]
    assert d["rows"][0]["type_label"] == "Issue"


def test_issues_are_newest_filed_first_not_in_file_order():
    d = A.build(_ops(issues=[_issue(1, 300), _issue(2, 10), _issue(3, 100)]), LINKS, "issues")
    assert [r["href"][-1] for r in d["rows"]] == ["2", "3", "1"]


# --- bounded rows ---------------------------------------------------------------------------

def test_each_view_is_exactly_eight_rows_from_thirty_inputs_newest_first():
    o = _ops(cycles=[_cycle(n=10 + i, pr=100 + i) for i in range(30)],
             wfs=[_wf(f"w{i}.yml", 200 + i) for i in range(30)],
             issues=[_issue(1000 + i, 400 + i) for i in range(30)])
    for key in ("agents", "workflows", "issues"):
        d = A.build(o, LINKS, key)
        assert len(d["rows"]) == 8, key
        isos = [r["iso"] for r in d["rows"]]
        assert isos == sorted(isos, reverse=True), key
    assert [r["href"].rsplit("/", 1)[1] for r in A.build(o, LINKS, "agents")["rows"]] == \
        [str(100 + i) for i in range(8)]


def test_all_is_the_eight_newest_across_kinds_and_the_other_views_still_fill():
    # The newest eight overall are all workflows; Agents and Issues must still show theirs.
    o = _ops(cycles=[_cycle(n=1000 + i, pr=100 + i) for i in range(10)],
             wfs=[_wf(f"w{i}.yml", 1 + i) for i in range(10)],
             issues=[_issue(500 + i, 2000 + i) for i in range(10)])
    allv = A.build(o, LINKS, "all")
    assert [r["kind"] for r in allv["rows"]] == ["workflow"] * 8
    isos = [r["iso"] for r in allv["rows"]]
    assert isos == sorted(isos, reverse=True)
    assert len(A.build(o, LINKS, "agents")["rows"]) == 8
    assert len(A.build(o, LINKS, "issues")["rows"]) == 8
    mixed = A.build(_ops(cycles=[_cycle(n=1, pr=1)], wfs=[_wf("w.yml", 2)], issues=[_issue(3, 3)]), LINKS)
    assert [r["kind"] for r in mixed["rows"]] == ["agent", "workflow", "issue"]


def test_the_agents_view_holds_only_agent_rows_and_the_workflows_view_only_workflow_rows():
    o = _ops(cycles=[_cycle(n=5, pr=1)], wfs=[_wf("w.yml", 6)], issues=[_issue(3, 7)])
    assert {r["kind"] for r in A.build(o, LINKS, "agents")["rows"]} == {"agent"}
    assert {r["kind"] for r in A.build(o, LINKS, "workflows")["rows"]} == {"workflow"}
    assert {r["kind"] for r in A.build(o, LINKS, "issues")["rows"]} == {"issue"}


def test_titles_and_subtitles_are_cut_and_stripped_of_newlines_and_control_characters():
    long = "x" * 500
    d = A.build(_ops(issues=[_issue(1, 1, title=long)]), LINKS, "issues")
    assert len(d["rows"][0]["title"]) == A.TITLE_MAX and d["rows"][0]["title"].endswith("…")
    d = A.build(_ops(wfs=[dict(_wf("a.yml"), display="  line one\nline\ttwo\x00\x07‮ end  ")]),
                LINKS, "workflows")
    assert d["rows"][0]["title"] == "line one line two end"
    assert A._text("y" * 500, A.SUB_MAX) == "y" * (A.SUB_MAX - 1) + "…"
    assert A._text("short", A.SUB_MAX) == "short" and A._text(7, 5) == "" and A._text(None, 5) == ""
    assert len(A.build(_ops(cycles=[dict(_cycle(), workflow="w" * 300)]), LINKS, "agents")
               ["rows"][0]["subtitle"]) <= A.SUB_MAX


def test_each_builder_hands_back_at_most_eight_rows_so_a_big_source_builds_only_eight():
    o = _ops(cycles=[_cycle(n=i, pr=i + 1) for i in range(50)], wfs=[_wf(f"w{i}.yml", i) for i in range(50)],
             issues=[_issue(i + 1, i) for i in range(50)])
    for fn in (A._agent_rows, A._workflow_rows, A._issue_rows):
        assert len(fn(o, NOW)[0]) == A.ROWS, fn.__name__


# --- the live merges, the live failures, and the supersede rule -----------------------------

def _merged(pr, n=1, by="loop", title=None):
    return {"pr": pr, "title": title if title is not None else f"PR title {pr}",
            "merged_at": _t(n), "by": by, "url": "javascript:alert(1)"}


def test_a_live_merge_shows_its_title_and_who_merged_it():
    d = A.build(_ops(live=True, shipped=[_merged(40, 5, "loop"), _merged(41, 6, "session"),
                                          _merged(42, 7, "other")]), LINKS, "agents")
    assert [(r["title"], r["subtitle"], r["state"], r["word"], r["href"]) for r in d["rows"]] == [
        ("PR title 40", "merged by the loop", "ok", "merged", f"{REPO}/pull/40"),
        ("PR title 41", "merged from a session", "ok", "merged", f"{REPO}/pull/41"),
        ("PR title 42", "merged", "ok", "merged", f"{REPO}/pull/42")]


def test_a_shipped_cycle_for_a_pr_already_merged_live_is_dropped_but_another_pr_is_kept():
    o = _ops(cycles=[_cycle(n=30, outcome="shipped", pr=40), _cycle(n=31, outcome="shipped", pr=99),
                     _cycle(n=32, outcome="pr open", pr=40)],
             live=True, shipped=[_merged(40, 5)])
    d = A.build(o, LINKS, "agents")
    assert [(r["title"], r["word"]) for r in d["rows"]] == [
        ("PR title 40", "merged"), ("Build cycle on PR #99", "shipped"),
        ("Build cycle on PR #40", "PR open")]


def test_when_today_is_not_live_the_snapshot_copies_of_today_are_ignored():
    o = _ops(cycles=[_cycle(n=30, pr=40)], live=False, shipped=[_merged(40, 5), _merged(41, 6)],
             failed=[{"run": 9, "workflow": "pr-gates", "conclusion": "failure", "started": _t(2)}],
             wfs=[_wf("pr-gates.yml", 60)])
    d = A.build(o, LINKS)
    assert sorted(_titles(d)) == ["Build cycle on PR #40", "pr-gates"]
    assert [r["state"] for r in d["rows"] if r["title"] == "pr-gates"] == ["ok"]
    for flag in (None, 1, "true", [True]):       # only the real True counts
        o["loop"]["today_live"] = flag
        assert len(A.build(o, LINKS)["rows"]) == 2, flag


def _fail(n, name="pr-gates", run=77):
    return {"run": run, "workflow": name, "conclusion": "failure", "started": _t(n), "url": "javascript:x"}


def test_a_newer_live_failure_replaces_that_workflows_row_and_an_older_one_does_not():
    wfs = [_wf("pr-gates.yml", 60, display="pr-gates"), _wf("agent-work.yml", 60, display="agent-work")]
    d = A.build(_ops(wfs=wfs, live=True, failed=[_fail(10, "PR-Gates")]), LINKS, "workflows")
    by = {r["title"]: r for r in d["rows"]}
    assert len(d["rows"]) == 2
    assert (by["PR-Gates"]["state"], by["PR-Gates"]["word"], by["PR-Gates"]["href"]) == (
        "bad", "failed", f"{REPO}/actions/runs/77")
    assert by["agent-work"]["state"] == "ok" and "pr-gates" not in by
    d = A.build(_ops(wfs=wfs, live=True, failed=[_fail(120)]), LINKS, "workflows")
    assert {r["title"]: r["state"] for r in d["rows"]} == {"pr-gates": "ok", "agent-work": "ok"}


def test_an_equally_old_live_failure_does_not_replace_the_row():
    d = A.build(_ops(wfs=[_wf("pr-gates.yml", 60)], live=True, failed=[_fail(60)]), LINKS, "workflows")
    assert [(r["title"], r["state"]) for r in d["rows"]] == [("pr-gates", "ok")]


def test_a_live_failure_with_no_matching_name_is_added_never_hidden():
    d = A.build(_ops(wfs=[_wf("a.yml", 60)], live=True, failed=[_fail(5, "Some other run")]),
                LINKS, "workflows")
    assert sorted((r["title"], r["state"]) for r in d["rows"]) == [("Some other run", "bad"), ("a", "ok")]


def test_the_newest_of_two_live_failures_of_one_workflow_wins():
    d = A.build(_ops(live=True, failed=[_fail(20, "x", 1), _fail(5, "x", 2), _fail(30, "x", 3)]),
                LINKS, "workflows")
    assert [r["href"] for r in d["rows"]] == [f"{REPO}/actions/runs/2"]


def test_live_failures_still_show_when_agents_json_is_unreadable_and_say_so():
    o = _ops(live=True, failed=[_fail(5)])
    o["agents"] = {"ok": False}
    d = A.build(o, LINKS, "workflows")
    assert d["state"] == "ok" and _titles(d) == ["pr-gates"]
    assert d["notes"] == ["Workflows: agents.json not read."]


# --- links are built, never taken from a row ------------------------------------------------

def test_no_row_string_reaches_an_href():
    evil = "javascript:alert(1)"
    o = _ops(cycles=[dict(_cycle(pr=3), url=evil, html_url=evil)],
             wfs=[dict(_wf("a.yml"), url=evil), dict(_wf("../x.yml")), dict(_wf("a b.yml")),
                  dict(_wf("A.yml")), dict(_wf("x.yml.evil"))],
             issues=[dict(_issue(1), url=evil, html_url=evil), dict(_issue(2), number="1/../x")],
             live=True, shipped=[dict(_merged(5), url=evil, html_url=evil)],
             failed=[dict(_fail(1, "z"), run="1/../x", html_url=evil)])
    hrefs = [r["href"] for k in ("agents", "workflows", "issues") for r in A.build(o, LINKS, k)["rows"]]
    assert hrefs and all(h == "" or h.startswith(REPO + "/") for h in hrefs), hrefs
    assert not any("javascript" in h or ".." in h or " " in h for h in hrefs)
    wf = {r["title"]: r["href"] for r in A.build(o, LINKS, "workflows")["rows"]}
    assert wf.pop("a") == f"{REPO}/actions/workflows/a.yml"
    assert len(wf) == 5 and set(wf.values()) == {""}, wf   # ../x, "a b", A, x.yml.evil and the live "z": no link
    assert [r["href"] for r in A.build(o, LINKS, "issues")["rows"] if r["title"] == "Issue title 2"] == [""]
    assert [r["href"] for r in A.build(o, LINKS, "workflows")["rows"] if r["title"] == "z"] == [""]


# --- states ---------------------------------------------------------------------------------

def test_a_readable_source_with_no_rows_says_empty_and_an_unreadable_one_says_unavailable():
    d = A.build(_ops(), LINKS, "issues")
    assert (d["state"], d["empty_text"], d["reason"], d["notes"]) == (
        "empty", "No issue activity in the data read", "", [])
    o = _ops()
    o["issues"] = {"ok": False, "rows": []}
    d = A.build(o, LINKS, "issues")
    assert d["state"] == "unavailable" and d["empty_text"] == "" and d["rows"] == []
    assert d["reason"] == "unavailable: issues.json not read"
    assert "no activity" not in d["reason"].lower() and "no issue" not in d["reason"].lower()


@pytest.mark.parametrize("key,text", [
    ("all", "No activity in the data read"), ("agents", "No agent activity in the data read"),
    ("workflows", "No workflow activity in the data read")])
def test_empty_texts(key, text):
    assert A.build(_ops(), LINKS, key)["empty_text"] == text


def test_a_half_empty_all_names_the_unreadable_source_and_never_reads_as_a_quiet_system():
    o = _ops(cycles=[_cycle(pr=1)])
    o["agents"] = None
    o["issues"] = {"ok": True, "rows": "nope"}
    d = A.build(o, LINKS)
    assert d["state"] == "ok" and len(d["rows"]) == 1
    assert d["notes"] == ["Workflows: agents.json not read.", "Issues: issues.json not read."]
    o["loop"] = None
    d = A.build(o, LINKS)
    assert d["state"] == "unavailable" and d["rows"] == []
    assert d["reason"] == "unavailable: loop.json not read; agents.json not read; issues.json not read"


def test_a_row_with_no_readable_time_is_left_out_and_counted_not_sorted_to_the_epoch():
    bad = [dict(_issue(9), created=c) for c in ("garbage", 123, None, "", "2026-11-28")]
    d = A.build(_ops(issues=[_issue(1, 5)] + bad, cycles=[dict(_cycle(), started="nope"), None, 3]),
                LINKS)
    assert [r["href"][-1] for r in d["rows"]] == ["1"]
    assert d["skipped"] == 8 and d["skipped_text"] == "8 rows left out: no readable time"
    one = A.build(_ops(issues=[dict(_issue(1), created="x")]), LINKS, "issues")
    assert one["skipped_text"] == "1 row left out: no readable time"
    assert A.build(_ops(issues=[_issue(1)]), LINKS, "issues")["skipped_text"] == ""


def test_the_freshness_lines_say_where_each_source_is_as_of_and_whether_today_is_live():
    d = A.build(_ops(live=True), LINKS)
    assert d["as_of"] == "agent cycles 5h ago, workflows 5h ago, issues 2h ago"
    assert d["live_text"] == "Today's merges and failed runs are live, read from GitHub."
    d = A.build(_ops(ages={"Team": {"text": "3d ago"}, "Delivery": None}), LINKS)
    assert d["as_of"] == "workflows 3d ago" and "not shown" in d["live_text"]
    assert A.build(_ops(ages=None), LINKS)["as_of"] == ""


# --- one source failing leaves the others ---------------------------------------------------

def test_each_source_failing_alone_leaves_the_others_and_sets_error(monkeypatch):
    def boom(ops, now):
        raise RuntimeError("boom")
    o = _ops(cycles=[_cycle(n=1, pr=1)], wfs=[_wf("w.yml", 2)], issues=[_issue(3, 3)])
    for name, survivors in (("agents", {"workflow", "issue"}), ("workflows", {"agent", "issue"}),
                            ("issues", {"agent", "workflow"})):
        monkeypatch.setitem(A._BUILDERS, name, boom)
        d = A.build(o, LINKS)
        assert d["error"] is True and d["state"] == "ok", name
        assert {r["kind"] for r in d["rows"]} == survivors, name
        assert d["notes"] == [f"{A._SOURCE[name]}: could not be computed."], name
        monkeypatch.undo()
    monkeypatch.setitem(A._BUILDERS, "issues", boom)
    d = A.build(o, LINKS, "issues")
    assert d["state"] == "unavailable" and d["error"] is True and d["reason"].startswith("unavailable: ")
    assert A.build(o, LINKS, "agents")["error"] is False       # a source not in the view cannot flag it


# --- garbage in, every key out --------------------------------------------------------------

GARBAGE_OPS = [None, {}, [], "x", 5, {"loop": None, "agents": None, "issues": None},
               {"loop": "x", "agents": [], "issues": 3},
               {"loop": {"ok": True, "rows": [None, 1, "x", []], "today_live": True,
                         "today_shipped": [None, 1, "x", {"pr": 1}], "today_failed": "x"}},
               {"loop": {"ok": True, "rows": [{"outcome": []}, {"started": 5}], "today_live": True,
                         "today_shipped": [{"merged_at": 5}], "today_failed": [{"started": 5}]}},
               {"agents": {"ok": False}}, {"agents": {"ok": True, "loops": "x"}},
               {"agents": {"ok": True, "loops": [None, 1, {"workflow": 5}, {"workflow": "a.yml"}]}},
               {"issues": {"ok": True, "rows": "a string"}},
               {"issues": {"ok": True, "rows": [None, 1, "x", [], {"created": "x"}]}},
               {"now_ist": "yesterday", "ages": "x"}, {"ages": {"Team": {"text": 5}}},
               _ops(cycles=[{"outcome": "shipped", "started": _t(1), "minutes": float("nan"),
                             "pr": float("inf"), "kind": ["x"], "workflow": {"a": 1}}])]


@pytest.mark.parametrize("links", [None, [], "x", 5, [None, 1, {"key": "overview"}, {"key": "overview", "href": 5}],
                                   LINKS])
@pytest.mark.parametrize("active", ["all", "agents", "workflows", "issues", None, ["x"], "zzz"])
def test_garbage_never_raises_and_always_returns_every_key(links, active):
    for ops in GARBAGE_OPS:
        d = A.build(ops, links, active)
        assert set(d) == KEYS, ops
        assert d["state"] in ("ok", "empty", "unavailable")
        assert len(d["rows"]) <= A.ROWS
        assert all(set(r) == ROW_KEYS for r in d["rows"])
        assert [c["label"] for c in d["chips"]] == ["All", "Agents", "Workflows", "Issues"]
        assert sum(c["current"] for c in d["chips"]) == 1


def test_the_last_resort_returns_every_key_too(monkeypatch):
    monkeypatch.setattr(A, "_now", lambda ops: 1 / 0)
    d = A.build(_ops(), LINKS, "issues")
    assert set(d) == KEYS and d["state"] == "unavailable" and d["error"] is True
    assert d["active"] == "issues" and d["rows"] == []


def test_an_empty_row_with_a_missing_workflow_and_a_non_string_display_still_builds():
    d = A.build(_ops(wfs=[dict(_wf("a.yml"), display=None), dict(_wf("b.yml"), display=5)]),
                LINKS, "workflows")
    assert sorted(_titles(d)) == ["a", "b"]


# --- the chips and the View all link --------------------------------------------------------

def test_chip_hrefs_keep_the_rails_window_and_day_and_exactly_one_is_current():
    d = A.build(_ops(), ops_tabs.tab_links("overview", 7, ""), "agents")
    assert [(c["key"], c["label"], c["href"], c["current"]) for c in d["chips"]] == [
        ("all", "All", "?tab=overview&window=7&activity=all#recent-activity", False),
        ("agents", "Agents", "?tab=overview&window=7&activity=agents#recent-activity", True),
        ("workflows", "Workflows", "?tab=overview&window=7&activity=workflows#recent-activity", False),
        ("issues", "Issues", "?tab=overview&window=7&activity=issues#recent-activity", False)]
    d = A.build(_ops(), ops_tabs.tab_links("overview", 7, "2026-11-20"), "zzz")
    assert d["active"] == "all" and d["chips"][0]["current"] is True
    assert d["chips"][2]["href"] == "?tab=overview&day=2026-11-20&activity=workflows#recent-activity"
    assert A.build(_ops(), None)["chips"][3]["href"] == "?tab=overview&activity=issues#recent-activity"


def test_deployments_is_not_a_chip_and_is_not_mentioned():
    d = A.build(_ops(), LINKS)
    assert "deploy" not in repr(d).lower()


def test_view_all_targets_the_tab_that_lists_that_kind_of_row():
    want = {"all": "runs", "agents": "runs", "workflows": "workflows", "issues": "backlog"}
    for key, tab in want.items():
        d = A.build(_ops(), LINKS, key)
        assert d["view_all"]["href"] == f"?tab={tab}&window=7", key
    assert A.build(_ops(), None, "issues")["view_all"]["href"] == "?tab=backlog"


# --- the real committed files, and speed -----------------------------------------------------

def test_on_the_real_committed_data_every_href_is_this_repos_and_no_row_has_a_bad_time(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops = ops_data.snapshot()
    for key in ("all", "agents", "workflows", "issues"):
        d = A.build(ops, ops_tabs.tab_links("overview", 7, ""), key)
        assert set(d) == KEYS and d["state"] == "ok" and d["error"] is False, key
        assert 1 <= len(d["rows"]) <= A.ROWS
        for r in d["rows"]:
            assert r["href"] == "" or r["href"].startswith("https://github.com/mahAnuj/astro-ai/"), r
            assert ops_data._ist(r["iso"]) is not None and r["when"] != "age unknown", r
            assert 0 < len(r["title"]) <= A.TITLE_MAX and len(r["subtitle"]) <= A.SUB_MAX
        isos = [r["iso"] for r in d["rows"]]
        assert isos == sorted(isos, reverse=True)


def test_build_over_five_thousand_loop_rows_stays_under_200_ms():
    o = _ops(cycles=[_cycle(n=i, pr=i + 1) for i in range(5000)],
             issues=[_issue(i + 1, i) for i in range(2000)], wfs=[_wf(f"w{i}.yml", i) for i in range(200)])
    t = time.perf_counter()
    d = A.build(o, LINKS)
    took = time.perf_counter() - t
    assert len(d["rows"]) == 8 and took < 0.2, took


# --- the route glue --------------------------------------------------------------------------

@pytest.mark.parametrize("q", ["?tab=overview", "?tab=overview&activity=agents", "?activity=zzz",
                               "?tab=agents&activity=issues", "?tab=overview&activity=%00&day=zz"])
def test_the_route_takes_activity_and_every_value_is_a_200_never_a_422(monkeypatch, q):
    import os
    from fastapi.testclient import TestClient
    from astro_ai import agent_status
    from astro_ai.main import app
    from astro_ai.routes import deps
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(agent_status, "snapshot",
                        lambda *a, **k: {"agents": [], "groups": [], "live": False, "counts": {}})
    seen = {}
    real = A.build

    def spy(ops, links, active="all"):
        seen["active"] = active
        return real(ops, links, active)
    monkeypatch.setattr(A, "build", spy)
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops" + q, auth=("admin", pw))
    assert r.status_code == 200
    if "tab=agents" in q:
        assert "active" not in seen                  # Overview alone pays for the panel
    else:
        assert seen["active"] == ("agents" if "activity=agents" in q else "all")
