"""The session-authored workflow PR of 2026-11-25: main-red-report reports dispatched main
runs (#1221, scripts/await_main_gates.py), and agent-measure / agent-sync gain full history,
the GA4 trend, kundli submissions and index status (#974, #1205, #1409, #1065). Exercised by
tests/test_await_main_gates.py. One area file, a literal list."""

MUTATIONS = [
    ("main-red: a pending run a later merge replaced is reported as a red main",
     "scripts/await_main_gates.py",
     '            if cur.get("conclusion") == "cancelled" and newer:\n',
     "            if False:\n",
     "test_a_replaced_pending_run_is_not_a_red_main"),
    ("main-red: a gates run from before the merge is taken as this merge's",
     "scripts/await_main_gates.py",
     '            if r.get("head_branch") == "main" and _ts(r["created_at"]) >= after]\n',
     '            if r.get("head_branch") == "main"]\n',
     "test_a_run_from_before_the_merge_is_never_taken"),
    ("main-red: agent-merge stops dispatching the reporter",
     ".github/workflows/agent-merge.yml",
     '            gh workflow run main-red-report.yml --repo "$GH_REPO" --ref main -f after="$after" \\\n',
     "            true \\\n",
     "test_agent_merge_dispatches_the_reporter_with_the_time_before_the_gates_dispatch"),
    ("measure: the analyst's checkout goes back to depth 1",
     ".github/workflows/agent-measure.yml",
     "        with:\n          fetch-depth: 0\n",
     "",
     "test_the_measurement_wiring_is_in_place"),
]
