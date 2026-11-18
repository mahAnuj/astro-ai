"""#1226 -- `scripts/fetch_ga4.py --journeys`: landing page x event, plus the tool /
event_type / mode splits, so #1070's completion ratio (completed / submitted) and
"which landing leads to a tool being used" are readable. Hermetic: `post`, `token` and
`window` are patched, nothing touches the network.

Each test is a way this export could ship wrong: landings that differ only by query
string or a slash reported as separate pages, truncation that is silent, an
unregistered custom dimension that takes the whole run down with it (or a 403 read as
"unregistered"), and a zero before an event existed that reads like a measurement."""
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

SPLIT_DIMS = ("customEvent:tool", "customEvent:event_type", "customEvent:mode")


def _row(dims, *metrics):
    return {"dimensionValues": [{"value": d} for d in dims],
            "metricValues": [{"value": str(m)} for m in metrics]}


class Fake:
    """Records every body. Request A has a landingPage dimension; a split has a
    customEvent one. `split_rows` / `split_exc` are keyed by that dimension name."""

    def __init__(self, a=None, a_row_count=None, split_rows=None, split_exc=None,
                 split_row_count=None):
        self.a, self.a_row_count = a or [], a_row_count
        self.split_rows = split_rows or {}
        self.split_exc = split_exc or {}
        self.split_row_count = split_row_count or {}
        self.bodies = []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        dims = [d["name"] for d in body["dimensions"]]
        if "landingPage" in dims:
            return {"rows": self.a, "rowCount": self.a_row_count
                    if self.a_row_count is not None else len(self.a)}
        dim = dims[1]
        if dim in self.split_exc:
            raise self.split_exc[dim]
        rows = self.split_rows.get(dim, [])
        return {"rows": rows, "rowCount": self.split_row_count.get(dim, len(rows))}


def run(monkeypatch, capsys, fake, *flags):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: ("2026-10-09", "2026-11-05"))
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", *flags])
    rc = ga.main()
    return rc, json.loads(capsys.readouterr().out)


A_ROWS = [
    _row(["/matching", "tool_submitted"], 10, 14),
    _row(["/matching/", "tool_submitted"], 2, 3),                 # trailing slash: same page
    _row(["/matching?utm_source=x", "tool_submitted"], 1, 1),     # query string: same page
    _row(["/matching", "matching_completed"], 9, 9),
    _row(["/", "cta_click"], 4, 6),
    _row(["(not set)", "tool_submitted"], 1, 1),
]
SPLITS_OK = {
    "customEvent:tool": [_row(["tool_submitted", "matching"], 18),
                         _row(["tool_submitted", "kundli"], 5)],
    "customEvent:event_type": [_row(["muhurat_searched", "griha_pravesh"], 3)],
    "customEvent:mode": [_row(["muhurat_searched", "single"], 3)],
}


def test_the_requests_ask_for_the_declared_events_and_each_split_on_its_own(
        monkeypatch, capsys):
    fake = Fake(A_ROWS, split_rows=SPLITS_OK)
    run(monkeypatch, capsys, fake, "--journeys")
    a, *splits = fake.bodies
    assert len(fake.bodies) == 4
    assert [d["name"] for d in a["dimensions"]] == ["landingPage", "eventName"]
    assert [m["name"] for m in a["metrics"]] == ["sessions", "eventCount"]
    assert a["limit"] == ga.LIMIT
    declared = ["tool_submitted", "kundli_generated", "matching_completed",
                "numerology_completed", "muhurat_searched", "dosha_check_completed",
                "ask_answered", "subscribe_completed", "cta_click"]
    assert a["dimensionFilter"]["filter"]["fieldName"] == "eventName"
    assert a["dimensionFilter"]["filter"]["inListFilter"]["values"] == declared
    assert [[d["name"] for d in b["dimensions"]] for b in splits] == [
        ["eventName", dim] for dim in SPLIT_DIMS]      # one custom dimension per request
    assert all(b["metrics"] == [{"name": "eventCount"}] for b in splits)
    assert splits[0]["dimensionFilter"]["filter"]["inListFilter"]["values"] == [
        "tool_submitted"]
    assert splits[1]["dimensionFilter"]["filter"]["inListFilter"]["values"] == [
        "muhurat_searched"]


def test_landings_fold_to_a_path_and_rows_that_fold_together_are_summed(
        monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_rows=SPLITS_OK), "--journeys")
    assert rc == 0
    by = {(r["landing"], r["event"]): r for r in out["rows"]}
    assert by[("/matching", "tool_submitted")] == {
        "landing": "/matching", "event": "tool_submitted", "sessions": 13, "event_count": 18}
    assert ("/matching/", "tool_submitted") not in by
    assert by[("/", "cta_click")]["event_count"] == 6
    assert ("(not set)", "tool_submitted") in by       # kept, not dropped: totals add up
    assert all(isinstance(r["event_count"], int) and isinstance(r["sessions"], int)
               for r in out["rows"])
    assert out["rows"][0]["event_count"] == 18         # most events first
    assert out["landing_count"] == 3
    assert out["event_totals"]["tool_submitted"] == 19
    assert out["event_totals"]["ask_answered"] == 0    # declared, none recorded
    assert out["mode"] == "journeys" and out["window"] == ["2026-10-09", "2026-11-05"]


@pytest.mark.parametrize("raw,path", [
    ("/matching/?fbclid=1", "/matching"), ("/matching#x", "/matching"),
    ("/muhurat/griha-pravesh/", "/muhurat/griha-pravesh"), ("/", "/"), ("/?a=1", "/"),
    ("(not set)", "(not set)")])
