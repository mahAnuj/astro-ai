"""#1277 (#1070 slice 4) -- `scripts/fetch_ga4.py --daily` carries returning users and a
per-day admin-landing count, each from its own optional request. Hermetic: `post`, `token`
and `window` are patched.

Each test is a way this could ship wrong: returning derived as activeUsers - newUsers (a
different quantity), a day with no returning row read as unknown when it is 0 (or as 0 when
the request FAILED), one failing extra request erasing the base series or the other extra,
a share computed over a zero denominator, or the admin filter dropped (every landing would
then count as an admin leak)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("fetch_ga4", ROOT / "scripts" / "fetch_ga4.py")
ga = importlib.util.module_from_spec(_spec)
sys.modules["fetch_ga4"] = ga
_spec.loader.exec_module(ga)

WIN = ("2026-11-10", "2026-11-14")


def _row(date, *vals):
    """Strings after the date are further dimension values, numbers are metric values."""
    return {"dimensionValues": [{"value": date.replace("-", "")}]
                               + [{"value": v} for v in vals if isinstance(v, str)],
            "metricValues": [{"value": str(v)} for v in vals if not isinstance(v, str)]}


BASE = {"rows": [_row("2026-11-10", 10, 12, 6), _row("2026-11-11", 8, 9, 3),
                 _row("2026-11-13", 20, 25, 15)]}
# 2026-11-12 has no returning row at all; 11-13 has a (not set) row that must be ignored.
RET = {"rows": [_row("2026-11-10", "returning", 4), _row("2026-11-10", "new", 6),
                _row("2026-11-11", "returning", 5),
                _row("2026-11-13", "(not set)", 99), _row("2026-11-13", "returning", 5)]}
ADMIN = {"rows": [_row("2026-11-10", 2), _row("2026-11-11", 1)]}


class Fake:
    """Routes by the request's dimensions and filter; an answer that is an ApiError (a SystemExit, not an Exception) is raised."""

    def __init__(self, base=BASE, ret=RET, admin=ADMIN):
        self.base, self.ret, self.admin, self.bodies = base, ret, admin, []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        names = [d["name"] for d in body["dimensions"]]
        ans = (self.ret if "newVsReturning" in names
               else self.admin if "dimensionFilter" in body else self.base)
        if isinstance(ans, BaseException):
            raise ans
        return ans


def run(monkeypatch, capsys, fake):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: WIN)
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", "--daily"])
    assert ga.main() == 0
    return json.loads(capsys.readouterr().out)


def _by(out, key):
    return {r["date"]: r[key] for r in out["rows"]}


def test_returning_is_mapped_by_date_and_a_missing_day_is_zero_on_success(monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake())
    # 11-12 has no returning row and no base row; 11-13 ignores the (not set) row.
    assert _by(out, "returning_users") == {
        "2026-11-10": 4, "2026-11-11": 5, "2026-11-12": 0, "2026-11-13": 5, "2026-11-14": 0}
    assert out["returning"]["status"] == "ok"
    assert out["returning"]["user_days"] == 14
    # 14 returning user-days over 10 + 8 + 20 active users.
    assert out["returning"]["share_pct"] == round(100 * 14 / 38, 1)
    note = out["returning"]["note"]
    assert "user-days" in note.lower() and "not unique people" in note
    assert "(not set)" in note


def test_a_failing_returning_request_is_null_with_the_http_code_and_base_rows_intact(
        monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake(ret=ga.ApiError("denied", 403)))
    assert all(v is None for v in _by(out, "returning_users").values())
    assert len(out["rows"]) == 5
    assert out["returning"]["status"] == "unavailable (HTTP 403)"
    assert out["returning"]["user_days"] is None
    assert _by(out, "active_users")["2026-11-10"] == 10
    assert _by(out, "new_users")["2026-11-13"] == 15
    assert out["days_with_traffic"] == 3


def test_share_is_null_when_status_is_not_ok_and_when_the_denominator_is_zero(
        monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake(ret=ga.ApiError("boom", 500)))
    assert out["returning"]["share_pct"] is None
    out = run(monkeypatch, capsys, Fake(base={"rows": []}, ret={"rows": []}))
    assert out["returning"]["status"] == "ok"
    assert out["returning"]["user_days"] == 0
    assert out["returning"]["share_pct"] is None      # 0 / 0 is not 0%


def test_admin_sessions_are_mapped_by_date_and_null_on_failure(monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake())
    assert _by(out, "admin_sessions") == {
        "2026-11-10": 2, "2026-11-11": 1, "2026-11-12": 0, "2026-11-13": 0, "2026-11-14": 0}
    assert "#735" in out["admin_note"]
    out = run(monkeypatch, capsys, Fake(admin=ga.ApiError("bad", 400)))
    assert all(v is None for v in _by(out, "admin_sessions").values())


def test_the_two_extra_requests_fail_independently(monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake(admin=ga.ApiError("bad", 400)))
    assert out["returning"]["status"] == "ok"
    assert _by(out, "returning_users")["2026-11-10"] == 4
    out = run(monkeypatch, capsys, Fake(ret=ga.ApiError("bad", 500)))
    assert _by(out, "admin_sessions")["2026-11-10"] == 2
    assert out["returning"]["status"] == "unavailable (HTTP 500)"


def test_no_data_days_carry_both_new_keys(monkeypatch, capsys):
    out = run(monkeypatch, capsys, Fake())
    gap = next(r for r in out["rows"] if r["date"] == "2026-11-12")
    assert gap["no_data"] is True
    assert gap["returning_users"] == 0 and gap["admin_sessions"] == 0
    out = run(monkeypatch, capsys, Fake(ret=ga.ApiError("x", 500), admin=ga.ApiError("x", 500)))
    gap = next(r for r in out["rows"] if r["date"] == "2026-11-12")
    assert "returning_users" in gap and gap["returning_users"] is None
    assert "admin_sessions" in gap and gap["admin_sessions"] is None


def test_request_bodies_use_newvsreturning_and_the_admin_regex_filter(monkeypatch, capsys):
    fake = Fake()
    run(monkeypatch, capsys, fake)
    assert len(fake.bodies) == 3
    ret = next(b for b in fake.bodies if "newVsReturning" in [d["name"] for d in b["dimensions"]])
    assert [d["name"] for d in ret["dimensions"]] == ["date", "newVsReturning"]
    assert [m["name"] for m in ret["metrics"]] == ["activeUsers"]
    assert ret["limit"] == 1200
    assert ret["dateRanges"] == fake.bodies[0]["dateRanges"]
    adm = next(b for b in fake.bodies if "dimensionFilter" in b)
    f = adm["dimensionFilter"]["filter"]
    assert f["fieldName"] == "landingPagePlusQueryString"
    assert f["stringFilter"] == {"matchType": "FULL_REGEXP", "value": "/admin([/?].*)?"}
    assert [m["name"] for m in adm["metrics"]] == ["sessions"]


def test_the_analyst_definition_names_the_new_fields_in_the_lever_1_row():
    md = (ROOT / ".claude/agents/analyst.md").read_text()
    lever1 = next(l for l in md.splitlines() if l.startswith("| 1 | **Growth**"))
    for needle in ("returning.user_days", "returning.share_pct", "admin_sessions"):
        assert needle in lever1, needle
