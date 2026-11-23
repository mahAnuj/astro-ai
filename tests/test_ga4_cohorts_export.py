"""#1364 -- `scripts/fetch_ga4.py --cohorts`: the window-wide cohort export that lets the
analyst say "N of M Direct sessions fall in cohorts with >=20 sessions and 0% engagement"
instead of "not measured". Hermetic: `post`, `token` and `window` are patched.

Each test is a way this export could ship wrong: a boundary that counts 19 or stops
counting 20, a cohort with one engaged session flagged as dead, `(not set)` rows dropped
(they are the very cohort the issue is about), a channel whose cohorts do not add up to its
sessions, a zero-session channel printing a share of 0, a truncated fetch passing silently,
summaries computed from the 50 rows shown instead of all, or the flag combining with
another report."""
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

WIN = ("2026-10-24", "2026-11-20")


def _cohort_rows(rows, row_count=None):
    """rows: (channel, browser, device, country, sessions, engaged, seconds)."""
    return {"rows": [{"dimensionValues": [{"value": v} for v in r[:4]],
                      "metricValues": [{"value": str(v)} for v in r[4:]]} for r in rows],
            "rowCount": len(rows) if row_count is None else row_count}


def _channel_rows(rows):
    """rows: (channel, sessions, engaged, seconds)."""
    return {"rows": [{"dimensionValues": [{"value": r[0]}],
                      "metricValues": [{"value": str(v)} for v in r[1:]]} for r in rows],
            "rowCount": len(rows)}


class Fake:
    """Answers the cohort request (4 dimensions) and the by-channel one (1); records bodies."""

    def __init__(self, cohort, channel):
        self.cohort, self.channel = cohort, channel
        self.bodies = []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        return self.cohort if len(body["dimensions"]) == 4 else self.channel


def run(monkeypatch, capsys, fake, *flags):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: WIN)
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", *flags])
    rc = ga.main()
    return rc, json.loads(capsys.readouterr().out)


def _ch(out):
    return {c["channel"]: c for c in out["channels"]}


def test_two_requests_with_the_declared_dimensions_metrics_and_window(monkeypatch, capsys):
    fake = Fake(_cohort_rows([("Direct", "Chrome", "desktop", "India", 30, 10, 900)]),
                _channel_rows([("Direct", 30, 10, 900)]))
    rc, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert rc == 0 and len(fake.bodies) == 2
    cohort, by_channel = fake.bodies
    assert [d["name"] for d in cohort["dimensions"]] == [
        "sessionDefaultChannelGroup", "browser", "deviceCategory", "country"]
    assert [d["name"] for d in by_channel["dimensions"]] == ["sessionDefaultChannelGroup"]
    for b in fake.bodies:
        assert [m["name"] for m in b["metrics"]] == [
            "sessions", "engagedSessions", "userEngagementDuration"]
        assert b["dateRanges"] == [{"startDate": WIN[0], "endDate": WIN[1]}]
        assert "dimensionFilter" not in b
        assert "date" not in [d["name"] for d in b["dimensions"]]
        assert b["orderBys"] == [{"metric": {"metricName": "sessions"}, "desc": True}]
    assert cohort["limit"] == 10000
    assert out["mode"] == "cohorts" and out["window"] == list(WIN)
    assert out["dimensions"] == ["sessionDefaultChannelGroup", "browser", "deviceCategory",
                                 "country"]
    assert out["min_cohort_sessions"] == 20