def test_fold_landing(raw, path):
    assert ga.fold_landing(raw) == path


def test_splits_are_emitted_with_status_ok(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_rows=SPLITS_OK), "--journeys")
    s = out["splits"]
    assert set(s) == {"tool", "event_type", "mode"}
    assert all(v["status"] == "ok" and v["truncated"] is False for v in s.values())
    assert s["tool"]["dimension"] == "customEvent:tool"
    assert s["tool"]["rows"] == [{"event": "tool_submitted", "value": "matching", "count": 18},
                                 {"event": "tool_submitted", "value": "kundli", "count": 5}]
    assert s["mode"]["rows"][0]["value"] == "single"


def test_truncation_of_the_main_request_is_reported_never_silent(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys,
                  Fake(A_ROWS, a_row_count=1500, split_rows=SPLITS_OK), "--journeys")
    assert out["truncated"] is True and out["row_count"] == 1500
    assert "TRUNCATED: 6 of 1500 landing x event rows" in out["coverage_note"]
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_rows=SPLITS_OK), "--journeys")
    assert out["truncated"] is False
    assert "TRUNCATED" not in out["coverage_note"]


def test_truncation_of_a_split_is_reported(monkeypatch, capsys):
    fake = Fake(A_ROWS, split_rows=SPLITS_OK, split_row_count={"customEvent:tool": 1200})
    rc, out = run(monkeypatch, capsys, fake, "--journeys")
    assert out["splits"]["tool"]["truncated"] is True
    assert out["splits"]["mode"]["truncated"] is False
    assert "split tool TRUNCATED: 2 of 1200" in out["coverage_note"]


def test_a_400_on_one_split_voids_only_that_split(monkeypatch, capsys):
    exc = {"customEvent:event_type": ga.ApiError("HTTP 400 from analyticsdata", 400)}
    rc, out = run(monkeypatch, capsys,
                  Fake(A_ROWS, split_rows=SPLITS_OK, split_exc=exc), "--journeys")
    assert rc == 0
    assert out["splits"]["event_type"]["status"] == "unregistered"
    assert out["splits"]["event_type"]["rows"] == []
    assert out["splits"]["tool"]["status"] == "ok" and out["splits"]["tool"]["rows"]
    assert out["splits"]["mode"]["status"] == "ok"
    assert out["event_totals"]["tool_submitted"] == 19      # request A intact
    assert len(out["rows"]) == 4                              # 6 raw rows, folded
    assert "not registered as a custom dimension" in out["coverage_note"]
    assert "customEvent:event_type" in out["coverage_note"]


def test_all_three_splits_unregistered_still_returns_the_landing_rows(monkeypatch, capsys):
    exc = {d: ga.ApiError("HTTP 400", 400) for d in SPLIT_DIMS}
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_exc=exc), "--journeys")
    assert rc == 0
    assert {v["status"] for v in out["splits"].values()} == {"unregistered"}
    assert out["rows"]


@pytest.mark.parametrize("status", [403, 500])
@pytest.mark.parametrize("dim", SPLIT_DIMS)
def test_any_other_error_on_a_split_still_fails_the_run(monkeypatch, capsys, status, dim):
    fake = Fake(A_ROWS, split_rows=SPLITS_OK,
                split_exc={dim: ga.ApiError(f"HTTP {status} from x", status)})
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--journeys")
    assert e.value.status == status


def test_a_403_on_the_main_request_fails_the_run(monkeypatch, capsys):
    def boom(url, body, bearer):
        raise ga.ApiError("HTTP 403 from x", 403)

    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, boom, "--journeys")
    assert e.value.status == 403


def test_a_split_of_only_not_set_is_not_emitted_as_data(monkeypatch, capsys):
    sr = dict(SPLITS_OK, **{"customEvent:tool": [_row(["tool_submitted", "(not set)"], 19)]})
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_rows=sr), "--journeys")
    assert out["splits"]["tool"]["status"] == "not_set"
    assert out["splits"]["tool"]["rows"] == []


def test_the_note_says_sessions_are_not_additive_and_dates_each_event(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake(A_ROWS, split_rows=SPLITS_OK), "--journeys")
    assert "NOT additive across events" in out["coverage_note"]
    ev = out["events"]
    assert ev["tool_submitted"] == {"since": None, "partial_history": None}
    assert ev["matching_completed"] == {"since": "2026-11-18", "partial_history": True}
    assert ev["cta_click"] == {"since": "2026-11-03", "partial_history": True}
    assert "not a measurement" in out["coverage_note"]
    # A window that starts after the event began has no partial history.
    monkeypatch.setattr(ga, "window", lambda days: ("2026-11-20", "2026-12-10"))
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", "--journeys"])
    monkeypatch.setattr(ga, "post", Fake(A_ROWS, split_rows=SPLITS_OK))
    ga.main()
    assert json.loads(capsys.readouterr().out)["events"]["matching_completed"][
        "partial_history"] is False


@pytest.mark.parametrize("other", ["--daily", "--events", "--anomalies", "--trend"])
def test_journeys_is_exclusive_with_the_other_reports(monkeypatch, capsys, other):
    fake = Fake(A_ROWS)
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--journeys", other)
    assert "--journeys" in str(e.value) and other in str(e.value)
    assert fake.bodies == []                          # refused before any request


def test_other_reports_are_not_changed_by_the_flag_existing(monkeypatch, capsys):
    calls = []

    def fake(url, body, bearer):
        calls.append(body)
        return {"rows": []}

    run(monkeypatch, capsys, fake)
    assert [d["name"] for d in calls[0]["dimensions"]] == [
        "landingPagePlusQueryString", "sessionDefaultChannelGroup"]
