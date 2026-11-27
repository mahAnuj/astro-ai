"""The PRs-shipped bars and Key metrics rows (#1133 slice 2b, backend half).

`ops_trends.build(ops, kpis, links)` derives both from the dict `ops_data.snapshot()`
holds and the KPI row beside it. Synthetic inputs, with the answers written out by
hand in the constants below, so a rule changed in the module fails here rather than
moving the expectation with it. Dates: TODAY is 2026-11-25, so the KPI window is
2026-11-18..24 and the previous one 2026-11-11..17.
"""
from __future__ import annotations

import importlib.util
import itertools
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import ops_kpis, ops_tabs, ops_trends  # noqa: E402

TODAY = "2026-11-25"
_ids = itertools.count(5000)
LINKS = ops_tabs.tab_links("overview", 7, "")


def row(date, outcome="shipped", *, pr=None, kind="ranked"):
    return {"run": next(_ids), "date_ist": date, "time_ist": "12:00", "outcome": outcome,
            "kind": kind, "pr": pr, "issue": None, "minutes": 5.0, "trigger": "schedule",
            "attribution": "receipt"}


def loop_rows():
    return [
        row("2026-11-18", pr=101), row("2026-11-18", "nothing"),
        row("2026-11-19", pr=101),                      # PR 101 again: counts on the 18th only
        row("2026-11-19", pr=102),
        row("2026-11-20", "failed"),                    # runs, shipped nothing: a real 0
        # 2026-11-21: no rows at all -> "no runs"
        row("2026-11-22", pr=103), row("2026-11-22", pr=104),
        row("2026-11-23", "judged", kind="qa-round", pr=103),
        row("2026-11-24", pr=105),
        row("2026-11-10", pr=80),                       # outside the window
    ]


def gsc(end="2026-11-24", days=14, clicks=lambda i: 10 + i):
    from datetime import date, timedelta
    e = date.fromisoformat(end)
    return [{"date": (e - timedelta(days=days - 1 - i)).isoformat(), "clicks": clicks(i),
             "impressions": 100} for i in range(days)]


def flow_days(newest="2026-11-27", days=15, closed=lambda i: 5, closed_by=None):
    from datetime import date, timedelta
    e = date.fromisoformat(newest)
    return [{"date": (e - timedelta(days=days - 1 - i)).isoformat(), "opened": 1,
             "closed": closed(i),
             "closed_by": closed_by(i) if closed_by else {"close-on-evidence": 2, "owner": 1}}
            for i in range(days)]


def ops(rows=None, *, gsc_rows=None, days=None, flow=None, traffic_window=None):
    o = {"today_ist": TODAY, "loop": {"ok": True, "rows": loop_rows() if rows is None else rows},
         "agents": {"ok": True, "agents": {}},
         "traffic": {"gsc_rows": gsc() if gsc_rows is None else gsc_rows,
                     "window": traffic_window or ["2026-10-28", "2026-11-26"]},
         "issue_flow": flow if flow is not None else {
             "days": flow_days() if days is None else days, "age": {"text": "2h ago"}},
         "ages": {}}
    return o


def run(o=None, **kw):
    o = o or ops(**kw)
    k = ops_kpis.build(o)
    return ops_trends.build(o, k, LINKS), k


def metric(t, key):
    return next(m for m in t["metrics"] if m["key"] == key)


# --- the bars ------------------------------------------------------------------------

def test_the_seven_bars_add_up_to_the_prs_merged_card():
    t, k = run()
    card = next(c for c in k["cards"] if c["key"] == "prs")
    assert len(t["bars"]["cols"]) == 7
    assert sum(c["value"] or 0 for c in t["bars"]["cols"]) == card["value"] == 5
    assert t["bars"]["total"] == 5


def test_a_pr_shipped_on_two_days_counts_once_on_its_first_day():
    t, _ = run()
    by = {c["date"]: c for c in t["bars"]["cols"]}
    assert by["2026-11-18"]["prs"] == "101" and by["2026-11-18"]["value"] == 1
    assert by["2026-11-19"]["prs"] == "102" and by["2026-11-19"]["value"] == 1
    assert by["2026-11-22"]["prs"] == "103,104" and by["2026-11-22"]["value"] == 2


def test_a_day_with_no_loop_rows_reads_no_runs_not_zero():
    t, _ = run()
    by = {c["date"]: c for c in t["bars"]["cols"]}
    gap = by["2026-11-21"]
    assert gap["state"] == "norun" and gap["value"] is None
    assert gap["value_text"] == "no runs" and gap["h"] == 0
    assert "no runs" in gap["tip"]
    assert next(r for r in t["bars"]["table"] if r["date"] == "2026-11-21")["value_text"] == "no runs"


