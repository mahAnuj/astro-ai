"""#1236 -- `fetch_ga4.py --anomalies` second tier. The spike bar is max(2 x median,
median + 10, 15), so at a median of 22 it is 44 and five of the seven days at 32+ users
(10-23, 11-09, 11-10, 11-12, 11-14) had no named source, four analyst reports running.
`watch_days` is the tier between; `spike_days` and its test are untouched.

Each test is a way this could ship wrong: a spike repeated in `watch`, a day cut by
`spike_days`' own cap of 3 falling into a gap, an unbounded request count against the
GA4 quota, or one failing watch day erasing the spike breakdown (the workflow deletes
the whole file on any failure). Hermetic: `post` is patched, nothing touches the network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("fetch_ga4", ROOT / "scripts" / "fetch_ga4.py")
ga = importlib.util.module_from_spec(_spec)
sys.modules["fetch_ga4"] = ga
_spec.loader.exec_module(ga)

START = date(2026, 10, 20)


def _days(vals):
    return [{"date": (START + timedelta(days=i)).isoformat(), "active_users": v}
            for i, v in enumerate(vals)]


# The issue's window: 28 days, median 22, seven days at or above 32, two at or above 44.
# 21 ordinary days (ten at 20, eleven at 22) put sorted[14] on 22.
_LOW = [20] * 10 + [22] * 11
_HIGH = [57, 40, 34, 46, 34, 32, 32]
ISSUE_VALS = _LOW[:3] + [_HIGH[0]] + _LOW[3:8] + _HIGH[1:3] + _LOW[8:12] + [_HIGH[3]] + \
    _LOW[12:15] + _HIGH[4:] + _LOW[15:]
ISSUE = _days(ISSUE_VALS)


def test_the_issue_window_has_the_shape_the_issue_describes():
    assert len(ISSUE) == 28
    assert sorted(ISSUE_VALS)[14] == 22
    assert sum(v >= 32 for v in ISSUE_VALS) == 7
    assert [r["active_users"] for r in ga.spike_days(ISSUE)] == [57, 46]


def test_the_five_days_under_the_spike_bar_come_back_most_extreme_first():
    spikes = ga.spike_days(ISSUE)
    watch = ga.watch_days(ISSUE, spikes)
    assert [r["active_users"] for r in watch] == [40, 34, 34, 32, 32]
    spike_dates = {s["date"] for s in spikes}
    assert not spike_dates & {r["date"] for r in watch}, "a spike must never repeat in watch"
    assert {r["median"] for r in watch} == {22}
    assert {r["threshold"] for r in watch} == {32}


def test_a_day_at_the_bar_is_in_and_one_below_it_is_out():
    vals = [22] * 20 + [32, 31] + [22] * 6
    watch = ga.watch_days(_days(vals), [])
    assert [r["active_users"] for r in watch] == [32]


def test_the_cap_keeps_the_most_extreme_days():
    vals = [22] * 19 + [33, 34, 35, 36, 37, 38, 39, 40, 41]
    watch = ga.watch_days(_days(vals), [])
    assert [r["active_users"] for r in watch] == [41, 40, 39, 38, 37, 36, 35]
    assert len(ga.watch_days(_days(vals), [], top=2)) == 2


def test_fewer_than_seven_days_judges_nothing():
    assert ga.watch_days(_days([3, 1, 2, 90]), []) == []
    assert ga.watch_days(_days([20] * 5 + [90]), []) == []


def test_a_spike_cut_by_the_spike_cap_lands_in_watch_not_in_a_gap():
    # Four days over the spike bar (44); spike_days keeps three.
    vals = [22] * 22 + [50, 60, 70, 80, 22, 22]
    rows = _days(vals)
    spikes = ga.spike_days(rows)
    assert [r["active_users"] for r in spikes] == [80, 70, 60]
    assert [r["active_users"] for r in ga.watch_days(rows, spikes)] == [50]


# --- anomalies(), end to end ---------------------------------------------------

def _drow(dims, sessions):
    return {"dimensionValues": [{"value": d} for d in dims],
            "metricValues": [{"value": str(v)} for v in (sessions, sessions, sessions, sessions * 30)]}


class Fake:
    def __init__(self, vals, fail_dates=()):
        self.vals, self.fail_dates, self.bodies = vals, set(fail_dates), []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        dims = [d["name"] for d in body["dimensions"]]
        if dims == ["date"]:
            return {"rows": [{"dimensionValues": [{"value": r["date"].replace("-", "")}],
                              "metricValues": [{"value": str(r["active_users"])}]}
                             for r in _days(self.vals)]}
        if body["dateRanges"][0]["startDate"] in self.fail_dates:
            from _gapi import ApiError
            raise ApiError("HTTP 429 from analyticsdata.googleapis.com", 429)
        if len(dims) == 2:
            return {"rows": [_drow(["google / organic", "/learn/x"], 9)]}
        return {"rows": [_drow(["Chrome", "mobile", "India"], 9)]}


def run(monkeypatch, capsys, fake):
    monkeypatch.setattr(ga, "post", fake)
    args = SimpleNamespace(property="123")
    assert ga.anomalies(args, "2026-10-20", "2026-11-16", "t") == 0
    return json.loads(capsys.readouterr().out)


def test_every_elevated_day_is_broken_down_and_tagged(monkeypatch, capsys):
    fake = Fake(ISSUE_VALS)
    out = run(monkeypatch, capsys, fake)
    assert [s["tier"] for s in out["spikes"]] == ["spike", "spike"]
    assert [w["tier"] for w in out["watch"]] == ["watch"] * 5
    assert out["rule"] == "active users >= max(2 x median, median + 10, 15)"
    assert out["watch_rule"] == "active users >= median + 10, not a spike"
    assert out["watch_omitted"] == 0
    for d in out["spikes"] + out["watch"]:
        assert d["by_source"] and d["by_tech"] and d["explanation"]
        assert d["by_source"][0]["sessionSourceMedium"] == "google / organic"
    assert len(fake.bodies) == 1 + 2 * (2 + 5)


def test_the_request_count_is_bounded_and_the_truncation_is_reported(monkeypatch, capsys):
    fake = Fake([22] * 19 + [33, 34, 35, 36, 37, 38, 39, 40, 41])
    out = run(monkeypatch, capsys, fake)
    assert out["spikes"] == []
    assert len(out["watch"]) == 7
    assert out["watch_omitted"] == 2
    assert len(fake.bodies) == 1 + 2 * 7


def test_a_failing_watch_day_leaves_the_spike_breakdown_intact(monkeypatch, capsys):
    # Fail exactly one watch day: the most extreme of the five.
    bad = next(r["date"] for r in ISSUE if r["active_users"] == 40)
    out = run(monkeypatch, capsys, Fake(ISSUE_VALS, fail_dates=[bad]))
    assert all(s["by_source"] and "failed" not in s["explanation"] for s in out["spikes"])
    failed = [w for w in out["watch"] if w["date"] == bad]
    assert len(failed) == 1
    assert failed[0]["explanation"] == "breakdown failed (HTTP 429)"
    assert failed[0]["by_source"] == [] and failed[0]["by_tech"] == []
    assert all(w["by_source"] for w in out["watch"] if w["date"] != bad)


def test_a_failing_spike_day_still_propagates(monkeypatch, capsys):
    import pytest
    spike = next(r["date"] for r in ISSUE if r["active_users"] == 57)
    with pytest.raises(SystemExit):
        run(monkeypatch, capsys, Fake(ISSUE_VALS, fail_dates=[spike]))
