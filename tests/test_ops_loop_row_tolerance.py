"""A malformed row in measurements/loop.json must not 500 /admin/ops (#1492).

`_loop_view` indexed `r["outcome"]` on every row and called `.get` on each, so one
truncated row (`{"date": "2026-11-20"}`) was a KeyError and a `null` row an
AttributeError. `snapshot()` is documented "never raises" and calls `_loop_view`
outside any try, so the whole control room died, on every tab, until the file
was fixed. `collect_loop_measurements.py` validates what it writes, but the page
reads whatever is in the bucket or the checkout, and a half-written or
hand-edited file is exactly the outage this page exists to report.

The fixture is dated RELATIVE TO TODAY (IST) so the KPI window always lands on
it. `ops_kpis._clean` already skipped bad rows and had a footer for them; the
view now drops what it cannot read and says how many, so the footer counts both.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

import pytest

from astro_ai import ops_data, ops_tabs

IST = timezone(timedelta(hours=5, minutes=30))
KEYS = [k for k, _ in ops_tabs.TABS]
FOOTER = re.compile(r"(\d+) row\(s\) in loop\.json could not be read")


def _today() -> datetime:
    return datetime.now(IST).replace(hour=12, minute=0, second=0, microsecond=0)


def _row(offset: int, outcome: str = "shipped", *, pr: int | None = None) -> dict:
    when = _today() + timedelta(days=offset)
    return {"run": 7000 + abs(offset), "workflow": "agent-work",
            "date": when.strftime("%Y-%m-%d"),
            "started": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "schedule", "conclusion": "success", "minutes": 5.0, "issue": None,
            "pr": pr, "outcome": outcome, "attribution": "receipt", "kind": "ranked",
            "tokens_input": 1, "tokens_output": 2, "tokens_cache_read": 3,
            "tokens_cache_write": 4, "cost_list_usd": 1.0}


GOOD = _row(-3, "shipped", pr=301)
# The view drops each of these, and says so: no outcome (a truncated row), not a dict at all,
# or an outcome that is not a string (it would be unhashable in the Counter).
UNREADABLE = [
    {"date": _row(-5)["date"]},
    None,
    "garbage",
    7,
    dict(_row(-4), outcome=["shipped"]),
]
# Kept by the view: `outcome` is a string and the date still reads. The first has a started that
# is not a string (TypeError in `_ist`), so its date comes from `date`.
INT_STARTED = dict(_row(-2, "shipped", pr=302), started=12345)
# Kept by the view with `date_ist` None; the KPI module cannot place it in a window and skips it.
INT_DATE = {"run": 1, "outcome": "shipped", "kind": "ranked", "date": 20261120}
MIXED = [GOOD, *UNREADABLE, INT_STARTED, INT_DATE]


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _serve(monkeypatch, rows):
    stamp = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {"loop.json": {"generated_at": stamp, "rows": rows}}
    monkeypatch.setattr(ops_data, "_fetch", lambda name: files.get(name))


def _page(q: str = ""):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _cycles_card(html: str) -> str:
    m = re.search(r'class="tile kpi k-cycles st-(\w+)".*?<span class="num[^"]*">([^<]*)</span>',
                  html, re.S)
    assert m, "no Cycles shipped card"
    return m.group(1) + ":" + m.group(2)


@pytest.mark.parametrize("key", KEYS)
def test_a_malformed_row_does_not_500_any_tab(monkeypatch, key):
    _serve(monkeypatch, MIXED)
    assert _page(f"?tab={key}").status_code == 200


def test_the_view_keeps_only_readable_rows_and_counts_what_it_dropped():
    v = ops_data._loop_view({"generated_at": None, "rows": MIXED}, "2000-01-01")
    assert v["ok"] is True
    assert [r.get("run") for r in v["rows"]] == [GOOD["run"], INT_STARTED["run"], INT_DATE["run"]]
    assert v["skipped_rows"] == len(UNREADABLE)
    assert v["outcomes"] == {"shipped": 3}
    by_run = {r["run"]: r for r in v["rows"]}
    assert by_run[INT_STARTED["run"]]["date_ist"] == INT_STARTED["date"]
    assert by_run[INT_STARTED["run"]]["time_ist"] == "—"
    assert by_run[INT_DATE["run"]]["date_ist"] is None


def test_an_outcome_less_dict_is_dropped_not_counted_as_unknown():
    v = ops_data._loop_view({"rows": [GOOD, {"date": GOOD["date"]}]}, GOOD["date"])
    assert v["outcomes"] == {"shipped": 1} and "unknown" not in v["outcomes"]
    assert [r["run"] for r in v["today_shipped"]] == [GOOD["run"]]


def test_a_non_string_ts_is_not_a_timestamp():
    assert ops_data._ist(123) is None
    assert ops_data._ist(["x"]) is None


def test_the_overview_footer_counts_every_row_left_out_and_good_rows_still_feed_the_cards(monkeypatch):
    _serve(monkeypatch, MIXED)
    h = _page("?tab=overview").text
    m = FOOTER.search(h)
    assert m, "no 'could not be read' footer"
    # five dropped by the view, plus the int-date row the KPI module cannot place
    assert int(m.group(1)) == len(UNREADABLE) + 1
    # GOOD and INT_STARTED are both builds that shipped inside the window
    assert _cycles_card(h) == "ok:2"


def test_a_clean_file_shows_no_footer(monkeypatch):
    _serve(monkeypatch, [GOOD, INT_STARTED])
    h = _page("?tab=overview").text
    assert not FOOTER.search(h)
    assert _cycles_card(h) == "ok:2"


def test_rows_that_are_not_a_list_is_unavailable_and_still_a_page(monkeypatch):
    _serve(monkeypatch, {"not": "a list"})
    assert ops_data._loop_view({"rows": {"not": "a list"}}, "2000-01-01")["ok"] is False
    r = _page("?tab=overview")
    assert r.status_code == 200
    assert _cycles_card(r.text) == "unavailable:unavailable"
    assert not FOOTER.search(r.text)


def test_the_no_snapshot_view_has_every_key_the_ok_view_has():
    ok = ops_data._loop_view({"rows": []}, "2000-01-01")
    bad = ops_data._loop_view(None, "2000-01-01")
    assert set(ok) == set(bad)
    assert bad["skipped_rows"] == 0 and ok["skipped_rows"] == 0


def test_an_empty_row_list_is_an_empty_window_not_a_zero(monkeypatch):
    _serve(monkeypatch, [])
    h = _page("?tab=overview").text
    assert not FOOTER.search(h)
    state, num = _cycles_card(h).split(":")
    assert state == "empty" and num == "no runs"