def test_a_day_with_runs_that_shipped_nothing_reads_a_real_zero():
    t, _ = run()
    by = {c["date"]: c for c in t["bars"]["cols"]}
    assert by["2026-11-20"]["state"] == "ok" and by["2026-11-20"]["value"] == 0
    assert by["2026-11-20"]["value_text"] == "0" and by["2026-11-20"]["prs"] == ""


def test_the_bars_name_weekday_and_date_oldest_first_and_stay_inside_the_plot():
    t, _ = run()
    b = t["bars"]
    assert [c["weekday"] for c in b["cols"]] == ["Wed", "Thu", "Fri", "Sat", "Sun", "Mon", "Tue"]
    assert [c["date"] for c in b["cols"]] == [f"2026-11-{n}" for n in range(18, 25)]
    for c in b["cols"]:
        assert 0 <= c["y"] <= b["plot_h"] and c["y"] + c["h"] == pytest.approx(b["plot_h"])
        assert c["x"] >= b["left"] and c["x"] + c["w"] <= b["right_x"]
    assert b["top"] >= b["peak"] == 2 and b["yticks"][0] == b["top"] and b["yticks"][-1] == 0


def test_the_bars_are_empty_not_zero_when_no_day_has_runs():
    t, _ = run(rows=[row("2026-11-01", pr=1)])
    assert t["bars"]["state"] == "empty" and all(c["value"] is None for c in t["bars"]["cols"])


def test_a_small_total_says_too_few_to_read():
    t, _ = run()
    assert t["bars"]["low_n"] and t["bars"]["n_text"].endswith("too few to read")


def test_bars_are_unavailable_when_the_kpi_row_is():
    t2 = ops_trends.build(ops(), ops_kpis._unavailable("x", error=False), LINKS)
    assert t2["bars"]["state"] == "unavailable" and t2["bars"]["cols"] == []
    assert t2["bars"]["total"] is None


# --- Organic search clicks ---------------------------------------------------------------

def test_the_gsc_window_ends_at_its_own_last_row_not_traffic_window():
    t, _ = run(gsc_rows=gsc(end="2026-11-24"), traffic_window=["2026-10-28", "2026-11-26"])
    m = metric(t, "organic")
    assert m["window_text"] == "2026-11-18 → 11-24"
    assert m["delta"]["previous_window"] == "2026-11-11 → 11-17"
    # 14 days of clicks 10..23: current = 17..23 = 140, previous = 10..16 = 91.
    assert m["display"] == "140" and m["delta"]["previous_text"] == "91"
    assert m["delta"]["state"] == "ok" and m["delta"]["direction"] == "up"


def test_the_gsc_window_follows_the_rows_when_they_end_earlier():
    t, _ = run(gsc_rows=gsc(end="2026-11-20"))
    assert metric(t, "organic")["window_text"] == "2026-11-14 → 11-20"


def test_the_organic_row_says_it_is_not_attributed_to_any_agent():
    t, _ = run()
    assert "not attributed to any agent" in metric(t, "organic")["note"]


def test_a_gap_in_the_previous_gsc_window_refuses_the_delta_and_prints_no_was():
    rows = [r for r in gsc() if r["date"] != "2026-11-14"]
    m = metric(run(gsc_rows=rows)[0], "organic")
    assert m["state"] == "ok" and m["display"] == "140", "the complete current week still shows"
    assert m["delta"]["state"] == "unavailable" and m["delta"]["previous_text"] == ""
    assert "no data for 1 of 7 days" in m["delta"]["text"]


def test_a_gap_in_the_current_gsc_window_shows_no_number_and_no_sparkline():
    rows = [r for r in gsc() if r["date"] != "2026-11-21"]
    m = metric(run(gsc_rows=rows)[0], "organic")
    assert m["state"] == "unavailable" and m["display"] == "unavailable" and m["spark"] is None
    assert "no data for 1 of 7 days" in m["n_text"]


def test_a_previous_window_that_starts_before_gsc_data_refuses_the_delta():
    m = metric(run(gsc_rows=gsc(days=10))[0], "organic")
    assert m["state"] == "ok" and m["delta"]["state"] == "unavailable"
    assert m["delta"]["previous_text"] == ""


def test_the_sparkline_covers_the_seven_current_days_at_120_by_32():
    s = metric(run()[0], "organic")["spark"]
    assert s["ok"] and s["n"] == 7 and s["total"] == 140
    assert [b["date"] for b in s["bands"]][0] == "2026-11-18"
    assert all(0 <= float(p.split(",")[0]) <= 120 and 0 <= float(p.split(",")[1]) <= 32
               for p in s["line"].split())