def test_headline_counts_only_cohorts_at_the_boundary_with_zero_engaged(monkeypatch, capsys):
    # 25 and 20 sessions, 0 engaged: counted (20 is the inclusive boundary).
    # 19 sessions, 0 engaged: too small to judge, but its sessions are still accounted for.
    # 25 sessions with 1 engaged: not zero engagement.
    cohort = _cohort_rows([
        ("Direct", "(not set)", "desktop", "United States", 25, 0, 0),
        ("Direct", "Chrome", "mobile", "China", 20, 0, 0),
        ("Direct", "Safari", "mobile", "India", 19, 0, 0),
        ("Direct", "Chrome", "desktop", "India", 25, 1, 40),
        ("Direct", "Firefox", "desktop", "India", 12, 6, 300),
    ])
    fake = Fake(cohort, _channel_rows([("Direct", 101, 7, 340)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert out["headline"] == ("45 of 101 Direct sessions fall in cohorts with "
                               ">=20 sessions and 0% engagement")
    d = _ch(out)["Direct"]
    assert (d["zero_cohorts"], d["zero_cohort_sessions"]) == (2, 45)
    assert d["small_cohort_sessions"] == 31          # 19 + 12
    assert d["zero_engagement_share"] == round(45 / 101, 4)
    flags = {(r["browser"], r["country"]): r["zero_engagement"] for r in out["rows"]}
    assert flags == {("(not set)", "United States"): True, ("Chrome", "China"): True,
                     ("Safari", "India"): False, ("Chrome", "India"): False,
                     ("Firefox", "India"): False}


def test_not_set_cohorts_are_kept_as_rows_and_counted(monkeypatch, capsys):
    cohort = _cohort_rows([("Direct", "(not set)", "(not set)", "(not set)", 40, 0, 0)])
    fake = Fake(cohort, _channel_rows([("Direct", 40, 0, 0)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert [(r["browser"], r["device"], r["country"]) for r in out["rows"]] == [
        ("(not set)", "(not set)", "(not set)")]
    assert _ch(out)["Direct"]["zero_cohort_sessions"] == 40


def test_every_channel_cohorts_add_up_to_its_sessions(monkeypatch, capsys):
    cohort = _cohort_rows([
        ("Direct", "Chrome", "desktop", "US", 30, 0, 0),        # zero
        ("Direct", "Chrome", "mobile", "IN", 50, 20, 800),      # big, engaged
        ("Direct", "Safari", "mobile", "IN", 8, 0, 0),          # small
        ("Organic Search", "Chrome", "mobile", "IN", 100, 70, 4000),
        ("Organic Search", "Edge", "desktop", "IN", 5, 0, 0),
    ])
    chan = _channel_rows([("Direct", 88, 20, 800), ("Organic Search", 105, 70, 4000)])
    _, out = run(monkeypatch, capsys, Fake(cohort, chan), "--cohorts")
    big_other = {"Direct": 50, "Organic Search": 100}
    for name, c in _ch(out).items():
        assert (c["zero_cohort_sessions"] + big_other[name] + c["small_cohort_sessions"]
                == c["sessions"])
    # Rates are recomputed from sums, never averaged over cohorts.
    assert _ch(out)["Direct"]["engaged_rate"] == round(20 / 88, 4)
    assert out["coverage_pct"] == 100 and out["total_sessions"] == 193


def test_a_channel_with_no_sessions_has_a_null_share_not_zero(monkeypatch, capsys):
    fake = Fake(_cohort_rows([("Organic Search", "Chrome", "mobile", "IN", 30, 20, 900)]),
                _channel_rows([("Organic Search", 30, 20, 900), ("Direct", 0, 0, 0)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    d = _ch(out)["Direct"]
    assert d["zero_engagement_share"] is None and d["engaged_rate"] is None
    assert out["headline"] == "no Direct sessions in the window, so no automated share can be stated"
    assert "0 of 0" not in out["headline"]


def test_an_empty_window_is_zeros_not_a_crash(monkeypatch, capsys):
    rc, out = run(monkeypatch, capsys, Fake({}, {}), "--cohorts")
    assert rc == 0
    assert out["total_sessions"] == 0 and out["coverage_pct"] is None
    assert out["rows"] == [] and out["channels"] == [] and out["cohort_count"] == 0
    assert out["headline"].startswith("no Direct sessions")


def test_truncation_is_reported_in_the_coverage_note(monkeypatch, capsys):
    cohort = _cohort_rows([("Direct", "Chrome", "desktop", "IN", 30, 10, 500)], row_count=77)
    fake = Fake(cohort, _channel_rows([("Direct", 30, 10, 500)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert out["truncated"] is True and out["row_count"] == 77
    assert "TRUNCATED: 1 of 77 cohort rows returned" in out["coverage_note"]


def test_the_note_says_flag_not_verdict_and_lower_bound(monkeypatch, capsys):
    fake = Fake(_cohort_rows([("Direct", "Chrome", "desktop", "IN", 30, 0, 0)]),
                _channel_rows([("Direct", 30, 0, 0)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    note = out["coverage_note"]
    assert "FLAG on a cohort, not a verdict" in note
    assert "GA4 cannot prove automation" in note and "lower bound" in note
    assert "TRUNCATED" not in note


def test_rows_are_capped_at_fifty_but_summaries_use_every_cohort(monkeypatch, capsys):
    # 60 cohorts of 20 zero-engaged sessions: all 60 count toward the channel, 50 are shown.
    rows = [("Direct", f"B{i:02d}", "desktop", "US", 20, 0, 0) for i in range(60)]
    fake = Fake(_cohort_rows(rows), _channel_rows([("Direct", 1200, 0, 0)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert len(out["rows"]) == 50 and out["rows_omitted"] == 10
    assert out["cohort_count"] == 60
    d = _ch(out)["Direct"]
    assert (d["zero_cohorts"], d["zero_cohort_sessions"]) == (60, 1200)
    assert out["headline"].startswith("1200 of 1200 Direct")
    # Ties on sessions break by (channel, browser, device, country), so the file is stable.
    assert [r["browser"] for r in out["rows"]] == [f"B{i:02d}" for i in range(50)]


def test_rows_sort_by_sessions_descending(monkeypatch, capsys):
    cohort = _cohort_rows([("Direct", "A", "desktop", "IN", 5, 1, 10),
                           ("Direct", "B", "desktop", "IN", 50, 9, 90)])
    fake = Fake(cohort, _channel_rows([("Direct", 55, 10, 100)]))
    _, out = run(monkeypatch, capsys, fake, "--cohorts")
    assert [r["browser"] for r in out["rows"]] == ["B", "A"]
    assert out["rows"][0]["avg_engagement_seconds"] == 1.8
    assert out["rows"][0]["engaged_rate"] == round(9 / 50, 4)


@pytest.mark.parametrize("other", ["--daily", "--events", "--anomalies", "--trend",
                                   "--journeys"])
def test_cohorts_with_another_report_is_refused_before_any_request(monkeypatch, capsys, other):
    fake = Fake({}, {})
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--cohorts", other)
    assert "--cohorts" in str(e.value) and other in str(e.value)
    assert fake.bodies == []


def test_cohorts_off_leaves_the_default_report_untouched(monkeypatch, capsys):
    calls = []

    def fake(url, body, bearer):
        calls.append(body)
        return {"rows": []}

    _, out = run(monkeypatch, capsys, fake)
    assert "mode" not in out and len(calls) == 2
    assert "browser" not in [d["name"] for d in calls[0]["dimensions"]]
