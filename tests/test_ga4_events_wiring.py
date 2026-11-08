"""#782 AC3: agent-measure writes /tmp/ga4-events.json, non-fatally, and the
analyst is told the file exists and may be absent."""
from __future__ import annotations

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "agent-measure.yml"
TEXT = WF.read_text()


def _steps():
    doc = yaml.safe_load(TEXT)
    return [s for job in doc["jobs"].values() for s in job.get("steps", [])]


def test_the_events_export_runs_in_the_fetch_step():
    run = next(s["run"] for s in _steps() if "fetch_ga4.py --days 28 --daily" in (s.get("run") or ""))
    assert "fetch_ga4.py --days 28 --events > /tmp/ga4-events.json" in run


def test_a_failed_events_export_cannot_fail_the_measurement_run():
    """Never run live, and the split needs owner-registered dimensions."""
    run = next(s["run"] for s in _steps() if "--events" in (s.get("run") or ""))
    line = run[run.index("--events"):].split("\n")[0:2]
    assert "||" in " ".join(line) and "rm -f /tmp/ga4-events.json" in " ".join(line)


def test_the_analyst_is_told_the_file_exists_and_what_absent_means():
    assert "/tmp/ga4-events.json       GA4 event counts" in TEXT
    assert "absent means not measured, never zero" in TEXT


def test_the_file_is_persisted_with_the_others():
    assert "cp -f /tmp/ga4-events.json /tmp/measure/" in TEXT