def test_a_week_with_few_clicks_says_too_few_to_read():
    m = metric(run(gsc_rows=gsc(clicks=lambda i: 1))[0], "organic")
    assert m["display"] == "7" and m["low_n"] and m["n_text"].endswith("too few to read")


def test_gsc_rows_that_are_missing_or_empty_are_unavailable_never_zero():
    for rows in ([], None):
        o = ops(gsc_rows=rows or [])
        if rows is None:
            o["traffic"] = {}
        m = metric(run(o)[0], "organic")
        assert m["state"] == "unavailable" and m["display"] == "unavailable"


@pytest.mark.parametrize("bad", [True, False, math.nan, math.inf, -3, "12", None, 1.5, [1]])
def test_a_garbage_click_count_is_skipped_not_summed(bad):
    rows = gsc()
    rows[-1] = {**rows[-1], "clicks": bad}          # the 24th: the newest row
    t, _ = run(gsc_rows=rows)
    m = metric(t, "organic")
    # The newest date is gone, so the window ends a day earlier and is complete.
    assert m["state"] == "ok" and m["window_text"] == "2026-11-17 → 11-23"
    assert "1 row(s) skipped" in m["n_text"]


def test_non_dict_rows_and_a_duplicated_date_are_dropped():
    rows = gsc() + ["x", 5, None, [1]]
    rows.append({"date": "2026-11-20", "clicks": 999})      # a second 11-20, which disagrees
    m = metric(run(gsc_rows=rows)[0], "organic")
    # The duplicated date is dropped whole, so the current week has a hole.
    assert m["state"] == "unavailable" and "first gap 2026-11-20" in m["n_text"]


def test_an_impossible_calendar_date_is_skipped():
    rows = gsc() + [{"date": "2026-13-45", "clicks": 5}, {"date": "20261120", "clicks": 5}]
    m = metric(run(gsc_rows=rows)[0], "organic")
    assert m["state"] == "ok" and m["display"] == "140" and "2 row(s) skipped" in m["n_text"]


def test_this_module_does_not_depend_on_traffic_view_having_screened_the_rows():
    o = ops(gsc_rows=[{"date": "2026-11-24", "clicks": {"x": 1}}, "junk", 7])
    t, _ = run(o)
    assert metric(t, "organic")["state"] == "unavailable" and t["bars"]["state"] == "ok"


# --- Issues closed ---------------------------------------------------------------------------

def test_the_collectors_partial_last_day_is_left_out_of_the_window():
    days = flow_days(newest="2026-11-27", closed=lambda i: 5)
    days[-1]["closed"] = 400                          # today, partial, would swamp the sum
    m = metric(run(days=days)[0], "issues")
    assert m["window_text"] == "2026-11-20 → 11-26"
    assert m["display"] == "35" and m["delta"]["previous_text"] == "35"
    assert m["delta"]["direction"] == "flat"


def test_the_partial_day_is_the_newest_date_even_when_its_own_row_is_garbage():
    days = flow_days()
    days[-1]["closed"] = math.nan
    m = metric(run(days=days)[0], "issues")
    assert m["state"] == "ok" and m["window_text"] == "2026-11-20 → 11-26"
    assert "1 day(s) skipped" in m["n_text"]


def test_a_gap_in_the_fourteen_days_refuses_the_delta():
    days = [d for d in flow_days() if d["date"] != "2026-11-15"]      # in the previous window
    m = metric(run(days=days)[0], "issues")
    assert m["display"] == "35"
    assert m["delta"]["state"] == "unavailable" and m["delta"]["previous_text"] == ""


def test_a_gap_in_the_current_issue_window_shows_no_number():
    days = [d for d in flow_days() if d["date"] != "2026-11-22"]
    m = metric(run(days=days)[0], "issues")
    assert m["state"] == "unavailable" and m["spark"] is None


def test_the_issues_row_counts_close_on_evidence_and_names_the_source_and_age():
    m = metric(run()[0], "issues")
    assert m["label"] == "Issues closed"
    assert "14 by close-on-evidence" in m["n_text"]       # 2 a day over 7 days
    assert "2h ago" in m["source"] and "issues.json" in m["source"]


@pytest.mark.parametrize("flow", [None, {"error": "boom"}, {"days": []}, {"days": "x"},
                                   {"days": [1, "a", None]}])
def test_an_unreadable_issue_trend_is_unavailable(flow):
    o = ops(flow=flow if flow is not None else {})
    if flow is None:
        o["issue_flow"] = None
    m = metric(run(o)[0], "issues")
    assert m["state"] == "unavailable" and m["display"] == "unavailable"


