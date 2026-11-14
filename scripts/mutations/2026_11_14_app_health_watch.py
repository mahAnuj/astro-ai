"""2026-11-14: the live app's health is filed after every cycle (steward), not by no one.

Each row re-breaks one piece and names the test that must go red."""

MUTATIONS = [
    ("app watch: a 3-call morning is judged on its own (one failure reads as 100%)",
     "scripts/watch_app_health.py",
     '    if app.get("ok") and int(app.get("calls") or 0) < MIN_CALLS:\n',
     '    if False:\n',
     "test_a_quiet_morning_falls_back_to_the_week_rather_than_crying_100_percent"),
    ("app watch: a local store is read as production",
     "scripts/watch_app_health.py",
     '    if str(app.get("store") or "").startswith("local:"):\n',
     '    if False:\n',
     "test_an_unreadable_or_local_store_is_not_ok_and_raises_nothing"),
    ("app watch: an unread app marks its open issues cleared",
     "scripts/file_ops_findings.py",
     "        if keep_prefix and kind.startswith(keep_prefix):\n            continue\n",
     "",
     "test_an_unread_app_leaves_its_open_issues_alone"),
    ("app watch: the bucket credentials are exported to the agents later in the job",
     ".github/workflows/agent-steward.yml",
     "          export_environment_variables: false\n",
     "          export_environment_variables: true\n",
     "test_credentials_reach_only_the_watcher_and_are_gone_before_any_agent"),
]
