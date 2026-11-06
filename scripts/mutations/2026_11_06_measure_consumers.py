"""Planners read measurements/latest.md before a run artifact (2026-11-06)."""

MUTATIONS = [
    ("measure consumers: agent-work goes back to the artifact-only fetch",
     ".github/workflows/agent-work.yml",
     "            cp measurements/latest.md /tmp/measure/report.md\n",
     "            true\n",
     "test_the_committed_report_is_used_before_any_artifact"),
    ("measure consumers: the analyst stops being told about the trend files",
     ".github/workflows/agent-measure.yml",
     "              /tmp/gsc-trend-page.json   per-page change, this window vs the previous one\n",
     "",
     "test_the_analyst_is_told_about_every_file_the_fetch_writes"),
]
