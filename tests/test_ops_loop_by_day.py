"""/admin/ops shows the loop day by day, not as a cycle ribbon (2026-11-09).

The ribbon placed cycles on a 24 h axis against two cron lines, built to show a
late cron (#345). By 2026-11-09 agent-work had six crons plus chaining, so the
lines were wrong and the owner could not read a benefit off it. These tests
drive `ops_data._by_day` directly and through the real route.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from astro_ai import llm_stats, ops_data

IST = ops_data.IST


def row(run, started, minutes, outcome, kind="ranked", helped=None):
    st = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return {"run": run, "started": started, "minutes": minutes, "outcome": outcome,
            "kind": kind, "owner_helped": helped,
            "date_ist": st.astimezone(IST).strftime("%Y-%m-%d")}


def test_counts_split_build_cycles_from_qa_rounds_and_by_outcome():
    rows = [row(1, "2026-11-08T01:00:00Z", 30, "shipped"),
            row(2, "2026-11-08T03:00:00Z", 20, "pr open", "issue"),
            row(3, "2026-11-08T05:00:00Z", 10, "nothing"),
            row(4, "2026-11-08T06:00:00Z", 5, "failed"),
            row(5, "2026-11-08T07:00:00Z", 12, "judged", "qa-round"),
            row(6, "2026-11-08T08:00:00Z", 3, "unknown", "qa-round")]
    (d,) = ops_data._by_day(rows)
    assert d["date"] == "2026-11-08"
    assert (d["build_cycles"], d["qa_rounds"]) == (4, 2)
    assert (d["shipped"], d["pr_open"], d["nothing"], d["failed"]) == (1, 1, 1, 2)


def test_shipped_splits_by_who_finished_it():
    rows = [row(1, "2026-11-08T01:00:00Z", 30, "shipped", helped=False),
            row(2, "2026-11-08T02:00:00Z", 30, "shipped", helped=True),
            row(3, "2026-11-08T03:00:00Z", 30, "shipped", helped=True),
            row(4, "2026-11-08T04:00:00Z", 30, "shipped")]          # not read yet
    (d,) = ops_data._by_day(rows)
    assert (d["shipped"], d["shipped_loop"], d["shipped_helped"], d["shipped_unread"]) == (4, 1, 2, 1)


def test_busy_time_is_the_union_of_build_runs_and_ignores_qa_rounds():
    # 06:30-07:30 IST and 07:00-08:00 IST overlap: 1.5 h busy, not 2 h. The QA
    # round runs in its own lane and must not count against build idle.
    rows = [row(1, "2026-11-08T01:00:00Z", 60, "shipped"),
            row(2, "2026-11-08T01:30:00Z", 60, "shipped"),
            row(3, "2026-11-08T04:00:00Z", 600, "judged", "qa-round")]
    (d,) = ops_data._by_day(rows)
    assert d["busy_h"] == 1.5 and d["idle_h"] == 22.5


def test_a_run_crossing_midnight_ist_is_clipped_to_its_start_day():
    # Starts 23:30 IST, runs 2 h: only 0.5 h belongs to that day.
    (d,) = ops_data._by_day([row(1, "2026-11-08T18:00:00Z", 120, "shipped")])
    assert d["busy_h"] == 0.5


def test_todays_idle_runs_only_up_to_now():
    now = datetime(2026, 11, 9, 6, 0, tzinfo=IST)            # 6 h into the day
    (d,) = ops_data._by_day([row(1, "2026-11-08T19:30:00Z", 60, "shipped")], now)  # 01:00 IST
    assert d["busy_h"] == 1.0 and d["idle_h"] == 5.0


def test_newest_day_first_and_capped():
    rows = [row(i, f"2026-10-{i:02d}T06:00:00Z", 10, "shipped") for i in range(1, 31)]
    out = ops_data._by_day(rows)
    assert len(out) == ops_data.BY_DAY_LIMIT
    assert out[0]["date"] == "2026-10-30" and out[-1]["date"] == "2026-10-17"


def test_the_empty_branch_carries_the_key_too():
    assert ops_data._loop_view(None, "2026-11-09", None)["by_day"] == []


@pytest.fixture
def page(client, monkeypatch, tmp_path):
    def render(files: dict):
        d = tmp_path / "m"
        d.mkdir(exist_ok=True)
        for name, doc in files.items():
            (d / name).write_text(json.dumps(doc))
        monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
        monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
        monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
        monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
        monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
        monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(d))
        ops_data._cache.clear()
        ops_data._app_cache.clear()
        try:
            r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
        finally:
            ops_data._cache.clear()
            ops_data._app_cache.clear()
        assert r.status_code == 200, r.text[:500]
        return r.text
    return render


def test_the_page_shows_the_day_table_and_no_ribbon(page):
    loop = {"generated_at": "2026-11-08T09:00:00Z", "rows": [
        {"run": 1, "workflow": "agent-work", "date": "2026-11-08", "started": "2026-11-08T03:51:33Z",
         "trigger": "schedule", "conclusion": "success", "minutes": 42.7, "issue": 570, "pr": 688,
         "pr_merged": True, "outcome": "shipped", "attribution": "receipt", "kind": "issue"}]}
    html = page({"loop.json": loop})
    assert "The loop, day by day" in html
    assert 'data-day="2026-11-08"' in html
    assert "Cycle ribbon" not in html and 'class="blk' not in html and "cron-line" not in html


def test_no_loop_file_says_so(page):
    html = page({})
    assert "The loop, day by day" in html and "loop.json</code> is missing" in html


# --- the chart (owner, 2026-11-09: "show it in some kind of graph as that will occupy less space")

def _days():
    return ops_data._by_day([row(1, "2026-11-07T01:00:00Z", 60, "shipped", helped=False),
                             row(2, "2026-11-08T01:00:00Z", 120, "shipped", helped=True),
                             row(3, "2026-11-08T03:00:00Z", 30, "failed"),
                             row(4, "2026-11-08T04:00:00Z", 30, "shipped")])


def test_the_chart_runs_oldest_left_and_stacks_results_below_waste():
    g = ops_data._by_day_chart(_days())
    assert [c["date"] for c in g["cols"]] == ["2026-11-07", "2026-11-08"]
    segs = g["cols"][1]["segs"]
    assert [s["cls"] for s in segs] == ["helped", "unread", "failed"]
    assert segs[0]["y"] > segs[1]["y"] > segs[2]["y"], "results sit at the bottom"


def test_segment_heights_follow_the_counts_on_one_axis():
    g = ops_data._by_day_chart(_days())
    col = g["cols"][1]
    total = sum(s["h"] + 2 for s in col["segs"])           # +2: the surface gap
    assert total == pytest.approx(3 / g["ymax"] * g["plot_h"], abs=0.1)


def test_the_busy_strip_is_hours_out_of_24():
    g = ops_data._by_day_chart(_days())
    assert g["cols"][1]["busy_h"] == pytest.approx(3.0 / 24 * g["strip_h"], abs=0.01)  # 2 h + 0.5 + 0.5


def test_the_tooltip_says_not_read_yet_rather_than_zero_help():
    tip = ops_data._by_day_chart(_days())["cols"][1]["tip"]
    assert "1 with your help, 1 not read yet" in tip


def test_no_days_no_chart():
    assert ops_data._by_day_chart([]) is None
    assert ops_data._loop_view(None, "2026-11-09", None)["by_day_chart"] is None


def test_the_page_draws_the_chart_and_keeps_the_table_one_click_away(page):
    loop = {"generated_at": "2026-11-08T09:00:00Z", "rows": [
        {"run": 1, "workflow": "agent-work", "date": "2026-11-08", "started": "2026-11-08T03:51:33Z",
         "trigger": "schedule", "conclusion": "success", "minutes": 42.7, "issue": 570, "pr": 688,
         "pr_merged": True, "outcome": "shipped", "attribution": "receipt", "kind": "issue",
         "owner_helped": True}]}
    html = page({"loop.json": loop})
    assert '<svg class="dchart"' in html and 'class="seg s-helped"' in html
    assert "<summary>Show as table</summary>" in html
    assert html.index('<svg class="dchart"') < html.index("<summary>Show as table</summary>")
