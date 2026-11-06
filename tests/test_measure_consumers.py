"""The planners read the committed analyst report, not a run's artifact.

Measured 2026-11-06: agent-work, agent-discover and agent-prioritise each took
the newest SUCCESSFUL agent-measure run and downloaded its `measurement`
artifact. That run is usually a collectors-only run whose analyst job was
skipped, so the download failed ("no valid artifacts found") under
continue-on-error, and only 18 of 74 build cycles since 10-30 planned with the
report. agent-measure already commits the same report as
measurements/latest.md, which every checkout holds."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _fetch_step(wf: str) -> str:
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / f"{wf}.yml").read_text())
    for job in doc["jobs"].values():
        for s in job.get("steps", []):
            if s.get("name") == "Fetch the latest measurement":
                return s["run"]
    raise AssertionError(f"{wf}: no 'Fetch the latest measurement' step")


@pytest.mark.parametrize("wf", ["agent-work", "agent-discover", "agent-prioritise"])
def test_the_committed_report_is_used_before_any_artifact(wf):
    run = _fetch_step(wf)
    assert "cp measurements/latest.md /tmp/measure/report.md" in run
    assert run.index("measurements/latest.md") < run.index("gh run download"), \
        "the artifact path must stay a fallback, not the first choice"


def test_agent_measure_writes_the_file_the_planners_read():
    run = (ROOT / ".github" / "workflows" / "agent-measure.yml").read_text()
    assert "cp /tmp/measure/report.md measurements/latest.md" in run


def test_the_analyst_is_told_about_every_file_the_fetch_writes():
    """Read the analyst's PROMPT only -- the fetch and persist steps name the
    same files, and a whole-file search passes with the prompt line deleted."""
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-measure.yml").read_text())
    prompts = [s["with"]["prompt"] for job in doc["jobs"].values() for s in job.get("steps", [])
               if "claude-code-action" in (s.get("uses") or "") and "analyst" in s["with"].get("prompt", "")]
    assert prompts, "no analyst prompt found"
    for f in ("gsc-daily.json", "ga4-daily.json", "gsc-trend-page.json", "gsc-trend-query.json"):
        assert f"/tmp/{f}" in prompts[0], f"{f} is fetched but not named to the analyst"
