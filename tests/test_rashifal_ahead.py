"""Tomorrow's rashifal is written the day before (#852, 2026-11-10).

Measured: the `0 22 * * *` job started 00:50-03:59 UTC over its last 12 runs,
after the 01:00 UTC Groq warm, so Groq generated every day (177 calls, 778,261
input tokens in a week) while Claude's valid text arrived afterwards.
"""
from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from astro_ai import ops_data

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "rashifal-generate.yml"
_spec = importlib.util.spec_from_file_location("rashifal_target_date", ROOT / "scripts" / "rashifal_target_date.py")
rtd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rtd)


def utc(h, m=0, day=10):
    return datetime(2026, 11, day, h, m, tzinfo=timezone.utc)


# --- the day a run writes ----------------------------------------------------

@pytest.mark.parametrize("now, want", [
    (utc(6, 17), "2026-11-11"),     # on time: 11:47 IST -> tomorrow
    (utc(12, 17), "2026-11-11"),    # the worst measured delay (6h): still tomorrow
    (utc(18, 0), "2026-11-11"),     # 23:30 IST
    (utc(19, 0), "2026-11-11"),     # 00:30 IST on the 11th: the day just started, not the 12th
    (utc(0, 10, day=11), "2026-11-11"),  # 05:40 IST: still the current day
])
def test_a_scheduled_run_writes_the_next_ist_day_it_can_still_beat(now, want):
    assert rtd.target("schedule", "", now) == want


def test_a_manual_run_writes_today_so_a_bad_day_can_be_regenerated():
    assert rtd.target("workflow_dispatch", "", utc(6, 17)) == "2026-11-10"


def test_a_given_date_wins_and_a_bad_one_is_refused():
    assert rtd.target("schedule", "2026-12-01", utc(6, 17)) == "2026-12-01"
    with pytest.raises(ValueError):
        rtd.target("workflow_dispatch", "2026-13-01", utc(6, 17))
    with pytest.raises(ValueError):
        rtd.target("workflow_dispatch", "tomorrow; rm -rf /", utc(6, 17))
    assert rtd.main(["x", "--date", "nope"]) == 2


# --- the workflow ------------------------------------------------------------

def _wf():
    return yaml.safe_load(WF.read_text())


def _on(doc):
    return doc[next(k for k in doc if str(k) in ("on", "True"))]


def test_the_cron_lands_before_ist_midnight_even_at_the_worst_measured_delay():
    (cron,) = [c["cron"] for c in _on(_wf())["schedule"]]
    minute, hour = (int(x) for x in cron.split()[:2])
    worst_delay_min = 6 * 60          # measured: 03:59 start for a 22:00 cron
    ist_midnight_utc_min = 18 * 60 + 30
    assert hour * 60 + minute + worst_delay_min + 45 < ist_midnight_utc_min, (
        f"{cron!r} + 6h delay + the 45-minute job can miss the day it writes")


def test_the_day_is_computed_once_and_passed_to_every_script_call():
    doc = _wf()
    pick = next(s for s in doc["jobs"]["prepare"]["steps"] if s.get("id") == "pick")
    assert "scripts/rashifal_target_date.py" in pick["run"]
    assert pick["env"] == {"EVENT": "${{ github.event_name }}", "DATE_IN": "${{ inputs.date }}"}, (
        "the dispatch input reaches the shell through env, never interpolated")
    assert "${{ inputs.date }}" not in pick["run"]
    assert doc["jobs"]["generate"]["env"]["RASHIFAL_DATE"] == "${{ needs.prepare.outputs.date }}"
    text = WF.read_text()
    joined = text.replace("\\\n", " ")        # fold shell line continuations
    calls = re.findall(r"uv run python scripts/(?:rashifal_brief|publish_rashifal)\.py[^\n]*", joined)
    assert len(calls) >= 5
    for call in calls:
        assert "--date" in call, f"a script call without --date guesses the day: {call[:90]!r}"


# --- the ops panel -----------------------------------------------------------

def test_an_unread_record_is_loading_not_never_ran(monkeypatch):
    monkeypatch.setattr(ops_data, "_rashifal_runs", lambda: None)
    v = ops_data._rashifal_view("2026-11-10")
    assert v["loading"] is True and v["never_ran"] is False


def test_an_empty_record_is_never_ran(monkeypatch):
    monkeypatch.setattr(ops_data, "_rashifal_runs", lambda: {})
    v = ops_data._rashifal_view("2026-11-10")
    assert v["loading"] is False and v["never_ran"] is True


def test_a_day_written_ahead_shows_as_today_when_it_arrives(monkeypatch):
    runs = {"2026-11-11": {"en": {"sections": 12}, "hi": {"sections": 12}},
            "2026-11-10": {"en": {"sections": 12}, "hi": {"sections": 12}}}
    monkeypatch.setattr(ops_data, "_rashifal_runs", lambda: runs)
    v = ops_data._rashifal_view("2026-11-10")
    assert v["today_complete"] and v["today_label"] == "24/24"


def test_the_panel_template_has_a_loading_state_and_the_new_schedule():
    html = (ROOT / "src/astro_ai/templates/admin_ops.html").read_text()
    assert "{% if R.loading %}" in html and "record not loaded yet" in html
    assert "nightly · 03:30 IST" not in html
