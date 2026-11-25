"""#1272: the server's own per-day count of fresh kundli generations, for #1068.

Each test is a way the export could have lied to the analyst: a read failure written as
zero, probes counted as visitors, a 303 count claimed that the event cannot give, or an
email leaking into a file that is committed to the repo.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "collect_kundli_submissions", ROOT / "scripts" / "collect_kundli_submissions.py")
ck = importlib.util.module_from_spec(_spec)
sys.modules["collect_kundli_submissions"] = ck
_spec.loader.exec_module(ck)

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def _ev(day, type_="form_kundli", **data):
    return {"ts": f"{day}T10:00:00+00:00", "type": type_, "email": "seeker@example.com", "data": data}


def _doc(evts, days=3):
    return ck.build(evts, NOW, days)


def _row(doc, day):
    return next(r for r in doc["days"] if r["date"] == day)


def test_a_day_with_no_events_at_all_is_null_not_zero():
    """storage.get returns None for 'absent' and for 'GCS failed': an empty day is unknown."""
    doc = _doc([_ev("2026-11-23", probe=False)])
    assert _row(doc, "2026-11-22")["fresh_generations"] is None
    assert _row(doc, "2026-11-23")["fresh_generations"] == 1
    assert doc["totals"]["days_unknown"] == 2


def test_a_day_with_other_events_but_no_kundli_is_a_real_zero():
    doc = _doc([_ev("2026-11-22", "page_view"), _ev("2026-11-23", probe=False)])
    assert _row(doc, "2026-11-22")["fresh_generations"] == 0


def test_a_day_at_the_event_cap_is_null_because_the_head_was_dropped(monkeypatch):
    monkeypatch.setattr(ck, "_cap", lambda: 3)
    doc = _doc([_ev("2026-11-23", "page_view")] * 3)
    assert _row(doc, "2026-11-23")["fresh_generations"] is None


def test_events_before_the_probe_marker_have_unknown_probe_split():
    doc = _doc([_ev("2026-11-22", lang="en"), _ev("2026-11-22", lang="en")])
    r = _row(doc, "2026-11-22")
    assert r["fresh_generations"] == 2 and r["probe"] is None and r["non_probe"] is None


def test_a_day_mixing_marked_and_unmarked_events_is_unknown_not_a_partial_split():
    doc = _doc([_ev("2026-11-23", probe=True), _ev("2026-11-23", lang="en")])
    r = _row(doc, "2026-11-23")
    assert r["fresh_generations"] == 2 and r["probe"] is None and r["non_probe"] is None


def test_once_marked_the_probe_split_is_exact():
    doc = _doc([_ev("2026-11-23", probe=True), _ev("2026-11-23", probe=False),
                _ev("2026-11-23", probe=False)])
    r = _row(doc, "2026-11-23")
    assert (r["fresh_generations"], r["probe"], r["non_probe"]) == (3, 1, 2)
    assert doc["totals"]["non_probe"] == 2 and doc["totals"]["probe_days_unknown"] == 2


def test_a_zero_sum_beside_an_unknown_day_is_unknown_not_zero():
    # 11-22 has no events (unknown), 11-23 is a known zero: nothing proves a quiet window.
    doc = _doc([_ev("2026-11-23", "page_view")], days=2)
    assert doc["totals"]["fresh_generations"] is None
    # a positive sum beside an unknown day is still reported (it is a floor, days_unknown says so)
    doc = _doc([_ev("2026-11-23", probe=False)], days=2)
    assert doc["totals"]["fresh_generations"] == 1 and doc["totals"]["days_unknown"] == 1


def test_semantics_says_what_the_number_is_not():
    s = _doc([_ev("2026-11-23", probe=False)])["semantics"]
    assert "FRESH" in s and "303" in s and "probe" in s and "NOT 1:1" in s
    assert "non_probe_dates" in s


def test_non_probe_dates_names_the_days_non_probe_sums_over():
    """#1408: fresh covers both days, non_probe only the marked one; the dates say which."""
    t = _doc([_ev("2026-11-22"), _ev("2026-11-23", probe=False)], days=2)["totals"]
    assert t["non_probe_dates"] == ["2026-11-23"]
    assert t["fresh_generations"] == 2 and t["non_probe"] == 1 and t["probe_days_unknown"] == 1


def test_non_probe_dates_skips_unmarked_empty_and_capped_days(monkeypatch):
    monkeypatch.setattr(ck, "_cap", lambda: 4)
    evts = [_ev("2026-11-18", probe=False),                        # marked
            # 11-19 has no events at all: unknown
            _ev("2026-11-20", probe=True), _ev("2026-11-20", lang="en"),  # mixed: unknown split
            _ev("2026-11-21", probe=True),                          # marked
            *[_ev("2026-11-22", "page_view")] * 4,                  # at the cap: unknown
            _ev("2026-11-23", "page_view")]                         # known zero kundli, marked (vacuously)
    doc = _doc(evts, days=6)
    assert doc["totals"]["non_probe_dates"] == ["2026-11-18", "2026-11-21", "2026-11-23"]


