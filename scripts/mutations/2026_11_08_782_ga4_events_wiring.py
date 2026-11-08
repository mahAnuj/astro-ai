"""#782 AC3: agent-measure runs the GA4 events export, non-fatally (2026-11-08)."""

MUTATIONS = [
    ("ga4 events: the export is not run",
     ".github/workflows/agent-measure.yml",
     "          uv run python scripts/fetch_ga4.py --days 28 --events > /tmp/ga4-events.json \\\n",
     "          true \\\n",
     "test_the_events_export_runs_in_the_fetch_step"),
    ("ga4 events: a failed export fails the whole measurement run",
     ".github/workflows/agent-measure.yml",
     '            || { echo "::warning::GA4 event export failed; /tmp/ga4-events.json is absent this run (#782)"; rm -f /tmp/ga4-events.json; }\n',
     '\n',
     "test_a_failed_events_export_cannot_fail_the_measurement_run"),
    ("ga4 events: the file is not persisted",
     ".github/workflows/agent-measure.yml",
     "          cp -f /tmp/ga4-events.json /tmp/measure/ 2>/dev/null || true\n",
     "",
     "test_the_file_is_persisted_with_the_others"),
]
