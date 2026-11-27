"""One missing traffic series must not 500 /admin/ops?tab=analytics (#1553).

`_series` returns `{"ok": False}` for an absent file or `rows: []`; the template evaluated the
macro's arguments (`T.impressions.total`, `'{:,}'.format(...)`) before its body, so the page died
while the OTHER series was fine. The template now guards each chart call and renders a labelled
"No data" note instead. Real `_fetch` against files in a tmp dir; nothing is stubbed.
"""
from __future__ import annotations

import json
import os

import pytest

from astro_ai import ops_data

WINDOW = ["2026-11-01", "2026-11-03"]
GA4 = {"window": WINDOW, "rows": [
    {"date": "2026-11-01", "active_users": 5, "sessions": 6},
    {"date": "2026-11-02", "active_users": 8, "sessions": 9},
    {"date": "2026-11-03", "active_users": 7, "sessions": 8}]}
GSC = {"window": WINDOW, "rows": [
    {"date": "2026-11-01", "impressions": 600, "clicks": 3},
    {"date": "2026-11-02", "impressions": 700, "clicks": 4}]}


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(tmp_path))
    for c in (ops_data._cache, ops_data._app_cache):
        c.clear()
    yield
    for c in (ops_data._cache, ops_data._app_cache):
        c.clear()


def _page(tmp_path, ga4=None, gsc=None):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    for name, doc in (("ga4-daily.json", ga4), ("gsc-daily.json", gsc)):
        if doc is not None:
            (tmp_path / name).write_text(json.dumps(doc))
    ops_data._cache.clear()
    ops_data._app_cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app, raise_server_exceptions=False).get(
        "/admin/ops?tab=analytics", auth=("admin", pw))


def _traffic(html: str) -> str:
    return html[html.index("<h2>Traffic"):].split("</section>")[0]


@pytest.mark.parametrize("gsc", [None, {"rows": []}], ids=["gsc-absent", "gsc-empty"])
def test_missing_search_series_still_renders_people(tmp_path, gsc):
    r = _page(tmp_path, ga4=GA4, gsc=gsc)
    assert r.status_code == 200
    assert "Traceback" not in r.text
    t = _traffic(r.text)
    assert t.count("<polyline") == 1
    assert "People · daily active users" in t
    assert "No data:" in t and "gsc-daily.json" in t


@pytest.mark.parametrize("ga4", [None, {"rows": []}], ids=["ga4-absent", "ga4-empty"])
def test_missing_people_series_still_renders_search(tmp_path, ga4):
    r = _page(tmp_path, ga4=ga4, gsc=GSC)
    assert r.status_code == 200
    assert "Traceback" not in r.text
    t = _traffic(r.text)
    assert t.count("<polyline") == 1
    assert "1,300" in t
    assert "No data:" in t and "ga4-daily.json" in t


def test_both_series_present_render_two_charts_and_no_note(tmp_path):
    r = _page(tmp_path, ga4=GA4, gsc=GSC)
    assert r.status_code == 200
    t = _traffic(r.text)
    assert t.count("<polyline") == 2
    assert "No data:" not in t


def test_neither_series_present_omits_the_traffic_panel(tmp_path):
    r = _page(tmp_path)
    assert r.status_code == 200
    assert "<h2>Traffic" not in r.text