def test_totals_probe_and_non_probe_are_exactly_the_sum_over_non_probe_dates():
    doc = _doc([_ev("2026-11-21", probe=True), _ev("2026-11-21", probe=False),
                _ev("2026-11-22", lang="en"),
                _ev("2026-11-23", probe=False), _ev("2026-11-23", probe=False)], days=3)
    t = doc["totals"]
    listed = [_row(doc, d) for d in t["non_probe_dates"]]
    assert t["non_probe_dates"] == ["2026-11-21", "2026-11-23"]
    assert t["non_probe"] == sum(r["non_probe"] for r in listed) == 3
    assert t["probe"] == sum(r["probe"] for r in listed) == 1
    assert t["fresh_generations"] == 5  # the unmarked day is in this one and in neither of the others


def test_no_marked_day_gives_empty_dates_and_null_totals():
    t = _doc([_ev("2026-11-22", lang="en"), _ev("2026-11-23", lang="en")], days=2)["totals"]
    assert t["non_probe_dates"] == []
    assert t["probe"] is None and t["non_probe"] is None


def test_the_analyst_definition_names_non_probe_dates():
    """Drift guard: the reader of this file is the analyst; it must be told which days to use."""
    md = (ROOT / ".claude/agents/analyst.md").read_text()
    assert "non_probe_dates" in md


def test_the_output_carries_no_email_identity_rashi_or_city(tmp_path):
    out = tmp_path / "k.json"
    evts = [_ev("2026-11-23", identity="deadbeefcafe1234", rashi_moon="Karka", rashi_lagna="Simha",
                city="Varanasi", lang="hi", probe=False)]
    assert ck.main(["x", "--out", str(out), "--days", "2"], reader=lambda d: evts, now=NOW) == 0
    text = out.read_text()
    for leaked in ("seeker@example.com", "deadbeefcafe1234", "Karka", "Simha", "Varanasi", "hi\""):
        assert leaked not in text, leaked
    assert json.loads(text)["days"][-1]["fresh_generations"] == 1


def test_days_outside_the_retention_window_is_a_usage_error(tmp_path):
    for bad in ("0", "31"):
        assert ck.main(["x", "--out", str(tmp_path / "k.json"), "--days", bad],
                       reader=lambda d: [], now=NOW) == 2
    assert not (tmp_path / "k.json").exists()


def test_an_unset_bucket_writes_nothing_and_exits_1(tmp_path, monkeypatch):
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    assert ck.main(["x", "--out", str(tmp_path / "k.json")], now=NOW) == 1
    assert not (tmp_path / "k.json").exists()


def test_a_read_that_raises_or_finds_nothing_writes_nothing(tmp_path):
    def boom(days):
        raise OSError("gcs down")
    assert ck.main(["x", "--out", str(tmp_path / "a.json")], reader=boom, now=NOW) == 1
    assert ck.main(["x", "--out", str(tmp_path / "b.json")], reader=lambda d: [], now=NOW) == 1
    assert not (tmp_path / "a.json").exists() and not (tmp_path / "b.json").exists()


def test_the_window_is_the_requested_utc_days_ending_today(tmp_path):
    out = tmp_path / "k.json"
    ck.main(["x", "--out", str(out), "--days", "5"], reader=lambda d: [_ev("2026-11-23", probe=False)], now=NOW)
    doc = json.loads(out.read_text())
    assert doc["window"] == {"from": "2026-11-19", "to": "2026-11-23"} and len(doc["days"]) == 5


# --- the call site: the route must mark probes, or the split above has nothing to read ----------

def _kundli_event(client, saved_chart, monkeypatch, birth_time, headers=None):
    from astro_ai.routes import kundli as K
    seen = []
    monkeypatch.setattr(K.notify, "kundli_generated", lambda **kw: None)
    monkeypatch.setattr(K.events, "record", lambda **kw: seen.append(kw))
    monkeypatch.setattr(K, "generate_reading", lambda *a, **k: "## Personality\n" + "Body. " * 80)
    saved_chart(birth_date="1991-03-07", birth_time=birth_time, birth_place="Varanasi, India", name="P")
    client.get("/kundli", headers=headers or {})
    return [kw for kw in seen if kw.get("type") == "form_kundli"]


def test_a_probe_request_marks_the_form_kundli_event(client, saved_chart, monkeypatch):
    from astro_ai import probe
    got = _kundli_event(client, saved_chart, monkeypatch, "03:11",
                        {probe.PROBE_HEADER: probe.PROBE_VALUE})
    assert len(got) == 1 and got[0]["data"]["probe"] is True


def test_an_ordinary_request_still_writes_the_marker_as_false(client, saved_chart, monkeypatch):
    got = _kundli_event(client, saved_chart, monkeypatch, "03:12")
    assert len(got) == 1 and got[0]["data"]["probe"] is False


def test_is_probe_is_an_exact_match_and_never_raises():
    from astro_ai import probe

    class _R:
        def __init__(self, v):
            self.headers = {} if v is None else {probe.PROBE_HEADER: v}

    assert probe.is_probe(_R(probe.PROBE_VALUE)) is True
    for v in (None, "", "0", "verify-production-x", "verify"):
        assert probe.is_probe(_R(v)) is False, v
    assert probe.is_probe(None) is False