def test_a_bool_or_negative_closed_count_is_not_a_count():
    days = flow_days()
    days[3]["closed"] = True
    days[4]["closed"] = -1
    m = metric(run(days=days)[0], "issues")
    assert "2 day(s) skipped" in m["n_text"]


def test_fix_closer_is_a_key_issue_flow_really_emits():
    spec = importlib.util.spec_from_file_location("issue_flow_trends", ROOT / "scripts" / "issue_flow.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["issue_flow_trends"] = mod
    spec.loader.exec_module(mod)
    assert ops_trends.FIX_CLOSER in mod.CLOSERS


# --- the two rows nothing collects ------------------------------------------------------------

@pytest.mark.parametrize("key,definition", [
    ("content", "/learn articles merged in the window."),
    ("cycle_time", "Time from an issue being opened to its fix merging."),
])
def test_a_not_collected_row_prints_the_owners_definition_and_no_number(key, definition):
    m = metric(run()[0], key)
    assert m["state"] == "unavailable" and m["display"] == "not collected"
    assert m["definition"] == definition
    assert m["spark"] is None and m["n"] == 0 and not any(ch.isdigit() for ch in m["display"])
    assert m["delta"]["state"] == "unavailable" and m["delta"]["previous_text"] == ""
    assert "slice 2e" in m["n_text"] and m["href"] == ""


def test_the_four_metric_rows_come_in_the_owners_order():
    t, _ = run()
    assert [m["label"] for m in t["metrics"]] == [
        "Organic search clicks", "Issues closed", "Content published", "Average cycle time"]


def test_the_not_collected_rows_survive_every_failure():
    for o, k, l in ((None, None, None), ("x", 5, "y"), ({}, {}, [])):
        t = ops_trends.build(o, k, l)
        assert [m["display"] for m in t["metrics"][2:]] == ["not collected", "not collected"]


# --- links ------------------------------------------------------------------------------------

def test_hrefs_come_only_from_the_validated_links_and_default_to_empty():
    t, _ = run()
    assert metric(t, "organic")["href"] == "?tab=analytics&window=7"
    assert metric(t, "issues")["href"] == "?tab=backlog&window=7"
    assert metric(t, "organic")["link_text"] and metric(t, "issues")["link_text"]
    o = ops()
    t2 = ops_trends.build(o, ops_kpis.build(o), [{"key": "analytics", "href": 5}, "x", None])
    assert metric(t2, "organic")["href"] == "" and metric(t2, "organic")["link_text"] == ""


# --- never raises ---------------------------------------------------------------------------------

@pytest.mark.parametrize("o,k,l", [
    (None, None, None), ({}, {}, None), ("x", "y", "z"), ([], [], []), (5, 5, 5),
    ({"traffic": 5, "issue_flow": 7}, {"pr_days": 3}, {}),
    ({"traffic": {"gsc_rows": "abc"}, "issue_flow": {"days": 5}}, {"pr_days": [None, 1]}, []),
    (ops(), {"pr_days": [{"date": "2026-11-18", "runs": True, "prs": []}]}, LINKS),
    (ops(), {"pr_days": [{"date": "nope", "runs": 1, "prs": []}]}, LINKS),
    (ops(), {"pr_days": [{"date": "2026-11-18", "runs": 1, "prs": "12"}]}, LINKS),
])
def test_build_never_raises_and_always_returns_the_same_shape(o, k, l):
    t = ops_trends.build(o, k, l)
    assert set(t) == {"error", "bars", "metrics"} and len(t["metrics"]) == 4
    assert t["bars"]["state"] in ("ok", "empty", "unavailable")
    for m in t["metrics"]:
        assert {"label", "display", "n_text", "window_text", "delta", "spark", "state",
                "source", "href", "link_text"} <= set(m)
        assert m["state"] == "ok" or m["display"] in ("unavailable", "not collected")


def test_a_failing_panel_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(ops_trends, "_organic", lambda *a: 1 / 0)
    t, _ = run()
    assert t["error"] is True
    assert metric(t, "organic")["state"] == "unavailable" and metric(t, "issues")["state"] == "ok"
    assert t["bars"]["state"] == "ok"


def test_a_total_failure_gives_the_unavailable_shape(monkeypatch):
    monkeypatch.setattr(ops_trends, "_build", lambda *a: 1 / 0)
    t = ops_trends.build(ops(), {}, LINKS)
    assert t["error"] is True and t["bars"]["state"] == "unavailable" and len(t["metrics"]) == 4


def test_a_clean_run_reports_no_error():
    assert run()[0]["error"] is False
