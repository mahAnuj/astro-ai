"""The /admin/ops tab shell, backend half (#1133 slice 1, step 1).

`ops_tabs` decides which tab renders, the rail links and the System Healthy
state. These are unit tests of that module plus one request through the real
route: a bad `?tab=` must degrade to Overview, never 422 or 500.
"""
from __future__ import annotations

import os
from urllib.parse import parse_qsl

import pytest

from astro_ai import ops_data, ops_tabs

KEYS = ["overview", "agents", "workflows", "runs", "backlog", "analytics", "monitoring"]


def test_the_tabs_are_the_seven_in_rail_order():
    assert [k for k, _ in ops_tabs.TABS] == KEYS
    assert ops_tabs.DEFAULT == "overview"
    assert dict(ops_tabs.TABS)["runs"] == "Runs & Traces"


@pytest.mark.parametrize("key", KEYS)
def test_pick_tab_keeps_every_real_key(key):
    assert ops_tabs.pick_tab(key) == key


@pytest.mark.parametrize("raw", [
    "", None, "zzz", "governance", "overview&x=1", "a" * 10_000, "<script>", 0, ["runs"],
])
def test_pick_tab_sends_anything_else_to_overview(raw):
    assert ops_tabs.pick_tab(raw) == "overview"


@pytest.mark.parametrize("raw,want", [("Agents", "agents"), (" runs ", "runs"), ("MONITORING", "monitoring")])
def test_pick_tab_forgives_case_and_whitespace(raw, want):
    assert ops_tabs.pick_tab(raw) == want


def test_tab_links_gives_seven_with_exactly_one_current():
    links = ops_tabs.tab_links("runs", 7, "")
    assert [l["key"] for l in links] == KEYS
    assert [l["key"] for l in links if l["current"]] == ["runs"]
    assert all(l["label"] for l in links)


def test_tab_links_carry_the_window_when_no_day_is_picked():
    for l in ops_tabs.tab_links("overview", 30, ""):
        q = parse_qsl(l["href"].lstrip("?"))
        assert q[0] == ("tab", l["key"])
        assert dict(q)["window"] == "30"
        assert "day" not in dict(q)


def test_tab_links_carry_the_day_and_drop_the_window_when_one_is_picked():
    for l in ops_tabs.tab_links("agents", 7, "2026-11-20"):
        q = parse_qsl(l["href"].lstrip("?"))
        assert q[0] == ("tab", l["key"])
        assert dict(q)["day"] == "2026-11-20"
        assert "window" not in dict(q)


def test_health_ok_when_nothing_is_open():
    h = ops_tabs.health([], 0, [])
    assert h["state"] == "ok" and h["count"] == 0
    assert h["label"] and h["detail"]


def test_health_watch_on_an_alert_that_is_not_red():
    h = ops_tabs.health([{"level": "amber"}], 0, [])
    assert h["state"] == "watch" and h["count"] == 1
    assert h["detail"] == "1 finding"


def test_health_watch_on_a_missing_panel_source():
    h = ops_tabs.health([], 0, ["loop.json", "cost.json"])
    assert h["state"] == "watch" and h["count"] == 2
    assert h["detail"] == "2 findings"


def test_health_bad_when_any_alert_is_red():
    h = ops_tabs.health([{"level": "red"}, {"level": "amber"}], 1, ["loop.json"])
    assert h["state"] == "bad" and h["count"] == 1
    assert h["detail"] == "1 red"


def test_health_never_raises_on_none():
    assert ops_tabs.health(None, None, None)["state"] == "ok"


# --- through the real route -----------------------------------------------------

@pytest.fixture
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _page(q: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


@pytest.mark.parametrize("q", [
    "?tab=zzz", "?tab=", "?tab=Governance", "?tab=runs&tab=agents", "?tab=" + "a" * 10_000,
    "?tab=%3Cscript%3E", "?tab=agents&window=abc",
])
def test_a_bad_tab_renders_the_page_not_an_error(_offline, q):
    r = _page(q)
    assert r.status_code == 200


@pytest.mark.parametrize("key", KEYS)
def test_every_real_tab_renders(_offline, key):
    assert _page(f"?tab={key}").status_code == 200
