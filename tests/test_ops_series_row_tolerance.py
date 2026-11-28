"""One malformed row in a daily series, a movers table or `trend.days` degrades its panel,
never all 7 /admin/ops tabs (#1554, the #1492 / #1541 / #1542 class).

`_traffic_view` and `_issue_flow_view` run from `snapshot()` ("never raises") outside any
try, so a `null` gsc row (AttributeError) or `closed: "x"` (TypeError) was a 500 on every
tab. These tests use the REAL `_fetch` against files in a tmp dir, as test_ops_nonobject_json
does; replacing `_fetch` would test nothing.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from astro_ai import ops_data, ops_tabs

KEYS = [k for k, _ in ops_tabs.TABS]
NOW = datetime(2026, 11, 27, 6, 0, tzinfo=timezone.utc)


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


def _page(key: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app, raise_server_exceptions=False).get(
        f"/admin/ops?tab={key}", auth=("admin", pw))


def _write(tmp_path, name, doc):
    (tmp_path / name).write_text(json.dumps(doc))
    ops_data._cache.clear()
    ops_data._app_cache.clear()


def _gsc(rows):
    return {"window": "2026-11-01..2026-11-14", "rows": rows}


def _good_gsc():
    return [{"date": "2026-11-01", "impressions": 10, "clicks": 1},
            {"date": "2026-11-02", "impressions": 20, "clicks": 2}]


def _day(date, opened=1, closed=1, open_end=10, net=0, **extra):
    return {"date": date, "opened": opened, "closed": closed, "open_end": open_end,
            "net": net, **extra}


def _trend(days, **extra):
    return {"generated_at": "2026-11-27T05:00:00Z", "trend": {"days": days, **extra}}


def _days(n=10):
    return [_day(f"2026-11-{i + 1:02d}", opened=i, closed=1, open_end=10 + i, net=i - 1)
            for i in range(n)]


def _traffic():
    return ops_data._traffic_view()


def _flow(doc=None):
    return ops_data._issue_flow_view(doc, NOW)


# 1, 4: a null row does not 500 any tab, for either daily file
@pytest.mark.parametrize("key", KEYS)
def test_a_null_gsc_row_does_not_500_any_tab(tmp_path, key):
    _write(tmp_path, "gsc-daily.json", _gsc([None, 3]))
    assert _page(key).status_code == 200


@pytest.mark.parametrize("key", KEYS)
def test_a_null_ga4_row_does_not_500_any_tab(tmp_path, key):
    _write(tmp_path, "ga4-daily.json", {"rows": [None, "x"]})
    assert _page(key).status_code == 200


def test_the_issue_repro_series_goes_blank_not_the_page(tmp_path):
    _write(tmp_path, "gsc-daily.json", _gsc([None, 3]))
    assert _traffic()["impressions"] == {"ok": False}


# 2: good rows beside a null one are kept
def test_a_null_row_beside_good_rows_keeps_the_good_ones(tmp_path):
    _write(tmp_path, "gsc-daily.json", _gsc([_good_gsc()[0], None, _good_gsc()[1]]))
    t = _traffic()
    assert t["impressions"]["ok"] is True
    assert t["impressions"]["n"] == 2
    assert t["clicks_total"] == 3
    assert len(t["gsc_rows"]) == 2


# 3: a non-numeric count is 0, not a crash
def test_a_non_numeric_count_is_zero(tmp_path):
    rows = [{"date": "2026-11-01", "impressions": "x", "clicks": "y"},
            {"date": "2026-11-02", "impressions": True, "clicks": float("nan")},
            {"date": "2026-11-03", "impressions": 7, "clicks": 4}]
    _write(tmp_path, "gsc-daily.json", _gsc(rows))
    t = _traffic()
    assert t["impressions"]["n"] == 3
    assert t["impressions"]["total"] == 7
    assert t["clicks_total"] == 4
    ga = [{"date": "2026-11-01", "active_users": "x", "sessions": None},
          {"date": "2026-11-02", "active_users": 5, "sessions": 9}]
    _write(tmp_path, "ga4-daily.json", {"rows": ga})
    t = _traffic()
    assert t["users"]["total"] == 5
    assert t["sessions_total"] == 9


# 5: movers drop what cannot be shown
@pytest.mark.parametrize("name,dim", [("gsc-trend-page.json", "pages"),
                                      ("gsc-trend-query.json", "queries")])
def test_movers_drop_unreadable_rows_and_keep_the_good_one(tmp_path, name, dim):
    key = "page" if dim == "pages" else "query"
    good = {key: "/x", "delta": 5}
    _write(tmp_path, name, {"rows": [None, {}, {key: "/y", "delta": "x"},
                                     {key: "/z", "delta": True}, {"delta": 3}, good]})
    m = _traffic()[dim]
    assert m["ok"] is True
    assert m["up"] == [good] and m["down"] == []


@pytest.mark.parametrize("key", KEYS)
def test_unreadable_movers_do_not_500_any_tab(tmp_path, key):
    _write(tmp_path, "gsc-trend-page.json", {"rows": [None, {"page": "/y", "delta": "x"}]})
    _write(tmp_path, "gsc-trend-query.json", {"rows": [3, {}]})
    assert _page(key).status_code == 200


# 6, 7: a bad trend day does not 500 any tab
@pytest.mark.parametrize("key", KEYS)
def test_a_null_trend_day_does_not_500_any_tab(tmp_path, key):
    _write(tmp_path, "issues.json", _trend(_days()[:4] + [None] + _days()[5:]))
    assert _page(key).status_code == 200


@pytest.mark.parametrize("key", KEYS)
def test_a_non_numeric_closed_does_not_500_any_tab(tmp_path, key):
    days = _days()
    days[3]["closed"] = "x"
    _write(tmp_path, "issues.json", _trend(days))
    assert _page(key).status_code == 200


# 8: readable days are kept, the rest are counted
def test_issue_flow_keeps_readable_days_and_counts_the_rest():
    days = _days(10)
    days[2] = None
    days[4]["closed"] = "x"
    del days[6]["open_end"]
    days[7]["opened"] = True
    v = _flow({"trend": {"days": days}})
    assert v["skipped_days"] == 4
    assert [d["date"] for d in v["days"]] == [days[i]["date"] for i in (0, 1, 3, 5, 8, 9)]
    assert len(v["chart"]["cols"]) == len(v["days"]) == 6


# 9: nothing readable is an error panel, not a 500
def test_all_days_unreadable_is_an_error_panel(tmp_path):
    _write(tmp_path, "issues.json", _trend([None, {"date": "2026-11-01", "closed": "x"}, 5]))
    assert _flow(json.load(open(tmp_path / "issues.json")))["error"] == \
        "the trend block has no readable days"
    for key in KEYS:
        assert _page(key).status_code == 200


# 10: breakdown maps are cosmetic: bad ones are emptied, the day stays
def test_a_bad_breakdown_is_ignored_not_fatal():
    days = _days(8)
    days[-1]["opened_by"] = {"loop": "x", "ops": 2}
    days[-2]["closed_by"] = "abc"
    days[-3]["opened_by"] = [1]
    v = _flow({"trend": {"days": days}})
    assert v["skipped_days"] == 0 and len(v["days"]) == 8
    assert dict(v["sources"])["loop bots"] == 0
    assert dict(v["sources"])["[OPS] findings"] == 2
    assert all(n == 0 for _, n in v["closers"])
    assert _flow({"trend": {"days": _days(8), "merged_open": "abc"}})["merged_open"] == []


# 11: a clean file is unchanged
def test_a_clean_file_is_unchanged(tmp_path):
    days = _days(10)
    v = _flow({"trend": {"days": days}})
    assert v["skipped_days"] == 0
    assert v["days"] == days
    assert v["opened"] == sum(d["opened"] for d in days[-7:])
    assert v["closed"] == 7
    assert v["delta"] == days[-1]["open_end"] - days[-8]["open_end"]
    _write(tmp_path, "gsc-daily.json", _gsc(_good_gsc()))
    t = _traffic()
    assert t["clicks_total"] == 3 and t["impressions"]["total"] == 30
    assert t["impressions"]["n"] == 2
    for key in KEYS:
        assert _page(key).status_code == 200


# --- #1559: a row with no string date is dropped from its series, not a 500 ----------------

_DATELESS = [{"impressions": 1, "clicks": 1},
             {"date": 5, "impressions": 1, "clicks": 1},
             {"date": None, "impressions": 1, "clicks": 1}]
_DAILY = [("gsc-daily.json", "impressions"), ("ga4-daily.json", "active_users")]


def _daily_doc(name, rows):
    return _gsc(rows) if name == "gsc-daily.json" else {"rows": rows}


@pytest.mark.parametrize("bad", _DATELESS)
@pytest.mark.parametrize("name,metric", _DAILY)
def test_a_dateless_daily_row_does_not_500_the_analytics_tab(tmp_path, name, metric, bad):
    _write(tmp_path, name, _daily_doc(name, [{**bad, metric: bad.get(metric, 1)}]))
    assert _page("analytics").status_code == 200


def test_a_dateless_daily_row_does_not_500_any_tab(tmp_path):
    _write(tmp_path, "gsc-daily.json", _gsc(list(_DATELESS)))
    _write(tmp_path, "ga4-daily.json", {"rows": [{"active_users": 1}, {"date": 5}]})
    assert [(k, _page(k).status_code) for k in KEYS] == [(k, 200) for k in KEYS]


def test_a_good_gsc_row_beside_a_dateless_one_keeps_the_good_one(tmp_path):
    good = {"date": "2026-11-01", "impressions": 1, "clicks": 1}
    _write(tmp_path, "gsc-daily.json",
           _gsc([{"impressions": 100, "clicks": 50}, good, {"date": 5, "impressions": 7}]))
    t = _traffic()
    assert t["impressions"]["ok"] is True
    assert t["impressions"]["n"] == 1 and t["impressions"]["total"] == 1
    assert t["clicks_total"] == 1


def test_a_good_ga4_row_beside_a_dateless_one_keeps_the_good_one(tmp_path):
    good = {"date": "2026-11-01", "active_users": 4, "sessions": 6}
    _write(tmp_path, "ga4-daily.json",
           {"rows": [{"active_users": 100, "sessions": 50}, good, {"date": None, "sessions": 9}]})
    t = _traffic()
    assert t["users"]["n"] == 1 and t["users"]["total"] == 4
    assert t["sessions_total"] == 6


def test_the_raw_row_lists_still_count_a_dateless_row(tmp_path):
    # ops_trends reports "N row(s) skipped" from this list, so it must not be screened here.
    _write(tmp_path, "gsc-daily.json", _gsc(_good_gsc() + [{"impressions": 1}]))
    assert len(_traffic()["gsc_rows"]) == 3


def test_ops_trends_still_reports_a_dateless_row_as_skipped(tmp_path):
    from astro_ai import ops_kpis, ops_trends
    from datetime import date, timedelta
    rows = [{"date": (date(2026, 11, 24) - timedelta(days=i)).isoformat(),
             "impressions": 5, "clicks": 10} for i in range(14)]
    _write(tmp_path, "gsc-daily.json", _gsc(rows + [{"impressions": 1, "clicks": 1}]))
    o = {"today_ist": "2026-11-25", "loop": {"ok": False}, "agents": {"ok": True, "agents": {}},
         "traffic": {"gsc_rows": _traffic()["gsc_rows"], "window": ["2026-10-28", "2026-11-26"]},
         "issue_flow": {"days": [], "age": {"text": "2h ago"}}, "ages": {}}
    t = ops_trends.build(o, ops_kpis.build(o), ops_tabs.tab_links("overview", 7, ""))
    organic = next(m for m in t["metrics"] if m["key"] == "organic")
    assert "1 row(s) skipped" in organic["n_text"]


def test_the_page_plots_a_dated_row_and_a_dateless_rows_value_appears_nowhere(tmp_path):
    rows = [{"date": "2026-11-01", "impressions": 10, "clicks": 1},
            {"impressions": 987654, "clicks": 1},
            {"date": "2026-11-02", "impressions": 20, "clicks": 2}]
    _write(tmp_path, "gsc-daily.json", _gsc(rows))
    r = _page("analytics")
    assert r.status_code == 200
    assert "11-01" in r.text and "11-02" in r.text
    assert "987654" not in r.text and "987,654" not in r.text


def test_when_only_dateless_rows_exist_the_series_says_no_data(tmp_path):
    # ga4 is readable, so the Traffic panel renders and the gsc chart must fall to its note.
    _write(tmp_path, "ga4-daily.json", {"rows": [{"date": "2026-11-01", "active_users": 3}]})
    _write(tmp_path, "gsc-daily.json", _gsc([{"impressions": 987654}]))
    assert _traffic()["impressions"] == {"ok": False}
    r = _page("analytics")
    assert r.status_code == 200 and "987654" not in r.text
    assert "measurements/gsc-daily.json</code> is missing or has no rows" in r.text
