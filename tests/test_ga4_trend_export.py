"""#1115 -- `scripts/fetch_ga4.py --trend`: the GA4 previous-window export the analyst
asked for in four reports running. Hermetic: `post`, `token` and `window` are patched,
nothing touches the network.

Each test is a way this export could ship wrong: a previous window that is not the same
length (every channel then looks like it collapsed), a channel that appears or vanishes
dropped by an inner join, a percentage change from zero printed as 0 or infinity, an empty
window crashing on a missing `rows` key, or users summed across channels."""
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

CUR = ("2026-10-17", "2026-11-13")
PREV = ("2026-09-19", "2026-10-16")


def _mv(sessions, users=None, new=None, engaged=None, secs=None):
    vals = [sessions, sessions if users is None else users, 0 if new is None else new,
            0 if engaged is None else engaged, 0 if secs is None else secs]
    return [{"value": str(v)} for v in vals]


def _total(*a, **k):
    return {"rows": [{"metricValues": _mv(*a, **k)}]}


def _channels(rows, row_count=None):
    return {"rows": [{"dimensionValues": [{"value": ch}], "metricValues": _mv(*mv)}
                     for ch, mv in rows],
            "rowCount": len(rows) if row_count is None else row_count}


class Fake:
    """Answers by the request's dateRange and whether it has a dimension; records bodies."""

    def __init__(self, cur_total, cur_ch, pre_total, pre_ch):
        self.answers = {(CUR[0], False): cur_total, (CUR[0], True): cur_ch,
                        (PREV[0], False): pre_total, (PREV[0], True): pre_ch}
        self.bodies = []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        return self.answers[(body["dateRanges"][0]["startDate"], "dimensions" in body)]


def run(monkeypatch, capsys, fake, *flags):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: CUR)
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", *flags])
    rc = ga.main()
    return rc, json.loads(capsys.readouterr().out)


def _by(out):
    return {r["channel"]: r for r in out["by_channel"]}


def test_previous_window_is_the_same_length_ending_the_day_before():
    # The pair #1115 quotes: 28 days, then the 28 before them.
    assert ga.previous_window(*CUR) == PREV
    assert ga.previous_window("2026-11-07", "2026-11-13") == ("2026-10-31", "2026-11-06")
    assert ga.previous_window("2026-03-01", "2026-03-01") == ("2026-02-28", "2026-02-28")


def test_four_requests_two_per_window_none_by_date(monkeypatch, capsys):
    fake = Fake(_total(100), _channels([("Organic Search", (100,))]),
                _total(50), _channels([("Organic Search", (50,))]))
    rc, out = run(monkeypatch, capsys, fake, "--trend")
    assert rc == 0
    assert len(fake.bodies) == 4
    ranges = [(b["dateRanges"][0]["startDate"], b["dateRanges"][0]["endDate"])
              for b in fake.bodies]
    assert sorted(ranges) == sorted([CUR, CUR, PREV, PREV])
    assert all(len(b["dateRanges"]) == 1 for b in fake.bodies)
    for b in fake.bodies:
        assert [m["name"] for m in b["metrics"]] == [
            "sessions", "activeUsers", "newUsers", "engagedSessions",
            "userEngagementDuration"]
        assert "date" not in [d["name"] for d in b.get("dimensions", [])]
    dims = [b["dimensions"] for b in fake.bodies if "dimensions" in b]
    assert dims == [[{"name": "sessionDefaultChannelGroup"}]] * 2
    assert all(b["limit"] == ga.LIMIT for b in fake.bodies if "dimensions" in b)
    assert out["mode"] == "trend" and out["property"] == "123"
    assert out["window"] == list(CUR) and out["window_prev"] == list(PREV)


