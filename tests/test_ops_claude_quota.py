"""/admin/ops shows how much Claude quota is left, and where the loop's time went
(owner, 2026-11-03: "I hope I can see the claude_usage on ops dashboard ... on
top like this much quota pending before reset", and "capture the wastage ...
idle time, time spent by workflow but not result").

Rendered through the real route with the measurements on disk, so the strip and
the panel are checked as a visitor sees them, not as a dict."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from astro_ai import llm_stats, ops_data

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
RESET_7D = int(datetime(2026, 11, 6, 6, 0, tzinfo=timezone.utc).timestamp())
RESET_5H = int(datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc).timestamp())


def usage(seven=0.69, five=0.04, rejected=()):
    return {"generated_at": "2026-11-03T11:00:00Z", "window_hours": 48,
            "latest": {"workflow": "agent-work", "run": 1, "at": "2026-11-03T10:56:53Z",
                       "five_hour": five, "seven_day": seven, "status": "allowed",
                       "resets": {"five_hour": RESET_5H, "seven_day": RESET_7D}},
            "peak_seven_day": seven, "rejected_runs": list(rejected), "readings": []}


WASTE = {"days": 7, "cycles": 20,
         "minutes_by_outcome": {"shipped": 300.0, "pr open": 0.0, "judged": 60.0,
                                "nothing": 240.0, "failed": 40.0, "unknown": 0.0},
         "minutes_total": 640.0, "minutes_without_result": 280.0, "share_without_result": 0.438,
         "shipped_prs": 6, "build_idle_hours": 120.5, "build_idle_share": 0.717}


def test_the_view_leads_with_the_WEEKLY_window_and_the_time_to_reset():
    v = ops_data._claude_view(usage(), NOW)
    assert (v["seven_used_pct"], v["seven_left_pct"]) == (69, 31)
    assert v["seven_resets_in"] == "2d 18h"
    assert v["five_used_pct"] == 4 and v["alert"] is False


def test_the_view_alerts_at_the_threshold_and_not_below():
    assert ops_data._claude_view(usage(seven=0.85), NOW)["alert"] is True
    assert ops_data._claude_view(usage(seven=0.84), NOW)["alert"] is False


def test_an_unreadable_usage_file_is_no_view_never_zero_percent():
    assert ops_data._claude_view(None, NOW) is None
    assert ops_data._claude_view({"latest": {}}, NOW) is None


def test_the_waste_view_turns_shares_into_percents():
    v = ops_data._waste_view({"waste": WASTE})
    assert (v["no_result_pct"], v["idle_pct"]) == (44, 72)
    assert ops_data._waste_view({"rows": []}) is None


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


def test_the_quota_strip_is_ABOVE_the_alerts_and_says_what_is_left(page):
    html = page({"claude_usage.json": usage()})
    assert "Claude weekly quota" in html and "% left" in html and "resets in" in html
    assert html.index("Claude weekly quota") < html.index("Objective"), "it leads the page"


def test_a_high_weekly_quota_raises_an_alert(page):
    html = page({"claude_usage.json": usage(seven=0.9)})
    assert "Claude weekly quota 90% used" in html


def test_no_usage_file_says_so_rather_than_showing_a_number(page):
    html = page({})
    assert "Claude quota unknown" in html


def test_the_waste_panel_renders_from_loop_json(page):
    loop = {"generated_at": "2026-11-03T09:00:00Z", "waste": WASTE, "rows": [
        {"run": 1, "workflow": "agent-work", "date": "2026-11-03", "started": "2026-11-03T03:51:33Z",
         "trigger": "schedule", "conclusion": "success", "minutes": 42.7, "issue": 570, "pr": 688,
         "pr_merged": True, "outcome": "shipped", "attribution": "receipt", "kind": "issue"},
        {"run": 2, "workflow": "agent-work", "date": "2026-11-03", "started": "2026-11-03T05:00:00Z",
         "trigger": "workflow_dispatch", "conclusion": "success", "minutes": 12.0, "issue": None,
         "pr": 649, "pr_merged": None, "outcome": "judged", "attribution": "receipt",
         "kind": "qa-round"}]}
    html = page({"loop.json": loop})
    assert "Where the loop&#39;s time went" in html or "Where the loop's time went" in html
    assert "minutes without a result" in html and "build lane idle" in html
    assert "120.5 h" in html
    assert "QA round" in html, "the newest cycle is a judged round and the sentence says so"
