"""#782 -- `scripts/fetch_ga4.py --events`: the analyst's only way to read `cta_click`
(#570). Before it, every metric that claimed a click was "undetermined" rather than
zero. Hermetic: `post`, `token` and `window` are patched, nothing touches the network.

Each test is a way this export could ship wrong: a split read as data when GA4
answered `(not set)`, a 403 swallowed as "parameters unregistered", or a zero that
reads like a broken export (or the reverse)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("fetch_ga4", ROOT / "scripts" / "fetch_ga4.py")
ga = importlib.util.module_from_spec(_spec)
sys.modules["fetch_ga4"] = ga
_spec.loader.exec_module(ga)


def _row(dims, count):
    return {"dimensionValues": [{"value": d} for d in dims],
            "metricValues": [{"value": str(count)}]}


class Fake:
    """Records every request body; answers request A (one dimension) and B (three)."""

    def __init__(self, a=None, b=None, b_exc=None, a_row_count=None):
        self.a, self.b, self.b_exc, self.a_row_count = a, b, b_exc, a_row_count
        self.bodies = []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        if len(body.get("dimensions", [])) == 3:
            if self.b_exc:
                raise self.b_exc
            return {"rows": self.b or []}
        rows = self.a or []
        return {"rows": rows, "rowCount": self.a_row_count
                if self.a_row_count is not None else len(rows)}


def run(monkeypatch, capsys, fake, *flags):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: ("2026-10-09", "2026-11-05"))
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", *flags])
    rc = ga.main()
    return rc, json.loads(capsys.readouterr().out)


A_ROWS = [_row(["page_view"], 900), _row(["cta_click"], 7)]
B_ROWS = [_row(["cta_click", "/learn/a", "/kundli"], 5),
          _row(["cta_click", "/learn/b", "/panchang"], 2)]


def test_the_requests_ask_for_event_name_and_the_exact_cta_click_split(monkeypatch, capsys):
    fake = Fake(A_ROWS, B_ROWS)
    run(monkeypatch, capsys, fake, "--events")
    a, b = fake.bodies
    assert a["dimensions"] == [{"name": "eventName"}]
    assert a["metrics"] == [{"name": "eventCount"}]
    assert [d["name"] for d in b["dimensions"]] == [
        "eventName", "customEvent:from_path", "customEvent:to_path"]
    assert b["dimensionFilter"]["filter"]["fieldName"] == "eventName"
    assert b["dimensionFilter"]["filter"]["stringFilter"] == {
        "matchType": "EXACT", "value": "cta_click"}


def test_happy_path_emits_integer_split_rows(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, B_ROWS), "--events")
    assert rc == 0
    assert out["dimensions"] == ["eventName"]
    assert out["rows"] == [{"event": "page_view", "count": 900},
                           {"event": "cta_click", "count": 7}]
    assert out["events_total"] == 907
    assert out["cta_click"]["count"] == 7
    assert out["cta_click"]["split_available"] is True
    assert out["cta_click"]["rows"] == [
        {"from_path": "/learn/a", "to_path": "/kundli", "count": 5},
        {"from_path": "/learn/b", "to_path": "/panchang", "count": 2}]
    assert all(isinstance(r["count"], int) for r in out["cta_click"]["rows"])
    assert "2026-11-03" in out["coverage_note"]       # partial history is stated


def test_a_400_on_the_split_keeps_the_total_and_names_the_unregistered_dimensions(
        monkeypatch, capsys):
    fake = Fake(A_ROWS, b_exc=ga.ApiError("HTTP 400 from analyticsdata.googleapis.com", 400))
    rc, out = run(monkeypatch, capsys, fake, "--events")
    assert rc == 0
    assert out["cta_click"]["count"] == 7
    assert out["cta_click"]["split_available"] is False
    assert out["cta_click"]["rows"] == []
    note = out["coverage_note"]
    assert "not registered as custom dimensions" in note
    assert "from_path" in note and "to_path" in note
    assert "TOTAL" in note


@pytest.mark.parametrize("status", [403, 500])
def test_any_other_error_on_the_split_still_fails_the_run(monkeypatch, capsys, status):
    fake = Fake(A_ROWS, b_exc=ga.ApiError(f"HTTP {status} from x", status))
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--events")
    assert e.value.status == status


def test_all_not_set_rows_are_not_emitted_as_data(monkeypatch, capsys):
    b = [_row(["cta_click", "(not set)", "(not set)"], 7)]
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, b), "--events")
    assert out["cta_click"]["split_available"] is False
    assert out["cta_click"]["rows"] == []
    assert out["cta_click"]["count"] == 7
    assert "(not set)" in out["coverage_note"] and "TOTAL" in out["coverage_note"]


def test_no_cta_click_row_is_a_zero_measurement_not_an_unreadable_export(
        monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake([_row(["page_view"], 900)], []), "--events")
    assert out["cta_click"]["count"] == 0
    assert "0 events recorded in the window" in out["coverage_note"]
    assert "unreadable" in out["coverage_note"]       # says 0 is NOT the unreadable case
    assert "not available" not in out["coverage_note"]


def test_a_property_with_no_events_at_all_says_so(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake([], []), "--events")
    assert out["cta_click"]["count"] == 0
    assert "no events at all" in out["coverage_note"]


def test_truncation_is_reported(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, B_ROWS, a_row_count=1500), "--events")
    assert out["truncated"] is True
    assert out["row_count"] == 1500
    assert "TRUNCATED: 2 of 1500" in out["coverage_note"]
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, B_ROWS), "--events")
    assert out["truncated"] is False


def test_the_default_and_daily_reports_keep_their_request_bodies(monkeypatch, capsys):
    calls = []

    def fake(url, body, bearer):
        calls.append(body)
        return {"rows": []}

    run(monkeypatch, capsys, fake)
    assert [d["name"] for d in calls[0]["dimensions"]] == [
        "landingPagePlusQueryString", "sessionDefaultChannelGroup"]
    assert [m["name"] for m in calls[0]["metrics"]] == [
        "sessions", "bounceRate", "screenPageViewsPerSession", "activeUsers"]
    assert "dimensionFilter" not in calls[0]
    calls.clear()
    run(monkeypatch, capsys, fake, "--daily")
    assert [d["name"] for d in calls[0]["dimensions"]] == ["date"]
    assert [m["name"] for m in calls[0]["metrics"]] == ["activeUsers", "sessions", "newUsers"]
    assert len(calls) == 1


def test_events_and_daily_together_are_refused(monkeypatch, capsys):
    fake = Fake(A_ROWS, B_ROWS)
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--events", "--daily")
    assert "--events" in str(e.value) and "--daily" in str(e.value)
    assert fake.bodies == []                          # refused before any request