def test_totals_carry_every_metric_and_delta_pct_arithmetic(monkeypatch, capsys):
    fake = Fake(_total(150, 90, 60, 75, 3000), _channels([("Direct", (150,))]),
                _total(100, 80, 0, 40, 1000), _channels([("Direct", (100,))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    t = out["totals"]
    assert t["current"] == {"sessions": 150, "active_users": 90, "new_users": 60,
                            "engaged_sessions": 75, "engagement_seconds": 3000}
    assert t["previous"]["sessions"] == 100
    assert t["delta"]["sessions"] == 50 and t["delta_pct"]["sessions"] == 50.0
    assert t["delta"]["active_users"] == 10 and t["delta_pct"]["active_users"] == 12.5
    assert t["delta_pct"]["engagement_seconds"] == 200.0
    assert t["delta"]["new_users"] == 60
    assert t["delta_pct"]["new_users"] is None        # previous 0: None, not 0 / inf
    assert all(isinstance(v, int) for v in t["current"].values())


def test_a_channel_only_now_is_new_with_no_percentage(monkeypatch, capsys):
    fake = Fake(_total(130), _channels([("Organic Search", (100,)), ("Referral", (30,))]),
                _total(100), _channels([("Organic Search", (100,))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    r = _by(out)["Referral"]
    assert r["is_new"] is True and r["is_gone"] is False
    assert r["previous"]["sessions"] == 0 and r["current"]["sessions"] == 30
    assert r["delta"]["sessions"] == 30
    assert r["delta_pct"]["sessions"] is None
    assert _by(out)["Organic Search"]["is_new"] is False


def test_a_channel_only_before_is_gone_not_dropped(monkeypatch, capsys):
    fake = Fake(_total(100), _channels([("Organic Search", (100,))]),
                _total(140), _channels([("Organic Search", (100,)), ("Paid Search", (40,))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    r = _by(out)["Paid Search"]
    assert r["is_gone"] is True and r["is_new"] is False
    assert r["current"]["sessions"] == 0 and r["previous"]["sessions"] == 40
    assert r["delta"]["sessions"] == -40
    assert r["delta_pct"]["sessions"] == -100.0


def test_channels_are_sorted_by_the_size_of_the_movement_not_its_sign(monkeypatch, capsys):
    fake = Fake(_total(190),
                _channels([("Organic Search", (140,)), ("Direct", (30,)), ("Social", (20,))]),
                _total(180),
                _channels([("Organic Search", (100,)), ("Direct", (60,)), ("Social", (20,))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    assert [r["channel"] for r in out["by_channel"]] == ["Organic Search", "Direct", "Social"]
    assert [r["delta"]["sessions"] for r in out["by_channel"]] == [40, -30, 0]


def test_an_empty_previous_window_is_zeros_and_says_so(monkeypatch, capsys):
    # GA4 sends no `rows` key at all for a window with no data.
    fake = Fake(_total(80), _channels([("Direct", (80,))]), {}, {})
    rc, out = run(monkeypatch, capsys, fake, "--trend")
    assert rc == 0
    assert out["totals"]["previous"] == dict.fromkeys(ga.TREND_KEYS, 0)
    assert out["totals"]["delta_pct"]["sessions"] is None
    assert "previous window empty: property may not have been collecting" \
        in out["coverage_note"]
    assert _by(out)["Direct"]["is_new"] is True
    assert out["channels_prev"] == 0


def test_empty_current_window_is_also_zeros_not_a_crash(monkeypatch, capsys):
    fake = Fake({}, {}, _total(40), _channels([("Direct", (40,))]))
    rc, out = run(monkeypatch, capsys, fake, "--trend")
    assert out["totals"]["current"]["sessions"] == 0
    assert out["totals"]["delta_pct"]["sessions"] == -100.0
    assert _by(out)["Direct"]["is_gone"] is True
    assert "previous window empty" not in out["coverage_note"]


def test_the_note_says_users_do_not_add_up_across_channels(monkeypatch, capsys):
    fake = Fake(_total(100, 60), _channels([("Direct", (50, 40)), ("Organic Search", (50, 40))]),
                _total(100, 60), _channels([("Direct", (100, 60))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    assert "do NOT sum to the site total" in out["coverage_note"]
    assert "must not be added up" in out["coverage_note"]


def test_coverage_share_and_truncation_are_reported(monkeypatch, capsys):
    fake = Fake(_total(200), _channels([("Direct", (150,))], row_count=9),
                _total(100), _channels([("Direct", (100,))]))
    _, out = run(monkeypatch, capsys, fake, "--trend")
    note = out["coverage_note"]
    assert "current window: channel rows account for 75% of the site's 200 sessions" in note
    assert "current window TRUNCATED: 1 of 9 channel rows returned" in note
    assert "previous window" not in note              # 100% covered, not truncated


@pytest.mark.parametrize("other", ["--daily", "--events", "--anomalies"])
def test_trend_with_another_report_is_refused_before_any_request(monkeypatch, capsys, other):
    fake = Fake({}, {}, {}, {})
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--trend", other)
    assert "--trend" in str(e.value) and other in str(e.value)
    assert fake.bodies == []


def test_trend_off_leaves_the_default_report_untouched(monkeypatch, capsys):
    calls = []

    def fake(url, body, bearer):
        calls.append(body)
        return {"rows": []}

    _, out = run(monkeypatch, capsys, fake)
    assert "mode" not in out and len(calls) == 2
