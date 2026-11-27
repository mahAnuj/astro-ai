"""The loop ring, Agent health and System health (#1133 slice 2c, backend half).

`ops_loop_health.build(ops, agents_now, tabs_health, links)` derives all three panels from
dicts the page already holds. Synthetic inputs, with every expected state and word written
out by hand below, so a rule changed in the module fails here rather than moving the
expectation with it. The workflow filenames and the four health colours are the
collector's own (measurements/agents.json).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import agent_status, ops_data, ops_loop_health as L, ops_tabs  # noqa: E402

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
LINKS = ops_tabs.tab_links("overview", 7, "")
HREF = {k["key"]: k["href"] for k in LINKS}


def _loop(wf, health="green", concl="success", *, verdict="not-due-yet", cadence=None,
          last="2026-11-27T10:00:00Z", **extra):
    return {"workflow": wf, "verdict": verdict, "last_run": last, "last_conclusion": concl,
            "last_run_health": health, "cadence": cadence, **extra}


def _all_green():
    return [_loop("agent-measure.yml", cadence=["00 21 * * *", "23 09 * * *"]),
            _loop("agent-prioritise.yml", cadence=["00 17 * * 0"]),
            _loop("agent-discover.yml", cadence=["00 20 * * 1"]),
            _loop("agent-work.yml", cadence=["00 23 * * *"]),
            _loop("pr-gates.yml", cadence=["47 20 * * *"]),
            _loop("agent-merge.yml", verdict="on-demand"),
            _loop("verify-production.yml", cadence=["17 06 * * 1"]),
            _loop("loop-outcomes.yml", "amber", "failure", cadence=["30 03 * * 2"])]


def _ops(loops=None, *, agents_ok=True, app=None, team=None, alerts=None):
    return {
        "now_ist": NOW.astimezone(ops_data.IST),
        "agents": {"ok": agents_ok, "loops": _all_green() if loops is None else loops,
                   "alerts": alerts or []},
        "app": app if app is not None else {"ok": True, "measured": True, "days": 7,
                                            "error_rate": 0.0},
        "ages": {"Team": team or {"text": "14m ago", "stale": False}},
    }


def _cards(spec):
    """spec: {group: [state, ...]} -> an agent_status-shaped dict."""
    cards = [{"id": f"{g}{i}", "group": g, "state": s}
             for g, states in spec.items() for i, s in enumerate(states)]
    return {"agents": cards, "groups": list(agent_status.GROUPS), "live": True, "counts": {}}


OK_CARDS = _cards({"build": ["building", "blocked", "waiting", "standby"],
                   "decide": ["done"], "measure": ["done", "idle"], "operate": ["done"]})
HEALTH = {"state": "ok", "label": "System healthy", "detail": "No open findings", "count": 0}


def _build(ops=None, cards=OK_CARDS, health=HEALTH, links=LINKS):
    return L.build(_ops() if ops is None else ops, cards, health, links)


def _node(d, n):
    return d["ring"]["nodes"][n - 1]


def _sys(d, key):
    return next(r for r in d["system"]["rows"] if r["key"] == key)


# --------------------------------------------------------------- the ring

def test_seven_nodes_in_order_with_the_owners_names():
    d = _build()
    assert [(n["n"], n["name"]) for n in d["ring"]["nodes"]] == [
        (1, "Measure"), (2, "Decide"), (3, "Build"), (4, "Check"), (5, "Merge"),
        (6, "Ship & Verify"), (7, "Score")]
    assert len(d["ring"]["arrows"]) == 7
    assert [(a["from"], a["to"]) for a in d["ring"]["arrows"]][-1] == (7, 1)


def test_node_states_come_from_last_run_health_hand_computed():
    d = _build()
    assert [n["state"] for n in d["ring"]["nodes"]] == [
        "ok", "ok", "ok", "ok", "ok", "ok", "watch"]


def test_a_running_node_says_running_at_last_collection():
    ops = _ops([_loop(f, "running", "in_progress") if f == "agent-work.yml" else r
                for r in _all_green() for f in [r["workflow"]]])
    n = _node(_build(ops), 3)
    assert n["state"] == "running"
    assert n["word"] == "running at last collection"


def test_decide_is_the_worst_of_its_two_workflows():
    for other, want in (("red", "bad"), ("amber", "watch"), ("running", "running")):
        loops = [_loop("agent-discover.yml", other) if r["workflow"] == "agent-discover.yml"
                 else r for r in _all_green()]
        assert _node(_build(_ops(loops)), 2)["state"] == want


def test_loop_outcomes_amber_prints_failure_but_is_watch_not_bad():
    n = _node(_build(), 7)
    assert n["state"] == "watch"
    assert n["workflows"][0]["conclusion"] == "failure"


def test_state_is_never_taken_from_the_conclusion_string():
    # a `failure` conclusion with a green collector colour stays green
    loops = [_loop("agent-merge.yml", "green", "failure") if r["workflow"] == "agent-merge.yml"
             else r for r in _all_green()]
    assert _node(_build(_ops(loops)), 5)["state"] == "ok"


def test_an_absent_loop_is_unavailable_never_ok():
    loops = [r for r in _all_green() if r["workflow"] != "pr-gates.yml"]
    n = _node(_build(_ops(loops)), 4)
    assert n["state"] == "unavailable"
    assert n["workflows"][0]["word"].startswith("unavailable")


def test_one_missing_workflow_of_two_makes_the_step_unavailable_not_ok():
    loops = [r for r in _all_green() if r["workflow"] != "agent-prioritise.yml"]
    assert _node(_build(_ops(loops)), 2)["state"] == "unavailable"


def test_an_unknown_health_value_is_unavailable():
    loops = [_loop("agent-merge.yml", "purple") if r["workflow"] == "agent-merge.yml"
             else r for r in _all_green()]
    assert _node(_build(_ops(loops)), 5)["state"] == "unavailable"


def test_a_workflow_named_twice_is_unavailable_because_which_copy_is_right_is_unknowable():
    loops = _all_green() + [_loop("agent-merge.yml", "red")]
    assert _node(_build(_ops(loops)), 5)["state"] == "unavailable"


def test_agents_json_unread_makes_every_node_unavailable_with_the_reason():
    d = _build(_ops(agents_ok=False))
    assert d["ring"]["state"] == "unavailable"
    assert d["ring"]["reason"] == "unavailable: agents.json not read"
    assert [n["state"] for n in d["ring"]["nodes"]] == ["unavailable"] * 7


def test_the_legend_cadence_is_the_real_cron_or_on_events():
    d = _build()
    assert _node(d, 1)["workflows"][0]["cadence"] == "cron 00 21 * * *; 23 09 * * * (UTC)"
    assert _node(d, 5)["workflows"][0]["cadence"] == "on events"
    # the static caption beside the circle
    assert [n["caption"] for n in d["ring"]["nodes"]] == [
        "daily", "weekly", "back to back", "each PR push", "every 30 min", "each deploy",
        "weekly"]


def test_a_cron_that_is_not_a_cron_is_not_printed():
    loops = [_loop("agent-measure.yml", cadence=["<script>alert(1)</script>", "0 1 * * *"])
             if r["workflow"] == "agent-measure.yml" else r for r in _all_green()]
    t = _node(_build(_ops(loops)), 1)["workflows"][0]["cadence"]
    assert "script" not in t and "0 1 * * *" in t


@pytest.mark.parametrize("concl,printed", [("success", "success"), ("in_progress", "in progress"),
                                           ("<b>x</b>", "unknown"), ("X" * 40, "unknown"),
                                           (5, "unknown"), (["success"], "unknown")])
def test_a_conclusion_is_printed_only_if_it_is_a_short_lower_case_word(concl, printed):
    loops = [_loop("agent-merge.yml", concl=concl) if r["workflow"] == "agent-merge.yml"
             else r for r in _all_green()]
    assert _node(_build(_ops(loops)), 5)["workflows"][0]["conclusion"] == printed


def test_hrefs_come_only_from_links_and_static_workflow_urls():
    d = _build()
    assert [n["href"] for n in d["ring"]["nodes"]] == [
        HREF["workflows"], HREF["workflows"], HREF["runs"], HREF["workflows"],
        HREF["workflows"], HREF["workflows"], HREF["workflows"]]
    # a poisoned row cannot reach a url: it is built from the static filename
    loops = _all_green() + [_loop("javascript:alert(1)")]
    urls = [w["url"] for n in _build(_ops(loops))["ring"]["nodes"] for w in n["workflows"]]
    assert all(u.startswith("https://github.com/mahAnuj/astro-ai/actions/workflows/") and
               u.endswith(".yml") for u in urls)
    # and with no links at all, the hrefs are empty rather than invented
    assert {n["href"] for n in _build(links=[])["ring"]["nodes"]} == {""}


def test_the_ring_carries_its_own_aria_and_hidden_table_text():
    r = _build()["ring"]
    assert r["aria"].startswith("The engineering loop, seven steps in a ring:")
    for name in ("Measure", "Decide", "Build", "Check", "Merge", "Ship & Verify", "Score"):
        assert name in r["aria"]
    assert [t["n"] for t in r["table"]] == [1, 2, 3, 4, 5, 6, 7]
    assert r["table"][6]["result"] == "last run amber"
    assert r["as_of"] == "as of 14m ago"


def test_geometry_is_rounded_numbers_inside_the_viewbox():
    r = _build()["ring"]
    for n in r["nodes"]:
        for k in ("x", "y", "label_x", "name_y", "caption_y"):
            assert isinstance(n[k], float) and round(n[k], 1) == n[k]
        assert 0 < n["x"] < r["w"] and 0 < n["y"] < r["h"]
        assert 0 < n["caption_y"] < r["h"]
    assert all(a["d"].startswith("M ") and " A " in a["d"] for a in r["arrows"])


# ------------------------------------------------------------ agent health

def test_four_groups_from_the_data_with_hand_counted_rows():
    a = _build()["agents"]
    assert a["header"] == "8 cards · 4 groups"
    rows = {g["name"]: g for g in a["groups"]}
    assert [g["name"] for g in a["groups"]] == ["build", "decide", "measure", "operate"]
    assert rows["build"]["n"] == 4 and rows["build"]["state"] == "watch"
    assert rows["build"]["word"] == "1 blocked"
    assert rows["build"]["counts_text"] == "1 building · 1 standby · 1 blocked · 1 waiting"
    assert rows["measure"]["counts_text"] == "1 done · 1 idle"
    assert rows["decide"]["state"] == "ok" and rows["decide"]["word"] == "none failed"


def test_a_fifth_group_appears_when_the_data_has_one_and_is_not_invented_otherwise():
    spec = {"build": ["done"], "decide": ["done"], "measure": ["done"], "operate": ["done"]}
    assert len(_build(cards=_cards(spec))["agents"]["groups"]) == 4
    five = _cards({**spec, "on request": ["idle"]})
    names = [g["name"] for g in _build(cards=five)["agents"]["groups"]]
    assert names == ["build", "decide", "measure", "operate", "on request"]


def test_failed_outranks_blocked_and_counts_come_from_cards_not_the_counts_key():
    cards = _cards({"build": ["failed", "failed", "blocked"]})
    cards["counts"] = {"failed": 99}
    g = _build(cards=cards)["agents"]["groups"][0]
    assert (g["state"], g["word"]) == ("bad", "2 failed")
    assert g["counts_text"] == "1 blocked · 2 failed"


@pytest.mark.parametrize("bad", [None, {}, [], {"agents": []}, {"agents": "x"},
                                 {"agents": [{"group": None}]},
                                 {"agents": [None, 3, {"group": "build"}, {"state": "done"}]}])
def test_garbage_agent_status_is_unavailable_not_zeros(bad):
    a = _build(cards=bad)["agents"]
    assert a["state"] == "unavailable"
    assert a["reason"] == "unavailable: agent_status returned no agents"
    assert a["groups"] == []


def test_unreadable_cards_are_counted_as_skipped_beside_good_ones():
    cards = _cards({"build": ["done"]})
    cards["agents"] += [None, {"group": "build"}]
    a = _build(cards=cards)["agents"]
    assert a["state"] == "ok" and a["skipped"] == 2
    assert a["skipped_text"] == "2 cards skipped: missing group or state"


def test_live_false_says_last_known_not_live():
    cards = {**OK_CARDS, "live": False}
    assert _build(cards=cards)["agents"]["live_text"] == "last known, GitHub not read"
    assert _build()["agents"]["live_text"] == "live, read from GitHub"


# ----------------------------------------------------------- system health

def test_four_system_rows_in_order():
    assert [r["key"] for r in _build()["system"]["rows"]] == [
        "llm", "actions", "website", "monitoring"]


def test_llm_row_uses_the_one_threshold_definition():
    quiet = _sys(_build(), "llm")
    assert (quiet["state"], quiet["word"]) == ("ok", "no findings")
    assert quiet["detail"] == "no findings in the last 7 days"
    red = _ops(app={"ok": True, "measured": True, "days": 7, "error_rate": 50.0,
                    "errors": 5, "calls": 10})
    row = _sys(_build(red), "llm")
    assert row["state"] == "bad" and row["detail"] == "50.0% of LLM calls are erroring"
    amber = _ops(app={"ok": True, "measured": False, "days": 3})
    row = _sys(_build(amber), "llm")
    assert row["state"] == "watch" and row["detail"] == "No LLM calls recorded"
    assert row["as_of"] == "last 3 days"


def test_llm_row_is_unavailable_when_the_app_could_not_be_read():
    row = _sys(_build(_ops(app={"ok": False})), "llm")
    assert row["state"] == "unavailable" and row["word"].startswith("unavailable")
    assert row["href"] == HREF["monitoring"]


def test_actions_row_hand_computed_cases():
    ok = _sys(_build(), "actions")
    assert ok["state"] == "ok"
    assert "8 loops read" in ok["detail"]
    broken = _ops(_all_green() + [_loop("agent-x.yml", verdict="broken")])
    row = _sys(_build(broken), "actions")
    assert (row["state"], row["word"]) == ("bad", "1 broken")
    assert "agent-x" in row["detail"]
    missed = _ops(_all_green() + [_loop("agent-y.yml", verdict="missing-slots")])
    assert _sys(_build(missed), "actions")["state"] == "watch"
    failed = _ops(_all_green() + [_loop("agent-z.yml", "red", "failure")])
    assert _sys(_build(failed), "actions")["state"] == "watch"
    stale = _ops(team={"text": "30h ago", "stale": True})
    row = _sys(_build(stale), "actions")
    assert (row["state"], row["word"]) == ("watch", "collection stale")


def test_actions_row_does_not_call_loop_outcomes_amber_a_failure():
    # loop-outcomes is `failure` + `amber` by contract and must not trip the row
    assert _sys(_build(), "actions")["state"] == "ok"


def test_actions_row_unavailable_when_agents_json_is_unread():
    assert _sys(_build(_ops(agents_ok=False)), "actions")["state"] == "unavailable"


@pytest.mark.parametrize("concl,health,state,word", [
    ("success", "green", "ok", "last check passed"),
    ("failure", "red", "bad", "last check failure"),
    ("timed_out", "red", "bad", "last check timed out"),
    ("in_progress", "running", "running", "check running at last collection"),
    ("skipped", "amber", "watch", "last check skipped"),
])
def test_website_row_by_last_conclusion(concl, health, state, word):
    loops = [_loop("verify-production.yml", health, concl) if r["workflow"] ==
             "verify-production.yml" else r for r in _all_green()]
    row = _sys(_build(_ops(loops)), "website")
    assert (row["state"], row["word"]) == (state, word)


def test_website_row_is_stale_after_eight_days_and_not_before():
    def at(days):
        t = (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        loops = [_loop("verify-production.yml", last=t) if r["workflow"] ==
                 "verify-production.yml" else r for r in _all_green()]
        return _sys(_build(_ops(loops)), "website")
    assert L.PROD_STALE_DAYS == 8
    assert at(7)["state"] == "ok"
    assert (at(9)["state"], at(9)["word"]) == ("watch", "stale")


def test_website_row_missing_is_unavailable_and_never_reads_as_uptime():
    loops = [r for r in _all_green() if r["workflow"] != "verify-production.yml"]
    row = _sys(_build(_ops(loops)), "website")
    assert row["word"] == "unavailable: verify-production not in agents.json"
    ok = _sys(_build(), "website")
    assert "not an uptime monitor" in ok["detail"]
    assert ok["href"].endswith("/actions/workflows/verify-production.yml")


def test_monitoring_row_is_the_rail_block_unchanged():
    for h in ({"state": "bad", "label": "Needs attention", "detail": "2 red", "count": 2},
              {"state": "watch", "label": "Needs a look", "detail": "1 finding", "count": 1},
              ops_tabs.health([], 0, [])):
        row = _sys(_build(health=h), "monitoring")
        assert (row["state"], row["word"], row["detail"]) == (h["state"], h["label"], h["detail"])


def test_monitoring_row_unavailable_when_health_is_garbage():
    for h in (None, {}, {"state": "fine"}, {"state": "ok", "label": 3, "detail": "x"}):
        assert _sys(_build(health=h), "monitoring")["state"] == "unavailable"


def test_no_panel_says_operational_or_all_healthy():
    for d in (_build(), _build(_ops(agents_ok=False)), L.build(None, None, None, None)):
        text = repr(d).lower()
        assert "operational" not in text and "all healthy" not in text


# ---------------------------------------------------------------- garbage

GARBAGE = [None, 0, "x", [], {}, {"agents": None}, {"agents": {"ok": True, "loops": "x"}},
           {"agents": {"ok": True, "loops": [None, 3, {"workflow": 5}, {"verdict": []}]}},
           {"agents": {"ok": True, "loops": [{"workflow": "agent-merge.yml",
                                              "last_run": 5, "last_run_health": [],
                                              "last_conclusion": {}, "cadence": "x"}]},
            "app": 3, "ages": None, "now_ist": "yesterday"}]


@pytest.mark.parametrize("ops", GARBAGE)
def test_build_never_raises_and_always_returns_the_three_panels(ops):
    for cards in (None, {}, {"agents": [{"group": None}]}, "x", OK_CARDS):
        for health in (None, {}, "x", HEALTH):
            for links in (None, [], [None, 3, {"key": "runs"}], LINKS):
                d = L.build(ops, cards, health, links)
                assert set(d) == {"error", "ring", "agents", "system"}
                assert len(d["system"]["rows"]) == 4
                assert all(n["state"] in L._SEVERITY for n in d["ring"]["nodes"])
                assert all(r["state"] in ("ok", "watch", "bad", "running", "unavailable")
                           for r in d["system"]["rows"])


def test_garbage_ops_gives_unavailable_everywhere_not_ok():
    d = L.build(None, None, None, None)
    assert [n["state"] for n in d["ring"]["nodes"]] == ["unavailable"] * 7
    assert d["agents"]["state"] == "unavailable"
    assert [r["state"] for r in d["system"]["rows"]] == ["unavailable"] * 4


def test_a_panel_that_raises_degrades_alone_and_sets_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(L, "_app_alerts", boom)
    d = _build()
    assert d["error"] is True
    assert _sys(d, "llm")["state"] == "unavailable"
    assert _sys(d, "llm")["word"] == "unavailable: could not be computed"
    assert _sys(d, "monitoring")["state"] == "ok"        # the other rows survive
    assert [n["state"] for n in d["ring"]["nodes"]][0] == "ok"


def test_a_ring_that_raises_degrades_alone_and_sets_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(L, "_ring", boom)
    d = _build()
    assert d["ring"]["state"] == "unavailable" and d["agents"]["state"] == "ok"
    assert _sys(d, "llm")["state"] == "ok"
    assert d["error"] is True


def test_agent_health_that_raises_degrades_alone_and_sets_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(L, "_agent_health", boom)
    d = _build()
    assert d["agents"]["state"] == "unavailable" and d["ring"]["state"] == "ok"
    assert d["error"] is True


def test_the_ring_workflow_names_exist_as_workflow_files():
    wf = ROOT / ".github" / "workflows"
    for _n, _name, files, _cap, _tab in L.STEPS:
        for f in files:
            assert (wf / f).exists(), f
    assert L.PROD_WORKFLOW == "verify-production.yml"


def test_every_step_tab_is_a_real_tab():
    keys = {k for k, _ in ops_tabs.TABS}
    assert {tab for *_x, tab in L.STEPS} <= keys
